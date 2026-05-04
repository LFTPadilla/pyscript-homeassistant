from datetime import datetime, time

def get_brightness_8bit_2(value: float = 0) -> int:
    """
    Convert brightness percentage to 8-bit integer value (0-255)
    Local version to avoid cross-module issues
    """
    try:
        brightness_ptc = float(input_number.brightness_lights) if value == 0 else value
        brightness_8bit = int(round((brightness_ptc * 255) / 100))
        brightness_8bit = max(0, min(255, brightness_8bit))
        return brightness_8bit
    except (ValueError, AttributeError):
        return 127  # 50% default brightness

# *************************** KITCHEN *****************************
@state_trigger("binary_sensor.kitchen_motion_sensor == 'on' or binary_sensor.espkitchen_kitchen_motion_pir_sensor == 'on'")
@time_active("range(sunset - 20min, sunrise + 20min)")
def motion_light_kitchen():
    """Kitchen motion-activated lighting with time-based light selection"""
    task.unique("motion_light_kitchen")

    try:
        # Skip in Away mode
        if input_select.house_mode in ["Away", "Sleep"]:
            log.debug("Kitchen motion: Skipped in Away mode")
            light.turn_off(entity_id='light.kitchen_light')
            # light.turn_off(entity_id='light.kitchen_strip_light')
            return

        current_time_str = datetime.now().strftime("%H:%M")
        # time_18_00 = datetime.strptime("18:00", "%H:%M").time()
        time_19_00 = datetime.strptime("19:00", "%H:%M").time()
        time_20_00 = datetime.strptime("20:00", "%H:%M").time()
        current_time = datetime.strptime(current_time_str, "%H:%M").time()
        brightness_8bit = get_brightness_8bit_2()

        # Select appropriate light based on time
        # if time_18_00 < current_time < time_20_00:
        #     light_name = 'light.kitchen_light'
        # else:
        #     light_name = 'light.kitchen_strip_light'

        light_name = 'light.kitchen_light'
        
        # Turn on light (red after 19:00 with schedule brightness)
        try:
            now_time = datetime.now().time()
            if now_time >= time_19_00 and input_boolean.light_red_mode == 'on':
                # Prefer red at night
                try:
                    # 19:00–19:59 => 20% (~51/255), 20:00+ => 1% (~3/255)
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, rgb_color=[255, 0, 0])
                    log.info(f"Kitchen motion: {light_name} ON RED at {red_brightness}/255")
                except Exception:
                    # Fallback to kelvin if light doesn't support RGB
                    kelvin = float(input_number.kelvin_temp)
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, color_temp_kelvin=kelvin)
                    log.info(f"Kitchen motion: {light_name} ON (fallback) at {red_brightness}/255, {kelvin}K")
            else:
                kelvin = float(input_number.kelvin_temp)
                light.turn_on(entity_id=light_name, brightness=brightness_8bit, color_temp_kelvin=kelvin)
                log.info(f"Kitchen motion: {light_name} ON at {brightness_8bit:.0f}/255, {kelvin}K")
        except Exception as e:
            log.error(f"Failed to turn on kitchen light {light_name}: {e}")
            return

        # Determine timeout based on energy saving mode
        try:
            time_turn_off = 60 if input_boolean.energy_saving == 'on' else 120
        except AttributeError:
            time_turn_off = 120  # Default timeout

        # Initial delay
        task.sleep(time_turn_off)

        # Stay on while motion detected
        while (binary_sensor.kitchen_motion_sensor == 'on' or
            binary_sensor.espkitchen_kitchen_motion_pir_sensor == 'on'):
            task.sleep(time_turn_off)

        # Turn off light
        try:
            light.turn_off(entity_id=light_name)
            log.info(f"Kitchen motion: {light_name} OFF - no motion detected")
        except Exception as e:
            log.error(f"Failed to turn off kitchen light {light_name}: {e}")

    except Exception as e:
        log.error(f"Kitchen motion lighting error: {e}")

