from __future__ import annotations

import pytest

from app.lyrics.models import LyricDocument, LyricLine, LyricToken
from app.lyrics.pronunciation import PronunciationSegment
from app.lyrics.reading_review import (
    ReadingCorrection,
    ReadingReviewError,
    apply_reading_corrections,
    document_review_payload,
    line_review_units,
)


def test_review_units_follow_janome_words_and_inflection() -> None:
    line = LyricLine(
        source="君は泣き声を隠した強い意志",
        surface="君は泣き声を隠した強い意志",
        reading="きみはなきごえをかくしたつよいいし",
        tokens=[
            LyricToken("君", "きみ"),
            LyricToken("は", "は", "wa"),
            LyricToken("泣", "な"),
            LyricToken("き", "き"),
            LyricToken("声", "ごえ"),
            LyricToken("を", "を"),
            LyricToken("隠", "かく"),
            LyricToken("し", "し"),
            LyricToken("た", "た"),
            LyricToken("強", "つよ"),
            LyricToken("い", "い"),
            LyricToken("意", "い"),
            LyricToken("志", "し"),
        ],
    )

    assert [
        (
            unit.start_token,
            unit.end_token,
            unit.surface,
            unit.reading,
        )
        for unit in line_review_units(line)
    ] == [
        (0, 1, "君", "きみ"),
        (2, 5, "泣き声", "なきごえ"),
        (6, 9, "隠した", "かくした"),
        (9, 11, "強い", "つよい"),
        (11, 13, "意志", "いし"),
    ]


def test_numeric_expression_is_one_review_unit() -> None:
    line = LyricLine(
        source="80億分の1の君",
        surface="80億分の1の君",
        reading="はちじゅうおくぶんのいちのきみ",
        tokens=[
            LyricToken("80", "はちじゅう"),
            LyricToken("億", "おく"),
            LyricToken("分", "ぶん"),
            LyricToken("の", "の"),
            LyricToken("1", "いち"),
            LyricToken("の", "の"),
            LyricToken("君", "きみ"),
        ],
    )

    assert [
        (unit.start_token, unit.end_token, unit.surface, unit.reading)
        for unit in line_review_units(line)
    ] == [
        (0, 5, "80億分の1", "はちじゅうおくぶんのいち"),
        (6, 7, "君", "きみ"),
    ]


def test_supported_numeric_shapes_stay_complete() -> None:
    cases = [
        (
            [LyricToken("3", "さん"), LyricToken("泊", "ぱく"), LyricToken("4", "よっ"), LyricToken("日", "か")],
            "3泊4日",
            "さんぱくよっか",
        ),
        (
            [LyricToken("午後", "ごご"), LyricToken("12", "じゅうに"), LyricToken("時", "じ"), LyricToken("半", "はん")],
            "午後12時半",
            "ごごじゅうにじはん",
        ),
        (
            [LyricToken("1", "わん"), LyricToken("LDK", "えるでぃーけー")],
            "1LDK",
            "わんえるでぃーけー",
        ),
    ]

    for tokens, surface, reading in cases:
        line = LyricLine(surface, surface, reading, tokens)

        units = line_review_units(line)

        assert [(unit.surface, unit.reading) for unit in units] == [
            (surface, reading)
        ]


def test_protected_alignment_token_is_never_merged_or_exposed() -> None:
    line = LyricLine(
        source="君は",
        surface="君は",
        reading="きみは",
        tokens=[
            LyricToken("君", "きみ"),
            LyricToken("は", "は", "wa"),
        ],
    )

    units = line_review_units(line)

    assert [(unit.start_token, unit.end_token, unit.surface) for unit in units] == [
        (0, 1, "君")
    ]


def test_kana_punctuation_and_whitespace_are_not_review_units() -> None:
    line = LyricLine(
        source="きっと、 またね",
        surface="きっと、 またね",
        reading="きっと、 またね",
        tokens=[
            LyricToken("きっと", "きっと"),
            LyricToken("、", "、"),
            LyricToken(" ", " "),
            LyricToken("またね", "またね"),
        ],
    )

    assert line_review_units(line) == []


def test_janome_boundary_inside_existing_token_falls_back_to_that_token() -> None:
    line = LyricLine(
        source="強い意志",
        surface="強い意志",
        reading="つよいいし",
        tokens=[LyricToken("強い意志", "つよいいし")],
    )

    units = line_review_units(line)

    assert [
        (unit.start_token, unit.end_token, unit.surface, unit.reading)
        for unit in units
    ] == [(0, 1, "強い意志", "つよいいし")]


def test_review_payload_adds_units_without_replacing_internal_tokens() -> None:
    document = LyricDocument(
        provider="local",
        source_text="泣き声",
        lines=[
            LyricLine(
                source="泣き声",
                surface="泣き声",
                reading="なきごえ",
                tokens=[
                    LyricToken("泣", "な"),
                    LyricToken("き", "き"),
                    LyricToken("声", "ごえ"),
                ],
            )
        ],
    )

    payload = document_review_payload(document)

    assert [token["surface"] for token in payload["lines"][0]["tokens"]] == [
        "泣",
        "き",
        "声",
    ]
    assert payload["lines"][0]["review_units"] == [
        {
            "start_token": 0,
            "end_token": 3,
            "surface": "泣き声",
            "reading": "なきごえ",
        }
    ]


