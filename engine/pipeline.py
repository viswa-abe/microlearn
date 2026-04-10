"""Orchestrator — runs the full ingest -> extract -> research -> generate -> index pipeline."""

import argparse
import sys
from pathlib import Path

# Add project root to path
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.ingest import ingest_bookmarks, ingest_text, ingest_pdf
from engine.research import extract_concepts, research_concept
from engine.generate import generate_cards, CONTENT_DIR
from server.db import init_db, index_cards, index_concepts


def run_pipeline(source_path: str, source_type: str = "bookmarks"):
    """Run the full pipeline: ingest -> extract concepts -> research -> generate cards -> index.

    Args:
        source_path: Path to source file (bookmarks JSON, PDF, or text file).
        source_type: One of "bookmarks", "pdf", "text".
    """
    # 1. Ingest
    print(f"[1/5] Ingesting {source_type} from {source_path}...")
    if source_type == "bookmarks":
        signals = ingest_bookmarks(source_path)
    elif source_type == "pdf":
        signals = ingest_pdf(source_path)
    elif source_type == "text":
        text = Path(source_path).read_text()
        signals = [ingest_text(text)]
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    print(f"   -> {len(signals)} signals extracted")

    if not signals:
        print("No signals found. Exiting.")
        return

    # 2. Extract concepts
    print("[2/5] Extracting concepts...")
    concepts = extract_concepts(signals)
    print(f"   -> {len(concepts)} concepts identified")

    for c in concepts:
        print(f"      - {c.get('name', '?')} ({c.get('cluster', '?')})")

    # 3. Research each concept
    print("[3/5] Researching concepts...")
    output_dir = str(CONTENT_DIR / "cards")
    all_created_files = []

    for i, concept in enumerate(concepts):
        print(f"   [{i + 1}/{len(concepts)}] Researching: {concept.get('name', '?')}...")
        research = research_concept(concept)

        # Carry cluster forward if research doesn't include it
        if "cluster" not in research:
            research["cluster"] = concept.get("cluster", "")

        # 4. Generate cards
        print(f"   [{i + 1}/{len(concepts)}] Generating cards...")
        files = generate_cards(research, output_dir)
        all_created_files.extend(files)
        print(f"      -> {len(files)} files created")

    # 5. Index into SQLite
    print("[5/5] Indexing into database...")
    init_db()
    card_count = index_cards()
    index_concepts()
    print(f"   -> {card_count} cards indexed")

    print(f"\nPipeline complete. {len(all_created_files)} files created:")
    for f in all_created_files:
        print(f"  {f}")


def main():
    parser = argparse.ArgumentParser(
        description="Microlearn card generation pipeline",
        prog="python -m engine.pipeline",
    )
    parser.add_argument(
        "--source", required=True,
        help="Path to source file (bookmarks JSON, PDF, or text file)",
    )
    parser.add_argument(
        "--type", dest="source_type", default="bookmarks",
        choices=["bookmarks", "pdf", "text"],
        help="Type of source (default: bookmarks)",
    )
    args = parser.parse_args()
    run_pipeline(args.source, args.source_type)


if __name__ == "__main__":
    main()
