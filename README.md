# 🌷 Tulips — Harshita's AI Persona

> An AI-powered voice + chat agent that represents Harshita Yadav, answers questions about her background, and books interviews — fully autonomous, no human in the loop.

Built for the Scaler AI Engineer Screening Assignment.

---

# 🔗 Live Links

| Service             | Link                             |
| ------------------- | -------------------------------- |
| 📞 Voice Agent      | +1 (254) 261-0169                |
| 💬 Chat UI          | https://tulips-rho.vercel.app    |
| 🔧 Backend API      | https://tulips-s84n.onrender.com |
| 📅 Book a Call      | https://cal.com/harshita-pgiap0  |
| 🎥 Loom Walkthrough | [ADD_LOOM_LINK]                  |

### 📞 How to Call the Voice Agent

The voice agent is live at **+1 (254) 261-0169** and is powered by Vapi.ai.

You can call it by:

* Directly dialing +1 (254) 261-0169
* Dialing internationally from India using +1-254-261-0169
* Using Skype or Google Voice
* Triggering a test call directly from the Vapi dashboard

The agent can:

* Introduce itself as Tulips, Harshita's AI representative
* Answer questions about experience, projects, and technical skills
* Retrieve information from the knowledge base
* Check calendar availability
* Schedule confirmed interview slots

---

# 🎯 Design Goals

Tulips was built around four core principles:

1. **Groundedness** — Responses should come from retrieved candidate information rather than model assumptions.
2. **Honesty** — The agent should acknowledge uncertainty instead of hallucinating.
3. **Low Latency** — Voice conversations should feel natural and responsive.
4. **Autonomous Scheduling** — Recruiters should be able to complete interview booking without human intervention.

---

# 🏗️ Architecture

```text
Resume PDF + GitHub READMEs
          ↓
Gemini Embeddings (text-embedding-004)
          ↓
Qdrant Cloud Vector Database
          ↓
Groq Llama 3.3 70B
          ↓
┌─────────────────┬──────────────────┐
│    Chat UI      │   Voice Agent    │
│ Next.js/Vercel  │   Vapi + Groq    │
│ /chat/stream    │ Deepgram STT/TTS │
└─────────────────┴──────────────────┘
          ↓                  ↓
     Cal.com Calendar Booking
```

---

# 💰 Cost Breakdown

| Layer          | Tool                         | Cost       |
| -------------- | ---------------------------- | ---------- |
| LLM            | Groq llama-3.3-70b-versatile | Free       |
| Embeddings     | Gemini text-embedding-004    | Free       |
| Vector DB      | Qdrant Cloud                 | Free       |
| Voice Platform | Vapi.ai                      | ~$0.08/min |
| STT            | Deepgram Flux                | Included   |
| TTS            | Deepgram Aura Asteria        | Included   |
| Backend        | FastAPI on Render            | Free       |
| Frontend       | Next.js on Vercel            | Free       |
| Calendar       | Cal.com                      | Free       |

**Estimated voice cost:** ~$0.08/min

**Estimated chat cost:** Within free-tier limits

---

# 📁 Project Structure

```text
tulips/
├── docs/
│   ├── harshitayadavv211.pdf
│   ├── project-warroom-summary.txt
│   ├── project-skyracer-summary.txt
│   ├── project-wordsmith-summary.txt
│   ├── internship-udchalo-summary.txt
│   ├── hackathons-summary.txt
│   └── smart-india-hackathon-summary.txt
│
├── frontend/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   │
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   └── BookingModal.tsx
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   └── vercel.json
│
├── main.py
├── ingest.py
├── persona_prompt.py
├── requirements.txt
├── Procfile
└── .env.example
```

---

# 🛠️ Tech Stack

| Layer           | Tool                      |
| --------------- | ------------------------- |
| LLM             | Groq Llama 3.3 70B        |
| Embeddings      | Gemini text-embedding-004 |
| Vector Database | Qdrant Cloud              |
| Voice Platform  | Vapi                      |
| Speech-to-Text  | Deepgram Flux             |
| Text-to-Speech  | Deepgram Aura             |
| Backend         | FastAPI                   |
| Frontend        | Next.js 14                |
| Styling         | Tailwind CSS              |
| Calendar        | Cal.com                   |
| Hosting         | Render + Vercel           |

