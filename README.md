# 🌷 Tulips

> An AI-powered voice and chat persona that answers recruiter questions, discusses candidate experience and projects, and autonomously schedules interviews using real calendar availability.

Built for the Scaler AI Engineer Screening Assignment.

---

## Overview

Tulips is an end-to-end AI persona system designed to simulate a candidate representative. Recruiters can interact with the persona via voice or chat, ask detailed questions about skills, projects, achievements, and experience, and directly schedule interviews without any human intervention.

The system uses Retrieval-Augmented Generation (RAG) over a candidate's resume, GitHub repositories, project documentation, and supporting materials. This ensures responses remain grounded, factual, and resistant to hallucination.

### Key Features

* 🎙️ Real-time voice conversations
* 💬 Public chat interface
* 📚 RAG-grounded responses
* 🔍 Resume and GitHub aware
* 📅 Autonomous interview scheduling
* 🛡️ Prompt injection resistance
* ⚡ Low-latency inference
* 🔄 Shared knowledge base across voice and chat

---

## System Architecture

```text
Resume PDF + GitHub READMEs + Project Docs
                    │
                    ▼
        Gemini Embeddings (Free)
                    │
                    ▼
          Qdrant Cloud Vector DB
                    │
                    ▼
           Retrieval Pipeline
                    │
                    ▼
        Groq Llama 3.3 70B Model
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
  Chat Interface             Voice Agent
 (Next.js/Vercel)           (Vapi + Groq)
      │                           │
      └─────────────┬─────────────┘
                    ▼
            Calendar Booking
               (Cal.com)
```

---

## Live Links

| Service              | URL                        |
| -------------------- | -------------------------- |
| 📞 Voice Agent       | `[YOUR_VAPI_PHONE_NUMBER]` |
| 💬 Chat UI           | `[YOUR_VERCEL_URL]`        |
| 🔧 Backend API       | `[YOUR_RENDER_URL]`        |
| 📂 GitHub Repository | `[YOUR_GITHUB_REPO]`       |

---

## Tech Stack

| Layer           | Technology                     | Cost         |
| --------------- | ------------------------------ | ------------ |
| LLM             | Groq `llama-3.3-70b-versatile` | Free         |
| Embeddings      | Gemini `text-embedding-004`    | Free         |
| Vector Database | Qdrant Cloud                   | Free         |
| Backend         | FastAPI                        | Free         |
| Frontend        | Next.js + Vercel               | Free         |
| Voice Agent     | Vapi.ai                        | Free Credits |
| Speech-to-Text  | Deepgram                       | Included     |
| Calendar        | Cal.com                        | Free         |
| Hosting         | Render                         | Free         |

### Estimated Cost

| Resource       | Cost        |
| -------------- | ----------- |
| Voice Call     | ~$0.05–0.10 |
| Chat Session   | ~$0.00      |
| Embeddings     | Free        |
| Vector Storage | Free        |

---

## Project Structure

```text
TULIPS/
│
├── docs/
│   ├── resume.pdf
│   ├── github_readmes/
│   └── project_docs/
│
├── frontend/
│   ├── app/
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── BookingModal.tsx
│   │   └── MessageBubble.tsx
│   ├── package.json
│   └── vercel.json
│
├── main.py
├── ingest.py
├── rag.py
├── calendar_service.py
├── persona_prompt.py
├── requirements.txt
├── Procfile
└── README.md
```

---

## Core Components

### RAG Pipeline

The retrieval layer powers both chat and voice experiences.

#### Sources

* Resume PDF
* GitHub README files
* Project documentation
* Additional candidate context

#### Flow

```text
User Question
      │
      ▼
Embedding Generation
      │
      ▼
Qdrant Similarity Search
      │
      ▼
Top-K Context Retrieval
      │
      ▼
Groq LLM Response
```

---

### Chat Interface

Features:

* Streaming responses
* Mobile responsive UI
* Source-grounded answers
* Interview scheduling support

Built with:

* Next.js
* TypeScript
* Tailwind CSS

---

### Voice Agent

Features:

* Natural conversation flow
* Handles interruptions
* Supports follow-up questions
* Dynamic slot booking
* Real-time tool calling

