# Ethics: consent, licences, labelling

## Consent record
* **No real person's face or voice is generated or cloned.** Characters are stylised painted figures and silhouettes; historical figures
  (rulers, soldiers, teachers) appear only symbolically (a crowd, a raised hand, a silhouette), never as a likeness.
* **Narration uses a stock prebuilt Gemini TTS voice**, not a clone of any relative or public figure.
* **People who watch the user tests** are not shown or voiced in the film. If you quote a viewer in the post or report, ask them first and record it here:

| Person | What I use | Their consent (how, when) |
|---|---|---|
| _none so far_ | | |

## Sensitive history
The film covers 1974 and later hardship. It states facts (Adwa 1896, the 1974 revolution, the exodus of educated people) and poses the rest as a question.
It names no group as the culprit. Draft test-viewers with different views checked it (see DESIGN.md).

## Licences (check each before you submit; terms change)
| Item | Used for | Licence / terms | Checked on |
|---|---|---|---|
| FLUX.1 schnell | keyframes | Apache 2.0 (verify on the model card) | _date_ |
| FLUX.2 klein 4B (if used) | keyframes | Apache 2.0; the 9B is non-commercial | _date_ |
| Wan 2.2 TI2V-5B | moving shots | Apache 2.0 | _date_ |
| ACE-Step 1.5 | score | MIT; outputs usable commercially | _date_ |
| Gemini TTS | narration | Google API terms; free-tier data may be used to improve products: **no private family details were sent** | _date_ |
| Procedural audio and placeholder art | sound design, demo | original code in this repo (add a LICENSE) | n/a |
| FFmpeg | assembly | LGPL/GPL depending on build | _date_ |
| Fonts (DejaVu, Noto Sans Ethiopic) | subtitles, end card | open licences | _date_ |

## Labelling plan
1. The film ends with a 3-second **"Made with AI"** end card (`assemble.py`).
2. The MP4 metadata `comment` says it is AI-generated.
3. When posting, switch the platform's **AI-generated content label ON**.
4. Leave SynthID / C2PA marks and metadata intact; do not strip them.
5. The post says in plain words which parts are AI and which are mine (story, direction, storyboard, code).
