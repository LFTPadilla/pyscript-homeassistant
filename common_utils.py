"""
Common utilities for PyScript automations.
Shared helpers: notify_coco, brightness helpers, night light parameters,
and centralized house‑mode‑aware TTS services.
"""

# ─── Notification targets ────────────────────────────────────────
NOTIFY_TARGETS = {
    "felipe_phone": "notify.mobile_app_pixel_9_pro",
    "tablet": "notify.mobile_app_galaxy_tab_s8_ultra",
    "watch": "notify.mobile_app_galaxy_watch4_gyqj",
    "valentina_phone": "notify.mobile_app_valentina_phone",
}

# Default target for Felipe
DEFAULT_TARGET = "felipe_phone"

# ─── House Mode TTS Policy ───────────────────────────────────────
# Controls whether speaker announcements are allowed in each mode.
#   tts_allowed : bool  — whether TTS plays at all
#   max_volume  : float — hard cap on volume (None = no cap, use caller's value)
#
# Modes where tts_allowed is False will silently skip all TTS unless
# the caller passes  force=True  (emergency / alarm wake‑up).

HOUSE_MODE_TTS_POLICY = {
    "Day":        {"tts_allowed": True,  "max_volume": None},   # Normal operation
    "Night":      {"tts_allowed": True,  "max_volume": 0.4},    # Lower volume
    "Friends":    {"tts_allowed": True,  "max_volume": None},   # Social, announcements OK
    "Sleep":      {"tts_allowed": False, "max_volume": 0.0},    # Complete silence
    "Away":       {"tts_allowed": False, "max_volume": 0.0},    # Nobody home
    "Cine":       {"tts_allowed": False, "max_volume": 0.0},    # Watching content
    "Reading":    {"tts_allowed": False, "max_volume": 0.0},    # Deep focus
    "Meditation": {"tts_allowed": False, "max_volume": 0.0},    # Complete silence
    "Hug":        {"tts_allowed": False, "max_volume": 0.0},    # Intimate, no interruptions
}


def get_tts_policy(force=False):
    """
    Evaluate TTS policy for the current house mode.

    Args:
        force: Bypass all mode restrictions (for emergencies / alarm wake‑up).

    Returns:
        (should_speak: bool, volume_cap: float | None)
        volume_cap is None when there is no cap.
    """
    if force:
        return (True, None)

    try:
        current_mode = state.get("input_select.house_mode")
    except Exception:
        return (True, None)  # fail‑open: allow TTS if state unavailable

    policy = HOUSE_MODE_TTS_POLICY.get(
        current_mode, {"tts_allowed": True, "max_volume": None}
    )
    return (policy["tts_allowed"], policy["max_volume"])


# ─── Brightness & night‑light helpers ────────────────────────────

def get_night_light_params():
    """Return (brightness_pct, kelvin) suitable for current night‑light preset."""
    return (1, 2200)


def get_brightness_8bit(brightness_pct=None):
    """Convert a 0‑100 brightness percentage to 0‑255 (8‑bit)."""
    if brightness_pct is None:
        try:
            brightness_pct = float(input_number.brightness_lights)
        except Exception:
            brightness_pct = 50
    return int(round(brightness_pct * 255 / 100))


# ─── Structured notification: notify_coco ─────────────────────────

@service
async def notify_coco(
    message: str,
    title: str = "Coco 🏠",
    target: str = "felipe_phone",
    speak: bool = False,
    speak_lang: str = "en",
    speak_volume: float = 0.5,
    critical: bool = False,
):
    """
    Unified notification service — push + optional TTS.

    Push notifications are **always** sent regardless of house mode.
    TTS respects the current house mode policy unless *critical* is True,
    in which case speech is forced through (emergency override).

    Args:
        message:      Notification body text.
        title:        Notification title (default "Coco 🏠").
        target:       'phone', 'tablet', 'watch', or 'all'.
        speak:        Also announce via OpenAI TTS on the Google Speaker.
        speak_lang:   Language for TTS (default 'en').
        speak_volume: Volume 0.0‑1.0 for TTS (default 0.5).
        critical:     High‑priority push AND force TTS even in silent modes.
    """
    # Build the notification data payload
    data = {}
    if critical:
        data["priority"] = "high"
        data["ttl"] = 0
        data["channel"] = "alarm_stream"

    # Resolve targets
    if target == "all":
        targets = list(NOTIFY_TARGETS.values())
    else:
        svc = NOTIFY_TARGETS.get(target)
        if svc is None:
            log.warning(f"notify_coco: unknown target '{target}', falling back to felipe_phone")
            svc = NOTIFY_TARGETS["felipe_phone"]
        targets = [svc]

    # Send push notifications (always, regardless of house mode)
    for svc_name in targets:
        try:
            domain = "notify"
            service = svc_name.split(".")[1]
            await hass.services.async_call(
                domain,
                service,
                {"message": message, "title": title, "data": data},
            )
            log.info(f"notify_coco: sent to {domain}.{service}")
        except Exception as e:
            log.error(f"notify_coco: failed to send to {svc_name} — {e}")

    # Optional TTS announcement — mode‑aware; critical → force bypass
    if speak:
        try:
            await pyscript.speak_openai(
                msg=message, lang=speak_lang, volume=speak_volume, force=critical
            )
        except Exception as e:
            log.error(f"notify_coco: TTS failed — {e}")


