from maque.rules import ActionOption
from maque.agents.human import HumanAgent
from maque.tiles import tile_text_cn


def test_tile_text_cn_for_suited_and_honor_tiles():
    assert tile_text_cn("9T") == "九索"
    assert tile_text_cn("9B") == "九筒"
    assert tile_text_cn("RD") == "红中"


def test_human_pretty_tile_uses_unified_cn_labels():
    assert HumanAgent._pretty_tile("8T") == "八索"
    assert HumanAgent._pretty_tile("3B") == "三筒"


def test_human_format_option_hides_raw_tile_code():
    text = HumanAgent._format_option(ActionOption("DISCARD", "9T"))
    assert "9T" not in text
    assert "九索" in text
