# Costs and measurements

Run `python pipeline/cost_report.py` after a real run and paste the table here. Fill `pipeline/prices.json` from each provider's pricing page.
Record the **actual free-tier limit you found** on the day (limits change).

| Stage | Model | Where | Free limit found | Calls | Mean latency | GPU min | List-price equivalent |
|---|---|---|---|---|---|---|---|
| Narration | Gemini TTS | Gemini API | _fill_ | | | 0 | |
| Keyframes | FLUX.1 schnell | Cloudflare | _fill_ | | | 0 | |
| Moving shots | Wan 2.2 TI2V-5B | Kaggle T4 x2 | _fill_ h/week | | | | |
| Score | ACE-Step 1.5 | Kaggle | | | | | |
| Sound design | procedural numpy | local | none | | | 0 | $0 |
| Assembly | FFmpeg | local | none | | | 0 | $0 |

**Frontier comparison** (only if you get access): same shot with an open model and a frontier model, cost + latency + blind preference.

Measured by the demo run on a 1-CPU sandbox (not real model numbers): ambience 0.19 s per shot, temp track 1.1 s, Ken Burns clip about 9 s each, full assembly about 1 min per aspect ratio.
