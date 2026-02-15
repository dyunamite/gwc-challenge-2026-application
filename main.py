import os
import io
import wave
import numpy as np
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageStat
from pydub import AudioSegment

app = Flask(__name__)

# --- Directory Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PREVIEW_DIR = os.path.join(STATIC_DIR, 'previews')
ASSETS_DIR = os.path.join(STATIC_DIR, 'assets')

for folder in [STATIC_DIR, PREVIEW_DIR, ASSETS_DIR]:
    os.makedirs(folder, exist_ok=True)

# --- Literature Logic ---
ZWSP, ZWNJ, WJ = "\u200B", "\u200C", "\u2060"
PREFIXES = ["un", "re", "in", "im", "dis", "pre", "post", "inter", "over", "under", "mis", "non"]
SUFFIXES = ["ing", "ed", "er", "est", "ly", "tion", "sion", "ment", "ness", "able", "ible", "al", "ize"]

def split_morphemes(word):
    lower = word.lower()
    prefix, suffix, core = "", "", word
    for p in PREFIXES:
        if lower.startswith(p) and len(word) > len(p) + 2:
            prefix, core = word[:len(p)], word[len(p):]
            break
    lower_core = core.lower()
    for s in SUFFIXES:
        if lower_core.endswith(s) and len(core) > len(s) + 2:
            suffix, core = core[-len(s):], core[:-len(s)]
            break
    parts = [p for p in [prefix, core, suffix] if p]
    return parts if parts else [word]

def watermark_text_logic(text):
    words = text.split()
    output_words = []
    pattern = [ZWSP, ZWNJ, WJ]
    for idx, word in enumerate(words):
        parts = split_morphemes(word)
        res = parts[0]
        for i in range(1, len(parts)):
            res += pattern[(idx + i) % 3] + parts[i]
        output_words.append(res)
    return " ".join(output_words)

# --- Music Logic ---
def find_quiet_window_simple(samples, sr, n_channels, search_start, search_end, window_sec=2):
    window_length = int(window_sec * sr) * n_channels
    hop_size = 1000 * n_channels 
    min_amplitude = float("inf")
    best_start = search_start

    for i in range(search_start, search_end - window_length, hop_size):
        window = samples[i : i + window_length]
        avg_amp = np.mean(np.abs(window))
        if avg_amp < min_amplitude:
            min_amplitude = avg_amp
            best_start = i
    return best_start

# --- Art Logic ---
def get_watermark_regions(img):
    W, H = img.size
    win_w, win_h = int(W * 0.20), int(H * 0.10)
    stride, scored_regions = 40, []
    gray_img = img.convert("L")
    for y in range(0, H - win_h, stride):
        for x in range(0, W - win_w, stride):
            region = gray_img.crop((x, y, x + win_w, y + win_h))
            score = ImageStat.Stat(region).stddev[0]
            scored_regions.append({'pos': (x, y), 'score': score})
    scored_regions.sort(key=lambda x: x['score'])
    return scored_regions[0]['pos'], scored_regions[len(scored_regions)//2]['pos'], scored_regions[-1]['pos'], (win_w, win_h)

def apply_wm(base_img, wm_path, pos, size):
    if not os.path.exists(wm_path): return base_img
    watermark = Image.open(wm_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    canvas = base_img.convert("RGBA")
    canvas.paste(watermark, pos, watermark)
    return canvas.convert("RGB")

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-literature', methods=['POST'])
def upload_literature():
    try:
        data = request.get_json()
        user_text = data.get('text', '')
        if not user_text: return jsonify({"success": False, "error": "No text provided"})
        protected_result = watermark_text_logic(user_text)
        debug_result = (protected_result.replace(ZWSP, '<span class="marker">[ZWSP]</span>')
                                      .replace(ZWNJ, '<span class="marker">[ZWNJ]</span>')
                                      .replace(WJ, '<span class="marker">[WJ]</span>'))
        return jsonify({"success": True, "result": protected_result, "debug": debug_result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/upload-art', methods=['POST'])
def upload_art():
    file = request.files.get('art')
    if not file: return jsonify({"success": False, "error": "No file"})
    img = Image.open(io.BytesIO(file.read())).convert("RGB")
    wm_path = os.path.join(ASSETS_DIR, 'watermark.png')
    p1, p2, p3, size = get_watermark_regions(img)
    previews = []
    for i, pos in enumerate([p1, p2, p3]):
        processed = apply_wm(img, wm_path, pos, size)
        fname = f"opt_{i}.png"
        processed.save(os.path.join(PREVIEW_DIR, fname), "PNG")
        previews.append(f"/static/previews/{fname}")
    return jsonify({"success": True, "preview1": previews[0], "preview2": previews[1], "preview3": previews[2]})

@app.route('/upload-music', methods=['POST'])
def upload_music():
    try:
        file = request.files.get('uploadMusic')
        file = request.files.get('uploadMusic')

        # This check makes the red squiggle go away
        if file and file.filename:
            filename = file.filename.lower()
            # ... put the rest of your audio logic inside this if block ...
        else:
            return jsonify({"success": False, "error": "No file selected"})

        if filename.endswith(".mp3"):
            audio = AudioSegment.from_mp3(file)
            audio_stream = io.BytesIO()
            audio.export(audio_stream, format="wav")
            audio_stream.seek(0)
        elif filename.endswith(".wav"):
            audio_stream = io.BytesIO(file.read())
        else:
            return jsonify({"success": False, "error": "Please upload MP3 or WAV"})

        with wave.open(audio_stream, 'rb') as wav:
            params = wav.getparams()
            n_channels = wav.getnchannels()
            sr = wav.getframerate()
            n_frames = wav.getnframes()
            frames = wav.readframes(n_frames)
            y = np.frombuffer(frames, dtype=np.int16).astype(np.float32).copy()

        total_samples = len(y)
        ten_sec_bound = int(10 * sr) * n_channels

        if total_samples <= (ten_sec_bound * 2):
            return jsonify({"success": False, "error": "Audio too short (min 20s)"})

        start = find_quiet_window_simple(y, sr, n_channels, ten_sec_bound, total_samples - ten_sec_bound)
        watermark_time_sec = (start / n_channels) / sr

        noise_samples = int(2 * sr) * n_channels
        noise = (np.random.normal(0, 1, noise_samples) * 5000).astype(np.float32)

        end_pos = min(start + len(noise), len(y))
        y[start:end_pos] += noise[:(end_pos - start)]
        y = np.clip(y, -32768, 32767).astype(np.int16)

        out_name = "protected_audio.wav"
        out_path = os.path.join(PREVIEW_DIR, out_name)

        with wave.open(out_path, 'wb') as obj:
            obj.setparams(params)
            obj.writeframes(y.tobytes())

        import time
        return jsonify({
            "success": True, 
            "audio_url": f"/static/previews/{out_name}?t={int(time.time())}",
            "timestamp": watermark_time_sec
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)