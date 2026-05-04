"""
Smart Home Demo Sequence
=========================
A dynamic demonstration of all smart home capabilities.
Narrated via Google Speaker (OpenAI TTS) with live device control.

Sections:
  1. Intro + Lights (on/off, brightness, color temp, red mode)
  2. Curtains (living room)
  3. Fans (kitchen extractor + bathroom fan)
  4. Robot vacuum
  5. House modes + Air quality + Energy sensors
  6. Cine mode activation

⚠️  DO NOT run automatically — call pyscript.run_smart_home_demo manually.
"""

from datetime import datetime

# ── Entity IDs ────────────────────────────────────────────────────────────────
ALL_LIGHTS = [
    "light.bathroom_light",
    "light.kitchen_light",
    "light.closet_strip_light",
    "light.bedroom_light",
    "light.livingroom_light",
]
CURTAIN         = "cover.curtain_living_room_curtain"
EXTRACTOR       = "switch.fan_stractor_kitchen"
BATHROOM_FAN    = "switch.100205961c_1"
BATHROOM_DIMMER = "light.bathroom_fan_dimmer"
VACUUM          = "vacuum.robot"
GOOGLE_SPEAKER  = "media_player.google_speaker"
AIR_SENSOR      = "sensor.espdesktop_ens160_air_quality_index"
PM10_SENSOR     = "sensor.espdesktop_pm_10_m"

RED_RGB = [255, 0, 0]
DEMO_FLAG = "input_boolean.demo_smart_home"
_TRIGGER_DEBOUNCE_S = 0.8
_LAST_TRIGGER_TS = 0.0


def _speak(msg: str, pause_after: int = 1, extra_wait: float = 0.0):
    """Speak via Google TTS on Google Speaker."""
    try:
        media_player.volume_set(entity_id=GOOGLE_SPEAKER, volume_level=0.6)
        task.sleep(0.2)
        pyscript.speak(msg=msg, lang='es', force=True)
    except Exception as e:
        log.warning(f"Demo TTS (Google): {e}")

    words = len(msg.split())
    wait = max(1.3, words * 0.27 + 0.8) + pause_after + extra_wait
    task.sleep(wait)


def _lights_on(brightness_pct: int, kelvin: int = None, rgb: list = None):
    b = int(round(255 * brightness_pct / 100))
    for eid in ALL_LIGHTS:
        try:
            if state.get(eid) not in ("unavailable", "unknown"):
                if rgb:
                    light.turn_on(entity_id=eid, brightness=b, rgb_color=rgb)
                elif kelvin:
                    light.turn_on(entity_id=eid, brightness=b, color_temp_kelvin=kelvin)
                else:
                    light.turn_on(entity_id=eid, brightness=b)
        except Exception as e:
            log.warning(f"Demo lights: {eid} — {e}")


def _lights_off():
    for eid in ALL_LIGHTS:
        try:
            if state.get(eid) not in ("unavailable", "unknown"):
                light.turn_off(entity_id=eid)
        except Exception:
            pass


def _demo_enabled() -> bool:
    """Return True only when demo flag is explicitly ON."""
    return state.get(DEMO_FLAG) == "on"


def _snapshot_state():
    """Capture minimal state to restore user environment after demo."""
    snap = {
        "house_mode": state.get("input_select.house_mode"),
        "red_mode": state.get("input_boolean.light_red_mode"),
        "curtain_state": state.get(CURTAIN),
        "lights": {},
    }
    for lid in ALL_LIGHTS:
        try:
            snap["lights"][lid] = {
                "state": state.get(lid),
                "brightness": state.getattr(lid).get("brightness") if state.getattr(lid) else None,
                "kelvin": state.getattr(lid).get("color_temp_kelvin") if state.getattr(lid) else None,
                "rgb": state.getattr(lid).get("rgb_color") if state.getattr(lid) else None,
            }
        except Exception:
            snap["lights"][lid] = {"state": "unknown"}
    return snap


def _restore_snapshot(snap):
    """Restore lights/mode/curtain from snapshot."""
    if not snap:
        return
    try:
        if snap.get("house_mode"):
            input_select.house_mode = snap["house_mode"]
        if snap.get("red_mode") in ("on", "off"):
            input_boolean.light_red_mode = snap["red_mode"]

        for lid, info in (snap.get("lights") or {}).items():
            if info.get("state") == "on":
                kwargs = {"entity_id": lid}
                if info.get("brightness") is not None:
                    kwargs["brightness"] = info["brightness"]
                if info.get("kelvin") is not None:
                    kwargs["color_temp_kelvin"] = info["kelvin"]
                if info.get("rgb") is not None:
                    kwargs["rgb_color"] = info["rgb"]
                light.turn_on(**kwargs)
            elif info.get("state") == "off":
                light.turn_off(entity_id=lid)

        if snap.get("curtain_state") == "open":
            cover.open_cover(entity_id=CURTAIN)
        elif snap.get("curtain_state") == "closed":
            cover.close_cover(entity_id=CURTAIN)
    except Exception as e:
        log.warning(f"Demo restore snapshot: {e}")