# *************************** LIVING ROOM *****************************
@state_trigger("binary_sensor.espdesktop_pir_sensor == 'on' or binary_sensor.desktop_vibration_chair == 'on'")
@time_active("range(sunset - 20min, sunrise + 20min)")
def motion_light_night_living_room():
    """Living room motion-activated lighting"""
    task.unique("motion_light_night_living_room")

    try:
        light_name = "light.livingroom_light"
        
        # Skip in quiet modes
        if input_select.house_mode in ["Sleep", "Cine", "Away"]:
            light.turn_off(entity_id=light_name)
            log.debug(f"Living room motion: Skipped in {input_select.house_mode} mode")
            return


        # Turn on light (red after 19:00 with schedule brightness)
        try:
            brightness_8bit = get_brightness_8bit_2()
            time_19_00 = datetime.strptime("19:00", "%H:%M").time()
            time_20_00 = datetime.strptime("20:00", "%H:%M").time()
            now_time = datetime.now().time()
            if now_time >= time_19_00 and input_boolean.light_red_mode == 'on':
                try:
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, rgb_color=[255, 0, 0])
                    log.info(f"Living room motion: {light_name} ON RED at {red_brightness}/255")
                except Exception:
                    kelvin = float(input_number.kelvin_temp)
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, color_temp_kelvin=kelvin)
                    log.info(f"Living room motion: {light_name} ON (fallback) at {red_brightness}/255, {kelvin}K")
            else:
                kelvin = float(input_number.kelvin_temp)
                light.turn_on(entity_id=light_name, brightness=brightness_8bit, color_temp_kelvin=kelvin)
                log.info(f"Living room motion: {light_name} ON at {brightness_8bit:.0f}/255, {kelvin}K")
        except Exception as e:
            log.error(f"Failed to turn on living room light: {e}")
            return

        # Determine timeout based on energy saving mode
        try:
            time_turn_off = 240 if input_boolean.energy_saving == 'off' else 60
        except AttributeError:
            time_turn_off = 120  # Default timeout

        # Initial delay
        task.sleep(time_turn_off)

        # Stay on while motion detected or in Read mode
        while (binary_sensor.espdesktop_pir_sensor == 'on' or
            input_select.house_mode == 'Read' or input_select.house_mode == 'Meeting'):
            task.sleep(time_turn_off)

        # Additional delay before fade
        task.sleep(30)

        # Turn off light
        try:
            light.turn_off(entity_id=light_name)
            log.info(f"Living room motion: {light_name} OFF - no motion detected")
        except Exception as e:
            log.error(f"Failed to turn off living room light: {e}")

    except Exception as e:
        log.error(f"Living room motion lighting error: {e}")

# *************************** BEDROOM *****************************
@state_trigger("binary_sensor.bedroom_motion == 'on'")
@time_active("range(sunset - 20min, sunrise)")
def motion_light_night_bedroom():
    """Bedroom motion-activated lighting"""
    task.unique("motion_light_night_bedroom")

    try:
        light_name = "light.bedroom_light"
        
        # Skip in Sleep or Away mode
        if input_select.house_mode == "Reading":
            return 

        if input_select.house_mode in ["Sleep", "Away"]:
            log.debug(f"Bedroom motion: Skipped in {input_select.house_mode} mode")
            light.turn_off(entity_id=light_name)
            return


        # Turn on light (red after 19:00 with schedule brightness)
        try:
            brightness_8bit = get_brightness_8bit_2()
            time_19_00 = datetime.strptime("19:00", "%H:%M").time()
            time_20_00 = datetime.strptime("20:00", "%H:%M").time()
            now_time = datetime.now().time()
            if now_time >= time_19_00 and input_boolean.light_red_mode == 'on':
                try:
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, rgb_color=[255, 0, 0])
                    log.info(f"Bedroom motion: {light_name} ON RED at {red_brightness}/255")
                except Exception:
                    kelvin = float(input_number.kelvin_temp)
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, color_temp_kelvin=kelvin)
                    log.info(f"Bedroom motion: {light_name} ON (fallback) at {red_brightness}/255, {kelvin}K")
            else:
                kelvin = float(input_number.kelvin_temp)
                light.turn_on(entity_id=light_name, brightness=brightness_8bit, color_temp_kelvin=kelvin)
                log.info(f"Bedroom motion: {light_name} ON at {brightness_8bit:.0f}/255, {kelvin}K")
        except Exception as e:
            log.error(f"Failed to turn on bedroom light: {e}")
            light.turn_off(entity_id=light_name)
            return

        # Determine timeout based on energy saving mode
        try:
            time_turn_off = 10 if input_boolean.energy_saving == 'on' else 60
        except AttributeError:
            time_turn_off = 60  # Default timeout

        # Stay on while motion detected
        while binary_sensor.bedroom_motion == 'on':
            task.sleep(time_turn_off)

        # Turn off light
        try:
            light.turn_off(entity_id=light_name)
            log.info(f"Bedroom motion: {light_name} OFF - no motion detected")
        except Exception as e:
            log.error(f"Failed to turn off bedroom light: {e}")

    except Exception as e:
        light.turn_off(entity_id=light_name)
        log.error(f"Bedroom motion lighting error: {e}")

