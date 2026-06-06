import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from google import genai
from google.genai import types as genai_types
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from groq import Groq
from pydantic import BaseModel, EmailStr
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from persona_prompt import build_system_prompt, inject_context

load_dotenv()

GEMINI_API_KEY       = os.environ["GEMINI_API_KEY"]
QDRANT_URL           = os.environ["QDRANT_URL"]
QDRANT_API_KEY       = os.environ["QDRANT_API_KEY"]
CALCOM_API_KEY       = os.environ["CALCOM_API_KEY"]
CALCOM_USERNAME      = os.environ["CALCOM_USERNAME"]
GROQ_API_KEY         = os.environ["GROQ_API_KEY"]
GROQ_API_KEY_BACKUP  = os.environ.get("GROQ_API_KEY_BACKUP", "")
RENDER_URL           = os.environ.get("RENDER_URL", "").rstrip("/")

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"api_version": "v1"},
)
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)

COLLECTION_NAME = "persona"
EMBEDDING_MODEL = "models/gemini-embedding-2"
GROQ_MODEL      = "llama-3.3-70b-versatile"
TOP_K           = 5
CALCOM_BASE     = "https://api.cal.com/v2"
EVENT_SLUG      = "30min"

app = FastAPI(title="AI Persona Chatbot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_SYSTEM_PROMPT = build_system_prompt()

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


def groq_complete(messages: list, stream: bool = False):
    try:
        return Groq(api_key=GROQ_API_KEY).chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
            stream=stream,
        )
    except Exception as primary_err:
        if not GROQ_API_KEY_BACKUP:
            raise primary_err
        return Groq(api_key=GROQ_API_KEY_BACKUP).chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
            stream=stream,
        )


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class BookRequest(BaseModel):
    name: str
    email: EmailStr
    note: Optional[str] = ""
    start_time: str

class BookResponse(BaseModel):
    confirmation: str
    booking_id: Optional[int] = None
    meeting_url: Optional[str] = None

class SlotsResponse(BaseModel):
    slots: list[str]


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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ping")
def ping():
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
        completion = groq_complete([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ])
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
            msg = (
                "I'm sorry, but I can't process that kind of request. "
                "I'm here to answer questions about my professional background. "
                "Feel free to ask me about my skills, experience, or projects!"
            )
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
            stream = groq_complete([
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ], stream=True)
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
                "Authorization":   f"Bearer {CALCOM_API_KEY}",
                "cal-api-version": "2024-08-13",
                "Content-Type":    "application/json",
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
                "username":      CALCOM_USERNAME,
                "eventTypeSlug": EVENT_SLUG,
                "start":         date_from,
                "end":           date_to,
                "timeZone":      "UTC",
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


@app.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    body    = await request.json()
    message = body.get("message", {})

    if message.get("type") != "function-call":
        return JSONResponse({"result": "ok"})

    fn     = message.get("functionCall", {})
    name   = fn.get("name", "")
    params = fn.get("parameters", {})

    async with httpx.AsyncClient(timeout=12.0) as client:

        if name == "get_answer":
            question = params.get("question", "").strip()
            if not question:
                return JSONResponse({"result": "Could you repeat the question? I didn't catch that."})
            try:
                resp = await client.post(
                    f"{RENDER_URL}/chat",
                    json={"message": question},
                    timeout=12.0,
                )
                resp.raise_for_status()
                answer = resp.json().get("response", "")
                if not answer:
                    answer = "I don't have that information right now — happy to discuss it on a call!"
            except httpx.HTTPStatusError as e:
                answer = f"I ran into an issue fetching that answer. Status: {e.response.status_code}."
            except Exception:
                answer = "Something went wrong on my end. Feel free to ask again or book a call!"
            return JSONResponse({"result": answer})

        elif name == "get_slots":
            try:
                resp = await client.get(f"{RENDER_URL}/slots", timeout=12.0)
                resp.raise_for_status()
                slots = resp.json().get("slots", [])
                if not slots:
                    return JSONResponse({
                        "result": "There are no available slots in the next 7 days. You can also reach Harshita directly at her LinkedIn."
                    })
                spoken_slots = [_fmt_slot(s) for s in slots[:5]]
                result = "Harshita has these slots open: " + ", or ".join(spoken_slots) + ". Which works best for you?"
            except httpx.HTTPStatusError as e:
                result = f"I couldn't fetch availability right now (status {e.response.status_code}). Would you like to try again?"
            except Exception:
                result = "I had trouble fetching the calendar. Could you try again in a moment?"
            return JSONResponse({"result": result})

        elif name == "book_meeting":
            caller_name  = params.get("caller_name", "").strip()
            caller_email = params.get("caller_email", "").strip()
            slot         = params.get("slot", "").strip()

            if not caller_name:
                return JSONResponse({"result": "Could you tell me your full name so I can book the slot?"})
            if not caller_email:
                return JSONResponse({"result": "What email should I send the confirmation to?"})
            if not slot:
                return JSONResponse({"result": "Which time slot would you like to book?"})

            try:
                resp = await client.post(
                    f"{RENDER_URL}/book",
                    json={
                        "name":       caller_name,
                        "email":      caller_email,
                        "start_time": slot,
                        "note":       "Booked via Tulips voice agent",
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
                result = (
                    f"You're all set, {caller_name}! Your call with Harshita is confirmed. "
                    f"A confirmation will be sent to {caller_email}. Looking forward to connecting!"
                )
            except httpx.HTTPStatusError as e:
                result = f"I couldn't complete the booking — {e.response.text[:200]}. Please try again or contact Harshita directly."
            except Exception:
                result = "Something went wrong with the booking. Please try once more or contact Harshita directly."
            return JSONResponse({"result": result})

        else:
            return JSONResponse({"result": f"I don't know how to handle '{name}' yet."})


def _fmt_slot(iso: str) -> str:
    try:
        dt     = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        day    = dt.day
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10 if day % 100 not in (11, 12, 13) else 0, "th")
        return dt.strftime(f"%B {day}{suffix} at %-I:%M %p UTC")
    except Exception:
        return iso