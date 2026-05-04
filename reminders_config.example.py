# Copy this file to reminders_config.py and fill in your personal reminders.
# reminders_config.py is gitignored to keep personal data private.

# Map of "HH:MM" -> TTS message string
DAILY_REMINDERS = {
    # "08:00": "Morning reminder message.",
    # "12:00": "Midday reminder message.",
    # "22:30": "Evening reminder message.",
}

# Optional: light actions triggered alongside a reminder
# Map of "HH:MM" -> keyword args passed to light.turn_on()
REMINDER_LIGHT_ACTIONS = {
    # "19:45": {"entity_id": "light.desktop_strip_light", "kelvin": 2700},
}
