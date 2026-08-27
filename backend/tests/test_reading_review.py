from __future__ import annotations

from app.lyrics.models import LyricDocument, LyricLine, LyricToken
from app.lyrics.reading_review import (
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
