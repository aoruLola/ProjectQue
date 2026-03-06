from dataclasses import dataclass

from fastapi.testclient import TestClient

from maque.web.server import create_app


@dataclass
class _FakeConfig:
    player_seat: str = "E"


class _FakeSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.config = _FakeConfig()
        self._events = [
            {"seq": 1, "type": "state_update", "payload": {"phase": "playing"}},
        ]
        self.actions = []
        self.start_ma_called = 0
        self.next_round_called = 0
        self.quit_called = 0

    def snapshot(self):
        return {"session_id": self.session_id, "phase": "playing", "pending_options": []}

    def get_events_since(self, seq: int):
        events = [event for event in self._events if event["seq"] >= seq]
        return events, len(self._events) + 1

    def submit_action(self, action: str, tile: str | None = None):
        self.actions.append((action, tile))
        return True, None

    def request_start_ma(self):
        self.start_ma_called += 1
        return True, None

    def request_next_round(self):
        self.next_round_called += 1
        return True, None

    def request_quit(self):
        self.quit_called += 1

    def is_closed(self):
        return False


class _FakeSessionManager:
    def __init__(self):
        self.sessions = {}
        self.created = 0

    def create_session(self, _config):
        self.created += 1
        session_id = f"s{self.created}"
        session = _FakeSession(session_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def count(self):
        return len(self.sessions)


def test_create_session_and_health():
    manager = _FakeSessionManager()
    app = create_app(session_manager=manager)
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200

    res = client.post("/api/sessions", json={})
    assert res.status_code == 200
    payload = res.json()
    assert payload["session_id"] == "s1"
    assert payload["player_seat"] == "E"

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert health.json()["sessions"] == 1


def test_ws_handles_join_and_commands():
    manager = _FakeSessionManager()
    app = create_app(session_manager=manager)
    client = TestClient(app)

    payload = client.post("/api/sessions", json={}).json()
    sid = payload["session_id"]
    session = manager.sessions[sid]

    with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state_update"

        ws.send_json({"type": "join"})
        joined = ws.receive_json()
        assert joined["type"] == "joined"

        ws.send_json({"type": "action", "action": "DISCARD", "tile": "1T"})
        ws.send_json({"type": "start_ma"})
        ws.send_json({"type": "next_round"})
        ws.send_json({"type": "quit"})
        info = ws.receive_json()
        assert info["type"] == "info"

    assert session.actions == [("DISCARD", "1T")]
    assert session.start_ma_called == 1
    assert session.next_round_called == 1
    assert session.quit_called == 1
