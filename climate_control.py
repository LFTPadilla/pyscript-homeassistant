@state_trigger("float(sensor.bathroom_sensor_humidity) > float(input_number.bathroom_fan_humidity_activation) and input_boolean.bathroom_fan_dynamic_humidity == 'on'")
def smart_bathroom_humidity_control():
    """
    Intelligent bathroom exhaust fan control system based on humidity levels and usage patterns

    Features:
    - Hysteresis control: Turns on at threshold, turns off at threshold-5% to prevent oscillation
    - Post-shower detection: Extended runtime after rapid humidity increases
    - House mode integration: Adjusts timing and behavior based on current mode
    - Manual override support: Respects manual control via input_boolean
    - Progressive timing: Longer runtime for higher humidity levels
    - Robust error handling: Graceful degradation when sensors unavailable
    - Smart logging: Detailed humidity tracking and fan operation status

    Triggers:
    - Humidity exceeds configured threshold (input_number.bathroom_fan_humidity_activation)
    - Dynamic control enabled (input_boolean.bathroom_fan_dynamic_humidity)
    - Respects house modes (not active in Sleep/Cine for noise control)
    """
    task.unique("smart_bathroom_humidity_control")

    # Get current humidity and configuration
    try:
        current_humidity = float(sensor.bathroom_sensor_humidity)
        humidity_threshold = float(input_number.bathroom_fan_humidity_activation)
        house_mode = input_select.house_mode
    except (ValueError, AttributeError) as e:
        log.error(f"Bathroom humidity control: Sensor or config unavailable - {e}")
        return

    # Skip operation in quiet modes for noise control
    if house_mode in ["Sleep", "Cine"]:
        log.info(f"Bathroom fan: Skipping operation in {house_mode} mode for noise control")
        return

    # Check for manual override
    try:
        manual_override = input_boolean.bathroom_fan_manual_override == 'on'
        if manual_override:
            log.info("Bathroom fan: Manual override active, skipping automatic control")
            return
    except AttributeError:
        # Manual override not configured, continue with automatic control
        pass

    # Calculate hysteresis threshold (turn off 5% below turn-on threshold)
    humidity_off_threshold = humidity_threshold - 5

    # Detect post-shower conditions (rapid humidity increase)
    # This is a simplified detection - could be enhanced with historical data
    post_shower_detected = current_humidity > (humidity_threshold + 15)

    # Turn on the fan at full speed for humidity removal
    light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=100)
    log.info(f"Bathroom fan: ON (100%) - Humidity {current_humidity:.1f}% (threshold: {humidity_threshold:.1f}%)")

    # Determine base runtime based on house mode
    if house_mode == "Away":
        base_runtime = 600  # 10 minutes - thorough drying when away
        check_interval = 120  # Check every 2 minutes
    elif house_mode == "Night":
        base_runtime = 180  # 3 minutes - shorter for noise reduction
        check_interval = 60   # Check every minute
    else:  # Day, Friends, Reading, etc.
        base_runtime = 300  # 5 minutes - standard operation
        check_interval = 90   # Check every 1.5 minutes

    # Extend runtime for post-shower conditions
    if post_shower_detected:
        base_runtime *= 1.5
        log.info(f"Bathroom fan: Post-shower detected, extending runtime to {base_runtime/60:.1f} minutes")

    # Initial minimum runtime to prevent short cycling
    task.sleep(base_runtime)

    # Continue running while humidity remains high with progressive checking
    extended_runtime = 0
    max_extended_runtime = 1800  # Maximum 30 minutes total runtime

    while extended_runtime < max_extended_runtime:
        try:
            current_humidity = float(sensor.bathroom_sensor_humidity)

            # Check if humidity has dropped sufficiently (hysteresis)
            if current_humidity <= humidity_off_threshold:
                log.info(f"Bathroom fan: Humidity dropped to {current_humidity:.1f}% (off threshold: {humidity_off_threshold:.1f}%) - turning OFF")
                break

            # Check for manual override during operation
            try:
                if input_boolean.bathroom_fan_manual_override == 'on':
                    log.info("Bathroom fan: Manual override activated during operation")
                    break
            except AttributeError:
                pass

            # Progressive timeout - increase check interval for very high humidity
            if current_humidity > (humidity_threshold + 20):
                current_check_interval = check_interval * 2  # Slower checks for very high humidity
            else:
                current_check_interval = check_interval

            log.debug(f"Bathroom fan: Still running - Humidity {current_humidity:.1f}% (target: ≤{humidity_off_threshold:.1f}%)")
            task.sleep(current_check_interval)
            extended_runtime += current_check_interval

        except (ValueError, AttributeError):
            log.warning("Bathroom fan: Sensor became unavailable during operation, running additional 2 minutes")
            task.sleep(120)  # Run 2 more minutes if sensor fails
            break

    # Maximum runtime protection
    if extended_runtime >= max_extended_runtime:
        log.warning(f"Bathroom fan: Maximum runtime ({max_extended_runtime/60:.0f} minutes) reached - forcing OFF")

    # Restore fan to baseline speed based on bathroom light state
    if light.bathroom_light == 'on':
        brightness = 70
    else:
        brightness = 50
    light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=brightness)
    total_runtime = (base_runtime + extended_runtime) / 60
    log.info(f"Bathroom fan: Set to {brightness}% - Total runtime: {total_runtime:.1f} minutes")

