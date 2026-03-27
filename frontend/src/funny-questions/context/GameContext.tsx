import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
  type Dispatch,
} from "react";
import type { GamePhase, PlayerInfo } from "@shared/types/game";
import type { RoundResult } from "../types/game";

interface FQState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: PlayerInfo[];
  scores: Record<string, number>;
  currentQuestion: string | null;
  currentRound: number;
  roundPhase: "voting" | "reveal" | null;
  votingEndsAt: string | null;
  hasVoted: boolean;
  roundResult: RoundResult | null;
  shameHolder: string | null;
  winner: string | null;
  pointsToWin: number;
  hostPaced: boolean;
  error: string | null;
}

type FQAction =
  | { type: "SET_GAME"; code: string; playerId: string; playerName: string; isHost: boolean }
  | { type: "SET_PHASE"; phase: GamePhase }
  | { type: "SET_PLAYERS"; players: PlayerInfo[] }
  | { type: "ADD_PLAYER"; player: PlayerInfo }
  | { type: "SET_SCORES"; scores: Record<string, number> }
  | { type: "NEW_QUESTION"; question: string; round: number; votingEndsAt: string; players: PlayerInfo[] }
  | { type: "SET_VOTED" }
  | { type: "SET_ROUND_RESULT"; result: RoundResult }
  | { type: "SET_WINNER"; winner: string }
  | { type: "SET_POINTS_TO_WIN"; pointsToWin: number }
  | { type: "SET_HOST_PACED"; hostPaced: boolean }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" }
  | { type: "RESET_GAME" };

const initialState: FQState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  scores: {},
  currentQuestion: null,
  currentRound: 0,
  roundPhase: null,
  votingEndsAt: null,
  hasVoted: false,
  roundResult: null,
  shameHolder: null,
  winner: null,
  pointsToWin: 20,
  hostPaced: false,
  error: null,
};

function fqReducer(state: FQState, action: FQAction): FQState {
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
    case "SET_SCORES":
      return { ...state, scores: action.scores };
    case "NEW_QUESTION":
      return {
        ...state,
        currentQuestion: action.question,
        currentRound: action.round,
        roundPhase: "voting",
        votingEndsAt: action.votingEndsAt,
        hasVoted: false,
        roundResult: null,
        players: action.players,
      };
    case "SET_VOTED":
      return { ...state, hasVoted: true };
    case "SET_ROUND_RESULT":
      return {
        ...state,
        roundPhase: "reveal",
        roundResult: action.result,
        scores: action.result.scores,
        shameHolder: action.result.shame_holder_name,
        winner: action.result.winner_name,
      };
    case "SET_WINNER":
      return { ...state, winner: action.winner, phase: "finished" };
    case "SET_POINTS_TO_WIN":
      return { ...state, pointsToWin: action.pointsToWin };
    case "SET_HOST_PACED":
      return { ...state, hostPaced: action.hostPaced };
    case "SET_ERROR":
      return { ...state, error: action.error };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    case "RESET":
      return initialState;
    case "RESET_GAME":
      return {
        ...initialState,
        code: state.code,
        playerId: state.playerId,
        playerName: state.playerName,
        isHost: state.isHost,
        players: state.players,
        phase: "lobby",
      };
    default:
      return state;
  }
}

const FQContext = createContext<{
  state: FQState;
  dispatch: Dispatch<FQAction>;
} | null>(null);

export function FQProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(fqReducer, initialState);
  return (
    <FQContext.Provider value={{ state, dispatch }}>
      {children}
    </FQContext.Provider>
  );
}

export function useFQ() {
  const ctx = useContext(FQContext);
  if (!ctx) throw new Error("useFQ must be used within FQProvider");
  return ctx;
}

export function useFQActions() {
  const { dispatch } = useFQ();

  return {
    setGame: useCallback(
      (code: string, playerId: string, playerName: string, isHost: boolean) =>
        dispatch({ type: "SET_GAME", code, playerId, playerName, isHost }),
      [dispatch]
    ),
    setPhase: useCallback(
      (phase: GamePhase) => dispatch({ type: "SET_PHASE", phase }),
      [dispatch]
    ),
    setPlayers: useCallback(
      (players: PlayerInfo[]) => dispatch({ type: "SET_PLAYERS", players }),
      [dispatch]
    ),
    addPlayer: useCallback(
      (player: PlayerInfo) => dispatch({ type: "ADD_PLAYER", player }),
      [dispatch]
    ),
    setScores: useCallback(
      (scores: Record<string, number>) => dispatch({ type: "SET_SCORES", scores }),
      [dispatch]
    ),
    newQuestion: useCallback(
      (question: string, round: number, votingEndsAt: string, players: PlayerInfo[]) =>
        dispatch({ type: "NEW_QUESTION", question, round, votingEndsAt, players }),
      [dispatch]
    ),
    setVoted: useCallback(() => dispatch({ type: "SET_VOTED" }), [dispatch]),
    setRoundResult: useCallback(
      (result: RoundResult) => dispatch({ type: "SET_ROUND_RESULT", result }),
      [dispatch]
    ),
    setWinner: useCallback(
      (winner: string) => dispatch({ type: "SET_WINNER", winner }),
      [dispatch]
    ),
    setPointsToWin: useCallback(
      (pointsToWin: number) => dispatch({ type: "SET_POINTS_TO_WIN", pointsToWin }),
      [dispatch]
    ),
    setHostPaced: useCallback(
      (hostPaced: boolean) => dispatch({ type: "SET_HOST_PACED", hostPaced }),
      [dispatch]
    ),
    setError: useCallback(
      (error: string) => dispatch({ type: "SET_ERROR", error }),
      [dispatch]
    ),
    reset: useCallback(() => dispatch({ type: "RESET" }), [dispatch]),
    resetGame: useCallback(() => dispatch({ type: "RESET_GAME" }), [dispatch]),
  };
}
