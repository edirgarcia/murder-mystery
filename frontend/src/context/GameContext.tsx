import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
  type Dispatch,
} from "react";
import type { GamePhase, PlayerInfo, PlayerCard, ClueInfo } from "../types/game";

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
  guessResult: { correct: boolean; suspect: string; murderer?: string } | null;
  solution: {
    murderer_name: string;
    murder_weapon: string;
    solution: Record<string, string[]>;
    murder_clues: ClueInfo[];
  } | null;
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
  | { type: "SET_GUESS_RESULT"; result: GameState["guessResult"] }
  | { type: "SET_SOLUTION"; solution: GameState["solution"] }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" };

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
  guessResult: null,
  solution: null,
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
    case "SET_GUESS_RESULT":
      return { ...state, guessResult: action.result };
    case "SET_SOLUTION":
      return { ...state, solution: action.solution };
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

  const setGuessResult = useCallback(
    (result: GameState["guessResult"]) =>
      dispatch({ type: "SET_GUESS_RESULT", result }),
    [dispatch]
  );

  const setSolution = useCallback(
    (solution: GameState["solution"]) =>
      dispatch({ type: "SET_SOLUTION", solution }),
    [dispatch]
  );

  const setError = useCallback(
    (error: string) => dispatch({ type: "SET_ERROR", error }),
    [dispatch]
  );

  const reset = useCallback(() => dispatch({ type: "RESET" }), [dispatch]);

  return {
    setGame,
    setPhase,
    setPlayers,
    addPlayer,
    setCharacterNames,
    setMurderWeapon,
    setCard,
    setGuessResult,
    setSolution,
    setError,
    reset,
  };
}
