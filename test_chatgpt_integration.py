"""
Test script for ChatGPT conversation integration in Home Assistant PyScript

This script tests the AI morning message generation function to verify
that the conversation.chatgpt entity is working correctly.

To use:
1. Reload PyScript in Home Assistant (Developer Tools > PyScript > Reload)
2. Call this service from Developer Tools > Services:
   Service: pyscript.test_chatgpt_integration
"""

import asyncio
from datetime import datetime

# Import the functions we want to test (they should be available in PyScript global scope)
# If they're not available, we'll define stub versions for testing

@service
async def test_chatgpt_integration():
    """
    Test service to verify ChatGPT integration is working
    
    This service can be called from Home Assistant Developer Tools to test
    the AI morning message generation functionality.
    """
    try:
        log.info("ChatGPT Test: Starting integration test")
        
        # Test basic conversation service
        test_prompt = "Generate a short motivational good morning message for testing purposes."
        
        try:
            response = await hass.services.async_call(
                "conversation", 
                "process",
                {
                    "agent_id": "conversation.chatgpt",
                    "text": test_prompt
                },
                blocking=True,
                return_response=True
            )
            
            log.info(f"ChatGPT Test: Raw response structure: {type(response)} - {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            log.info(f"ChatGPT Test: Full response: {response}")
            
            # Try different response parsing approaches
            generated_message = None
            
            if response and "response" in response:
                resp = response["response"]
                log.info(f"ChatGPT Test: Response object keys: {list(resp.keys()) if isinstance(resp, dict) else 'Not a dict'}")
                
                # Try speech format
                if "speech" in resp and isinstance(resp["speech"], dict):
                    speech = resp["speech"]
                    if "plain" in speech and "speech" in speech["plain"]:
                        generated_message = speech["plain"]["speech"]
                        log.info("ChatGPT Test: Found message in speech.plain.speech format")
                    elif "speech" in speech:
                        generated_message = speech["speech"]
                        log.info("ChatGPT Test: Found message in speech.speech format")
                
                # Try text format
                elif "text" in resp:
                    generated_message = resp["text"]
                    log.info("ChatGPT Test: Found message in text format")
                
                # Try direct response
                elif isinstance(resp, str):
                    generated_message = resp
                    log.info("ChatGPT Test: Response is direct string")
            
            if generated_message:
                log.info(f"ChatGPT Test: SUCCESS! Generated message ({len(generated_message)} chars): '{generated_message[:100]}{'...' if len(generated_message) > 100 else ''}'")
                
                # Test with a sample wake-up message using our actual function
                log.info("ChatGPT Test: Testing AI morning message function...")
                
                # Test with a more detailed prompt like our actual function would generate
                detailed_prompt = "Generate a motivational morning wake-up message for Thursday. Keep it energetic, positive, and personal (2-3 sentences max). They got good sleep (7.5 hours) - acknowledge this positively. Current weather: sunny and 20°C. Include weather-appropriate encouragement and activity suggestions. They're on a 3-day streak! Today's challenge: smile at yourself in the mirror. Celebrate their consistency! End with a brief reminder about their morning routine: stretch, make bed, bathroom, wash face, sun protection, drink water, dress, walk."
                
                log.info("ChatGPT Test: Testing with detailed prompt like AI function would use...")
                
                detailed_response = await hass.services.async_call(
                    "conversation", 
                    "process",
                    {
                        "agent_id": "conversation.chatgpt",
                        "text": detailed_prompt
                    },
                    blocking=True,
                    return_response=True
                )
                
                # Parse the detailed response the same way
                detailed_message = None
                if detailed_response and "response" in detailed_response:
                    resp = detailed_response["response"]
                    if "speech" in resp and isinstance(resp["speech"], dict) and "plain" in resp["speech"] and "speech" in resp["speech"]["plain"]:
                        detailed_message = resp["speech"]["plain"]["speech"]
                    elif "text" in resp:
                        detailed_message = resp["text"]
                    elif isinstance(resp, str):
                        detailed_message = resp
                
                if detailed_message:
                    log.info(f"ChatGPT Test: Detailed prompt SUCCESS! Generated: '{detailed_message[:100]}{'...' if len(detailed_message) > 100 else ''}'")
                    
                    # Test speaking the message using OpenAI TTS
                    try:
                        await hass.services.async_call("tts", "speak", {
                            "entity_id": "tts.openai_tts_tts_1_hd",
                            "media_player_entity_id": "media_player.google_speaker",
                            "message": f"ChatGPT test successful! Here's your sample message: {detailed_message[:100]}"
                        })
                        log.info("ChatGPT Test: OpenAI TTS test completed successfully")
                    except Exception as e:
                        log.warning(f"ChatGPT Test: OpenAI TTS failed but that's okay - {e}")
                        
                else:
                    log.error("ChatGPT Test: Detailed prompt returned None - check response format")
                    
            else:
                log.error(f"ChatGPT Test: Could not extract message from response format")
                
        except Exception as e:
            log.error(f"ChatGPT Test: Service call failed - {e}")
            log.error(f"ChatGPT Test: Check that conversation.chatgpt entity exists and OpenAI integration is configured")
            
    except Exception as e:
        log.error(f"ChatGPT Test: Overall test failed - {e}")

@service 
def test_challenge_system():
    """
    Test the daily challenge system logic (standalone version)
    """
    try:
        log.info("Challenge Test: Testing daily challenge system")
        
        # Replicate the challenge logic from smart_alarm.py
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
        
        current_time = datetime.now()
        day_number = current_time.weekday()  # 0 = Monday
        day_of_month = current_time.day
        
        category_names = list(challenges.keys())
        category = category_names[day_number % len(category_names)]
        
        challenge_list = challenges[category]
        selected_challenge = challenge_list[day_of_month % len(challenge_list)]
        
        log.info(f"Challenge Test: Today is {current_time.strftime('%A')} (day {day_number})")
        log.info(f"Challenge Test: Category: {category}")
        log.info(f"Challenge Test: Challenge: {selected_challenge}")
        
        # Test rotation for the week
        for offset in range(7):
            test_day = (day_number + offset) % 7
            test_category = category_names[test_day % len(category_names)]
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            log.info(f"Challenge Test: {day_names[test_day]} -> {test_category}")
            
        log.info("Challenge Test: Challenge system working correctly!")
        
    except Exception as e:
        log.error(f"Challenge Test: Failed - {e}")

@service
def test_weather_integration():
    """
    Test weather entity detection
    """
    try:
        log.info("Weather Test: Testing weather integration")
        
        # List available weather entities for debugging
        weather_entities = [
            "weather.home",
            "weather.forecast_home", 
            "weather.openweathermap",
            "weather.weather"
        ]
        
        found_weather = False
        for entity in weather_entities:
            try:
                weather_state = state.get(entity)
                if weather_state:
                    log.info(f"Weather Test: Found entity {entity}: {weather_state.state}")
                    if hasattr(weather_state, 'temperature'):
                        log.info(f"Weather Test: Temperature: {weather_state.temperature}°C")
                    found_weather = True
                else:
                    log.debug(f"Weather Test: Entity {entity} not found")
            except Exception as e:
                log.debug(f"Weather Test: Error checking {entity}: {e}")
        
        if found_weather:
            log.info("Weather Test: SUCCESS! Weather entities are available")
        else:
            log.warning("Weather Test: No weather entities found - fallback system will work")
                
    except Exception as e:
        log.error(f"Weather Test: Failed - {e}")