from datetime import datetime
from typing import Callable
import time


RED_RGB = [255, 0, 0]
EXCLUDED_LIGHTS = {"light.bathroom_fan_dimmer", "light.kitchen_fan_dimmer"}
TIME_19_00 = datetime.strptime("19:00", "%H:%M").time()
TIME_20_00 = datetime.strptime("20:00", "%H:%M").time()

@service
def get_brightness_8bit(value: float = 0) -> int:
    """
    Convert brightness percentage to 8-bit integer value (0-255)

    Args:
        value: Brightness percentage (0-100), uses input_number.brightness_lights if 0

    Returns:
        8-bit brightness value as integer (0-255)
    """
    try:
        brightness_ptc = float(input_number.brightness_lights) if value == 0 else value
        brightness_8bit = int(round((brightness_ptc * 255) / 100))
        # Ensure it's within valid range and definitely an integer
        brightness_8bit = max(0, min(255, brightness_8bit))
        log.debug(f"Brightness conversion: {brightness_ptc}% → {brightness_8bit}/255 (type: {type(brightness_8bit)})")
        return brightness_8bit
    except (ValueError, AttributeError) as e:
        log.error(f"Failed to get brightness value: {e}")
        return int(127)  # 50% default brightness as explicit integer


@service
async def smooth_transition(
    entity_id: str,
    attribute: str = "brightness",
    target: float = 0,
    duration: float = 5,
    interval: float = 0.1
) -> None:
    """
    Smoothly transition light attributes with easing animation

    Perfect for gentle light dimming to off, or smooth brightness/temperature changes

    Args:
        entity_id: Light entity to control (e.g., 'light.kitchen_light')
        attribute: 'brightness' or 'color_temp' (default: 'brightness')
        target: Target value to reach (0-100 for brightness, K for color_temp)
        duration: Transition duration in seconds (default: 5 for gentle fade)
        interval: Update interval in seconds (default: 0.1 for smooth animation)

    Examples:
        # Gentle 5-second fade to off
        pyscript.smooth_transition(entity_id='light.kitchen_light', target=0)

        # Quick 2-second brightness change
        pyscript.smooth_transition(entity_id='light.bedroom_light', target=50, duration=2)

        # Slow color temperature transition
        pyscript.smooth_transition(entity_id='light.living_room', attribute='color_temp', target=2700, duration=10)
    """
    task.unique(f"smooth_transition_{entity_id.replace('.', '_')}_{attribute}")

    try:
        # Get current value from the actual light entity, not input_number
        light_attrs = state.getattr(entity_id)
        if not light_attrs:
            log.error(f"Light transition: Entity {entity_id} not found")
            return

        if attribute == "brightness":
            # Get current brightness as percentage (0-100)
            current_brightness_255 = light_attrs.get("brightness", 255)
            start_value = (current_brightness_255 * 100) / 255
        elif attribute == "color_temp":
            start_value = light_attrs.get("color_temp", 3000)
        else:
            log.error(f"Light transition: Invalid attribute '{attribute}'. Use 'brightness' or 'color_temp'")
            return

        log.info(f"Light transition: {entity_id} {attribute} {start_value:.1f} → {target} over {duration}s")

        # Special handling for turning off lights
        if attribute == "brightness" and target == 0:
            # Ensure light is on before starting transition
            if state.get(entity_id) != 'on':
                log.debug(f"Light transition: {entity_id} already off, skipping")
                return

        start_time = time.time()
        steps = int(duration / interval)

        for step in range(steps):
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break

            progress = elapsed / duration
            # Smooth easing - feels more natural than linear
            eased = 1 - (1 - progress) ** 2  # Ease out quad
            current = start_value + (target - start_value) * eased

            try:
                if attribute == "brightness":
                    if current <= 1:  # Close to zero, just turn off
                        light.turn_off(entity_id=entity_id)
                        log.info(f"Light transition: {entity_id} turned OFF (fade complete)")
                        return
                    else:
                        brightness_255 = int((current * 255) / 100)
                        light.turn_on(entity_id=entity_id, brightness=brightness_255)
                        log.debug(f"Light transition: {entity_id} brightness {current:.1f}% ({brightness_255}/255)")

                elif attribute == "color_temp":
                    light.turn_on(entity_id=entity_id, color_temp=int(current))
                    log.debug(f"Light transition: {entity_id} color_temp {current:.0f}K")

                await task.sleep(interval)

            except Exception as e:
                log.warning(f"Light transition: Failed to update {entity_id} at step {step} - {e}")
                break

        # Ensure final state is reached
        try:
            if attribute == "brightness":
                if target == 0:
                    light.turn_off(entity_id=entity_id)
                    log.info(f"Light transition: {entity_id} fade to OFF completed")
                else:
                    brightness_255 = int((target * 255) / 100)
                    light.turn_on(entity_id=entity_id, brightness=brightness_255)
                    log.info(f"Light transition: {entity_id} brightness set to {target}%")
            else:
                light.turn_on(entity_id=entity_id, color_temp=int(target))
                log.info(f"Light transition: {entity_id} color_temp set to {target}K")

        except Exception as e:
            log.error(f"Light transition: Failed to set final state for {entity_id} - {e}")

    except Exception as e:
        log.error(f"Light transition: Error for {entity_id} - {e}")

