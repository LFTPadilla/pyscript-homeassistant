#!/usr/bin/env python3
"""
Morning Blinds & Temperature Forecast
Checks today's weather forecast and recommends blind position
to keep apartment in 18-23°C comfort range.
"""

import requests
import json
from datetime import datetime, timezone

import os
HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}

COMFORT_MIN = 18.0
COMFORT_MAX = 23.0
HOT_THRESHOLD = 28.0  # Above this → morning sun will overheat apartment

CONDITION_ICONS = {
    "sunny": "☀️",
    "partlycloudy": "⛅",
    "cloudy": "☁️",
    "rainy": "🌧️",
    "pouring": "⛈️",
    "lightning": "⚡",
    "snowy": "❄️",
    "fog": "🌫️",
    "clear-night": "🌙",
    "windy": "💨",
}

def get_forecast():
    resp = requests.post(
        f"{HA_URL}/api/services/weather/get_forecasts?return_response",
        headers=HEADERS,
        json={"entity_id": "weather.forecast_home", "type": "daily"}
    )
    data = resp.json()
    forecasts = data.get("service_response", {}).get("weather.forecast_home", {}).get("forecast", [])
    if forecasts:
        return forecasts[0]  # Today's forecast
    return None

def get_current_temps():
    indoor = None
    outdoor = None
    try:
        r = requests.get(f"{HA_URL}/api/states/sensor.t_h_sensor_temperature", headers=HEADERS)
        indoor = float(r.json()["state"])
    except:
        pass
    try:
        r = requests.get(f"{HA_URL}/api/states/sensor.exterior_temp_hum_temperature", headers=HEADERS)
        outdoor = float(r.json()["state"])
    except:
        pass
    return indoor, outdoor

def main():
    forecast = get_forecast()
    indoor_now, outdoor_now = get_current_temps()

    if not forecast:
        print("❌ No se pudo obtener el pronóstico del tiempo.")
        return

    temp_max = forecast.get("temperature", 0)
    temp_min = forecast.get("templow", 0)
    condition = forecast.get("condition", "unknown")
    uv_index = forecast.get("uv_index", 0)
    precipitation = forecast.get("precipitation", 0)
    icon = CONDITION_ICONS.get(condition, "🌤️")

    # Decision logic
    is_hot_day = temp_max >= HOT_THRESHOLD
    is_sunny = condition in ["sunny", "partlycloudy"]
    is_rainy = condition in ["rainy", "pouring", "lightning"]

    # Build recommendation
    if is_hot_day and is_sunny:
        blind_rec = "🪟 CIERRA las persianas antes de las 8 AM — el sol de la mañana va a calentar el apartamento fuerte. Ábrelas después de mediodía cuando el sol ya no dé directamente."
        temp_strategy = f"Con {temp_max:.0f}°C de máxima, mantener persianas cerradas puede ahorrar 3-5°C adentro."
        emoji_status = "🔥"
    elif is_hot_day and not is_sunny:
        blind_rec = "🪟 Puedes dejar las persianas semi-abiertas — aunque va a hacer calor, la nubosidad reduce el efecto del sol directo."
        temp_strategy = f"Máxima de {temp_max:.0f}°C pero nublado — ventila con cuidado por la mañana."
        emoji_status = "🌡️"
    elif not is_hot_day and is_rainy:
        blind_rec = "🪟 Deja las persianas abiertas — día lluvioso y fresco, el apartamento se mantendrá solo en rango cómodo."
        temp_strategy = f"Máxima de {temp_max:.0f}°C con lluvia — temperatura ideal para ventilar."
        emoji_status = "🌧️"
    else:
        blind_rec = "🪟 Día tranquilo — puedes abrir las persianas sin problema. La temperatura se mantendrá dentro del rango cómodo."
        temp_strategy = f"Máxima de {temp_max:.0f}°C — condiciones ideales."
        emoji_status = "✅"

    # Build message
    lines = [
        f"🌅 *Buenos días Felipe — Pronóstico del apartamento*",
        f"",
        f"{icon} *Hoy:* {condition.replace('-', ' ').title()} {emoji_status}",
        f"🌡️ *Temperatura:* {temp_min:.0f}°C – {temp_max:.0f}°C",
        f"☔ *Lluvia:* {precipitation:.1f}mm | ☀️ UV: {uv_index:.0f}",
        f"",
    ]

    if indoor_now and outdoor_now:
        lines += [
            f"📊 *Ahora mismo:*",
            f"  • Interior: {indoor_now:.1f}°C",
            f"  • Exterior: {outdoor_now:.1f}°C",
            f"",
        ]

    lines += [
        f"🎯 *Rango objetivo:* {COMFORT_MIN:.0f}°C – {COMFORT_MAX:.0f}°C",
        f"",
        f"{blind_rec}",
        f"",
        f"_{temp_strategy}_",
    ]

    message = "\n".join(lines)
    print(message)

if __name__ == "__main__":
    main()
