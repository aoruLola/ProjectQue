from maque.rules import evaluate_hu


def test_normal_hu():
    hand = [
        "1T", "2T", "3T",
        "4T", "5T", "6T",
        "7T", "8T", "9T",
        "2B", "3B", "4B",
        "5B", "5B",
    ]
    result = evaluate_hu(hand)
    assert result.is_hu
    assert result.pattern == "normal"


def test_pengpeng_hu():
    hand = [
        "1T", "1T", "1T",
        "2T", "2T", "2T",
        "3B", "3B", "3B",
        "RD", "RD", "RD",
        "9B", "9B",
    ]
    result = evaluate_hu(hand)
    assert result.is_hu
    assert result.pattern == "pengpenghu"


def test_qixiaodui():
    hand = [
        "1T", "1T", "2T", "2T", "3T", "3T", "4B", "4B",
        "5B", "5B", "6B", "6B", "EW", "EW",
    ]
    result = evaluate_hu(hand)
    assert result.is_hu
    assert result.pattern == "qixiaodui"


def test_haohua_qixiaodui():
    hand = [
        "1T", "1T", "1T", "1T",
        "2T", "2T", "3T", "3T",
        "4B", "4B", "5B", "5B", "6B", "6B",
    ]
    result = evaluate_hu(hand)
    assert result.is_hu
    assert result.pattern == "haohua_qixiaodui"


def test_ghost_wildcard_hu():
    hand = [
        "1T", "2T", "WB",
        "4T", "5T", "6T",
        "7T", "8T", "9T",
        "2B", "3B", "4B",
        "5B", "5B",
    ]
    result = evaluate_hu(hand)
    assert result.is_hu
    assert not result.is_wugui

