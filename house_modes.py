from datetime import datetime, timedelta, time

@state_trigger("input_select.house_mode")
def changed_house_mode(value=None, old_value=None):
    task.unique("changed_house_mode")
    log.warning(f"changed_house_mode started, mode: {input_select.house_mode}")

    # Remember mode before Away (UI dropdown or automations, not only the away button)
    if input_select.house_mode == "Away" and old_value not in (None, "Away"):
        input_text.previous_house_mode = old_value

    # Sleep: all lights/fans off before any TTS or cover actions (instant dark)
    if input_select.house_mode == 'Sleep':
        input_boolean.light_red_mode = 'off'  # Clear red mode so lights properly turn off
        pyscript.turn_on_off_all_lights(action='off')
        pyscript.turn_on_off_all_fans(action='off')

        ALL_LIGHTS = [
            "light.bedroom_light", "light.kitchen_light", "light.livingroom_light",
            "light.bathroom_light", "light.closet_strip_light"
        ]
        for _ in range(3):  # 3 retries
            for lid in ALL_LIGHTS:
                try:
                    light.turn_off(entity_id=lid)
                except Exception:
                    pass
            task.sleep(0.5)

        light.turn_off(entity_id='light.bathroom_fan_dimmer')
        switch.turn_off(entity_id='switch.desktop_strip_plug_socket_3')
        switch.turn_off(entity_id='switch.desktop_strip_plug_socket_5')
        switch.turn_off(entity_id='switch.fan_stractor_kitchen')

    if input_select.house_mode in ["Away", "Sleep"]:
        # Car window security audit
        car_windows_state = state.get("input_boolean.car_windows_closed")
        if car_windows_state == 'off' or car_windows_state is None:
            mode_msg = "going to sleep" if input_select.house_mode == 'Sleep' else "leaving the house"
            try:
                pyscript.speak_openai(
                    msg=f'Felipe, the car windows are still open. Please close them before {mode_msg}.',
                    lang='en',
                    force=True
                )
            except Exception as e:
                log.warning(f"speak_openai failed: {e}")

        try:
            val = state.get("binary_sensor.livingroom_door_sensor")
            if val == 'on':
                pyscript.speak_openai(msg='La ventana está abierta', lang='es', force=True)
            else:
                cover.close_cover(entity_id="cover.curtain_living_room_curtain")
        except Exception as e:
            log.warning(f"livingroom_door_sensor check failed: {e}")

    log.warning(f"changed_house_mode pre-Sleep/Away check completed")

    if input_select.house_mode == 'Sleep':
        switch.turn_off(entity_id='switch.switch_bedroom_cameras_socket_1')
        media_player.media_stop(entity_id="media_player.google_speaker")
        switch.turn_off(entity_id="switch.pump_cat_switch")
        input_boolean.morning_routine_executed = 'off'


    if input_select.house_mode == 'Away':
        log.warning("Away mode logic started")
        # So smart_arrival works even when Away is set from the UI (not only the away button)
        try:
            input_datetime.away_mode_time_activated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            log.warning(f"Away mode: could not set away_mode_time_activated: {e}")
        switch.turn_on(entity_id='switch.switch_bedroom_cameras_socket_1')
        log.warning("Turned on bedroom cameras")
        media_player.media_stop(entity_id="media_player.google_speaker")
        # Desk to position 2 — try both Zigbee and ESPHome entities
        try:
            switch.turn_off(entity_id='switch.desktop_table_desktop_table_position_2_stand')
        except Exception as e:
            log.warning(f"Error desktop zigbee: {e}")
            
        try:
            switch.turn_off(entity_id='switch.espdesktop_desktop_table_2_position_standup')
        except Exception as e:
            log.warning(f"Error desktop esp: {e}")
            
        switch.turn_off(entity_id="switch.robot_do_not_disturb")
        pyscript.turn_on_off_all_lights(action='on')
        pyscript.turn_on_off_all_fans(action='on')
        log.warning("Lights and fans on, starting vacuum")
        
        # Start vacuum immediately — no delay to avoid task.unique cancellation
        try:
            vacuum.set_fan_speed(entity_id="vacuum.robot", fan_speed="gentle")
            task.sleep(2)
            vacuum.start(entity_id="vacuum.robot")
            log.warning("Vacuum started")
        except Exception as e:
            log.warning(f"Vacuum error: {e}")
            
        # Lights off after ~5 min — best effort (may be cancelled by task.unique)
        task.sleep(283)
        pyscript.turn_on_off_all_lights(action='off')

    if input_select.house_mode == 'Cine':
        switch.turn_on(entity_id="switch.kitchen_filter_plug")
        cover.close_cover(entity_id="cover.curtain_living_room_curtain")
        input_number.kelvin_temp = 2300
        task.sleep(1)
        input_number.brightness_lights = 1
        task.sleep(1)
        switch.turn_off(entity_id='switch.desktop_table_desktop_table_position_3_top')
        media_player.media_stop(entity_id="media_player.google_speaker")
        pyscript.turn_on_off_all_fans(action='off')
        switch.turn_off(entity_id="switch.pump_cat_switch")
        task.sleep(3)
        pyscript.turn_on_off_all_lights(action='off')

    if input_select.house_mode == 'Reading':
        pyscript.turn_on_off_all_lights(action='off')
        task.sleep(1)
        light.turn_on(entity_id="light.living_room_light_light", brightness=10, color_temp_kelvin=2300)

    if input_select.house_mode == 'Day':
        switch.turn_on(entity_id='switch.switch_bedroom_cameras_socket_1')
        switch.turn_on(entity_id="switch.refrigerator_plug")
        # switch.turn_on(entity_id="switch.monitor_plug")
        switch.turn_on(entity_id="switch.pump_cat_switch")
        # switch.turn_on(entity_id='switch.fan_stractor_kitchen')
        switch.turn_on(entity_id="switch.ups_switch")
        light.turn_on(entity_id='light.bathroom_fan_dimmer', brightness=172) 
        input_number.brightness_lights = 50
        input_number.kelvin_temp = 4000

        # brightness_8bit = pyscript.get_brightness_8bit()
        # current_time_str = datetime.now().strftime("%H:%M")
        # time_5_00 = datetime.strptime("5:00", "%H:%M").time()
        # time_6_15 = datetime.strptime("6:15", "%H:%M").time()
        # current_time = datetime.strptime(current_time_str, "%H:%M").time()

        # if time_5_00 < current_time < time_6_15:
        #     smooth_transition(3800, 2400, 7200, 10, update_color_temp, easing_out_quad)
        # else:

    if input_select.house_mode == 'Night':
        # br = float(input_number.brightness_lights)
        # smooth_transition(float(input_number.brightness_lights), 10, 7200, 10, update_brightness, easing_out_quad)#     input_number.brightness_lights = 10
        # smooth_transition(3800, 2400, 7200, 10, update_color_temp, easing_out_quad)
        input_number.brightness_lights = 10
        input_number.kelvin_temp = 2800

        # pyscript.turn_on_off_all_lights(action='on')

    if input_select.house_mode == 'Friends':
        input_number.brightness_lights = 70
        input_number.kelvin_temp = 4400
        pyscript.turn_on_off_all_lights(action='on')
        cover.open_cover(entity_id="cover.curtain_living_room_curtain")
        switch.turn_on(entity_id='switch.fragance_plug')
        task.sleep(120)
        switch.turn_off(entity_id='switch.fragance_plug')

    if input_select.house_mode == 'Meditation':
        pyscript.turn_on_off_all_lights(action='off')

    if input_select.house_mode == 'Hug':
        switch.turn_off(entity_id='switch.switch_bedroom_cameras_socket_1')
        cover.close_cover(entity_id="cover.curtain_living_room_curtain")
        input_number.brightness_lights = 1
        input_number.kelvin_temp = 2200

