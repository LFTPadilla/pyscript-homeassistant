@event_trigger("zha_event")
def handle_knob_events(device_ieee=None, command=None, args=None, **kwargs):
    """
    Knob controller that toggles between brightness and temperature adjustment modes
    """
    # Only process events from our specific remote
    if device_ieee != "a4:c1:38:a5:e1:3b:c0:23":
        return
    
    # Debug log
    # log.info(f"Knob event received: command={command}, args={args}")
    
    # Handle toggle to switch between brightness and temperature modes
    if command == "toggle":
        # log.info("Toggle between brightness and temperature modes")
        
        # Get current mode
        current_mode = state.get("input_boolean.knob_mode_brightness_temp")
        
        # Toggle the mode
        if current_mode == "on":
            # "on" means brightness mode, switch to temperature mode
            input_boolean.turn_off(entity_id="input_boolean.knob_mode_brightness_temp")
            task.sleep(0.1)  # Small delay to ensure state is updated
            # Notify the user about mode change
            persistent_notification.create(
                message="Knob set to Temperature Adjustment Mode",
                title="Mode Changed",
                notification_id="knob_mode"
            )
        else:
            # "off" means temperature mode, switch to brightness mode
            input_boolean.turn_on(entity_id="input_boolean.knob_mode_brightness_temp")
            task.sleep(0.1)  # Small delay to ensure state is updated
            # Notify the user about mode change
            persistent_notification.create(
                message="Knob set to Brightness Adjustment Mode",
                title="Mode Changed",
                notification_id="knob_mode"
            )
    
    # Handle step events for brightness or temperature adjustment
    elif command == "step" and isinstance(args, list) and len(args) >= 2:
        # Extract step mode from position 0
        step_mode = args[0]
        # Extract step size from position 1 and scale it
        raw_step_size = int(args[1])
        
        # Different scaling for brightness vs temperature
        brightness_step = max(1, raw_step_size // 4)
        temp_step = max(50, raw_step_size * 5)  # Larger steps for kelvin temp
        
        # Check current mode (on = brightness mode, off = temperature mode)
        is_brightness_mode = state.get("input_boolean.knob_mode_brightness_temp") == "on"
        
        # Log what we're doing
        mode_name = "Brightness" if is_brightness_mode else "Temperature"
        # log.info(f"Adjusting {mode_name}, Step mode: {step_mode}, Raw step: {raw_step_size}")
        
        # Process based on current mode and step direction
        if hasattr(step_mode, "value"):
            # UP direction
            if step_mode.value == 0:
                if is_brightness_mode:
                    # BRIGHTNESS UP
                    try:
                        current = float(state.get("input_number.brightness_lights"))
                        new_value = min(max(current + brightness_step, 1), 100)
                        input_number.set_value(entity_id="input_number.brightness_lights", value=new_value)
                        log.info(f"Brightness set to {new_value}")
                    except Exception as e:
                        log.error(f"Error adjusting brightness: {e}")
                else:
                    # TEMPERATURE UP
                    try:
                        current = float(state.get("input_number.kelvin_temp"))
                        new_value = min(max(current + temp_step, 2000), 6400)
                        input_number.set_value(entity_id="input_number.kelvin_temp", value=new_value)
                        log.info(f"Temperature set to {new_value}K")
                    except Exception as e:
                        log.error(f"Error adjusting temperature: {e}")
            
            # DOWN direction
            elif step_mode.value == 1:
                if is_brightness_mode:
                    # BRIGHTNESS DOWN
                    try:
                        current = float(state.get("input_number.brightness_lights"))
                        new_value = min(max(current - brightness_step, 1), 100)
                        input_number.set_value(entity_id="input_number.brightness_lights", value=new_value)
                        log.info(f"Brightness set to {new_value}")
                    except Exception as e:
                        log.error(f"Error adjusting brightness: {e}")
                else:
                    # TEMPERATURE DOWN
                    try:
                        current = float(state.get("input_number.kelvin_temp"))
                        new_value = min(max(current - temp_step, 2000), 6400)
                        input_number.set_value(entity_id="input_number.kelvin_temp", value=new_value)
                        log.info(f"Temperature set to {new_value}K")
                    except Exception as e:
                        log.error(f"Error adjusting temperature: {e}")