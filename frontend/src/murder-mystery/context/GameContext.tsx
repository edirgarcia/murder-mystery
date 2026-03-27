import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
  type Dispatch,
} from "react";
import type { GamePhase, PlayerInfo } from "@shared/types/game";
import type { PlayerCard, LeaderboardEntry } from "../types/game";

interface GameState {
  code: string | null;
  playerId: string | null;
  playerName: string | null;
  isHost: boolean;
  phase: GamePhase | null;
  players: PlayerInfo[];
  characterNames: string[];
  murderWeapon: string | null;
  card: PlayerCard | null;
  hasGuessed: boolean;
  guessedAt: string | null;
  leaderboard: LeaderboardEntry[] | null;
  currentRound: number;
  roundDurations: number[];
  roundStartedAt: string | null;
  startedAt: string | null;
  error: string | null;
}

type GameAction =
  | { type: "SET_GAME"; code: string; playerId: string; playerName: string; isHost: boolean }
  | { type: "SET_PHASE"; phase: GamePhase }
  | { type: "SET_PLAYERS"; players: PlayerInfo[] }
  | { type: "ADD_PLAYER"; player: PlayerInfo }
  | { type: "REMOVE_PLAYER"; playerId: string }
  | { type: "SET_CHARACTER_NAMES"; names: string[] }
  | { type: "SET_MURDER_WEAPON"; weapon: string | null }
  | { type: "SET_CARD"; card: PlayerCard }
  | { type: "SET_HAS_GUESSED"; guessedAt: string }
  | { type: "SET_LEADERBOARD"; leaderboard: LeaderboardEntry[] }
  | { type: "SET_ROUND_INFO"; round: number; startedAt: string; durationSeconds: number }
  | { type: "SET_ROUND_DURATIONS"; roundDurations: number[] }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" }
  | { type: "RESET_GAME" };

const initialState: GameState = {
  code: null,
  playerId: null,
  playerName: null,
  isHost: false,
  phase: null,
  players: [],
  characterNames: [],
  murderWeapon: null,
  card: null,
  hasGuessed: false,
  guessedAt: null,
  leaderboard: null,
  currentRound: 0,
  roundDurations: [],
  roundStartedAt: null,
  startedAt: null,
  error: null,
};

function gameReducer(state: GameState, action: GameAction): GameState {
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
    case "SET_CHARACTER_NAMES":
      return { ...state, characterNames: action.names };
    case "SET_MURDER_WEAPON":
      return { ...state, murderWeapon: action.weapon };
    case "SET_CARD":
      return { ...state, card: action.card };
    case "SET_HAS_GUESSED":
      return { ...state, hasGuessed: true, guessedAt: action.guessedAt };
    case "SET_LEADERBOARD":
      return { ...state, leaderboard: action.leaderboard };
    case "SET_ROUND_INFO": {
      const newState: Partial<GameState> = {
        currentRound: action.round,
        roundStartedAt: action.startedAt,
      };
      // Set startedAt on first round (overall game start for scoring)
      if (action.round === 1 && !state.startedAt) {
        newState.startedAt = action.startedAt;
      }
      return { ...state, ...newState };
    }
    case "SET_ROUND_DURATIONS":
      return { ...state, roundDurations: action.roundDurations };
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

const GameContext = createContext<{
  state: GameState;
  dispatch: Dispatch<GameAction>;
} | null>(null);

export function GameProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(gameReducer, initialState);
  return (
    <GameContext.Provider value={{ state, dispatch }}>
      {children}
    </GameContext.Provider>
  );
}

export function useGame() {
  const ctx = useContext(GameContext);
  if (!ctx) throw new Error("useGame must be used within GameProvider");
  return ctx;
}

export function useGameActions() {
  const { dispatch } = useGame();

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

  const setCharacterNames = useCallback(
    (names: string[]) => dispatch({ type: "SET_CHARACTER_NAMES", names }),
    [dispatch]
  );

  const setMurderWeapon = useCallback(
    (weapon: string | null) => dispatch({ type: "SET_MURDER_WEAPON", weapon }),
    [dispatch]
  );

  const setCard = useCallback(
    (card: PlayerCard) => dispatch({ type: "SET_CARD", card }),
    [dispatch]
  );

  const setHasGuessed = useCallback(
    (guessedAt: string) => dispatch({ type: "SET_HAS_GUESSED", guessedAt }),
    [dispatch]
  );

  const setLeaderboard = useCallback(
    (leaderboard: LeaderboardEntry[]) =>
      dispatch({ type: "SET_LEADERBOARD", leaderboard }),
    [dispatch]
  );

  const setRoundInfo = useCallback(
    (round: number, startedAt: string, durationSeconds: number) =>
      dispatch({ type: "SET_ROUND_INFO", round, startedAt, durationSeconds }),
    [dispatch]
  );

  const setRoundDurations = useCallback(
    (roundDurations: number[]) =>
      dispatch({ type: "SET_ROUND_DURATIONS", roundDurations }),
    [dispatch]
  );

  const setError = useCallback(
    (error: string) => dispatch({ type: "SET_ERROR", error }),
    [dispatch]
  );

  const reset = useCallback(() => dispatch({ type: "RESET" }), [dispatch]);

  const resetGameState = useCallback(() => dispatch({ type: "RESET_GAME" }), [dispatch]);

  return {
    setGame,
    setPhase,
    setPlayers,
    addPlayer,
    setCharacterNames,
    setMurderWeapon,
    setCard,
    setHasGuessed,
    setLeaderboard,
    setRoundInfo,
    setRoundDurations,
    setError,
    reset,
    resetGameState,
  };
}
