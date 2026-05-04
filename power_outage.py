"""
Power Outage Detection & Restoration Automation
================================================
Power chain: House Grid/Solar → EcoFlow River 2 → Small UPS → Desk devices
                                                             (router, Mac, monitor, RPi, miniPC)

PRIMARY sensor: sensor.river2_battery_ac_in_power
  - Drops to 0W instantly when grid power is lost
  - Most reliable: direct measurement at the source

SECONDARY sensors (confirmation): Sonoff voltage sensors
  - sensor.sonoff_1002176d5e_voltage
  - sensor.sonoff_1002058e4c_voltage
  - sensor.sonoff_1002059aaf_voltage
  - sensor.sonoff_1002059636_voltage

Outage = River 2 AC input drops to 0 + at least 2 Sonoff confirm low voltage
Restored = River 2 AC input back > 50W OR Sonoff majority back > 100V
"""

from datetime import datetime

# River 2 AC input threshold — below this = no grid power
RIVER2_OUTAGE_THRESHOLD = 5.0   # Watts
RIVER2_RESTORE_THRESHOLD = 50.0  # Watts

# Sonoff voltage thresholds
VOLTAGE_OUTAGE_THRESHOLD = 10.0    # Volts
VOLTAGE_RESTORE_THRESHOLD = 100.0  # Volts
SONOFF_CONFIRM_MIN_OUTAGE = 2      # Require at least 2 sensors low to confirm outage

SONOFF_CONFIRM_SENSORS = [
    "sensor.sonoff_1002176d5e_voltage",
    "sensor.sonoff_1002058e4c_voltage",
    "sensor.sonoff_1002059aaf_voltage",
    "sensor.sonoff_1002059636_voltage",
]

_outage_start_time = None
_outage_notified = False


def _get_river2_ac_in():
    """Get River 2 AC input power (primary outage sensor).
    Returns -1 if sensor is unavailable/unknown (to skip outage logic).
    Only returns 0 when the sensor explicitly reads 0W (true outage).
    """
    raw = state.get("sensor.river2_battery_ac_in_power")
    if raw is None or str(raw).lower() in ("unknown", "unavailable", "none", ""):
        return -1  # sensor offline / battery restarting — NOT an outage
    try:
        return float(raw)
    except (TypeError, ValueError):
        return -1  # unparseable — treat as unavailable, not as outage


def _get_river2_info():
    """Get relevant River 2 stats for notifications."""
    try:
        battery = state.get("sensor.river2_battery_battery_level") or "?"
        remaining = state.get("sensor.river2_battery_discharge_remaining_time") or "?"
        solar = state.get("sensor.river2_battery_solar_in_power") or "0"
        return f"🔋 {battery}% | ☀️ Solar: {solar}W | ⏱️ Autonomía: {remaining} min"
    except Exception:
        return ""


def _get_sonoff_dead_count():
    """Count confirmation Sonoff sensors reading low voltage."""
    dead = 0
    for eid in SONOFF_CONFIRM_SENSORS:
        val = state.get(eid)
        try:
            if float(val) < VOLTAGE_OUTAGE_THRESHOLD:
                dead += 1
        except (TypeError, ValueError):
            pass
    return dead


