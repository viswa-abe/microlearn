"""Feed algorithm — blends cards from multiple sources with weighted selection."""

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path for server.db import
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from server.db import get_db


def get_feed(limit: int = 20) -> list[dict]:
    """Return an ordered list of cards to show, blended from multiple sources.

    Blend weights:
        - Continue thread (40%): next card in the concept the user was last engaged with
        - Fresh (25%): cards from recently ingested signals
        - Bridge (15%): cards from concepts adjacent to engaged ones
        - Resurface (10%): cards seen 3+ days ago, different angle
        - Backfill (10%): fundamental cards for concepts user engaged with at higher depth
    """
    conn = get_db()

    # Calculate slot counts
    slots = {
        "continue": max(1, int(limit * 0.40)),
        "fresh": max(1, int(limit * 0.25)),
        "bridge": max(1, int(limit * 0.15)),
        "resurface": max(1, int(limit * 0.10)),
        "backfill": max(1, int(limit * 0.10)),
    }

    # Adjust to match exact limit
    total = sum(slots.values())
    if total < limit:
        slots["continue"] += limit - total
    elif total > limit:
        slots["continue"] -= total - limit

    feed = []
    seen_ids = set()

    # 1. Continue thread — next card in last-engaged concept
    continue_cards = _get_continue_cards(conn, slots["continue"], seen_ids)
    feed.extend(continue_cards)

    # 2. Fresh — recently created cards not yet seen
    fresh_cards = _get_fresh_cards(conn, slots["fresh"], seen_ids)
    feed.extend(fresh_cards)

    # 3. Bridge — cards from adjacent concepts
    bridge_cards = _get_bridge_cards(conn, slots["bridge"], seen_ids)
    feed.extend(bridge_cards)

    # 4. Resurface — cards seen 3+ days ago
    resurface_cards = _get_resurface_cards(conn, slots["resurface"], seen_ids)
    feed.extend(resurface_cards)

    # 5. Backfill — fundamental cards for concepts engaged at higher depth
    backfill_cards = _get_backfill_cards(conn, slots["backfill"], seen_ids)
    feed.extend(backfill_cards)

    conn.close()

    # If we don't have enough cards, fill remaining with any unseen cards
    if len(feed) < limit:
        conn = get_db()
        remaining = limit - len(feed)
        placeholders = ",".join("?" * len(seen_ids)) if seen_ids else "''"
        query = f"SELECT * FROM cards WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?"
        params = list(seen_ids) + [remaining]
        rows = conn.execute(query, params).fetchall()
        feed.extend([dict(r) for r in rows])
        conn.close()

    return feed[:limit]


