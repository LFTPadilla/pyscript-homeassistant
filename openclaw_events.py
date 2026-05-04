"""
OpenClaw Events — complex aggregation automations.
  1. Energy summary at 10 PM
  2. Sedentary nudge (every 2 hours of inactivity)
  3. Door left open alert (main door, livingroom window)
"""

from datetime import datetime

# ─── 1. Energy Summary at 10 PM ──────────────────────────────────

POWER_SENSORS = {
    "Washer":       "sensor.washer_machine_power",
    "Fridge":       "sensor.refrigerator_power",
    "Server":       "sensor.hp_nixos_power",
}

@time_trigger("cron(0 22 * * *)")
async def nightly_energy_summary():
    """Push a summary of current power draw at 10 PM."""
    lines = []
    total_w = 0.0
    for label, entity in POWER_SENSORS.items():
        try:
            val = float(state.get(entity))
            total_w += val
            lines.append(f"  • {label}: {val:.0f} W")
        except (ValueError, TypeError):
            lines.append(f"  • {label}: unavailable")

    body = "\n".join(lines)
    msg = f"⚡ Nightly Power Snapshot\n{body}\n  ─────\n  Total: {total_w:.0f} W"

    # await pyscript.notify_coco(
    #     message=msg,
    #     title="⚡ Energy Summary",
    #     speak=True,
    #     speak_lang="en",
    # )
    log.info("Energy summary sent (notification commented out)")


# ─── 2. Sedentary Nudge ──────────────────────────────────────────

# Check every 2 hours during waking hours; nudge if steps are low.
STEPS_ENTITY = "sensor.iphone_steps"
SEDENTARY_STEP_THRESHOLD = 250  # steps expected per 2‑hour window

_last_step_count = None

@time_trigger("cron(0 10,12,14,16,18,20 * * *)")
async def sedentary_nudge():
    """Nudge Felipe if step count hasn't increased much in 2 hours."""
    global _last_step_count

    try:
        current_steps = int(float(state.get(STEPS_ENTITY)))
    except (ValueError, TypeError):
        log.warning("Sedentary nudge: steps sensor unavailable")
        _last_step_count = None
        return

    # Skip if in Away/Sleep mode (not sedentary at home)
    mode = state.get("input_select.house_mode")
    if mode in ["Away", "Sleep"]:
        _last_step_count = current_steps
        return

    if _last_step_count is not None:
        delta = current_steps - _last_step_count
        if delta < SEDENTARY_STEP_THRESHOLD:
            # await pyscript.notify_coco(
            #     message=f"🚶 Only {delta} steps in the last 2 hours. Time to move around!",
            #     title="Move Reminder",
            #     speak=True,
            #     speak_lang="en",
            #     speak_volume=0.4,
            # )
            log.info(f"Sedentary nudge suppressed (delta={delta}) — notifications disabled")

    _last_step_count = current_steps


# ─── 3. Door Left Open Alert ─────────────────────────────────────

DOOR_SENSORS = {
    "Main door":        "binary_sensor.main_door_sensor",
    "Living room window": "binary_sensor.livingroom_door_sensor",
}

DOOR_OPEN_TIMEOUT = 300  # seconds (5 minutes)

@state_trigger("binary_sensor.main_door_sensor == 'on'")
@state_trigger("binary_sensor.livingroom_door_sensor == 'on'")
async def door_left_open_alert(**kwargs):
    """Alert if a door/window stays open for more than 5 minutes."""
    trigger_entity = kwargs.get("var_name", "")

    # Determine friendly name
    friendly = "Door"
    for name, eid in DOOR_SENSORS.items():
        if eid == trigger_entity:
            friendly = name
            break

    task.unique(f"door_open_{trigger_entity}")

    await task.sleep(DOOR_OPEN_TIMEOUT)

    # Re‑check — still open?
    if state.get(trigger_entity) == 'on':
        # Skip alert for Living Room Window if NOT in Away or Sleep mode
        if trigger_entity == "binary_sensor.livingroom_door_sensor":
            current_mode = state.get("input_select.house_mode")
            if current_mode not in ["Away", "Sleep"]:
                log.info(f"Door open alert: Window is open, but house is in {current_mode} mode. Skipping alert.")
                return

        minutes = DOOR_OPEN_TIMEOUT // 60
        await pyscript.notify_coco(
            message=f"🚪 {friendly} has been open for {minutes} minutes!",
            title="Door Open Alert",
            speak=True,
            speak_lang="en",
        )
        log.warning(f"Door open alert: {friendly} open >{minutes} min")
