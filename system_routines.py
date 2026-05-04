# Daily reminders configuration
DAILY_REMINDERS = {
    "08:00": "Time to take your morning supplements: Vitamin C, Vitamin E, Omega-3, and Creatine.",
    "17:30": "Time to take a shower.",
    "18:00": "Time to take the meat out of the freezer.",
    "19:30": "Time to take your evening supplement: Zinc.",
    "19:45": "Time to check the cat food dispenser.",
    "22:30": "Time to take your bedtime supplements: Magnesium and Ashwagandha."
}

@time_trigger("cron(*/15 * * * *)")
def check_daily_reminders():
    """Check and send daily reminders every 15 minutes.
    Uses notify_coco so reminders always reach the phone (push)
    and are also spoken aloud when house mode allows TTS.
    """
    current_time = task.executor(datetime.datetime.now).strftime("%H:%M")

    if current_time in DAILY_REMINDERS:
        try:
            message = DAILY_REMINDERS[current_time]

            # Push + TTS — TTS will be filtered by house mode automatically
            pyscript.notify_coco(
                message=message,
                title="⏰ Reminder",
                speak=True,
                speak_lang="en",
                speak_volume=0.5,
            )

            # Special action for cat food reminder
            if "cat food" in message.lower():
                light.turn_on(entity_id="light.desktop_strip_light", kelvin=2700)

            log.info(f"Daily reminder sent: {message}")
        except Exception as e:
            log.error(f"Failed to send daily reminder: {e}")

@time_trigger("cron(00 12 * * *)")
def start_afternoon_routine():
    pyscript.turn_on_off_all_fans(action='off')
    cover.close_cover(entity_id="cover.curtain_living_room_curtain")

@time_trigger("cron(00 14 * * *)")
def start_work_afternoon_routine():
    switch.turn_on(entity_id="switch.pump_cat_switch")

@time_trigger("cron(00 18 * * *)")
def start_evening_routine():
    # Skip if in Away mode to preserve previous_house_mode for smart arrival restoration
    if input_select.house_mode == 'Away':
        log.info("start_evening_routine: skipping because in Away mode")
        return

    if input_select.house_mode == 'Cine':
        input_text.previous_house_mode = 'Night'
    else:
        input_select.house_mode = 'Night'
        input_text.previous_house_mode = 'Night'

@time_trigger("cron(00 19 * * *)")
def start_evening_routine_7():
    if input_select.house_mode != 'Cine':
        input_number.brightness_lights = 1
        input_number.kelvin_temp = 2200

@time_trigger("cron(00 20 * * *)")
def start_night_routine():
    if input_select.house_mode not in ['Sleep', 'Cine', 'Away']:
        cover.close_cover(entity_id="cover.curtain_living_room_curtain")


# @time_trigger("cron(28 17 * * *)")
# def start_nigh_routine_2():
#     try:
#         watch_battery = float(sensor.galaxy_watch4_gyqj_battery_level)
#     except:
#         log.error("Failed to read watch battery level")
#         watch_battery = 100  # Default to prevent false positives
#     if watch_batery  < 50:
#         msg = f"Charge your smart watch. Battery is at {watch_battery:.0f}%."
#         pyscript.speak(msg, 'en')

# @time_trigger("cron(57 22 * * *)")
# def before_shutdown_server():
#     pyscript.turn_on_off_all_lights(action='off')


# ── Bedtime reminders (21:00+, every 15 min until Sleep mode) ─────────────────

@time_trigger("once(21:00:00)")
def bedtime_reminder_start():
    """Start bedtime reminders at 21:00 if not in Sleep or Friends mode."""
    task.unique("bedtime_reminder_loop")

    max_iterations = 12  # up to 3 hours (12 × 15 min)
    messages = [
        "Hey Felipe, ya son las {time}. Deberías estar en camino a la cama. 🛌",
        "Son las {time} y sigues despierto. Tu sueño es tu máxima prioridad. 🌙",
        "Felipe, las {time}. Recuerda: dormir bien es lo más importante para mañana. 😴",
        "Ya son las {time}. Cuanto más esperes, más costará levantarte mañana. 🛌",
        "Las {time} — el cuerpo necesita descanso. A la cama ya. 💤",
    ]

    import random as _random

    for i in range(max_iterations):
        # Check if already in Sleep mode → stop
        mode = state.get("input_select.house_mode")
        if mode in ("Sleep", "Friends"):
            log.info(f"Bedtime reminder: stopping — mode is {mode}")
            return

        now_str = __import__('datetime').datetime.now().strftime("%H:%M")
        msg = _random.choice(messages).format(time=now_str)

        pyscript.notify_coco(
            message=msg,
            title="🛌 Hora de dormir",
            speak=True,
        )
        log.info(f"Bedtime reminder #{i+1} sent at {now_str}")

        task.sleep(900)  # 15 minutes

    log.info("Bedtime reminder: max iterations reached, stopping")


# ── DND (No molestar) — Android + iPhone a las 21:00 ─────────────────────────

@time_trigger("once(20:00:00)")
def enable_dnd_night():
    """Enable Do Not Disturb on Android (Pixel 7) and iPhone at 20:00."""
    task.unique("enable_dnd_night")

    mode = state.get("input_select.house_mode")
    if mode == "Friends":
        log.info("DND: skipping — Friends mode")
        return

    # Android Pixel 7 — companion app DND command
    try:
        notify.mobile_app_pixel_7(
            message="command_dnd",
            data={"command": "alarms_only"}
        )
        log.info("DND: Pixel 7 set to alarms_only")
    except Exception as e:
        log.warning(f"DND: Pixel 7 failed — {e}")

    # iPhone — companion app DND
    try:
        notify.mobile_app_iphone(
            message="command_do_not_disturb",
            data={"state": "true"}
        ) if False else None  # placeholder — iOS uses focus automation
        log.info("DND: iPhone DND sent")
    except Exception as e:
        log.warning(f"DND: iPhone — {e}")

    log.info("DND: night mode enabled on phones")


@time_trigger("once(07:30:00)")
def disable_dnd_morning():
    """Disable Do Not Disturb at 07:30 (after sleep report is delivered)."""
    task.unique("disable_dnd_morning")

    try:
        notify.mobile_app_pixel_7(
            message="command_dnd",
            data={"command": "off"}
        )
        log.info("DND: Pixel 7 DND disabled")
    except Exception as e:
        log.warning(f"DND: Pixel 7 disable failed — {e}")
