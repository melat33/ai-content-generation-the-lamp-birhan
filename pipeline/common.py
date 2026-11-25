"""Shared helpers: contract loading, hashing/caching, logging, retries, audio I/O, timeline."""
import hashlib, json, os, subprocess, sys, time, wave
from math import gcd
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SB_PATH = ROOT / "storyboard.json"
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
OUT = ROOT / "outputs"
RUNS = ROOT / "runs.jsonl"

SR = 44100          # internal sample rate for all audio
FPS = 24
LEAD = 0.6          # seconds of picture before narration starts in a shot
TAIL = 0.5          # seconds of picture after narration ends
ENDCARD_S = 3.0


def load_dotenv():
    """Tiny .env reader so keys never need to live in code. Handles Windows BOM, spaces and quotes."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v:
                    os.environ.setdefault(k.strip(), v)


load_dotenv()


def demo_mode(argv=None) -> bool:
    return os.environ.get("DEMO") == "1" or "--placeholder" in (argv or sys.argv)


def load_storyboard() -> dict:
    import jsonschema
    sb = json.loads(SB_PATH.read_text(encoding="utf-8-sig"))   # tolerate a Windows BOM
    jsonschema.validate(sb, json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig")))
    return sb


def sha(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def log_run(**kw):
    """One line per model call / tool run in runs.jsonl."""
    kw = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **kw}
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def cached(out: Path, key: str) -> bool:
    stamp = out.with_suffix(out.suffix + ".hash")
    return out.exists() and stamp.exists() and stamp.read_text() == key


def stamp(out: Path, key: str):
    out.with_suffix(out.suffix + ".hash").write_text(key)


def with_retries(fn, *, tries=3, stage="", shot=None, **meta):
    """Run fn() with exponential backoff; every failure is logged. Returns (result, latency_s, attempt)."""
    last = None
    for attempt in range(1, tries + 1):
        t0 = time.time()
        try:
            res = fn()
            return res, round(time.time() - t0, 2), attempt
        except Exception as e:  # quota, network, model errors
            last = e
            log_run(stage=stage, shot=shot, status="error", attempt=attempt, error=str(e)[:300], **meta)
            print(f"  [{shot or stage}] attempt {attempt}/{tries} failed: {str(e)[:160]}")
            if attempt < tries:
                # free-tier rate limits (429) reset per minute: wait it out instead of burning the retries
                wait = 50 if "429" in str(e) else 2 ** attempt
                if wait > 10: print(f"  waiting {wait}s for the rate limit to reset...")
                time.sleep(wait)
    raise RuntimeError(f"{stage} {shot or ''} failed after {tries} tries: {last}")


def run(cmd, cwd=None, capture=True):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=capture, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str, cmd))[:200]}\n{(r.stderr or '')[-1500:]}")
    return r


def ffprobe_duration(path: Path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", path])
    return float(r.stdout.strip())


# ---------- audio I/O (16-bit PCM WAV, mono internally) ----------
def read_wav(path: Path, target_sr=SR):
    with wave.open(str(path), "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: expected 16-bit PCM")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != target_sr:
        from scipy.signal import resample_poly
        g = gcd(sr, target_sr)
        x = resample_poly(x, target_sr // g, sr // g).astype(np.float32)
    return x


def write_wav(path: Path, x, sr=SR):
    x = np.nan_to_num(np.asarray(x, dtype=np.float32))
    x = np.clip(x, -1.0, 1.0)
    if x.ndim == 2:
        ch, data = x.shape[1], x
    else:
        ch, data = 1, x
    pcm = (data * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def rms_db(x) -> float:
    r = float(np.sqrt(np.mean(np.square(x)) + 1e-12))
    return 20 * np.log10(r + 1e-12)


def set_rms_db(x, target_db):
    return x * (10 ** ((target_db - rms_db(x)) / 20))


# ---------- timeline: narration length decides how long each shot lives ----------
def timeline(sb: dict) -> list:
    t, rows = 0.0, []
    for s in sb["shots"]:
        wav = OUT / "narration" / f"{s['id']}.wav"
        narr_len = wav_seconds(wav) if wav.exists() else 0.0
        dur = max(float(s["duration_s"]), LEAD + narr_len + TAIL)
        rows.append({"shot": s, "id": s["id"], "start": t, "dur": dur, "narr": wav if wav.exists() else None,
                     "narr_len": narr_len, "narr_start": t + LEAD})
        t += dur
    return rows


def total_seconds(tl) -> float:
    return tl[-1]["start"] + tl[-1]["dur"]


def find_font(prefer=("NotoSansEthiopic", "Abyssinica", "NotoSerifEthiopic")):
    """Look for a font file; users can drop one into assets/fonts/."""
    dirs = [ROOT / "assets" / "fonts", Path("/usr/share/fonts"), Path("/Library/Fonts"),
            Path.home() / "Library/Fonts", Path("C:/Windows/Fonts"), Path.home() / ".fonts"]
    for name in prefer:
        for d in dirs:
            if d.exists():
                for p in d.rglob("*"):
                    if p.suffix.lower() in (".ttf", ".otf") and name.lower() in p.name.lower():
                        return str(p)
    return None


def gemini_tts_rest(text: str, style: str, voice: str, model: str) -> bytes:
    """Gemini 3.8 TTS over plain REST (exactly the documented v1beta request), so it does not depend on the SDK version.
    Returns the audio bytes (a WAV file by default)."""
    import base64, requests
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing (put it in .env)")
    body = {
        "contents": [{"role": "user", "parts": [{"text": text, "speech_metadata": {"style": style}}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"voice": voice}}},
    }
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])