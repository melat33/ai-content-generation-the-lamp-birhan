"""Ambience stage: the sound of each place, synthesised in code (original, no licences, no model quota).

Church bell, choir drone, kebero drum, tsenatsel (sistrum), birds, wind, quill, crowd, aeroplane, flame,
room tone, suitcase latch, footsteps. Each shot lists the layers it wants in storyboard.json.
Output: outputs/ambience/sNN.wav (per shot) -> assemble.py joins them with soft crossfades.

  python pipeline/ambience.py            # all shots (cached shots skipped)
  python pipeline/ambience.py --preview church_bell   # write outputs/ambience/preview_<type>.wav to listen
"""
import argparse
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from common import *


def _n(d): return int(d * SR)
def _t(d): return np.arange(_n(d)) / SR
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, fc, o=2): return sosfilt(butter(o, fc, btype="low", fs=SR, output="sos"), x)
def hp(x, fc, o=2): return sosfilt(butter(o, fc, btype="high", fs=SR, output="sos"), x)
def peak(x, p): return x * (p / (np.max(np.abs(x)) + 1e-9))


def pink(rng, n):
    X = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR); f[0] = f[1]
    return np.fft.irfft(X / np.sqrt(f), n)


def slow_env(rng, n, rate=0.25, depth=0.5):
    """Smooth random amplitude movement (gusts, swells)."""
    k = max(2, int(SR / rate / 4))
    e = lp(rng.standard_normal(n + k), rate, 1)[k:]
    e = e / (np.max(np.abs(e)) + 1e-9)
    return 1 - depth + depth * (0.5 + 0.5 * e)


def reverb(x, rng, secs=1.8, wet=0.3):
    n = _n(secs); ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * secs / 4))
    y = fftconvolve(x, ir)[: len(x)]
    return (1 - wet) * x + wet * peak(y, np.max(np.abs(x)) + 1e-9)


# ---------- generators: (duration_s, rng) -> mono float32 at peak ~0.5 ----------
def church_bell(d, rng):
    """Inharmonic bronze partials, slow decay, struck every ~3 s, through a stone-room reverb."""
    x = np.zeros(_n(d) + SR * 6)
    f0 = 196.0
    ratios = [0.5, 1.0, 1.19, 1.56, 2.0, 2.51, 3.0, 4.1]
    amps = [1.0, 0.8, 0.6, 0.5, 0.4, 0.25, 0.2, 0.1]
    decs = [6.0, 4.5, 3.5, 2.8, 2.2, 1.5, 1.1, 0.8]
    tt = np.arange(SR * 6) / SR
    strike = sum(a * np.sin(2 * np.pi * f0 * r * tt + rng.uniform(0, 6)) * np.exp(-tt / dc) for r, a, dc in zip(ratios, amps, decs))
    strike *= np.minimum(1, tt / 0.004)
    t = 0.25
    while t < d - 0.3:
        i = int(t * SR); x[i:i + len(strike)] += strike * rng.uniform(0.8, 1.0)
        t += rng.uniform(2.6, 3.4)
    x = reverb(lp(x[: _n(d)], 4200), rng, 2.2, 0.35)
    return peak(x, 0.5)


def choir_drone(d, rng):
    """Distant sustained vowel-like pad on D (a nod to church chant; not a voice)."""
    t = _t(d); x = np.zeros_like(t)
    for f in (73.4, 146.8, 220.0, 293.7):
        vib = 1 + 0.004 * np.sin(2 * np.pi * rng.uniform(4.5, 5.8) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        x += sum(np.sin(k * ph) / k for k in range(1, 18))
    y = bp(x, 500, 900) + 0.6 * bp(x, 900, 1500) + 0.4 * lp(x, 300)
    y *= (0.4 + 0.6 * np.minimum(1, t / 1.5)) * np.minimum(1, (d - t) / 1.5)
    return peak(reverb(y, rng, 2.5, 0.4), 0.4)


def kebero(d, rng, bpm=72):
    x = np.zeros(_n(d) + SR); beat = 60 / bpm; pat = [1.0, 0.0, 0.55, 0.8]
    k = 0; t = 0.1
    while t < d:
        a = pat[k % 4]
        if a:
            tt = np.arange(int(0.5 * SR)) / SR
            f = 55 + 45 * np.exp(-tt / 0.05)
            hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.16) + 0.25 * lp(rng.standard_normal(len(tt)), 900) * np.exp(-tt / 0.02)
            i = int(t * SR); x[i:i + len(hit)] += a * hit
        k += 1; t += beat
    return peak(x[: _n(d)], 0.5)


def tsenatsel(d, rng):
    """Sistrum shake: metallic rattle bursts."""
    x = np.zeros(_n(d) + SR); t = 0.3
    while t < d - 0.2:
        L = int(rng.uniform(0.18, 0.3) * SR); tt = np.arange(L) / SR
        burst = hp(rng.standard_normal(L), 3500) * np.exp(-tt / 0.07) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 28 * tt)))
        burst += 0.3 * sum(np.sin(2 * np.pi * f * tt) for f in (3150, 4720, 6300)) * np.exp(-tt / 0.05)
        i = int(t * SR); x[i:i + L] += burst * rng.uniform(0.5, 1)
        t += rng.uniform(0.7, 1.3)
    return peak(x[: _n(d)], 0.35)


def birds(d, rng):
    x = np.zeros(_n(d) + SR); t = rng.uniform(0.1, 0.6)
    while t < d - 0.3:
        base = rng.uniform(2600, 5200)
        for _ in range(rng.integers(2, 6)):
            L = int(rng.uniform(0.05, 0.14) * SR); tt = np.arange(L) / SR
            f = base * (1 + 0.25 * np.sin(2 * np.pi * rng.uniform(6, 14) * tt)) + rng.uniform(-400, 400) * tt / tt[-1]
            ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.abs(np.sin(np.pi * tt / tt[-1]))
            i = int(t * SR); x[i:i + L] += ch; t += L / SR + rng.uniform(0.04, 0.12)
        t += rng.uniform(0.8, 2.6)
    return peak(x[: _n(d)], 0.3)


