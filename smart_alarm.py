from datetime import datetime, timedelta, date
import random, json, urllib.request, urllib.parse, urllib.error, base64

# ── Fitbit helpers (embedded to avoid cross-file import issues in pyscript) ───

_FITBIT_TOKENS_PATH = "/home/node/.openclaw/workspace/skills/fitbit/tokens.json"

def _fitbit_load_tokens():
    with open(_FITBIT_TOKENS_PATH) as f:
        return json.load(f)

def _fitbit_save_tokens(tok):
    with open(_FITBIT_TOKENS_PATH, "w") as f:
        json.dump(tok, f, indent=2)

def _fitbit_refresh(tokens):
    creds = base64.b64encode(f"{tokens['client_id']}:{tokens['client_secret']}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
    }).encode()
    req = urllib.request.Request(
        "https://api.fitbit.com/oauth2/token", data=data,
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        new = json.loads(r.read())
    tokens["access_token"] = new["access_token"]
    tokens["refresh_token"] = new.get("refresh_token", tokens["refresh_token"])
    _fitbit_save_tokens(tokens)
    return tokens

def _fitbit_get(path):
    tokens = _fitbit_load_tokens()
    def _req(tok):
        r = urllib.request.Request(
            f"https://api.fitbit.com{path}",
            headers={"Authorization": f"Bearer {tok['access_token']}"}
        )
        with urllib.request.urlopen(r, timeout=15) as resp:
            return json.loads(resp.read())
    try:
        return _req(tokens)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return _req(_fitbit_refresh(tokens))
        raise

def _get_fitbit_sleep():
    """Fetch last night's Fitbit sleep data. Returns dict or None."""
    try:
        tokens = _fitbit_load_tokens()
        uid = tokens["user_id"]
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        data = _fitbit_get(f"/1.2/user/{uid}/sleep/date/{yesterday}.json")
        if not data.get("sleep"):
            return None
        s = data["summary"]
        total_min = s.get("totalMinutesAsleep", 0)
        stages    = s.get("stages", {})
        return {
            "total_hours": round(total_min / 60.0, 2),
            "deep_min":    stages.get("deep", 0),
            "rem_min":     stages.get("rem", 0),
            "light_min":   stages.get("light", 0),
            "awake_min":   stages.get("wake", 0),
        }
    except Exception as e:
        log.warning(f"SmartAlarm: Fitbit sleep fetch failed — {e}")
        return None

def _classify_fitbit_sleep(sleep):
    """Return 'excellent', 'good', or 'poor' based on Fitbit data."""
    if sleep["total_hours"] >= 7.5 and sleep["deep_min"] >= 60:
        return "excellent"
    elif sleep["total_hours"] >= 6.5 and sleep["deep_min"] >= 40:
        return "good"
    else:
        return "poor"

async def generate_ai_morning_message(sleep_duration=None, weather_info=None, challenge=None, streak=0, air_quality=None, fitbit_sleep=None):
    """
    Generate personalized motivational morning messages using ChatGPT conversation entity

    Uses the conversation.chatgpt entity to generate contextual wake-up messages
    based on sleep quality, weather conditions, daily challenges, and air quality.

    Args:
        sleep_duration: Hours of sleep (float)
        weather_info: Weather conditions and temperature
        challenge: Today's micro-challenge
        streak: Current challenge streak count
        air_quality: Indoor air quality information

    Returns:
        Generated motivational message string or None if generation fails
    """
    try:
        # Build context for ChatGPT prompt
        current_time = datetime.now()
        day_name = current_time.strftime('%A')

        # Create contextual prompt for ChatGPT
        context_parts = [
            f"Generate a motivational morning wake-up message for {day_name}.",
            "Keep it energetic, positive, and personal (2-3 sentences max).",
            "Use text only - no emojis or special characters.",
            "Shuffle the order of the details so each message feels fresh and non-repetitive.",
            "Always include an uplifting affirmation or positive encouragement for the day."
        ]

        # Add sleep context — prefer real Fitbit data if available
        if fitbit_sleep:
            h = fitbit_sleep["total_hours"]
            deep = fitbit_sleep["deep_min"]
            rem  = fitbit_sleep["rem_min"]
            quality = _classify_fitbit_sleep(fitbit_sleep)
            if quality == "excellent":
                context_parts.append(
                    f"They got excellent sleep ({h:.1f} hours, {deep}min deep, {rem}min REM) — celebrate this and energize them!"
                )
            elif quality == "good":
                context_parts.append(
                    f"They got decent sleep ({h:.1f} hours, {deep}min deep, {rem}min REM) — acknowledge positively and keep them motivated."
                )
            else:
                context_parts.append(
                    f"They got poor sleep ({h:.1f} hours, only {deep}min deep sleep, {rem}min REM) — be gentle, encouraging, suggest staying hydrated and taking it easy this morning."
                )
        elif sleep_duration:
            if sleep_duration >= 8:
                context_parts.append(f"They got excellent sleep ({sleep_duration:.1f} hours) - celebrate this!")
            elif sleep_duration >= 7:
                context_parts.append(f"They got good sleep ({sleep_duration:.1f} hours) - acknowledge this positively.")
            else:
                context_parts.append(f"They got limited sleep ({sleep_duration:.1f} hours) - encourage gently and suggest energy-boosting tips.")

        # Add weather context
        if weather_info:
            context_parts.append(f"Current weather: {weather_info['condition']} and {weather_info['temperature']}°C. Include weather-appropriate encouragement and activity suggestions.")

        # Add air quality context
        if air_quality:
            context_parts.append(f"Indoor air quality at workspace: {air_quality['pm25_level']:.1f} μg/m³ ({air_quality['category']}). {air_quality['recommendation']}")

        # Add challenge context
        if challenge:
            if streak > 0:
                context_parts.append(f"They're on a {streak}-day streak! Today's challenge: {challenge}. Celebrate their consistency!")
            else:
                context_parts.append(f"Today's new challenge: {challenge}. Make it sound fun and achievable!")

        # Add routine reminder context
        context_parts.append("End with a brief reminder about their morning routine: stretch, make bed, bathroom, wash face, sun protection, drink water, dress, walk.")

        prompt = " ".join(context_parts)

        # Call ChatGPT service using conversation entity
        try:
            response = await hass.services.async_call(
                "conversation",
                "process",
                {
                    "agent_id": "conversation.chatgpt",  # Your ChatGPT conversation entity
                    "text": prompt
                },
                blocking=True,
                return_response=True
            )

            # Extract the generated message from conversation response
            if response and "response" in response and "speech" in response["response"]:
                generated_message = response["response"]["speech"]["plain"]["speech"].strip()
                log.info(f"AI Morning Message: Generated {len(generated_message)} character message")
                return generated_message
            elif response and "response" in response and "text" in response["response"]:
                generated_message = response["response"]["text"].strip()
                log.info(f"AI Morning Message: Generated {len(generated_message)} character message")
                return generated_message
            else:
                log.warning(f"AI Morning Message: Unexpected response format - {response}")
                return None

        except Exception as e:
            log.error(f"AI Morning Message: ChatGPT service call failed - {e}")
            return None

    except Exception as e:
        log.error(f"AI Morning Message: Generation error - {e}")
        return None

def get_positive_affirmation():
    """Return a rotating positive affirmation for daily encouragement."""
    positive_messages = [
        "Today is full of opportunities—step forward with confidence!",
        "You've got everything you need to make today amazing!",
        "Your energy sets the tone—shine brightly today!",
        "Every small step today fuels your bigger dreams!",
        "This morning is a fresh start—embrace it with gratitude!",
    ]
    return random.choice(positive_messages)

async def get_weather_context():
    """
    Get current weather information for context

    Returns:
        Dict with weather condition and temperature, or None if unavailable
    """
    try:
        # Try common weather entity names
        weather_entities = [
            "weather.home",
            "weather.forecast_home",
            "weather.openweathermap",
            "weather.weather"
        ]

        for entity in weather_entities:
            try:
                weather_state = state.get(entity)
                if weather_state:
                    # Get temperature - try both temperature and temp attributes
                    temperature = None
                    if hasattr(weather_state, 'temperature'):
                        temperature = weather_state.temperature
                    elif hasattr(weather_state, 'temp'):
                        temperature = weather_state.temp

                    return {
                        "condition": weather_state.state,
                        "temperature": temperature or "unknown"
                    }
            except:
                continue

        log.debug("Weather context: No weather entities found")
        return None

    except Exception as e:
        log.error(f"Weather context error: {e}")
        return None

async def get_air_quality_context():
    """
    Get current indoor air quality information from desk sensor

    Returns:
        Dict with PM2.5 level and workspace recommendations, or None if unavailable
    """
    try:
        # Get PM2.5 level from desktop sensor
        pm25_sensor = state.get("sensor.espdesktop_pm_2_5_m")
        if not pm25_sensor:
            log.debug("Air quality: PM2.5 sensor not available")
            return None

        pm25_level = float(pm25_sensor.state)

        # Determine indoor air quality category and workspace recommendations
        if pm25_level <= 12:
            category = "excellent"
            recommendation = "Perfect indoor air quality at your workspace!"
        elif pm25_level <= 35:
            category = "good"
            recommendation = "Good indoor air - your workspace is healthy"
        elif pm25_level <= 55:
            category = "moderate"
            recommendation = "Consider opening a window for fresh air circulation"
        else:
            category = "needs attention"
            recommendation = "Indoor air needs attention - check air purifier or ventilation"

        return {
            "pm25_level": pm25_level,
            "category": category,
            "recommendation": recommendation
        }

    except (ValueError, AttributeError) as e:
        log.debug(f"Air quality context error: {e}")
        return None

def get_daily_challenge():
    """
    Get or generate today's micro-challenge

    Returns:
        Dict with challenge text and current streak
    """
    try:
        # Challenge categories with rotating options
        challenges = {
            "fitness": [
                "10 pushups after coffee",
                "5-minute stretch session",
                "Walk 500 extra steps",
                "30-second plank hold",
                "Take stairs whenever possible"
            ],
            "wellness": [
                "Drink a glass of water first thing",
                "Practice 5 deep breaths",
                "Write down 3 gratitudes",
                "Spend 2 minutes in sunlight",
                "Do a 1-minute meditation"
            ],
            "productivity": [
                "Make your bed immediately",
                "Clear your workspace first",
                "Plan your top 3 priorities",
                "Do one small task you've been avoiding",
                "Organize one small area"
            ],
            "mindfulness": [
                "Notice 5 things you're grateful for",
                "Eat breakfast without distractions",
                "Take 3 conscious breaths",
                "Smile at yourself in the mirror",
                "Set a positive intention for the day"
            ]
        }

        # Get day of week to rotate challenge categories
        current_time = datetime.now()
        day_number = current_time.weekday()  # 0 = Monday

        category_names = list(challenges.keys())
        category = category_names[day_number % len(category_names)]

        # Select challenge based on day of month to add variety
        day_of_month = current_time.day
        challenge_list = challenges[category]
        selected_challenge = challenge_list[day_of_month % len(challenge_list)]

        # Try to get streak from Home Assistant (will implement entity later)
        streak = 0
        try:
            # This will be implemented when we add the input helpers
            streak_entity = state.get("input_number.challenge_streak")
            if streak_entity:
                streak = int(float(streak_entity.state))
        except:
            pass

        return {
            "challenge": selected_challenge,
            "category": category,
            "streak": streak
        }

    except Exception as e:
        log.error(f"Daily challenge error: {e}")
        return {"challenge": "Start your day with intention", "category": "general", "streak": 0}

@state_trigger("input_select.house_mode == 'Sleep'")
def activate_smart_alarm():
    """
    Smart alarm system that calculates optimal wake time based on sleep cycles

    Features:
    - Calculates wake time between 8-8.5 hours after sleep mode activation
    - Accounts for natural 90-minute sleep cycles
    - Sets up gentle wake-up sequence with gradual lighting and sounds
    - Provides sleep quality optimization
    """
    task.unique("smart_alarm_activation")

    try:
        sleep_time = datetime.now()
        log.info(f"Smart alarm: Sleep mode activated at {sleep_time.strftime('%H:%M')}")

        # Store sleep time for tracking
        input_datetime.sleep_start_time = sleep_time.strftime('%Y-%m-%d %H:%M:%S')

        # Calculate target sleep duration (8 to 8.5 hours)
        min_sleep_hours = 8.0
        max_sleep_hours = 9

        # Calculate sleep cycles (90-minute cycles)
        cycle_length_minutes = 90

        # Find optimal wake time within the 8-8.5 hour window
        earliest_wake = sleep_time + timedelta(hours=min_sleep_hours)
        latest_wake = sleep_time + timedelta(hours=max_sleep_hours)

        # Calculate sleep cycles to find optimal wake windows
        optimal_wake_times = []
        current_time = earliest_wake

        while current_time <= latest_wake:
            optimal_wake_times.append(current_time)
            current_time += timedelta(minutes=cycle_length_minutes)

        # Ensure we have wake times to work with
        if not optimal_wake_times:
            log.error("Smart alarm: No optimal wake times calculated")
            return

        # Choose the wake time closest to 8.25 hours (middle of range)
        target_duration = timedelta(hours=8.25)
        ideal_wake_time = sleep_time + target_duration

        # Find closest optimal wake time to ideal
        best_wake_time = min(optimal_wake_times, key=lambda x: abs((x - ideal_wake_time).total_seconds()))

        # Store the calculated wake time
        input_datetime.smart_alarm_wake_time = best_wake_time.strftime('%Y-%m-%d %H:%M:%S')

        actual_sleep_duration = (best_wake_time - sleep_time).total_seconds() / 3600
        log.info(f"Smart alarm: Wake time set for {best_wake_time.strftime('%H:%M')} "
                f"({actual_sleep_duration:.1f} hours of sleep)")

        # Set up the wake-up task
        task.create(schedule_wake_up_sequence(best_wake_time))

        # Optional: Provide sleep time confirmation
        try:
            sleep_duration_text = f"{actual_sleep_duration:.1f} hours"
            # force=True: this fires right as Sleep mode activates — must bypass TTS filter
            pyscript.speak_openai(msg=f"Good night! Wake up scheduled for {best_wake_time.strftime('%I:%M %p')} after {sleep_duration_text} of sleep", lang='en', force=True)
        except Exception as e:
            log.debug(f"Smart alarm: Could not provide sleep confirmation - {e}")

    except Exception as e:
        log.error(f"Smart alarm activation error: {e}")

async def schedule_wake_up_sequence(wake_time):
    """
    Schedule and execute the gentle wake-up sequence
    """
    task.unique("smart_alarm_wake_sequence")

    try:
        current_time = datetime.now()
        sleep_until = wake_time - timedelta(minutes=15)  # Start 15 minutes before target

        if sleep_until > current_time:
            sleep_duration = (sleep_until - current_time).total_seconds()
            log.info(f"Smart alarm: Sleeping until wake sequence at {sleep_until.strftime('%H:%M')}")
            await task.sleep(sleep_duration)

        # Check if still in sleep mode (user might have woken up early)
        if input_select.house_mode != "Sleep":
            log.info("Smart alarm: User already awake, canceling wake sequence")
            return

        log.info("Smart alarm: Starting gentle wake-up sequence")
        await execute_gentle_wake_up()

    except Exception as e:
        log.error(f"Smart alarm wake sequence error: {e}")

async def execute_gentle_wake_up():
    """
    Execute the gentle wake-up sequence with gradual lighting and sounds.
    Fetches real Fitbit sleep quality to adapt light intensity.
    """
    try:
        # Fetch Fitbit sleep data upfront for the entire sequence
        fitbit_sleep = _get_fitbit_sleep()
        sleep_quality = _classify_fitbit_sleep(fitbit_sleep) if fitbit_sleep else "good"
        log.info(f"Smart alarm: Fitbit sleep quality = {sleep_quality} | data = {fitbit_sleep}")

        # Phase 1: Pre-wake preparation (5 minutes before full wake)
        log.info("Smart alarm: Phase 1 - Pre-wake preparation")

        # Very gentle lighting start
        await gentle_light_wake_up(phase="pre-wake", sleep_quality=sleep_quality)

        # Soft nature sounds at very low volume
        await gentle_audio_wake_up(phase="pre-wake")

        # Wait 5 minutes
        await task.sleep(300)

        # Phase 2: Light wake-up (gradual brightness increase)
        log.info("Smart alarm: Phase 2 - Light wake-up sequence")

        await gentle_light_wake_up(phase="wake", sleep_quality=sleep_quality)

        # Wait 3 minutes
        await task.sleep(180)

        # Phase 3: Audio wake-up (gentle sounds)
        log.info("Smart alarm: Phase 3 - Audio wake-up sequence")

        await gentle_audio_wake_up(phase="wake")

        # Wait 2 minutes
        await task.sleep(120)

        # Phase 4: Full wake-up (normal day lighting)
        log.info("Smart alarm: Phase 4 - Full wake-up")

        # Transition to Day mode
        input_select.house_mode = "Day"

        # Provide wake-up summary with real Fitbit data
        await provide_wake_up_summary(fitbit_sleep=fitbit_sleep)

    except Exception as e:
        log.error(f"Gentle wake-up execution error: {e}")

async def gentle_light_wake_up(phase="wake", sleep_quality="good"):
    """
    Gradual lighting wake-up sequence.
    sleep_quality: 'excellent' | 'good' | 'poor'
    Poor sleep → dimmer, warmer lights to ease into the day.
    Excellent sleep → brighter, cooler lights to energize.
    """
    try:
        # Light targets based on sleep quality
        quality_wake = {
            "excellent": (50, 4200),   # bright & energetic
            "good":      (30, 3200),   # balanced
            "poor":      (15, 2700),   # very gentle
        }
        wake_brightness, wake_kelvin = quality_wake.get(sleep_quality, (30, 3200))

        if phase == "pre-wake":
            # Always start very dim regardless of sleep quality
            target_brightness = 3
            target_kelvin = 2000
            duration = 180  # 3 minutes gradual increase

        else:  # phase == "wake"
            target_brightness = wake_brightness
            target_kelvin = wake_kelvin
            duration = 300  # 5 minutes gradual increase

        # Start with bedroom light for personal wake-up
        bedroom_light = "light.bedroom_light"

        # Ensure light is on at minimum brightness first
        light.turn_on(entity_id=bedroom_light, brightness=1, color_temp_kelvin=2000)
        await task.sleep(2)

        # Gradually increase brightness
        await pyscript.smooth_transition(
            entity_id=bedroom_light,
            attribute="brightness",
            target=target_brightness,
            duration=duration
        )

        # Gradually warm up color temperature
        await task.sleep(30)  # Small delay between brightness and color changes
        await pyscript.smooth_transition(
            entity_id=bedroom_light,
            attribute="color_temp",
            target=target_kelvin,
            duration=duration//2
        )

        if phase == "wake":
            # Add living room light for fuller illumination
            await task.sleep(60)
            light.turn_on(entity_id="light.livingroom_light", brightness=20, color_temp_kelvin=3000)

        log.info(f"Smart alarm: {phase} lighting sequence completed")

    except Exception as e:
        log.error(f"Gentle light wake-up error: {e}")

async def gentle_audio_wake_up(phase="wake"):
    """
    Gentle audio wake-up with nature sounds and gradual volume
    """
    try:
        if phase == "pre-wake":
            # Very quiet nature sounds
            volume = 0.3
            duration = 120  # 2 minutes
            sounds = ["soft rain", "gentle birds", "quiet ocean waves"]

        else:  # phase == "wake"
            # Slightly louder, more varied sounds
            volume = 0.5
            duration = 180  # 3 minutes
            sounds = ["morning birds", "gentle stream", "light wind chimes"]

        # Choose random sound for variety
        sound_choice = random.choice(sounds)

        # Use Google Speaker for wake-up sounds
        try:
            # Set volume
            media_player.volume_set(entity_id="media_player.google_speaker", volume_level=volume)
            await task.sleep(1)

            # Create wake-up message with nature description
            if phase == "pre-wake":
                message = f"Good morning. Starting gentle wake-up with {sound_choice}"
            else:
                message = f"Rise and shine. Time to wake up gently with {sound_choice}"

            # Speak the wake-up message softly — force=True: still in Sleep mode during wake sequence
            pyscript.speak_openai(msg=message, lang='en', force=True)

            # Note: Actual nature sounds would require audio files or streaming service
            # For now, we use TTS descriptions as gentle audio cues

        except Exception as e:
            log.warning(f"Smart alarm: Could not play wake-up audio - {e}")
            # Fallback to simple TTS announcement
            try:
                if phase == "wake":
                    pyscript.speak_openai(msg="Good morning! Time to wake up gently", lang='en', force=True)
            except:
                pass

        log.info(f"Smart alarm: {phase} audio sequence completed")

    except Exception as e:
        log.error(f"Gentle audio wake-up error: {e}")

async def provide_wake_up_summary(fitbit_sleep=None):
    """
    Provide AI-enhanced wake-up summary with motivational content.
    fitbit_sleep: real Fitbit sleep dict (or None to fall back to calculated duration).
    """
    try:
        current_time = datetime.now()

        # Calculate fallback sleep duration from HA datetime entity
        sleep_duration = None
        try:
            sleep_start_str = input_datetime.sleep_start_time
            sleep_start = datetime.strptime(sleep_start_str, '%Y-%m-%d %H:%M:%S')
            sleep_duration = (current_time - sleep_start).total_seconds() / 3600
        except:
            pass

        # If no Fitbit data passed in, try fetching now
        if fitbit_sleep is None:
            fitbit_sleep = _get_fitbit_sleep()

        # Use Fitbit hours as primary sleep_duration if available
        if fitbit_sleep:
            sleep_duration = fitbit_sleep["total_hours"]

        # Get all context information
        weather_info = await get_weather_context()
        air_quality_info = await get_air_quality_context()
        challenge_info = get_daily_challenge()

        # Generate AI-powered wake-up message with full context + real Fitbit data
        ai_message = await generate_ai_morning_message(
            sleep_duration=sleep_duration,
            weather_info=weather_info,
            challenge=challenge_info["challenge"],
            streak=challenge_info["streak"],
            air_quality=air_quality_info,
            fitbit_sleep=fitbit_sleep,
        )

        # Use AI message if available, otherwise fallback to traditional summary
        if ai_message:
            summary_message = ai_message
            log.info("Smart alarm: Using AI-generated wake-up summary")
        else:
            # Fallback summary with positive encouragement
            positive_note = get_positive_affirmation()
            if sleep_duration:
                sleep_quality = "excellent" if sleep_duration >= 8 else "good"
                summary_message = (f"Good morning! You slept for {sleep_duration:.1f} hours. "
                                 f"Sleep quality: {sleep_quality}. "
                                 f"Current time is {current_time.strftime('%I:%M %p')}. "
                                 f"Today's challenge: {challenge_info['challenge']}. "
                                 f"{positive_note}")
            else:
                summary_message = (f"Good morning! Current time is {current_time.strftime('%I:%M %p')}. "
                                   f"Today's challenge: {challenge_info['challenge']}. "
                                   f"{positive_note}")

        # Provide wake-up summary using high-quality OpenAI TTS
        # force=True: mode may still be transitioning from Sleep → Day
        pyscript.speak_openai(msg=summary_message, lang='en', force=True)

        log.info(f"Smart alarm: Wake-up sequence completed at {current_time.strftime('%H:%M')}")
        log.info(f"Smart alarm: Today's challenge ({challenge_info['category']}): {challenge_info['challenge']}")

    except Exception as e:
        log.error(f"Wake-up summary error: {e}")

@service
async def cancel_smart_alarm():
    """
    Cancel the smart alarm if user wakes up early
    """
    try:
        # This would be called automatically when house mode changes from Sleep
        log.info("Smart alarm: Alarm canceled - user woke up early")

        # Could add logic here to track early wake-ups for pattern analysis

    except Exception as e:
        log.error(f"Cancel smart alarm error: {e}")

@service
def get_sleep_statistics():
    """
    Service to get sleep pattern statistics
    """
    try:
        # This could be expanded to track sleep patterns over time
        # For now, just provide current sleep session info

        try:
            sleep_start_str = input_datetime.sleep_start_time
            wake_time_str = input_datetime.smart_alarm_wake_time

            if sleep_start_str and wake_time_str:
                sleep_start = datetime.strptime(sleep_start_str, '%Y-%m-%d %H:%M:%S')
                planned_wake = datetime.strptime(wake_time_str, '%Y-%m-%d %H:%M:%S')
                planned_duration = (planned_wake - sleep_start).total_seconds() / 3600

                log.info(f"Sleep statistics: Bedtime {sleep_start.strftime('%H:%M')}, "
                        f"Planned wake {planned_wake.strftime('%H:%M')}, "
                        f"Duration {planned_duration:.1f} hours")
            else:
                log.info("Sleep statistics: No current sleep session")

        except Exception as e:
            log.error(f"Sleep statistics error: {e}")

    except Exception as e:
        log.error(f"Get sleep statistics error: {e}")

@state_trigger("binary_sensor.closet_motion_sensor == 'on'")
@time_active("range(05:00, 08:00)")
async def smart_morning_routine():
    """
    Smart morning routine triggered by closet motion sensor

    Automatically starts the day when you get dressed in the morning
    Only active between 5:00 AM and 8:00 AM to prevent false triggers
    Includes time-based logic and prevents multiple executions
    """
    task.unique("smart_morning_routine")

    # Skip if house is in Away mode
    if input_select.house_mode == "Away":
        log.debug("Morning routine: Skipped in Away mode")
        return

    current_time = datetime.now()

    # Check if morning routine already executed today
    try:
        if input_boolean.morning_routine_executed == 'on':
            log.debug("Morning routine: Already executed today")
            return
    except AttributeError:
        log.warning("Morning routine: morning_routine_executed boolean not found")

    log.info(f"Morning routine: Triggered by closet motion at {current_time.strftime('%H:%M')}")

    # Cancel any active smart alarm (user woke up naturally)
    if input_select.house_mode == "Sleep":
        log.info("Morning routine: Canceling smart alarm - natural wake-up detected")
        await cancel_smart_alarm()

    # Execute morning routine steps
    await execute_morning_routine()

    # Mark routine as executed for today
    try:
        input_boolean.turn_on(entity_id="input_boolean.morning_routine_executed")
        log.info("Morning routine: Marked as executed for today")
    except AttributeError:
        log.warning("Morning routine: Could not mark as executed")

async def execute_morning_routine():
    """
    Execute the complete morning routine sequence
    """
    try:
        log.info("Morning routine: Starting execution")

        # Step 1: Switch to previous house mode (or Day if none)
        try:
            previous_mode = input_text.previous_house_mode
            if previous_mode and previous_mode not in ["Sleep", "Night"]:
                target_mode = previous_mode
            else:
                target_mode = "Day"

            log.info(f"Morning routine: Switching to {target_mode} mode")
            input_select.house_mode = target_mode

            # Small delay to let house mode change take effect
            await task.sleep(2)

        except Exception as e:
            log.error(f"Morning routine: Could not switch house mode - {e}")
            # Fallback to Day mode
            input_select.house_mode = "Day"

        # Step 2: Gradual morning lighting
        await morning_lighting_sequence()

        # Step 3: Optional morning announcements
        await morning_announcements()

        # Step 4: Morning device activation
        await morning_device_activation()

        log.info("Morning routine: Execution completed successfully")

    except Exception as e:
        log.error(f"Execute morning routine error: {e}")

async def morning_lighting_sequence():
    """
    Gradual morning lighting to ease into the day
    """
    try:
        log.info("Morning routine: Starting lighting sequence")

        # Get current time for context
        current_time = datetime.now()
        current_hour = current_time.hour

        # Determine lighting based on time
        if current_hour < 6:
            # Very early morning - dim lighting
            target_brightness = 15
            target_kelvin = 2700
        else:
            # Normal morning - full day lighting
            target_brightness = 50
            target_kelvin = 4000

        # Update global brightness and temperature
        input_number.set_value(entity_id="input_number.brightness_lights", value=target_brightness)
        await task.sleep(1)
        input_number.set_value(entity_id="input_number.kelvin_temp", value=target_kelvin)
        await task.sleep(1)

        # Turn on key morning lights gradually
        morning_lights = [
            "light.bedroom_light",
            "light.bathroom_light",
            "light.kitchen_light"
        ]

        for light_entity in morning_lights:
            try:
                # Start very dim and gradually increase
                light.turn_on(entity_id=light_entity, brightness=10, color_temp_kelvin=2700)
                await task.sleep(2)

                # Gradually increase to target brightness
                await pyscript.smooth_transition(
                    entity_id=light_entity,
                    attribute="brightness",
                    target=target_brightness,
                    duration=30  # 30 second gradual increase
                )

                # Small delay between lights
                await task.sleep(5)

            except Exception as e:
                log.warning(f"Morning routine: Could not control {light_entity} - {e}")

        log.info(f"Morning routine: Lighting sequence completed (brightness: {target_brightness}%, kelvin: {target_kelvin}K)")

    except Exception as e:
        log.error(f"Morning lighting sequence error: {e}")

async def morning_announcements():
    """
    Enhanced morning announcements with AI-generated motivational content
    """
    try:
        current_time = datetime.now()

        # Get sleep duration for context
        sleep_duration = None
        try:
            sleep_start_str = input_datetime.sleep_start_time
            if sleep_start_str:
                sleep_start = datetime.strptime(sleep_start_str, '%Y-%m-%d %H:%M:%S')
                sleep_duration = (current_time - sleep_start).total_seconds() / 3600
        except:
            pass

        # Get all context information
        weather_info = await get_weather_context()
        air_quality_info = await get_air_quality_context()
        challenge_info = get_daily_challenge()

        # Generate AI-powered morning message with full context
        ai_message = await generate_ai_morning_message(
            sleep_duration=sleep_duration,
            weather_info=weather_info,
            challenge=challenge_info["challenge"],
            streak=challenge_info["streak"],
            air_quality=air_quality_info,
        )

        # Use AI message if available, otherwise fallback to traditional message
        if ai_message:
            morning_message = ai_message
            log.info("Morning routine: Using AI-generated motivational message")
        else:
            # Fallback to enhanced traditional message
            if current_time.hour < 6:
                greeting = "Good early morning!"
            elif current_time.hour < 8:
                greeting = "Good morning!"
            else:
                greeting = "Good late morning!"

            details = []

            if sleep_duration:
                if sleep_duration >= 8:
                    sleep_quality = "excellent"
                elif sleep_duration >= 7:
                    sleep_quality = "good"
                else:
                    sleep_quality = "short but restful"
                details.append(f"You slept for {sleep_duration:.1f} hours—{sleep_quality} rest!")

            if weather_info:
                details.append(f"It's {weather_info['condition']} and {weather_info['temperature']}°C outside.")

            if air_quality_info:
                if air_quality_info["category"] in ["excellent", "good"]:
                    details.append(air_quality_info['recommendation'])
                else:
                    details.append(f"Air quality alert: {air_quality_info['recommendation']}")

            if challenge_info["streak"] > 0:
                details.append(f"You're on a {challenge_info['streak']}-day streak! Today's challenge: {challenge_info['challenge']}.")
            else:
                details.append(f"Today's micro-challenge: {challenge_info['challenge']}.")

            random.shuffle(details)
            details_text = " ".join(details)

            routine_steps = "Remember: stretch, make bed, bathroom, wash face, sun protection, drink water, dress, and walk."
            positive_note = get_positive_affirmation()

            message_parts = [f"{greeting} Morning routine activated."]
            if details_text:
                message_parts.append(details_text)
            message_parts.append(f"Current time is {current_time.strftime('%I:%M %p')}.")
            message_parts.append(positive_note)
            message_parts.append(routine_steps)

            morning_message = " ".join(message_parts)
            log.info("Morning routine: Using fallback enhanced message")

        # Announce the morning routine using high-quality OpenAI TTS
        # force=True: mode may still be transitioning from Sleep → Day
        try:
            pyscript.speak_openai(msg=morning_message, lang='en', force=True)
            log.info(f"Morning routine: Morning announcement delivered ({len(morning_message)} characters)")

            # Log the challenge for tracking
            log.info(f"Morning routine: Today's challenge ({challenge_info['category']}): {challenge_info['challenge']}")
            if challenge_info["streak"] > 0:
                log.info(f"Morning routine: Current streak: {challenge_info['streak']} days")

        except Exception as e:
            log.warning(f"Morning routine: Could not deliver announcement - {e}")

    except Exception as e:
        log.error(f"Morning announcements error: {e}")

async def morning_device_activation():
    """
    Activate morning devices and systems
    """
    try:
        log.info("Morning routine: Activating morning devices")

        # Essential morning devices
        morning_devices = [
            "switch.refrigerator_plug",
            "switch.monitor_plug",
            "switch.pump_cat_switch",
            "switch.ups_switch"
        ]

        activated_count = 0
        for device in morning_devices:
            try:
                switch.turn_on(entity_id=device)
                activated_count += 1
                await task.sleep(1)  # Small delay between device activations
            except Exception as e:
                log.warning(f"Morning routine: Could not activate {device} - {e}")

        log.info(f"Morning routine: Activated {activated_count}/{len(morning_devices)} morning devices")

        # Optional: Start coffee maker or other morning appliances
        # This could be expanded based on what smart appliances you have

    except Exception as e:
        log.error(f"Morning device activation error: {e}")

@time_trigger("cron(0 0 * * *)")  # Reset at midnight
def reset_morning_routine_flag():
    """
    Reset the morning routine executed flag at midnight
    """
    try:
        input_boolean.turn_off(entity_id="input_boolean.morning_routine_executed")
        log.info("Morning routine: Reset executed flag for new day")
    except Exception as e:
        log.error(f"Reset morning routine flag error: {e}")
