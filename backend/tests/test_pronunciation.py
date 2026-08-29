from __future__ import annotations

from app.lyrics.models import (
    LyricDocument,
    LyricLine,
    LyricToken,
    lyric_document_from_dict,
)
from app.lyrics.pronunciation import (
    PronunciationSegment,
    pronunciation_segments,
)


def test_unique_literal_kana_anchor_creates_safe_segments() -> None:
    assert pronunciation_segments("泣き声", "なきごえ") == [
        PronunciationSegment(0, 1, "な", True),
        PronunciationSegment(1, 2, "き", False),
        PronunciationSegment(2, 3, "ごえ", True),
    ]


def test_repeated_anchor_with_multiple_solutions_falls_back_atomically() -> None:
    assert pronunciation_segments("思い出", "あいいで") == [
        PronunciationSegment(0, 3, "あいいで", True),
    ]


def test_missing_anchor_falls_back_atomically() -> None:
    assert pronunciation_segments("80億分の1", "にこから") == [
        PronunciationSegment(0, 6, "にこから", True),
    ]


def test_continuous_kanji_run_is_not_split_per_character() -> None:
    assert pronunciation_segments("歌姫", "うたひめ") == [
        PronunciationSegment(0, 2, "うたひめ", True),
    ]


def test_unchanged_kana_needs_no_explicit_mapping() -> None:
    assert pronunciation_segments("きっと", "きっと") == []


def test_katakana_literal_anchor_is_matched_as_hiragana() -> None:
    assert pronunciation_segments("1000メーター", "せんめーたー") == [
        PronunciationSegment(0, 4, "せん", True),
        PronunciationSegment(4, 8, "めーたー", False),
    ]


def test_many_repeated_anchors_do_not_require_enumerating_every_solution() -> None:
    surface = "思" + "い出" * 200
    reading = "あ" + "いい" * 200 + "で"

    assert pronunciation_segments(surface, reading) == [
        PronunciationSegment(0, len(surface), reading, True),
    ]


def test_lyric_token_pronunciation_segments_round_trip() -> None:
    token = LyricToken(
        "泣き声",
        "なきごえ",
        pronunciation_segments=[
            PronunciationSegment(0, 1, "な", True),
            PronunciationSegment(1, 2, "き", False),
            PronunciationSegment(2, 3, "ごえ", True),
        ],
    )
    document = LyricDocument(
        provider="local",
        source_text="泣き声",
        lines=[
            LyricLine(
                source="泣き声",
                surface="泣き声",
                reading="なきごえ",
                tokens=[token],
            )
        ],
    )

    assert lyric_document_from_dict(document.to_dict()) == document


def test_old_lyric_json_without_segments_remains_readable() -> None:
    document = lyric_document_from_dict(
        {
            "provider": "local",
            "source_text": "君",
            "lines": [
                {
                    "source": "君",
                    "surface": "君",
                    "reading": "きみ",
                    "tokens": [{"surface": "君", "reading": "きみ"}],
                }
            ],
            "warnings": [],
        }
    )

    assert document.lines[0].tokens[0].pronunciation_segments == []


def test_empty_segments_do_not_change_existing_lyric_json_shape() -> None:
    document = LyricDocument(
        provider="local",
        source_text="君",
        lines=[
            LyricLine(
                source="君",
                surface="君",
                reading="きみ",
                tokens=[LyricToken("君", "きみ")],
            )
        ],
    )

    token = document.to_dict()["lines"][0]["tokens"][0]

    assert "pronunciation_segments" not in token