@state_trigger("input_boolean.energy_saving")
def changed_state_energy_saving():
    if input_boolean.energy_saving == 'on':
        if input_select.house_mode in [ 'Day', 'Friends']:
            input_number.brightness = 30
        else:
            input_number.brightness = 1
    else:
        input_number.brightness = 60

@state_trigger("input_boolean.away_mode == 'on'")
def away_button_triggered():
    input_boolean.away_mode = 'off'
    current_time = datetime.now()
    if input_select.house_mode == "Away":
        input_select.house_mode = input_text.previous_house_mode
        switch.turn_off(entity_id='switch.fragance_plug')
        vacuum.set_fan_speed(entity_id="vacuum.robot", fan_speed="gentle")
        pyscript.turn_on_off_all_fans(action='off')
    else:
        input_text.previous_house_mode = input_select.house_mode
        input_select.house_mode = "Away"
        input_datetime.away_mode_time_activated = current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # === AWAY MODE ACTIONS ===
        # Turn on bedroom cameras
        switch.turn_on(entity_id='switch.switch_bedroom_cameras_socket_1')
        # Stop any playing media
        media_player.media_stop(entity_id="media_player.google_speaker")
        # Put desk down (both Zigbee and ESPHome entities)
        switch.turn_off(entity_id='switch.desktop_table_desktop_table_position_2_stand')
        switch.turn_off(entity_id='switch.espdesktop_desktop_table_2_position_standup')
        # Disable robot DND
        switch.turn_off(entity_id="switch.robot_do_not_disturb")
        # Turn on all lights and fans
        pyscript.turn_on_off_all_lights(action='on')
        pyscript.turn_on_off_all_fans(action='on')
        
        # Start vacuum
        try:
            vacuum.set_fan_speed(entity_id="vacuum.robot", fan_speed="gentle")
            task.sleep(2)
            vacuum.start(entity_id="vacuum.robot")
        except Exception as e:
            log.warning(f"Vacuum start failed: {e}")
        
        # Schedule lights off after ~5 min
        task.sleep(283)
        pyscript.turn_on_off_all_lights(action='off')
        # ========================
        
        pyscript.notify_coco(
            message="🏃 Away mode activated. Cameras ON, vacuum started, fans running.",
            title="Away Mode",
            speak=True,
        )
        # If its after 6PM turn on the lights
        six_pm = time(18, 0)
        if current_time.time() >= six_pm:
            light.turn_on(entity_id="light.kitchen_light")
            light.turn_on(entity_id="light.livingroom_light")

