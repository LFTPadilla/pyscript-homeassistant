"""
Fridge Door Cost Tracker
========================
Tracks fridge/freezer door open events and daily energy consumption
from the 'refrigerator' smart plug.

Logic:
- Counts door openings and total open time (fridge + freezer separately)
- Reads total daily energy from the plug (captures ALL compressor work,
  including recovery cycles AFTER the door closes)
- At midnight: saves yesterday's snapshot and resets counters for the new day
- At 07:00: sends a summary of YESTERDAY (full 24h) with:
    · Total kWh + COP for the previous day
    · Number of openings + total time open
    · Estimated cost per opening (total / openings)

Energy price: 940 COP/kWh
Sensors: binary_sensor.fridge_door, binary_sensor.freezer_door
Plug:    sensor.refrigerator_energy (kWh cumulative)
"""

FRIDGE_DOOR   = "binary_sensor.fridge_door"
FREEZER_DOOR  = "binary_sensor.freezer_door"
ENERGY_SENSOR = "sensor.refrigerator_energy"

COP_PER_KWH   = 940.0

# Current day energy baseline (captured at midnight / startup)
_energy_day_start = None

# Yesterday's closed data (saved at midnight, reported at 07:00)
_yesterday = {
    "energy_start": None,   # kWh at start of yesterday
    "energy_end":   None,   # kWh at end of yesterday (midnight)
    "door_stats": {
        "fridge":  {"count": 0, "total_s": 0.0},
        "freezer": {"count": 0, "total_s": 0.0},
    },
    "date": None,           # "YYYY-MM-DD" label
}

# Door open tracking (current day)
_open_at = {"fridge": None, "freezer": None}
_door_stats = {
    "fridge":  {"count": 0, "total_s": 0.0},
    "freezer": {"count": 0, "total_s": 0.0},
}


def _get_energy():
    try:
        val = state.get(ENERGY_SENSOR)
        if val is None or str(val).lower() in ("unknown", "unavailable"):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def _snapshot_day_start():
    global _energy_day_start
    e = _get_energy()
    if e is not None:
        _energy_day_start = e
        log.info(f"FridgeCost: day-start energy snapshot = {e:.4f} kWh")
    else:
        log.warning("FridgeCost: could not read energy sensor at day start")


def _record_open(door: str):
    _open_at[door] = float(time.time())
    log.info(f"FridgeCost: {door} opened")


def _record_close(door: str):
    if _open_at[door] is None:
        return
    duration_s = float(time.time()) - _open_at[door]
    _door_stats[door]["count"]   += 1
    _door_stats[door]["total_s"] += duration_s
    log.info(f"FridgeCost: {door} closed — {duration_s:.0f}s open (total openings: {_door_stats[door]['count']})")
    _open_at[door] = None


# ── Door triggers ─────────────────────────────────────────────────────────────

@state_trigger(f"{FRIDGE_DOOR} == 'on'")
def fridge_opened():
    _record_open("fridge")


@state_trigger(f"{FRIDGE_DOOR} == 'off'")
def fridge_closed():
    _record_close("fridge")


@state_trigger(f"{FREEZER_DOOR} == 'on'")
def freezer_opened():
    _record_open("freezer")


@state_trigger(f"{FREEZER_DOOR} == 'off'")
def freezer_closed():
    _record_close("freezer")


# ── Midnight: close out the day ───────────────────────────────────────────────

@time_trigger("once(00:00:30)")
def midnight_reset():
    """At midnight: save yesterday's data and reset counters for the new day."""
    global _yesterday, _energy_day_start
    task.unique("fridge_midnight_reset")

    from datetime import date, timedelta
    yesterday_label = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    energy_end = _get_energy()

    # Save yesterday's complete data
    _yesterday = {
        "energy_start": _energy_day_start,
        "energy_end":   energy_end,
        "door_stats": {
            "fridge":  {"count": _door_stats["fridge"]["count"],  "total_s": _door_stats["fridge"]["total_s"]},
            "freezer": {"count": _door_stats["freezer"]["count"], "total_s": _door_stats["freezer"]["total_s"]},
        },
        "date": yesterday_label,
    }

    log.info(f"FridgeCost: midnight — saved yesterday ({yesterday_label}) data, energy_end={energy_end}")

    # Reset current-day counters
    for door in _door_stats:
        _door_stats[door]["count"]   = 0
        _door_stats[door]["total_s"] = 0.0

    # New day baseline
    _snapshot_day_start()


# ── 07:00: report yesterday ───────────────────────────────────────────────────

@time_trigger("once(07:00:00)")
def daily_fridge_summary():
    """Send yesterday's full 24h report at 07:00."""
    task.unique("daily_fridge_summary")

    y = _yesterday
    date_label = y.get("date") or "ayer"

    e_start = y.get("energy_start")
    e_end   = y.get("energy_end")

    if e_start is not None and e_end is not None:
        total_kwh = max(0.0, e_end - e_start)
        total_cop = total_kwh * COP_PER_KWH
    else:
        total_kwh = None
        total_cop = None

    door_stats = y.get("door_stats", _door_stats)
    total_openings = door_stats["fridge"]["count"] + door_stats["freezer"]["count"]

    lines = [f"🧊 *Resumen nevera — {date_label}*\n"]

    if total_kwh is not None:
        lines.append(f"⚡ *Energía (24h):* {total_kwh:.3f} kWh → *{total_cop:.0f} COP*")
    else:
        lines.append("⚡ *Energía (24h):* sin datos (sensor no disponible)")

    lines.append("")

    for door, label in [("fridge", "Nevera"), ("freezer", "Freezer")]:
        count   = door_stats[door]["count"]
        total_s = door_stats[door]["total_s"]
        mins, secs = divmod(int(total_s), 60)
        if count == 0:
            lines.append(f"🚪 *{label}:* sin aperturas")
        else:
            lines.append(
                f"🚪 *{label}:* {count} apertura{'s' if count != 1 else ''} · "
                f"{mins}m {secs}s abierta en total"
            )

    if total_cop is not None and total_openings > 0:
        cost_per_open = total_cop / total_openings
        lines.append(
            f"\n📊 *Costo por apertura:* ~{cost_per_open:.0f} COP "
            f"({total_openings} aperturas)"
        )

    message = "\n".join(lines)
    log.info(f"FridgeCost 07:00 summary:\n{message}")
    # pyscript.notify_coco(message=message, title="Costo Nevera ayer", speak=False)


# ── Startup snapshot ──────────────────────────────────────────────────────────

@time_trigger("startup")
def startup_snapshot():
    """Capture energy baseline when pyscript loads."""
    task.unique("fridge_startup_snapshot")
    _snapshot_day_start()
    log.info("FridgeCost: module loaded, energy baseline captured.")
