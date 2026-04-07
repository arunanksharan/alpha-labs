"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { AgentEvent } from "@/types";
import { WS_URL } from "@/lib/utils";

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);

    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000); // Reconnect
    };
    socket.onmessage = (msg) => {
      try {
        const event: AgentEvent = JSON.parse(msg.data);
        setEvents((prev) => [...prev.slice(-99), event]);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.current = socket;
  }, []);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);

  return { events, connected };
}
