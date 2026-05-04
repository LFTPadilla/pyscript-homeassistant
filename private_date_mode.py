import requests
import json
import time

import os
HA_URL = os.environ.get("HA_URL", "http://localhost:8123/api")
TOKEN = os.environ.get("HA_TOKEN", "")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def call_service(domain, service, data):
    url = f"{HA_URL}/services/{domain}/{service}"
    try:
        response = requests.post(url, headers=HEADERS, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error calling {domain}.{service}: {e}")
        return False

def activate_date_mode():
    print("🌹 Activando Modo Cita (Privado)...")

    # 1. Apagar luces principales
    call_service("light", "turn_off", {
        "entity_id": ["light.kitchen_light", "light.entryway_light", "light.bathroom_light"]
    })

    # 2. Configurar luces ambientales a rojo / cálido
    # Sala y cuarto en rojo, brillo bajo/medio
    romantic_light_data = {
        "entity_id": ["light.livingroom_light", "light.bedroom_light", "light.desktop_strip_light"],
        "color_name": "red",
        "brightness_pct": 30,
        "transition": 3
    }
    call_service("light", "turn_on", romantic_light_data)

    # 3. Poner música tipo R&B / Lounge en el Google Speaker (opcional)
    # Por ahora solo preparamos el volumen
    call_service("media_player", "volume_set", {
        "entity_id": "media_player.google_speaker",
        "volume_level": 0.3
    })
    
    # 4. Iniciar música de YouTube Music (Neo-Soul / R&B romantic)
    # Playlist ID o stream:
    call_service("media_player", "play_media", {
        "entity_id": "media_player.google_speaker",
        "media_content_id": "https://streams.radiomast.io/ref:b6e9a5b6-cf2e-4d2e-b5e0-36898c498d3b", # Placeholder, pero pondrá ambiente
        "media_content_type": "music"
    })

    print("✅ Modo Cita activado correctamente.")

if __name__ == "__main__":
    activate_date_mode()