@service
def switch_to_previous_house_mode():
    """
    Service to switch house_mode to the previously stored mode
    Reads from input_text.previous_house_mode and sets input_select.house_mode
    """
    previous_mode = input_text.previous_house_mode

    if previous_mode:
        input_select.select_option(
            entity_id='input_select.house_mode',
            option=previous_mode
        )
        log.info(f"Switched house mode to previous mode: {previous_mode}")
    else:
        log.warning("No previous house mode found")

# Restore last mode on startup
@time_trigger("startup")
def restore_last_mode():
    """Restore the last active mode after a system restart"""
    try:
        last_mode = input_text.previous_house_mode
        if last_mode:
            log.info(f"Restoring last mode: {last_mode}")
            input_select.house_mode = last_mode
            # change_house_mode('Sleep', last_mode)
    except Exception as e:
        log.error(f"Failed to restore last mode: {str(e)}")

@state_trigger("input_boolean.cine_mode == 'on'")
def cine_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.cine_mode = 'off'
    input_select.house_mode = 'Cine'

@state_trigger("input_boolean.day_mode == 'on'")
def day_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.day_mode = 'off'
    input_select.house_mode = 'Day'

@state_trigger("input_boolean.friends_mode == 'on'")
def friends_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.friends_mode = 'off'
    input_select.house_mode = 'Friends'

@state_trigger("input_boolean.meditation_mode == 'on'")
def meditation_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.meditation_mode = 'off'
    input_select.house_mode = 'Meditation'

@state_trigger("input_boolean.hug_mode == 'on'")
def hug_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.hug_mode = 'off'
    input_select.house_mode = 'Hug'

@state_trigger("input_boolean.night_mode == 'on'")
def night_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.night_mode = 'off'
    input_select.house_mode = 'Night'

@state_trigger("input_boolean.reading_mode == 'on'")
def reading_button_triggered():
    input_text.previous_house_mode = input_select.house_mode
    input_boolean.reading_mode = 'off'
    input_select.house_mode = 'Reading'

