from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_TARGETS = ["歌声", "泣き声", "歌姫", "無き声", "君"]


def collect_target_readings(payload: dict, targets: list[str]) -> dict:
    found: dict[str, list[str]] = {target: [] for target in targets}
    for line in payload.get("lines", []):
        for token in line.get("tokens", []):
            surface = str(token.get("surface", ""))
            if surface in found:
                reading = str(token.get("reading", ""))
                if reading not in found[surface]:
                    found[surface].append(reading)
    return {
        "provider": str(payload.get("provider", "unknown")),
        "targets": found,
    }


def load_result(path: Path, targets: list[str]) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return collect_target_readings(payload, targets)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare target lyric readings from two lyrics_processed.json files."
    )
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path, nargs="?")
    parser.add_argument("--target", action="append", dest="targets")
    args = parser.parse_args()

    targets = args.targets or DEFAULT_TARGETS
    output = {"first": load_result(args.first, targets)}
    if args.second is not None:
        output["second"] = load_result(args.second, targets)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