---

# ⚙️ Setup Instructions

## Prerequisites

* Python 3.11+
* Node.js 18+
* Groq Account
* Google AI Studio Account
* Qdrant Cloud Account
* Vapi Account
* Cal.com Account

---

## Clone Repository

```bash
git clone https://github.com/harshitayadavv/tulips.git
cd tulips
```

---

## Backend Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

---

## Environment Variables

Create `.env`

```env
GROQ_API_KEY=

GROQ_API_KEY_2=

GEMINI_API_KEY=

QDRANT_URL=
QDRANT_API_KEY=

CALCOM_API_KEY=
CALCOM_USERNAME=
```

---

## Ingest Documents

```bash
python ingest.py
```

---

## Run Backend

```bash
uvicorn main:app --reload
```

Backend:

```text
http://localhost:8000
```

Swagger Docs:

```text
http://localhost:8000/docs
```

---

## Run Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# 🚀 Deployment

## Backend → Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Add all environment variables through the Render dashboard.

---

## Frontend → Vercel

Root Directory:

```text
frontend
```

Environment Variable:

```env
NEXT_PUBLIC_BACKEND_URL=https://tulips-s84n.onrender.com
```

---

## Voice Agent → Vapi

Configuration:

* Model: llama-3.3-70b-versatile
* STT: Deepgram Flux
* TTS: Deepgram Aura Asteria
* Webhook:

```text
https://tulips-s84n.onrender.com/vapi-webhook
```

* Phone Number:

```text
+1 (254) 261-0169
```

---

# 📡 API Endpoints

| Method | Endpoint      | Description           |
| ------ | ------------- | --------------------- |
| GET    | /health       | Health check          |
| GET    | /ping         | Keep-alive endpoint   |
| POST   | /chat         | Standard RAG chat     |
| POST   | /chat/stream  | Streaming SSE chat    |
| GET    | /slots        | Calendar availability |
| POST   | /book         | Interview booking     |
| POST   | /vapi-webhook | Voice tool execution  |

---

# 📊 Evaluation Summary

| Metric                       | Result   |
| ---------------------------- | -------- |
| Voice First Response Latency | ~1050 ms |
| Tool Call Latency            | ~2.9 s   |
| Transcription Accuracy       | ~94%     |
| Booking Success Rate         | 5/5      |
| Chat Pass Rate               | 9/10     |
| Hallucination Rate           | 10% → 0% |
| Prompt Injection Protection  | 5/5      |

Full details available in:

```text
evals_report.pdf
```

---

# 🐛 Key Failure Modes & Fixes

### 1. Groq Rate Limits

**Issue**

100k TPD limit exceeded.

**Fix**

Added multi-key fallback routing.

---

### 2. Cal.com API Deprecation

**Issue**

Legacy v1 endpoints returned 410 errors.

**Fix**

Migrated to Cal.com v2 endpoints and updated authentication flow.

---

### 3. Render Cold Starts

**Issue**

First request latency reached 30–50 seconds.

**Fix**

Added UptimeRobot keep-alive pings against `/ping`.

---

### 4. Frontend Environment Variables

**Issue**

Backend URL was unavailable after deployment.

**Fix**

Configured build-time environment variables in Vercel.

---

# 🔮 What I'd Build With 2 More Weeks

1. Redis-backed conversation memory
2. Automatic GitHub repository synchronization
3. Sentiment-aware tone adaptation
4. Shared streaming infrastructure across voice and chat
5. Advanced reranking for retrieval quality

---

# 🎥 Loom Walkthrough

Add Loom recording link here before submission.

---

# 👩‍💻 Built By

**Harshita Yadav**

Email: [harshitayadavv211@gmail.com](mailto:harshitayadavv211@gmail.com)

GitHub: https://github.com/harshitayadavv

LinkedIn: https://www.linkedin.com/in/harshita-yadav-6b287b296

---

Keep all services active for at least 7 days after submission.

Scaler reviewers may interact with both the voice and chat interfaces without prior notice.
