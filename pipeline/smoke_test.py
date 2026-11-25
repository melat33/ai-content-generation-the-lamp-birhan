"""Smoke test: call each provider once, log latency to runs.jsonl. Run this first (make smoke)."""
import os, shutil, time
from common import *


def timed(name, fn):
    t0 = time.time()
    try:
        fn(); ok, err = True, None
    except Exception as e:
        ok, err = False, str(e)[:200]
    lat = round(time.time() - t0, 2)
    log_run(stage="smoke", provider=name, ok=ok, latency_s=lat, error=err)
    hint = ""
    if not ok and "503" in (err or ""): hint = "  <- Google is busy, try again in a few minutes"
    if not ok and "401" in (err or ""): hint = "  <- token rejected: re-check CF_API_TOKEN and its Workers AI permission"
    print(f"{'OK  ' if ok else 'FAIL'} {name:<22} {lat}s {err or ''}{hint}")


def gemini_text():
    from google import genai
    c = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    c.models.generate_content(model=os.environ.get("TEXT_MODEL", "gemini-3.8-flash"), contents="Say OK")


def gemini_tts():
    gemini_tts_rest("ሰላም", "calm and warm", "Kore", os.environ.get("TTS_MODEL", "gemini-3.8-flash-tts"))


def cloudflare():
    import requests
    m = os.environ.get("KEYFRAME_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/ai/run/{m}",
        headers={"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}, json={"prompt": "a brass lamp", "steps": 2}, timeout=120)
    r.raise_for_status()


print("ffmpeg:", "found" if shutil.which("ffmpeg") else "MISSING (install it)")
timed("gemini text", gemini_text)
timed("gemini tts (amharic)", gemini_tts)
timed("cloudflare flux", cloudflare)
print("Kaggle (Wan 2.2) and ACE-Step run in notebooks: open notebooks/ and log the first GPU run in COSTS.md.")