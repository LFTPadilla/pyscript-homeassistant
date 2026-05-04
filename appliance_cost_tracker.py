"""
Appliance Cost & Water Tracker
================================
Detects washing machine and dishwasher cycles by monitoring power consumption.
Calculates energy cost per cycle and correlates with kitchen water meter.

Sensors:
  Dishwasher power:  sensor.sonoff_1002176d5e_power  (W)
  Washer power:      sensor.washer_machine_power      (W)
  Water (hourly):    sensor.espkitchen_water_h_liters (L — resets each hour)
  Water (total):     sensor.espkitchen_total_water_flow (pulses, cumulative)

Energy price: 940 COP/kWh

Cycle detection:
  - Starts when power > ACTIVE_THRESHOLD for 30s
  - Ends when power < IDLE_THRESHOLD continuously for the debounce period
  - Energy calculated via Riemann sum (W × elapsed seconds / 3600 / 1000)

False-alarm prevention:
  - Separate debounce times per appliance (5 min each) to survive low-power
    phases like dishwasher drying (≈16 W) or washer low-spin coast-down.
  - Minimum cycle duration guard: ignores cycle-end if total runtime is
    suspiciously short (< MIN_CYCLE_S).
  - Idle threshold kept low (dishwasher 10 W, washer 15 W) so brief dips
    don't reset the debounce timer unnecessarily.

Daily report at 07:10 (10 min after fridge report).
"""

from datetime import datetime, date, timedelta

COP_PER_KWH        = 940.0

# Power thresholds (W)
DISHWASHER_ACTIVE  = 30    # above = cycle running
DISHWASHER_IDLE    = 10    # below this → start idle debounce
WASHER_ACTIVE      = 100
WASHER_IDLE        = 15    # lowered from 20 W to reduce false triggers

# Debounce: power must stay below IDLE threshold for this long before cycle ends.
# Raised from 120 s to 300 s (5 min) to survive low-power drying/coast-down phases.
DISHWASHER_DEBOUNCE_S = 300   # 5 minutes
WASHER_DEBOUNCE_S     = 300   # 5 minutes

# Minimum realistic cycle duration.  A cycle-end signal is ignored if the
# appliance ran for less than this many seconds (guards against spurious start+stop).
DISHWASHER_MIN_CYCLE_S = 1200   # 20 minutes
WASHER_MIN_CYCLE_S     = 1800   # 30 minutes

# Water sensor
WATER_TOTAL_SENSOR = "sensor.espkitchen_total_water_flow"  # cumulative pulses
WATER_LITERS_PER_PULSE = 0.001  # adjust if known (typical: 1 pulse = 1mL or 1L)

# ── In-memory state ────────────────────────────────────────────────────────────

_state = {
    "dishwasher": {
        "active":        False,
        "cycle_start":   None,
        "energy_wh":     0.0,      # Wh accumulated this cycle
        "last_power":    0.0,
        "last_ts":       None,
        "idle_since":    None,
        "water_start":   None,     # total water pulses at cycle start
        "cycles_today":  [],       # list of finished cycle dicts
    },
    "washer": {
        "active":        False,
        "cycle_start":   None,
        "energy_wh":     0.0,
        "last_power":    0.0,
        "last_ts":       None,
        "idle_since":    None,
        "water_start":   None,
        "cycles_today":  [],
    },
}


def _get_water_total():
    try:
        val = state.get(WATER_TOTAL_SENSOR)
        return float(val) if val not in (None, "unavailable", "unknown") else None
    except (ValueError, TypeError):
        return None


def _safe_power(sensor_id):
    try:
        val = state.get(sensor_id)
        return float(val) if val not in (None, "unavailable", "unknown") else 0.0
    except (ValueError, TypeError):
        return 0.0


