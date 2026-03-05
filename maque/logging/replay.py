from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..state import ActionEvent, GameState


class EventLogger:
    def __init__(self, log_dir: str | Path) -> None:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = path / f"game_{stamp}.jsonl"

    def log(self, state: GameState, event: ActionEvent) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": asdict(event),
            "state_digest": {
                "turn": state.turn,
                "current": state.current,
                "wall": len(state.wall),
                "discards": {
                    seat: list(state.discard_view.recent_by_player[seat]) for seat in ("E", "S", "W", "N")
                },
                "history_count": len(state.discard_view.history_compact),
            },
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")


class ReplayView:
    @staticmethod
    def replay(log_path: str | Path) -> list[str]:
        lines: list[str] = []
        path = Path(log_path)
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                data = json.loads(raw)
                ev = data["event"]
                tile = f" {ev['tile']}" if ev.get("tile") else ""
                frm = f" <- {ev['from_player']}" if ev.get("from_player") else ""
                lines.append(f"T{ev['turn']} {ev['player']} {ev['action']}{tile}{frm}")
        return lines
