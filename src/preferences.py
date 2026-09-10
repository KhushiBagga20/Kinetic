"""
Preferences — who the user is and how they want the terminal to behave.

Stored in one local JSON file next to the portfolio, git-ignored, never sent
anywhere. Two kinds of setting live here:

    profile        name, base currency, horizon, risk appetite, watchlist —
                   used to personalise both the interface and the answers the
                   model gives
    accessibility  text size, contrast and motion, applied to the stylesheet

Everything has a sensible default, so the app is fully usable before anyone
fills anything in.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

import config

HORIZONS = ["Short term (weeks)", "Medium term (1-3 years)", "Long term (5 years+)"]
RISK_APPETITES = ["Conservative", "Balanced", "Aggressive"]
TEXT_SIZES = {"Normal": 1.0, "Large": 1.15, "Larger": 1.3}


@dataclass
class Preferences:
    # -- profile --------------------------------------------------------------
    name: str = ""
    base_currency: str = config.BASE_CURRENCY
    horizon: str = HORIZONS[2]
    risk_appetite: str = RISK_APPETITES[1]
    watchlist: list[str] = field(default_factory=list)
    # -- accessibility --------------------------------------------------------
    text_size: str = "Normal"
    high_contrast: bool = False
    reduce_motion: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def greeting_name(self) -> str:
        return self.name.split()[0] if self.name.strip() else ""

    def describe(self) -> str:
        """A one-paragraph description of the user, for the model's system prompt."""
        parts = []
        if self.name.strip():
            parts.append(f"The user's name is {self.name.strip()}.")
        parts.append(f"They think in {self.base_currency}.")
        parts.append(f"Their stated horizon is: {self.horizon.lower()}.")
        parts.append(f"Their stated risk appetite is: {self.risk_appetite.lower()}.")
        if self.watchlist:
            parts.append(f"They are watching: {', '.join(self.watchlist)}.")
        return " ".join(parts)


_PATH = config.PORTFOLIO_FILE.parent / "preferences.json"


def load() -> Preferences:
    """Read preferences from disk, falling back to defaults."""
    if not _PATH.exists():
        return Preferences()
    try:
        payload = json.loads(_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Preferences()
    defaults = Preferences()
    known = {f for f in defaults.as_dict()}
    return Preferences(**{k: v for k, v in payload.items() if k in known})


def save(preferences: Preferences) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(preferences.as_dict(), indent=2), encoding="utf-8")


def update(**changes: Any) -> Preferences:
    """Change a few fields and persist the result."""
    current = load()
    for key, value in changes.items():
        if hasattr(current, key):
            setattr(current, key, value)
    save(current)
    return current


def add_to_watchlist(symbol: str) -> Preferences:
    symbol = symbol.strip().upper()
    current = load()
    if symbol and symbol not in current.watchlist:
        current.watchlist.append(symbol)
        save(current)
    return current


def remove_from_watchlist(symbol: str) -> Preferences:
    current = load()
    current.watchlist = [s for s in current.watchlist if s != symbol.strip().upper()]
    save(current)
    return current
