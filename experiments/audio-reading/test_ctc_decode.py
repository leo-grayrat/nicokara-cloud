from ctc_decode import collapse_ctc_ids


def test_collapses_repeated_frames_and_removes_blank():
    labels = ["-", "a", "i", "k"]
    assert collapse_ctc_ids([0, 1, 1, 0, 2, 2, 0, 3, 3], labels, 0) == "aik"


def test_blank_separates_same_character_repetition():
    labels = ["-", "a"]
    assert collapse_ctc_ids([1, 1, 0, 1, 1], labels, 0) == "aa"


def test_keeps_nonblank_character_order():
    labels = ["-", "m", "e", "z", "a", "t"]
    frame_ids = [1, 1, 0, 2, 2, 3, 0, 4, 4, 1, 0, 2, 5, 4]
    assert collapse_ctc_ids(frame_ids, labels, 0) == "mezameta"
