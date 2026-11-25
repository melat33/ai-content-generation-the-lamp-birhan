"""Radio cut: narration over the temp score on a black screen. Test this with 3+ people from your audience BEFORE generating pictures.
  python pipeline/radio_cut.py    -> outputs/final/radio_cut.mp4
"""
from assemble import *

def main():
    sb = load_storyboard(); tl = timeline(sb); total = total_seconds(tl)
    BUILD.mkdir(parents=True, exist_ok=True); FINAL.mkdir(parents=True, exist_ok=True)
    build_stems(sb, tl, total, with_ambience=False)
    mix_and_master(BUILD / "radio_master.wav")
    out = FINAL / "radio_cut.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=black:s=640x360:r=24:d={total:.2f}", "-i", BUILD / "radio_master.wav",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", out])
    print(f"wrote {out}  ({total:.0f}s). Play it to 3+ people and write what they said in DESIGN.md")

if __name__ == "__main__":
    main()
