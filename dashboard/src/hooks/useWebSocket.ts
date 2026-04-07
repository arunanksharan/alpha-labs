"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { AgentEvent } from "@/types";
import { WS_URL } from "@/lib/utils";

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    // Clean up previous socket
    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
    }

    try {
      const socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        setConnected(true);
        console.log("[WS] Connected to", WS_URL);
      };

      socket.onclose = () => {
        setConnected(false);
        // Reconnect with backoff (suppress console noise)
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      socket.onerror = () => {
        // Silently handle — onclose will fire after this
      };

      socket.onmessage = (msg) => {
        try {
          const event: AgentEvent = JSON.parse(msg.data);
          setEvents((prev) => [...prev.slice(-99), event]);
        } catch {
          // Ignore malformed
        }
      };

      ws.current = socket;
    } catch {
      // WebSocket constructor can throw if URL is invalid
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, []);

  useEffect(() => {
    // Delay first connect slightly to avoid SSR race
    const timer = setTimeout(connect, 500);
    return () => {
      clearTimeout(timer);
      clearTimeout(reconnectTimer.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [connect]);

  return { events, connected };
}
