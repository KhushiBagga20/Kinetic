"""
The automation loop — keeps every result ready so the user never has to ask.

One background thread, started with the web server:

    at start      load the local model in the background (if enabled)
    every minute  refresh live quotes for holdings, watchlist and indices
    every 5 min   rebuild the briefing: themes, exposure, forecasts, note

Pages read the latest results from `latest()`, which is instant. Anything that
changes the book (adding or removing a holding) calls `refresh_soon()` so the
next rebuild happens right away instead of waiting for the timer.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

import config

log = logging.getLogger("kinetic.automation")


def _stamp(seconds: float | None) -> str | None:
    if not seconds:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class Automation:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._rebuild_requested = True   # build once as soon as the loop starts
        self._building = False
        self._briefing: dict[str, Any] | None = None
        self._last_fast = 0.0
        self._last_slow = 0.0
        self._last_error = ""
        self._cycles = 0

    # -- lifecycle ---------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="kinetic-automation", daemon=True)
        self._thread.start()
        if config.AUTO_LOAD_MODEL:
            threading.Thread(target=self._load_model, name="kinetic-model-load", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def refresh_soon(self) -> None:
        """Ask for a full rebuild on the next tick (e.g. after the book changed)."""
        self._rebuild_requested = True
        self._wake.set()

    # -- reading -----------------------------------------------------------------

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return self._briefing

    def status(self) -> dict[str, Any]:
        next_slow = (self._last_slow + config.AUTO_SLOW_SEC) if self._last_slow else None
        return {
            "enabled": config.AUTOMATION_ENABLED,
            "running": self.running,
            "building": self._building,
            "cycles": self._cycles,
            "fast_every_sec": config.AUTO_FAST_SEC,
            "slow_every_sec": config.AUTO_SLOW_SEC,
            "last_quotes": _stamp(self._last_fast),
            "last_rebuild": _stamp(self._last_slow),
            "next_rebuild": _stamp(next_slow),
            "last_error": self._last_error,
            "has_briefing": self._briefing is not None,
        }

    # -- work --------------------------------------------------------------------

    def rebuild(self) -> dict[str, Any]:
        """Build a fresh briefing now (also used directly when automation is off)."""
        from src import briefing

        self._building = True
        try:
            result = briefing.build()
            with self._lock:
                self._briefing = result
            self._last_error = ""
            return result
        finally:
            self._building = False
            self._last_slow = time.time()

    def _refresh_quotes(self) -> None:
        from src import portfolio, preferences
        from src.market import prefetch

        symbols = [h.symbol for h in portfolio.load_holdings()]
        symbols += preferences.load().watchlist
        symbols += config.INDEX_SYMBOLS
        prefetch(symbols)
        self._last_fast = time.time()

    def _load_model(self) -> None:
        from src.llm import engine

        try:
            engine().load()
            log.info("Model loaded in the background")
            self.refresh_soon()  # rebuild so the briefing gets its written note
        except Exception as exc:
            log.warning("Background model load failed: %s", exc)

    def _run(self) -> None:
        while not self._stop.is_set():
            now = time.time()
            try:
                if now - self._last_fast >= config.AUTO_FAST_SEC:
                    self._refresh_quotes()
                if self._rebuild_requested or now - self._last_slow >= config.AUTO_SLOW_SEC:
                    self._rebuild_requested = False
                    self.rebuild()
                self._cycles += 1
            except Exception as exc:  # the loop must never die on one bad fetch
                self._last_error = f"{type(exc).__name__}: {exc}"
                log.warning("Automation cycle failed: %s", self._last_error)
                self._last_fast = time.time()  # back off until the next tick instead of retrying at once
            self._wake.wait(timeout=5)
            self._wake.clear()


_automation = Automation()


def automation() -> Automation:
    """The single process-wide automation loop."""
    return _automation