def _update_appliance(name, power, active_thresh, idle_thresh, debounce_s, min_cycle_s):
    """Core cycle tracker. Call on every power state change.

    Parameters
    ----------
    name          : "dishwasher" | "washer"
    power         : current power reading in Watts
    active_thresh : W above which a cycle is considered started
    idle_thresh   : W below which the idle debounce timer starts
    debounce_s    : seconds power must stay below idle_thresh to end the cycle
    min_cycle_s   : minimum seconds a cycle must last before it can be declared done
                    (prevents false alarms during brief low-power phases)
    """
    s = _state[name]
    now = datetime.now()
    ts  = now.timestamp()

    # Accumulate energy if cycle is active
    if s["active"] and s["last_ts"] is not None:
        elapsed_s = ts - s["last_ts"]
        s["energy_wh"] += s["last_power"] * elapsed_s / 3600.0  # W·s → Wh

    s["last_power"] = power
    s["last_ts"]    = ts

    # ── Cycle START ──────────────────────────────────────────────────────────
    if not s["active"] and power > active_thresh:
        s["active"]      = True
        s["cycle_start"] = now
        s["energy_wh"]   = 0.0
        s["idle_since"]  = None
        s["water_start"] = _get_water_total()
        log.info(f"ApplianceCost: {name} cycle STARTED at {now.strftime('%H:%M')}, water={s['water_start']}")

    # ── Cycle END detection (debounce + minimum duration guard) ─────────────
    elif s["active"] and power < idle_thresh:
        cycle_elapsed_s = ts - s["cycle_start"].timestamp()

        if cycle_elapsed_s < min_cycle_s:
            # Too short to be a real cycle end — skip idle detection entirely.
            log.info(
                f"ApplianceCost: {name} power dropped to {power:.1f}W but cycle only "
                f"{cycle_elapsed_s:.0f}s old (min={min_cycle_s}s). Ignoring idle."
            )
            return

        if s["idle_since"] is None:
            s["idle_since"] = ts
            log.info(
                f"ApplianceCost: {name} power dropped to {power:.1f}W "
                f"(below {idle_thresh}W). Idle debounce started ({debounce_s}s)."
            )
        elif (ts - s["idle_since"]) >= debounce_s:
            # Cycle finished!
            duration_s  = ts - s["cycle_start"].timestamp()
            energy_kwh  = s["energy_wh"] / 1000.0
            cost_cop    = energy_kwh * COP_PER_KWH

            # Water used (pulses → liters)
            water_end   = _get_water_total()
            if water_end is not None and s["water_start"] is not None:
                water_l = (water_end - s["water_start"]) * WATER_LITERS_PER_PULSE
            else:
                water_l = None

            cycle = {
                "start":      s["cycle_start"].strftime("%H:%M"),
                "duration_m": round(duration_s / 60, 1),
                "energy_kwh": round(energy_kwh, 4),
                "cost_cop":   round(cost_cop, 1),
                "water_l":    round(water_l, 1) if water_l is not None else None,
            }
            s["cycles_today"].append(cycle)

            log.info(
                f"ApplianceCost: {name} cycle DONE — "
                f"{cycle['duration_m']}min, {cycle['energy_kwh']}kWh, "
                f"{cycle['cost_cop']}COP, water={cycle['water_l']}L"
            )

            # Notify immediately when cycle ends
            water_str = f" · 💧 {cycle['water_l']:.0f}L" if cycle["water_l"] is not None else ""
            label = "🫧 Lavavajillas" if name == "dishwasher" else "👕 Lavadora"
            pyscript.notify_coco(
                message=(
                    f"{label} terminó.\n"
                    f"⏱️ {cycle['duration_m']} min · "
                    f"⚡ {cycle['energy_kwh']} kWh · "
                    f"💰 *{cycle['cost_cop']:.0f} COP*"
                    f"{water_str}"
                ),
                title=f"{label} listo",
                speak=False,
            )

            # Reset state
            s["active"]      = False
            s["cycle_start"] = None
            s["energy_wh"]   = 0.0
            s["idle_since"]  = None
            s["water_start"] = None

    elif s["active"] and power >= idle_thresh:
        # Still running — reset idle timer if it was counting down
        if s["idle_since"] is not None:
            log.info(
                f"ApplianceCost: {name} power back to {power:.1f}W "
                f"(>= {idle_thresh}W). Idle debounce reset."
            )
        s["idle_since"] = None


# ── State triggers ─────────────────────────────────────────────────────────────

@state_trigger("sensor.sonoff_1002176d5e_power")
def dishwasher_power_changed(**kwargs):
    task.unique("appliance_dishwasher_update")
    power = _safe_power("sensor.sonoff_1002176d5e_power")
    _update_appliance(
        "dishwasher", power,
        DISHWASHER_ACTIVE, DISHWASHER_IDLE,
        DISHWASHER_DEBOUNCE_S, DISHWASHER_MIN_CYCLE_S,
    )


@state_trigger("sensor.washer_machine_power")
def washer_power_changed(**kwargs):
    task.unique("appliance_washer_update")
    power = _safe_power("sensor.washer_machine_power")
    _update_appliance(
        "washer", power,
        WASHER_ACTIVE, WASHER_IDLE,
        WASHER_DEBOUNCE_S, WASHER_MIN_CYCLE_S,
    )


# ── Midnight reset ─────────────────────────────────────────────────────────────

@time_trigger("once(00:01:00)")
def appliance_midnight_reset():
    task.unique("appliance_midnight_reset")
    _state["dishwasher"]["cycles_today"].clear()
    _state["washer"]["cycles_today"].clear()
    log.info("ApplianceCost: daily counters reset at midnight")


# ── Daily report at 07:10 ──────────────────────────────────────────────────────

@time_trigger("once(07:10:00)")
def appliance_daily_report():
    task.unique("appliance_daily_report")

    lines = ["🔌 *Resumen electrodomésticos — ayer*\n"]
    any_data = False

    for name, label in [("dishwasher", "🫧 Lavavajillas"), ("washer", "👕 Lavadora")]:
        cycles = _state[name]["cycles_today"]
        if not cycles:
            lines.append(f"{label}: sin ciclos registrados")
            continue

        any_data = True
        total_kwh = sum(c["energy_kwh"] for c in cycles)
        total_cop = sum(c["cost_cop"]   for c in cycles)
        total_min = sum(c["duration_m"] for c in cycles)
        total_water = sum(c["water_l"] for c in cycles if c["water_l"] is not None)

        water_str = f" · 💧 {total_water:.0f}L" if total_water else ""
        lines.append(
            f"{label}: {len(cycles)} ciclo{'s' if len(cycles)>1 else ''} · "
            f"{total_min:.0f} min · "
            f"{total_kwh:.3f} kWh · "
            f"*{total_cop:.0f} COP*{water_str}"
        )

        for i, c in enumerate(cycles, 1):
            w = f" · 💧{c['water_l']:.0f}L" if c["water_l"] is not None else ""
            lines.append(f"  _{i}. {c['start']} — {c['duration_m']}min · {c['cost_cop']:.0f}COP{w}_")

    if not any_data:
        lines.append("_Sin ciclos detectados ayer._")

    pyscript.notify_coco(
        message="\n".join(lines),
        title="Reporte electrodomésticos",
        speak=False,
    )
