"""
ElevenLabs TTS for Home Assistant via Pyscript
================================================
Calls the home server audio API (configured via AUDIO_SERVER env var) which handles
ElevenLabs API calls and audio caching. Returns a URL that the
Google Speaker can play directly via media_player.play_media.

Home server must be running: python3 el_audio_server.py
"""

_AUDIO_SERVER = pyscript.config.get("audio_server_url", "http://localhost:8765")
_SPEAKER      = "media_player.google_speaker"
_DEFAULT_VOICE = "rachel"


@service
async def test_elevenlabs():
    """Quick test: generates and plays a short clip via the audio server."""
    log.warning("EL_TEST: starting...")

    try:
        await hass.services.async_call("media_player", "volume_set", {
            "entity_id": _SPEAKER, "volume_level": 0.3
        })
        await task.sleep(0.3)
    except Exception as e:
        log.warning(f"EL_TEST: volume_set failed: {e}")

    tts_url = f"{_AUDIO_SERVER}/tts?text=Hola%2C+esto+es+una+prueba+de+ElevenLabs.&voice=rachel"
    try:
        session = aiohttp_client.async_get_clientsession(hass)
        async with session.get(tts_url, timeout=20) as resp:
            data = await resp.json()
            audio_url = data.get("url")
            log.warning(f"EL_TEST: audio URL = {audio_url}")
    except Exception as e:
        log.error(f"EL_TEST: server call failed: {e}")
        return

    if audio_url:
        try:
            await hass.services.async_call("media_player", "play_media", {
                "entity_id": _SPEAKER,
                "media_content_id": audio_url,
                "media_content_type": "audio/mp3",
            })
            log.warning("EL_TEST: play_media called OK!")
        except Exception as e:
            log.error(f"EL_TEST: play_media failed: {e}")


@service
async def speak_elevenlabs(msg: str, voice: str = _DEFAULT_VOICE, volume: float = 0.7, force: bool = False):
    """
    ElevenLabs TTS on Google Speaker via home server audio API.

    Args:
        msg:    Text to speak (auto-split at sentence boundaries)
        voice:  rachel | jessica | matilda | roger | adam | george
        volume: 0.0–1.0 (default 0.7)
        force:  Bypass house mode TTS policy
    """
    import re

    # Policy check
    try:
        from common_utils import get_tts_policy
        should_speak, vol_cap = get_tts_policy(force=force)
        if not should_speak:
            log.info("speak_elevenlabs: skipped (mode policy)")
            return
        if vol_cap is not None:
            volume = min(volume, vol_cap)
    except Exception as e:
        log.warning(f"speak_elevenlabs: policy check error ({e}), proceeding")

    # Set volume
    try:
        await hass.services.async_call("media_player", "volume_set", {
            "entity_id": _SPEAKER, "volume_level": volume
        })
        await task.sleep(0.3)
    except Exception as e:
        log.warning(f"speak_elevenlabs: volume_set failed: {e}")

    # Split into sentences
    chunks = [s.strip() for s in re.split(r'(?<=[.!?])\s+', msg) if s.strip()] or [msg]
    log.info(f"speak_elevenlabs: {len(chunks)} chunk(s), voice={voice}, vol={volume}")

    session = aiohttp_client.async_get_clientsession(hass)

    for chunk in chunks:
        encoded = chunk.replace(" ", "+").replace(",", "%2C").replace(".", "%2E").replace("!", "%21").replace("?", "%3F")
        tts_url = f"{_AUDIO_SERVER}/tts?text={encoded}&voice={voice}"

        try:
            async with session.get(tts_url, timeout=20) as resp:
                if resp.status != 200:
                    log.error(f"speak_elevenlabs: server returned {resp.status}")
                    continue
                data = await resp.json()
                audio_url = data.get("url")
        except Exception as e:
            log.error(f"speak_elevenlabs: server call failed: {e}")
            continue

        if not audio_url:
            log.error("speak_elevenlabs: no URL in server response")
            continue

        try:
            await hass.services.async_call("media_player", "play_media", {
                "entity_id": _SPEAKER,
                "media_content_id": audio_url,
                "media_content_type": "audio/mp3",
            })
            log.info(f"speak_elevenlabs: playing {audio_url}")
        except Exception as e:
            log.error(f"speak_elevenlabs: play_media failed: {e}")
            continue

        # Wait for playback
        wait = max(2.5, len(chunk.split()) * 0.4 + 1.5)
        await task.sleep(wait)