def _cleanup_demo_end(force_day: bool = False):
    """Shared cleanup for normal completion or early stop."""
    try:
        input_boolean.light_red_mode = "off"
        if force_day:
            input_select.house_mode = "Day"
        media_player.media_stop(entity_id=GOOGLE_SPEAKER)
        switch.turn_off(entity_id=EXTRACTOR)
        switch.turn_off(entity_id=BATHROOM_FAN)
        light.turn_off(entity_id="light.kitchen_light")
        light.turn_off(entity_id="light.bathroom_light")
        light.turn_off(entity_id="light.bedroom_light")
        switch.turn_off(entity_id="switch.kitchen_filter_plug")
        # Ensure vacuum is silent
        try:
            vacuum.stop(entity_id=VACUUM)
        except Exception:
            pass
        try:
            cover.stop_cover(entity_id=CURTAIN)
        except Exception:
            pass
        input_boolean.turn_off(entity_id=DEMO_FLAG)
    except Exception as e:
        log.warning(f"Demo cleanup: {e}")


def _abort_if_flag_off(snap=None) -> bool:
    """Stop sequence if user toggled demo flag OFF during run."""
    if _demo_enabled():
        return False
    log.info("Demo: stopped because input_boolean.demo_smart_home is OFF")
    _cleanup_demo_end(force_day=False)
    _restore_snapshot(snap)
    return True


@service
def stop_smart_home_demo():
    """
    Stop any running smart home demo immediately.
    Call via: pyscript.stop_smart_home_demo()
    Restores lights to normal Day mode.
    """
    task.unique("smart_home_demo", kill_me=True)
    log.info("Demo: Stopped by user request.")
    # Restore safe state
    _cleanup_demo_end(force_day=True)


@state_trigger("input_boolean.demo_smart_home")
def demo_smart_home_flag_trigger(value=None, old_value=None):
    """Start/stop demo from input_boolean.demo_smart_home (debounced)."""
    global _LAST_TRIGGER_TS
    try:
        now_ts = datetime.now().timestamp()
        if value == old_value:
            return
        if (now_ts - _LAST_TRIGGER_TS) < _TRIGGER_DEBOUNCE_S:
            return
        _LAST_TRIGGER_TS = now_ts

        if value == "on":
            log.info("Demo trigger: input_boolean.demo_smart_home -> ON")
            pyscript.run_smart_home_demo()
        elif value == "off":
            log.info("Demo trigger: input_boolean.demo_smart_home -> OFF")
            pyscript.stop_smart_home_demo()
    except Exception as e:
        log.warning(f"Demo trigger error: {e}")