@service
def bathroom_fan_manual_control(action: str, duration: int = 300):
    """
    Manual bathroom fan control service for immediate override

    Args:
        action: 'on' or 'off' to control the fan
        duration: Runtime in seconds when turning on (default: 5 minutes)
    """
    if action == 'on':
        light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=100)
        log.info(f"Bathroom fan: Manual 100% for {duration/60:.1f} minutes")
        task.sleep(duration)
        # Return to baseline based on bathroom light
        target = 70 if light.bathroom_light == 'on' else 50
        light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=target)
        log.info("Bathroom fan: Manual timer expired - restoring baseline")
    elif action == 'off':
        target = 70 if light.bathroom_light == 'on' else 50
        light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=target)
        log.info("Bathroom fan: Manual OFF - returning to baseline")
    else:
        log.error(f"Bathroom fan: Invalid action '{action}' - use 'on' or 'off'")


@state_trigger("light.bathroom_light == 'on'")
def bathroom_light_fan_boost():
    """Boost bathroom fan when the bathroom light turns on."""
    light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=70)


@state_trigger("light.bathroom_light == 'off'")
def bathroom_light_fan_baseline():
    """Return bathroom fan to baseline when the bathroom light turns off, except in quiet modes."""
    try:
        if input_select.house_mode in ["Sleep", "Cine"]:
            light.turn_off(entity_id="light.bathroom_fan_dimmer")
            log.info(f"Bathroom fan: keeping OFF in {input_select.house_mode} mode")
            return
    except Exception as e:
        log.warning(f"Bathroom fan baseline mode check failed: {e}")
    light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=50)

