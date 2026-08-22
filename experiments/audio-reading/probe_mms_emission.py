from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ctc_decode import collapse_ctc_ids
from mms_probe_utils import labels_by_id


def run_probe(audio_path: Path, *, device_name: str = "auto") -> dict[str, Any]:
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

    token_dict = bundle.get_dict()
    labels = labels_by_id(token_dict)
    blank_id = token_dict["-"]
    frame_ids = emission[0].argmax(dim=-1).detach().cpu().tolist()

    return {
        "model": "torchaudio.pipelines.MMS_FA",
        "device": str(device),
        "input_sample_rate": int(input_sample_rate),
        "model_sample_rate": int(bundle.sample_rate),
        "frame_count": len(frame_ids),
        "token_dict": token_dict,
        "blank_id": blank_id,
        "greedy_frame_ids": frame_ids,
        "decoded": collapse_ctc_ids(frame_ids, labels, blank_id),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Probe raw MMS_FA emissions with greedy CTC decoding."
    )
    parser.add_argument("audio", type=Path)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = run_probe(args.audio, device_name=args.device)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
