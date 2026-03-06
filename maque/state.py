from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from .tiles import SEATS


@dataclass
class Meld:
    kind: str
    tiles: list[str]
    from_seat: str | None = None


@dataclass
class PlayerState:
    seat: str
    hand: list[str] = field(default_factory=list)
    melds: list[Meld] = field(default_factory=list)
    discards: list[str] = field(default_factory=list)


@dataclass
class DiscardViewState:
    recent_by_player: dict[str, deque[str]] = field(
        default_factory=lambda: {seat: deque(maxlen=2) for seat in SEATS}
    )
    global_discards: list[str] = field(default_factory=list)
    history_compact: list[str] = field(default_factory=list)

    def add_discard(self, seat: str, tile: str) -> None:
        self.recent_by_player[seat].append(tile)
        self.global_discards.append(tile)
        # Backward-compatible alias now representing global discard timeline.
        self.history_compact = self.global_discards


@dataclass
class ActionEvent:
    turn: int
    player: str
    action: str
    tile: str | None = None
    from_player: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    llm_raw: str | None = None


@dataclass
class RoundContext:
    gang_baopay_source: dict[str, str] = field(default_factory=dict)
    feed_streak: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    last_feeder_for_receiver: dict[str, str] = field(default_factory=dict)

    def register_feed_set(self, feeder: str, receiver: str) -> None:
        previous = self.last_feeder_for_receiver.get(receiver)
        key = (feeder, receiver)
        if previous == feeder:
            self.feed_streak[key] += 1
        else:
            if previous is not None and previous != feeder:
                self.feed_streak[(previous, receiver)] = 0
            self.feed_streak[key] = 1
        self.last_feeder_for_receiver[receiver] = feeder

    def should_baopay_for_feed(self, feeder: str, receiver: str) -> bool:
        return self.feed_streak.get((feeder, receiver), 0) >= 3


@dataclass
class GameState:
    players: dict[str, PlayerState]
    wall: list[str]
    dealer: str = "E"
    current: str = "E"
    turn: int = 0
    winner: str | None = None
    win_source: str | None = None
    win_tile: str | None = None
    last_discard: tuple[str, str] | None = None
    discard_view: DiscardViewState = field(default_factory=DiscardViewState)
    events: list[ActionEvent] = field(default_factory=list)
    context: RoundContext = field(default_factory=RoundContext)

    def next_turn(self) -> None:
        self.turn += 1
