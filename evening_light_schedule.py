"""
Evening Light Schedule — Circadian Wind-Down
=============================================
Gradual light reduction from 18:00 to 21:00 to support melatonin production.

Schedule:
  18:00 → 10% brightness, 2700K warm yellow (gentle transition begins)
  19:00 → 5% brightness, 2000K (very dim, ultra-warm)
  20:00 → Red mode ON, 20% brightness, RGB red [255,0,0]
  20:00→21:00 → Smooth ramp from 20% → 1% red (every 5 min)
  21:00 → 1% red (minimum) — stays until Sleep mode

All transitions respect the current house mode:
  - Skips if mode is Away, Cine, Friends, or Hug (social/activity modes)
  - Always runs in Day, Night, Reading, Meditation
"""

from datetime import datetime

RED_RGB    = [255, 0, 0]
SKIP_MODES = {"Away", "Cine", "Friends", "Sleep"}

ALL_LIGHTS = [
    "light.bathroom_light",
    "light.kitchen_light",
    "light.closet_strip_light",
    "light.bedroom_light",
    "light.livingroom_light",
]


def _should_run():
    mode = state.get("input_select.house_mode")
    return mode not in SKIP_MODES


def _set_lights_warm(brightness_pct, kelvin):
    """Set all available lights to warm white."""
    brightness_8bit = int(round(255 * brightness_pct / 100))
    for light_entity in ALL_LIGHTS:
        try:
            if state.get(light_entity) not in ("unavailable", "unknown"):
                light.turn_on(
                    entity_id=light_entity,
                    brightness=brightness_8bit,
                    color_temp_kelvin=kelvin,
                )
        except Exception as e:
            log.warning(f"EveningLight: {light_entity} — {e}")

    # Update shared input_number helpers
    input_number.brightness_lights = brightness_pct
    input_number.kelvin_temp = kelvin
    log.info(f"EveningLight: warm {brightness_pct}% / {kelvin}K")


def _set_lights_red(brightness_pct):
    """Set all available lights to red."""
    brightness_8bit = int(round(255 * brightness_pct / 100))
    for light_entity in ALL_LIGHTS:
        try:
            if state.get(light_entity) not in ("unavailable", "unknown"):
                light.turn_on(
                    entity_id=light_entity,
                    brightness=brightness_8bit,
                    rgb_color=RED_RGB,
                )
        except Exception as e:
            log.warning(f"EveningLight: {light_entity} — {e}")

    log.info(f"EveningLight: red {brightness_pct}%")


# ── 18:00 — Warm yellow transition ───────────────────────────────────────────

@time_trigger("once(18:00:00)")
def evening_phase_1():
    """18:00 → 10% warm yellow (2700K)"""
    task.unique("evening_phase_1")
    if not _should_run():
        return
    _set_lights_warm(10, 2700)
    log.info("EveningLight: Phase 1 — 18:00 warm yellow 10%")


# ── 19:00 — Ultra dim warm ────────────────────────────────────────────────────

@time_trigger("once(19:00:00)")
def evening_phase_2():
    """19:00 → 5% ultra-warm (2000K)"""
    task.unique("evening_phase_2")
    if not _should_run():
        return
    _set_lights_warm(5, 2000)
    log.info("EveningLight: Phase 2 — 19:00 ultra-warm 5%")


# ── 20:00 — Red mode + ramp down ─────────────────────────────────────────────

@time_trigger("once(20:00:00)")
def evening_phase_3():
    """20:00 → Red mode ON at 20%, then ramp to 1% over 60 minutes."""
    task.unique("evening_phase_3")
    if not _should_run():
        return

    # Activate red mode boolean
    input_boolean.light_red_mode = "on"
    _set_lights_red(20)
    log.info("EveningLight: Phase 3 — 20:00 RED 20%")

    # Ramp from 20% → 1% over 60 min (12 steps × 5 min)
    # Step size: (20 - 1) / 12 ≈ 1.58% per step
    start_pct = 20.0
    end_pct   = 1.0
    steps     = 12
    step_size = (start_pct - end_pct) / steps

    for i in range(1, steps + 1):
        task.sleep(300)  # 5 minutes

        # Check if user manually changed mode — stop ramp
        if not _should_run() or input_select.house_mode == "Sleep":
            log.info("EveningLight: ramp interrupted (mode change)")
            return

        current_pct = max(end_pct, start_pct - (i * step_size))
        _set_lights_red(round(current_pct, 1))

    log.info("EveningLight: ramp complete — holding at 1% red until Sleep")


# ── Service to manually trigger red mode now ─────────────────────────────────

@service
def activate_red_mode(brightness_pct=20):
    """Manually activate red mode at specified brightness (default 20%)."""
    input_boolean.light_red_mode = "on"
    _set_lights_red(brightness_pct)
    log.info(f"EveningLight: manual red mode at {brightness_pct}%")
