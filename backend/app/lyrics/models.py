from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.lyrics.pronunciation import PronunciationSegment


@dataclass(frozen=True)
class LyricToken:
    surface: str
    reading: str
    alignment_pronunciation: str | None = None
    pronunciation_segments: list[PronunciationSegment] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class LyricLine:
    source: str
    surface: str
    reading: str
    tokens: list[LyricToken] = field(default_factory=list)


@dataclass(frozen=True)
class LyricDocument:
    provider: str
    source_text: str
    lines: list[LyricLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for line in value["lines"]:
            for token in line["tokens"]:
                if not token["pronunciation_segments"]:
                    token.pop("pronunciation_segments")
        return value


def lyric_document_from_dict(value: dict[str, Any]) -> LyricDocument:
    return LyricDocument(
        provider=str(value["provider"]),
        source_text=str(value["source_text"]),
        lines=[
            LyricLine(
                source=str(line["source"]),
                surface=str(line["surface"]),
                reading=str(line["reading"]),
                tokens=[
                    LyricToken(
                        surface=str(token["surface"]),
                        reading=str(token["reading"]),
                        alignment_pronunciation=(
                            str(token["alignment_pronunciation"])
                            if token.get("alignment_pronunciation") is not None
                            else None
                        ),
                        pronunciation_segments=[
                            PronunciationSegment(
                                surface_start=int(segment["surface_start"]),
                                surface_end=int(segment["surface_end"]),
                                reading=str(segment["reading"]),
                                ruby=bool(segment["ruby"]),
                            )
                            for segment in token.get(
                                "pronunciation_segments", []
                            )
                        ],
                    )
                    for token in line.get("tokens", [])
                ],
            )
            for line in value.get("lines", [])
        ],
        warnings=[str(warning) for warning in value.get("warnings", [])],
    )