@state_trigger("input_boolean.sleep_mode == 'on'")
def sleep_button_triggered():
    previous_mode = input_select.house_mode
    input_text.previous_house_mode = previous_mode
    input_boolean.sleep_mode = 'off'

    # If already in Sleep, re-run the shutdown actions explicitly.
    # Otherwise, setting Sleep -> Sleep won't retrigger changed_house_mode.
    if previous_mode == 'Sleep':
        log.warning("sleep_button_triggered: already in Sleep, forcing lights/fans shutdown again")
        input_boolean.light_red_mode = 'off'
        pyscript.turn_on_off_all_lights(action='off')
        pyscript.turn_on_off_all_fans(action='off')

        ALL_LIGHTS = [
            "light.bedroom_light", "light.kitchen_light", "light.livingroom_light",
            "light.bathroom_light", "light.closet_strip_light", "light.bathroom_fan_dimmer"
        ]
        for _ in range(3):
            for lid in ALL_LIGHTS:
                try:
                    light.turn_off(entity_id=lid)
                except Exception as e:
                    log.warning(f"sleep_button_triggered force-off failed for {lid}: {e}")
            task.sleep(0.5)
        return

    input_select.house_mode = 'Sleep'

@state_trigger("binary_sensor.main_door_sensor == 'on'")
def smart_arrival_detection():
    """
    Smart arrival detection: return to previous house mode when opening main door.
    Triggers only if current mode is 'Away' and it has been active for more than 5 minutes.
    Runs the same fan/vacuum/fragrance cleanup as toggling the away button off, then restores mode.
    Provides a personalized greeting on the Google Speaker.
    """
    task.unique("smart_arrival_detection")

    try:
        # 1. Verify if the house mode is 'Away'
        current_mode = state.get("input_select.house_mode")
        if current_mode != "Away":
            log.debug("Smart arrival: Not in Away mode, skipping.")
            return

        # 2. Verify if it has been more than 5 minutes since Away mode was activated
        try:
            away_time_str = state.get("input_datetime.away_mode_time_activated")
            if not away_time_str:
                log.warning("Smart arrival: away_mode_time_activated is empty.")
                return

            away_time = datetime.strptime(away_time_str, '%Y-%m-%d %H:%M:%S')
            time_diff = datetime.now() - away_time

            if time_diff < timedelta(minutes=5):
                log.info(f"Smart arrival: Door opened, but only {time_diff.total_seconds()/60:.1f} min since Away mode. Skipping.")
                return
        except Exception as e:
            log.error(f"Smart arrival: Error checking away time: {e}")
            return

        # 3. Determine the personalized welcome message
        # Check person states (home/not_home)
        felipe_status = state.get("person.felipe")
        valentina_status = state.get("person.valentina")

        if felipe_status == "home" and valentina_status != "home":
            welcome_msg = "Welcome back, Felipe!"
        elif valentina_status == "home" and felipe_status != "home":
            welcome_msg = "Welcome back, Valentina!"
        else:
            welcome_msg = "Welcome home!"

        # 4. Give the message via Google Speaker
        try:
            pyscript.speak_openai(
                msg=welcome_msg, 
                lang='en', 
                volume=0.6, 
                force=True # Force because we are still in 'Away' mode policy (TTS=False)
            )
        except Exception as e:
            log.error(f"Smart arrival: Failed to speak welcome message: {e}")

        # 5. Same cleanup as away_button when leaving Away (fans, vacuum profile, fragrance)
        try:
            switch.turn_off(entity_id='switch.fragance_plug')
        except Exception as e:
            log.warning(f"Smart arrival: fragance_plug off failed: {e}")
        try:
            vacuum.set_fan_speed(entity_id="vacuum.robot", fan_speed="gentle")
        except Exception as e:
            log.warning(f"Smart arrival: vacuum fan speed failed: {e}")
        try:
            pyscript.turn_on_off_all_fans(action='off')
        except Exception as e:
            log.warning(f"Smart arrival: turn_on_off_all_fans failed: {e}")

        # 6. Restore previous mode (or default to Day)
        previous_mode = state.get("input_text.previous_house_mode") or "Day"
        input_select.house_mode = previous_mode
        log.info(f"Smart arrival: Restored house mode to {previous_mode}. Greeting: {welcome_msg}")

        # 7. Send system notification to Felipe's phone by default
        pyscript.notify_coco(
            message=f"{welcome_msg} House mode restored to {previous_mode}.",
            title="Smart Arrival",
            target="felipe_phone"
        )

    except Exception as e:
        log.error(f"Smart arrival detection error: {e}")

