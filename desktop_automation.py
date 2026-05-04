from datetime import datetime, time




@state_trigger("binary_sensor.desktop_vibration_chair == 'on'") # and sensor.pchp_pchp_activewindow != 'unavailable'")
def vibration_sensor_chair_ocupancy():
    """Turn on bedroom light for 5 minutes when there is motion and it's dark"""
    log.info(f"triggered; Chair ocuppancy")
    task.unique("vibration_sensor_chair_ocupancy")
    binary_sensor.vibration_sensor_vibration = 'off'

    if sensor.hp_nixos_power == 'unavailable':
        log.warning("hp_nixos_power sensor unavailable; skipping desk power on")
        return

    if input_select.house_mode not in ["Sleep", "Cine", "Away"]:
        if input_boolean.fans_desk_big == 'on':
            switch.turn_on(entity_id='switch.desktop_strip_plug_socket_1')
        else:
            switch.turn_off(entity_id='switch.desktop_strip_plug_socket_1')

        
        switch.turn_off(entity_id='switch.desktop_strip_plug_socket_5')
        switch.turn_on(entity_id='switch.desktop_strip_plug_socket_2')
        switch.turn_on(entity_id='switch.desktop_strip_plug_socket_3')
        switch.turn_on(entity_id='switch.desktop_strip_plug_socket_4')

        current_time_str = datetime.now().strftime("%H:%M")
        time_18_00 = datetime.strptime("18:00", "%H:%M").time()
        time_23_00 = datetime.strptime("23:00", "%H:%M").time()
        current_time = datetime.strptime(current_time_str, "%H:%M").time()
        if time_18_00 < current_time < time_23_00:
            brightness_8bit = pyscript.get_brightness_8bit()
            light.turn_on(entity_id="light.living_room_light", brightness=brightness_8bit, kelvin=float(input_number.kelvin_temp))

    # task.sleep(1000)
    # switch.turn_off(enti ty_id='switch.desktop_strip_plug_socket_1')
    # switch.turn_off(entity_id='switch.desktop_strip_plug_socket_2')
    # switch.turn_off(entity_id='switch.desktop_strip_plug_socket_3')
    # switch.turn_off(entity_id='switch.desktop_strip_plug_socket_4')
    # switch.turn_off(entity_id='switch.desktop_strip_plug_socket_5')





# @state_trigger("sensor.hp_nixos_load_avg")
# def load_hp_avg():
#     load = float(sensor.hp_nixos_load_avg)

#     # Scale the load (0-25) to fan speed (20-80)
#     # Calculate percentage of maximum load
#     load_percentage = min(load / 25.0, 1.0)

#     # Map the load percentage to fan speed range (20-80)
#     fan_speed = 20 + (load_percentage * 60)

#     # Round to nearest integer
#     fan_speed = round(fan_speed)

#     # Set the fan speed
#     service.call("fan", "set_percentage", entity_id="fan.fan_2_fan_speed", percentage=fan_speed)

#     # Log the change
#     logger.info(f"Load: {load:.2f}, Setting fan speed to {fan_speed}%")

# @state_trigger("sensor.pchp_pchp_activewindow == 'unavailable'")
# def pc_hp_shutdown():
#     task.unique("pc_hp_shutdown")
#     switch.turn_off(entity_id='switch.desktop_strip_plug_socket_1')
#     switch.turn_off(entity_id='switch.desktop_strip_plug_socket_2')
#     switch.turn_off(entity_id='switch.desktop_strip_plug_socket_3')
#     switch.turn_off(entity_id='switch.desktop_strip_plug_socket_4')
#     switch.turn_off(entity_id='switch.desktop_strip_plug_socket_5')
