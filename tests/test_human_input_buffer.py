from maque.agents.human import HumanAgent


class _FakeMsvcrt:
    def __init__(self, keys: list[bytes]) -> None:
        self._keys = list(keys)
        self.read_count = 0

    def kbhit(self) -> bool:
        return bool(self._keys)

    def getch(self) -> bytes:
        self.read_count += 1
        return self._keys.pop(0)


def test_drain_windows_input_buffer_consumes_all_keys():
    fake = _FakeMsvcrt([b"a", b"\r", b"\xe0"])
    drained = HumanAgent._drain_windows_input_buffer(fake)

    assert drained == 3
    assert fake.read_count == 3
    assert fake.kbhit() is False


def test_drain_windows_input_buffer_empty():
    fake = _FakeMsvcrt([])
    drained = HumanAgent._drain_windows_input_buffer(fake)

    assert drained == 0
    assert fake.read_count == 0
