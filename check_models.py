"""Run this to see exactly which embedding models your Gemini API key can access."""
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={"api_version": "v1"},
)

print("=== Models supporting embedContent ===")
for m in client.models.list():
    supported = getattr(m, "supported_actions", []) or []
    if "embedContent" in supported:
        print(f"  {m.name}")

print("\n=== Trying direct embed with 'models/text-embedding-004' ===")
try:
    r = client.models.embed_content(
        model="models/text-embedding-004",
        contents="hello world",
    )
    print("  ✅ Success:", r.embeddings[0].values[:3])
except Exception as e:
    print(f"  ❌ {e}")

print("\n=== Trying without 'models/' prefix ===")
try:
    r = client.models.embed_content(
        model="text-embedding-004",
        contents="hello world",
    )
    print("  ✅ Success:", r.embeddings[0].values[:3])
except Exception as e:
    print(f"  ❌ {e}")

print("\n=== Trying v1beta with 'models/text-embedding-004' ===")
client_beta = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={"api_version": "v1beta"},
)
try:
    r = client_beta.models.embed_content(
        model="models/text-embedding-004",
        contents="hello world",
    )
    print("  ✅ Success:", r.embeddings[0].values[:3])
except Exception as e:
    print(f"  ❌ {e}")

print("\n=== Trying gemini-embedding-004 (newer alias) ===")
for api_ver in ["v1", "v1beta"]:
    c = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"api_version": api_ver})
    for name in ["gemini-embedding-004", "models/gemini-embedding-004"]:
        try:
            r = c.models.embed_content(model=name, contents="hello world")
            print(f"  ✅ {api_ver} / {name}: {r.embeddings[0].values[:3]}")
        except Exception as e:
            print(f"  ❌ {api_ver} / {name}: {e}")