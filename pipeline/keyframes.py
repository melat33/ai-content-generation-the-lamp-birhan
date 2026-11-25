"""Keyframe stage: storyboard.json -> outputs/keyframes/sNN.png (square 1024, subject centred so 9:16 and 16:9 crops both work).

  python pipeline/keyframes.py --reference   # reference sheet first (look + symbol), approve it by eye
  python pipeline/keyframes.py               # every shot (cached shots skipped)
  python pipeline/keyframes.py --shot s05
  python pipeline/keyframes.py --placeholder # painted placeholders, no API (demo only)
"""
import argparse, base64, io, os, sys
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter
from common import *

MODEL = os.environ.get("KEYFRAME_MODEL", "@cf/black-forest-labs/flux-1-schnell")
STEPS = int(os.environ.get("KEYFRAME_STEPS", "4"))
SIZE = 1024


def full_prompt(sb, shot_prompt):
    return f"{shot_prompt}. Featuring {sb['reference']['symbol']}. {sb['style_block']}"


def cloudflare(prompt):
    acc, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not (acc and tok):
        sys.exit("CF_ACCOUNT_ID / CF_API_TOKEN missing (see .env.example), or run `make demo`.")
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODEL}",
                      headers={"Authorization": f"Bearer {tok}"}, json={"prompt": prompt, "steps": STEPS}, timeout=120)
    r.raise_for_status()
    img = r.json()["result"]["image"]
    return Image.open(io.BytesIO(base64.b64decode(img))).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)


# ---- placeholder painter: stylised silhouettes, clearly labelled ----
PALETTE = {"built": ((250, 205, 120), (150, 70, 40)), "fall": ((120, 120, 125), (35, 35, 45)),
           "question": ((255, 215, 140), (90, 60, 50))}


def placeholder(shot, label):
    top, bot = PALETTE[shot["act"]]
    y = np.linspace(0, 1, SIZE)[:, None, None]
    arr = (np.array(top) * (1 - y) + np.array(bot) * y) * np.ones((1, SIZE, 1))
    img = Image.fromarray(arr.astype("uint8"), "RGB")
    d = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(shot["seed"])
    # ground
    d.rectangle([0, 760, SIZE, SIZE], fill=(25, 18, 15, 230))
    # simple silhouettes by shot id
    sid = int(shot["id"][1:])
    if sid in (1, 10):    # rock church: block with cross cut-out
        d.rectangle([330, 430, 700, 790], fill=(20, 14, 12, 255)); d.rectangle([500, 520, 530, 700], fill=(240, 190, 110, 255)); d.rectangle([465, 570, 565, 598], fill=(240, 190, 110, 255))
    elif sid == 3:        # crowd + banners
        for i in range(24):
            x = 120 + i * 33; d.ellipse([x, 700, x + 26, 726], fill=(20, 14, 12, 255)); d.rectangle([x + 6, 726, x + 20, 790], fill=(20, 14, 12, 255))
        d.rectangle([300, 520, 306, 720], fill=(20, 14, 12, 255)); d.polygon([(306, 520), (420, 545), (306, 575)], fill=(200, 60, 40, 255))
    elif sid in (2, 4, 9):   # table / figures
        d.rectangle([250, 640, 780, 665], fill=(20, 14, 12, 255)); d.rectangle([280, 665, 300, 790], fill=(20, 14, 12, 255)); d.rectangle([730, 665, 750, 790], fill=(20, 14, 12, 255))
        for x in (380, 640):
            d.ellipse([x, 500, x + 60, 560], fill=(20, 14, 12, 255)); d.rectangle([x - 10, 560, x + 70, 640], fill=(20, 14, 12, 255))
    elif sid in (6,):     # empty desks
        for r in range(3):
            for c in range(4):
                x = 200 + c * 160 + r * 25; yy = 600 + r * 60; d.rectangle([x, yy, x + 110, yy + 14], fill=(15, 12, 12, 255)); d.rectangle([x + 8, yy + 14, x + 16, yy + 55], fill=(15, 12, 12, 255))
    elif sid == 7:        # suitcase
        d.rectangle([380, 650, 640, 790], fill=(18, 12, 10, 255)); d.rectangle([480, 625, 540, 650], fill=(18, 12, 10, 255))
    elif sid == 8:        # lone path
        d.polygon([(480, 560), (545, 560), (760, 1024), (270, 1024)], fill=(55, 48, 42, 255))
    # lamp glow in centre (the thread)
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    lx, ly = SIZE // 2, 640 if sid not in (5, 9, 10) else 560
    for r, a in ((260, 40), (170, 70), (100, 110), (55, 170)):
        g.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(255, 200, 110, a if shot["act"] != "fall" or sid == 5 else a // 3))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(img); d.ellipse([lx - 16, ly - 22, lx + 16, ly + 10], fill=(255, 225, 150, 255)); d.rectangle([lx - 22, ly + 10, lx + 22, ly + 26], fill=(150, 100, 40, 255))
    arr = np.array(img.convert("RGB")).astype(np.float32) + rng.normal(0, 6, (SIZE, SIZE, 1))
    img = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))
    ImageDraw.Draw(img).text((14, SIZE - 24), f"PLACEHOLDER {label}", fill=(255, 255, 255))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--reference", action="store_true"); ap.add_argument("--placeholder", action="store_true")
    args = ap.parse_args()
    demo = demo_mode()
    sb = load_storyboard()
    (OUT / "keyframes").mkdir(parents=True, exist_ok=True); (OUT / "reference").mkdir(parents=True, exist_ok=True)

    jobs = []
    if args.reference:
        jobs.append(("reference", sb["reference"]["prompt"] + ". " + sb["style_block"], sb["reference"]["seed"], OUT / "reference" / "reference.png", None))
    else:
        for s in sb["shots"]:
            if args.shot and s["id"] != args.shot:
                continue
            jobs.append((s["id"], full_prompt(sb, s["image_prompt"]), s["seed"], OUT / "keyframes" / f"{s['id']}.png", s))

    for sid, prompt, seed, path, shot in jobs:
        mode = "placeholder" if demo else MODEL
        key = sha(mode, prompt, seed, STEPS, SIZE)
        if not args.force and cached(path, key):
            print(f"[{sid}] cached"); continue
        if demo:
            img, lat, att = placeholder(shot or {"act": "built", "seed": seed, "id": "s01"}, sid), 0.0, 1
        else:
            img, lat, att = with_retries(lambda: cloudflare(prompt), stage="keyframes", shot=sid, model=MODEL)
        img.save(path); stamp(path, key)
        log_run(stage="keyframes", shot=sid, model=mode, seed=seed, steps=STEPS, prompt=prompt, input_hash=key,
                latency_s=lat, cost_usd=0.0, attempt=att, status="ok")
        print(f"[{sid}] done ({lat}s)")


if __name__ == "__main__":
    main()
