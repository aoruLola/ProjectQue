from maque.cli import _table_setup
from maque.tiles import SEATS


def test_table_setup_ranges_and_dealer():
    dealer, d1, d2, seed = _table_setup(42)
    assert dealer in SEATS
    assert 1 <= d1 <= 6
    assert 1 <= d2 <= 6
    assert isinstance(seed, int)
    assert seed > 0
    assert (seed >> 48) == (d1 * 10 + d2)


def test_table_setup_deterministic_with_seed():
    a = _table_setup(2026)
    b = _table_setup(2026)
    assert a == b
