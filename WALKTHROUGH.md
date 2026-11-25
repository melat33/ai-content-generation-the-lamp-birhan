# Walkthrough video plan (max 5 minutes)

| Time | Show | Say |
|---|---|---|
| 0:00-0:30 | the film's first 15 s | who it is for, the feeling, the one thread (the lamp) |
| 0:30-1:45 | `ARCHITECTURE.md` diagram, `storyboard.json`, `schema/` | one contract, five stages, every shot has a reason |
| 1:45-2:45 | one hard decision (pick yours: narration sets timing; Ken Burns fallback; procedural sound design vs model) | the alternatives, what the logs showed |
| 2:45-4:15 | **live regeneration** | edit one keyframe prompt (e.g. s05) or one narration line in `storyboard.json`; run `make film`; terminal prints `cached` for all other shots; show the single new line in `runs.jsonl`. Pausing during the job is fine; you need not rerun Wan on camera |
| 4:15-5:00 | the final cut, the end card | what broke (FAILURES.md), what you would build next |

Rehearse once so the demo runs clean. Record in a quiet room; show the terminal at a readable size.
