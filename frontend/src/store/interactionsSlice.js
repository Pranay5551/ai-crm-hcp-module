import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export const fetchInteractions = createAsyncThunk(
  "interactions/fetchAll",
  async () => {
    const res = await axios.get(`${API_BASE}/api/interactions/`);
    return res.data;
  }
);

export const createInteraction = createAsyncThunk(
  "interactions/create",
  async (payload) => {
    const res = await axios.post(`${API_BASE}/api/interactions/`, payload);
    return res.data;
  }
);

export const sendChatMessage = createAsyncThunk(
  "interactions/sendChatMessage",
  async ({ sessionId, message }) => {
    const res = await axios.post(`${API_BASE}/api/chat/`, {
      session_id: sessionId,
      message,
    });
    return res.data;
  }
);

const initialState = {
  items: [],
  status: "idle", // idle | loading | succeeded | failed
  error: null,
  chatMessages: [], // { role: 'user' | 'assistant', content: string }
  chatStatus: "idle",
  formDraft: {
    hcp_name: "",
    interaction_type: "Meeting",
    interaction_date: "",
    time: "",
    attendees: [],
    topics_discussed: "",
    materials_shared: [],
    samples_distributed: [],
    sentiment: "neutral",
    outcomes: "",
    follow_up_actions: "",
  },
};

const interactionsSlice = createSlice({
  name: "interactions",
  initialState,
  reducers: {
    updateFormDraft(state, action) {
      state.formDraft = { ...state.formDraft, ...action.payload };
    },
    resetFormDraft(state) {
      state.formDraft = initialState.formDraft;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.items = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message;
      })
      .addCase(createInteraction.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
        state.formDraft = initialState.formDraft;
      })
      .addCase(sendChatMessage.pending, (state, action) => {
        state.chatStatus = "loading";
        state.chatMessages.push({ role: "user", content: action.meta.arg.message });
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatStatus = "succeeded";
        state.chatMessages.push({
          role: "assistant",
          content: action.payload.reply,
          toolCalls: action.payload.tool_calls,
        });
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatStatus = "failed";
        state.chatMessages.push({
          role: "assistant",
          content: "Sorry, something went wrong processing that.",
        });
      });
  },
});

export const { updateFormDraft, resetFormDraft } = interactionsSlice.actions;
export default interactionsSlice.reducer;