def test_correction_merges_review_unit_and_records_safe_segments() -> None:
    document = LyricDocument(
        provider="local",
        source_text="泣き声",
        lines=[
            LyricLine(
                source="泣き声",
                surface="泣き声",
                reading="なきこえ",
                tokens=[
                    LyricToken("泣", "な"),
                    LyricToken("き", "き"),
                    LyricToken("声", "こえ"),
                ],
            )
        ],
    )

    reviewed = apply_reading_corrections(
        document,
        [
            ReadingCorrection(
                line_index=0,
                start_token=0,
                end_token=3,
                surface="泣き声",
                current_reading="なきこえ",
                corrected_reading="なきごえ",
            )
        ],
    )

    assert reviewed.lines[0].reading == "なきごえ"
    assert reviewed.lines[0].tokens == [
        LyricToken(
            "泣き声",
            "なきごえ",
            pronunciation_segments=[
                PronunciationSegment(0, 1, "な", True),
                PronunciationSegment(1, 2, "き", False),
                PronunciationSegment(2, 3, "ごえ", True),
            ],
        )
    ]


def test_accepting_defaults_still_creates_pronunciation_units() -> None:
    document = LyricDocument(
        provider="local",
        source_text="泣き声",
        lines=[
            LyricLine(
                source="泣き声",
                surface="泣き声",
                reading="なきごえ",
                tokens=[
                    LyricToken("泣", "な"),
                    LyricToken("き", "き"),
                    LyricToken("声", "ごえ"),
                ],
            )
        ],
    )

    reviewed = apply_reading_corrections(document, [])

    assert [(token.surface, token.reading) for token in reviewed.lines[0].tokens] == [
        ("泣き声", "なきごえ")
    ]
    assert reviewed.lines[0].tokens[0].pronunciation_segments == [
        PronunciationSegment(0, 1, "な", True),
        PronunciationSegment(1, 2, "き", False),
        PronunciationSegment(2, 3, "ごえ", True),
    ]


def test_unmappable_correction_is_kept_as_one_atomic_unit() -> None:
    document = LyricDocument(
        provider="local",
        source_text="80億分の1",
        lines=[
            LyricLine(
                source="80億分の1",
                surface="80億分の1",
                reading="はちじゅうおくぶんのいち",
                tokens=[
                    LyricToken("80", "はちじゅう"),
                    LyricToken("億", "おく"),
                    LyricToken("分", "ぶん"),
                    LyricToken("の", "の"),
                    LyricToken("1", "いち"),
                ],
            )
        ],
    )

    reviewed = apply_reading_corrections(
        document,
        [
            ReadingCorrection(
                line_index=0,
                start_token=0,
                end_token=5,
                surface="80億分の1",
                current_reading="はちじゅうおくぶんのいち",
                corrected_reading="にこから",
            )
        ],
    )

    assert reviewed.lines[0].tokens == [
        LyricToken(
            "80億分の1",
            "にこから",
            pronunciation_segments=[
                PronunciationSegment(0, 6, "にこから", True)
            ],
        )
    ]


def test_accepting_defaults_preserves_protected_pronunciation() -> None:
    document = LyricDocument(
        provider="local",
        source_text="君は",
        lines=[
            LyricLine(
                source="君は",
                surface="君は",
                reading="きみは",
                tokens=[
                    LyricToken("君", "きみ"),
                    LyricToken("は", "は", "wa"),
                ],
            )
        ],
    )

    reviewed = apply_reading_corrections(document, [])

    assert reviewed.lines[0].tokens[0].surface == "君"
    assert reviewed.lines[0].tokens[1] == LyricToken("は", "は", "wa")


@pytest.mark.parametrize(
    "correction",
    [
        ReadingCorrection(1, 0, 1, "君", "きみ", "きみ"),
        ReadingCorrection(0, 0, 2, "君は", "きみは", "きみわ"),
        ReadingCorrection(0, 0, 1, "別", "きみ", "きみ"),
        ReadingCorrection(0, 0, 1, "君", "くん", "きみ"),
        ReadingCorrection(0, 0, 1, "君", "きみ", "kimi"),
        ReadingCorrection(0, 0, 1, "君", "きみ", "123"),
        ReadingCorrection(0, 0, 1, "君", "きみ", ""),
    ],
)
def test_invalid_correction_rejects_the_whole_batch(
    correction: ReadingCorrection,
) -> None:
    document = LyricDocument(
        provider="local",
        source_text="君は",
        lines=[
            LyricLine(
                source="君は",
                surface="君は",
                reading="きみは",
                tokens=[
                    LyricToken("君", "きみ"),
                    LyricToken("は", "は", "wa"),
                ],
            )
        ],
    )

    with pytest.raises(ReadingReviewError):
        apply_reading_corrections(document, [correction])

    assert document.lines[0].tokens == [
        LyricToken("君", "きみ"),
        LyricToken("は", "は", "wa"),
    ]


def test_overlapping_corrections_reject_the_whole_batch() -> None:
    document = LyricDocument(
        provider="local",
        source_text="君の声",
        lines=[
            LyricLine(
                source="君の声",
                surface="君の声",
                reading="きみのこえ",
                tokens=[
                    LyricToken("君", "きみ"),
                    LyricToken("の", "の"),
                    LyricToken("声", "こえ"),
                ],
            )
        ],
    )

    with pytest.raises(ReadingReviewError):
        apply_reading_corrections(
            document,
            [
                ReadingCorrection(0, 0, 1, "君", "きみ", "くん"),
                ReadingCorrection(0, 0, 3, "君の声", "きみのこえ", "きみのこえ"),
            ],
        )
