import { ApiError } from "@/api/client";

/**
 * Turn a failed request into something the user can act on.
 *
 * Pages used to wrap mutations in a bare `catch {}`, so a rejected request changed
 * nothing on screen and explained nothing. That became a visible dead end once the API
 * started returning 409 for a settled session: tapping a dish simply did nothing.
 */
export function isSettledError(err: unknown): boolean {
  return (
    err instanceof ApiError &&
    err.status === 409 &&
    (err.data as { detail?: string } | null)?.detail === "session_settled"
  );
}

export function isQuotaError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 402;
}

export function apiErrorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return "Что-то пошло не так. Попробуйте ещё раз.";
  switch (err.status) {
    case 401:
      return "Откройте мини-приложение из Telegram.";
    case 402:
      return "Лимит сканов исчерпан.";
    case 403:
      return "Нет доступа к этому чеку.";
    case 404:
      return "Чек не найден — возможно, ссылка устарела.";
    case 409:
      return isSettledError(err)
        ? "Чек уже рассчитан, изменить его нельзя."
        : "Это действие сейчас недоступно.";
    case 502:
    case 504:
      return "Сервис временно недоступен. Попробуйте позже.";
    default:
      return "Что-то пошло не так. Попробуйте ещё раз.";
  }
}
