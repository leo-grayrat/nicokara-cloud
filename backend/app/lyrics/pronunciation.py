from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import unicodedata


@dataclass(frozen=True)
class PronunciationSegment:
    surface_start: int
    surface_end: int
    reading: str
    ruby: bool


@dataclass(frozen=True)
class _SurfacePart:
    start: int
    end: int
    text: str
    variable: bool


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return "".join(
        chr(ord(character) - 0x60)
        if "ァ" <= character <= "ヶ"
        else character
        for character in normalized
    )


def _is_variable_character(character: str) -> bool:
    normalized = _normalize(character)
    code_point = ord(character)
    return (
        0x3400 <= code_point <= 0x4DBF
        or 0x4E00 <= code_point <= 0x9FFF
        or 0xF900 <= code_point <= 0xFAFF
        or character in "々〆"
        or (
            len(normalized) == 1
            and normalized.isascii()
            and normalized.isalnum()
        )
    )


def _surface_parts(surface: str) -> list[_SurfacePart]:
    parts: list[_SurfacePart] = []
    for index, character in enumerate(surface):
        variable = _is_variable_character(character)
        if parts and parts[-1].variable == variable:
            previous = parts[-1]
            parts[-1] = _SurfacePart(
                start=previous.start,
                end=index + 1,
                text=previous.text + character,
                variable=variable,
            )
        else:
            parts.append(
                _SurfacePart(
                    start=index,
                    end=index + 1,
                    text=character,
                    variable=variable,
                )
            )
    return parts


def _unique_anchor_solution(
    parts: list[_SurfacePart],
    reading: str,
) -> list[tuple[int, int]] | None:
    minimum_suffix: list[int] = [0] * (len(parts) + 1)
    for index in range(len(parts) - 1, -1, -1):
        minimum_suffix[index] = minimum_suffix[index + 1] + (
            1 if parts[index].variable else len(_normalize(parts[index].text))
        )

    @lru_cache(maxsize=None)
    def solve(
        part_index: int,
        reading_offset: int,
    ) -> tuple[int, tuple[tuple[int, int], ...] | None]:
        if part_index == len(parts):
            return (
                (1, ())
                if reading_offset == len(reading)
                else (0, None)
            )

        part = parts[part_index]
        if not part.variable:
            literal = _normalize(part.text)
            if not reading.startswith(literal, reading_offset):
                return 0, None
            count, tail = solve(
                part_index + 1,
                reading_offset + len(literal),
            )
            if count == 0 or tail is None:
                return 0, None
            return count, ((reading_offset, reading_offset + len(literal)), *tail)

        maximum_end = len(reading) - minimum_suffix[part_index + 1]
        count = 0
        first_path: tuple[tuple[int, int], ...] | None = None
        for reading_end in range(reading_offset + 1, maximum_end + 1):
            tail_count, tail = solve(part_index + 1, reading_end)
            if tail_count == 0 or tail is None:
                continue
            if first_path is None:
                first_path = ((reading_offset, reading_end), *tail)
            count = min(2, count + tail_count)
            if count == 2:
                break
        return count, first_path

    count, path = solve(0, 0)
    return list(path) if count == 1 and path is not None else None


def _atomic_segment(
    surface: str,
    reading: str,
) -> PronunciationSegment:
    return PronunciationSegment(
        surface_start=0,
        surface_end=len(surface),
        reading=_normalize(reading),
        ruby=True,
    )


def _validated_segments(
    surface: str,
    reading: str,
    parts: list[_SurfacePart],
    solution: list[tuple[int, int]],
) -> list[PronunciationSegment]:
    normalized_reading = _normalize(reading)
    if len(parts) != len(solution):
        return [_atomic_segment(surface, reading)]

    segments = [
        PronunciationSegment(
            surface_start=part.start,
            surface_end=part.end,
            reading=normalized_reading[start:end],
            ruby=part.variable,
        )
        for part, (start, end) in zip(parts, solution, strict=True)
    ]
    if (
        not segments
        or segments[0].surface_start != 0
        or segments[-1].surface_end != len(surface)
        or any(
            left.surface_end != right.surface_start
            for left, right in zip(segments, segments[1:])
        )
        or "".join(segment.reading for segment in segments)
        != normalized_reading
        or any(
            not segment.ruby
            and _normalize(surface[segment.surface_start : segment.surface_end])
            != segment.reading
            for segment in segments
        )
    ):
        return [_atomic_segment(surface, reading)]
    return segments


def pronunciation_segments(
    surface: str,
    reading: str,
) -> list[PronunciationSegment]:
    normalized_reading = _normalize(reading)
    if not surface or not normalized_reading:
        return []
    parts = _surface_parts(surface)
    if parts and not any(part.variable for part in parts):
        return [] if _normalize(surface) == normalized_reading else [
            _atomic_segment(surface, reading)
        ]
    solution = _unique_anchor_solution(parts, normalized_reading)
    if solution is None:
        return [_atomic_segment(surface, reading)]
    return _validated_segments(surface, reading, parts, solution)
