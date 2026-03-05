from maque.scoring import compute_settlement
from maque.rules import HuResult


def test_baopei_single_payer_covers_all():
    hu = HuResult(is_hu=True, pattern="pengpenghu", is_wugui=False, source="zimo")
    st = compute_settlement(winner="E", hu_result=hu, ma_tiles=["1W"], baopei_payer="S")

    assert st.final_delta_by_player["E"] > 0
    assert st.final_delta_by_player["S"] < 0
    assert st.final_delta_by_player["W"] == 0
    assert st.final_delta_by_player["N"] == 0
    assert sum(st.final_delta_by_player.values()) == 0


def test_non_baopei_all_losers_pay():
    hu = HuResult(is_hu=True, pattern="normal", is_wugui=True, source="zimo")
    st = compute_settlement(winner="E", hu_result=hu, ma_tiles=["2W", "3W"], baopei_payer=None)

    assert st.final_delta_by_player["S"] < 0
    assert st.final_delta_by_player["W"] < 0
    assert st.final_delta_by_player["N"] < 0
    assert sum(st.final_delta_by_player.values()) == 0

