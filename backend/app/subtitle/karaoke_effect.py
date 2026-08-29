from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from app.alignment.models import AlignedLine, AlignedToken
from app.alignment.japanese import normalize_reading


@dataclass(frozen=True)
class KaraokeChunk:
    text: str
    duration_cs: int


def escape_ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def is_sung_text(text: str) -> bool:
    return any(
        not unicodedata.category(character).startswith(("P", "S", "Z"))
        for character in text
    )


def character_chunks(token: AlignedToken) -> list[KaraokeChunk]:
    mapped = _pronunciation_chunks(token)
    if mapped is not None:
        return mapped
    characters = list(token.surface)
    if not characters:
        return []
    sung_indices = [
        index
        for index, character in enumerate(characters)
        if is_sung_text(character)
    ]
    if not sung_indices:
        return [
            KaraokeChunk(text=character, duration_cs=0)
            for character in characters
        ]
    total_cs = round((token.end_ms - token.start_ms) / 10)
    durations = [0] * len(characters)
    if token.moras:
        boundaries = [
            _sequence_time_ms(
                token,
                len(token.moras) * index / len(sung_indices),
            )
            for index in range(len(sung_indices) + 1)
        ]
        for position, character_index in enumerate(sung_indices):
            durations[character_index] = max(
                0,
                round((boundaries[position + 1] - boundaries[position]) / 10),
            )
    else:
        base, remainder = divmod(max(0, total_cs), len(sung_indices))
        for position, character_index in enumerate(sung_indices):
            durations[character_index] = base + (
                1 if position >= len(sung_indices) - remainder else 0
            )
    return [
        KaraokeChunk(
            text=character,
            duration_cs=durations[index],
        )
        for index, character in enumerate(characters)
    ]


def _reading_time_ms(token: AlignedToken, character_offset: int) -> int:
    segments = _mora_segments(token)
    full_length = sum(len(text) for text, _, _ in segments)
    if not segments or full_length == 0:
        reading_length = max(1, len(normalize_reading(token.reading)))
        bounded = min(reading_length, max(0, character_offset))
        return round(
            token.start_ms
            + (token.end_ms - token.start_ms) * bounded / reading_length
        )
    bounded = min(full_length, max(0, character_offset))
    if bounded == full_length:
        return token.end_ms
    cursor = 0
    for text, start_ms, end_ms in segments:
        segment_end = cursor + len(text)
        if bounded < segment_end:
            return round(
                start_ms
                + (end_ms - start_ms) * (bounded - cursor) / len(text)
            )
        cursor = segment_end
    return token.end_ms


def _pronunciation_chunks(
    token: AlignedToken,
) -> list[KaraokeChunk] | None:
    segments = token.pronunciation_segments
    if not segments:
        return None
    if (
        segments[0].surface_start != 0
        or segments[-1].surface_end != len(token.surface)
        or any(
            left.surface_end != right.surface_start
            for left, right in zip(segments, segments[1:])
        )
        or "".join(normalize_reading(segment.reading) for segment in segments)
        != normalize_reading(token.reading)
    ):
        return None

    chunks: list[KaraokeChunk] = []
    reading_offset = 0
    for segment in segments:
        normalized = normalize_reading(segment.reading)
        start_ms = _reading_time_ms(token, reading_offset)
        reading_offset += len(normalized)
        end_ms = _reading_time_ms(token, reading_offset)
        chunks.append(
            KaraokeChunk(
                text=token.surface[
                    segment.surface_start : segment.surface_end
                ],
                duration_cs=max(0, round((end_ms - start_ms) / 10)),
            )
        )
    return chunks


def _mora_segments(token: AlignedToken) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    for index, mora in enumerate(token.moras):
        previous = token.moras[index - 1] if index > 0 else None
        start_ms = max(
            token.start_ms,
            token.start_ms if previous is None else previous.end_ms,
        )
        end_ms = min(
            token.end_ms,
            max(
                start_ms,
                token.end_ms if index == len(token.moras) - 1 else mora.end_ms,
            ),
        )
        result.append((normalize_reading(mora.reading), start_ms, end_ms))
    return result


def _sequence_time_ms(token: AlignedToken, position: float) -> int:
    segments = _mora_segments(token)
    if not segments:
        return token.start_ms
    bounded = min(float(len(segments)), max(0.0, position))
    index = min(len(segments) - 1, int(bounded))
    progress = bounded - index
    if bounded >= len(segments):
        return token.end_ms
    _, start_ms, end_ms = segments[index]
    return round(start_ms + (end_ms - start_ms) * progress)


