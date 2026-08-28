from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Callable

from app.alignment.models import AlignedLine, AlignedToken
from app.alignment.japanese import normalize_reading


@dataclass(frozen=True)
class RubyPlacement:
    text: str
    x: int
    y: int
    token_index: int


@dataclass(frozen=True)
class RubyReading:
    surface_start: int
    surface_end: int
    reading: str
    reading_start: int


def contains_kanji(text: str) -> bool:
    return any(
        "\u3400" <= character <= "\u4dbf"
        or "\u4e00" <= character <= "\u9fff"
        for character in text
    )


def kanji_runs(text: str) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, character in enumerate(text):
        if contains_kanji(character):
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(text)))
    return runs


def kanji_readings(surface: str, reading: str) -> list[tuple[int, int, str]]:
    runs = kanji_runs(surface)
    if not runs:
        return []
    pattern_parts = ["^"]
    position = 0
    for start, end in runs:
        pattern_parts.append(
            re.escape(normalize_reading(surface[position:start]))
        )
        pattern_parts.append("(.*?)")
        position = end
    pattern_parts.append(re.escape(normalize_reading(surface[position:])))
    pattern_parts.append("$")
    match = re.fullmatch(
        "".join(pattern_parts),
        normalize_reading(reading),
    )
    captured = list(match.groups()) if match else []
    return [
        (
            start,
            end,
            captured[index]
            if index < len(captured) and captured[index]
            else normalize_reading(surface[start:end]),
        )
        for index, (start, end) in enumerate(runs)
    ]


def token_ruby_readings(token: AlignedToken) -> list[RubyReading]:
    if token.pronunciation_segments:
        readings: list[RubyReading] = []
        reading_start = 0
        for segment in token.pronunciation_segments:
            normalized = normalize_reading(segment.reading)
            if segment.ruby:
                readings.append(
                    RubyReading(
                        surface_start=segment.surface_start,
                        surface_end=segment.surface_end,
                        reading=normalized,
                        reading_start=reading_start,
                    )
                )
            reading_start += len(normalized)
        return readings

    result: list[RubyReading] = []
    reading_cursor = 0
    normalized_token_reading = normalize_reading(token.reading)
    for surface_start, surface_end, reading in kanji_readings(
        token.surface,
        token.reading,
    ):
        reading_start = normalized_token_reading.find(reading, reading_cursor)
        if reading_start < 0:
            reading_start = reading_cursor
        result.append(
            RubyReading(
                surface_start=surface_start,
                surface_end=surface_end,
                reading=reading,
                reading_start=reading_start,
            )
        )
        reading_cursor = reading_start + len(reading)
    return result


def ruby_placements(
    line: AlignedLine,
    *,
    play_res_x: int,
    baseline_y: int,
    base_font_size: int,
    ruby_font_size: int = 48,
    char_width_ratio: float = 0.68,
    center_x: int | None = None,
    letter_spacing: float = 0,
    measure_text: Callable[[str], float] | None = None,
) -> list[RubyPlacement]:
    fallback_width = float(round(base_font_size * char_width_ratio))

    def width(text: str) -> float:
        characters = list(text)
        measured = (
            sum(measure_text(character) for character in characters)
            if measure_text is not None
            else len(characters) * fallback_width
        )
        return measured + max(0, len(characters) - 1) * letter_spacing

    line_width = width(line.surface)
    line_left = (center_x or play_res_x / 2) - line_width / 2
    placements: list[RubyPlacement] = []
    character_offset = 0
    for token_index, token in enumerate(line.tokens):
        for ruby in token_ruby_readings(token):
            placements.append(
                RubyPlacement(
                    text=ruby.reading,
                    x=round(
                        line_left
                        + width(
                            line.surface[
                                : character_offset + ruby.surface_start
                            ]
                        )
                        + (
                            letter_spacing
                            if character_offset + ruby.surface_start > 0
                            else 0
                        )
                        + width(
                            token.surface[
                                ruby.surface_start : ruby.surface_end
                            ]
                        )
                        / 2
                    ),
                    y=baseline_y - base_font_size // 2 - 2,
                    token_index=token_index,
                )
            )
        character_offset += len(token.surface)
    return placements
