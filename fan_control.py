DEVICE_IEEE = "a4:c1:38:f3:f3:c6:73:85"
ENTITY_ID = "light.bathroom_fan_dimmer"
MIN_BRIGHT = 50
MAX_BRIGHT = 255
DEFAULT_BRIGHT = 50

def clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))

def get_current_brightness(entity=ENTITY_ID):
    attrs = state.getattr(entity) or {}
    b = attrs.get("brightness")
    if not isinstance(b, (int, float)):
        return DEFAULT_BRIGHT
    return int(b)

def set_brightness(entity, value):
    value = clamp(value, MIN_BRIGHT, MAX_BRIGHT)
    light.turn_on(entity_id=entity, brightness=value)
    log.info(f"Brightness set to {value}")
    return value

def parse_direction(step_mode):
    # step_mode may be an object with .value, an int, or a string like "up"/"down"
    if hasattr(step_mode, "value"):
        try:
            return int(step_mode.value)
        except Exception:
            return None
    if isinstance(step_mode, (int, float, str)):
        s = str(step_mode).lower()
        if s in ("0", "up", "increase", "in"):
            return 0
        if s in ("1", "down", "decrease", "de"):
            return 1
        try:
            return int(s)
        except Exception:
            return None
    return None

@event_trigger("zha_event")
def handle_fan_knob_events(device_ieee=None, command=None, args=None, **kwargs):
    log.debug(f"command={command} ")
    if device_ieee != DEVICE_IEEE:
        return

    task.unique("handle_fan_knob_events")
    try:
        log.debug(f"Knob event: command={command}, args={args}")

        if command == "toggle":
            try:
                light.toggle(entity_id=ENTITY_ID)
            except Exception as e:
                log.error(f"Knob toggle error: {e}")
            return

        if command == "step" and isinstance(args, list) and len(args) >= 2:
            step_mode = args[0]
            try:
                step = int(args[1])
            except Exception:
                step = 1

            direction = parse_direction(step_mode)
            if direction is None:
                log.warning(f"Unknown step_mode: {step_mode}")
                return

            delta = step if direction == 0 else -step

            try:
                current = get_current_brightness(ENTITY_ID)
                new_value = set_brightness(ENTITY_ID, current + delta)
                # new_value already logged inside set_brightness
            except Exception as e:
                log.error(f"Error adjusting brightness: {e}")
            return

    except Exception as e:
        log.error(f"Knob controller error: {e}")
