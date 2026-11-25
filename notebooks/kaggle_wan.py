"""Run on Kaggle (GPU: 2x T4) or Colab. Animates each keyframe with Wan 2.2 TI2V-5B (image-to-video).

SETUP (once, in notebook cells):
    !git clone https://github.com/Wan-Video/Wan2.2.git && cd Wan2.2 && pip install -r requirements.txt
    !huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./Wan2.2-TI2V-5B
UPLOAD: storyboard.json + outputs/keyframes/*.png as a Kaggle dataset (path below), then run this file.
DOWNLOAD: /kaggle/working/wan/sNN.mp4 -> copy into outputs/wan/ in your repo, then `make shots`.

This script follows the official Wan2.2 README command for TI2V-5B. Check the README for flags that changed.
It saves after every shot and skips finished ones, because Kaggle sessions time out. Log GPU minutes in COSTS.md.
Prompt = motion + camera only (the keyframe already holds the subject).
"""
import json, os, subprocess, time
from pathlib import Path

DATA = Path(os.environ.get("DATA", "/kaggle/input/lamp-keyframes"))
OUT = Path("/kaggle/working/wan"); OUT.mkdir(parents=True, exist_ok=True)
SIZE = os.environ.get("SIZE", "1280*704")       # try a smaller size for drafts if you hit OOM / quota limits
FRAMES = os.environ.get("FRAMES", "121")        # ~5 s at 24 fps; fewer frames = faster
ONLY = os.environ.get("ONLY")                   # e.g. ONLY=s03 to redo one shot

sb = json.loads((DATA / "storyboard.json").read_text(encoding="utf-8"))
for s in sb["shots"]:
    sid = s["id"]
    if ONLY and sid != ONLY: continue
    dst = OUT / f"{sid}.mp4"
    if dst.exists(): print(sid, "exists, skipped"); continue
    t0 = time.time()
    cmd = ["python", "generate.py", "--task", "ti2v-5B", "--size", SIZE, "--ckpt_dir", "./Wan2.2-TI2V-5B",
           "--offload_model", "True", "--convert_model_dtype", "--t5_cpu", "--frame_num", FRAMES,
           "--image", str(DATA / "keyframes" / f"{sid}.png"), "--prompt", s["motion_prompt"],
           "--base_seed", str(s["seed"]), "--save_file", str(dst)]
    r = subprocess.run(cmd, cwd="Wan2.2")
    mins = round((time.time() - t0) / 60, 2)
    with open(OUT / "wan_runs.jsonl", "a") as f:     # copy these lines into the repo's runs.jsonl
        f.write(json.dumps({"stage": "wan", "shot": sid, "model": "Wan2.2-TI2V-5B", "size": SIZE, "frames": FRAMES,
                            "seed": s["seed"], "gpu_minutes": mins, "ok": r.returncode == 0}) + "\n")
    print(sid, "done" if r.returncode == 0 else "FAILED", mins, "min")
