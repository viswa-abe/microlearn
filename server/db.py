"""SQLite data layer for Microlearn — card index, engagement, feed state."""

import sqlite3
import os
import yaml
import re
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent.parent / "data" / "microlearn.db"
CONTENT_DIR = Path(__file__).parent.parent / "content"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            concept TEXT NOT NULL,
            title TEXT NOT NULL,
            topic TEXT,
            depth INTEGER DEFAULT 1,
            idea TEXT,
            example TEXT,
            probe TEXT,
            connections TEXT,  -- JSON array
            source_type TEXT,
            source_id TEXT,
            file_path TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cluster TEXT,
            depth INTEGER DEFAULT 1,
            connections TEXT,  -- JSON array of {to, weight}
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS engagement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL,
            event TEXT NOT NULL,  -- seen, swipe_left, swipe_right, tap, linger, probe_tap, voice
            duration_ms INTEGER,
            metadata TEXT,  -- JSON
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (card_id) REFERENCES cards(id)
        );

        CREATE TABLE IF NOT EXISTS feed_state (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_cards_concept ON cards(concept);
        CREATE INDEX IF NOT EXISTS idx_cards_topic ON cards(topic);
        CREATE INDEX IF NOT EXISTS idx_engagement_card ON engagement(card_id);
        CREATE INDEX IF NOT EXISTS idx_engagement_event ON engagement(event);

        -- Full-text search
        CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
            id, title, topic, idea, example, probe,
            content='cards',
            content_rowid='rowid'
        );
    """)
    conn.commit()
    conn.close()


def parse_card_file(path: Path) -> dict | None:
    """Parse a markdown card file with YAML frontmatter."""
    text = path.read_text()
    # Split frontmatter
    match = re.match(r'^---\n(.+?)\n---\n(.+)', text, re.DOTALL)
    if not match:
        return None

    meta = yaml.safe_load(match.group(1))
    body = match.group(2)

    # Extract sections
    sections = {}
    current = None
    lines = []
    for line in body.split('\n'):
        if line.startswith('## '):
            if current:
                sections[current] = '\n'.join(lines).strip()
            current = line[3:].strip().lower()
            lines = []
        else:
            lines.append(line)
    if current:
        sections[current] = '\n'.join(lines).strip()

    card_id = path.stem
    return {
        'id': card_id,
        'concept': meta.get('concept', ''),
        'title': meta.get('title', ''),
        'topic': meta.get('topic', ''),
        'depth': meta.get('depth', 1),
        'idea': sections.get('idea', ''),
        'example': sections.get('example', ''),
        'probe': sections.get('probe', ''),
        'connections': str(meta.get('connections', [])),
        'source_type': meta.get('source', {}).get('type', '') if isinstance(meta.get('source'), dict) else '',
        'source_id': meta.get('source', {}).get('id', '') if isinstance(meta.get('source'), dict) else '',
        'file_path': str(path),
        'created_at': meta.get('created', datetime.now(timezone.utc).strftime('%Y-%m-%d')),
    }


def index_cards():
    """Read all card markdown files and index them into SQLite."""
    cards_dir = CONTENT_DIR / "cards"
    if not cards_dir.exists():
        return

    conn = get_db()
    count = 0
    for path in sorted(cards_dir.glob("*.md")):
        card = parse_card_file(path)
        if not card:
            continue
        conn.execute("""
            INSERT OR REPLACE INTO cards
            (id, concept, title, topic, depth, idea, example, probe,
             connections, source_type, source_id, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card['id'], card['concept'], card['title'], card['topic'],
            card['depth'], card['idea'], card['example'], card['probe'],
            card['connections'], card['source_type'], card['source_id'],
            card['file_path'], card['created_at'],
        ))
        # Update FTS
        conn.execute("INSERT OR REPLACE INTO cards_fts(id, title, topic, idea, example, probe) VALUES (?, ?, ?, ?, ?, ?)",
                     (card['id'], card['title'], card['topic'], card['idea'], card['example'], card['probe']))
        count += 1

    conn.commit()
    conn.close()
    return count


def index_concepts():
    """Read concept YAML files and index them."""
    concepts_dir = CONTENT_DIR / "concepts"
    if not concepts_dir.exists():
        return

    conn = get_db()
    for path in sorted(concepts_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        conn.execute("""
            INSERT OR REPLACE INTO concepts (id, name, cluster, depth, connections, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            path.stem,
            data.get('name', path.stem),
            data.get('cluster', ''),
            data.get('depth', 1),
            str(data.get('connections', [])),
            datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        ))

    conn.commit()
    conn.close()


def record_engagement(card_id: str, event: str, duration_ms: int = 0, metadata: str = "{}"):
    conn = get_db()
    conn.execute(
        "INSERT INTO engagement (card_id, event, duration_ms, metadata) VALUES (?, ?, ?, ?)",
        (card_id, event, duration_ms, metadata)
    )
    conn.commit()
    conn.close()


def search_cards(query: str, limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, topic, idea, example, probe FROM cards_fts WHERE cards_fts MATCH ? LIMIT ?",
        (query, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_cards() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM cards ORDER BY concept, depth").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_card(card_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_cards_by_concept(concept: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cards WHERE concept = ? ORDER BY depth", (concept,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_engagement_stats(card_id: str) -> dict:
    conn = get_db()
    rows = conn.execute(
        "SELECT event, COUNT(*) as count FROM engagement WHERE card_id = ? GROUP BY event",
        (card_id,)
    ).fetchall()
    conn.close()
    return {r['event']: r['count'] for r in rows}


if __name__ == "__main__":
    init_db()
    n = index_cards()
    index_concepts()
    print(f"Indexed {n} cards")
