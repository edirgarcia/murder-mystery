import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import type { GamePhase } from "@shared/types/game";
import type {
  AccusationResult,
  GameOverData,
  PDGameInfo,
  PDPlayerInfo,
  PDPrivateState,
  RoundResult,
  TeamColor,
  Winner,
} from "../types/game";

interface PDState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: PDPlayerInfo[];
  privateState: PDPrivateState | null;
  teamScores: Record<TeamColor, number>;
  currentRound: number;
  totalRounds: number;
  roundPhase: "voting" | "accusation" | "reveal" | null;
  votingEndsAt: string | null;
  accusationEndsAt: string | null;
  revealEndsAt: string | null;
  revealType: "round" | "accusation" | null;
  hasVoted: boolean;
  hasAccused: boolean;
  latestRoundResult: RoundResult | null;
  latestAccusationResult: AccusationResult | null;
  winner: Winner | null;
  finalSpies: GameOverData["spies"] | null;
  error: string | null;
}

type PDAction =
  | { type: "SET_GAME"; code: string; playerId: string; playerName: string; isHost: boolean }
  | { type: "SET_PHASE"; phase: GamePhase }
  | { type: "SET_PLAYERS"; players: PDPlayerInfo[] }
  | { type: "ADD_PLAYER"; player: PDPlayerInfo }
  | { type: "SET_PRIVATE_STATE"; privateState: PDPrivateState }
  | { type: "SET_TEAM_SCORES"; teamScores: Record<TeamColor, number> }
  | { type: "ROUND_STARTED"; round: number; totalRounds: number; votingEndsAt: string | null; players: PDPlayerInfo[]; teamScores: Record<TeamColor, number> }
  | { type: "SET_VOTED" }
  | { type: "ACCUSATION_STARTED"; accusationEndsAt: string | null; players: PDPlayerInfo[] }
  | { type: "SET_ACCUSED" }
  | { type: "SET_ROUND_RESULT"; result: RoundResult }
  | { type: "SET_ACCUSATION_RESULT"; result: AccusationResult }
  | { type: "SET_WINNER"; data: GameOverData }
  | { type: "SYNC_GAME_INFO"; info: PDGameInfo }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" };

const initialState: PDState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  privateState: null,
  teamScores: { red: 0, blue: 0 },
  currentRound: 0,
  totalRounds: 10,
  roundPhase: null,
  votingEndsAt: null,
  accusationEndsAt: null,
  revealEndsAt: null,
  revealType: null,
  hasVoted: false,
  hasAccused: false,
  latestRoundResult: null,
  latestAccusationResult: null,
  winner: null,
  finalSpies: null,
  error: null,
};