@state_trigger("float(sensor.espdesktop_pm_2_5_m) > 5")
def control_air_purifier_by_pm25():
    """
    Smart air purifier control based on PM2.5 particulate levels and house mode

    Controls an air filter fan to reduce airborne particulates:
    - Fan requires minimum 30% speed to start (hardware limitation)
    - Once started, stays at 30% minimum to avoid constant cycling
    - Speed adjusts based on PM2.5 levels within house mode limits
    - Cinema/Sleep modes: completely OFF for silence
    - Other modes: maintain air quality while respecting noise levels
    """
    task.unique("air_purifier_control")

    # Get current PM2.5 level
    try:
        pm25_level = float(sensor.espdesktop_pm_2_5_m)
    except (ValueError, AttributeError):
        log.error("PM2.5 sensor unavailable, skipping air purifier control")
        return

    # Get current house mode
    house_mode = input_select.house_mode

    # Determine max fan speed based on house mode (noise considerations)
    if house_mode in ["Sleep", "Cine"]:
        # Complete silence required
        max_fan_speed = 0
        target_speed = 0
        log.info(f"Air purifier: {house_mode} mode - turning OFF for silence")
    elif house_mode == "Night":
        # Quiet operation - max 50%
        max_fan_speed = 50
    elif house_mode == "Day":
        # Moderate noise acceptable - max 70%
        max_fan_speed = 70
    elif house_mode == "Away":
        # No noise concern - max 100%
        max_fan_speed = 100
    else:
        # Default for other modes
        max_fan_speed = 60

    # Calculate target speed based on PM2.5 levels (if not in silent modes)
    if max_fan_speed > 0:
        if pm25_level < 5:
            # Low particulates - maintain minimum 30% to avoid cycling
            target_speed = 30
        elif pm25_level < 15:
            # Low-medium particulates - 30-40% range
            target_speed = min(30 + (pm25_level - 5) * 1, max_fan_speed)
        elif pm25_level < 35:
            # Medium-high particulates - 40-60% range
            target_speed = min(40 + (pm25_level - 15) * 1, max_fan_speed)
        else:
            # High particulates - 60% to max speed
            target_speed = min(60 + (pm25_level - 35) * 0.5, max_fan_speed)

        # Ensure minimum 30% when running (hardware requirement)
        target_speed = max(30, min(target_speed, max_fan_speed))

    # Get current fan speed
    try:
        current_speed = float(state.getattr("fan.server_esp_fan_speed").get("percentage", 0))
    except (AttributeError, TypeError):
        # Fallback if can't read current speed
        current_speed = 0

    # Apply new speed if significantly different
    if abs(target_speed - current_speed) >= 5:
        if target_speed == 0:
            fan.turn_off(entity_id="fan.server_esp_fan_speed")
            log.info(f"Air purifier: PM2.5 at {pm25_level:.1f} μg/m³ - turning OFF ({house_mode} mode)")
        else:
            fan.set_percentage(entity_id="fan.server_esp_fan_speed", percentage=int(target_speed))
            log.info(f"Air purifier: PM2.5 at {pm25_level:.1f} μg/m³ - setting to {target_speed:.0f}% (max {max_fan_speed}% in {house_mode} mode)")

@service
def turn_on_off_all_fans(action='on'):
    """
    Control all ventilation fans with proper error handling
    
    Args:
        action: 'on' or 'off' to control fans
    
    Features:
    - Graceful handling of missing fan entities
    - Proper error logging for debugging
    - Bathroom fan dimmer controlled independently
    """
    fans_switch = ['fan_closet_plug', 'fan_stractor_kitchen']
    fan_light = 'light.bathroom_fan_dimmer'
    
    turned_on = []
    turned_off = []
    failed = []

    if action == 'on':
        for fan in fans_switch:
            entity_id = 'switch.' + fan
            try:
                switch.turn_on(entity_id=entity_id)
                turned_on.append(fan)
                log.debug(f"Fan control: Turned ON {entity_id}")
            except Exception as e:
                failed.append((fan, str(e)))
                log.warning(f"Fan control: Could not turn ON {entity_id} - {e}")
        
        # Turn on bathroom fan light to baseline
        try:
            light.turn_on(entity_id=fan_light, brightness_pct=50)
            log.debug(f"Fan control: Set bathroom fan to 50%")
        except Exception as e:
            log.warning(f"Fan control: Could not control {fan_light} - {e}")
        
        log.info(f"Fan control: ON complete - {len(turned_on)} fans activated, {len(failed)} failed")
        if failed:
            for fan, err in failed:
                log.error(f"  - {fan}: {err}")
                
    elif action == 'off':
        for fan in fans_switch:
            entity_id = 'switch.' + fan
            try:
                switch.turn_off(entity_id=entity_id)
                turned_off.append(fan)
                log.debug(f"Fan control: Turned OFF {entity_id}")
            except Exception as e:
                failed.append((fan, str(e)))
                log.warning(f"Fan control: Could not turn OFF {entity_id} - {e}")
        
        # Set bathroom fan light to baseline
        try:
            light.turn_off(entity_id=fan_light)
            log.debug(f"Fan control: Turned OFF bathroom fan light")
        except Exception as e:
            log.warning(f"Fan control: Could not control {fan_light} - {e}")
        
        log.info(f"Fan control: OFF complete - {len(turned_off)} fans deactivated, {len(failed)} failed")
        if failed:
            for fan, err in failed:
                log.error(f"  - {fan}: {err}")
    else:
        log.error(f"Fan control: Invalid action '{action}' - use 'on' or 'off'")

# ===================== DEHUMIDIFIER CONTROL =====================