@state_trigger("sensor.river2_battery_ac_in_power")
def monitor_power_outage_river2(**kwargs):
    """
    PRIMARY trigger: River 2 AC input power change.
    Instantly detects grid loss (ac_in drops to 0W).
    """
    global _outage_start_time, _outage_notified

    task.unique("power_outage_monitor")

    ac_in = _get_river2_ac_in()

    if ac_in < 0:
        log.debug("Power monitor: sensor unavailable/unknown — skipping (not an outage)")
        return  # sensor unavailable or battery restarting — ignore

    log.debug(f"Power monitor (River2): ac_in={ac_in}W | outage_active={_outage_notified}")

    # ── OUTAGE DETECTED (River2 + Sonoff confirmation) ─────────────────────
    if ac_in <= RIVER2_OUTAGE_THRESHOLD and not _outage_notified:
        dead = _get_sonoff_dead_count()
        if dead < SONOFF_CONFIRM_MIN_OUTAGE:
            # Typical false positive when EcoFlow is unplugged manually
            log.info(
                f"Power monitor: River2 low ({ac_in}W) but Sonoff confirms only {dead}/{len(SONOFF_CONFIRM_SENSORS)} low → skip outage alert"
            )
            return

        _outage_start_time = datetime.now()
        _outage_notified = True

        river_info = _get_river2_info()
        log.warning(f"⚡ POWER OUTAGE at {_outage_start_time.strftime('%H:%M:%S')} | AC in: {ac_in}W | Sonoff low: {dead}/{len(SONOFF_CONFIRM_SENSORS)} | {river_info}")

        pyscript.notify_coco(
            message=(
                f"⚡ *Apagón detectado* a las {_outage_start_time.strftime('%H:%M')}.\n"
                f"Confirmación Sonoff: {dead}/{len(SONOFF_CONFIRM_SENSORS)} en bajo voltaje.\n"
                f"{river_info}\n"
                f"Desk en UPS — router, Mac, RPi activos."
            ),
            title="⚡ Luz se fue",
            speak=False,
        )

    # ── POWER RESTORED ───────────────────────────────────────────────────────
    elif _outage_notified:
        dead = _get_sonoff_dead_count()
        if not (ac_in >= RIVER2_RESTORE_THRESHOLD or dead < SONOFF_CONFIRM_MIN_OUTAGE):
            return
        restored_at = datetime.now()
        _outage_notified = False

        if _outage_start_time:
            duration_sec = int((restored_at - _outage_start_time).total_seconds())
            duration_min = duration_sec // 60
            duration_s = duration_sec % 60
            duration_str = f"{duration_min}m {duration_s}s" if duration_min > 0 else f"{duration_s}s"
        else:
            duration_str = "desconocida"

        river_info = _get_river2_info()
        log.info(f"✅ POWER RESTORED at {restored_at.strftime('%H:%M:%S')} | Duration: {duration_str} | AC in: {ac_in}W")

        pyscript.notify_coco(
            message=(
                f"✅ *Luz volvió* a las {restored_at.strftime('%H:%M')}.\n"
                f"Duración: *{duration_str}*\n"
                f"{river_info}"
            ),
            title="✅ Luz restaurada",
            speak=False,
        )

        _outage_start_time = None


@state_trigger(
    "sensor.sonoff_1002176d5e_voltage or "
    "sensor.sonoff_1002058e4c_voltage or "
    "sensor.sonoff_1002059aaf_voltage or "
    "sensor.sonoff_1002059636_voltage"
)
def monitor_power_outage_sonoff(**kwargs):
    """
    SECONDARY trigger: Sonoff voltage sensors as backup confirmation.
    Catches outages if River 2 sensor is unavailable.
    """
    global _outage_start_time, _outage_notified

    if _outage_notified:
        return  # River 2 already handling it

    ac_in = _get_river2_ac_in()
    if ac_in >= 0:
        return  # River 2 sensor is working, defer to primary

    # River 2 unavailable — use Sonoff as fallback
    dead = _get_sonoff_dead_count()
    task.unique("power_outage_monitor")

    if dead >= SONOFF_CONFIRM_MIN_OUTAGE and not _outage_notified:
        _outage_start_time = datetime.now()
        _outage_notified = True
        log.warning(f"⚡ OUTAGE (Sonoff fallback): {dead}/{len(SONOFF_CONFIRM_SENSORS)} sensors low")
        pyscript.notify_coco(
            message=(
                f"⚡ *Apagón detectado* (vía Sonoff) a las {_outage_start_time.strftime('%H:%M')}. "
                f"Confirmación: {dead}/{len(SONOFF_CONFIRM_SENSORS)} sensores. River 2 no responde."
            ),
            title="⚡ Luz se fue",
            speak=False,
        )


@time_trigger("startup")
def power_outage_startup_check():
    """On pyscript startup, check current power state and reset vars."""
    global _outage_start_time, _outage_notified

    ac_in = _get_river2_ac_in()
    log.info(f"Power outage module loaded. River2 AC in: {ac_in}W")

    if ac_in >= RIVER2_RESTORE_THRESHOLD:
        _outage_start_time = None
        _outage_notified = False
        log.info("Power outage: startup — grid power normal.")
    elif ac_in >= 0 and ac_in <= RIVER2_OUTAGE_THRESHOLD:
        dead = _get_sonoff_dead_count()
        if dead >= SONOFF_CONFIRM_MIN_OUTAGE:
            _outage_start_time = datetime.now()
            _outage_notified = True
            log.warning(f"Power outage: startup — outage confirmed ({dead}/{len(SONOFF_CONFIRM_SENSORS)} Sonoff low).")
        else:
            _outage_start_time = None
            _outage_notified = False
            log.info("Power outage: startup — River2 low without Sonoff confirmation (likely manual EcoFlow disconnect).")
