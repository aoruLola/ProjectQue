from __future__ import annotations

import json
import os
import re

from ..rules import ActionOption
from ..tiles import GHOST_TILE
from .base import AgentDecision
from .fallback import RuleSafeAgent


class OpenAILLMAgent:
    HOUSE_RULES = [
        "Zhaoqing Mahjong uses full self-draw only; no winning on other player's discard.",
        "No chi is allowed. On discard claims, only PASS/PENG/GANG_MING are possible.",
        "White board WB is ghost (wildcard). Prefer keeping WB; avoid discarding WB unless there is no alternative discard.",
        "Base winning shape is 4 sets + 1 pair; also support qixiaodui and pengpenghu.",
    ]

    def __init__(
        self,
        model: str,
        fallback: RuleSafeAgent | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.fallback = fallback or RuleSafeAgent()
        self.base_url = base_url
        self._client = None

    def decide(self, seat: str, context: dict, legal_options: list[ActionOption]) -> AgentDecision:
        if not legal_options:
            return AgentDecision(action="PASS", reason="no legal options")

        try:
            raw = self._call_openai(seat, context, legal_options)
            parsed = self._parse_response(raw)
            decision = self._validate(parsed, legal_options)
            decision = self._apply_house_policy(seat, context, legal_options, decision)
            decision.raw = raw
            return decision
        except Exception as exc:
            fallback = self.fallback.decide(seat, context, legal_options)
            fallback.raw = f"LLM_ERROR: {exc}"
            fallback.reason = f"fallback due to llm error: {exc}"
            return fallback

    def _call_openai(self, seat: str, context: dict, legal_options: list[ActionOption]) -> str:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("openai package is not installed") from exc
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")

            base_url = self._resolve_base_url()
            kwargs: dict[str, str] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = OpenAI(**kwargs)

        legal_payload = [{"action": o.action, "tile": o.tile} for o in legal_options]
        prompt = {
            "seat": seat,
            "visible_state": context,
            "legal_options": legal_payload,
            "house_rules": self.HOUSE_RULES,
            "instruction": "Choose exactly one legal option and return JSON only: {\"action\":\"...\",\"tile\":\"...\",\"reason\":\"...\"}",
        }

        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are a Mahjong bot for Zhaoqing Mahjong. Follow house_rules strictly. Respond with strict JSON only.",
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=True),
                },
            ],
        )

        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("empty LLM response")
        return content.strip()

    def _resolve_base_url(self) -> str | None:
        if self.base_url:
            return self.base_url
        env_url = os.getenv("MAQUE_OPENAI_BASE_URL")
        if env_url:
            return env_url
        return os.getenv("OPENAI_BASE_URL")

    @staticmethod
    def _parse_response(raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise RuntimeError("response is not valid JSON")
            return json.loads(match.group(0))

    @staticmethod
    def _validate(parsed: dict, legal_options: list[ActionOption]) -> AgentDecision:
        action = str(parsed.get("action", "")).upper().strip()
        tile = parsed.get("tile")
        if isinstance(tile, str):
            tile = tile.upper().strip()
        reason = str(parsed.get("reason", "llm decision"))

        legal = {(opt.action, opt.tile) for opt in legal_options}
        if (action, tile) in legal:
            return AgentDecision(action=action, tile=tile, reason=reason)

        # Allow tile-less match for actions like HU/PASS
        if (action, None) in legal:
            return AgentDecision(action=action, tile=None, reason=reason)

        raise RuntimeError(f"illegal action from llm: {action} {tile}")

    def _apply_house_policy(
        self,
        seat: str,
        context: dict,
        legal_options: list[ActionOption],
        decision: AgentDecision,
    ) -> AgentDecision:
        if decision.action != "DISCARD" or decision.tile != GHOST_TILE:
            return decision

        alternatives = [opt for opt in legal_options if opt.action == "DISCARD" and opt.tile != GHOST_TILE]
        if not alternatives:
            return decision

        safe = self.fallback.decide(seat, context, alternatives)
        if safe.action == "DISCARD" and safe.tile and safe.tile != GHOST_TILE:
            return AgentDecision(
                action="DISCARD",
                tile=safe.tile,
                reason=f"{decision.reason}; policy avoid discarding ghost",
            )
        return decision
