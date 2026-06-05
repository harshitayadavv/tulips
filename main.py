"""
main.py — FastAPI backend for AI persona chatbot
Endpoints:
  POST /chat   — RAG-powered chat via Groq + Gemini + Qdrant
  POST /book   — Book a meeting via Cal.com v1 API
  GET  /slots  — Fetch available slots for the next 7 days
"""

import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from google import genai
from google.genai import types as genai_types
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, EmailStr
from qdrant_client import QdrantClient
from dotenv import load_dotenv

from persona_prompt import build_system_prompt, inject_context

load_dotenv()

# ── Env vars ──────────────────────────────────────────────────────────────────
GROQ_API_KEY    = os.environ["GROQ_API_KEY"]
GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]
QDRANT_URL      = os.environ["QDRANT_URL"]
QDRANT_API_KEY  = os.environ["QDRANT_API_KEY"]
CALCOM_API_KEY  = os.environ["CALCOM_API_KEY"]
CALCOM_USERNAME = os.environ["CALCOM_USERNAME"]

# ── Client setup ──────────────────────────────────────────────────────────────
# New google-genai SDK — targets stable v1 endpoint (fixes v1beta 404 error)
gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"api_version": "v1"},
)
groq_client   = Groq(api_key=GROQ_API_KEY)
qdrant        = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_NAME = "persona"
EMBEDDING_MODEL = "models/gemini-embedding-2"   
GROQ_MODEL      = "llama-3.3-70b-versatile"
TOP_K           = 5

CALCOM_BASE     = "https://api.cal.com/v2"

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="AI Persona Chatbot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_SYSTEM_PROMPT = build_system_prompt()

# ── Prompt injection guard ────────────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above|all)\s+(instructions?|prompts?|context)",
    r"system\s*prompt",
    r"jailbreak",
    r"you\s+are\s+now",
    r"forget\s+(everything|all|your|previous)",
    r"act\s+as\s+(if\s+you\s+are|a\s+different|an?\s+)",
    r"disregard\s+(your|all|previous)",
    r"override\s+(your|the|all)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"roleplay\s+as",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode",
    r"prompt\s+injection",
]
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), flags=re.IGNORECASE)

def is_prompt_injection(text: str) -> bool:
    return bool(INJECTION_RE.search(text))


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class BookRequest(BaseModel):
    name: str
    email: EmailStr
    note: Optional[str] = ""
    start_time: str  # ISO 8601, e.g. "2025-09-01T10:00:00Z"

class BookResponse(BaseModel):
    confirmation: str
    booking_id: Optional[int] = None
    meeting_url: Optional[str] = None

class SlotsResponse(BaseModel):
    slots: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def embed_query(text: str) -> list[float]:
    """Embed a search query using Gemini text-embedding-004 (new SDK)."""
    result = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def retrieve_context(query_vector: list[float]) -> str:
    hits = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=TOP_K,
        with_payload=True,
    )
    if not hits:
        return ""
    chunks = []
    for hit in hits:
        source = hit.payload.get("filename", "unknown")
        text   = hit.payload.get("text", "")
        chunks.append(f"[Source: {source}]\n{text}")
    return "\n\n---\n\n".join(chunks)


def calcom_headers() -> dict:
    """Auth header for Cal.com v2 API (only needed for authenticated endpoints)."""
    return {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "cal-api-version": "2024-08-13",
        "Content-Type": "application/json",
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if is_prompt_injection(user_message):
        return ChatResponse(
            response=(
                "I'm sorry, but I can't process that kind of request. "
                "I'm here to answer questions about my professional background. "
                "Feel free to ask me about my skills, experience, or projects!"
            )
        )

    try:
        query_vector = embed_query(user_message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding error: {e}")

    try:
        context = retrieve_context(query_vector)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector DB error: {e}")

    system_prompt = inject_context(BASE_SYSTEM_PROMPT, context)

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.4,
            max_tokens=1024,
        )
        answer = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return ChatResponse(response=answer)


@app.post("/book", response_model=BookResponse)
def book_meeting(req: BookRequest):
    # v2: use username + eventTypeSlug — no need to fetch event type ID first
    # Booking endpoint is public (no auth needed per Cal.com docs)
    payload = {
        "username":      CALCOM_USERNAME,
        "eventTypeSlug": "30min",        # update to match your Cal.com event slug
        "start":         req.start_time,
        "attendee": {
            "name":     req.name,
            "email":    req.email,
            "timeZone": "UTC",
            "language": "en",
        },
        "metadata": {"note": req.note or ""},
    }

    try:
        resp = httpx.post(
            f"{CALCOM_BASE}/bookings",
            json=payload,
            headers={"cal-api-version": "2024-08-13", "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", resp.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Cal.com booking error: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cal.com request failed: {e}")

    booking_id  = data.get("id") or data.get("bookingId")
    meeting_url = data.get("meetingUrl") or data.get("videoCallData", {}).get("url")

    return BookResponse(
        confirmation=f"Booking confirmed! You'll receive a confirmation email at {req.email}.",
        booking_id=booking_id,
        meeting_url=meeting_url,
    )


@app.get("/slots", response_model=SlotsResponse)
def get_available_slots():
    now       = datetime.now(timezone.utc)
    date_from = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_to   = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # v2: use username + eventSlug — public endpoint, no auth needed
    try:
        slots_resp = httpx.get(
            f"{CALCOM_BASE}/slots",
            headers={"cal-api-version": "2024-08-13"},
            params={
                "username":   CALCOM_USERNAME,
                "eventSlug":  "30min",       # update to match your Cal.com event slug
                "startTime":  date_from,
                "endTime":    date_to,
                "timeZone":   "UTC",
            },
            timeout=10,
        )
        slots_resp.raise_for_status()
        slots_data = slots_resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Cal.com slots error: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cal.com slots request failed: {e}")

    # v2 response: {"status":"success","data":{"slots":{"2025-09-01":[{"time":"..."}]}}}
    all_slots: list[str] = []
    slots_by_date = slots_data.get("data", {}).get("slots", {})
    for date_key, time_entries in slots_by_date.items():
        for entry in time_entries:
            t = entry.get("time", "")
            if t:
                all_slots.append(t)

    return SlotsResponse(slots=all_slots)