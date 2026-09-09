"""
Agent — the core financial research agent with tool calling.

Builds the agent with:
    - LLM (MLX placeholder)
    - Tools (stock lookup, news fetcher, document retriever)
    - System prompt (tool sequencing, source attribution)
    - Conversation memory (last 10 turns)
"""

from typing import Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from src.llm.model import get_llm
from src.tools.stock_lookup import get_stock_price
from src.tools.news_fetcher import get_market_news
from src.tools.document_retriever import retrieve_financial_docs
from src.agent.prompts import get_system_prompt

import config


class FinancialResearchAgent:
    """
    Financial Research Agent that orchestrates LLM + Tools + RAG.

    Handles:
        - Query classification (live data vs document data vs both)
        - Tool calling in correct sequence
        - Source attribution in responses
        - Conversation memory
        - Disclaimer injection
    """

    def __init__(self):
        self.llm = get_llm()
        self.tools: Dict[str, BaseTool] = {
            "get_stock_price": get_stock_price,
            "get_market_news": get_market_news,
            "retrieve_financial_docs": retrieve_financial_docs,
        }
        self.system_prompt = get_system_prompt()
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10  # Keep last 10 turns

    def _classify_query(self, query: str) -> List[str]:
        """
        Classify what tools the query needs.

        Returns a list of tool names to call.
        Uses keyword heuristics for fast classification
        (no LLM call needed — keeps latency low).
        """
        query_lower = query.lower()
        tools_needed = []

        # ── Live data indicators ─────────────────────────────────────
        live_keywords = [
            "current", "today", "now", "live", "price", "stock",
            "market", "trading", "share price", "quote", "ticker",
            "how much", "what is the price", "market cap", "volume",
        ]
        if any(kw in query_lower for kw in live_keywords):
            tools_needed.append("get_stock_price")

        # ── News indicators ──────────────────────────────────────────
        news_keywords = [
            "news", "recent", "latest", "headlines", "announcement",
            "report", "event", "development", "update",
        ]
        if any(kw in query_lower for kw in news_keywords):
            tools_needed.append("get_market_news")

        # ── Document data indicators ─────────────────────────────────
        doc_keywords = [
            "revenue", "earnings", "profit", "loss", "annual",
            "quarterly", "q1", "q2", "q3", "q4", "fiscal",
            "balance sheet", "income statement", "cash flow",
            "expense ratio", "nav", "aum", "fund", "portfolio",
            "risk factor", "management", "guidance", "outlook",
            "document", "report", "filing", "10-k", "10-q",
        ]
        if any(kw in query_lower for kw in doc_keywords):
            tools_needed.append("retrieve_financial_docs")

        # If no classification matched, default to document search + stock
        if not tools_needed:
            tools_needed = ["retrieve_financial_docs"]

        return tools_needed

    def _extract_ticker(self, query: str) -> Optional[str]:
        """
        Try to extract a stock ticker from the query.
        Looks for common patterns like AAPL, GOOGL, RELIANCE.NS, etc.
        """
        import re

        # Pattern: uppercase 1-5 letter word optionally followed by .NS/.BO
        ticker_pattern = r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b'
        matches = re.findall(ticker_pattern, query.upper())

        # Filter out common English words that look like tickers
        stop_words = {
            "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
            "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET",
            "HAS", "HIM", "HIS", "HOW", "ITS", "MAY", "NEW", "OLD",
            "SEE", "NOW", "WAY", "WHO", "DID", "LET", "SAY", "SHE",
            "USE", "HER", "WHAT", "WHEN", "FROM", "HAVE", "THIS",
            "WILL", "WITH", "THAN", "THAT", "THEM", "BEEN", "SOME",
        }

        for match in matches:
            if match not in stop_words and len(match) >= 2:
                return match

        return None

    def query(self, user_query: str) -> str:
        """
        Process a user query through the agent.

        Steps:
            1. Classify what tools are needed
            2. Extract ticker if relevant
            3. Call tools in sequence (document first, then live)
            4. Combine results with LLM
            5. Add source attribution and disclaimers

        Args:
            user_query: The user's natural language question.

        Returns:
            The agent's grounded, source-attributed response.
        """
        # Step 1: Classify query
        tools_needed = self._classify_query(user_query)
        ticker = self._extract_ticker(user_query)

        # Step 2: Call tools and collect results
        tool_results = {}

        # Call document tool first (faster — local lookup)
        if "retrieve_financial_docs" in tools_needed:
            try:
                result = retrieve_financial_docs.invoke({"query": user_query})
                tool_results["documents"] = result
            except Exception as e:
                tool_results["documents"] = f"Error retrieving documents: {e}"

        # Call live data tools
        if "get_stock_price" in tools_needed and ticker:
            try:
                result = get_stock_price.invoke({"ticker": ticker})
                tool_results["stock_price"] = result
            except Exception as e:
                tool_results["stock_price"] = f"Error fetching stock data: {e}"

        if "get_market_news" in tools_needed:
            search_term = ticker or user_query
            try:
                result = get_market_news.invoke({"query": search_term})
                tool_results["news"] = result
            except Exception as e:
                tool_results["news"] = f"Error fetching news: {e}"

        # Step 3: Build prompt with tool results
        prompt = self._build_agent_prompt(user_query, tool_results)

        # Step 4: Generate response
        response = self.llm.invoke(prompt)

        # Step 5: Update conversation history
        self._update_history(user_query, response)

        return response

    def _build_agent_prompt(
        self, query: str, tool_results: Dict[str, str]
    ) -> str:
        """Build the full prompt including system prompt, context, and query."""
        parts = [self.system_prompt, ""]

        # Add conversation history for context
        if self.conversation_history:
            parts.append("## Recent Conversation")
            for turn in self.conversation_history[-5:]:
                parts.append(f"User: {turn['user']}")
                parts.append(f"Assistant: {turn['assistant'][:300]}...")
                parts.append("")

        # Add tool results
        if tool_results:
            parts.append("## Data Retrieved")
            for source, data in tool_results.items():
                parts.append(f"### {source.replace('_', ' ').title()}")
                parts.append(data)
                parts.append("")

        # Add the current query
        parts.append(f"## Current Question")
        parts.append(f"User: {query}")
        parts.append("")
        parts.append("Please provide a comprehensive, source-attributed answer:")

        return "\n".join(parts)

    def _update_history(self, user_query: str, response: str):
        """Update conversation history, keeping the last N turns."""
        self.conversation_history.append({
            "user": user_query,
            "assistant": response,
        })
        # Trim to max history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()

    def get_tools_list(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())


# ─── Factory ─────────────────────────────────────────────────────────────────

_agent_instance: Optional[FinancialResearchAgent] = None


def get_agent() -> FinancialResearchAgent:
    """Get the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = FinancialResearchAgent()
    return _agent_instance
