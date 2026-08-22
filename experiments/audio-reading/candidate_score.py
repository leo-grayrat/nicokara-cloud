from __future__ import annotations

from typing import Iterable, Protocol


class SpanLike(Protocol):
    score: float

    def __len__(self) -> int: ...


def weighted_span_score(spans: Iterable[SpanLike]) -> float:
    """Average token confidence weighted by aligned frame duration."""
    weighted = 0.0
    total_frames = 0
    for span in spans:
        frames = len(span)
        weighted += float(span.score) * frames
        total_frames += frames
    if total_frames <= 0:
        raise ValueError("candidate alignment contains no frames")
    return weighted / total_frames
