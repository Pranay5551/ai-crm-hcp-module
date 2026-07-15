import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import InteractionForm from "./InteractionForm";
import ChatAssistant from "./ChatAssistant";
import { fetchInteractions } from "../store/interactionsSlice";

export default function LogInteractionScreen() {
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(fetchInteractions());
  }, [dispatch]);

  return (
    <div className="screen-grid">
      <InteractionForm />
      <ChatAssistant />
    </div>
  );
}
