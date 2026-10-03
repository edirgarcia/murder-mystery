import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { useSessionRestore } from "@shared/hooks/useRestoreSession";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { buildWsUrl, getGameInfo, getState } from "../api/http";
import type { GamePhase, PlayerInfo, PrivateState, PublicState, WSEvent } from "../types/game";

// The server pushes full public/private snapshots after every change, so the
// client is a thin mirror: no per-event reducers to keep in sync.
interface TCState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: PlayerInfo[];
  pub: PublicState | null;
  priv: PrivateState | null;
  // serverTime - clientTime in ms, so countdowns are fair across devices.
  clockOffset: number;
}

interface TCContextValue {
  state: TCState;
  setGame: (code: string, playerId: string, playerName: string, isHost: boolean) => void;
  setPlayers: (players: PlayerInfo[]) => void;
  setPhase: (phase: GamePhase) => void;
  setPublic: (pub: PublicState) => void;
  setPrivate: (priv: PrivateState | null) => void;
}

const initialState: TCState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  pub: null,
  priv: null,
  clockOffset: 0,
};

const TCContext = createContext<TCContextValue | null>(null);

export function TCProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TCState>(initialState);

  const setGame = useCallback(
    (code: string, playerId: string, playerName: string, isHost: boolean) =>
      setState((s) => ({ ...s, code, playerId, playerName, isHost, phase: s.phase ?? "lobby" })),
    []
  );
  const setPlayers = useCallback((players: PlayerInfo[]) => setState((s) => ({ ...s, players })), []);
  const setPhase = useCallback((phase: GamePhase) => setState((s) => ({ ...s, phase })), []);
  const setPublic = useCallback(
    (pub: PublicState) =>
      setState((s) => ({
        ...s,
        pub,
        clockOffset: new Date(pub.server_time).getTime() - Date.now(),
      })),
    []
  );
  const setPrivate = useCallback((priv: PrivateState | null) => setState((s) => ({ ...s, priv })), []);

  const value = useMemo(
    () => ({ state, setGame, setPlayers, setPhase, setPublic, setPrivate }),
    [state, setGame, setPlayers, setPhase, setPublic, setPrivate]
  );
  return <TCContext.Provider value={value}>{children}</TCContext.Provider>;
}

export function useTC() {
  const ctx = useContext(TCContext);
  if (!ctx) throw new Error("useTC must be used within TCProvider");
  return ctx;
}

/**
 * Restores the session, loads the current snapshot and keeps it live over
 * the WebSocket. Used by every in-game page (player, dashboard, results).
 * `onEvent` sees every server event (e.g. narration); `send` writes to the socket.
 */
export function useTCConnection(code: string | undefined, onEvent?: (event: WSEvent) => void) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const navigate = useNavigate();
  const { state, setGame, setPlayers, setPhase, setPublic, setPrivate } = useTC();
  useSessionRestore("tc", code, state.playerId, setGame);

  useEffect(() => {
    if (!code || !state.playerId) return;
    getGameInfo(code)
      .then((info) => {
        setPlayers(info.players);
        setPhase(info.phase);
        if (info.phase === "lobby") navigate(`/lobby/${code}`, { replace: true });
      })
      .catch(() => navigate("/", { replace: true }));
    getState(code, state.playerId)
      .then((s) => {
        setPublic(s.public);
        setPrivate(s.private);
      })
      .catch(() => undefined);
  }, [code, state.playerId, navigate, setPhase, setPlayers, setPublic, setPrivate]);

  const handleEvent = useCallback(
    (event: WSEvent) => {
      onEventRef.current?.(event);
      switch (event.event) {
        case "state":
          setPublic(event.data as unknown as PublicState);
          break;
        case "private_state":
          setPrivate(event.data as unknown as PrivateState);
          break;
        case "game_over":
          setPhase("finished");
          navigate(`/result/${code}`);
          break;
      }
    },
    [code, navigate, setPhase, setPrivate, setPublic]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  const wsRef = useWebSocket(wsUrl, handleEvent);

  const send = useCallback(
    (message: Record<string, unknown>) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
    },
    [wsRef]
  );

  return { state, send };
}
