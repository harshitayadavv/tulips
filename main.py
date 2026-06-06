"""
main.py — FastAPI backend for AI persona chatbot
Endpoints:
  POST /chat   — RAG-powered chat via Groq + Gemini + Qdrant
  POST /book   — Book a meeting via Cal.com v2 API
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
from fastapi.responses import StreamingResponse
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
# google-genai SDK forced to stable v1 endpoint (v1beta doesn't support gemini-embedding-2)
gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"api_version": "v1"},
)
groq_client = Groq(api_key=GROQ_API_KEY)
qdrant      = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)

COLLECTION_NAME = "persona"
EMBEDDING_MODEL = "models/gemini-embedding-2"  # only model available on this API key
GROQ_MODEL      = "llama-3.3-70b-versatile"
TOP_K           = 5

CALCOM_BASE     = "https://api.cal.com/v2"

# ─────────────────────────────────────────────────────────────────────────────
# !! UPDATE THIS to match your Cal.com event slug !!
# Go to cal.com/event-types → click your event → copy the last part of the URL
# e.g. cal.com/harshita/30min  →  EVENT_SLUG = "30min"
# ─────────────────────────────────────────────────────────────────────────────
EVENT_SLUG = "30min"

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
    start_time: str  # ISO 8601 UTC, e.g. "2025-09-01T10:00:00Z"

class BookResponse(BaseModel):
    confirmation: str
    booking_id: Optional[int] = None
    meeting_url: Optional[str] = None

class SlotsResponse(BaseModel):
    slots: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def embed_query(text: str) -> list[float]:
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


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if is_prompt_injection(user_message):
        def injection_gen():
            msg = ("I'm sorry, but I can't process that kind of request. "
                   "I'm here to answer questions about my professional background. "
                   "Feel free to ask me about my skills, experience, or projects!")
            yield f"data: {msg}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(injection_gen(), media_type="text/event-stream")

    try:
        query_vector = embed_query(user_message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding error: {e}")

    try:
        context = retrieve_context(query_vector)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector DB error: {e}")

    system_prompt = inject_context(BASE_SYSTEM_PROMPT, context)

    def generate():
        try:
            stream = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.4,
                max_tokens=1024,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {delta}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Sorry, something went wrong: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/book", response_model=BookResponse)
def book_meeting(req: BookRequest):
    """
    Creates a booking via Cal.com v2 API.
    Uses username + eventTypeSlug (no event type ID lookup needed).
    cal-api-version 2024-08-13 is required for /bookings.
    """
    payload = {
        "username":      CALCOM_USERNAME,
        "eventTypeSlug": EVENT_SLUG,
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
            headers={
                "Authorization":    f"Bearer {CALCOM_API_KEY}",
                "cal-api-version":  "2024-08-13",
                "Content-Type":     "application/json",
            },
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
    """
    Returns available slots for the next 7 days via Cal.com v2 API.
    Uses username + eventTypeSlug (cal-api-version: 2024-09-04, params: start/end).
    cal-api-version 2024-09-04 is required for /slots (different from /bookings!).
    Params are 'start'/'end', NOT 'startTime'/'endTime'.
    """
    now       = datetime.now(timezone.utc)
    date_from = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_to   = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        slots_resp = httpx.get(
            f"{CALCOM_BASE}/slots",
            headers={
                "Authorization":   f"Bearer {CALCOM_API_KEY}",
                "cal-api-version": "2024-09-04",
            },
            params={
                "username":  CALCOM_USERNAME,
                "eventTypeSlug": EVENT_SLUG,
                "start":     date_from,
                "end":       date_to,
                "timeZone":  "UTC",
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

    # 2024-09-04 shape: {"data": {"2025-09-01": [{"start": "..."}], ...}}
    # 2024-08-13 shape: {"data": {"slots": {"2025-09-01": [{"time": "..."}]}}}
    # Handle both to be safe
    raw           = slots_data.get("data", {})
    slots_by_date = raw.get("slots", raw)
    all_slots: list[str] = []
    for date_key, time_entries in slots_by_date.items():
        if not isinstance(time_entries, list):
            continue
        for entry in time_entries:
            t = entry.get("start") or entry.get("time", "")
            if t:
                all_slots.append(t)

    return SlotsResponse(slots=all_slots)