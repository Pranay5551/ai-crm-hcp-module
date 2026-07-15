import { configureStore } from "@reduxjs/toolkit";
import interactionsReducer from "./interactionsSlice";

export const store = configureStore({
  reducer: {
    interactions: interactionsReducer,
  },
});
