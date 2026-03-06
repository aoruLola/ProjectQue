from maque.rules import HuResult
from maque.scoring import compute_settlement, ma_tile_face_value, ma_tile_unit_score


def test_ma_tile_face_value_mapping():
    assert ma_tile_face_value("1T") == 10
    assert ma_tile_face_value("1B") == 10
    assert ma_tile_face_value("9T") == 9
    assert ma_tile_face_value("EW") == 5
    assert ma_tile_face_value("RD") == 5


def test_ma_tile_unit_score_is_face_plus_one():
    assert ma_tile_unit_score("1T") == 11
    assert ma_tile_unit_score("2T") == 3
    assert ma_tile_unit_score("EW") == 6


def test_compute_settlement_uses_ma_unit_total():
    hu = HuResult(is_hu=True, pattern="normal", is_wugui=False, source="zimo")
    st = compute_settlement(winner="E", hu_result=hu, ma_tiles=["1T", "EW"], baopei_payer=None)

    assert st.ma_unit_scores == [11, 6]
    assert st.ma_unit_total == 17
    # base 1 + ma_unit_total 17 => per loser 18
    assert st.final_delta_by_player["E"] == 54
    assert st.final_delta_by_player["S"] == -18
    assert st.final_delta_by_player["W"] == -18
    assert st.final_delta_by_player["N"] == -18
