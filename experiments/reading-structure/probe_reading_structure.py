from __future__ import annotations

import argparse
import json
from pathlib import Path

from janome.tokenizer import Tokenizer
from pykakasi import kakasi


DEFAULT_CASES = [
    "泣き声",
    "目覚めた",
    "物語",
    "今日",
    "大人しい",
]

_CONVERTER = kakasi()
_TOKENIZER = Tokenizer()


def to_hiragana(text: str) -> str:
    return "".join(item["hira"] for item in _CONVERTER.convert(text))


def inspect_text(text: str) -> dict:
    tokens = []
    for item in _TOKENIZER.tokenize(text):
        janome_reading = getattr(item, "reading", "*")
        janome_phonetic = getattr(item, "phonetic", "*")
        tokens.append(
            {
                "surface": item.surface,
                "part_of_speech": item.part_of_speech,
                "base_form": getattr(item, "base_form", "*"),
                "infl_type": getattr(item, "infl_type", "*"),
                "infl_form": getattr(item, "infl_form", "*"),
                "janome_reading": janome_reading,
                "janome_reading_hira": (
                    to_hiragana(janome_reading)
                    if janome_reading and janome_reading != "*"
                    else None
                ),
                "janome_phonetic": janome_phonetic,
                "pykakasi_for_token": to_hiragana(item.surface),
            }
        )

    return {
        "text": text,
        "pykakasi_whole": to_hiragana(text),
        "pykakasi_after_janome_split": "".join(
            token["pykakasi_for_token"] for token in tokens
        ),
        "janome_joined_reading": "".join(
            token["janome_reading_hira"] or "" for token in tokens
        ),
        "tokens": tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Janome morphology/readings with the current "
            "Janome-token + pykakasi reading path."
        )
    )
    parser.add_argument(
        "texts",
        nargs="*",
        help="Japanese strings to inspect. Uses built-in cases when omitted.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = {
        "cases": [inspect_text(text) for text in (args.texts or DEFAULT_CASES)]
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
