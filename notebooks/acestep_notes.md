# ACE-Step 1.5: making and choosing the score

1. Run `python pipeline/music.py --print-prompt` to get the caption, BPM, key and cue list from storyboard.json.
2. Follow the ACE-Step 1.5 guide (https://github.com/ACE-Step/ACE-Step-1.5) on Kaggle or Colab. Put the caption in the caption field,
   BPM and key in their own fields (not in the caption), tick instrumental, 30-60 s per section.
3. Generate **3 candidates** (different seeds). Save them as `outputs/music/candidates/cand1.wav`, `cand2.wav`, `cand3.wav`.
4. Listen to each **quietly under the narration** and write down why you chose one (this is an EXPERIMENTS.md entry).
5. `python pipeline/music.py --choose outputs/music/candidates/cand2.wav --why "no lead melody, leaves room for voice"`
6. Re-run `make assemble`. Until you do this, the film uses the procedural temp track (clearly a placeholder).
7. Note in COSTS.md: seconds per track, GPU minutes, VRAM used.
