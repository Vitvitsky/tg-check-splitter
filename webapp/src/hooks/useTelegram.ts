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

export function useHaptic() {
  return {
    impactOccurred: hapticFeedbackImpactOccurred,
    notificationOccurred: hapticFeedbackNotificationOccurred,
    selectionChanged: hapticFeedbackSelectionChanged,
  };
}

export { mainButton, backButton };
