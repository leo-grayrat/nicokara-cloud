from __future__ import annotations

import importlib

import pytest

from app.alignment.models import AlignedLine, AlignedToken
from app.lyrics.pronunciation import PronunciationSegment


def test_ruby_is_created_for_kanji_runs_not_the_whole_mixed_token() -> None:
    try:
        module = importlib.import_module("app.subtitle.ruby")
    except ModuleNotFoundError:
        pytest.fail("Ruby subtitle layout is not implemented")

    line = AlignedLine(
        surface="食べる物語",
        reading="たべるものがたり",
        start_ms=1000,
        end_ms=4000,
        confidence=1.0,
        tokens=[
            AlignedToken("食べる", "たべる", 1000, 2000, 1.0),
            AlignedToken("物語", "ものがたり", 2000, 4000, 1.0),
        ],
    )

    placements = module.ruby_placements(
        line,
        play_res_x=1920,
        baseline_y=670,
        base_font_size=96,
        center_x=960,
    )

    assert [item.text for item in placements] == ["た", "ものがたり"]
    assert [(item.x, item.y) for item in placements] == [
        (830, 620),
        (1058, 620),
    ]


def test_kana_only_tokens_never_receive_ruby() -> None:
    module = importlib.import_module("app.subtitle.ruby")
    line = AlignedLine(
        surface="かなだけ",
        reading="かなだけ",
        start_ms=0,
        end_ms=1000,
        confidence=1.0,
        tokens=[AlignedToken("かなだけ", "かなだけ", 0, 1000, 1.0)],
    )

    placements = module.ruby_placements(
        line,
        play_res_x=1920,
        baseline_y=670,
        base_font_size=96,
    )

    assert placements == []


def test_ruby_placement_uses_measured_glyph_widths() -> None:
    module = importlib.import_module("app.subtitle.ruby")
    line = AlignedLine(
        surface="Wi\u6f22",
        reading="Wi\u304b\u3093",
        start_ms=0,
        end_ms=1000,
        confidence=1,
        tokens=[
            AlignedToken("W", "W", 0, 100, 1),
            AlignedToken("i", "i", 100, 200, 1),
            AlignedToken("\u6f22", "\u304b\u3093", 200, 1000, 1),
        ],
    )
    widths = {"W": 30.0, "i": 5.0, "\u6f22": 20.0}

    placements = module.ruby_placements(
        line,
        play_res_x=200,
        baseline_y=100,
        base_font_size=20,
        center_x=100,
        letter_spacing=10,
        measure_text=lambda text: sum(widths[character] for character in text),
    )

    assert placements[0].x == 128


def test_explicit_pronunciation_segments_define_ruby_ranges() -> None:
    line = AlignedLine(
        surface="泣き声",
        reading="なきごえ",
        start_ms=0,
        end_ms=1000,
        confidence=1.0,
        tokens=[
            AlignedToken(
                "泣き声",
                "なきごえ",
                0,
                1000,
                1.0,
                pronunciation_segments=[
                    PronunciationSegment(0, 1, "な", True),
                    PronunciationSegment(1, 2, "き", False),
                    PronunciationSegment(2, 3, "ごえ", True),
                ],
            )
        ],
    )

    placements = importlib.import_module("app.subtitle.ruby").ruby_placements(
        line,
        play_res_x=300,
        baseline_y=100,
        base_font_size=20,
        center_x=150,
    )

    assert [placement.text for placement in placements] == ["な", "ごえ"]


def test_atomic_pronunciation_segment_covers_the_whole_surface() -> None:
    line = AlignedLine(
        surface="80億分の1",
        reading="にこから",
        start_ms=0,
        end_ms=1000,
        confidence=1.0,
        tokens=[
            AlignedToken(
                "80億分の1",
                "にこから",
                0,
                1000,
                1.0,
                pronunciation_segments=[
                    PronunciationSegment(0, 6, "にこから", True)
                ],
            )
        ],
    )

    placements = importlib.import_module("app.subtitle.ruby").ruby_placements(
        line,
        play_res_x=300,
        baseline_y=100,
        base_font_size=20,
        center_x=150,
    )

    assert [(placement.text, placement.token_index) for placement in placements] == [
        ("にこから", 0)
    ]
