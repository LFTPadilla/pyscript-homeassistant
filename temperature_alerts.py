import time

# Cooldown to avoid spamming the notification (e.g., 4 hours)
LAST_NOTIFIED_TIME = 0
COOLDOWN_SECONDS = 4 * 3600

# Temperature thresholds
MIN_INTERNAL_TEMP_FOR_ALERT = 22.0  # Don't alert if internal temp is below this (already cool)
WARM_TEMP_THRESHOLD = 25.0           # Temperature considered "hot"

@state_trigger("sensor.t_h_sensor_temperature or sensor.exterior_temp_hum_temperature")
def check_temperature_ventilation():
    """
    Checks if internal temperature is significantly higher than external.
    Only notifies if internal temp is >= 22°C to avoid unnecessary notifications.
    Adjusts message based on how warm it is inside:
    - >= 25°C: Use strong "it's hot" message
    - 22-25°C: Use gentle ventilation suggestion message
    Recommends opening windows if the house mode permits it.
    """
    global LAST_NOTIFIED_TIME

    current_time = time.time()

    # Do not spam the notification
    if current_time - LAST_NOTIFIED_TIME < COOLDOWN_SECONDS:
        return

    # Check current house mode
    try:
        mode = input_select.house_mode
    except Exception:
        mode = "Day"

    # Skip notification entirely if Felipe is sleeping or not at home
    if mode in ["Sleep", "Away"]:
        log.debug(f"Ventilation alert: Skipped because house mode is '{mode}'")
        return

    try:
        internal_temp = float(sensor.t_h_sensor_temperature)
        external_temp = float(sensor.exterior_temp_hum_temperature)
    except Exception as e:
        log.error(f"Ventilation alert: Error reading temperatures - {e}")
        return

    # Skip if internal temp is below minimum threshold (already cool enough)
    if internal_temp < MIN_INTERNAL_TEMP_FOR_ALERT:
        log.debug(f"Ventilation alert: Internal temp {internal_temp:.1f}°C is below {MIN_INTERNAL_TEMP_FOR_ALERT}°C, skipping")
        return

    diff = internal_temp - external_temp

    # Only alert if difference is significant (>= 5°C)
    if diff >= 5.0:
        # Determine message based on how warm it is
        if internal_temp >= WARM_TEMP_THRESHOLD:
            # It's hot inside
            msg = f"Felipe, hace calor adentro ({internal_temp:.1f}°C) y afuera está mucho más fresco ({external_temp:.1f}°C). Te recomiendo abrir las ventanas para ventilar."
        else:
            # It's moderately warm inside
            msg = f"Felipe, está un poco caluroso adentro ({internal_temp:.1f}°C) mientras que afuera está más fresco ({external_temp:.1f}°C). Podrías abrir las ventanas si lo deseas."

        # Use centralized notify_coco service
        # Push notification is always sent, but TTS is suppressed automatically
        # by notify_coco if mode is Cine, Reading, Meditation, etc.
        pyscript.notify_coco(
            message=msg,
            title="Sugerencia de Ventilación 🌬️",
            target="felipe_phone",
            speak=True,
            speak_lang="es",
            speak_volume=0.6
        )

        log.info(f"Ventilation alert sent: {msg}")
        LAST_NOTIFIED_TIME = current_time