# ─── TTS services ────────────────────────────────────────────────

_TTS_SPEAKER = "media_player.google_speaker"


async def _snapshot_speaker_state(entity_id: str):
    """Capture current speaker playback state so TTS can restore/stop correctly."""
    try:
        media_state = state.get(entity_id)
    except Exception:
        media_state = None

    snapshot = {
        "was_playing": media_state == "playing",
        "media_state": media_state,
        "volume_level": None,
    }

    try:
        attrs = state.getattr(entity_id) or {}
        snapshot["volume_level"] = attrs.get("volume_level")
    except Exception:
        pass

    return snapshot


async def _restore_speaker_after_tts(entity_id: str, snapshot: dict):
    """If music was playing before TTS, resume in-place. Otherwise stop the speaker."""
    await task.sleep(0.5)

    try:
        if snapshot.get("volume_level") is not None:
            await hass.services.async_call("media_player", "volume_set", {
                "entity_id": entity_id,
                "volume_level": snapshot["volume_level"],
            })
    except Exception as e:
        log.warning(f"TTS restore: volume restore failed — {e}")

    if snapshot.get("was_playing"):
        try:
            await hass.services.async_call("media_player", "media_play", {"entity_id": entity_id})
            log.info("TTS restore: resumed previous media on Google Speaker")
            return
        except Exception as e:
            log.warning(f"TTS restore: media_play resume failed — {e}")

    try:
        await hass.services.async_call("media_player", "media_stop", {"entity_id": entity_id})
        log.info("TTS restore: speaker was idle before TTS, stopped playback")
    except Exception as e:
        log.warning(f"TTS restore: media_stop failed — {e}")


@service
async def speak(msg: str, lang: str = 'en', force: bool = False):
    """
    Text‑to‑speech via Google Translate + Chime TTS.
    Respects house mode TTS policy unless force=True (emergency override).
    """
    try:
        should_speak, volume_cap = get_tts_policy(force=force)
        if not should_speak:
            current_mode = state.get("input_select.house_mode")
            log.info(f"speak: skipping TTS — house is in {current_mode} mode")
            return

        volume = 0.5
        if volume_cap is not None:
            volume = min(volume, volume_cap)

        await hass.services.async_call("chime_tts", "say", {
            "entity_id": _TTS_SPEAKER,
            "tts_platform": "google_translate",
            "language": lang,
            "tts_speed": 145,
            "volume_level": volume,
            "message": msg,
        })
        log.info(f"TTS: Spoken '{msg[:50]}…'")
    except Exception as e:
        log.error(f"TTS: Failed — {e}")


@service
async def speak_openai(msg: str, lang: str = 'es', volume: float = 0.7, voice: str = 'nova', force: bool = False):
    """
    High‑quality OpenAI TTS on Google Speaker.
    Respects house mode TTS policy unless force=True (emergency override).
    Volume is capped per mode (e.g. Night mode caps at 0.4).
    """
    try:
        should_speak, volume_cap = get_tts_policy(force=force)
        if not should_speak:
            current_mode = state.get("input_select.house_mode")
            log.info(f"speak_openai: skipping TTS — house is in {current_mode} mode")
            return

        speaker_snapshot = await _snapshot_speaker_state(_TTS_SPEAKER)
        if speaker_snapshot.get("was_playing"):
            try:
                await hass.services.async_call("media_player", "media_pause", {"entity_id": _TTS_SPEAKER})
                await task.sleep(0.5)
            except Exception as e:
                log.warning(f"speak_openai: media_pause before TTS failed — {e}")

        # Apply volume cap from mode policy
        if volume_cap is not None:
            volume = min(volume, volume_cap)

        await hass.services.async_call("media_player", "volume_set", {
            "entity_id": _TTS_SPEAKER,
            "volume_level": volume,
        })
        await task.sleep(0.5)

        # Onyx / Male voice — Felipe's preferred TTS entity
        voice_id = 'tts.openai_tts_tts_1_hd_2'

        # NOTE: OpenAI TTS auto-detects language from text — do NOT pass 'language'.
        # Long messages cause garbled audio on Google Speaker; split into chunks.
        import re
        chunks = [s.strip() for s in re.split(r'(?<=[.!?])\s+', msg) if s.strip()]
        if not chunks:
            chunks = [msg]

        for chunk in chunks:
            await hass.services.async_call("tts", "speak", {
                "entity_id": voice_id,
                "media_player_entity_id": _TTS_SPEAKER,
                "message": chunk,
                "options": {"voice": voice if voice in ['alloy','echo','fable','onyx','nova','shimmer'] else 'nova'},
            })
            # ~0.35s per word + 2s speaker buffer between chunks
            chunk_wait = 2 + (len(chunk.split()) * 0.4)
            await task.sleep(chunk_wait)

        await _restore_speaker_after_tts(_TTS_SPEAKER, speaker_snapshot)
        log.info(f"OpenAI TTS: Spoken '{msg[:50]}…' ({lang}, voice={voice}, vol={volume})")
    except Exception as e:
        log.error(f"OpenAI TTS: Failed — {e}")
