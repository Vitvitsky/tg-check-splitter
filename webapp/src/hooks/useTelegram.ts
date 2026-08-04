import {
  useLaunchParams,
  useSignal,
  initDataUser,
  hapticFeedbackImpactOccurred,
  hapticFeedbackNotificationOccurred,
  hapticFeedbackSelectionChanged,
  mainButton,
  backButton,
} from "@telegram-apps/sdk-react";
import type { User } from "@telegram-apps/sdk-react";

export function useTelegramUser(): User | undefined {
  return useSignal(initDataUser);
}

export function useRawInitData(): string {
  const lp = useLaunchParams();
  return lp.initDataRaw ?? "";
}

/**
 * Тактильная отдача — украшение, и она не должна стоять на пути у действия.
 *
 * Функции SDK v2 бросают исключение, если метод не поддержан клиентом
 * (ERR_NOT_SUPPORTED — Telegram Desktop и старые версии не умеют haptic) или если SDK
 * не инициализирован (ERR_NOT_INITIALIZED). Вызовы стоят внутри обработчиков кликов
 * *перед* navigate() и mutate(), поэтому любое такое исключение молча отменяло само
 * действие: кнопка нажимается, а переход и запрос не происходят.
 *
 * init() в main.tsx закрывает причину ERR_NOT_INITIALIZED, но поддержка платформы от нас
 * не зависит — поэтому глушим здесь, а не полагаемся только на init().
 */
function quiet<A extends unknown[]>(fn: (...args: A) => unknown) {
  return (...args: A): void => {
    try {
      fn(...args);
    } catch {
      // Вибрации нет — действие всё равно должно выполниться.
    }
  };
}

const haptic = {
  impactOccurred: quiet(hapticFeedbackImpactOccurred),
  notificationOccurred: quiet(hapticFeedbackNotificationOccurred),
  selectionChanged: quiet(hapticFeedbackSelectionChanged),
};

export function useHaptic() {
  return haptic;
}

export { mainButton, backButton };
