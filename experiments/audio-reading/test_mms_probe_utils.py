from mms_probe_utils import labels_by_id


def test_labels_by_id_inverts_sparse_token_mapping():
    mapping = {"-": 0, "a": 1, "z": 3}
    assert labels_by_id(mapping) == ["-", "a", "", "z"]
