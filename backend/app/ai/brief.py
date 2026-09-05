"""
SignalGraph — AI-Generated Market Brief (Milestone 11, optional)
====================================================================
Exposes:
  generate_brief(feed_items: list[dict]) -> str
  validate_brief(text: str, feed_items: list[dict]) -> bool
  deterministic_brief(feed_items: list[dict]) -> str

A single, narrow AI capability layered on top of the already-complete,
already-verified feed: a two-to-three sentence synthesized overview
across the ranked items, generated from nothing but the ticker,
severity, and why-strings build_feed() already produces — never raw
price history, and never a buy/sell/price-direction opinion.

Zero-cost by default, same pattern as app/chat/assistant.py: without
ANTHROPIC_API_KEY configured, generate_brief() returns the
deterministic fallback immediately, with no API call attempted.
AI_BRIEF_ENABLED is a kill switch — set to "false" in the environment
to force the fallback path even with a key configured, without a
redeploy, if the feature misbehaves close to demo time.

The brief is validated before it is ever used, not trusted outright:
rejected if it names any instrument ticker absent from feed_items, or
contains "buy", "sell", or "should invest" (case-insensitive). A
rejected brief is discarded exactly as if the API call itself had
failed — this is what makes "the AI never controls market truth" a
verified property of the system, not an assumption about prompt
quality.
"""

import re

from app.config import ANTHROPIC_API_KEY, AI_BRIEF_ENABLED

MODEL = "claude-opus-5"
TIMEOUT_SECONDS = 4.0
TICKER_PATTERN = re.compile(r"\b[A-Z][A-Z&]{1,10}\.NS\b")
FORBIDDEN_SUBSTRINGS = ("buy", "sell", "should invest")

SYSTEM_PROMPT = (
    "You write a two-to-three sentence plain-language summary of a stock watchlist's "
    "current notable activity, for someone who has not seen the numbers. You are given "
    "only a list of tickers, their severity, and the specific reasons each was flagged — "
    "nothing else. Never invent a ticker, price, or event not in that list. Never give a "
    "buy, sell, hold, or price-direction opinion of any kind, and never predict what will "
    "happen next — describe only what was detected, never what to do about it."
)


def deterministic_brief(feed_items: list[dict]) -> str:
    """The non-AI fallback: a plain template over the highest-severity
    item's own why-strings. Used whenever the AI path is disabled,
    unavailable, or fails validation — and also by build_feed() for
    the very first request, before any background generation has run."""
    if not feed_items:
        return "Nothing unusual across your watchlist right now."
    top = max(feed_items, key=lambda item: item.get("severity", 0))
    why = "; ".join(top.get("why", [])) or "no specific reasons recorded"
    return f"Since your last check, the most notable activity was in {top['instrument']}: {why}."


def validate_brief(text: str, feed_items: list[dict]) -> bool:
    """False if `text` names a ticker not present in feed_items, or
    contains any forbidden advice-shaped substring. True otherwise."""
    if not text or not text.strip():
        return False

    lowered = text.lower()
    if any(bad in lowered for bad in FORBIDDEN_SUBSTRINGS):
        return False

    known_tickers = {item["instrument"] for item in feed_items}
    for mentioned in TICKER_PATTERN.findall(text):
        if mentioned not in known_tickers:
            return False

    return True


def generate_brief(feed_items: list[dict]) -> str:
    """
    Called from a background task (see routes/feed.py), never inline
    within the GET /api/feed request path. Falls back to the
    deterministic template on: AI_BRIEF_ENABLED=false, no API key, an
    empty feed, any API error or timeout, or failed validation.
    """
    fallback = deterministic_brief(feed_items)

    if not AI_BRIEF_ENABLED or not ANTHROPIC_API_KEY or not feed_items:
        return fallback

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=TIMEOUT_SECONDS)
        prompt_lines = "\n".join(
            f"- {item['instrument']}: severity {item['severity']} ({item.get('surface', '')}) — "
            + ("; ".join(item.get("why", [])) or "no specific reasons recorded")
            for item in feed_items
        )
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Notable activity:\n{prompt_lines}"}],
        )
        text = next((block.text for block in response.content if block.type == "text"), "")
    except Exception:
        return fallback

    if not validate_brief(text, feed_items):
        return fallback

    return text
