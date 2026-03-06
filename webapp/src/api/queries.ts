import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchApi, fetchApiNoBody } from "./client";
import type {
  Session,
  SessionBrief,
  Share,
  Quota,
  Item,
  Member,
  OcrResult,
  VoteResult,
} from "./types";

// ---- Queries ----

export function useSession(inviteCode: string) {
  return useQuery({
    queryKey: ["session", "invite", inviteCode],
    queryFn: () =>
      fetchApi<Session>(`/api/sessions/invite/${inviteCode}`),
    enabled: !!inviteCode,
  });
}

export function useSessionById(sessionId: string) {
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => fetchApi<Session>(`/api/sessions/${sessionId}`),
    enabled: !!sessionId,
  });
}

export function useMySessions() {
  return useQuery({
    queryKey: ["sessions", "my"],
    queryFn: () => fetchApi<SessionBrief[]>("/api/sessions/my"),
  });
}

export function useShares(sessionId: string) {
  return useQuery({
    queryKey: ["shares", sessionId],
    queryFn: () => fetchApi<Share[]>(`/api/sessions/${sessionId}/shares`),
    enabled: !!sessionId,
  });
}

export function useMyShare(sessionId: string) {
  return useQuery({
    queryKey: ["my-share", sessionId],
    queryFn: () => fetchApi<Share>(`/api/sessions/${sessionId}/my-share`),
    enabled: !!sessionId,
  });
}

export function useQuota() {
  return useQuery({
    queryKey: ["quota"],
    queryFn: () => fetchApi<Quota>("/api/quota"),
  });
}

// ---- Mutations ----

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (currency: string = "RUB") =>
      fetchApi<Session>("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ currency }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions", "my"] }),
  });
}

export function useJoinSession() {
  return useMutation({
    mutationFn: (inviteCode: string) =>
      fetchApi<Member>(`/api/sessions/invite/${inviteCode}/join`, {
        method: "POST",
      }),
  });
}

export function useVote(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { itemId: string; quantity?: number }) =>
      fetchApi<VoteResult>(`/api/sessions/${sessionId}/vote`, {
        method: "POST",
        body: JSON.stringify({ item_id: args.itemId, quantity: args.quantity }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["session"] });
      qc.invalidateQueries({ queryKey: ["my-share", sessionId] });
    },
  });
}

export function useSetTip(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tipPercent: number) =>
      fetchApi<unknown>(`/api/sessions/${sessionId}/tip`, {
        method: "POST",
        body: JSON.stringify({ tip_percent: tipPercent }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-share", sessionId] });
      qc.invalidateQueries({ queryKey: ["shares", sessionId] });
    },
  });
}

export function useConfirm(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<unknown>(`/api/sessions/${sessionId}/confirm`, {
        method: "POST",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useUnconfirm(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<unknown>(`/api/sessions/${sessionId}/unconfirm`, {
        method: "POST",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useUploadPhotos(sessionId: string) {
  return useMutation({
    mutationFn: async (files: File[]) => {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      // Don't set Content-Type — browser sets multipart boundary
      return fetchApiNoBody(`/api/sessions/${sessionId}/photos`, {
        method: "POST",
        body: formData,
        headers: {}, // Override default Content-Type
      });
    },
  });
}

export function useTriggerOcr(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<OcrResult>(`/api/sessions/${sessionId}/ocr`, {
        method: "POST",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useUpdateItems(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (
      items: Array<{ name: string; price: number; quantity?: number }>,
    ) =>
      fetchApi<Item[]>(`/api/sessions/${sessionId}/items`, {
        method: "PUT",
        body: JSON.stringify({ items }),
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useDeleteItem(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) =>
      fetchApiNoBody(`/api/sessions/${sessionId}/items/${itemId}`, {
        method: "DELETE",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useFinishVoting(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<unknown>(`/api/sessions/${sessionId}/finish`, {
        method: "POST",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useSettle(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<Share[]>(`/api/sessions/${sessionId}/settle`, {
        method: "POST",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["session"] });
      qc.invalidateQueries({ queryKey: ["shares", sessionId] });
    },
  });
}

export function useResolveUnvoted(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (decisions: Record<string, "split" | "remove">) =>
      fetchApi<unknown>(`/api/sessions/${sessionId}/resolve-unvoted`, {
        method: "POST",
        body: JSON.stringify({ decisions }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["session"] }),
  });
}

export function useRemind(sessionId: string) {
  return useMutation({
    mutationFn: (memberTgId: number) =>
      fetchApi<{ sent: boolean }>(
        `/api/sessions/${sessionId}/remind/${memberTgId}`,
        { method: "POST" },
      ),
  });
}

export function useResetQuota() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<unknown>("/api/quota/reset", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quota"] }),
  });
}

export function useClearHistory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApiNoBody("/api/sessions/history", { method: "DELETE" }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["sessions", "my"] }),
  });
}
