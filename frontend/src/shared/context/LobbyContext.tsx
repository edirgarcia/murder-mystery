import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
  type Dispatch,
} from "react";
import type { GamePhase, PlayerInfo } from "../types/game";

export interface LobbyState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: PlayerInfo[];
  error: string | null;
}

type LobbyAction =
  | { type: "SET_GAME"; code: string; playerId: string; playerName: string; isHost: boolean }
  | { type: "SET_PHASE"; phase: GamePhase }
  | { type: "SET_PLAYERS"; players: PlayerInfo[] }
  | { type: "ADD_PLAYER"; player: PlayerInfo }
  | { type: "REMOVE_PLAYER"; playerId: string }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" };

const initialState: LobbyState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  error: null,
};

function lobbyReducer(state: LobbyState, action: LobbyAction): LobbyState {
  switch (action.type) {
    case "SET_GAME":
      return {
        ...state,
        code: action.code,
        playerId: action.playerId,
        playerName: action.playerName,
        isHost: action.isHost,
        phase: "lobby",
      };
    case "SET_PHASE":
      return { ...state, phase: action.phase };
    case "SET_PLAYERS":
      return { ...state, players: action.players };
    case "ADD_PLAYER":
      if (state.players.find((p) => p.id === action.player.id)) return state;
      return { ...state, players: [...state.players, action.player] };
    case "REMOVE_PLAYER":
      return {
        ...state,
        players: state.players.filter((p) => p.id !== action.playerId),
      };
    case "SET_ERROR":
      return { ...state, error: action.error };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

const LobbyContext = createContext<{
  state: LobbyState;
  dispatch: Dispatch<LobbyAction>;
} | null>(null);

export function LobbyProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(lobbyReducer, initialState);
  return (
    <LobbyContext.Provider value={{ state, dispatch }}>
      {children}
    </LobbyContext.Provider>
  );
}

export function useLobby() {
  const ctx = useContext(LobbyContext);
  if (!ctx) throw new Error("useLobby must be used within LobbyProvider");
  return ctx;
}

export function useLobbyActions() {
  const { dispatch } = useLobby();

  const setGame = useCallback(
    (code: string, playerId: string, playerName: string, isHost: boolean) =>
      dispatch({ type: "SET_GAME", code, playerId, playerName, isHost }),
    [dispatch]
  );

  const setPhase = useCallback(
    (phase: GamePhase) => dispatch({ type: "SET_PHASE", phase }),
    [dispatch]
  );

  const setPlayers = useCallback(
    (players: PlayerInfo[]) => dispatch({ type: "SET_PLAYERS", players }),
    [dispatch]
  );

  const addPlayer = useCallback(
    (player: PlayerInfo) => dispatch({ type: "ADD_PLAYER", player }),
    [dispatch]
  );

  const setError = useCallback(
    (error: string) => dispatch({ type: "SET_ERROR", error }),
    [dispatch]
  );

  const reset = useCallback(() => dispatch({ type: "RESET" }), [dispatch]);

  return { setGame, setPhase, setPlayers, addPlayer, setError, reset };
}
