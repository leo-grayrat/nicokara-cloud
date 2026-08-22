from __future__ import annotations


def collapse_ctc_ids(frame_ids: list[int], labels: list[str], blank_id: int) -> str:
    """Collapse greedy CTC frame ids into a token string."""
    result: list[str] = []
    previous: int | None = None
    for token_id in frame_ids:
        if token_id != previous and token_id != blank_id:
            result.append(labels[token_id])
        previous = token_id
    return "".join(result)
