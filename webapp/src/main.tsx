import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { init, isTMA } from "@telegram-apps/sdk-react";
import "./index.css";
import App from "./App";
import { setInitDataProvider } from "./api/client";

// Инициализация SDK. Без неё приложение выглядит работающим, но ломается на первом же
// действии, и очень неочевидно.
//
// В @telegram-apps/sdk v2 каждая функция обёрнута проверкой: если сигнал версии равен
// "0.0" — а его выставляет именно init() — вызов бросает ERR_NOT_INITIALIZED («the SDK
// was not initialized. Use the SDK init() function»). init() не вызывался нигде, поэтому
// бросали все: hapticFeedbackImpactOccurred, hapticFeedbackSelectionChanged, openInvoice.
//
// Исключение летит синхронно из обработчика клика и убивает всё, что стоит в обработчике
// после него:
//   • VotingPage.handleNext  — haptic.impactOccurred() до navigate() → «Confirm Selection
//     ничего не делает»;
//   • VotingPage.sendVote    — haptic.selectionChanged() между оптимистичным апдейтом и
//     voteMutation.mutate() → счётчик +/- бегает, но POST /vote не уходит и в БД ноль.
//
// Отсюда же и то, что useTelegramUser() (useSignal(initDataUser)) возвращал undefined.
//
// isTMA("simple") — чтобы открытие в обычном браузере (например, при отладке) не падало
// на старте: там init() бросил бы ERR_UNKNOWN_ENV.
if (isTMA("simple")) {
  init();
}

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
