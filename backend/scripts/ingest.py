"""
Command-line ingestion.

    python scripts/ingest.py                     index data/documents/
    python scripts/ingest.py report.pdf notes.md index specific files
    python scripts/ingest.py --live NVDA AAPL    capture live market snapshots
    python scripts/ingest.py --status            show what is indexed
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.rag import ingest_directory, ingest_file, ingest_market_feed, sources, stats


def main(argv: list[str]) -> int:
    if "--status" in argv:
        counts = stats()
        print(f"Index at {counts['path']}")
        print(f"  documents:   {counts['documents']} chunks")
        print(f"  market feed: {counts['market_feed']} chunks")
        print(f"  embeddings:  {counts['embedding_model']}")
        for row in sources():
            print(f"  · {row['source']}: {row['chunks']} chunks")
        return 0

    if "--live" in argv:
        symbols = [a for a in argv[argv.index("--live") + 1:] if not a.startswith("-")]
        if not symbols:
            print("Give at least one symbol, e.g. --live NVDA AAPL")
            return 1
        for symbol in symbols:
            print(f"{symbol}: {ingest_market_feed(symbol)} live passages indexed")
        return 0

    paths = [a for a in argv if not a.startswith("-")]
    if paths:
        for path in paths:
            print(f"{path}: {ingest_file(path)} chunks")
        return 0

    print(f"Indexing {config.DOCUMENTS_DIR}")
    results = ingest_directory()
    if not results:
        print("No supported files found. Drop PDFs or text files in that folder first.")
        return 1
    for name, chunks in results.items():
        print(f"  {name}: {chunks} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
