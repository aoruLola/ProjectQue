from __future__ import annotations

from pathlib import Path

from ..tiles import HONORS, SUITS


def required_tile_codes() -> list[str]:
    codes: list[str] = []
    for suit in SUITS:
        for n in range(1, 10):
            codes.append(f"{n}{suit}")
    codes.extend(HONORS)
    codes.append("back")
    return codes


def check_tile_assets(tiles_dir: Path) -> dict[str, object]:
    required = required_tile_codes()
    missing = [code for code in required if not (tiles_dir / f"{code}.png").exists()]
    return {
        "tiles_dir": str(tiles_dir),
        "required_codes": required,
        "missing_codes": missing,
        "all_present": len(missing) == 0,
    }