@service
def run_smart_home_demo():
    """
    Execute the full smart home demo sequence.
    Call via: pyscript.run_smart_home_demo()
    """
    task.unique("smart_home_demo")
    log.info("Demo: Starting smart home demonstration sequence")

    # Raise run flag (source of truth for whether demo should keep running)
    try:
        input_boolean.turn_on(entity_id=DEMO_FLAG)
    except Exception as e:
        log.warning(f"Demo flag turn_on failed ({DEMO_FLAG}): {e}")

    if not _demo_enabled():
        log.warning("Demo aborted: input_boolean.demo_smart_home is not ON")
        return

    # Save current state to restore at the end
    demo_snapshot = _snapshot_state()
    prev_mode = state.get("input_select.house_mode")

    # ── INTRO + LIGHTS OPEN ───────────────────────────────────────────────────
    _speak(
        "Iniciando demostración del hogar inteligente. Empecemos con las luces. Enciendo todas las luces de la casa al máximo brillo.",
        pause_after=2
    )
    _lights_on(100, kelvin=5000)
    task.sleep(2)
    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 1: LIGHTS ─────────────────────────────────────────────────────

    # Warm color transition
    _speak("Ahora cambio la temperatura de blanco frío a luz cálida.", pause_after=1)
    _lights_on(50, kelvin=2700)
    task.sleep(3)

    # Red mode
    _speak("Y ahora modo rojo, el color ideal para la noche el cual protege la producción de melatonina y mejora el sueño.", pause_after=1)
    input_boolean.light_red_mode = "on"
    _lights_on(20, rgb=RED_RGB)
    task.sleep(3)

    # Back to normal for demo
    input_boolean.light_red_mode = "off"
    _lights_on(60, kelvin=4000)

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 2: CURTAINS ───────────────────────────────────────────────────
    _speak(
        "También controlo las persianas de la sala. ",
        pause_after=1
    )
    try:
        
        cover.open_cover(entity_id=CURTAIN)
        task.sleep(3)
        cover.close_cover(entity_id=CURTAIN)
        task.sleep(2)
    except Exception as e:
        log.warning(f"Demo curtains: {e}")

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 3: DESK ───────────────────────────────────────────────────────
    _speak("También puedo controlar la altura de tu escritorio inteligente.")
    try:
        switch.turn_off(entity_id="switch.desktop_table_desktop_table_position_2_stand")
        task.sleep(2)
    except Exception as e:
        log.warning(f"Demo desk: {e}")

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 4: FANS ───────────────────────────────────────────────────────
    _speak(
        "Ahora los ventiladores: enciendo el extractor de la cocina y el ventilador del baño.",
        pause_after=1
    )
    try:
        switch.turn_on(entity_id=EXTRACTOR)
        # Kitchen light on while extractor is running
        light.turn_on(entity_id="light.kitchen_light", brightness=180)
        switch.turn_on(entity_id=BATHROOM_FAN)
        light.turn_on(entity_id="light.bathroom_light", brightness=180)
        task.sleep(2)
        # Brightness up on dimmer (represents speed)
        if state.get(BATHROOM_DIMMER) not in ("unavailable", "unknown"):
            light.turn_on(entity_id=BATHROOM_DIMMER, brightness=200)
        task.sleep(2)
    except Exception as e:
        log.warning(f"Demo fans: {e}")

    _speak("Apago los ventiladores.", pause_after=1)
    try:
        switch.turn_off(entity_id=EXTRACTOR)
        light.turn_off(entity_id="light.kitchen_light")
        switch.turn_off(entity_id=BATHROOM_FAN)
        light.turn_off(entity_id="light.bathroom_light")
        light.turn_on(entity_id=BATHROOM_DIMMER, brightness=10)
    except Exception:
        pass
    task.sleep(2)

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 5: ROBOT VACUUM ───────────────────────────────────────────────
    _speak(
        "También controlo el robot aspiradora. Iniciando.",
        pause_after=1
    )
    try:
        light.turn_on(entity_id="light.bedroom_light", brightness=170)
        vacuum.start(entity_id=VACUUM)
        task.sleep(1)

        battery = state.get("sensor.robot_battery") or "?"
        try:
            bnum = float(str(battery))
            battery_speech = str(int(bnum)) if bnum.is_integer() else str(round(bnum, 1)).replace('.', ',')
        except Exception:
            battery_speech = str(battery)
        _speak(f"Batería del robot al {battery_speech} por ciento.", pause_after=1)

        _speak("Lo mando de vuelta a la base.", pause_after=1)
        task.sleep(3)
        vacuum.stop(entity_id=VACUUM)
        light.turn_off(entity_id="light.bedroom_light")
    except Exception as e:
        log.warning(f"Demo vacuum: {e}")

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 6: SENSORS ────────────────────────────────────────────────────
    try:
        aqi = state.get(AIR_SENSOR) or "?"
        pm10 = state.get(PM10_SENSOR) or "?"
        _speak(
            f"También monitoreo la calidad del aire en tiempo real.",
            pause_after=2
        )
    except Exception as e:
        log.warning(f"Demo sensors: {e}")

    _speak(
        "También trackeo el consumo de energía de la nevera, lavadora y lavavajillas, además del consumo de agua.",
        pause_after=1
    )

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── SECTION 7: MODES + CINE ───────────────────────────────────────────────
    _speak(
        "La casa tiene múltiples modos inteligentes como Noche, Lectura, Ausente, Dormir y Cine. Cada uno ajusta luces, automatizaciones y comportamientos.",
        pause_after=2,
        extra_wait=5
    )
    _speak("Activando modo Cine ahora.", pause_after=2)
    if _abort_if_flag_off(demo_snapshot):
        return

    input_select.house_mode = "Cine"
    task.sleep(5)

    _speak(
        "El modo Cine baja la intensidad de las luces, y desactiva automatizaciones de movimiento y notificaciones para no interrumpir.",
        pause_after=1
    )
    _speak("Restaurando el modo anterior.", pause_after=1)

    # Restore previous mode
    restore_mode = prev_mode or "Day"
    input_select.house_mode = restore_mode

    # If we return to Day mode, ensure projector plug is OFF
    if restore_mode == "Day":
        try:
            switch.turn_off(entity_id="switch.kitchen_filter_plug")
        except Exception as e:
            log.warning(f"Demo projector off: {e}")

    if _abort_if_flag_off(demo_snapshot):
        return

    # ── OUTRO ─────────────────────────────────────────────────────────────────
    _speak(
        "Eso fue una muestra del hogar inteligente: todo controlado desde Telegram con Coco, tu asistente.",
        pause_after=2,
        extra_wait=2
    )

    # End cleanly and restore original environment
    _cleanup_demo_end(force_day=False)
    _restore_snapshot(demo_snapshot)

    log.info("Demo: Sequence completed.")
