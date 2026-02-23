import { useEffect, useRef, useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRawInitData } from "./useTelegram";

type WsEventType =
  | "vote_updated"
  | "member_joined"
  | "member_confirmed"
  | "member_unconfirmed"
  | "tip_changed"
  | "session_status"
  | "items_updated";

interface WsEvent {
  type: WsEventType;
  data: Record<string, unknown>;
}

export function useWebSocket(sessionId: string | null) {
  const initData = useRawInitData();
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>(undefined);
  const reconnectDelay = useRef(1000);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);

  const connect = useCallback(() => {
    if (!sessionId || !initData) return;

    const protocol =
      window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}?token=${encodeURIComponent(initData)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectDelay.current = 1000; // Reset backoff
    };

    ws.onmessage = (event) => {
      try {
        const parsed: WsEvent = JSON.parse(event.data as string);
        setLastEvent(parsed);
        // Invalidate relevant queries
        queryClient.invalidateQueries({
          queryKey: ["session", sessionId],
        });
        if (
          parsed.type === "tip_changed" ||
          parsed.type === "vote_updated"
        ) {
          queryClient.invalidateQueries({
            queryKey: ["shares", sessionId],
          });
          queryClient.invalidateQueries({
            queryKey: ["my-share", sessionId],
          });
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      // Auto-reconnect with exponential backoff
      reconnectTimeout.current = setTimeout(() => {
        reconnectDelay.current = Math.min(
          reconnectDelay.current * 2,
          30000,
        );
        connect();
      }, reconnectDelay.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [sessionId, initData, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected, lastEvent };
}
