"""Narration stage: storyboard.json -> outputs/narration/sNN.wav (one file per shot).

  python pipeline/narration.py              # all shots, cached shots skipped
  python pipeline/narration.py --shot s03   # one shot
  python pipeline/narration.py --placeholder   # offline demo voice (NOT a real narration)
"""
import argparse, os, sys
import numpy as np
from common import *

MODEL = os.environ.get("TTS_MODEL", "gemini-3.8-flash-tts")   # confirm the current ID in AI Studio
VOICE = os.environ.get("TTS_VOICE", "Kore")
STYLE = os.environ.get("TTS_STYLE",
    "calm, warm and unhurried, like a grandparent telling a story, with a short pause between sentences")


def synth_gemini(client, types, text):
    """Gemini 3.8 TTS via REST: transcript in parts[].text, delivery in speech_metadata.style, voice in speechConfig."""
    return decode_audio(gemini_tts_rest(text, STYLE, VOICE, MODEL))


def decode_audio(data: bytes):
    """Return (float32 mono array, sample_rate). The API may return a WAV container or raw 16-bit 24 kHz PCM."""
    if data[:4] == b"RIFF":
        import io, wave
        with wave.open(io.BytesIO(data), "rb") as w:
            sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
            x = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768.0
        return (x.reshape(-1, ch).mean(axis=1) if ch > 1 else x), sr
    return np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0, 24000


def synth_placeholder(text):
    """Syllable-like hum so ducking can be tested offline. Clearly not speech."""
    rng = np.random.default_rng(len(text))
    secs = max(1.5, len(text) / 11.0)
    t = np.arange(int(secs * 24000)) / 24000
    f0 = 140 + 15 * np.sin(2 * np.pi * 0.4 * t)
    x = np.sin(2 * np.pi * np.cumsum(f0) / 24000) + 0.4 * np.sin(4 * np.pi * np.cumsum(f0) / 24000)
    syll = 0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * t + rng.uniform(0, 6))
    return (0.25 * x * syll ** 1.5).astype(np.float32), 24000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--placeholder", action="store_true")
    args = ap.parse_args()
    demo = demo_mode()

    client = types = None
    if not demo:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY missing. Put it in .env (see .env.example), or run `make demo` for placeholders.")
        pass  # REST call in common.gemini_tts_rest (no SDK needed)

    sb = load_storyboard()
    d = OUT / "narration"; d.mkdir(parents=True, exist_ok=True)
    for s in sb["shots"]:
        if args.shot and s["id"] != args.shot:
            continue
        text = s["narration"]["am"]
        mode = "placeholder" if demo else MODEL
        key = sha(mode, VOICE, STYLE, text)
        wav = d / f"{s['id']}.wav"
        if not args.force and cached(wav, key):
            print(f"[{s['id']}] cached"); continue
        if demo:
            (x, sr), lat, att = synth_placeholder(text), 0.0, 1
        else:
            (x, sr), lat, att = with_retries(lambda: synth_gemini(client, types, text), stage="narration", shot=s["id"], model=MODEL)
        write_wav(wav, x, sr); stamp(wav, key)
        secs = round(len(x) / sr, 2)
        log_run(stage="narration", shot=s["id"], model=mode, voice=VOICE, input_hash=key, chars=len(text),
                audio_seconds=secs, target_seconds=s["duration_s"], latency_s=lat, cost_usd=0.0, attempt=att, status="ok")
        print(f"[{s['id']}] audio={secs}s target={s['duration_s']}s")


if __name__ == "__main__":
    main()