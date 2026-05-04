@state_trigger("vacuum.robot")
def vacuum_state_changed():
    """
    Control desktop table position and fan speed based on vacuum state.
    """
    vacuum_entity = "vacuum.robot"
    house_mode = state.get("input_select.house_mode")
    vacuum_state = state.get(vacuum_entity)
    
    log.info(f"Vacuum state changed to: {vacuum_state}")

    # When vacuum starts cleaning, raise the table to position 2 (Standing)
    # This prevents the robot from getting stuck or hitting the chair/cables
    if vacuum_state == "cleaning":
        log.info("Vacuum is cleaning. Raising desktop table to position 2.")
        switch.turn_on(entity_id="switch.desktop_table_desktop_table_position_2_stand")
        
        # Set fan speed based on house mode
        if house_mode == "Away":
            vacuum.set_fan_speed(entity_id=vacuum_entity, fan_speed="normal")
            log.info("House empty - setting vacuum to normal speed")
        else:
            vacuum.set_fan_speed(entity_id=vacuum_entity, fan_speed="gentle")
            log.info("Someone home - setting vacuum to gentle speed")

    # Optional: Lower table when returning to dock? 
    # For now, we only fulfill the "raise on start" request.

@state_trigger("vacuum.robot.battery_level")
def manage_vacuum_battery():
    """Smart battery management for vacuum"""
    task.unique("manage_vacuum_battery")
    
    try:
        battery_level = float(state.get("vacuum.robot.battery_level"))
    except (TypeError, ValueError):
        return

    vacuum_state = state.get("vacuum.robot")

    # If battery is low while cleaning, reduce speed
    if battery_level < 40 and vacuum_state == "cleaning":
        vacuum.set_fan_speed(entity_id="vacuum.robot", fan_speed="gentle")
        log.info(f"Battery low ({battery_level}%) - reducing fan speed")

    # If battery critical, return to base
    if battery_level < 15 and vacuum_state == "cleaning":
        vacuum.return_to_base(entity_id="vacuum.robot")
        log.info(f"Battery critical ({battery_level}%) - returning to dock")
