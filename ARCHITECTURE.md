# Architecture

## Shape

```
                 storyboard.json  (validated by schema/storyboard.schema.json before every run)
                       |
   +-------------------+------------------------------+
   |                   |                              |
narration.py     keyframes.py -> shots.py         ambience.py     music.py
(Gemini TTS)     (FLUX)        (Wan clip or       (procedural)   (ACE-Step pick
 sNN.wav          sNN.png       Ken Burns)         sNN.wav        or temp track)
   |                   |        sNN_v.mp4 / _h.mp4      |              |
   +-------------------+------------------------------+--------------+
                                     |
                               assemble.py (FFmpeg)
                  timeline -> stems -> duck -> loudnorm -> subtitles -> end card -> 9:16 + 16:9
```

## Contracts

* `storyboard.json` is the only input every stage reads. Each shot has: `id`, `act`, `duration_s`, `shot_size`, `reason` (why the shot exists),
  `image_prompt`, `motion_prompt` (motion and camera only), `narration.{am,en}`, `music_cue`, `seed`, optional `grade` and `ambience`.
* Stage outputs are files named by shot id (`s03.wav`, `s03.png`, `s03_v.mp4`). A stage never reads another stage's code, only its files.
* `timeline()` in `common.py` is the one place timing is decided: **narration length sets shot length**
  (`max(duration_s, 0.6 s lead + narration + 0.5 s tail)`), so picture, subtitles, ambience and music all follow the voice.

## Caching

Each output has a sidecar `<file>.hash` = SHA-256 of everything that can change it (model, voice/style, prompt, seed, steps, duration, grade, clip hash).
Re-running skips any file whose hash matches. Editing one narration line regenerates that one WAV; editing one image prompt regenerates that
keyframe and its two clips. `--force` ignores the cache; `--shot sNN` limits a stage to one shot.

## Failure handling

* **Retries:** `with_retries` does 3 attempts with exponential backoff; every failed attempt is logged to `runs.jsonl` with the error text.
* **Quota or GPU runs out:** the Kaggle script saves after every shot and skips finished ones, so a timed-out session resumes.
* **Fallback ladder:** Wan clip fails -> Ken Burns on the keyframe; ACE-Step unavailable -> procedural temp track;
  a model stage fails -> the log says which shot, and the rest of the film is untouched.
* **Fail early:** schema validation runs first, and stages refuse to run without their keys (they never silently fall back to placeholders;
  placeholders only run with `DEMO=1` / `--placeholder`, so a demo file cannot be mistaken for the film).
* **Secrets:** read from `.env` / environment; `.env` is git-ignored.

## Sound design (the "church sound")

`ambience.py` synthesises original layers per shot from the `ambience` list in the storyboard: bronze church bell (inharmonic partials,
slow decay, stone-room reverb), a distant choir-like drone on D, kebero drum, tsenatsel (sistrum) rattle, dawn birds, wind, a quill on parchment,
crowd murmur, a passing aeroplane, lamp flame crackle, room tone, a suitcase latch and footsteps. The arc is audible in the data:
layers are rich in Act 1, drain in Act 2 (room tone, wind) and return in Act 3 (bell, birds, flame).
Because it is code, it has no licence issues and costs no quota. Swap in recorded sounds later if you wish.

## Mix

Stems are level-matched first (voice -20 dBFS RMS, music -25, ambience -30), then `sidechaincompress`
(threshold 0.02, ratio 6, attack 300 ms, release 1500 ms) ducks the score under the voice, then a **two-pass `loudnorm`** targets -14 LUFS, true peak -1 dB.

## Why this shape

One contract and one-file-per-output means any shot can be re-made alone, any stage can be swapped (FLUX.1 schnell for FLUX.2 klein,
Ken Burns for Wan) without touching the others, and the evidence for each choice lives in `runs.jsonl`.