# @state_trigger("sensor.espkitchen_kitchen_room_humidity")
def dehumidifier_humidity_control():
    """
    Basic control for a dehumidifier plug based on room humidity.

    - Turns **on** when humidity rises above 75%
    - Turns **off** when humidity falls below 70%
    """
    try:
        humidity = float(sensor.espkitchen_kitchen_room_humidity)
    except (ValueError, TypeError, AttributeError):
        log.error("Dehumidifier: humidity sensor unavailable")
        return

    if humidity > 75 and switch.deshumidifier_plug != 'on':
        switch.turn_on(entity_id="switch.deshumidifier_plug")
        log.info(f"Dehumidifier: ON - Humidity {humidity:.1f}% (>75%)")
        pyscript.notify_coco(
            message=f"💧 Kitchen humidity high ({humidity:.0f}%). Dehumidifier turned ON.",
            title="Humidity Alert",
        )
    elif humidity < 70 and switch.deshumidifier_plug != 'off':
        switch.turn_off(entity_id="switch.deshumidifier_plug")
        log.info(f"Dehumidifier: OFF - Humidity {humidity:.1f}% (<70%)")

# ===================== BED COOLING PUMP CONTROL =====================
from datetime import datetime, time as dt_time
from typing import Optional

# Configuration: minimal hysteresis and time window
BED_TEMP_ON_C = 24.5   # turn ON at or above this temperature
BED_TEMP_OFF_C = 23.5  # turn OFF at or below this temperature
NIGHT_START = dt_time(22, 30)  # 22:30
NIGHT_END = dt_time(3, 0)      # 03:00

def _is_night_window(now: Optional[datetime] = None) -> bool:
    """Return True if current time is within the night window [22:30 → 03:00)."""
    now = now or datetime.now()
    t = now.time()
    return t >= NIGHT_START or t < NIGHT_END

def _get_bed_temp() -> Optional[float]:
    try:
        return float(sensor.t_h_sensor_temperature)
    except (ValueError, TypeError, AttributeError):
        return None

def _ensure_pump_state(desired_on: bool, reason: str = ""):
    entity = "switch.pump_bed_plug"
    current_on = (state.get(entity) == 'on')
    if desired_on and not current_on:
        switch.turn_on(entity_id=entity)
        if reason:
            log.info(f"Bed pump: ON ({reason})")
    elif (not desired_on) and current_on:
        switch.turn_off(entity_id=entity)
        if reason:
            log.info(f"Bed pump: OFF ({reason})")

@state_trigger(f"float(sensor.t_h_sensor_temperature) >= {BED_TEMP_ON_C}")
def bed_pump_on_when_hot_at_night():
    """
    Turn ON the bed cooling pump when bedroom temperature is at/above BED_TEMP_ON_C
    and current time is within the night window. Minimal, robust hysteresis control.
    """
    task.unique("bed_pump_on_when_hot_at_night")
    temp = _get_bed_temp()
    if temp is None:
        log.warning("Bed pump: temperature unavailable; skipping ON evaluation")
        return

    if _is_night_window() and temp >= BED_TEMP_ON_C:
        _ensure_pump_state(True, reason=f"{temp:.1f}°C ≥ {BED_TEMP_ON_C}°C and in night window")

@state_trigger(f"float(sensor.t_h_sensor_temperature) <= {BED_TEMP_OFF_C}")
def bed_pump_off_when_cool():
    """Turn OFF the bed cooling pump when temperature drops to/under BED_TEMP_OFF_C."""
    task.unique("bed_pump_off_when_cool")
    temp = _get_bed_temp()
    if temp is None:
        log.warning("Bed pump: temperature unavailable; skipping OFF evaluation")
        return
    if temp <= BED_TEMP_OFF_C:
        _ensure_pump_state(False, reason=f"{temp:.1f}°C ≤ {BED_TEMP_OFF_C}°C (hysteresis off)")

@time_trigger("cron(30 22 * * *)")
def bed_pump_check_at_night_start():
    """At night start, turn ON if it's already hot enough."""
    temp = _get_bed_temp()
    if temp is None:
        return
    if temp >= BED_TEMP_ON_C:
        _ensure_pump_state(True, reason=f"night start and {temp:.1f}°C ≥ {BED_TEMP_ON_C}°C")

@time_trigger("cron(0 7 * * *)")
def bed_pump_force_off_at_night_end():
    """At night end, always ensure the pump is OFF."""
    _ensure_pump_state(False, reason="night window ended")
