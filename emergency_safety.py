EXTRACTOR = "switch.fan_stractor_kitchen"
BIG_KITCHEN_FAN = "switch.fan_closet_plug"
SMOKE_ENTITY = "binary_sensor.wifi_smoke_alarm_smoke"
SMOKE_APPLIANCE_CUTOFF_DELAY_S = 300  # 5 minutes


@state_trigger("binary_sensor.wifi_smoke_alarm_smoke == 'on'")
def emergency_smoke_response():
    """Emergency smoke alarm response"""
    task.unique("emergency_smoke_response")

    log.error("🚨 SMOKE ALARM ACTIVATED - EMERGENCY MODE")

    # Maximum lighting for evacuation
    input_number.brightness_lights = 100
    input_number.kelvin_temp = 6500
    pyscript.turn_on_off_all_lights(action='on')

    # IMPORTANT: do NOT cut appliances immediately (avoid false positives while cooking).
    # We only cut dangerous appliances if smoke persists for 5 minutes.

    # Turn on all ventilation (explicitly: extractor + big kitchen fan)
    light.turn_on(entity_id="light.bathroom_fan_dimmer", brightness_pct=100)
    switch.turn_on(entity_id=EXTRACTOR)
    switch.turn_on(entity_id=BIG_KITCHEN_FAN)

    # Retry once to ensure both fans are ON during emergency
    task.sleep(0.8)
    if state.get(EXTRACTOR) != "on":
        switch.turn_on(entity_id=EXTRACTOR)
    if state.get(BIG_KITCHEN_FAN) != "on":
        switch.turn_on(entity_id=BIG_KITCHEN_FAN)

    # Emergency announcement — force=True bypasses ALL house mode restrictions
    pyscript.speak_openai(msg="SMOKE ALARM! EVACUATE IMMEDIATELY!", lang='en', force=True)

    # Critical push notification
    pyscript.notify_coco(
        message=(
            "🚨 SMOKE ALARM ACTIVATED! Evacuate immediately! Ventilation ON. "
            "Safety cutoff of appliances will trigger only if smoke persists 5 minutes."
        ),
        title="🔥 EMERGENCY — SMOKE",
        target="all",
        speak=False,  # already spoke above via forced speak()
        critical=True,
    )

    # Delayed appliance cutoff only if smoke remains active for 5 minutes
    task.sleep(SMOKE_APPLIANCE_CUTOFF_DELAY_S)
    if state.get(SMOKE_ENTITY) == "on":
        switch.turn_off(entity_id="switch.water_heater_plug")
        switch.turn_off(entity_id="switch.washer_machine_plug")
        switch.turn_off(entity_id="switch.kitchen_filter_plug")
        log.warning("Smoke persisted 5 min: dangerous appliances turned OFF")
        pyscript.notify_coco(
            message="⛔ Humo persistente por 5 minutos: apagué calentador, lavadora y kitchen_filter_plug por seguridad.",
            title="⛔ Corte de seguridad por humo",
            target="all",
            speak=False,
            critical=True,
        )

    # Enable cameras
    switch.turn_on(entity_id="switch.livingroomcam_recordings")

@state_trigger("binary_sensor.wifi_smoke_alarm_smoke == 'off'")
def smoke_alarm_cleared():
    """Return to normal when smoke clears"""
    input_number.brightness_lights = 30
    input_number.kelvin_temp = 3000
    pyscript.speak_openai(msg="Smoke alarm cleared. Check all areas for safety.", lang='en', force=True)
    pyscript.notify_coco(
        message="✅ Smoke alarm cleared. Check all areas for safety.",
        title="Smoke Cleared",
        target="all",
    )


@state_trigger("sensor.espdesktop_pm_1_0_m == 'unavailable'")
def espdesktop_disconnected():
    """Restart espdesktop sensors when PM1.0 becomes unavailable"""
    try:
        switch.turn_off(entity_id="switch.fan_stractor_kitchen")
        task.sleep(1)
        switch.turn_on(entity_id="switch.fan_stractor_kitchen")
        log.info("ESPDesktop recovery: Restarted kitchen fan extractor")
    except Exception as e:
        log.error(f"ESPDesktop recovery failed: {e}")
