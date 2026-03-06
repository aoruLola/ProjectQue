from maque.agents.human import HumanAgent


def test_format_meld_summary_uses_space_and_pipe_separator():
    public_melds = {
        "E": [
            {"kind": "PENG", "tiles": ["3B", "3B", "3B"], "from": "S"},
            {"kind": "GANG_MING", "tiles": ["4T", "4T", "4T", "4T"], "from": "W"},
        ],
        "S": [],
        "W": [],
        "N": [],
    }

    expected = " ".join([HumanAgent._tile_text_cn("3B")] * 3) + " | " + " ".join([HumanAgent._tile_text_cn("4T")] * 4)
    summary = HumanAgent._format_meld_summary(public_melds, "E")

    assert summary == expected


def test_format_meld_summary_returns_empty_marker_when_no_melds():
    summary = HumanAgent._format_meld_summary({"E": []}, "E")
    assert summary == "(无)"


def test_tile_color_mapping_for_discards():
    assert HumanAgent._tile_color("3B") == "cyan"
    assert HumanAgent._tile_color("4T") == "green"
    assert HumanAgent._tile_color("RD") == "red"