def _calculate_red_brightness(default_brightness: int, now_time) -> int:
    """Determine brightness for red mode using evening schedule."""
    if now_time >= TIME_19_00:
        percentage = 0.01 if now_time >= TIME_20_00 else 0.20
        return max(1, int(round(255 * percentage)))
    return max(1, default_brightness)


def _apply_light_settings(light_entity: str, brightness_8bit: int, kelvin: float, red_mode: bool, now_time) -> None:
    """Turn on a light with either red or kelvin settings."""
    if red_mode:
        red_brightness = _calculate_red_brightness(brightness_8bit, now_time)
        try:
            light.turn_on(entity_id=light_entity, brightness=red_brightness, rgb_color=RED_RGB)
        except Exception:
            light.turn_on(entity_id=light_entity, brightness=red_brightness, color_temp_kelvin=kelvin)
    else:
        light.turn_on(entity_id=light_entity, brightness=brightness_8bit, color_temp_kelvin=kelvin)


def _apply_settings_to_lights(lights, brightness_8bit: int, kelvin: float, red_mode: bool, only_if_on: bool) -> int:
    """Apply the requested settings to a collection of lights."""
    updated_count = 0
    now_time = datetime.now().time()

    for light_entity in lights:
        if light_entity in EXCLUDED_LIGHTS:
            log.debug(f"Skipping excluded light {light_entity}")
            continue

        if only_if_on and state.get(light_entity) != 'on':
            continue

        try:
            _apply_light_settings(light_entity, brightness_8bit, kelvin, red_mode, now_time)
            updated_count += 1
        except Exception as e:
            log.warning(f"Failed to update light {light_entity}: {e}")

    return updated_count


@state_trigger("input_number.brightness_lights or input_number.kelvin_temp")
def brightness_kelvin_updated():
    """Update all active lights when brightness or color temperature changes"""
    task.unique("brightness_kelvin_update")

    try:
        lights = state.names(domain="light")
        brightness_8bit = get_brightness_8bit()
        kelvin = float(input_number.kelvin_temp)
        red_mode_active = state.get("input_boolean.light_red_mode") == 'on'

        updated_count = _apply_settings_to_lights(
            lights,
            brightness_8bit=brightness_8bit,
            kelvin=kelvin,
            red_mode=red_mode_active,
            only_if_on=True,
        )

        if red_mode_active:
            log.info(f"Updated {updated_count} lights for red mode")
        else:
            log.info(f"Updated {updated_count} lights: brightness={brightness_8bit:.0f}/255, kelvin={kelvin}K")

    except Exception as e:
        log.error(f"Failed to update lights brightness/kelvin: {e}")


