@event_trigger("zha_event")
def handle_music_knob_events(device_ieee=None, command=None, args=None, **kwargs):
    """
    Knob controller for Google speaker music playback
    Controls volume with rotation and play/pause with toggle
    """
    # Replace with your knob's IEEE address
    if device_ieee != "a4:c1:38:36:07:75:9b:0f":
        return

    task.unique("handle_music_knob_events")
    # Debug log
    # log.info(f"Music knob event: command={command}, args={args}")

    # Set target media player
    speaker = "media_player.google_speaker_2"

    # Handle toggle for play/pause
    if command == "toggle":
        # log.info("Toggle play/pause")

        # Get current state of the speaker
        current_state = state.get(speaker)

        # Toggle play/pause based on current state
        if current_state == "playing":
            # If playing, pause it
            media_player.media_pause(entity_id=speaker)
            # log.info("Paused playback")
        elif current_state == "paused":
            # If paused, resume playback
            media_player.media_play(entity_id=speaker)
            # log.info("Resumed playback")
        elif current_state == "idle" or current_state == "off":
            # If idle or off, try to play last media
            media_player.media_play(entity_id=speaker)
             # Play white noise or ambient sound to change state to playing
            media_player.play_media(
                entity_id=speaker,
                media_content_id="https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",  # Replace with your preferred ambient sound URL
                media_content_type="audio/wav"
            )
            # log.info("Started playback")

        # Show notification
        # persistent_notification.create(
        #     message=f"Google Speaker: {'Paused' if current_state == 'playing' else 'Playing'}",
        #     title="Music Control",
        #     notification_id="music_control"
        # )

    # Handle volume adjustment with rotation
    elif command == "step" and isinstance(args, list) and len(args) >= 2:
        # Extract step mode and size
        step_mode = args[0]
        raw_step_size = int(args[1])

        # Scale for smoother volume adjustment (1-100)
        volume_step = max(1, raw_step_size // 5) / 100.0  # Convert to 0.0-1.0 range

        if hasattr(step_mode, "value"):
            # Get current volume using the correct method
            try:
                # Get speaker attributes
                speaker_attributes = state.getattr(speaker)
                # Extract volume_level from attributes
                current_volume = float(speaker_attributes.get("volume_level", 0.5))
                # log.info(f"Current volume: {current_volume}")

                # Volume UP
                if step_mode.value == 0:
                    new_volume = min(max(current_volume + volume_step, 0.0), 1.0)
                    media_player.volume_set(entity_id=speaker, volume_level=new_volume)
                    # log.info(f"Volume UP to {new_volume:.2f}")

                # Volume DOWN
                elif step_mode.value == 1:
                    new_volume = min(max(current_volume - volume_step, 0.0), 1.0)
                    media_player.volume_set(entity_id=speaker, volume_level=new_volume)
                    # log.info(f"Volume DOWN to {new_volume:.2f}")

                # Show volume level as notification (optional)
                volume_percentage = int(new_volume * 100)
                # persistent_notification.create(
                #     message=f"Volume: {volume_percentage}%",
                #     title="Volume Adjustment",
                #     notification_id="volume_level"
                # )
            except Exception as e:
                log.error(f"Error adjusting volume: {e}")
                # Fallback method if we can't get current volume
                if step_mode.value == 0:
                    media_player.volume_up(entity_id=speaker)
                    # log.info("Volume UP (default step)")
                elif step_mode.value == 1:
                    media_player.volume_down(entity_id=speaker)
                    # log.info("Volume DOWN (default step)")
