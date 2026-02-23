import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import { setInitDataProvider } from "./api/client";

// Set up initData provider for API client
// Will be populated once Telegram SDK initializes
setInitDataProvider(() => {
  return window.Telegram?.WebApp?.initData ?? "";
});

// Declare Telegram global
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
      };
    };
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