@service
def turn_on_off_all_lights(action: str, force_red: bool = False):
    """
    Turn all lights on or off

    Args:
        action: 'on' or 'off'
    """
    task.unique("all_lights_control")

    try:
        lights = state.names(domain="light")

        if action == 'on':
            brightness_8bit = get_brightness_8bit()
            kelvin = float(input_number.kelvin_temp)
            red_mode_active = force_red or state.get("input_boolean.light_red_mode") == 'on'

            success_count = _apply_settings_to_lights(
                lights,
                brightness_8bit=brightness_8bit,
                kelvin=kelvin,
                red_mode=red_mode_active,
                only_if_on=False,
            )

            if red_mode_active:
                log.info(f"Turned on {success_count}/{len(lights)} lights in red mode")
            else:
                log.info(f"Turned on {success_count}/{len(lights)} lights at {brightness_8bit:.0f}/255, {kelvin}K")

        elif action == 'off':
            success_count = 0
            for light_entity in lights:
                try:
                    light.turn_off(entity_id=light_entity)
                    success_count += 1
                except Exception as e:
                    log.warning(f"Failed to turn off light {light_entity}: {e}")

            log.info(f"Turned off {success_count}/{len(lights)} lights")
        else:
            log.error(f"Invalid action '{action}' - use 'on' or 'off'")

    except Exception as e:
        log.error(f"Failed to control all lights: {e}")


def _restore_kelvin_settings() -> None:
    """Reapply kelvin configuration to all currently active lights."""
    lights = state.names(domain="light")
    if not lights:
        log.info("Red light mode deactivated - no lights found to restore")
        return

    brightness_8bit = get_brightness_8bit()
    kelvin = float(input_number.kelvin_temp)

    restored_count = _apply_settings_to_lights(
        lights,
        brightness_8bit=brightness_8bit,
        kelvin=kelvin,
        red_mode=False,
        only_if_on=True,
    )

    log.info(f"Red light mode deactivated - restored kelvin settings for {restored_count} lights")


@state_trigger("input_boolean.light_red_mode")
def handle_red_light_mode(value=None, old_value=None):
    """Toggle red lighting mode across the house when the helper changes."""
    task.unique("handle_red_light_mode")

    try:
        if value == 'on':
            log.info("Red light mode activated - turning on all lights in red")
            turn_on_off_all_lights(action='on', force_red=True)
        else:
            log.info("Red light mode disabled - restoring kelvin temperature")
            _restore_kelvin_settings()

    except Exception as e:
        log.error(f"Red light mode handling error: {e}")


@service
async def fade_light_off(entity_id: str, duration: float = 5):
    """
    Convenience service to fade a light off smoothly

    Args:
        entity_id: Light entity to fade off
        duration: Fade duration in seconds (default: 5)

    Usage:
        # Gentle 5-second fade
        pyscript.fade_light_off(entity_id='light.kitchen_light')

        # Quick 2-second fade
        pyscript.fade_light_off(entity_id='light.bedroom_light', duration=2)

        # Very slow fade for bedtime
        pyscript.fade_light_off(entity_id='light.bedroom_light', duration=30)
    """
    await smooth_transition(entity_id=entity_id, attribute="brightness", target=0, duration=duration)


@service
async def fade_all_lights_off(duration: float = 5):
    """
    Fade all lights off smoothly

    Args:
        duration: Fade duration in seconds (default: 5)

    Perfect for bedtime or leaving the house
    """
    task.unique("fade_all_lights_off")

    try:
        lights = state.names(domain="light")
        on_lights = [light_entity for light_entity in lights if state.get(light_entity) == 'on']

        if not on_lights:
            log.info("Fade all lights: No lights currently on")
            return

        log.info(f"Fading off {len(on_lights)} lights over {duration} seconds")

        # Start all fades simultaneously for synchronized effect
        for light_entity in on_lights:
            try:
                # Create concurrent fade tasks
                task.create(smooth_transition(entity_id=light_entity, attribute="brightness",
                                           target=0, duration=duration))
            except Exception as e:
                log.warning(f"Failed to start fade for {light_entity}: {e}")

        log.info(f"All lights fading to OFF over {duration} seconds")

    except Exception as e:
        log.error(f"Failed to fade all lights: {e}")
