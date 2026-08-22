from dataclasses import dataclass

import pytest

from candidate_score import weighted_span_score


@dataclass
class FakeSpan:
    score: float
    frames: int

    def __len__(self) -> int:
        return self.frames


def test_weighted_span_score_uses_frame_duration():
    spans = [FakeSpan(0.9, 1), FakeSpan(0.3, 3)]
    assert weighted_span_score(spans) == pytest.approx(0.45)
