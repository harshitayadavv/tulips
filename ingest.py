"""
ingest.py — Document ingestion pipeline
Reads .txt and .pdf files from docs/, chunks them, embeds with Gemini,
and upserts into a Qdrant collection named 'persona'.
"""

import os
import uuid
import math
import argparse
from pathlib import Path

from google import genai
from google.genai import types as genai_types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
from dotenv import load_dotenv

# ── PDF support ───────────────────────────────────────────────────────────────
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠  pdfplumber not installed — PDF files will be skipped.")

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]
QDRANT_URL      = os.environ["QDRANT_URL"]
QDRANT_API_KEY  = os.environ["QDRANT_API_KEY"]

COLLECTION_NAME = "persona"
EMBEDDING_MODEL = "models/gemini-embedding-2"   
EMBEDDING_DIM   = 3072
CHUNK_TOKENS    = 500
OVERLAP_TOKENS  = 50
DOCS_DIR        = Path("docs")

# ── Client setup ──────────────────────────────────────────────────────────────
# New google-genai SDK targets the stable v1 endpoint (fixes the v1beta 404)
gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"api_version": "v1"},
)
qdrant        = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_TOKENS, overlap: int = OVERLAP_TOKENS) -> list[str]:
    """
    Splits text into overlapping chunks by estimated token count.
    Splits on whitespace boundaries to avoid cutting mid-word.
    ~1.3 tokens per word on average.
    """
    words = text.split()
    chunks: list[str] = []
    words_per_chunk = max(1, int(chunk_size / 1.3))
    words_overlap   = max(0, int(overlap  / 1.3))

    start = 0
    while start < len(words):
        end   = min(start + words_per_chunk, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += words_per_chunk - words_overlap

    return chunks


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf(path: Path) -> str:
    if not PDF_SUPPORT:
        print(f"  ⚠  Skipping {path.name} (pdfplumber not installed)")
        return ""
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings using Gemini text-embedding-004 (new SDK)."""
    embeddings = []
    for text in texts:
        result = gemini_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        embeddings.append(result.embeddings[0].values)
    return embeddings


def ensure_collection():
    """Create the Qdrant collection if it doesn't already exist."""
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"✅ Created Qdrant collection '{COLLECTION_NAME}'")
    else:
        print(f"ℹ  Collection '{COLLECTION_NAME}' already exists — upserting into it.")


# ─────────────────────────────────────────────────────────────────────────────
# Main ingestion
# ─────────────────────────────────────────────────────────────────────────────

def ingest(docs_dir: Path = DOCS_DIR, wipe: bool = False):
    if not docs_dir.exists():
        print(f"❌ docs/ directory not found at: {docs_dir.resolve()}")
        return

    ensure_collection()

    if wipe:
        print("🗑  Wiping existing vectors…")
        qdrant.delete_collection(COLLECTION_NAME)
        ensure_collection()

    files = list(docs_dir.glob("*.txt")) + list(docs_dir.glob("*.pdf"))
    if not files:
        print("⚠  No .txt or .pdf files found in docs/")
        return

    total_points = 0

    for file_path in files:
        print(f"\n📄 Processing: {file_path.name}")

        if file_path.suffix == ".txt":
            raw_text = read_txt(file_path)
        elif file_path.suffix == ".pdf":
            raw_text = read_pdf(file_path)
        else:
            continue

        if not raw_text.strip():
            print(f"  ⚠  Empty content — skipping.")
            continue

        chunks = chunk_text(raw_text)
        print(f"  → {len(chunks)} chunks created")

        print(f"  → Embedding {len(chunks)} chunks via Gemini…")
        vectors = embed_texts(chunks)

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "filename":    file_path.name,
                        "chunk_index": idx,
                        "text":        chunk,
                    },
                )
            )

        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        total_points += len(points)
        print(f"  ✅ Upserted {len(points)} points for {file_path.name}")

    print(f"\n🎉 Ingestion complete — {total_points} total vectors in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest docs into Qdrant")
    parser.add_argument("--wipe", action="store_true",
                        help="Delete and recreate the collection before ingesting")
    parser.add_argument("--docs", type=Path, default=DOCS_DIR,
                        help="Path to docs folder (default: ./docs)")
    args = parser.parse_args()
    ingest(docs_dir=args.docs, wipe=args.wipe)