def get_concept_feed(concept: str) -> list[dict]:
    """Return depth-ordered cards for a specific concept."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cards WHERE concept = ? ORDER BY depth, created_at",
        (concept,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_continue_cards(conn, limit: int, seen_ids: set) -> list[dict]:
    """Get next cards in the concept the user was last engaged with."""
    # Find the most recently engaged concept
    row = conn.execute("""
        SELECT c.concept, MAX(e.created_at) as last_engaged
        FROM engagement e
        JOIN cards c ON c.id = e.card_id
        GROUP BY c.concept
        ORDER BY last_engaged DESC
        LIMIT 1
    """).fetchone()

    if not row:
        return []

    concept = row["concept"]

    # Find the max depth seen in this concept
    depth_row = conn.execute("""
        SELECT MAX(c.depth) as max_depth
        FROM engagement e
        JOIN cards c ON c.id = e.card_id
        WHERE c.concept = ?
    """, (concept,)).fetchone()

    max_seen_depth = depth_row["max_depth"] if depth_row and depth_row["max_depth"] else 0

    # Get next cards (unseen or deeper)
    rows = conn.execute("""
        SELECT * FROM cards
        WHERE concept = ? AND id NOT IN (
            SELECT DISTINCT card_id FROM engagement
        )
        ORDER BY depth
        LIMIT ?
    """, (concept, limit)).fetchall()

    cards = [dict(r) for r in rows]
    for c in cards:
        seen_ids.add(c["id"])
    return cards


def _get_fresh_cards(conn, limit: int, seen_ids: set) -> list[dict]:
    """Get recently created cards not yet seen."""
    placeholders = ",".join("?" * len(seen_ids)) if seen_ids else "''"
    query = f"""
        SELECT * FROM cards
        WHERE id NOT IN ({placeholders})
        AND id NOT IN (SELECT DISTINCT card_id FROM engagement)
        ORDER BY created_at DESC
        LIMIT ?
    """
    params = list(seen_ids) + [limit]
    rows = conn.execute(query, params).fetchall()

    cards = [dict(r) for r in rows]
    for c in cards:
        seen_ids.add(c["id"])
    return cards


def _get_bridge_cards(conn, limit: int, seen_ids: set) -> list[dict]:
    """Get cards from concepts adjacent to ones the user has engaged with."""
    # Get engaged concepts
    rows = conn.execute("""
        SELECT DISTINCT c.concept, c.connections
        FROM engagement e
        JOIN cards c ON c.id = e.card_id
    """).fetchall()

    adjacent_concepts = set()
    for row in rows:
        conns = row["connections"]
        if conns:
            try:
                parsed = json.loads(conns.replace("'", '"'))
                if isinstance(parsed, list):
                    adjacent_concepts.update(parsed)
            except (json.JSONDecodeError, ValueError):
                pass

    if not adjacent_concepts:
        return []

    # Get unseen cards from adjacent concepts
    concept_placeholders = ",".join("?" * len(adjacent_concepts))
    seen_placeholders = ",".join("?" * len(seen_ids)) if seen_ids else "''"
    query = f"""
        SELECT * FROM cards
        WHERE concept IN ({concept_placeholders})
        AND id NOT IN ({seen_placeholders})
        ORDER BY depth
        LIMIT ?
    """
    params = list(adjacent_concepts) + list(seen_ids) + [limit]
    rows = conn.execute(query, params).fetchall()

    cards = [dict(r) for r in rows]
    for c in cards:
        seen_ids.add(c["id"])
    return cards


def _get_resurface_cards(conn, limit: int, seen_ids: set) -> list[dict]:
    """Get cards seen 3+ days ago for spaced repetition."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    seen_placeholders = ",".join("?" * len(seen_ids)) if seen_ids else "''"

    query = f"""
        SELECT c.* FROM cards c
        JOIN engagement e ON e.card_id = c.id
        WHERE e.created_at < ?
        AND c.id NOT IN ({seen_placeholders})
        GROUP BY c.id
        ORDER BY RANDOM()
        LIMIT ?
    """
    params = [cutoff] + list(seen_ids) + [limit]
    rows = conn.execute(query, params).fetchall()

    cards = [dict(r) for r in rows]
    for c in cards:
        seen_ids.add(c["id"])
    return cards


def _get_backfill_cards(conn, limit: int, seen_ids: set) -> list[dict]:
    """Get fundamental (depth=1) cards for concepts the user engaged with at higher depth."""
    seen_placeholders = ",".join("?" * len(seen_ids)) if seen_ids else "''"

    query = f"""
        SELECT c.* FROM cards c
        WHERE c.depth = 1
        AND c.concept IN (
            SELECT DISTINCT c2.concept FROM cards c2
            JOIN engagement e ON e.card_id = c2.id
            WHERE c2.depth > 1
        )
        AND c.id NOT IN (SELECT DISTINCT card_id FROM engagement)
        AND c.id NOT IN ({seen_placeholders})
        LIMIT ?
    """
    params = list(seen_ids) + [limit]
    rows = conn.execute(query, params).fetchall()

    cards = [dict(r) for r in rows]
    for c in cards:
        seen_ids.add(c["id"])
    return cards
