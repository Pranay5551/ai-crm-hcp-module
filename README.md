# AI-First CRM — HCP Interaction Module

An AI-first "Log HCP Interaction" screen for pharma field reps, letting them log interactions
with Healthcare Professionals (HCPs) either via a **structured form** or a **conversational AI
chat interface**, backed by a **LangGraph** agent running on **Groq**-hosted LLMs.

## Why this design

Field reps visit HCPs all day and hate re-typing the same information into forms after a
meeting. The AI-first idea here: let them *talk* (or type free text) about what happened, and
have an agent do the structuring — extracting the HCP name, topics, materials, sentiment, and
outcomes — while still keeping a traditional form for reps who prefer precise, structured entry
or need to correct what the agent inferred. Both paths write to the same `interactions` table,
so the form and chat are two doors into one record.

## Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  React + Redux Frontend     │  REST  │  FastAPI Backend             │
│  - InteractionForm.jsx      │◄──────►│  - /api/interactions (CRUD)  │
│  - ChatAssistant.jsx        │        │  - /api/chat (agent endpoint)│
└─────────────────────────────┘        └──────────────────┬───────────┘
                                                          │
                                                 ┌────────▼─────────┐
                                                 │  LangGraph Agent │
                                                 │  (ReAct loop)    │
                                                 └────────┬─────────┘
                                                           │ binds
                                    ┌──────────────────────┼────────────────────────┐
                                    ▼                      ▼                        ▼
                          log_interaction        edit_interaction         search_hcp_history
                        (LLM entity extraction)  (modify existing)      schedule_followup
                                                                       suggest_next_best_action
                                                           │
                                                  ┌────────▼────────────┐
                                                  │  Postgres (SQLA)    │
                                                  │  hcps / interactions│
                                                  └─────────────────────┘
```

## Role of the LangGraph agent

The agent is the reasoning layer between "what the rep said" and "what gets saved." It runs as
a small ReAct-style graph: an `agent` node (Groq LLM with tools bound) decides whether to
respond directly or call a tool, a `tools` node executes the call, and control loops back to
the agent until it produces a final confirmation message for the rep. This lets a single free
text message like *"Met Dr. Sharma, discussed OncoBoost Phase III data, she seemed positive,
shared the brochure, follow up in 2 weeks"* result in a fully logged record with the follow-up
scheduled, without the rep touching a form.

## The 5 tools

| Tool | Purpose |
|---|---|
| `log_interaction` | Takes free text (chat message or voice-note transcript), uses the LLM to extract structured fields (HCP name, topics, materials, sentiment, outcomes), and creates a new `Interaction` row. |
| `edit_interaction` | Takes an interaction id + a JSON patch, updates the record (e.g. rep corrects sentiment or adds a missed detail). |
| `search_hcp_history` | Fuzzy-searches past interactions by HCP name — gives the rep or agent context before a visit ("what did we last discuss with Dr. Smith?"). |
| `schedule_followup` | Appends a dated follow-up note to an interaction, so "follow up in 2 weeks" becomes a concrete tracked action. |
| `suggest_next_best_action` | Uses the LLM to propose up to 3 next steps from the logged interaction (e.g. "Schedule follow-up meeting," "Send Phase III PDF," "Add to advisory board list") — mirrors the "AI Suggested Follow-ups" shown in the UI mock. |

## Tech stack

- **Frontend:** React + Redux Toolkit, Google Inter font
- **Backend:** FastAPI (Python)
- **Agent framework:** LangGraph (ReAct loop, `ToolNode`)
- **LLM:** Groq — `openai/gpt-oss-20b` for extraction (fast, cheap), can swap to
  `openai/gpt-oss-120b` for the reasoning-heavier `suggest_next_best_action` tool
- **Database:** PostgreSQL via SQLAlchemy

## Running locally

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start   # runs on http://localhost:3000, expects backend on :8000
```

### Database
Create a Postgres database matching `DATABASE_URL` in `.env` (e.g. `createdb hcp_crm`).
Tables are auto-created on backend startup via SQLAlchemy's `create_all`.

## What's structured vs. what's AI-assisted

- **Structured form path** (`POST /api/interactions/`): fields go straight to the DB, no LLM
  involved — for reps who want precision and speed with no round-trip to an LLM.
- **Conversational path** (`POST /api/chat/`): every message goes through the LangGraph agent,
  which decides which tool(s) to call. This is where the LLM does the heavy lifting: entity
  extraction, sentiment inference, and follow-up suggestions.

## Known simplifications (given the assignment's time-boxed nature)

- Chat session history is stored in-memory (`_SESSIONS` dict) rather than persisted — swap for
  Redis or a `chat_messages` table (already modeled) for production.
- Voice-note transcription ("Summarize from Voice Note") is stubbed as a UI affordance; a real
  implementation would pipe audio through a speech-to-text service before hitting
  `log_interaction`.
- No auth/multi-tenant rep identity — `session_id` is hardcoded for the demo.

## A note on the LLM model choice

The assignment brief specifies `gemma2-9b-it`. By the time of this submission, Groq had
deprecated that model (and its originally-suggested fallback, `llama-3.3-70b-versatile`, is
also deprecated as of June 2026). I substituted Groq's currently recommended replacements:
`openai/gpt-oss-20b` for fast/cheap extraction tasks (`log_interaction`, `edit_interaction`),
and `openai/gpt-oss-120b` available for heavier reasoning tasks. These fill the same roles the
brief intended — a fast small model for structured extraction, a larger model available for
more nuanced reasoning — just with Groq's current model lineup.
