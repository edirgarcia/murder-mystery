import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import type { GamePhase, PlayerInfo } from "@shared/types/game";
import type { ReviewCategory, RoundResult } from "../types/game";

interface BastaState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: PlayerInfo[];
  scores: Record<string, number>;
  categories: string[];
  currentRound: number;
  roundsToPlay: number;
  roundPhase: "answering" | "review" | "reveal" | null;
  currentLetter: string | null;
  reviewCategory: ReviewCategory | null;
  roundEndsAt: string | null;
  submissionsIn: number;
  hasSubmitted: boolean;
  roundResult: RoundResult | null;
  winner: string | null;
  roundSeconds: number;
  hostPaced: boolean;
  error: string | null;
}

type BastaAction =
  | { type: "SET_GAME"; code: string; playerId: string; playerName: string; isHost: boolean }
  | { type: "SET_PHASE"; phase: GamePhase }
  | { type: "SET_PLAYERS"; players: PlayerInfo[] }
  | { type: "ADD_PLAYER"; player: PlayerInfo }
  | { type: "SET_SCORES"; scores: Record<string, number> }
  | {
      type: "NEW_ROUND";
      round: number;
      roundsToPlay: number;
      letter: string;
      categories: string[];
      roundEndsAt: string | null;
      players: PlayerInfo[];
      scores: Record<string, number>;
    }
  | { type: "SET_SUBMITTED" }
  | { type: "SET_SUBMISSIONS"; submissionsIn: number }
  | { type: "SET_ROUND_TIMER"; roundEndsAt: string }
  | { type: "SET_REVIEW_CATEGORY"; reviewCategory: ReviewCategory }
  | { type: "UPDATE_VETO"; category: string; targetPlayerIds: string[]; vetoCount: number }
  | { type: "SET_ROUND_RESULT"; result: RoundResult }
  | { type: "SET_WINNER"; winner: string; scores: Record<string, number> }
  | { type: "SET_CONFIG"; categories: string[]; roundsToPlay: number; roundSeconds: number; hostPaced: boolean }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" }
  | { type: "RESET_GAME" };

const initialState: BastaState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  scores: {},
  categories: [],
  currentRound: 0,
  roundsToPlay: 5,
  roundPhase: null,
  currentLetter: null,
  reviewCategory: null,
  roundEndsAt: null,
  submissionsIn: 0,
  hasSubmitted: false,
  roundResult: null,
  winner: null,
  roundSeconds: 15,
  hostPaced: false,
  error: null,
};

function bastaReducer(state: BastaState, action: BastaAction): BastaState {
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
      if (state.players.some((player) => player.id === action.player.id)) {
        return state;
      }
      return { ...state, players: [...state.players, action.player] };
    case "SET_SCORES":
      return { ...state, scores: action.scores };
    case "NEW_ROUND":
      return {
        ...state,
        phase: "playing",
        currentRound: action.round,
        roundsToPlay: action.roundsToPlay,
        currentLetter: action.letter,
        categories: action.categories,
        roundEndsAt: action.roundEndsAt,
        roundPhase: "answering",
        players: action.players,
        scores: action.scores,
        submissionsIn: 0,
        hasSubmitted: false,
        reviewCategory: null,
        roundResult: null,
        error: null,
      };
    case "SET_SUBMITTED":
      return { ...state, hasSubmitted: true };
    case "SET_SUBMISSIONS":
      return { ...state, submissionsIn: action.submissionsIn };
    case "SET_ROUND_TIMER":
      return { ...state, roundEndsAt: action.roundEndsAt };
    case "SET_REVIEW_CATEGORY":
      return {
        ...state,
        roundPhase: "review",
        roundEndsAt: null,
        reviewCategory: action.reviewCategory,
      };
    case "UPDATE_VETO":
      if (!state.reviewCategory || state.reviewCategory.category !== action.category) {
        return state;
      }
      return {
        ...state,
        reviewCategory: {
          ...state.reviewCategory,
          answers: state.reviewCategory.answers.map((answer) =>
            action.targetPlayerIds.includes(answer.player_id)
              ? { ...answer, veto_count: action.vetoCount }
              : answer
          ),
        },
      };
    case "SET_ROUND_RESULT":
      return {
        ...state,
        roundPhase: "reveal",
        roundEndsAt: null,
        reviewCategory: null,
        roundResult: action.result,
        scores: action.result.scores,
        winner: action.result.winner_name,
      };
    case "SET_WINNER":
      return {
        ...state,
        phase: "finished",
        roundPhase: null,
        winner: action.winner,
        scores: action.scores,
      };
    case "SET_CONFIG":
      return {
        ...state,
        categories: action.categories,
        roundsToPlay: action.roundsToPlay,
        roundSeconds: action.roundSeconds,
        hostPaced: action.hostPaced,
      };
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

const BastaContext = createContext<{
  state: BastaState;
  dispatch: Dispatch<BastaAction>;
} | null>(null);

export function BastaProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(bastaReducer, initialState);
  return (
    <BastaContext.Provider value={{ state, dispatch }}>
      {children}
    </BastaContext.Provider>
  );
}

export function useBasta() {
  const ctx = useContext(BastaContext);
  if (!ctx) throw new Error("useBasta must be used within BastaProvider");
  return ctx;
}

export function useBastaActions() {
  const { dispatch } = useBasta();

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
    newRound: useCallback(
      (
        round: number,
        roundsToPlay: number,
        letter: string,
        categories: string[],
        roundEndsAt: string | null,
        players: PlayerInfo[],
        scores: Record<string, number>
      ) =>
        dispatch({
          type: "NEW_ROUND",
          round,
          roundsToPlay,
          letter,
          categories,
          roundEndsAt,
          players,
          scores,
        }),
      [dispatch]
    ),
    setSubmitted: useCallback(() => dispatch({ type: "SET_SUBMITTED" }), [dispatch]),
    setSubmissions: useCallback(
      (submissionsIn: number) => dispatch({ type: "SET_SUBMISSIONS", submissionsIn }),
      [dispatch]
    ),
    setRoundTimer: useCallback(
      (roundEndsAt: string) => dispatch({ type: "SET_ROUND_TIMER", roundEndsAt }),
      [dispatch]
    ),
    setReviewCategory: useCallback(
      (reviewCategory: ReviewCategory) =>
        dispatch({ type: "SET_REVIEW_CATEGORY", reviewCategory }),
      [dispatch]
    ),
    updateVeto: useCallback(
      (category: string, targetPlayerIds: string[], vetoCount: number) =>
        dispatch({ type: "UPDATE_VETO", category, targetPlayerIds, vetoCount }),
      [dispatch]
    ),
    setRoundResult: useCallback(
      (result: RoundResult) => dispatch({ type: "SET_ROUND_RESULT", result }),
      [dispatch]
    ),
    setWinner: useCallback(
      (winner: string, scores: Record<string, number>) =>
        dispatch({ type: "SET_WINNER", winner, scores }),
      [dispatch]
    ),
    setConfig: useCallback(
      (categories: string[], roundsToPlay: number, roundSeconds: number, hostPaced: boolean) =>
        dispatch({ type: "SET_CONFIG", categories, roundsToPlay, roundSeconds, hostPaced }),
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
