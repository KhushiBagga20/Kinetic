"""
Fast unit tests — no network, no model weights.

    python -m pytest tests -q      (or: python tests/test_pipeline.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.agent import ResearchAgent
from src.llm import Piece, Reply, StreamParser, ToolCall, parse_tool_call
from src.rag.chunking import split_text
from src.rag.retriever import BM25, tokenize


# ─── Chunking ─────────────────────────────────────────────────────────────────

def test_tables_stay_intact() -> None:
    document = (
        "ITEM 7. RESULTS\n\n"
        "Revenue grew across both segments.\n\n"
        "Segment Revenue (USD millions)\n"
        "Products      1,428   1,201   18.9%\n"
        "Services        612     540   13.3%\n"
        "Total         2,040   1,741   17.2%\n"
    )
    chunks = split_text(document, {"source": "test"})
    table_chunk = next(c for c in chunks if "1,428" in c.text)
    assert "Services" in table_chunk.text and "Total" in table_chunk.text, "table row split"
    assert table_chunk.metadata["section"] == "ITEM 7. RESULTS"


def test_heading_breaks_overlap() -> None:
    document = "SECTION A\n\nAlpha content here.\n\nSECTION B\n\nBeta content here.\n"
    chunks = split_text(document, {"source": "test"}, size=60, overlap=20)
    for chunk in chunks:
        if chunk.metadata.get("section") == "SECTION B":
            assert "Alpha" not in chunk.text, "content leaked across a heading"


# ─── Lexical search ───────────────────────────────────────────────────────────

def test_bm25_ranks_exact_terms_first() -> None:
    corpus = [
        "Operating margin expanded to 31.4% in fiscal 2024.",
        "The company sells consumer hardware and services.",
        "Free cash flow reached 107 billion USD.",
    ]
    scores = BM25(corpus).scores("operating margin fiscal 2024")
    assert scores.argmax() == 0
    assert scores[1] < scores[0]


def test_tokenizer_keeps_financial_tokens() -> None:
    assert "31.4%" in tokenize("Operating margin was 31.4% this year")
    assert "fy2024" in tokenize("Guidance for FY2024")


# ─── Gemma tool calls ─────────────────────────────────────────────────────────

def test_parse_tool_call_types() -> None:
    call = parse_tool_call('call:search_documents{deep:true,k:3,query:<|"|>Q2 revenue<|"|>}')
    assert call.name == "search_documents"
    assert call.arguments == {"deep": True, "k": 3, "query": "Q2 revenue"}


def test_stream_parser_handles_split_markers() -> None:
    parser = StreamParser()
    stream = (
        '<|channel>thought\nChecking the price.\n<channel|>'
        'One moment.<|tool_call>call:get_stock_quote{symbol:<|"|>AAPL<|"|>}<tool_call|>'
        "Apple trades at 315.34 USD."
    )
    for character in stream:  # worst case: one character per token
        parser.feed(character)
    parser.finish()

    assert parser.thought.strip() == "Checking the price."
    assert [c.name for c in parser.tool_calls] == ["get_stock_quote"]
    assert parser.tool_calls[0].arguments == {"symbol": "AAPL"}
    assert "315.34" in parser.answer and "<|tool_call>" not in parser.answer


# ─── Agent loop (LLM stubbed) ─────────────────────────────────────────────────

class StubLLM:
    """Two turns: call a tool, then answer using its result."""

    def __init__(self) -> None:
        self.is_loaded = True
        self.step = 0
        self._reply = Reply()
        self.saw_tool_result = False

    def stream(self, messages, tools=None, max_tokens=None, thinking=None):
        if self.step == 0:
            self.step = 1
            self._reply = Reply(
                text="", tool_calls=[ToolCall("get_market_movers", {"kind": "day_gainers"})]
            )
            yield Piece("answer", "Let me check. ")
            yield Piece("tool", "get_market_movers")
            return
        self.saw_tool_result = any(m.get("role") == "tool" for m in messages)
        self._reply = Reply(text="Here are the movers.", tokens=4, tokens_per_sec=30.0)
        for word in ["Here ", "are ", "the ", "movers."]:
            yield Piece("answer", word)

    def last_reply(self) -> Reply:
        return self._reply


def test_agent_runs_tool_then_answers(monkeypatch) -> None:
    import src.agent as agent_module

    stub = StubLLM()
    monkeypatch.setattr(agent_module, "engine", lambda: stub)
    monkeypatch.setattr(agent_module, "search_with_timing", lambda q, k=None: ([], 1.0))
    monkeypatch.setattr(agent_module.tools, "call", lambda name, args: "SIG +23.96%")

    events = list(ResearchAgent().stream("what is moving today?"))
    kinds = [event.kind for event in events]

    assert "tool_call" in kinds and "step_reset" in kinds
    assert stub.saw_tool_result, "the tool result was not fed back to the model"
    done = events[-1]
    assert done.kind == "done"
    assert done.text == "Here are the movers."
    assert done.data["tools_used"] == ["get_market_movers"]


# ─── Portfolio maths (market stubbed) ─────────────────────────────────────────

def test_portfolio_pricing_weights_and_fx(monkeypatch, tmp_path) -> None:
    import config
    from src import portfolio as portfolio_module

    monkeypatch.setattr(config, "PORTFOLIO_FILE", tmp_path / "portfolio.json")
    monkeypatch.setattr(config, "BASE_CURRENCY", "INR")

    class FakeQuote:
        def __init__(self, name, price, currency, change):
            self.name, self.price, self.currency = name, price, currency
            self.change, self.change_percent = change, change / price * 100
            self.market_state = "REGULAR"

    quotes = {
        "INFY.NS": FakeQuote("Infosys", 1000.0, "INR", 10.0),
        "AAPL": FakeQuote("Apple", 200.0, "USD", -2.0),
    }
    monkeypatch.setattr(portfolio_module, "get_quote", lambda s: quotes.get(s))
    monkeypatch.setattr(portfolio_module, "prefetch", lambda symbols, with_fundamentals=False: None)
    monkeypatch.setattr(portfolio_module, "get_fundamentals", lambda s: {"sector": "Technology"})
    monkeypatch.setattr(
        portfolio_module, "get_fx_rate", lambda base, quote: 1.0 if base == quote else 100.0
    )

    portfolio_module.save_holdings([
        portfolio_module.Holding("INFY.NS", 10, 900.0),   # 10,000 INR now, cost 9,000
        portfolio_module.Holding("AAPL", 5, 150.0),       # 1,000 USD -> 100,000 INR
    ])

    rows = {row.symbol: row for row in portfolio_module.positions()}
    assert rows["INFY.NS"].unrealised == pytest.approx(1000.0)
    assert rows["INFY.NS"].unrealised_percent == pytest.approx(11.111, rel=1e-3)
    # The US holding is ten times larger once converted at 100 INR per USD.
    assert rows["AAPL"].value_in_base == pytest.approx(100_000.0)
    assert rows["AAPL"].weight == pytest.approx(90.909, rel=1e-3)

    totals = portfolio_module.summary()
    assert totals["market_value"] == pytest.approx(110_000.0)
    assert totals["largest_position"] == "AAPL"


def test_blended_average_cost_on_topping_up(monkeypatch, tmp_path) -> None:
    import config
    from src import portfolio as portfolio_module

    monkeypatch.setattr(config, "PORTFOLIO_FILE", tmp_path / "portfolio.json")
    portfolio_module.add_holding("TCS.NS", 10, 2000.0)
    portfolio_module.add_holding("TCS.NS", 10, 3000.0)

    holding = portfolio_module.load_holdings()[0]
    assert holding.quantity == 20
    assert holding.average_cost == pytest.approx(2500.0)


# ─── Simulation and backtest (synthetic prices) ───────────────────────────────

def _synthetic_history(days: int = 400, drift: float = 0.0, seed: int = 3):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.012, days)))
    index = pd.date_range("2024-01-01", periods=days, freq="B")
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000},
        index=index,
    )


def test_monte_carlo_bands_are_ordered_and_odds_are_sane() -> None:
    import numpy as np
    from src import simulation

    returns = np.random.default_rng(1).normal(0, 0.01, 400)
    flat = simulation.monte_carlo(100.0, returns, 10, paths=800)
    assert len(flat["bands"]) == 11  # day 0 plus 10 sessions
    last = flat["bands"][-1]
    assert last["p5"] <= last["p16"] <= last["p50"] <= last["p84"] <= last["p95"]
    assert 0.35 < flat["probability_up"] < 0.65, "no drift should be close to a coin flip"

    tilted = simulation.monte_carlo(100.0, returns, 10, drift_per_day=0.003, paths=800)
    assert tilted["probability_up"] > flat["probability_up"]


def test_monte_carlo_refuses_thin_history() -> None:
    import numpy as np
    from src import simulation

    assert simulation.monte_carlo(100.0, np.zeros(10), 10) == {}
    assert simulation.monte_carlo(None, np.zeros(100), 10) == {}


def test_backtest_reports_skill_in_range() -> None:
    from src import simulation

    result = simulation.backtest(_synthetic_history(), horizon=10)
    assert result["available"]
    assert 0.0 <= result["skill"] <= 1.0
    assert 0.0 <= result["hit_rate"] <= 1.0
    assert 0.0 <= result["band_coverage"] <= 1.0


def test_backtest_needs_enough_history() -> None:
    from src import simulation

    assert not simulation.backtest(_synthetic_history(days=50), horizon=10)["available"]


# ─── Themes and exposure ──────────────────────────────────────────────────────

def test_keyword_themes_match_whole_words() -> None:
    from src.market import Article
    from src.themes import keyword_themes

    def headline(title: str) -> Article:
        return Article(title=title, publisher="t", published="", url="", summary="", provider="t")

    found = keyword_themes([headline("RBI holds repo rate steady"), headline("Company said profits rose")])
    names = [item["theme"] for item in found]
    assert "interest rate changes" in names
    assert "AI and technology spending" not in names, "'ai' must not match inside 'said'"


def test_exposure_direction_labels() -> None:
    from src.exposure import _direction

    assert _direction(0.4, True) == "tailwind"
    assert _direction(-0.4, True) == "headwind"
    assert _direction(0.05, True) == "mixed"
    assert _direction(0.9, False) == "watch"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
