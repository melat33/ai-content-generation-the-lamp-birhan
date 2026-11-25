"""Assembly stage (all FFmpeg + numpy, deterministic): picture + narration + ambience + score -> final MP4s.

  * timeline from narration lengths; subtitles (English) burned in, <=2 lines of <=32 chars, inside the safe area
  * stems normalised separately, score DUCKED under the voice (sidechaincompress 0.02 / 6 / 300 ms / 1500 ms)
  * two-pass loudnorm to -14 LUFS, true peak -1 dB
  * end card ("Made with AI") appended, exports 9:16 and 16:9
  python pipeline/assemble.py
"""
import json, re, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from common import *

BUILD = OUT / "build"; FINAL = OUT / "final"
VOICE_DB, MUSIC_DB, AMB_DB = -20.0, -25.0, -30.0


def build_stems(sb, tl, total, with_ambience=True):
    n = int(total * SR); BUILD.mkdir(parents=True, exist_ok=True)
    voice = np.zeros(n, dtype=np.float32)
    for r in tl:
        if r["narr"]:
            x = read_wav(r["narr"]); i = int(r["narr_start"] * SR); seg = x[: max(0, n - i)]; voice[i:i + len(seg)] += seg
    act = voice[np.abs(voice) > 0.005]
    if len(act): voice *= 10 ** ((VOICE_DB - rms_db(act)) / 20)
    score = OUT / "music" / "score.wav"
    music = np.zeros(n, dtype=np.float32)
    if score.exists():
        m = read_wav(score)[:n]; music[: len(m)] = m; music = set_rms_db(music, MUSIC_DB)
    amb = np.zeros(n, dtype=np.float32)
    if with_ambience:
        f = int(0.15 * SR)
        for r in tl:
            p = OUT / "ambience" / f"{r['id']}.wav"
            if not p.exists(): continue
            x = read_wav(p).copy(); i = int(r["start"] * SR)
            x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
            seg = x[: max(0, n - i)]; amb[i:i + len(seg)] += seg
        if np.any(amb): amb = set_rms_db(amb, AMB_DB)
    for name, x in (("voice", voice), ("music", music), ("amb", amb)):
        write_wav(BUILD / f"{name}.wav", x)


def mix_and_master(out_wav: Path):
    t0 = time.time()
    fg = ("[0:a]asplit=2[vo][sc];"
          "[1:a][sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[md];"
          "[vo][md][2:a]amix=inputs=3:duration=first:normalize=0,aformat=channel_layouts=stereo[mix]")
    pre = BUILD / "mix_pre.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", BUILD / "voice.wav", "-i", BUILD / "music.wav", "-i", BUILD / "amb.wav",
         "-filter_complex", fg, "-map", "[mix]", pre])
    # two-pass loudnorm
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_LRA={m['input_lra']}:measured_TP={m['input_tp']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", pre, "-af", af, out_wav])
    log_run(stage="assemble", tool="ffmpeg-audio", measured_lufs_before=m["input_i"], measured_tp_before=m["input_tp"],
            target_lufs=-14, latency_s=round(time.time() - t0, 2), cost_usd=0.0, status="ok")
    return m


def srt_time(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s - int(s)) * 1000):03}"


def build_srt(tl, path: Path):
    cues = []
    for r in tl:
        text = r["shot"]["narration"]["en"]
        sents = [x.strip() for x in re.split(r"(?<=[.?!])\s+", text) if x.strip()]
        chunks, cur = [], ""
        for s in sents:   # group sentences so each cue is <= 2 lines of 38 chars
            cand = (cur + " " + s).strip()
            if len(textwrap.wrap(cand, 32)) <= 2: cur = cand
            else: chunks.append(cur); cur = s
        if cur: chunks.append(cur)
        t0 = r["narr_start"]; span = r["narr_len"] if r["narr_len"] > 0 else max(1.0, r["dur"] - LEAD - TAIL)
        tot = sum(len(c) for c in chunks)
        for c in chunks:
            d = span * len(c) / tot
            cues.append((t0, t0 + d, "\n".join(textwrap.wrap(c, 32)[:2]))); t0 += d
    path.write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b - 0.05)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")


