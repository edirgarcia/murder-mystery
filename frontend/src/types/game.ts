export type GamePhase = "lobby" | "generating" | "playing" | "finished";

export interface PlayerInfo {
  id: string;
  name: string;
}

export type Difficulty = "easy" | "medium" | "hard" | "harder" | "hardest";

export interface GameInfo {
  code: string;
  phase: GamePhase;
  players: PlayerInfo[];
  min_players: number;
  max_players: number;
  character_names: string[];
  murder_weapon: string | null;
  difficulty: Difficulty | null;
  host_name: string;
  timer_duration_seconds: number | null;
  started_at: string | null;
  guesses_count: number;
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
  status: string;
  guessed_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  player_name: string;
  suspect_guessed: string;
  correct: boolean;
  time_taken_seconds: number | null;
}

export interface ResultsResponse {
  murderer_name: string;
  murder_weapon: string;
  leaderboard: LeaderboardEntry[];
  murder_clues: ClueInfo[];
}

export interface WSEvent {
  event: string;
  data: Record<string, unknown>;
}