# *************************** CLOSET *****************************
@state_trigger("binary_sensor.closet_motion_sensor == 'on'")
# @time_active("range(sunset - 20min, sunrise + 15min)")
def motion_light_night_closet():
    """Closet motion-activated lighting"""
    task.unique("motion_light_night_closet")

    try:
        light_name = "light.closet_strip_light"

        # Skip in Sleep or Away mode (and turn off light)
        if input_select.house_mode in ["Sleep", "Away", "Reading"]:
            log.debug(f"Closet motion: Skipped in {input_select.house_mode} mode")
            light.turn_off(entity_id=light_name)
            return

        # Turn on light (red after 18:00 with schedule brightness)
        try:
            brightness_8bit = get_brightness_8bit_2()
            time_18_00 = datetime.strptime("18:00", "%H:%M").time()
            time_20_00 = datetime.strptime("20:00", "%H:%M").time()
            now_time = datetime.now().time()
            if now_time >= time_18_00 and input_boolean.light_red_mode == 'on':
                try:
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, rgb_color=[255, 0, 0])
                    log.info(f"Closet motion: {light_name} ON RED at {red_brightness}/255")
                except Exception:
                    kelvin = float(state.get("input_number.kelvin_temp"))
                    red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                    light.turn_on(entity_id=light_name, brightness=red_brightness, color_temp_kelvin=kelvin)
                    log.info(f"Closet motion: {light_name} ON (fallback) at {red_brightness}/255, {kelvin}K")
            else:
                kelvin = float(state.get("input_number.kelvin_temp"))
                switch.turn_on(entity_id='switch.fragance_plug') 
                light.turn_on(entity_id=light_name, brightness=brightness_8bit, color_temp_kelvin=kelvin)
                log.info(f"Closet motion: {light_name} ON at {brightness_8bit:.0f}/255, {kelvin}K")
        except Exception as e:
            log.error(f"Failed to turn on closet light: {e}")
            return

        # Determine timeout based on energy saving mode
        try:
            time_turn_off = 10 if input_boolean.energy_saving == 'on' else 30
        except AttributeError:
            time_turn_off = 30  # Default timeout

        # Stay on while motion detected
        while binary_sensor.closet_motion_sensor == 'on':
            task.sleep(time_turn_off)

        # Turn off light
        try:
            light.turn_off(entity_id=light_name)
            switch.turn_off(entity_id='switch.fragance_plug') 
            log.info(f"Closet motion: {light_name} OFF - no motion detected")
        except Exception as e:
            log.error(f"Failed to turn off closet light: {e}")

    except Exception as e:
        log.error(f"Closet motion lighting error: {e}")

# *************************** BATHROOM *****************************
@state_trigger("binary_sensor.bathroom_motion_sensor == 'on'")
# @time_active("range(sunset - 20min, sunrise)")
def motion_light_bathroom():
    """Bathroom motion-activated lighting"""
    task.unique("motion_light_bathroom")

    try:
        light_name = "light.bathroom_light"
        # Skip in Sleep or Away mode
        if input_select.house_mode in ['Sleep', 'Away']:
            log.debug(f"Bathroom motion: Skipped in {input_select.house_mode} mode")
            light.turn_off(entity_id=light_name)
            return

        # Turn on light
        try:
            brightness_8bit = get_brightness_8bit_2()

            # After 19:00, use red color with schedule brightness; otherwise warm white
            now_time = datetime.now().time()
            time_19_00 = datetime.strptime("19:00", "%H:%M").time()
            time_20_00 = datetime.strptime("20:00", "%H:%M").time()

            if now_time >= time_19_00 and input_boolean.light_red_mode == 'on':
                # Set to red after 19:00 with schedule brightness
                red_brightness = int(round(255 * (0.01 if now_time >= time_20_00 else 0.20)))
                light.turn_on(entity_id=light_name, brightness=red_brightness, rgb_color=[255, 0, 0])
                log.info(f"Bathroom motion: {light_name} ON RED at {red_brightness}/255")
            else:
                # Warmer temperature for bathroom (+300K)
                kelvin = float(input_number.kelvin_temp) + 300
                light.turn_on(
                    entity_id=light_name,
                    brightness=brightness_8bit,
                    color_temp_kelvin=kelvin,
                )
                log.info(
                    f"Bathroom motion: {light_name} ON at {brightness_8bit:.0f}/255, {kelvin}K"
                )
        except Exception as e:
            log.error(f"Failed to turn on bathroom light: {e}")
            return

        # Determine timeout based on energy saving mode and house mode
        try:
            time_turn_off = 30 if input_boolean.energy_saving == 'on' else 50

            # Shorter timeout for quiet modes
            if input_select.house_mode in ["Cine"]:
                time_turn_off -= 20

        except AttributeError:
            time_turn_off = 50  # Default timeout

        # Stay on while motion detected
        while binary_sensor.bathroom_motion_sensor == 'on':
            task.sleep(time_turn_off)

        # Turn off light
        try:
            light.turn_off(entity_id=light_name)
            log.info(f"Bathroom motion: {light_name} OFF - no motion detected")
        except Exception as e:
            log.error(f"Failed to turn off bathroom light: {e}")

    except Exception as e:
        log.error(f"Bathroom motion lighting error: {e}")
