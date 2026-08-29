from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
from typing import Any, Iterable

from janome.tokenizer import Tokenizer

from app.lyrics.models import LyricDocument, LyricLine, LyricToken
from app.lyrics.pronunciation import PronunciationSegment, pronunciation_segments


_REVIEWABLE_SURFACE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaffA-Za-z0-9]")
_FLEXIBLE_READING_SURFACE = re.compile(r"[A-Za-z0-9０-９]")
_VALID_CORRECTED_READING = re.compile(
    r"[\u3040-\u30ff\u31f0-\u31ffーゝゞヽヾ・]+"
)
_NUMERIC_REVIEW_EXPRESSION = re.compile(
    r"(?:"
    r"[0-9０-９]+(?:万|億|兆)*分の[0-9０-９]+"
    r"|[0-9０-９]+月[0-9０-９]+日"
    r"|[0-9０-９]+泊[0-9０-９]+日"
    r"|(?:午前|午後)?[0-9０-９]+時(?:半)?"
    r"|[0-9０-９]+(?:丁目|メーター|人|分|泊|つ|年|月|日|時|万|億|兆)"
    r"|[0-9０-９]+(?:[:：][0-9０-９]+|[A-Za-z]+)?"
    r")"
)
_TOKENIZER = Tokenizer()


@dataclass(frozen=True)
class ReadingReviewUnit:
    start_token: int
    end_token: int
    surface: str
    reading: str
    pronunciation_segments: list[PronunciationSegment]


@dataclass(frozen=True)
class ReadingCorrection:
    line_index: int
    start_token: int
    end_token: int
    surface: str
    current_reading: str
    corrected_reading: str


class ReadingReviewError(ValueError):
    pass


@dataclass(frozen=True)
class _CandidateSpan:
    start: int
    end: int
    accepts_auxiliary: bool = False


def _token_offsets(line: LyricLine) -> list[tuple[int, int]] | None:
    offsets: list[tuple[int, int]] = []
    position = 0
    for token in line.tokens:
        start = position
        position += len(token.surface)
        offsets.append((start, position))
    return offsets if position == len(line.surface) else None


def _janome_spans(surface: str) -> list[_CandidateSpan] | None:
    spans: list[_CandidateSpan] = []
    cursor = 0
    for item in _TOKENIZER.tokenize(surface):
        start = surface.find(item.surface, cursor)
        if start < 0:
            return None
        end = start + len(item.surface)
        major_part = item.part_of_speech.split(",", maxsplit=1)[0]
        if (
            major_part == "助動詞"
            and spans
            and spans[-1].accepts_auxiliary
            and spans[-1].end == start
        ):
            previous = spans[-1]
            spans[-1] = _CandidateSpan(
                start=previous.start,
                end=end,
                accepts_auxiliary=True,
            )
        else:
            spans.append(
                _CandidateSpan(
                    start=start,
                    end=end,
                    accepts_auxiliary=major_part in {"動詞", "形容詞"},
                )
            )
        cursor = end
    return spans


def _candidate_spans(surface: str) -> list[_CandidateSpan] | None:
    janome = _janome_spans(surface)
    if janome is None:
        return None
    numeric = [
        _CandidateSpan(match.start(), match.end())
        for match in _NUMERIC_REVIEW_EXPRESSION.finditer(surface)
    ]
    if not numeric:
        return janome
    retained = [
        candidate
        for candidate in janome
        if not any(
            candidate.start < numeric_span.end
            and numeric_span.start < candidate.end
            for numeric_span in numeric
        )
    ]
    return sorted([*retained, *numeric], key=lambda item: (item.start, item.end))


def _fallback_units(
    line: LyricLine,
    offsets: list[tuple[int, int]],
) -> list[ReadingReviewUnit]:
    return [
        ReadingReviewUnit(
            start_token=index,
            end_token=index + 1,
            surface=token.surface,
            reading=token.reading,
            pronunciation_segments=pronunciation_segments(
                token.surface,
                token.reading,
            ),
        )
        for index, token in enumerate(line.tokens)
        if token.alignment_pronunciation is None
        and _REVIEWABLE_SURFACE.search(token.surface) is not None
    ]


