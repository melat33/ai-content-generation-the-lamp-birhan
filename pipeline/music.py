"""Music stage.

Order of preference:
  1. outputs/music/chosen.wav  -> your ACE-Step pick (copy it there; see notebooks/acestep_notes.md)
  2. otherwise a procedural TEMP TRACK (krar-like plucks + pad in D minor pentatonic) so the edit can proceed.
The temp track is a placeholder, say so in COSTS.md / EXPERIMENTS.md if you ship it.

  python pipeline/music.py                 # build/cached temp track or use chosen.wav
  python pipeline/music.py --print-prompt  # caption/metadata to paste into ACE-Step
  python pipeline/music.py --choose outputs/music/candidates/cand2.wav --why "quietest under voice"
"""
import argparse, shutil
import numpy as np
from scipy.signal import butter, sosfilt
from common import *

PENTA = [293.66, 349.23, 392.0, 440.0, 523.25]   # D F G A C (D minor pentatonic)


def pluck(freq, dur, rng, decay=0.9965):
    n = int(SR * dur); N = max(2, int(SR / freq)); buf = list(rng.uniform(-1, 1, N)); out = np.empty(n)
    for i in range(n):
        j = i % N; out[i] = buf[j]; buf[j] = decay * 0.5 * (buf[j] + buf[(j + 1) % N])
    return out


def temp_track(sb, tl, total):
    rng = np.random.default_rng(sb["music"]["seed"]); bpm = sb["music"]["bpm"]; beat = 60 / bpm
    n = int(total * SR); x = np.zeros(n + SR * 3)
    # pad level per shot (the emotional arc lives in the storyboard acts)
    level = {"built": 0.55, "fall": 0.18, "question": 0.5}
    xs = [r["start"] for r in tl] + [total]
    ys = [level[r["shot"]["act"]] for r in tl] + [0.1]
    env = np.interp(np.arange(n) / SR, xs, ys)
    t = np.arange(n) / SR
    pad = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * a for f, a in ((73.4, 0.5), (110.0, 0.35), (146.8, 0.3), (174.6, 0.18), (220.0, 0.12)))
    x[:n] += 0.5 * pad * env * (0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * t))
    # plucks follow acts
    for r in tl:
        act = r["shot"]["act"]; step = beat if act != "fall" else beat * 4; tt = r["start"]; k = 0
        while tt < r["start"] + r["dur"]:
            if act == "built":   note = PENTA[[0, 2, 3, 2, 1, 3, 4, 3][k % 8]]
            elif act == "fall":  note = PENTA[[0, 1][k % 2]] / 2
            else:                note = PENTA[[3, 2, 1, 0, 1, 2, 3, 4][k % 8]]
            vel = {"built": 0.5, "fall": 0.25, "question": 0.42}[act] * rng.uniform(0.8, 1.0)
            p = pluck(note, 1.5, rng) * vel; i = int(tt * SR); x[i:i + len(p)] += p
            k += 1; tt += step
    # final chord rings and fades over the end card
    for f in (146.8, 220.0, 293.66, 349.23):
        p = pluck(f, 2.8, rng, 0.9985) * 0.4; i = int((total - 3.2) * SR); x[i:i + len(p)] += p
    x = x[:n]
    x *= np.minimum(1, (total - t) / 2.0)          # fade out
    x *= np.minimum(1, t / 1.0)
    return sosfilt(butter(2, 4500, btype="low", fs=SR, output="sos"), x).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print-prompt", action="store_true"); ap.add_argument("--choose"); ap.add_argument("--why", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sb = load_storyboard(); m = sb["music"]; d = OUT / "music"; d.mkdir(parents=True, exist_ok=True)

    if args.print_prompt:
        print("CAPTION :", m["caption"]); print("INSTRUMENTAL:", m["instrumental"]); print("BPM :", m["bpm"]); print("KEY :", m["key"])
        print("DURATION:", m["duration_s"], "s   (generate 3 seeds; 30-60 s is most stable, join sections if needed)")
        print("CUES BY SHOT:"); [print(f"  {s['id']} ({s['act']}): {s['music_cue']}") for s in sb["shots"]]
        return
    if args.choose:
        shutil.copy(args.choose, d / "chosen.wav")
        with open(ROOT / "EXPERIMENTS.md", "a", encoding="utf-8") as f:
            f.write(f"\n<!-- music choice -->\nChosen score: {args.choose}. Reason: {args.why}\n")
        log_run(stage="music", action="choose", file=args.choose, why=args.why); print("chosen.wav set"); return

    tl = timeline(sb); total = total_seconds(tl) + ENDCARD_S
    out = d / "score.wav"
    chosen = d / "chosen.wav"
    if chosen.exists():
        key = sha("chosen", file_sha(chosen), round(total, 1))
        if args.force or not cached(out, key):
            x = read_wav(chosen); n = int(total * SR)
            x = np.pad(x, (0, max(0, n - len(x))))[:n]; x *= np.minimum(1, (total - np.arange(n) / SR) / 2.5)
            write_wav(out, x); stamp(out, key)
        print("using your chosen ACE-Step track"); log_run(stage="music", model="ace-step (chosen)", input_hash=key, cost_usd=0.0, status="ok"); return
    key = sha("temp", sb["music"], [round(r["dur"], 2) for r in tl], [r["shot"]["act"] for r in tl])
    if not args.force and cached(out, key):
        print("temp track cached"); return
    t0 = time.time(); x = temp_track(sb, tl, total); write_wav(out, x); stamp(out, key)
    log_run(stage="music", model="procedural-temp-track", input_hash=key, latency_s=round(time.time() - t0, 2), cost_usd=0.0, status="ok")
    print(f"temp track written ({total:.1f}s). Replace with an ACE-Step pick: outputs/music/chosen.wav")


if __name__ == "__main__":
    main()
