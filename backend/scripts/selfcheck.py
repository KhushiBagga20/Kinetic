"""
Self-check — verify every part of the stack except the language model.

    python scripts/selfcheck.py

Confirms that live data is flowing, that retrieval works, that the tools and
the forecast engine return sensible output, and that the local model weights
are present. It never loads the model.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

PASS, FAIL = "  ok  ", " fail "


def check(label: str, function) -> bool:
    started = time.perf_counter()
    try:
        detail = function()
        elapsed = (time.perf_counter() - started) * 1000
        print(f"[{PASS}] {label:<28} {elapsed:7.0f} ms  {detail}")
        return True
    except Exception as exc:
        print(f"[{FAIL}] {label:<28}          {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    from src import portfolio, preferences, tools
    from src.market import get_fx_rate, get_history, get_movers, get_news, get_quote, resolve_symbol, session
    from src.prediction import forecast
    from src.rag import ingest_market_feed, retrieve, stats

    symbol = config.DEFAULT_SYMBOL
    results = []

    print(f"\nKinetic self-check — {config.APP_NAME}\n")

    results.append(check("live quote", lambda: f"{symbol} at {get_quote(symbol).price:,.2f}"))
    results.append(check("symbol resolution", lambda: f"'infosys' → {resolve_symbol('infosys')}"))
    results.append(check("price history", lambda: f"{len(get_history(symbol))} candles"))
    results.append(check("news feed", lambda: f"{len(get_news(symbol))} headlines"))
    results.append(check("screener", lambda: f"{len(get_movers('most_actives', 5))} movers"))
    results.append(check("exchange session", lambda: f"{session(symbol)['exchange']} {session(symbol)['label']}"))
    results.append(check("live FX", lambda: f"USD/INR {get_fx_rate('USD', 'INR'):,.2f}"))
    results.append(check("live ingestion", lambda: f"{ingest_market_feed(symbol)} passages indexed"))
    results.append(check("hybrid retrieval", lambda: f"{len(retrieve(f'{symbol} valuation and news'))} passages"))
    results.append(check("vector store", lambda: f"{stats()['documents']} doc / {stats()['market_feed']} live chunks"))
    results.append(check("forecast engine", lambda: forecast(symbol).signal))
    results.append(check("tool registry", lambda: f"{len(tools.schemas())} tools"))
    results.append(check("tool execution", lambda: tools.call("get_stock_quote", {"symbol": symbol}).splitlines()[0]))
    results.append(check("preferences store", lambda: f"profile for '{preferences.load().name or 'unnamed'}'"))
    results.append(check("portfolio pricing", lambda: f"{len(portfolio.positions())} positions priced"))
    results.append(check("portfolio exposure", lambda: f"{len(portfolio.exposure('rising interest rates'))} holdings matched"))

    from src import briefing, exposure, themes

    def simulation_check() -> str:
        result = forecast(symbol)
        return (
            f"{result.probability_up * 100:.0f}% up odds, backtest skill {result.skill:.2f}"
            if result.probability_up is not None
            else "no simulation (thin history)"
        )

    results.append(check("monte carlo + backtest", simulation_check))
    results.append(check("theme detection", lambda: f"{len(themes.detect_themes([symbol]))} themes"))
    results.append(check("automatic exposure", lambda: f"{len(exposure.auto_report()['themes'])} themes touch the book"))
    results.append(check("daily briefing", lambda: f"{len(briefing.build(write_note=False)['forecasts'])} holdings forecast"))

    def model_present() -> str:
        from huggingface_hub import try_to_load_from_cache

        path = Path(config.LLM_MODEL)
        if path.exists():
            return f"local path {path}"
        cached = try_to_load_from_cache(config.LLM_MODEL, "config.json")
        if isinstance(cached, str):
            return f"weights cached ({config.LLM_MODEL})"
        raise RuntimeError("weights not downloaded yet — they will be fetched on first load")

    results.append(check("local model weights", model_present))

    failures = results.count(False)
    print(f"\n{len(results) - failures}/{len(results)} checks passed\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
