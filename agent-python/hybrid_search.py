"""
============================================================
🔍 HYBRID SEARCH ENGINE
============================================================
Routes between two best-in-class search APIs based on query intent:

  Tavily  → Recent news, current events, prices, trending topics
  Exa     → Deep research, explanations, concepts, technical docs

Routing is pattern-based (zero extra LLM tokens) with automatic
fallback: if either engine fails, the other is tried.

Usage (as a LangChain tool):
    from hybrid_search import hybrid_web_search
    tools = [hybrid_web_search, ...]
============================================================
"""

import os
import re
import logging
from datetime import datetime

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Routing patterns ──────────────────────────────────────────────────────────

# Queries matching these → Tavily (recency-first)
_TAVILY_PATTERNS = re.compile(
    r"\b(latest|recent|news|today|current(ly)?|price|weather|breaking|trending|"
    r"update|right now|live|just announced|stock price|crypto|earnings|"
    r"released|launched|happened|this week|this month|forecast|scores?|results?)\b",
    re.IGNORECASE,
)

# Queries matching these → Exa (semantic-first)
_EXA_PATTERNS = re.compile(
    r"\b(explain|what is|what are|how does|how do|overview|background|history|"
    r"compare|comparison|analyz[es]|analysis|research|academic|technical|"
    r"documentation|deep dive|comprehensive|mechanism|concept|theory|"
    r"why does|why do|architecture|design|principles|guide|tutorial|"
    r"difference between|versus|review|survey|state of the art|benchmark)\b",
    re.IGNORECASE,
)


def _route_query(query: str) -> str:
    """
    Returns 'tavily' or 'exa' based on query intent.

    Decision logic:
      - Recent signals only  → tavily
      - Deep signals only    → exa
      - Both or neither      → tavily (safer general-purpose default)
    """
    is_recent = bool(_TAVILY_PATTERNS.search(query))
    is_deep = bool(_EXA_PATTERNS.search(query))

    if is_deep and not is_recent:
        return "exa"
    return "tavily"


# ── Tavily client ─────────────────────────────────────────────────────────────

_tavily_client = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    time_range="month",
)


def _run_tavily(query: str) -> str:
    current_date = datetime.now().strftime("%B %Y")
    dated_query = f"{query} {current_date}"
    results = _tavily_client.invoke(dated_query)
    if isinstance(results, list):
        return "\n\n".join(
            f"Source: {r.get('url', 'N/A')}\n{r.get('content', '')}"
            for r in results
        )
    return str(results)


# ── Exa client ────────────────────────────────────────────────────────────────

def _run_exa(query: str) -> str:
    try:
        from exa_py import Exa
    except ImportError:
        logger.warning("exa-py not installed — falling back to Tavily")
        return _run_tavily(query)

    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        logger.warning("EXA_API_KEY not set — falling back to Tavily")
        return _run_tavily(query)

    exa = Exa(api_key=api_key)
    response = exa.search_and_contents(
        query,
        num_results=5,
        use_autoprompt=True,
        highlights={"num_sentences": 3, "highlights_per_url": 2},
    )

    parts = []
    for r in response.results:
        highlights = getattr(r, "highlights", []) or []
        snippet = " ... ".join(highlights) if highlights else (getattr(r, "text", "") or "")[:400]
        parts.append(f"Source: {r.url}\nTitle: {r.title}\n{snippet}")

    return "\n\n".join(parts) if parts else "No results found."


# ── Public @tool ──────────────────────────────────────────────────────────────

@tool
def hybrid_web_search(query: str) -> str:
    """Search the web for information. Automatically routes between two engines:
    - Tavily: for recent news, current events, prices, trending topics
    - Exa:    for deep research, explanations, concepts, technical documentation

    Args:
        query: The search query
    """
    engine = _route_query(query)
    logger.info(f"🔍 HybridSearch → {engine.upper()}: '{query}'")

    try:
        result = _run_exa(query) if engine == "exa" else _run_tavily(query)
        return f"[{engine.upper()}]\n{result}"
    except Exception as primary_err:
        fallback = "tavily" if engine == "exa" else "exa"
        logger.warning(f"{engine} failed ({primary_err}), trying {fallback}")
        try:
            result = _run_tavily(query) if fallback == "tavily" else _run_exa(query)
            return f"[{fallback.upper()} fallback]\n{result}"
        except Exception as fallback_err:
            return f"Search failed on both engines. Last error: {fallback_err}"
