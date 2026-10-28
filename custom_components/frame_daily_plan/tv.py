"""Samsung The Frame Art Mode client (sync; run through the executor).

Uses the samsungtvws library that Home Assistant already ships for its own
Samsung integration. Each call opens its own connection, so a sleeping TV costs
one timeout and never a stale socket.
"""

from __future__ import annotations

import logging
from typing import Any

from samsungtvws import SamsungTVWS
from samsungtvws.art import SamsungTVArt

_LOGGER = logging.getLogger(__name__)
PORT = 8002


class FrameTVError(Exception):
    """The TV could not be reached or refused the request."""


def pair(host: str, name: str, timeout: int) -> str:
    """Open the remote channel so the TV shows its Allow prompt; return the token."""
    try:
        remote = SamsungTVWS(host=host, port=PORT, name=name, timeout=timeout)
        remote.open()
        remote.close()
    except Exception as err:  # noqa: BLE001  the library raises many types
        raise FrameTVError(f"pairing failed: {err}") from err
    if not remote.token:
        raise FrameTVError("the TV did not hand out a token (Allow not pressed?)")
    return remote.token


def device_info(host: str, timeout: int) -> dict[str, Any]:
    """The TV's REST device record (model, wifiMac, FrameTVSupport...)."""
    try:
        return SamsungTVWS(host=host, port=PORT, timeout=timeout).rest_device_info()["device"]
    except Exception as err:  # noqa: BLE001
        raise FrameTVError(f"cannot reach {host}: {err}") from err


def _slideshow_args(status: dict[str, Any] | None) -> dict[str, str] | None:
    """What to send back to the TV to restart its "Display All" slideshow; None when off."""
    if not isinstance(status, dict):
        return None
    value = str(status.get("value", "off"))
    if not value.isdigit() or int(value) == 0:
        return None
    return {"value": value, "category_id": str(status.get("category_id", "")), "type": str(status.get("type", ""))}


def new_state() -> dict[str, Any]:
    return {"plan_ids": [], "restore_id": None, "slideshow": None}


class FrameTV:
    """One Frame, one paired client."""

    def __init__(self, host: str, token: str, name: str, timeout: int) -> None:
        self.host = host
        self.token = token
        self.name = name
        self.timeout = timeout

    def _art(self) -> SamsungTVArt:
        art = SamsungTVArt(host=self.host, port=PORT, token=self.token, name=self.name, timeout=self.timeout)
        try:
            art.open()
        except Exception as err:  # noqa: BLE001
            raise FrameTVError(f"cannot connect to {self.host}: {err}") from err
        return art

    def _run(self, fn):
        art = self._art()
        try:
            return fn(art)
        except FrameTVError:
            raise
        except Exception as err:  # noqa: BLE001
            raise FrameTVError(str(err) or type(err).__name__) from err
        finally:
            try:
                art.close()
            except Exception:  # noqa: BLE001
                pass

    def art_mode(self) -> bool:
        return self._run(lambda a: a.get_artmode() == "on")

    def set_art_mode(self, on: bool) -> None:
        self._run(lambda a: a.set_artmode(on))

    def show_image(self, jpeg: bytes, state: dict[str, Any]) -> dict[str, Any]:
        """Upload and show the plan, remembering what to put back. Returns the new state."""

        def go(a: SamsungTVArt) -> dict[str, Any]:
            current = (a.get_current() or {}).get("content_id")
            if current and current not in state["plan_ids"]:
                state["restore_id"] = current
            slideshow = _slideshow_args(a.get_slideshow_status())
            if slideshow:
                state["slideshow"] = slideshow
            content_id = a.upload(jpeg, matte="none", portrait_matte="none", file_type="jpg")
            state["plan_ids"].append(content_id)
            if slideshow:  # the TV's own rotation would replace the plan within the hour
                a.set_slideshow_status(0, category_id=slideshow["category_id"])
            a.select_image(content_id, show=a.get_artmode() == "on")  # never interrupt TV mode
            self._delete_plans(a, state, keep=content_id)
            return state

        return self._run(go)

    def restore(self, state: dict[str, Any]) -> dict[str, Any]:
        """Put the artwork and slideshow back, delete our plan images."""

        def go(a: SamsungTVArt) -> dict[str, Any]:
            if state.get("restore_id"):
                a.select_image(state["restore_id"], show=a.get_artmode() == "on")
            slideshow = state.get("slideshow")
            if slideshow:
                a.set_slideshow_status(int(slideshow["value"]), type=slideshow["type"] == "shuffleslideshow",
                                       category_id=slideshow["category_id"])
                state["slideshow"] = None
            self._delete_plans(a, state)
            return state

        return self._run(go)

    @staticmethod
    def _delete_plans(a: SamsungTVArt, state: dict[str, Any], keep: str | None = None) -> None:
        # Only images we uploaded ourselves are ever deleted.
        old = [i for i in state["plan_ids"] if i != keep]
        if old:
            try:
                a.delete_list(old)
                old = []
            except Exception as err:  # noqa: BLE001  retried next time
                _LOGGER.warning("Could not delete old plan images %s: %s", old, err)
        state["plan_ids"] = old + ([keep] if keep else [])
