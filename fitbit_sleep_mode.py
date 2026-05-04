"""
Fitbit Sleep → House Mode Integration
======================================
Reads last night's Fitbit sleep data at 06:50 and adjusts the morning
wake-up ambiance based on actual sleep quality.

Sleep quality tiers:
  EXCELLENT  ≥ 7.5h + deep ≥ 60min  → Normal Day mode, energetic lights
  GOOD       ≥ 6.5h                  → Soft morning, warm lights
  POOR       < 6.5h OR deep < 40min  → Ultra-gentle wake-up, dimmer/warmer

Sends a Telegram sleep summary alongside the house adjustment.

Fitbit tokens: ~/.openclaw/workspace/skills/fitbit/tokens.json
"""

import json, urllib.request, urllib.parse, urllib.error, base64, os
from datetime import date, timedelta, datetime

FITBIT_TOKENS_PATH = "/home/felipe/.openclaw/workspace/skills/fitbit/tokens.json"

# Sleep thresholds
EXCELLENT_HOURS   = 7.5
EXCELLENT_DEEP    = 60   # minutes
GOOD_HOURS        = 6.5
POOR_DEEP         = 40   # minutes — below this = poor regardless of total


def _load_tokens():
    with open(FITBIT_TOKENS_PATH) as f:
        return json.load(f)


def _save_tokens(tokens):
    with open(FITBIT_TOKENS_PATH, "w") as f:
        json.dump(tokens, f, indent=2)


def _refresh_token(tokens):
    creds = base64.b64encode(
        f"{tokens['client_id']}:{tokens['client_secret']}".encode()
    ).decode()
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
    }).encode()
    req = urllib.request.Request(
        "https://api.fitbit.com/oauth2/token",
        data=data,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        new = json.loads(resp.read())
    tokens["access_token"] = new["access_token"]
    tokens["refresh_token"] = new.get("refresh_token", tokens["refresh_token"])
    _save_tokens(tokens)
    return tokens


def _fitbit_get(path, tokens):
    """GET Fitbit API, auto-refresh on 401."""
    def _do_request(tok):
        req = urllib.request.Request(
            f"https://api.fitbit.com{path}",
            headers={"Authorization": f"Bearer {tok['access_token']}"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    try:
        return _do_request(tokens)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            tokens = _refresh_token(tokens)
            return _do_request(tokens)
        raise


def _get_sleep_data():
    """Fetch last night's sleep summary from Fitbit."""
    tokens = _load_tokens()
    uid = tokens["user_id"]
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    data = _fitbit_get(f"/1.2/user/{uid}/sleep/date/{yesterday}.json", tokens)

    if not data.get("sleep"):
        return None

    summary = data["summary"]
    total_min   = summary.get("totalMinutesAsleep", 0)
    total_hours = total_min / 60.0
    stages      = summary.get("stages", {})
    deep_min    = stages.get("deep", 0)
    rem_min     = stages.get("rem", 0)
    light_min   = stages.get("light", 0)
    awake_min   = stages.get("wake", 0)

    return {
        "date":        yesterday,
        "total_hours": round(total_hours, 2),
        "deep_min":    deep_min,
        "rem_min":     rem_min,
        "light_min":   light_min,
        "awake_min":   awake_min,
    }


def _classify_sleep(sleep):
    """Return 'excellent', 'good', or 'poor'."""
    if sleep["total_hours"] >= EXCELLENT_HOURS and sleep["deep_min"] >= EXCELLENT_DEEP:
        return "excellent"
    elif sleep["total_hours"] >= GOOD_HOURS and sleep["deep_min"] >= POOR_DEEP:
        return "good"
    else:
        return "poor"


def _apply_morning_ambiance(quality):
    """
    Adjust lights based on sleep quality.
    Uses the same input_number helpers as house_modes.py.
    """
    if quality == "excellent":
        # Bright, energetic morning
        input_number.brightness_lights = 60
        input_number.kelvin_temp       = 4500
        log.info("FitbitSleep: excellent sleep → bright energetic lights (60%, 4500K)")

    elif quality == "good":
        # Warm, comfortable morning
        input_number.brightness_lights = 35
        input_number.kelvin_temp       = 3500
        log.info("FitbitSleep: good sleep → soft warm lights (35%, 3500K)")

    else:  # poor
        # Very gentle, dim and warm — ease into the day
        input_number.brightness_lights = 15
        input_number.kelvin_temp       = 2700
        log.info("FitbitSleep: poor sleep → gentle dim lights (15%, 2700K)")


def _build_summary_message(sleep, quality):
    hours = int(sleep["total_hours"])
    mins  = int((sleep["total_hours"] - hours) * 60)

    quality_emoji = {"excellent": "🌟", "good": "✅", "poor": "⚠️"}[quality]
    quality_label = {"excellent": "Excelente", "good": "Bueno", "poor": "Insuficiente"}[quality]

    ambiance_desc = {
        "excellent": "Luces al 60%, energizantes. ¡A conquistar el día!",
        "good":      "Luces suaves al 35%. Buenos días 👋",
        "poor":      "Luces muy suaves al 15%. Tómatelo con calma esta mañana.",
    }[quality]

    msg = (
        f"😴 *Sueño de anoche ({sleep['date']})*\n\n"
        f"{quality_emoji} Calidad: *{quality_label}*\n"
        f"⏱️ Total: *{hours}h {mins}m*\n"
        f"🌊 Profundo: {sleep['deep_min']} min\n"
        f"🌀 REM: {sleep['rem_min']} min\n"
        f"💡 {ambiance_desc}"
    )

    if quality == "poor":
        msg += "\n\n💡 _Tip: intenta acostarte 30min antes esta noche._"

    return msg


@time_trigger("once(06:50:00)")
def morning_sleep_adjustment():
    """Run at 06:50: fetch Fitbit sleep, adjust house ambiance, notify Felipe."""
    task.unique("fitbit_morning_sleep")

    # Only run if house is in Sleep mode (don't interrupt if already awake)
    current_mode = state.get("input_select.house_mode")
    if current_mode not in ("Sleep", "Night"):
        log.info(f"FitbitSleep: house mode is '{current_mode}', skipping adjustment")

    try:
        sleep = _get_sleep_data()
    except Exception as e:
        log.error(f"FitbitSleep: failed to fetch sleep data — {e}")
        pyscript.notify_coco(
            message="⚠️ No pude obtener datos de sueño de Fitbit esta mañana.",
            title="Fitbit",
            speak=False,
        )
        return

    if sleep is None:
        log.warning("FitbitSleep: no sleep data for yesterday")
        pyscript.notify_coco(
            message="😴 No hay datos de sueño en Fitbit para anoche. ¿Llevaste el reloj puesto?",
            title="Fitbit",
            speak=False,
        )
        return

    quality = _classify_sleep(sleep)
    log.info(f"FitbitSleep: quality={quality}, hours={sleep['total_hours']}, deep={sleep['deep_min']}min")

    # Adjust lights
    _apply_morning_ambiance(quality)

    # Send Telegram summary
    message = _build_summary_message(sleep, quality)
    pyscript.notify_coco(message=message, title="Buenos días 🌅", speak=False)
