# Failures (what broke, what I tried, what fixed it)

Add an entry the moment something breaks. Real blockers (quota, memory, consistency, language) are what the graders look for.

## Template
**F00: short title** · date
* Symptom: exact error or what looked wrong
* Cause (known or suspected):
* What I tried (in order):
* What fixed it / the workaround:
* Evidence: `runs.jsonl` line, commit, or file

## Things likely to bite (watch for them; log what actually happens)
* Gemini TTS Amharic: mispronounced numbers/names (1966 ዓ.ም.), drift in pace, a wrong model ID, free-tier rate limits.
* Cloudflare daily allowance running out; FLUX ignoring "no text" or drawing realistic faces.
* Lamp changing shape between keyframes (identity drift): fix prompt wording and the `reference.symbol` string, then re-run E03.
* Kaggle: session timeout, out-of-memory on a T4 (lower `SIZE`/`FRAMES`, keep offloading), slow queue. Switch remaining shots to Ken Burns early.
* FFmpeg: missing `sidechaincompress`/`loudnorm` in an old build (use FFmpeg 5+), missing Amharic font for the end card (drop Noto Sans Ethiopic into `assets/fonts/`).

## Entries
_none yet_
