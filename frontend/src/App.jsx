import React from "react";
import LogInteractionScreen from "./components/LogInteractionScreen";

export default function App() {
  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>AI-First CRM</h1>
        <span>HCP Module — Log Interaction</span>
      </div>
      <LogInteractionScreen />
    </div>
  );
}
