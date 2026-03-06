from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..cli import DEFAULT_PLAY_MODEL
from .session import SessionConfig, SessionManager
from .tile_assets import check_tile_assets


class SessionCreateRequest(BaseModel):
    model: str = Field(default=DEFAULT_PLAY_MODEL)
    base_url: str | None = Field(default=None)
    seed: int | None = Field(default=None)


def create_app(session_manager: SessionManager | None = None) -> FastAPI:
    app = FastAPI(title="MAQUE Web")
    manager = session_manager or SessionManager()
    app.state.session_manager = manager

    repo_root = Path(__file__).resolve().parents[2]
    static_dir = Path(__file__).resolve().parent / "static"
    assets_dir = repo_root / "assets"
    tiles_dir = assets_dir / "tiles"
    app.state.asset_status = check_tile_assets(tiles_dir)

    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def web_index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "sessions": manager.count(),
            "asset_status": app.state.asset_status,
        }

    @app.post("/api/sessions")
    def create_session(req: SessionCreateRequest) -> dict[str, Any]:
        session = manager.create_session(
            SessionConfig(
                model=req.model,
                base_url=req.base_url,
                seed=req.seed,
                player_seat="E",
                log_dir="./logs",
            )
        )
        return {
            "session_id": session.session_id,
            "player_seat": session.config.player_seat,
            "asset_status": app.state.asset_status,
            "snapshot": session.snapshot(),
        }

    @app.websocket("/ws/sessions/{session_id}")
    async def session_ws(websocket: WebSocket, session_id: str) -> None:
        session = manager.get_session(session_id)
        if session is None:
            await websocket.close(code=4404, reason="session not found")
            return

        await websocket.accept()
        cursor = 1

        async def send_error(message: str) -> None:
            await websocket.send_json({"type": "error", "payload": {"message": message}})

        while True:
            events, next_cursor = session.get_events_since(cursor)
            for event in events:
                await websocket.send_json(event)
            cursor = next_cursor

            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=0.2)
            except asyncio.TimeoutError:
                if session.is_closed():
                    continue
                continue
            except WebSocketDisconnect:
                break
            except Exception:
                await send_error("消息格式错误")
                continue

            msg_type = str(payload.get("type") or "").strip()
            if msg_type == "join":
                await websocket.send_json({"type": "joined", "payload": session.snapshot()})
                continue
            if msg_type == "action":
                ok, err = session.submit_action(
                    action=str(payload.get("action") or ""),
                    tile=payload.get("tile"),
                )
                if not ok and err:
                    await send_error(err)
                continue
            if msg_type == "start_ma":
                ok, err = session.request_start_ma()
                if not ok and err:
                    await send_error(err)
                continue
            if msg_type == "next_round":
                ok, err = session.request_next_round()
                if not ok and err:
                    await send_error(err)
                continue
            if msg_type == "quit":
                session.request_quit()
                await websocket.send_json({"type": "info", "payload": {"message": "已退出会话"}})
                break

            await send_error("未知消息类型")

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run("maque.web.server:create_app", factory=True, host=host, port=port, reload=False)