Built with:

* Vapi
* Deepgram
* Groq

---

### Calendar Booking

The booking system:

1. Fetches available slots
2. Presents options
3. Confirms selection
4. Creates interview event
5. Returns confirmation

No manual intervention required.

---

## Setup Instructions

### Prerequisites

* Python 3.11+
* Node.js 18+
* Groq Account
* Google AI Studio Account
* Qdrant Cloud Account
* Vapi Account
* Cal.com Account
* Render Account
* Vercel Account

---

### Clone Repository

```bash
git clone https://github.com/[YOUR_GITHUB]/tulips.git
cd tulips
```

---

### Backend Setup

```bash
py -3.11 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

---

### Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=

GEMINI_API_KEY=

QDRANT_URL=
QDRANT_API_KEY=

CALCOM_API_KEY=
CALCOM_USERNAME=
```

---

### Document Ingestion

Place the following files inside `docs/`:

```text
docs/
├── resume.pdf
├── github_readmes/
└── project_docs/
```

Run:

```bash
python ingest.py
```

---

### Run Backend

```bash
uvicorn main:app --reload
```

Available at:

```text
http://localhost:8000
```

Swagger Docs:

```text
http://localhost:8000/docs
```

---

### Run Frontend

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

## Deployment

### Backend → Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

### Frontend → Vercel

```bash
vercel --prod
```

Environment Variable:

```env
NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com
```

---

### Voice Agent → Vapi

Configure:

* Assistant Prompt
* Tool Definitions
* Booking Functions
* Webhook URL

```text
https://your-backend.onrender.com/vapi-webhook
```

---

## API Endpoints

| Method | Endpoint        | Description                        |
| ------ | --------------- | ---------------------------------- |
| POST   | `/chat`         | RAG-grounded chat response         |
| GET    | `/slots`        | Retrieve available interview slots |
| POST   | `/book`         | Create booking                     |
| POST   | `/vapi-webhook` | Handle Vapi tool calls             |
| GET    | `/ping`         | Health check                       |

---

## Example Evaluations

| Test               | Expected Behaviour             |
| ------------------ | ------------------------------ |
| Resume Question    | Accurate grounded answer       |
| GitHub Question    | Repo-specific response         |
| Follow-up Question | Maintains context              |
| Prompt Injection   | Refuses manipulation           |
| Interview Booking  | Successfully schedules meeting |

---

## Evals Summary

| Metric                       | Result |
| ---------------------------- | ------ |
| Hallucination Rate           | [X]%   |
| Retrieval Precision          | [X]%   |
| Retrieval Recall             | [X]%   |
| Voice First Response Latency | [X] ms |
| Booking Success Rate         | [X]/5  |

Full details available in:

```text
evals_report.pdf
```

---

## Failure Modes Discovered

### 1. Hallucinated Repository Information

**Root Cause**

Insufficient retrieved context.

**Fix**

Increased retrieval depth and added reranking.

---

### 2. Prompt Injection Attempts

**Root Cause**

User instructions conflicting with system instructions.

**Fix**

Added strict grounding and instruction hierarchy.

---

### 3. Booking Errors

**Root Cause**

Invalid slot formatting from external calendar APIs.

**Fix**

Added slot validation and fallback handling.

---

## Tradeoff Chosen

### Cost vs Latency

I chose Groq's hosted inference over larger proprietary models because it provided significantly lower latency while maintaining sufficient response quality for recruiter-facing conversations.

This improved voice responsiveness and reduced operational costs.

---

## What I'd Build With 2 More Weeks

* Redis-based cross-session memory
* Automated GitHub synchronization
* Multilingual voice support
* Analytics dashboard
* Advanced retrieval reranking
* Resume version tracking
* Recruiter interaction analytics

---

## Loom Walkthrough

🎥 [YOUR_LOOM_URL]

---

## Author

**Harshita Yadav**

Built for the Scaler AI Engineer Screening Assignment.

📧 [harshitayadavv211@gmail.com](mailto:harshitayadavv211@gmail.com)

---

Built with FastAPI, Groq, Gemini, Qdrant, Vapi, Next.js, and Cal.com.
