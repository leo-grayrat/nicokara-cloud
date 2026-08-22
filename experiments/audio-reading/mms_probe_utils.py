from __future__ import annotations


def labels_by_id(token_dict: dict[str, int]) -> list[str]:
    """Invert an MMS token dictionary into an id-indexed label table."""
    labels = [""] * (max(token_dict.values()) + 1)
    for label, token_id in token_dict.items():
        labels[token_id] = label
    return labels