def font(size, ethiopic=False):
    p = find_font() if ethiopic else None
    for cand in ([p] if p else []) + ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf", "Arial.ttf"]:
        try: return ImageFont.truetype(cand, size)
        except Exception: continue
    return ImageFont.load_default()


def end_card(sb, W, H, path: Path):
    """End card: ONE line only, 'Made with AI by <author>' (the AI disclosure is required by the challenge)."""
    img = Image.new("RGB", (W, H), (18, 22, 38)); d = ImageDraw.Draw(img)
    text = "Made with AI" + (f" by {sb['author']}" if sb.get("author") else "")
    size = int(W * 0.09)
    while size > 20:                       # shrink until the line fits inside 88% of the width
        f = font(size)
        if d.textlength(text, font=f) <= W * 0.88: break
        size -= 2
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, H / 2 - size / 2), text, font=f, fill=(255, 255, 255))
    img.save(path)


def encode_endcard(png, out, dur=ENDCARD_S):
    vf = f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur - 0.5}:d=0.5,format=yuv420p"
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", 1, "-i", png, "-t", dur, "-vf", vf, "-r", FPS, "-c:v", "libx264", "-crf", 20, "-preset", "veryfast", out])


def render(sb, tl, a, W, H, audio, total):
    t0 = time.time()
    clips = [OUT / "shots" / f"{r['id']}_{a}.mp4" for r in tl]
    png, card = BUILD / f"endcard_{a}.png", BUILD / f"endcard_{a}.mp4"
    end_card(sb, W, H, png); encode_endcard(png, card)
    lst = BUILD / f"list_{a}.txt"; lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips + [card]))
    # libass sizes are in a 288-unit-high script space (PlayResY=288), so: v ~53 px font, ~330 px from bottom; h ~45 px, ~64 px
    fs, mv, ol = (8, 49, 1.6) if H > W else (12, 10, 1.4)
    style = f"FontName=DejaVu Sans,FontSize={fs},PrimaryColour=&H00FFFFFF,OutlineColour=&H90000000,BorderStyle=1,Outline={ol},Shadow=0,Alignment=2,MarginV={mv}"
    out = FINAL / ("film_9x16.mp4" if a == "v" else "film_16x9.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", 0, "-i", lst.name, "-i", audio.name,
         "-vf", f"subtitles=subs.srt:force_style='{style}'",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", 22, "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-r", FPS,
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
         "-metadata", f"title={sb['title']}", "-metadata", "comment=Made with AI: AI-generated images, narration, music and sound.",
         out.resolve()], cwd=BUILD)
    log_run(stage="assemble", tool="ffmpeg-video", aspect=a, output=out.name, seconds=round(total, 1),
            latency_s=round(time.time() - t0, 2), cost_usd=0.0, status="ok")
    print("wrote", out)


def main():
    sb = load_storyboard(); tl = timeline(sb); total = total_seconds(tl) + ENDCARD_S
    BUILD.mkdir(parents=True, exist_ok=True); FINAL.mkdir(parents=True, exist_ok=True)
    build_stems(sb, tl, total)
    m = mix_and_master(BUILD / "master.wav")
    print(f"audio mastered: {m['input_i']} LUFS -> -14 LUFS, true peak target -1 dB")
    build_srt(tl, BUILD / "subs.srt"); (FINAL / "subs.srt").write_text((BUILD / "subs.srt").read_text(encoding="utf-8"), encoding="utf-8")
    for a, (W, H) in (("v", (1080, 1920)), ("h", (1920, 1080))):
        render(sb, tl, a, W, H, BUILD / "master.wav", total)


if __name__ == "__main__":
    main()