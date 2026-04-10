"""Microlearn API server — serves cards, records engagement."""

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from server.db import (
    init_db, index_cards, index_concepts, get_all_cards, get_card,
    get_cards_by_concept, record_engagement, search_cards,
)

# Try to import feed, fall back to simple ordering
try:
    from engine.feed import get_feed, get_concept_feed
    HAS_FEED = True
except ImportError:
    HAS_FEED = False


class MicrolearnHandler(SimpleHTTPRequestHandler):
    """Serves the PWA and handles API requests."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/feed":
            limit = int(params.get("limit", [20])[0])
            if HAS_FEED:
                cards = get_feed(limit=limit)
            else:
                cards = get_all_cards()[:limit]
            self._json_response(cards)

        elif path == "/api/cards":
            cards = get_all_cards()
            self._json_response(cards)

        elif path.startswith("/api/cards/"):
            card_id = path.split("/api/cards/")[1]
            card = get_card(card_id)
            if card:
                self._json_response(card)
            else:
                self._json_response({"error": "not found"}, 404)

        elif path.startswith("/api/concepts/"):
            concept = path.split("/api/concepts/")[1].rstrip("/")
            parts = concept.split("/")
            concept_slug = parts[0]
            if len(parts) > 1 and parts[1] == "cards":
                if HAS_FEED:
                    cards = get_concept_feed(concept_slug)
                else:
                    cards = get_cards_by_concept(concept_slug)
                self._json_response(cards)
            else:
                cards = get_cards_by_concept(concept_slug)
                self._json_response(cards)

        elif path == "/api/search":
            q = params.get("q", [""])[0]
            if q:
                results = search_cards(q)
                self._json_response(results)
            else:
                self._json_response([])

        else:
            # Serve static files from project root
            self.directory = str(PROJECT_ROOT)
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"
        data = json.loads(body)

        if path == "/api/engagement":
            card_id = data.get("card_id", "")
            event = data.get("event", "")
            duration_ms = data.get("duration_ms", 0)
            metadata = json.dumps(data.get("metadata", {}))

            if card_id and event:
                record_engagement(card_id, event, duration_ms, metadata)
                self._json_response({"ok": True})
            else:
                self._json_response({"error": "card_id and event required"}, 400)

        elif path == "/api/reindex":
            n = index_cards()
            index_concepts()
            self._json_response({"indexed": n})

        else:
            self._json_response({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    init_db()
    n = index_cards()
    index_concepts()
    print(f"Indexed {n} cards")

    port = 8899
    server = HTTPServer(("", port), MicrolearnHandler)
    print(f"Microlearn server running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
