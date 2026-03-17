export type GamePhase = "lobby" | "generating" | "playing" | "finished";

export interface PlayerInfo {
  id: string;
  name: string;
  is_host: boolean;
}

export interface GameInfo {
  code: string;
  phase: GamePhase;
  players: PlayerInfo[];
  min_players: number;
  max_players: number;
  character_names: string[];
  murder_weapon: string | null;
}

export interface ClueInfo {
  type: string;
  text: string;
}

export interface PlayerCard {
  character_name: string;
  clues: ClueInfo[];
}

export interface GuessResponse {
  correct: boolean;
  suspect_name: string;
  actual_murderer: string | null;
}

export interface SolutionResponse {
  murderer_name: string;
  murder_weapon: string;
  solution: Record<string, string[]>;
  murder_clues: ClueInfo[];
}

export interface WSEvent {
  event: string;
  data: Record<string, unknown>;
}
