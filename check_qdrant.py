"""Diagnose Qdrant Cloud connectivity issues."""
import os, time
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL     = os.environ["QDRANT_URL"]
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]

print(f"Connecting to: {QDRANT_URL}\n")

# Test 1: raw HTTPS reachability
print("=== Test 1: Raw HTTPS ping ===")
import httpx
try:
    r = httpx.get(QDRANT_URL, timeout=10)
    print(f"  ✅ Reachable — HTTP {r.status_code}")
except Exception as e:
    print(f"  ❌ {e}")

# Test 2: Qdrant client with longer timeout
print("\n=== Test 2: Qdrant client (30s timeout) ===")
from qdrant_client import QdrantClient
try:
    t0 = time.time()
    q = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )
    cols = q.get_collections()
    print(f"  ✅ Connected in {time.time()-t0:.1f}s")
    print(f"  Collections: {[c.name for c in cols.collections]}")
except Exception as e:
    print(f"  ❌ {e}")

# Test 3: check URL format
print("\n=== Test 3: URL format check ===")
if QDRANT_URL.endswith("/"):
    print("  ⚠  URL has trailing slash — remove it from .env")
else:
    print("  ✅ No trailing slash")
if ":6333" in QDRANT_URL:
    print("  ℹ  Port 6333 in URL — make sure your Qdrant cluster allows external port 6333")
if "localhost" in QDRANT_URL or "127.0.0.1" in QDRANT_URL:
    print("  ⚠  URL points to localhost — did you mean to use Qdrant Cloud?")