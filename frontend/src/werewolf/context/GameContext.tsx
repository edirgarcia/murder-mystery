import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import type { GamePhase } from "@shared/types/game";
import type { DaySubPhase, NightSubPhase, Role, WitchPrompt, WolfPackMember, WWPlayerInfo, WinCondition } from "../types/game";

interface WWState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: WWPlayerInfo[];
  role: Role | null;
  alive: boolean;
  loverId: string | null;
  nightSubPhase: NightSubPhase | null;
  daySubPhase: DaySubPhase | null;
  nightNumber: number;
  dayNumber: number;
  phaseEndsAt: string | null;
  winner: WinCondition | null;
  rolesReveal: Record<string, Role>;
  lastDeaths: string[];
  hasSubmittedAction: boolean;
  hasVoted: boolean;
  seerResult: { targetName: string; isWerewolf: boolean } | null;
  witchPrompt: WitchPrompt | null;
  alphaWolfId: string | null;
  packMembers: WolfPackMember[];
  wolfPreselections: Record<string, string>;
  error: string | null;
}

type WWAction =
  | { type: "SET_GAME"; code: string; playerId: string; playerName: string; isHost: boolean }
  | { type: "SET_PHASE"; phase: GamePhase }
  | { type: "SET_PLAYERS"; players: WWPlayerInfo[] }
  | { type: "ADD_PLAYER"; player: WWPlayerInfo }
  | { type: "SET_PRIVATE"; role: Role; alive: boolean; loverId: string | null }
  | { type: "SET_PHASE_DETAIL"; nightSubPhase: NightSubPhase | null; daySubPhase: DaySubPhase | null; nightNumber: number; dayNumber: number; phaseEndsAt: string | null }
  | { type: "SET_WINNER"; winner: WinCondition; roles: Record<string, Role> }
  | { type: "SET_LAST_DEATHS"; lastDeaths: string[] }
  | { type: "SET_SEER_RESULT"; targetName: string; isWerewolf: boolean }
  | { type: "SET_WITCH_PROMPT"; prompt: WitchPrompt }
  | { type: "CLEAR_WITCH_PROMPT" }
  | { type: "SET_WOLF_PACK"; alphaWolfId: string; pack: WolfPackMember[] }
  | { type: "SET_WOLF_PRESELECTION"; wolfId: string; targetId: string }
  | { type: "CLEAR_WOLF_PRESELECTIONS" }
  | { type: "SET_ACTION_SUBMITTED"; value: boolean }
  | { type: "SET_HAS_VOTED"; value: boolean }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" };

const initialState: WWState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  role: null,
  alive: true,
  loverId: null,
  nightSubPhase: null,
  daySubPhase: null,
  nightNumber: 0,
  dayNumber: 0,
  phaseEndsAt: null,
  winner: null,
  rolesReveal: {},
  lastDeaths: [],
  hasSubmittedAction: false,
  hasVoted: false,
  seerResult: null,
  witchPrompt: null,
  alphaWolfId: null,
  packMembers: [],
  wolfPreselections: {},
  error: null,
};

function reducer(state: WWState, action: WWAction): WWState {
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
      if (state.players.some((p) => p.id === action.player.id)) return state;
      return { ...state, players: [...state.players, action.player] };
    case "SET_PRIVATE":
      return { ...state, role: action.role, alive: action.alive, loverId: action.loverId };
    case "SET_PHASE_DETAIL": {
      const isVoting = action.daySubPhase === "voting";
      return {
        ...state,
        nightSubPhase: action.nightSubPhase,
        daySubPhase: action.daySubPhase,
        nightNumber: action.nightNumber,
        dayNumber: action.dayNumber,
        phaseEndsAt: action.phaseEndsAt,
        hasSubmittedAction: action.nightSubPhase ? false : state.hasSubmittedAction,
        hasVoted: isVoting ? false : state.hasVoted,
        witchPrompt: action.nightSubPhase !== "witch" ? null : state.witchPrompt,
        wolfPreselections: action.nightSubPhase === "werewolves" ? {} : state.wolfPreselections,
      };
    }
    case "SET_WINNER":
      return {
        ...state,
        phase: "finished",
        winner: action.winner,
        rolesReveal: action.roles,
      };
    case "SET_LAST_DEATHS":
      return { ...state, lastDeaths: action.lastDeaths };
    case "SET_SEER_RESULT":
      return {
        ...state,
        seerResult: { targetName: action.targetName, isWerewolf: action.isWerewolf },
      };
    case "SET_WITCH_PROMPT":
      return { ...state, witchPrompt: action.prompt };
    case "CLEAR_WITCH_PROMPT":
      return { ...state, witchPrompt: null };
    case "SET_WOLF_PACK":
      return { ...state, alphaWolfId: action.alphaWolfId, packMembers: action.pack };
    case "SET_WOLF_PRESELECTION":
      return { ...state, wolfPreselections: { ...state.wolfPreselections, [action.wolfId]: action.targetId } };
    case "CLEAR_WOLF_PRESELECTIONS":
      return { ...state, wolfPreselections: {} };
    case "SET_ACTION_SUBMITTED":
      return { ...state, hasSubmittedAction: action.value };
    case "SET_HAS_VOTED":
      return { ...state, hasVoted: action.value };
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

const WWContext = createContext<{ state: WWState; dispatch: Dispatch<WWAction> } | null>(null);

export function WWProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return <WWContext.Provider value={{ state, dispatch }}>{children}</WWContext.Provider>;
}

