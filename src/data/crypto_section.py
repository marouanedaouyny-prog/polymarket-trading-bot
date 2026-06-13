"""
Fetch markets from Polymarket's public Crypto section page.

The public Gamma /markets feed does not always include the live crypto section
markets shown on polymarket.com/crypto. This module reads the page's embedded
Next.js query cache and normalizes its events into market dictionaries.
"""

import html
import json
from typing import Dict, List, Optional

import requests


def _extract_next_data(page_html: str) -> Optional[Dict]:
    marker = '<script id="__NEXT_DATA__"'
    start = page_html.find(marker)
    if start < 0:
        return None

    start = page_html.find(">", start)
    end = page_html.find("</script>", start)
    if start < 0 or end < 0:
        return None

    raw_json = html.unescape(page_html[start + 1:end])
    return json.loads(raw_json)


def _matching_json_object(text: str, start: int) -> Optional[str]:
    in_string = False
    escaped = False
    depth = 0

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return None


def _extract_streamed_query_states(page_html: str) -> List[Dict]:
    """Extract React-query states from current app-router streamed HTML."""
    decoded = (
        page_html
        .replace('\\\\\"', '"')
        .replace('\\\"', '"')
        .replace("\\/", "/")
    )
    states = []
    search_from = 0

    while True:
        key_index = decoded.find('"queryKey":[', search_from)
        if key_index < 0:
            break

        object_start = decoded.rfind('{"dehydratedAt"', 0, key_index)
        if object_start < 0:
            search_from = key_index + 12
            continue

        fragment = _matching_json_object(decoded, object_start)
        if not fragment:
            search_from = key_index + 12
            continue

        partial_end = fragment.find(',"queryKey"')
        if partial_end < 0:
            search_from = key_index + 12
            continue

        try:
            parsed = json.loads(fragment[:partial_end] + "}")
            data = parsed.get("state", {}).get("data")
            if isinstance(data, dict):
                states.append(data)
        except json.JSONDecodeError:
            pass

        search_from = key_index + 12

    return states


def _event_markets(event: Dict) -> List[Dict]:
    markets = event.get("markets") or []
    normalized = []

    for market in markets:
        if not isinstance(market, dict):
            continue

        item = dict(market)
        item.setdefault("question", market.get("question") or event.get("title", ""))
        item.setdefault("category", "crypto")
        item.setdefault("tags", event.get("tags") or [])
        item.setdefault("image", event.get("image"))
        item.setdefault("icon", event.get("icon"))

        if not item.get("endDate"):
            item["endDate"] = event.get("endDate")
        if not item.get("endDateIso"):
            item["endDateIso"] = event.get("endDate")
        if not item.get("volume"):
            item["volume"] = event.get("volume") or event.get("volume24hr")
        if not item.get("volume24hr"):
            item["volume24hr"] = event.get("volume24hr")
        if not item.get("liquidity"):
            item["liquidity"] = event.get("liquidity") or event.get("liquidityClob")

        item["sourceEventId"] = event.get("id")
        item["sourceEventSlug"] = event.get("slug")
        item["sourceEventTitle"] = event.get("title")
        item["source"] = "polymarket_crypto_page"
        normalized.append(item)

    return normalized


def fetch_crypto_section_markets(locale: str = "fr", limit: int = 200) -> List[Dict]:
    url = f"https://polymarket.com/{locale}/crypto" if locale else "https://polymarket.com/crypto"
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=30)
    response.raise_for_status()

    next_data = _extract_next_data(response.text)
    if next_data:
        queries = (
            next_data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
        )
        query_data = [query.get("state", {}).get("data") for query in queries]
    else:
        query_data = _extract_streamed_query_states(response.text)

    seen = set()
    markets = []

    for data in query_data:
        events = []

        if isinstance(data, dict) and "pages" in data:
            for page in data.get("pages") or []:
                if isinstance(page, dict):
                    events.extend(page.get("events") or [])
        elif isinstance(data, dict) and "markets" in data:
            events.append(data)

        for event in events:
            for market in _event_markets(event):
                market_key = (
                    market.get("conditionId")
                    or market.get("condition_id")
                    or market.get("id")
                    or market.get("slug")
                )
                if not market_key or market_key in seen:
                    continue
                seen.add(market_key)
                markets.append(market)
                if len(markets) >= limit:
                    return markets

    return markets
