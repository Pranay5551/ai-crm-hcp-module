import React, { useState, useRef, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage } from "../store/interactionsSlice";

const SESSION_ID = "demo-session-1"; // in production: derive per logged-in rep

export default function ChatAssistant() {
  const dispatch = useDispatch();
  const { chatMessages, chatStatus } = useSelector((s) => s.interactions);
  const [input, setInput] = useState("");
  const threadRef = useRef(null);

  useEffect(() => {
    threadRef.current?.scrollTo(0, threadRef.current.scrollHeight);
  }, [chatMessages]);

  const handleSend = () => {
    if (!input.trim()) return;
    dispatch(sendChatMessage({ sessionId: SESSION_ID, message: input.trim() }));
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <div className="panel chat-panel">
      <div className="chat-header">🤖 AI Assistant — Log interaction via chat</div>

      <div className="chat-thread" ref={threadRef}>
        {chatMessages.length === 0 && (
          <div className="chat-bubble assistant">
            Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy,
            positive sentiment, shared brochure") or ask for help.
          </div>
        )}
        {chatMessages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.content}
            {m.toolCalls?.length > 0 && (
              <span className="tool-tag">tools used: {m.toolCalls.join(", ")}</span>
            )}
          </div>
        ))}
        {chatStatus === "loading" && (
          <div className="chat-bubble assistant">Thinking…</div>
        )}
      </div>

      <div className="chat-input-row">
        <input
          placeholder="Describe interaction..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="btn-primary" onClick={handleSend} disabled={chatStatus === "loading"}>
          Log
        </button>
      </div>
    </div>
  );
}
