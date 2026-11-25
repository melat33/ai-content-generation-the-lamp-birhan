# Experiments (hypothesis -> change -> result)

Rules: change ONE thing, keep the seed fixed, write the result in numbers or what people said. The entries below are PLANNED.
Fill in **Result** and **Decision** only after you run them. Do not write results you did not measure.

| # | Hypothesis | Change (one variable) | How I measure | Result | Decision |
|---|---|---|---|---|---|
| E01 | A calm style instruction makes Amharic narration clearer than none | `TTS_STYLE` on/off, same voice | 3 listeners rate clarity 1-5; audio_seconds in runs.jsonl | _fill_ | |
| E02 | Another prebuilt voice suits the story better than `Kore` | `TTS_VOICE` Kore vs 2 others | listener pick + pronunciation errors | _fill_ | |
| E03 | Style block + symbol description keeps the lamp consistent across shots | with vs without `style_block`/`reference.symbol` in prompts, same seeds | count shots where lamp/look matches the reference (of 10) | _fill_ | |
| E04 | 8 steps beat 4 steps for FLUX.1 schnell on faces/hands | `KEYFRAME_STEPS` 4 vs 8 | defects per 10 keyframes, latency | _fill_ | |
| E05 | FLUX.2 klein (reference-image conditioning) is more consistent than schnell | `KEYFRAME_MODEL` | consistency count as E03 | _fill_ | |
| E06 | Wan at reduced size is good enough for drafts and saves quota | `SIZE` draft vs 1280*704, same keyframe/seed | GPU minutes per clip, visual defects | _fill_ | |
| E07 | A simple one-motion prompt beats a complex one | motion prompt simple vs complex | defects (flicker, morph) per 5 clips | _fill_ | |
| E08 | Ken Burns stills are preferred over Wan clips for some shots | blind A/B, 5+ people | preference counts | _fill_ | |
| E09 | The ambience layer (bell, drone, kebero) makes the radio cut feel more Ethiopian/emotional | radio cut with vs without ambience | 3+ listeners, what they felt | _fill_ | |
| E10 | The suggested ducking settings keep the voice clear | threshold/release default vs one change | voice intelligibility on phone speaker; LUFS before/after | _fill_ | |
| E11 | A hopeful question ending lands better than a quiet sad one | two endings of s10 | which ending people remember, how they felt | _fill_ | |
| E12 | ACE-Step candidate N is the best under narration | 3 seeds | listen under the voice at low volume | _fill_ | |

## Report prompt
Pick **one** suggested practice that beat your instinct and **one** that did not (e.g. radio cut before pictures; reference sheet first;
logging everything; letting the agent write stage scripts). Evidence for each should point to rows above or to `runs.jsonl`.
