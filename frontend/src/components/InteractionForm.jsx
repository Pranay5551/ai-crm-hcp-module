import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { updateFormDraft, createInteraction } from "../store/interactionsSlice";

const SENTIMENTS = ["positive", "neutral", "negative"];

export default function InteractionForm() {
  const dispatch = useDispatch();
  const draft = useSelector((s) => s.interactions.formDraft);
  const [saveState, setSaveState] = useState("idle"); // idle | saving | success | error
  const [errorMsg, setErrorMsg] = useState("");

  const set = (field) => (e) => dispatch(updateFormDraft({ [field]: e.target.value }));

  const handleSubmit = async () => {
    setSaveState("saving");
    setErrorMsg("");
    try {
      await dispatch(createInteraction(draft)).unwrap();
      setSaveState("success");
      setTimeout(() => setSaveState("idle"), 3000);
    } catch (err) {
      setSaveState("error");
      setErrorMsg(err?.message || "Failed to save. Check that the backend is running.");
    }
  };

  return (
    <div className="panel">
      <h2 className="panel-title">Log HCP Interaction</h2>

      <div className="field-row">
        <div className="field">
          <label>HCP Name</label>
          <input
            placeholder="Search or select HCP..."
            value={draft.hcp_name}
            onChange={set("hcp_name")}
          />
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <select value={draft.interaction_type} onChange={set("interaction_type")}>
            <option>Meeting</option>
            <option>Call</option>
            <option>Email</option>
            <option>Conference</option>
          </select>
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Date</label>
          <input type="date" value={draft.interaction_date} onChange={set("interaction_date")} />
        </div>
        <div className="field">
          <label>Time</label>
          <input type="time" value={draft.time} onChange={set("time")} />
        </div>
      </div>

      <div className="field" style={{ marginBottom: 12 }}>
        <label>Attendees</label>
        <input
          placeholder="Enter names or search..."
          value={draft.attendees.join(", ")}
          onChange={(e) =>
            dispatch(updateFormDraft({ attendees: e.target.value.split(",").map((s) => s.trim()) }))
          }
        />
      </div>

      <div className="field" style={{ marginBottom: 8 }}>
        <label>Topics Discussed</label>
        <textarea
          placeholder="Enter key discussion points..."
          value={draft.topics_discussed}
          onChange={set("topics_discussed")}
        />
      </div>
      <button className="btn-secondary" style={{ marginBottom: 16 }}>
        🎙 Summarize from Voice Note (Requires Consent)
      </button>

      <div className="field-row">
        <div className="field">
          <label>Materials Shared</label>
          <input
            placeholder="No materials added"
            value={draft.materials_shared.join(", ")}
            onChange={(e) =>
              dispatch(updateFormDraft({ materials_shared: e.target.value.split(",").map((s) => s.trim()) }))
            }
          />
        </div>
        <div className="field">
          <label>Samples Distributed</label>
          <input
            placeholder="No samples added"
            value={draft.samples_distributed.join(", ")}
            onChange={(e) =>
              dispatch(updateFormDraft({ samples_distributed: e.target.value.split(",").map((s) => s.trim()) }))
            }
          />
        </div>
      </div>

      <div className="field" style={{ marginBottom: 4 }}>
        <label>Observed / Inferred HCP Sentiment</label>
      </div>
      <div className="sentiment-row">
        {SENTIMENTS.map((s) => (
          <label
            key={s}
            className="sentiment-option"
            data-value={s}
            data-active={draft.sentiment === s}
          >
            <input
              type="radio"
              name="sentiment"
              checked={draft.sentiment === s}
              onChange={() => dispatch(updateFormDraft({ sentiment: s }))}
            />
            {s[0].toUpperCase() + s.slice(1)}
          </label>
        ))}
      </div>

      <div className="field" style={{ marginBottom: 12 }}>
        <label>Outcomes</label>
        <textarea
          placeholder="Key outcomes or agreements..."
          value={draft.outcomes}
          onChange={set("outcomes")}
        />
      </div>

      <div className="field" style={{ marginBottom: 12 }}>
        <label>Follow-up Actions</label>
        <textarea
          placeholder="Enter next steps or tasks..."
          value={draft.follow_up_actions}
          onChange={set("follow_up_actions")}
        />
      </div>

      <button className="btn-primary" onClick={handleSubmit} disabled={!draft.hcp_name || saveState === "saving"}>
        {saveState === "saving" ? "Saving..." : "Save Interaction"}
      </button>
      {saveState === "success" && (
        <p style={{ color: "#1A8A5F", fontSize: 13, marginTop: 8 }}>✓ Interaction saved successfully.</p>
      )}
      {saveState === "error" && (
        <p style={{ color: "#C4432B", fontSize: 13, marginTop: 8 }}>✗ {errorMsg}</p>
      )}
    </div>
  );
}