def ruby_chunks(
    token: AlignedToken,
    reading: str,
    *,
    reading_start: int | None = None,
) -> list[KaraokeChunk]:
    normalized = normalize_reading(reading)
    if not normalized:
        return []
    segments = _mora_segments(token)
    full_reading = "".join(text for text, _, _ in segments)
    match_start = (
        reading_start
        if reading_start is not None
        else full_reading.find(normalized)
    )
    if segments and match_start >= 0:
        chunks: list[KaraokeChunk] = []
        character_offset = 0
        match_end = match_start + len(normalized)
        for text, start_ms, end_ms in segments:
            segment_end = character_offset + len(text)
            overlap_start = max(match_start, character_offset)
            overlap_end = min(match_end, segment_end)
            if overlap_start < overlap_end:
                duration = end_ms - start_ms
                for character_index in range(overlap_start, overlap_end):
                    local_index = character_index - character_offset
                    character_start = start_ms + duration * local_index / len(text)
                    character_end = start_ms + duration * (local_index + 1) / len(text)
                    chunks.append(
                        KaraokeChunk(
                            text=full_reading[character_index],
                            duration_cs=max(
                                0,
                                round((character_end - character_start) / 10),
                            ),
                        )
                    )
            character_offset = segment_end
        if chunks and "".join(chunk.text for chunk in chunks) == normalized:
            return chunks

    total_cs = max(0, round((token.end_ms - token.start_ms) / 10))
    base, remainder = divmod(total_cs, len(normalized))
    return [
        KaraokeChunk(
            text=character,
            duration_cs=base + (1 if index >= len(normalized) - remainder else 0),
        )
        for index, character in enumerate(normalized)
    ]


def ruby_start_ms(
    token: AlignedToken,
    reading: str,
    *,
    reading_start: int | None = None,
) -> int:
    normalized = normalize_reading(reading)
    segments = _mora_segments(token)
    full_reading = "".join(text for text, _, _ in segments)
    match_start = (
        reading_start
        if reading_start is not None
        else full_reading.find(normalized)
    )
    if not segments or match_start < 0:
        return token.start_ms
    character_offset = 0
    for text, start_ms, end_ms in segments:
        segment_end = character_offset + len(text)
        if match_start < segment_end:
            local_index = match_start - character_offset
            return round(start_ms + (end_ms - start_ms) * local_index / len(text))
        character_offset = segment_end
    return token.start_ms


def line_chunks(line: AlignedLine) -> list[KaraokeChunk]:
    result: list[KaraokeChunk] = []
    for index, token in enumerate(line.tokens):
        chunks = character_chunks(token)
        if not chunks:
            continue
        next_start_ms = (
            line.tokens[index + 1].start_ms
            if index + 1 < len(line.tokens)
            else line.end_ms
        )
        gap_cs = round(max(0, next_start_ms - token.end_ms) / 10)
        if not result:
            gap_cs += round(max(0, token.start_ms - line.start_ms) / 10)
        sung_index = next(
            (
                chunk_index
                for chunk_index in range(len(chunks) - 1, -1, -1)
                if is_sung_text(chunks[chunk_index].text)
            ),
            None,
        )
        if sung_index is not None:
            chunks[sung_index] = KaraokeChunk(
                text=chunks[sung_index].text,
                duration_cs=chunks[sung_index].duration_cs + gap_cs,
            )
        result.extend(chunks)

    if result:
        target_cs = round((line.end_ms - line.start_ms) / 10)
        difference = target_cs - sum(chunk.duration_cs for chunk in result)
        if difference > 0:
            index = next(
                index
                for index in range(len(result) - 1, -1, -1)
                if is_sung_text(result[index].text)
            )
            result[index] = KaraokeChunk(
                text=result[index].text,
                duration_cs=result[index].duration_cs + difference,
            )
        elif difference < 0:
            remaining = -difference
            for index in range(len(result) - 1, -1, -1):
                if not is_sung_text(result[index].text):
                    continue
                reduction = min(result[index].duration_cs, remaining)
                result[index] = KaraokeChunk(
                    text=result[index].text,
                    duration_cs=result[index].duration_cs - reduction,
                )
                remaining -= reduction
                if remaining == 0:
                    break
    return result


def render_karaoke(chunks: list[KaraokeChunk]) -> str:
    return "".join(
        (
            rf"{{\kf{chunk.duration_cs}}}{escape_ass_text(chunk.text)}"
            if chunk.duration_cs > 0 and is_sung_text(chunk.text)
            else escape_ass_text(chunk.text)
        )
        for chunk in chunks
    )
