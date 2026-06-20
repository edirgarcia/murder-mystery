import { useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { WSEvent } from "../types/game";
import { HOST_LEFT_NOTICE_KEY } from "../constants";

type EventHandler = (event: WSEvent) => void;

export function useWebSocket(
  wsUrl: string | null,
  onEvent: EventHandler
) {
  const navigate = useNavigate();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const intentionalClose = useRef(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!wsUrl) return;

    intentionalClose.current = false;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    };

    ws.onmessage = (e) => {
      try {
        const event: WSEvent = JSON.parse(e.data);
        if (event.event === "host_left") {
          // Host ended the game — stop reconnecting and return to the home
          // page with a notice. (Host pages never receive this event.)
          intentionalClose.current = true;
          clearTimeout(reconnectTimer.current);
          ws.close();
          sessionStorage.setItem(HOST_LEFT_NOTICE_KEY, "1");
          navigate("/");
          return;
        }
        if (event.event !== "pong") {
          onEventRef.current(event);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      // Only reconnect if this was an unexpected disconnect
      if (!intentionalClose.current && ws === wsRef.current) {
        reconnectTimer.current = setTimeout(connect, 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [wsUrl, navigate]);

  useEffect(() => {
    connect();
    return () => {
      intentionalClose.current = true;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