def line_review_units(line: LyricLine) -> list[ReadingReviewUnit]:
    offsets = _token_offsets(line)
    candidates = _candidate_spans(line.surface)
    if offsets is None or candidates is None:
        return _fallback_units(line, offsets or [])

    boundary_to_token = {0: 0}
    for token_index, (_, end) in enumerate(offsets):
        boundary_to_token[end] = token_index + 1

    units: list[ReadingReviewUnit] = []
    used_tokens: set[int] = set()
    for candidate in candidates:
        start_token = boundary_to_token.get(candidate.start)
        end_token = boundary_to_token.get(candidate.end)
        ranges: list[tuple[int, int]]
        if start_token is not None and end_token is not None:
            ranges = [(start_token, end_token)]
        else:
            overlapping = [
                token_index
                for token_index, (start, end) in enumerate(offsets)
                if start < candidate.end and candidate.start < end
            ]
            ranges = [
                (token_index, token_index + 1)
                for token_index in overlapping
            ]

        for range_start, range_end in ranges:
            token_indexes = range(range_start, range_end)
            if any(index in used_tokens for index in token_indexes):
                continue
            selected = line.tokens[range_start:range_end]
            surface = "".join(token.surface for token in selected)
            if (
                not selected
                or _REVIEWABLE_SURFACE.search(surface) is None
                or any(
                    token.alignment_pronunciation is not None
                    for token in selected
                )
            ):
                continue
            units.append(
                ReadingReviewUnit(
                    start_token=range_start,
                    end_token=range_end,
                    surface=surface,
                    reading="".join(token.reading for token in selected),
                    pronunciation_segments=pronunciation_segments(
                        surface,
                        "".join(token.reading for token in selected),
                    ),
                )
            )
            used_tokens.update(token_indexes)

    return sorted(units, key=lambda unit: unit.start_token)


def document_review_payload(document: LyricDocument) -> dict[str, Any]:
    payload = document.to_dict()
    for line, line_payload in zip(
        document.lines,
        payload["lines"],
        strict=True,
    ):
        line_payload["review_units"] = [
            asdict(unit) for unit in line_review_units(line)
        ]
    return payload


def _validate_corrections(
    document: LyricDocument,
    corrections: Iterable[ReadingCorrection],
) -> dict[tuple[int, int, int], str]:
    validated: dict[tuple[int, int, int], str] = {}
    occupied: dict[int, list[tuple[int, int]]] = {}
    units_by_line = [
        {
            (unit.start_token, unit.end_token): unit
            for unit in line_review_units(line)
        }
        for line in document.lines
    ]

    for correction in corrections:
        if not 0 <= correction.line_index < len(document.lines):
            raise ReadingReviewError("歌词行号超出范围")
        line = document.lines[correction.line_index]
        if not (
            0 <= correction.start_token
            < correction.end_token
            <= len(line.tokens)
        ):
            raise ReadingReviewError("审核单位范围超出词元边界")

        for start, end in occupied.setdefault(correction.line_index, []):
            if correction.start_token < end and start < correction.end_token:
                raise ReadingReviewError("同一批修正包含重叠范围")
        occupied[correction.line_index].append(
            (correction.start_token, correction.end_token)
        )

        unit = units_by_line[correction.line_index].get(
            (correction.start_token, correction.end_token)
        )
        if unit is None:
            raise ReadingReviewError("修正范围不是服务端生成的审核单位")
        selected = line.tokens[correction.start_token : correction.end_token]
        if any(token.alignment_pronunciation is not None for token in selected):
            raise ReadingReviewError("显式发音不能在注音确认阶段修改")
        if (
            correction.surface != unit.surface
            or correction.surface
            != "".join(token.surface for token in selected)
        ):
            raise ReadingReviewError("歌词表面文字与审核单位不一致")
        if correction.current_reading != unit.reading:
            raise ReadingReviewError("当前读音与审核单位不一致")
        if _VALID_CORRECTED_READING.fullmatch(correction.corrected_reading) is None:
            raise ReadingReviewError("修正读音必须是非空假名")
        original_literals = [
            segment
            for segment in unit.pronunciation_segments
            if not segment.ruby
        ]
        corrected_literals = [
            segment
            for segment in pronunciation_segments(
                unit.surface,
                correction.corrected_reading,
            )
            if not segment.ruby
        ]
        if (
            _FLEXIBLE_READING_SURFACE.search(unit.surface) is None
            and corrected_literals != original_literals
        ):
            raise ReadingReviewError("修正读音不能改变歌词中的字面假名")

        validated[
            (
                correction.line_index,
                correction.start_token,
                correction.end_token,
            )
        ] = correction.corrected_reading

    return validated


def apply_reading_corrections(
    document: LyricDocument,
    corrections: Iterable[ReadingCorrection],
) -> LyricDocument:
    validated = _validate_corrections(document, corrections)
    reviewed_lines: list[LyricLine] = []

    for line_index, line in enumerate(document.lines):
        units = {
            unit.start_token: unit
            for unit in line_review_units(line)
        }
        reviewed_tokens: list[LyricToken] = []
        token_index = 0
        while token_index < len(line.tokens):
            unit = units.get(token_index)
            if unit is None:
                reviewed_tokens.append(line.tokens[token_index])
                token_index += 1
                continue

            reading = validated.get(
                (line_index, unit.start_token, unit.end_token),
                unit.reading,
            )
            reviewed_tokens.append(
                LyricToken(
                    surface=unit.surface,
                    reading=reading,
                    pronunciation_segments=pronunciation_segments(
                        unit.surface,
                        reading,
                    ),
                )
            )
            token_index = unit.end_token

        reviewed_lines.append(
            replace(
                line,
                reading="".join(token.reading for token in reviewed_tokens),
                tokens=reviewed_tokens,
            )
        )

    return replace(document, lines=reviewed_lines)
