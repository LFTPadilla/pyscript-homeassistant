#!/usr/bin/env python3
"""
ElevenLabs Audio Server for Home Assistant
==========================================
Runs on the home server (configured via AUDIO_SERVER_IP env var).
Accepts text → generates ElevenLabs audio → serves MP3.

Endpoints:
  GET /tts?text=Hello&voice=rachel  → generates audio, returns JSON with URL
  GET /audio/<filename>             → serves the MP3 file
  GET /health                       → health check

Usage:
  python3 el_audio_server.py
"""

import http.server
import urllib.parse
import urllib.request
import json
import os
import hashlib
import threading

API_KEY    = os.environ.get("ELEVENLABS_API_KEY", "")
MODEL      = "eleven_multilingual_v2"
SERVER_IP  = os.environ.get("AUDIO_SERVER_IP", "localhost")
PORT       = int(os.environ.get("AUDIO_SERVER_PORT", 8765))
AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "el_audio_cache")
SERVER_URL = f"http://{SERVER_IP}:{PORT}"

VOICES = {
    "rachel":  "EXAVITQu4vr4xnSDxMaL",
    "jessica": "cgSgspJ2msm64kCltF4R",
    "matilda": "XrExE9yKIg1WjnnlVkGX",
    "roger":   "CwhRBWXzGAHq8TQ4Fs17",
    "adam":    "pNInz6obpgDQGcFmaJgB",
    "george":  "JBFqnCBsd6RMkjVDRZzb",
}

os.makedirs(AUDIO_DIR, exist_ok=True)


def generate_audio(text: str, voice: str = "rachel") -> str:
    """Generate audio via ElevenLabs, cache by hash, return URL."""
    voice_id = VOICES.get(voice, VOICES["rachel"])
    cache_key = hashlib.md5(f"{text}|{voice_id}".encode()).hexdigest()[:12]
    filename = f"coco_{cache_key}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    if os.path.exists(filepath):
        print(f"[cache hit] {filename}")
        return f"{SERVER_URL}/audio/{filename}"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.3},
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("xi-api-key", API_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "audio/mpeg")

    with urllib.request.urlopen(req, timeout=15) as resp:
        with open(filepath, "wb") as f:
            f.write(resp.read())

    print(f"[generated] {filename} ({os.path.getsize(filepath)} bytes)")
    return f"{SERVER_URL}/audio/{filename}"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", len(data))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            self.send_json(200, {"status": "ok", "server": f"{SERVER_IP}:{PORT}"})

        elif parsed.path == "/tts":
            text  = params.get("text",  [""])[0]
            voice = params.get("voice", ["rachel"])[0]
            if not text:
                self.send_json(400, {"error": "missing text param"})
                return
            try:
                audio_url = generate_audio(text, voice)
                self.send_json(200, {"url": audio_url, "voice": voice})
            except Exception as e:
                print(f"[error] {e}")
                self.send_json(500, {"error": str(e)})

        elif parsed.path.startswith("/audio/"):
            filename = os.path.basename(parsed.path)
            filepath = os.path.join(AUDIO_DIR, filename)
            if os.path.exists(filepath):
                self.send_file(filepath)
            else:
                self.send_json(404, {"error": "not found"})

        else:
            self.send_json(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"🎙️  ElevenLabs Audio Server running at {SERVER_URL}")
    print(f"   Audio cache: {AUDIO_DIR}")
    print(f"   Test: curl '{SERVER_URL}/tts?text=Hola&voice=rachel'")
    server.serve_forever()
