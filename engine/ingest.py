"""Signal ingestion — reads various sources and produces normalized signals."""

import json
from pathlib import Path


def ingest_bookmarks(bookmarks_json_path: str) -> list[dict]:
    """Read a TweetHoarder JSON export and extract interest signals.

    Each signal: {text, source_type, source_id, topics_hint}
    """
    path = Path(bookmarks_json_path)
    raw = json.loads(path.read_text())

    # TweetHoarder exports an array of tweet objects
    tweets = raw if isinstance(raw, list) else raw.get("data", raw.get("tweets", []))

    signals = []
    for tweet in tweets:
        # Handle both TweetHoarder formats
        text = tweet.get("full_text") or tweet.get("text", "")
        tweet_id = tweet.get("id_str") or tweet.get("id", "")

        # Extract hashtags as topic hints
        entities = tweet.get("entities", {})
        hashtags = [h.get("tag") or h.get("text", "") for h in entities.get("hashtags", [])]

        # Also pull from URLs / quoted tweet text if available
        quoted_text = ""
        if "quoted_status" in tweet:
            quoted_text = tweet["quoted_status"].get("full_text", "")
        if quoted_text:
            text = f"{text}\n\n> {quoted_text}"

        signals.append({
            "text": text.strip(),
            "source_type": "twitter_bookmark",
            "source_id": str(tweet_id),
            "topics_hint": hashtags,
        })

    return signals


def ingest_text(text: str, source_type: str = "manual") -> dict:
    """Ingest a manual text/thought drop as a signal."""
    return {
        "text": text.strip(),
        "source_type": source_type,
        "source_id": "",
        "topics_hint": [],
    }


def ingest_pdf(pdf_path: str) -> list[dict]:
    """Chunk a PDF into section signals (placeholder implementation).

    Uses simple page-based splitting. Replace with proper PDF parsing later.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    signals = []
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(path))
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                signals.append({
                    "text": text,
                    "source_type": "pdf",
                    "source_id": f"{path.stem}:page-{i + 1}",
                    "topics_hint": [],
                })
        doc.close()
    except ImportError:
        # Fallback: just register the PDF as a single signal
        signals.append({
            "text": f"[PDF content from {path.name} — PyMuPDF not installed for extraction]",
            "source_type": "pdf",
            "source_id": path.stem,
            "topics_hint": [],
        })

    return signals
