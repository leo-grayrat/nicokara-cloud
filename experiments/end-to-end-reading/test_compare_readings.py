from compare_readings import collect_target_readings


def test_collect_target_readings_finds_exact_tokens_and_provider() -> None:
    payload = {
        "provider": "local",
        "source_text": "歌声\n泣き声\nでも君は",
        "lines": [
            {
                "source": "歌声",
                "surface": "歌声",
                "reading": "うたごえ",
                "tokens": [{"surface": "歌声", "reading": "うたごえ"}],
            },
            {
                "source": "泣き声",
                "surface": "泣き声",
                "reading": "なきこえ",
                "tokens": [{"surface": "泣き声", "reading": "なきこえ"}],
            },
            {
                "source": "でも君は",
                "surface": "でも君は",
                "reading": "でもくんは",
                "tokens": [
                    {"surface": "でも", "reading": "でも"},
                    {"surface": "君", "reading": "くん"},
                    {"surface": "は", "reading": "は"},
                ],
            },
        ],
    }

    result = collect_target_readings(payload, ["歌声", "泣き声", "君"])

    assert result["provider"] == "local"
    assert result["targets"] == {
        "歌声": ["うたごえ"],
        "泣き声": ["なきこえ"],
        "君": ["くん"],
    }
