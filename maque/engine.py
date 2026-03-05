from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agents.base import Agent, AgentDecision
from .rules import (
    DISCARD,
    GANG_AN,
    GANG_JIA,
    GANG_MING,
    HU,
    PASS,
    PENG,
    ActionOption,
    claim_order,
    evaluate_hu,
    legal_actions_after_draw,
    legal_actions_on_discard,
    legal_actions_on_qianggang,
    next_seat,
    remove_tiles,
    upgrade_peng_to_jiagang,
)
from .scoring import Settlement, compute_settlement
from .state import ActionEvent, GameState, Meld, PlayerState
from .tiles import SEATS, build_wall, sort_tiles


@dataclass
class GameResult:
    state: GameState
    settlement: Settlement | None
    log_path: str | None


class MahjongEngine:
    def __init__(
        self,
        agents: dict[str, Agent],
        event_logger: Any | None = None,
        seed: int | None = None,
        dealer: str = "E",
    ) -> None:
        self.agents = agents
        self.event_logger = event_logger
        self.seed = seed
        self.dealer = dealer

    def init_game(self) -> GameState:
        wall = build_wall(self.seed)
        players = {seat: PlayerState(seat=seat) for seat in SEATS}

        for _ in range(13):
            for seat in SEATS:
                players[seat].hand.append(wall.pop())

        players[self.dealer].hand.append(wall.pop())

        return GameState(players=players, wall=wall, dealer=self.dealer, current=self.dealer)

    def run(self) -> GameResult:
        state = self.init_game()
        settlement: Settlement | None = None

        phase = "after_draw"  # dealer already has 14 tiles
        while not state.winner and state.wall:
            if phase == "need_draw":
                self._draw_for_current(state)
                if state.winner:
                    break
                phase = "after_draw"
                continue

            if phase == "after_draw":
                phase = self._process_after_draw_phase(state)
                continue

            if phase == "discard_only":
                phase = self._process_discard_only_phase(state)
                continue

            raise RuntimeError(f"unknown phase: {phase}")

        if state.winner:
            hu_result = evaluate_hu(
                state.players[state.winner].hand,
                source=state.win_source or "zimo",
            )
            baopei_payer = None
            if state.win_source == "qianggang":
                baopei_payer = state.events[-1].from_player
            elif state.win_source == "zimo":
                baopei_payer = state.context.gang_baopay_source.get(state.winner)
                if not baopei_payer:
                    for feeder in SEATS:
                        if feeder == state.winner:
                            continue
                        if state.context.should_baopay_for_feed(feeder, state.winner):
                            baopei_payer = feeder
                            break

            ma_count = 2 if hu_result.is_wugui and state.win_source == "zimo" else 1
            ma_tiles = [state.wall.pop() for _ in range(min(ma_count, len(state.wall)))]
            settlement = compute_settlement(
                winner=state.winner,
                hu_result=hu_result,
                ma_tiles=ma_tiles,
                baopei_payer=baopei_payer,
            )

        log_path = str(self.event_logger.path) if self.event_logger else None
        return GameResult(state=state, settlement=settlement, log_path=log_path)

    def _draw_for_current(self, state: GameState) -> None:
        if not state.wall:
            return
        seat = state.current
        tile = state.wall.pop()
        state.players[seat].hand.append(tile)
        self._record_event(state, ActionEvent(turn=state.turn, player=seat, action="DRAW", tile=tile))

    def _process_after_draw_phase(self, state: GameState) -> str:
        seat = state.current
        player = state.players[seat]

        while True:
            options = legal_actions_after_draw(player)
            decision = self._decide(seat, state, options)

            if decision.action == HU:
                state.winner = seat
                state.win_source = "zimo"
                self._record_event(
                    state,
                    ActionEvent(
                        turn=state.turn,
                        player=seat,
                        action=HU,
                        metadata={"reason": decision.reason},
                        llm_raw=decision.raw,
                    ),
                )
                return "done"

            if decision.action == GANG_AN and decision.tile:
                remove_tiles(player.hand, decision.tile, 4)
                player.melds.append(Meld(kind=GANG_AN, tiles=[decision.tile] * 4, from_seat=None))
                self._record_event(
                    state,
                    ActionEvent(turn=state.turn, player=seat, action=GANG_AN, tile=decision.tile, llm_raw=decision.raw),
                )
                if not state.wall:
                    return "done"
                draw_tile = state.wall.pop()
                player.hand.append(draw_tile)
                self._record_event(
                    state,
                    ActionEvent(turn=state.turn, player=seat, action="DRAW", tile=draw_tile, metadata={"gang_draw": True}),
                )
                continue

            if decision.action == GANG_JIA and decision.tile:
                robbed = self._try_qianggang(state, seat, decision.tile)
                if robbed:
                    return "done"

                removed = False
                if decision.tile in player.hand:
                    player.hand.remove(decision.tile)
                    removed = True
                upgraded = upgrade_peng_to_jiagang(player, decision.tile)
                if not (removed and upgraded):
                    options = [o for o in options if o.action == DISCARD]
                    decision = self._decide(seat, state, options)
                else:
                    self._record_event(
                        state,
                        ActionEvent(turn=state.turn, player=seat, action=GANG_JIA, tile=decision.tile, llm_raw=decision.raw),
                    )
                    if not state.wall:
                        return "done"
                    draw_tile = state.wall.pop()
                    player.hand.append(draw_tile)
                    self._record_event(
                        state,
                        ActionEvent(turn=state.turn, player=seat, action="DRAW", tile=draw_tile, metadata={"gang_draw": True}),
                    )
                    continue

            if decision.action == DISCARD and decision.tile:
                self._discard_tile(state, seat, decision.tile, llm_raw=decision.raw)
                return self._resolve_discard_reactions(state, seat, decision.tile)

            fallback = [opt for opt in options if opt.action == DISCARD]
            if not fallback:
                raise RuntimeError("No discard option available")
            decision = self._decide(seat, state, fallback)
            self._discard_tile(state, seat, decision.tile, llm_raw=decision.raw)
            return self._resolve_discard_reactions(state, seat, decision.tile)

    def _process_discard_only_phase(self, state: GameState) -> str:
        seat = state.current
        player = state.players[seat]
        unique_tiles = sorted(set(player.hand))
        options = [ActionOption(DISCARD, t) for t in unique_tiles]
        decision = self._decide(seat, state, options)
        if decision.action != DISCARD or not decision.tile:
            decision = AgentDecision(action=DISCARD, tile=unique_tiles[0], reason="forced discard")
        self._discard_tile(state, seat, decision.tile, llm_raw=decision.raw)
        return self._resolve_discard_reactions(state, seat, decision.tile)

    def _resolve_discard_reactions(self, state: GameState, discarder: str, tile: str) -> str:
        state.context.gang_baopay_source.pop(discarder, None)

        for seat in claim_order(discarder):
            options = legal_actions_on_discard(state.players[seat], tile)
            if len(options) == 1:
                continue
            decision = self._decide(seat, state, options)

            if decision.action == GANG_MING:
                player = state.players[seat]
                remove_tiles(player.hand, tile, 3)
                player.melds.append(Meld(kind=GANG_MING, tiles=[tile] * 4, from_seat=discarder))
                state.context.register_feed_set(discarder, seat)
                state.context.gang_baopay_source[seat] = discarder
                self._record_event(
                    state,
                    ActionEvent(
                        turn=state.turn,
                        player=seat,
                        action=GANG_MING,
                        tile=tile,
                        from_player=discarder,
                        llm_raw=decision.raw,
                    ),
                )
                if not state.wall:
                    state.current = next_seat(seat)
                    state.next_turn()
                    return "need_draw"
                draw_tile = state.wall.pop()
                player.hand.append(draw_tile)
                self._record_event(
                    state,
                    ActionEvent(turn=state.turn, player=seat, action="DRAW", tile=draw_tile, metadata={"gang_draw": True}),
                )
                state.current = seat
                return "after_draw"

            if decision.action == PENG:
                player = state.players[seat]
                remove_tiles(player.hand, tile, 2)
                player.melds.append(Meld(kind=PENG, tiles=[tile] * 3, from_seat=discarder))
                state.context.register_feed_set(discarder, seat)
                self._record_event(
                    state,
                    ActionEvent(
                        turn=state.turn,
                        player=seat,
                        action=PENG,
                        tile=tile,
                        from_player=discarder,
                        llm_raw=decision.raw,
                    ),
                )
                state.current = seat
                return "discard_only"

        state.current = next_seat(discarder)
        state.next_turn()
        return "need_draw"

    def _try_qianggang(self, state: GameState, gang_seat: str, tile: str) -> bool:
        for seat in claim_order(gang_seat):
            player = state.players[seat]
            options = legal_actions_on_qianggang(player, tile)
            if len(options) == 1:
                continue
            decision = self._decide(seat, state, options)
            if decision.action == HU:
                state.winner = seat
                state.win_source = "qianggang"
                self._record_event(
                    state,
                    ActionEvent(
                        turn=state.turn,
                        player=seat,
                        action=HU,
                        tile=tile,
                        from_player=gang_seat,
                        metadata={"qianggang": True},
                        llm_raw=decision.raw,
                    ),
                )
                return True
        return False

    def _discard_tile(self, state: GameState, seat: str, tile: str, llm_raw: str | None = None) -> None:
        player = state.players[seat]
        if tile not in player.hand:
            tile = sort_tiles(player.hand)[0]
        player.hand.remove(tile)
        player.discards.append(tile)
        state.discard_view.add_discard(seat, tile)
        state.last_discard = (seat, tile)
        self._record_event(
            state,
            ActionEvent(turn=state.turn, player=seat, action=DISCARD, tile=tile, llm_raw=llm_raw),
        )

    def _decide(self, seat: str, state: GameState, options: list[ActionOption]) -> AgentDecision:
        agent = self.agents[seat]
        context = self._build_context_for_seat(state, seat)
        return agent.decide(seat=seat, context=context, legal_options=options)

    def _build_context_for_seat(self, state: GameState, seat: str) -> dict:
        player = state.players[seat]
        return {
            "self_hand": sort_tiles(player.hand),
            "self_melds": [{"kind": m.kind, "tiles": m.tiles, "from": m.from_seat} for m in player.melds],
            "public_discards": {s: list(state.players[s].discards) for s in SEATS},
            "discard_view": {
                "recent_by_player": {s: list(state.discard_view.recent_by_player[s]) for s in SEATS},
                "history_compact": list(state.discard_view.history_compact),
            },
            "last_discard": state.last_discard,
            "wall_count": len(state.wall),
            "turn": state.turn,
            "current": state.current,
            "last_event": (state.events[-1].__dict__ if state.events else None),
            "indexed_hand": [(idx + 1, tile) for idx, tile in enumerate(sort_tiles(player.hand))],
        }

    def _record_event(self, state: GameState, event: ActionEvent) -> None:
        state.events.append(event)
        if self.event_logger is not None:
            self.event_logger.log(state, event)