function reducer(state: PDState, action: PDAction): PDState {
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
      if (state.players.some((player) => player.id === action.player.id)) return state;
      return { ...state, players: [...state.players, action.player] };
    case "SET_PRIVATE_STATE":
      return { ...state, privateState: action.privateState };
    case "SET_TEAM_SCORES":
      return { ...state, teamScores: action.teamScores };
    case "ROUND_STARTED":
      return {
        ...state,
        currentRound: action.round,
        totalRounds: action.totalRounds,
        roundPhase: "voting",
        votingEndsAt: action.votingEndsAt,
        accusationEndsAt: null,
        revealEndsAt: null,
        revealType: null,
        players: action.players,
        teamScores: action.teamScores,
        hasVoted: false,
        hasAccused: false,
        latestRoundResult: null,
        latestAccusationResult: null,
      };
    case "SET_VOTED":
      return { ...state, hasVoted: true };
    case "ACCUSATION_STARTED":
      return {
        ...state,
        roundPhase: "accusation",
        accusationEndsAt: action.accusationEndsAt,
        votingEndsAt: null,
        revealEndsAt: null,
        revealType: null,
        players: action.players,
        hasAccused: false,
      };
    case "SET_ACCUSED":
      return { ...state, hasAccused: true };
    case "SET_ROUND_RESULT":
      return {
        ...state,
        roundPhase: "reveal",
        votingEndsAt: null,
        revealEndsAt: action.result.reveal_ends_at ?? null,
        revealType: "round",
        latestRoundResult: action.result,
        teamScores: action.result.team_scores,
      };
    case "SET_ACCUSATION_RESULT":
      return {
        ...state,
        roundPhase: "reveal",
        accusationEndsAt: null,
        revealEndsAt: action.result.reveal_ends_at ?? null,
        revealType: "accusation",
        latestAccusationResult: action.result,
        teamScores: action.result.team_scores,
        players: action.result.players,
      };
    case "SET_WINNER":
      return {
        ...state,
        phase: "finished",
        winner: action.data.winner,
        teamScores: action.data.team_scores,
        players: action.data.players,
        finalSpies: action.data.spies,
        roundPhase: null,
      };
    case "SYNC_GAME_INFO":
      return {
        ...state,
        phase: action.info.phase,
        players: action.info.players,
        teamScores: action.info.team_scores,
        currentRound: action.info.current_round,
        totalRounds: action.info.total_rounds,
        roundPhase: action.info.round_phase as PDState["roundPhase"],
        votingEndsAt: action.info.voting_ends_at ?? null,
        accusationEndsAt: action.info.accusation_ends_at ?? null,
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

const PDContext = createContext<{ state: PDState; dispatch: Dispatch<PDAction> } | null>(null);

export function PDProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return <PDContext.Provider value={{ state, dispatch }}>{children}</PDContext.Provider>;
}

export function usePD() {
  const ctx = useContext(PDContext);
  if (!ctx) throw new Error("usePD must be used within PDProvider");
  return ctx;
}

export function usePDActions() {
  const { dispatch } = usePD();

  return {
    setGame: useCallback(
      (code: string, playerId: string, playerName: string, isHost: boolean) =>
        dispatch({ type: "SET_GAME", code, playerId, playerName, isHost }),
      [dispatch]
    ),
    setPhase: useCallback((phase: GamePhase) => dispatch({ type: "SET_PHASE", phase }), [dispatch]),
    setPlayers: useCallback((players: PDPlayerInfo[]) => dispatch({ type: "SET_PLAYERS", players }), [dispatch]),
    addPlayer: useCallback((player: PDPlayerInfo) => dispatch({ type: "ADD_PLAYER", player }), [dispatch]),
    setPrivateState: useCallback(
      (privateState: PDPrivateState) => dispatch({ type: "SET_PRIVATE_STATE", privateState }),
      [dispatch]
    ),
    setTeamScores: useCallback(
      (teamScores: Record<TeamColor, number>) => dispatch({ type: "SET_TEAM_SCORES", teamScores }),
      [dispatch]
    ),
    roundStarted: useCallback(
      (round: number, totalRounds: number, votingEndsAt: string | null, players: PDPlayerInfo[], teamScores: Record<TeamColor, number>) =>
        dispatch({ type: "ROUND_STARTED", round, totalRounds, votingEndsAt, players, teamScores }),
      [dispatch]
    ),
    setVoted: useCallback(() => dispatch({ type: "SET_VOTED" }), [dispatch]),
    accusationStarted: useCallback(
      (accusationEndsAt: string | null, players: PDPlayerInfo[]) =>
        dispatch({ type: "ACCUSATION_STARTED", accusationEndsAt, players }),
      [dispatch]
    ),
    setAccused: useCallback(() => dispatch({ type: "SET_ACCUSED" }), [dispatch]),
    setRoundResult: useCallback((result: RoundResult) => dispatch({ type: "SET_ROUND_RESULT", result }), [dispatch]),
    setAccusationResult: useCallback(
      (result: AccusationResult) => dispatch({ type: "SET_ACCUSATION_RESULT", result }),
      [dispatch]
    ),
    setWinner: useCallback((data: GameOverData) => dispatch({ type: "SET_WINNER", data }), [dispatch]),
    syncGameInfo: useCallback((info: PDGameInfo) => dispatch({ type: "SYNC_GAME_INFO", info }), [dispatch]),
    setError: useCallback((error: string) => dispatch({ type: "SET_ERROR", error }), [dispatch]),
    clearError: useCallback(() => dispatch({ type: "CLEAR_ERROR" }), [dispatch]),
  };
}
