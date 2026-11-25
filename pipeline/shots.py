"""Moving-shot stage: keyframe (+ optional Wan 2.2 clip) -> outputs/shots/sNN_{v,h}.mp4

For every shot:
  * if outputs/wan/sNN.mp4 exists (rendered on Kaggle, see notebooks/), it is cropped to 9:16 and 16:9 and used;
  * otherwise the keyframe gets a slow Ken Burns move (push-in / pan / static, read from the motion prompt).
Both ratios are cut from the SAME material (subject centred). Colour grade comes from storyboard 'grade'.
Cached by hash of keyframe + clip + duration + motion + grade.
"""
import argparse
from common import *

ASPECTS = {"v": (1080, 1920), "h": (1920, 1080)}
FADE = 0.35


def motion_kind(prompt: str) -> str:
    p = prompt.lower()
    if "pan" in p: return "pan"
    if "static" in p: return "static"
    return "push"


def grade_chain(sat, dur):
    return (f"eq=saturation={sat}:contrast=1.03,vignette=PI/5,"
            f"fade=t=in:st=0:d={FADE},fade=t=out:st={max(0, dur - FADE):.2f}:d={FADE},format=yuv420p")


def kenburns(kf, out, W, H, dur, kind, sat):
    N = int(round(dur * FPS))
    if H > W: crop = "crop=576:1024:224:0"
    else:     crop = "crop=1024:576:0:224"
    if kind == "pan":    z, x, y = "1.12", f"(iw-iw/zoom)*on/{N}", "ih/2-(ih/zoom/2)"
    elif kind == "static": z, x, y = "1.0", "0", "0"
    else:                z, x, y = f"1+0.10*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    vf = f"{crop},scale={int(1.5*W)}:{int(1.5*H)}:flags=lanczos,zoompan=z='{z}':x='{x}':y='{y}':d={N}:s={W}x{H}:fps={FPS}," + grade_chain(sat, dur)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", kf, "-vf", vf, "-frames:v", N, "-c:v", "libx264", "-crf", 20, "-preset", "veryfast", "-r", FPS, out])


def from_clip(clip, out, W, H, dur, sat):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={dur:.2f},trim=duration={dur:.2f},setpts=PTS-STARTPTS," + grade_chain(sat, dur))
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", 0.2, "-i", clip, "-vf", vf, "-an", "-c:v", "libx264", "-crf", 20, "-preset", "veryfast", "-r", FPS, out])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--shot"); ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sb = load_storyboard(); tl = timeline(sb)
    d = OUT / "shots"; d.mkdir(parents=True, exist_ok=True)
    for r in tl:
        s = r["shot"]
        if args.shot and s["id"] != args.shot: continue
        kf = OUT / "keyframes" / f"{s['id']}.png"; clip = OUT / "wan" / f"{s['id']}.mp4"
        if not kf.exists(): raise SystemExit(f"{kf} missing: run keyframes first")
        kind = motion_kind(s["motion_prompt"]); sat = s.get("grade", {}).get("saturation", 1.0)
        src = "wan2.2" if clip.exists() else f"kenburns-{kind}"
        for a, (W, H) in ASPECTS.items():
            out = d / f"{s['id']}_{a}.mp4"
            key = sha(file_sha(kf), file_sha(clip) if clip.exists() else None, round(r["dur"], 2), kind, sat, a)
            if not args.force and cached(out, key):
                print(f"[{s['id']}_{a}] cached"); continue
            t0 = time.time()
            if clip.exists(): from_clip(clip, out, W, H, r["dur"], sat)
            else: kenburns(kf, out, W, H, r["dur"], kind, sat)
            stamp(out, key)
            log_run(stage="shots", shot=s["id"], aspect=a, source=src, dur_s=round(r["dur"], 2), input_hash=key,
                    latency_s=round(time.time() - t0, 2), gpu_minutes=0, cost_usd=0.0, status="ok")
            print(f"[{s['id']}_{a}] {src} {r['dur']:.1f}s")


if __name__ == "__main__":
    main()
