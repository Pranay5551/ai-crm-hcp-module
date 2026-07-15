"""
LangGraph Tools for the HCP Interaction Agent.

Five tools are defined, per assignment spec:
  1. log_interaction        (required)
  2. edit_interaction       (required)
  3. search_hcp_history     (extra)
  4. schedule_followup      (extra)
  5. suggest_next_best_action (extra)

Each tool is a thin wrapper around DB operations, with the LLM used inside
`log_interaction` for entity extraction/summarization from free text
(chat message or voice-note transcript).
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from langchain_core.tools import tool

from app.database import SessionLocal
from app.models import Interaction, HCP, SentimentEnum, InteractionTypeEnum
from app.agent.llm import get_llm

EXTRACTION_PROMPT = """You are a life-sciences CRM assistant. Extract structured fields from the
following free-text description of a field rep's interaction with a Healthcare Professional (HCP).

Return ONLY valid JSON (no markdown, no preamble) with these keys:
{{
  "hcp_name": string,
  "interaction_type": one of ["Meeting", "Call", "Email", "Conference"],
  "attendees": [string],
  "topics_discussed": string,
  "materials_shared": [string],
  "samples_distributed": [string],
  "sentiment": one of ["positive", "neutral", "negative"],
  "outcomes": string,
  "follow_up_actions": string
}}

If a field isn't mentioned, use an empty string or empty list. Infer sentiment from tone/wording.

Text: {text}
"""

SUGGESTION_PROMPT = """Given this logged HCP interaction, suggest up to 3 concrete follow-up
actions a pharma field rep should take next. Be specific (e.g. "Schedule follow-up meeting in 2
weeks", "Send Phase III trial data PDF"). Return ONLY a JSON array of strings, nothing else.

Interaction summary: {summary}
"""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1) if raw.startswith("json\n") else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise


@tool
def log_interaction(free_text: str) -> str:
    """
    Log a new HCP interaction from free-form text (typed chat message or transcribed
    voice note). Uses the LLM to extract structured entities (HCP name, topics,
    materials, sentiment, outcomes) and persists a new Interaction record.
    Returns a JSON string with the created interaction's id and extracted fields.
    """
    llm = get_llm(temperature=0.1)
    prompt = EXTRACTION_PROMPT.format(text=free_text)
    response = llm.invoke(prompt)
    fields = _extract_json(response.content)

    db = SessionLocal()
    try:
        hcp_name = fields.get("hcp_name") or "Unknown HCP"
        hcp = db.query(HCP).filter(HCP.name.ilike(hcp_name)).first()
        if not hcp:
            hcp = HCP(name=hcp_name)
            db.add(hcp)
            db.flush()

        interaction = Interaction(
            hcp_id=hcp.id,
            hcp_name=hcp_name,
            interaction_type=fields.get("interaction_type", "Meeting") or "Meeting",
            interaction_date=datetime.utcnow(),
            attendees=fields.get("attendees", []),
            topics_discussed=fields.get("topics_discussed", ""),
            materials_shared=fields.get("materials_shared", []),
            samples_distributed=fields.get("samples_distributed", []),
            sentiment=fields.get("sentiment", "neutral") or "neutral",
            outcomes=fields.get("outcomes", ""),
            follow_up_actions=fields.get("follow_up_actions", ""),
            raw_source_text=free_text,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        result = {
            "id": interaction.id,
            "hcp_name": interaction.hcp_name,
            "interaction_type": interaction.interaction_type,
            "sentiment": interaction.sentiment,
            "topics_discussed": interaction.topics_discussed,
            "status": "logged",
        }
        return json.dumps(result)
    finally:
        db.close()


@tool
def edit_interaction(interaction_id: str, updates_json: str) -> str:
    """
    Edit an existing logged interaction. `interaction_id` is the record's id.
    `updates_json` is a JSON string of the fields to change, e.g.
    '{"sentiment": "positive", "outcomes": "Agreed to trial samples"}'.
    Returns a JSON string confirming the updated record.
    """
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"error": f"No interaction found with id {interaction_id}"})

        updates = json.loads(updates_json)
        allowed = {
            "hcp_name", "interaction_type", "attendees", "topics_discussed",
            "materials_shared", "samples_distributed", "sentiment",
            "outcomes", "follow_up_actions",
        }
        for key, value in updates.items():
            if key in allowed:
                setattr(interaction, key, value)
        interaction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(interaction)

        return json.dumps({
            "id": interaction.id,
            "status": "updated",
            "updated_fields": list(updates.keys()),
        })
    finally:
        db.close()


@tool
def search_hcp_history(hcp_name: str) -> str:
    """
    Retrieve past logged interactions for a given HCP by name (fuzzy match).
    Useful for giving reps context before a visit ("What did we last discuss
    with Dr. Smith?"). Returns a JSON array of past interaction summaries.
    """
    db = SessionLocal()
    try:
        interactions = (
            db.query(Interaction)
            .filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
            .order_by(Interaction.interaction_date.desc())
            .limit(5)
            .all()
        )
        history = [
            {
                "id": i.id,
                "date": i.interaction_date.isoformat() if i.interaction_date else None,
                "type": i.interaction_type,
                "topics": i.topics_discussed,
                "sentiment": i.sentiment,
                "outcomes": i.outcomes,
            }
            for i in interactions
        ]
        return json.dumps(history)
    finally:
        db.close()


@tool
def schedule_followup(interaction_id: str, followup_note: str, days_from_now: int = 14) -> str:
    """
    Schedule a follow-up action tied to a logged interaction (e.g. "Schedule
    follow-up meeting in 2 weeks"). Appends the follow-up note and target date
    to the interaction's follow_up_actions field.
    """
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"error": f"No interaction found with id {interaction_id}"})

        target_date = (datetime.utcnow() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")
        note = f"[Follow-up by {target_date}] {followup_note}"
        interaction.follow_up_actions = (
            f"{interaction.follow_up_actions}\n{note}".strip()
            if interaction.follow_up_actions else note
        )
        db.commit()
        return json.dumps({"id": interaction.id, "status": "followup_scheduled", "target_date": target_date})
    finally:
        db.close()


@tool
def suggest_next_best_action(interaction_id: str) -> str:
    """
    Use the LLM to suggest up to 3 AI-recommended next-best-actions for a
    logged interaction (e.g. schedule follow-up, share specific materials,
    add HCP to advisory board list). Persists suggestions on the record and
    returns them as a JSON array.
    """
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"error": f"No interaction found with id {interaction_id}"})

        summary = (
            f"HCP: {interaction.hcp_name}, Type: {interaction.interaction_type}, "
            f"Topics: {interaction.topics_discussed}, Sentiment: {interaction.sentiment}, "
            f"Outcomes: {interaction.outcomes}"
        )
        llm = get_llm(temperature=0.4)
        response = llm.invoke(SUGGESTION_PROMPT.format(summary=summary))
        raw = response.content.strip()
        try:
            suggestions = json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("["), raw.rfind("]")
            suggestions = json.loads(raw[start:end + 1]) if start != -1 else []

        interaction.ai_suggested_followups = suggestions
        db.commit()
        return json.dumps(suggestions)
    finally:
        db.close()


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    search_hcp_history,
    schedule_followup,
    suggest_next_best_action,
]
