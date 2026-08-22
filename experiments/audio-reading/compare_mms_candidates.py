from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from candidate_score import weighted_span_score


def compare_candidates(
    audio_path: Path,
    candidates: list[str],
    *,
    device_name: str = "auto",
) -> dict[str, Any]:
    import librosa
    import torch
    import torchaudio

    bundle = torchaudio.pipelines.MMS_FA
    device = torch.device(
        "cuda"
        if device_name == "auto" and torch.cuda.is_available()
        else ("cpu" if device_name == "auto" else device_name)
    )

    audio, input_sample_rate = librosa.load(str(audio_path), sr=None, mono=True)
    waveform = torch.from_numpy(audio).float().unsqueeze(0)
    if input_sample_rate != bundle.sample_rate:
        waveform = torchaudio.functional.resample(
            waveform,
            input_sample_rate,
            bundle.sample_rate,
        )

    model = bundle.get_model().to(device)
    try:
        with torch.inference_mode():
            emission, _ = model(waveform.to(device))
    finally:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        token_spans = aligner(emission[0], tokenizer([candidate]))
        spans = token_spans[0]
        results.append(
            {
                "candidate": candidate,
                "score": weighted_span_score(spans),
                "start_frame": int(spans[0].start),
                "end_frame": int(spans[-1].end),
                "span_count": len(spans),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return {
        "model": "torchaudio.pipelines.MMS_FA",
        "device": str(device),
        "input_sample_rate": int(input_sample_rate),
        "model_sample_rate": int(bundle.sample_rate),
        "frame_count": int(emission.shape[1]),
        "results": results,
        "score_margin": (
            results[0]["score"] - results[1]["score"]
            if len(results) >= 2
            else None
        ),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare candidate romanized readings against one audio clip."
    )
    parser.add_argument("audio", type=Path)
    parser.add_argument(
        "--candidate",
        action="append",
        required=True,
        help="Normalized MMS romanization, for example nakigoe or nakikoe.",
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = compare_candidates(
        args.audio,
        args.candidate,
        device_name=args.device,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
