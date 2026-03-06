from pathlib import Path

from maque.web.tile_assets import check_tile_assets, required_tile_codes


def test_required_tile_codes_cover_current_rules():
    codes = required_tile_codes()
    assert "1T" in codes
    assert "9B" in codes
    assert "EW" in codes
    assert "WB" in codes
    assert "back" in codes


def test_check_tile_assets_reports_missing(tmp_path: Path):
    (tmp_path / "1T.png").write_bytes(b"x")
    status = check_tile_assets(tmp_path)
    assert status["all_present"] is False
    assert "1T" not in status["missing_codes"]
    assert "back" in status["missing_codes"]
