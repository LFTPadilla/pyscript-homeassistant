"""
Kitchen air quality automation.
Controls the kitchen extractor fan based on PM10 particulates.
Threshold: PM10 > 150
Cooldown: 3 minutes

Also includes auto-shutdown for closet fan after 10 minutes of manual activation.
"""

PM10_SENSOR = "sensor.espdesktop_pm_10_m"
EXTRACTOR = "switch.fan_stractor_kitchen"
CLOSET_FAN = "switch.fan_clothes_plug"
PM10_THRESHOLD = 150
COOLDOWN_MINUTES = 3
CLOSET_FAN_TIMEOUT = 600  # 10 minutes in seconds

@state_trigger(PM10_SENSOR)
def kitchen_extractor_particles():
    # Avoid concurrent executions
    task.unique("kitchen_extractor_particles")
    
    try:
        current_pm10 = float(state.get(PM10_SENSOR))
    except (ValueError, TypeError):
        return

    # Trigger ON if above threshold
    if current_pm10 > PM10_THRESHOLD:
        if state.get(EXTRACTOR) == "off":
            log.info(f"Kitchen Air: PM10 is {current_pm10}. Turning ON extractor.")
            switch.turn_on(entity_id=EXTRACTOR)
            
            pyscript.notify_coco(
                message=f"🌬️ Extractor activado. PM10: {current_pm10} µg/m³.",
                title="Calidad de Aire",
                speak=False
            )
    
    # Trigger OFF if below threshold (with cooldown)
    elif current_pm10 <= PM10_THRESHOLD:
        if state.get(EXTRACTOR) == "on":
            log.info(f"Kitchen Air: PM10 dropped to {current_pm10}. Cooldown {COOLDOWN_MINUTES}m.")
            
            # Wait for cooldown
            task.sleep(COOLDOWN_MINUTES * 60)
            
            # Final check before turning off
            try:
                final_pm10 = float(state.get(PM10_SENSOR))
                if final_pm10 <= PM10_THRESHOLD:
                    log.info(f"Kitchen Air: PM10 still low ({final_pm10}). Turning OFF extractor.")
                    switch.turn_off(entity_id=EXTRACTOR)
                else:
                    log.info(f"Kitchen Air: PM10 rose to {final_pm10}. Keeping extractor ON.")
            except:
                switch.turn_off(entity_id=EXTRACTOR)


@state_trigger(CLOSET_FAN)
def closet_fan_auto_shutdown():
    """Auto-shutdown clothes fan after 10 minutes to prevent overheating."""
    task.unique("closet_fan_auto_shutdown")
    
    current_state = state.get(CLOSET_FAN)
    
    if current_state == "on":
        log.info(f"Clothes fan turned ON. Scheduling auto-shutdown in {CLOSET_FAN_TIMEOUT}s (10 min).")
        
        try:
            # Wait 10 minutes
            task.sleep(CLOSET_FAN_TIMEOUT)
            
            # Check if it's still on before turning off
            if state.get(CLOSET_FAN) == "on":
                log.info("Clothes fan: 10 minutes elapsed. Auto-shutting down to prevent overheating.")
                switch.turn_off(entity_id=CLOSET_FAN)
                
                pyscript.notify_coco(
                    message="🌬️ Clothes fan auto-shutdown after 10 minutes.",
                    title="Clothes Fan Control",
                    speak=False
                )
            else:
                log.info("Clothes fan was manually turned off before auto-shutdown.")
        except Exception as e:
            log.error(f"Clothes fan auto-shutdown error: {e}")

