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
from fastapi import Request          # add this if not already present
from fastapi.responses import JSONResponse  # add this if not already present

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

@app.get("/ping")
def ping():
    """Lightweight health check for UptimeRobot — keeps Render from cold-starting."""
    return {"pong": True}

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

# ── Vapi Voice Agent Webhook ──────────────────────────────────────────────────
# Handles function-call events from the Vapi voice agent.
# Vapi calls this URL when the assistant needs to invoke a tool.
# Required env var: RENDER_URL (your Render backend base URL, no trailing slash)

@app.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    """
    Receives Vapi function-call events and routes them to the correct backend.

    Vapi payload shape:
    {
      "message": {
        "type": "function-call",
        "functionCall": {
          "name": "get_answer" | "get_slots" | "book_meeting",
          "parameters": { ... }
        }
      }
    }

    Must return: { "result": "<string for LLM to speak>" }
    """
    body = await request.json()
    message = body.get("message", {})

    # Ignore non-function-call events (status-update, transcript, etc.)
    if message.get("type") != "function-call":
        return JSONResponse({"result": "ok"})

    fn     = message.get("functionCall", {})
    name   = fn.get("name", "")
    params = fn.get("parameters", {})

    RENDER_URL = os.environ.get("RENDER_URL", "").rstrip("/")

    # Use async httpx — compatible with httpx>=0.28.1,<1.0.0
    async with httpx.AsyncClient(timeout=12.0) as client:

        # ── Tool: get_answer ───────────────────────────────────────────────
        # Calls POST /chat — your existing RAG endpoint
        if name == "get_answer":
            question = params.get("question", "").strip()
            if not question:
                return JSONResponse({"result": "Could you repeat the question? I didn't catch that."})
            try:
                resp = await client.post(
                    f"{RENDER_URL}/chat",
                    json={"message": question},   # matches ChatRequest.message in main.py
                    timeout=12.0,
                )
                resp.raise_for_status()
                data   = resp.json()
                answer = data.get("response", "")  # matches ChatResponse.response
                if not answer:
                    answer = "I don't have that information right now — happy to discuss it on a call!"
            except httpx.HTTPStatusError as e:
                answer = f"I ran into an issue fetching that answer. Status: {e.response.status_code}."
            except Exception:
                answer = "Something went wrong on my end. Feel free to ask again or book a call!"
            return JSONResponse({"result": answer})

        # ── Tool: get_slots ────────────────────────────────────────────────
        # Calls GET /slots — your existing Cal.com v2 slots endpoint
        # Returns a spoken-friendly list of up to 5 upcoming slots
        elif name == "get_slots":
            try:
                resp = await client.get(
                    f"{RENDER_URL}/slots",
                    timeout=12.0,
                )
                resp.raise_for_status()
                data  = resp.json()
                slots = data.get("slots", [])   # matches SlotsResponse.slots (list[str])

                if not slots:
                    return JSONResponse({
                        "result": (
                            "There are no available slots in the next 7 days. "
                            "You can also reach Harshita directly at her LinkedIn."
                        )
                    })

                # Format max 5 slots into a natural spoken list
                def fmt(iso: str) -> str:
                    """Turn '2025-06-10T14:00:00Z' → 'June 10th at 2 PM UTC'"""
                    try:
                        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                        return dt.strftime("%-d %B at %-I:%M %p UTC").replace(
                            dt.strftime("%-d"), _ordinal(dt.day)
                        )
                    except Exception:
                        return iso

                spoken_slots = [fmt(s) for s in slots[:5]]
                slot_list    = ", or ".join(spoken_slots)
                result = (
                    f"Harshita has the following slots open: {slot_list}. "
                    "Which one works best for you?"
                )
            except httpx.HTTPStatusError as e:
                result = (
                    f"I couldn't fetch availability right now (status {e.response.status_code}). "
                    "Would you like to try again in a moment?"
                )
            except Exception:
                result = "I had trouble fetching the calendar. Could you try again in a moment?"
            return JSONResponse({"result": result})

        # ── Tool: book_meeting ─────────────────────────────────────────────
        # Calls POST /book — your existing Cal.com v2 booking endpoint
        # Vapi collects: caller_name, caller_email, slot (ISO 8601 UTC string)
        elif name == "book_meeting":
            caller_name  = params.get("caller_name", "").strip()
            caller_email = params.get("caller_email", "").strip()
            slot         = params.get("slot", "").strip()

            # Validate before hitting Cal.com
            if not caller_name:
                return JSONResponse({"result": "Could you tell me your full name so I can book the slot?"})
            if not caller_email:
                return JSONResponse({"result": "What email address should I send the confirmation to?"})
            if not slot:
                return JSONResponse({"result": "Which time slot would you like to book?"})

            try:
                resp = await client.post(
                    f"{RENDER_URL}/book",
                    json={
                        "name":       caller_name,
                        "email":      caller_email,
                        "start_time": slot,          # matches BookRequest.start_time
                        "note":       "Booked via Tulips voice agent",
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
                result = (
                    f"You're all set, {caller_name}! Your call with Harshita is confirmed. "
                    f"A confirmation will be sent to {caller_email}. "
                    "Looking forward to connecting!"
                )
            except httpx.HTTPStatusError as e:
                err_text = e.response.text[:200]
                result = (
                    f"I couldn't complete the booking right now — {err_text}. "
                    "Please try again or reach Harshita directly."
                )
            except Exception as e:
                result = "Something went wrong with the booking. Please try once more or contact Harshita directly."
            return JSONResponse({"result": result})

        # ── Unknown tool ───────────────────────────────────────────────────
        else:
            return JSONResponse({"result": f"I don't know how to handle '{name}' yet."})


def _ordinal(n: int) -> str:
    """Return ordinal string: 1 → '1st', 2 → '2nd', 3 → '3rd', 4 → '4th' etc."""
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10 if n % 100 not in (11, 12, 13) else 0, "th")
    return f"{n}{suffix}"