import asyncio
import logging
import os
import tempfile
import uuid
import edge_tts
from flask import Flask, request, send_file, jsonify, after_this_request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Voice map: frontend sends a short code (v1-v14), we resolve it to the
# real Edge-TTS voice name here. Full names are also accepted directly as a
# fallback, so nothing breaks if the frontend ever sends the full name instead.
VOICE_MAP = {
    "v1": "my-MM-ThihaNeural",
    "v2": "my-MM-NilarNeural",
    "v3": "it-IT-GiuseppeMultilingualNeural",
    "v4": "en-AU-WilliamMultilingualNeural",
    "v5": "en-US-AndrewMultilingualNeural",
    "v6": "en-US-AvaMultilingualNeural",
    "v7": "en-US-BrianMultilingualNeural",
    "v8": "en-US-EmmaMultilingualNeural",
    "v9": "fr-FR-RemyMultilingualNeural",
    "v10": "fr-FR-VivienneMultilingualNeural",
    "v11": "de-DE-SeraphinaMultilingualNeural",
    "v12": "de-DE-FlorianMultilingualNeural",
    "v13": "pt-BR-ThalitaMultilingualNeural",
    "v14": "ko-KR-HyunsuMultilingualNeural",
}
ALLOWED_VOICE_NAMES = set(VOICE_MAP.values())
TEMP_DIR = tempfile.gettempdir()

def _resolve_voice(raw):
    """Accepts either a short code ('v3') or a full Edge-TTS voice name
    ('it-IT-GiuseppeMultilingualNeural') and returns the full name, or None
    if it doesn't match either."""
    if raw in VOICE_MAP:
        return VOICE_MAP[raw]
    if raw in ALLOWED_VOICE_NAMES:
        return raw
    return None

def _parse_int(value, name, lo, hi):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None, f"'{name}' must be an integer between {lo} and {hi}."
    if not (lo <= v <= hi):
        return None, f"'{name}' must be between {lo} and {hi}, got {v}."
    return v, None

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    text = data.get("text", "")
    if not text.strip():
        return jsonify({"error": "No text provided."}), 400

    voice = _resolve_voice(data.get("voice", "v2"))
    if voice is None:
        return jsonify({"error": "Invalid voice selection."}), 400

    rate, err = _parse_int(data.get("rate", 0), "rate", -50, 50)
    if err: return jsonify({"error": err}), 400

    pitch, err = _parse_int(data.get("pitch", 0), "pitch", -50, 50)
    if err: return jsonify({"error": err}), 400

    rate_str = f"{rate:+d}%"
    pitch_str = f"{pitch:+d}Hz"

    filename = f"tts_{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(TEMP_DIR, filename)

    async def _generate():
        communicate = edge_tts.Communicate(text.strip(), voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_path)

    try:
        asyncio.run(_generate())
    except Exception as e:
        logger.error("TTS error: %s", e)
        if os.path.exists(output_path):
            os.remove(output_path)
        return jsonify({"error": "Audio generation failed."}), 500

    @after_this_request
    def _cleanup(response):
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass
        return response

    return send_file(output_path, mimetype="audio/mpeg", as_attachment=False, download_name="myanmar_tts.mp3")
