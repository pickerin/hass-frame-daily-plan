import json
import threading

import pytest

import tv


class FakeArt:
    def __init__(self, current="SAM-1", slideshow=None, artmode="on", new_id="MY_F1"):
        self.current, self.slideshow, self.artmode, self.calls = current, slideshow or {"value": "off"}, artmode, []
        self.new_id = new_id

    def open(self): pass
    def close(self): pass
    def get_current(self): return {"content_id": self.current}
    def get_slideshow_status(self): return self.slideshow
    def get_artmode(self): return self.artmode
    def upload(self, data, **kw): self.calls.append(("upload", len(data))); return self.new_id
    def set_slideshow_status(self, duration, **kw): self.calls.append(("slideshow", duration, kw.get("category_id")))
    def select_image(self, cid, show=True): self.calls.append(("select", cid, show)); self.current = cid
    def delete_list(self, ids): self.calls.append(("delete", list(ids))); return True


def test_show_then_restore_round_trip(monkeypatch):
    art = FakeArt(slideshow={"value": "60", "type": "slideshow", "category_id": "STORE22_C0008_SC_480"})
    frame = tv.FrameTV("h", "t", "n", 1)
    monkeypatch.setattr(frame, "_art", lambda: art)
    state = frame.show_image(b"jpeg", tv.new_state())
    assert state["restore_id"] == "SAM-1" and state["plan_ids"] == ["MY_F1"]
    assert state["slideshow"]["category_id"] == "STORE22_C0008_SC_480"
    assert ("slideshow", 0, "STORE22_C0008_SC_480") in art.calls and ("select", "MY_F1", True) in art.calls
    state = frame.restore(state)
    assert ("select", "SAM-1", True) in art.calls and ("slideshow", 60, "STORE22_C0008_SC_480") in art.calls
    assert ("delete", ["MY_F1"]) in art.calls and state == {"plan_ids": [], "restore_id": "SAM-1", "slideshow": None}


def test_second_show_keeps_original_restore_id(monkeypatch):
    art = FakeArt(current="MY_F1", new_id="MY_F2")
    frame = tv.FrameTV("h", "t", "n", 1)
    monkeypatch.setattr(frame, "_art", lambda: art)
    state = frame.show_image(b"x", {"plan_ids": ["MY_F1"], "restore_id": "SAM-9", "slideshow": None})
    assert state["restore_id"] == "SAM-9" and ("delete", ["MY_F1"]) in art.calls


def test_errors_are_wrapped(monkeypatch):
    class Down(FakeArt):
        def open(self): raise OSError("down")
    frame = tv.FrameTV("h", "t", "n", 1)
    monkeypatch.setattr(frame, "_art", lambda: Down())
    with pytest.raises(tv.FrameTVError, match="cannot connect"):
        frame.art_mode()


def test_watchdog_aborts_hung_call(monkeypatch):
    class HungWS:
        def __init__(self): self.aborted = threading.Event()
        def abort(self): self.aborted.set()

    class Hung(FakeArt):
        connection = HungWS()
        def get_artmode(self):
            assert self.connection.aborted.wait(5), "watchdog never fired"
            raise OSError("socket closed")

    frame = tv.FrameTV("h", "t", "n", 1)
    frame.watchdog = 0.05
    monkeypatch.setattr(frame, "_art", lambda: Hung())
    with pytest.raises(tv.FrameTVError, match="did not answer within"):
        frame.art_mode()


class FakeWS:
    def __init__(self, events): self.events, self.closed = iter(events), False
    def recv(self): return json.dumps({"event": next(self.events), "data": {}})
    def close(self): self.closed = True


def test_open_tolerates_startup_noise(monkeypatch):
    ws = FakeWS(["ms.channel.connect", "ms.channel.clientDisconnect", "d2d_service_message", "ms.channel.ready"])
    monkeypatch.setattr(tv.websocket, "create_connection", lambda *a, **k: ws)
    art = tv._Art(host="h", port=8002, token="t", name="n", timeout=1)
    assert art.open() is ws


def test_open_fails_on_unexpected_event(monkeypatch):
    ws = FakeWS(["ms.channel.connect", "ms.channel.unauthorized"])
    monkeypatch.setattr(tv.websocket, "create_connection", lambda *a, **k: ws)
    art = tv._Art(host="h", port=8002, token="t", name="n", timeout=1)
    with pytest.raises(tv.exceptions.UnauthorizedError):
        art.open()
    assert ws.closed and art.connection is None
