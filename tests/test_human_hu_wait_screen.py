from maque.agents.human import HumanAgent


def test_build_hu_wait_lines_contains_winner_and_ascii_hand():
    lines = HumanAgent._build_hu_wait_lines(
        winner_seat="S",
        winner_hand=["1T", "9T", "EW"],
    )
    text = "\n".join(lines)

    assert "胡牌" in text
    assert "南风" in text
    assert "赢家手牌" in text
    assert "┌─────┐" in text
    assert "买马计算公式" in text
    assert "单张马分" in text
