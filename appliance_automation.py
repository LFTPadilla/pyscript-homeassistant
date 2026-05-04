
# state_trigger("input_select.washer_machine_status")
"""
def washer_machine_changed_state():
    status = input_select.washer_machine_status
    log.info(f"Washer Machine chaged status {status}")
    if status == 'Running':
        input_boolean.take_out_landury = 'off'

        if input_boolean.hot_washer_machine == 'on':
            switch.turn_off(entity_id="switch.water_heater")
            task.sleep(90)
            switch.turn_on(entity_id="switch.water_heater")
        elif input_boolean.hot_washer_machine == 'off':
            switch.turn_on(entity_id="switch.water_heater")
    elif status == 'Idle':
        count = 0
        while input_boolean.take_out_laundry == 'off':
            speak("Se finalizó el lavado", "es")
            task.sleep(500)

        switch.turn_on(entity_id="switch.humidifier_plug")
        task.sleep(2000)
        switch.turn_off(entity_id="switch.humidifier_plug")

@state_trigger("binary_sensor.door_washer_machine == 'on' and input_boolean.take_out_laundry == 'off'")
def laundry_out():
    input_boolean.take_out_laundry = 'on'
"""
# @state_trigger("sensor.washer_machine_power")
# def washer_machine_state_by_power():
#     task.unique("washer_machine_status_by_power")
#     power = float(sensor.washer_machine_power)
#     log.info(f"Washer Machine chaged status {sensor.washer_machine_power}")
#     if power > 0 and power <= 5 and input_select.washer_machine_status == 'Off':
#         input_select.washer_machine_status = 'On'
#     if power > 0 and power <= 5 and input_select.washer_machine_status == 'Running':
#         input_select.washer_machine_status = 'Clean Required'
#         speak("La lavadora require lavado de tambor","es")
#     elif power > 5 and input_select.washer_machine_status != 'Running':
#         input_select.washer_machine_status = 'Running'
#     elif power == 0 and input_select.washer_machine_status == 'Running':
#         input_select.washer_machine_status = 'Off'
#         switch.turn_off(entity_id="switch.washer_machine_plug")
