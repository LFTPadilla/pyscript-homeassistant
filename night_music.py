"""
night_music.py - Música clásica nocturna automática a las 7 PM

Rota entre 7 géneros/playlists clásicas según el día de la semana.
Usa el Google Speaker (media_player.google_speaker) con streams de radio clásica.
No requiere autenticación, no consume tokens de LLMs.
"""

import datetime

# Streams de radio clásica libre (no requieren auth)
CLASSICAL_STREAMS = {
    0: {  # Domingo
        "name": "Piano Clásico",
        "url": "https://streams.radiomast.io/ref:b6e9a5b6-cf2e-4d2e-b5e0-36898c498d3b"
    },
    1: {  # Lunes
        "name": "Classical KUSC",
        "url": "https://kusc.streamguys1.com/kusc128.mp3"
    },
    2: {  # Martes
        "name": "France Musique",
        "url": "https://icecast.radiofrance.fr/francemusique-midfi.mp3"
    },
    3: {  # Miércoles
        "name": "Radio Swiss Classic",
        "url": "https://stream.srg-ssr.ch/m/rsc_de/mp3_128"
    },
    4: {  # Jueves
        "name": "BBC Radio 3",
        "url": "https://stream.live.vc.bbcmedia.co.uk/bbc_radio_three"
    },
    5: {  # Viernes
        "name": "Classic FM",
        "url": "https://media-ice.musicradio.com/ClassicFMMP3"
    },
    6: {  # Sábado
        "name": "Venice Classic Radio",
        "url": "https://uk2.streamingpulse.com/ssl/vcr1"
    },
}

SPEAKER = "media_player.google_speaker"
VOLUME_NIGHT_MUSIC = 0.25  # Volumen suave para la noche


@time_trigger("cron(0 19 * * *)")
def night_classical_music():
    """Reproduce música clásica a las 7 PM, rotando por género cada día."""
    # Solo activar si el modo de casa no es Sleep ni Away
    house_mode = state.get("input_select.house_mode")
    if house_mode in ["Sleep", "Away"]:
        log.info(f"night_classical_music: Skipping (house_mode={house_mode})")
        return

    # Elegir stream por día de la semana
    day_of_week = datetime.datetime.now().weekday()  # 0=Lun ... 6=Dom (Python)
    # Ajustar: Python usa 0=Lun, el diccionario usa 0=Dom
    # Convertir: (weekday + 1) % 7 => 0=Dom, 1=Lun ... 6=Sáb
    stream_key = (day_of_week + 1) % 7
    stream = CLASSICAL_STREAMS[stream_key]

    log.info(f"night_classical_music: Reproduciendo '{stream['name']}' (día={stream_key})")

    # Bajar el volumen suavemente
    media_player.volume_set(entity_id=SPEAKER, volume_level=VOLUME_NIGHT_MUSIC)

    # Reproducir stream
    media_player.play_media(
        entity_id=SPEAKER,
        media_content_id=stream["url"],
        media_content_type="music"
    )

    log.info(f"night_classical_music: ✅ Reproduciendo en {SPEAKER}")