def wind(d, rng):
    n = _n(d); x = bp(pink(rng, n), 120, 1200) * slow_env(rng, n, 0.3, 0.7)
    return peak(x, 0.4)


def quill(d, rng):
    x = np.zeros(_n(d) + SR); t = 0.2
    while t < d - 0.3:
        L = int(rng.uniform(0.15, 0.45) * SR); tt = np.arange(L) / SR
        s = bp(rng.standard_normal(L), 2500, 7500) * np.abs(np.sin(np.pi * tt / tt[-1])) ** 1.5 * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * rng.uniform(5, 11) * tt)))
        i = int(t * SR); x[i:i + L] += s; t += L / SR + rng.uniform(0.25, 0.9)
    return peak(x[: _n(d)], 0.25)


def crowd(d, rng):
    n = _n(d); x = bp(pink(rng, n), 180, 1800) * slow_env(rng, n, 0.5, 0.5)
    x += 0.4 * bp(pink(rng, n), 500, 2500) * slow_env(rng, n, 0.8, 0.8)
    return peak(x, 0.4)


def plane(d, rng):
    n = _n(d); t = _t(d)
    env = np.exp(-((t - d * 0.55) ** 2) / (2 * (d * 0.22) ** 2))
    x = (lp(rng.standard_normal(n), 260, 3) + 0.4 * bp(rng.standard_normal(n), 400, 1400)) * env
    x += 0.25 * np.sin(2 * np.pi * np.cumsum(70 + 18 * env) / SR) * env
    return peak(x, 0.4)


def flame(d, rng):
    n = _n(d); x = 0.15 * bp(pink(rng, n), 200, 3000) * slow_env(rng, n, 1.5, 0.5)
    for i in rng.integers(0, n, int(d * rng.uniform(3, 7))):
        L = int(rng.uniform(0.004, 0.02) * SR); tt = np.arange(L) / SR
        c = hp(rng.standard_normal(L), 1500) * np.exp(-tt / 0.004) * rng.uniform(0.3, 1)
        x[i:i + L] += c[: max(0, min(L, n - i))] if i + L <= n else 0
    return peak(x, 0.3)


def room_tone(d, rng):
    n = _n(d); t = _t(d)
    x = lp(pink(rng, n), 500) + 0.05 * np.sin(2 * np.pi * 50 * t)   # 50 Hz mains hum
    return peak(x, 0.2)


def latch(d, rng):
    x = np.zeros(_n(d) + SR)
    for frac, f in ((0.42, 1900), (0.5, 1350)):
        L = int(0.12 * SR); tt = np.arange(L) / SR
        c = (np.sin(2 * np.pi * f * tt) * 0.6 + hp(rng.standard_normal(L), 2500) * 0.5) * np.exp(-tt / 0.012)
        i = int(frac * d * SR); x[i:i + L] += c
    L = int(0.25 * SR); tt = np.arange(L) / SR
    i = int(0.36 * d * SR); x[i:i + L] += lp(rng.standard_normal(L), 400) * np.exp(-tt / 0.07) * 0.7   # cloth thud
    return peak(x[: _n(d)], 0.5)


def footsteps(d, rng):
    x = np.zeros(_n(d) + SR); t = 0.3 * d
    while t < 0.8 * d:
        L = int(0.14 * SR); tt = np.arange(L) / SR
        s = lp(rng.standard_normal(L), 700) * np.exp(-tt / 0.03)
        i = int(t * SR); x[i:i + L] += s * rng.uniform(0.6, 1); t += rng.uniform(0.55, 0.7)
    return peak(x[: _n(d)], 0.3)


GEN = dict(church_bell=church_bell, choir_drone=choir_drone, kebero=kebero, tsenatsel=tsenatsel, birds=birds, wind=wind,
           quill=quill, crowd=crowd, plane=plane, flame=flame, room_tone=room_tone, latch=latch, footsteps=footsteps)


def render_shot(layers, dur, seed):
    rng = np.random.default_rng(seed); mix = np.zeros(_n(dur))
    for L in layers:
        g = 10 ** (L.get("gain_db", -12) / 20)
        mix += GEN[L["type"]](dur, rng) * g
    return mix.astype(np.float32)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--preview"); ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    d = OUT / "ambience"; d.mkdir(parents=True, exist_ok=True)
    if args.preview:
        write_wav(d / f"preview_{args.preview}.wav", GEN[args.preview](8, np.random.default_rng(1)) * 0.8)
        print("wrote", d / f"preview_{args.preview}.wav"); return
    sb = load_storyboard(); tl = timeline(sb)
    for row in tl:
        s = row["shot"]; layers = s.get("ambience", [])
        key = sha(layers, round(row["dur"], 2), s["seed"])
        wav = d / f"{s['id']}.wav"
        if not args.force and cached(wav, key):
            print(f"[{s['id']}] cached"); continue
        t0 = time.time(); x = render_shot(layers, row["dur"], s["seed"]); write_wav(wav, x); stamp(wav, key)
        log_run(stage="ambience", shot=s["id"], model="procedural-numpy", layers=[l["type"] for l in layers], input_hash=key,
                latency_s=round(time.time() - t0, 2), cost_usd=0.0, status="ok")
        print(f"[{s['id']}] {', '.join(l['type'] for l in layers)}")


if __name__ == "__main__":
    main()
