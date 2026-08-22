# Audio Reading Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested experiment that exposes MMS_FA acoustic emissions, performs CTC greedy decoding, and compares competing Japanese sung-reading candidates against the same audio.

**Architecture:** Keep all new code under `experiments/audio-reading/`. The experiment must not alter the production pipeline. Pure decoding and scoring logic are isolated from model/audio loading so they can be unit-tested without TorchAudio model downloads.

**Tech Stack:** Python, pytest, TorchAudio MMS_FA for real probes only.

**Spec:** `docs/superpowers/specs/2026-08-23-audio-reading-probe-design.md`

## Global Constraints

- Do not modify the production lyric-processing or alignment pipeline in this experiment.
- Do not commit copyrighted song audio.
- Treat free decoding and candidate scores as probes, not as promised production solutions.
- Prefer small, inspectable JSON outputs over automatic acceptance decisions.

---

### Task 1: CTC greedy decoder

**Files:**
- Create: `experiments/audio-reading/ctc_decode.py`
- Create: `experiments/audio-reading/test_ctc_decode.py`

**Interfaces:**
- Produces: `collapse_ctc_ids(frame_ids: list[int], labels: list[str], blank_id: int) -> str`

- [ ] Write tests showing repeated frame IDs collapse, blanks disappear, and repeated letters separated by blank remain distinct.
- [ ] Run the test and confirm it fails because `ctc_decode.py` does not exist yet.
- [ ] Implement the minimal pure decoder.
- [ ] Run the test and confirm all decoder cases pass.

### Task 2: MMS emission probe

**Files:**
- Create: `experiments/audio-reading/mms_probe_utils.py`
- Create: `experiments/audio-reading/test_mms_probe_utils.py`
- Create: `experiments/audio-reading/probe_mms_emission.py`
- Create: `experiments/audio-reading/README.md`
- Create: `experiments/audio-reading/.gitignore`

**Interfaces:**
- Consumes: `collapse_ctc_ids(...)`
- Produces a JSON report containing model sample rate, frame count, token dictionary, greedy frame IDs, and collapsed decoded text.

- [ ] Test inversion of the MMS token dictionary into an id-indexed label table.
- [ ] Run the test and confirm it fails before the helper exists.
- [ ] Implement `labels_by_id(token_dict: dict[str, int]) -> list[str]`.
- [ ] Implement a CLI that loads an audio file, resamples to `torchaudio.pipelines.MMS_FA.sample_rate`, runs the model once, takes `argmax` over emission frames, and decodes using the bundle dictionary.
- [ ] Keep local audio under `experiments/audio-reading/data/` and ignore that directory.
- [ ] Document exact local commands and explain that noisy output is expected.

### Task 3: Candidate-reading comparison

**Files:**
- Create: `experiments/audio-reading/candidate_score.py`
- Create: `experiments/audio-reading/test_candidate_score.py`
- Create: `experiments/audio-reading/compare_mms_candidates.py`

**Interfaces:**
- Produces: `weighted_span_score(spans) -> float`.
- Produces a JSON ranking of normalized romanized candidates aligned against one shared MMS emission, including each score and the top-two score margin.

- [ ] Write a failing test proving span confidence is weighted by aligned frame duration.
- [ ] Implement the minimal weighted scoring helper and run all pure tests.
- [ ] Implement a CLI that runs MMS_FA once, then aligns each `--candidate` against the same emission via `bundle.get_tokenizer()` and `bundle.get_aligner()`.
- [ ] Sort candidate results by score and record `score_margin` without defining an automatic acceptance threshold.
- [ ] Document that candidates with very different lengths may be biased and should later be compared with identical surrounding lyric anchors.

### Task 4: Reading cases and evaluation notes

**Files:**
- Create: `experiments/audio-reading/cases.json`
- Create: `experiments/audio-reading/results/README.md`

**Interfaces:**
- `cases.json` records surface text, known actual reading, and misleading/ordinary alternative reading.

- [ ] Seed cases for `泣き声 / なきごえ / なきこえ`, `目覚めた / めざめた / めさめた`, and a song-specific `宇宙 / そら / うちゅう` case.
- [ ] Define a result table that records raw greedy decode, actual/competing candidate scores, margin, and conclusion.
- [ ] Do not claim success until real audio has been run locally.

### Task 5: Verification

- [ ] Run all pure unit tests.
- [ ] Import/compile both probe scripts without downloading a model where possible.
- [ ] Verify no audio files are tracked.
- [ ] Compare the experiment branch against `main` and confirm no production files changed.
