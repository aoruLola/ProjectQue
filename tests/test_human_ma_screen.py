from maque.agents.human import HumanAgent


def test_build_ma_screen_lines_contains_required_blocks():
    lines = HumanAgent._build_ma_screen_lines(
        winner_seat="S",
        winner_hand=["1T", "9T", "EW"],
        ma_tiles=["2T", "RD"],
        ma_unit_scores=[3, 6],
        round_delta={"E": -300, "S": 900, "W": -300, "N": -300},
        leaderboard={"E": 100, "S": 300, "W": -200, "N": -200},
        self_seat="E",
        self_hand=["1B", "2B", "3B"],
    )
    text = "\n".join(lines)

    assert "赢家手牌" in text
    assert "马牌" in text
    assert "排行榜" in text
    assert "自己手牌" in text
    assert "二索" in text
    assert "红中" in text
    assert "┌─────┐" in text
    assert "本局分数" in text
    assert "东风(E): -300" in text