export function useWW() {
  const ctx = useContext(WWContext);
  if (!ctx) throw new Error("useWW must be used within WWProvider");
  return ctx;
}

export function useWWActions() {
  const { dispatch } = useWW();

  return {
    setGame: useCallback(
      (code: string, playerId: string, playerName: string, isHost: boolean) =>
        dispatch({ type: "SET_GAME", code, playerId, playerName, isHost }),
      [dispatch]
    ),
    setPhase: useCallback((phase: GamePhase) => dispatch({ type: "SET_PHASE", phase }), [dispatch]),
    setPlayers: useCallback((players: WWPlayerInfo[]) => dispatch({ type: "SET_PLAYERS", players }), [dispatch]),
    addPlayer: useCallback((player: WWPlayerInfo) => dispatch({ type: "ADD_PLAYER", player }), [dispatch]),
    setPrivate: useCallback(
      (role: Role, alive: boolean, loverId: string | null) => dispatch({ type: "SET_PRIVATE", role, alive, loverId }),
      [dispatch]
    ),
    setPhaseDetail: useCallback(
      (nightSubPhase: NightSubPhase | null, daySubPhase: DaySubPhase | null, nightNumber: number, dayNumber: number, phaseEndsAt: string | null) =>
        dispatch({ type: "SET_PHASE_DETAIL", nightSubPhase, daySubPhase, nightNumber, dayNumber, phaseEndsAt }),
      [dispatch]
    ),
    setWinner: useCallback(
      (winner: WinCondition, roles: Record<string, Role>) => dispatch({ type: "SET_WINNER", winner, roles }),
      [dispatch]
    ),
    setLastDeaths: useCallback((lastDeaths: string[]) => dispatch({ type: "SET_LAST_DEATHS", lastDeaths }), [dispatch]),
    setSeerResult: useCallback(
      (targetName: string, isWerewolf: boolean) => dispatch({ type: "SET_SEER_RESULT", targetName, isWerewolf }),
      [dispatch]
    ),
    setWitchPrompt: useCallback(
      (prompt: WitchPrompt) => dispatch({ type: "SET_WITCH_PROMPT", prompt }),
      [dispatch]
    ),
    clearWitchPrompt: useCallback(() => dispatch({ type: "CLEAR_WITCH_PROMPT" }), [dispatch]),
    setWolfPack: useCallback(
      (alphaWolfId: string, pack: WolfPackMember[]) => dispatch({ type: "SET_WOLF_PACK", alphaWolfId, pack }),
      [dispatch]
    ),
    setWolfPreselection: useCallback(
      (wolfId: string, targetId: string) => dispatch({ type: "SET_WOLF_PRESELECTION", wolfId, targetId }),
      [dispatch]
    ),
    clearWolfPreselections: useCallback(() => dispatch({ type: "CLEAR_WOLF_PRESELECTIONS" }), [dispatch]),
    setActionSubmitted: useCallback((value: boolean) => dispatch({ type: "SET_ACTION_SUBMITTED", value }), [dispatch]),
    setHasVoted: useCallback((value: boolean) => dispatch({ type: "SET_HAS_VOTED", value }), [dispatch]),
    setError: useCallback((error: string) => dispatch({ type: "SET_ERROR", error }), [dispatch]),
    clearError: useCallback(() => dispatch({ type: "CLEAR_ERROR" }), [dispatch]),
  };
}
