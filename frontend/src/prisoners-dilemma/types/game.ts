export type { GamePhase, WSEvent } from "@shared/types/game";

export type TeamColor = "red" | "blue";
export type Decision = "trust" | "betray";
export type Winner = TeamColor | "draw";

export interface PDPlayerInfo {
  id: string;
  name: string;
  team: TeamColor | null;
  spy_exposed: boolean;
}

export interface PDGameInfo {
  code: string;
  phase: import("@shared/types/game").GamePhase;
  players: PDPlayerInfo[];
  min_players: number;
  max_players: number;
  host_name: string;
  current_round: number;
  total_rounds: number;
  round_phase: "voting" | "accusation" | "reveal" | null;
  voting_ends_at: string | null;
  accusation_ends_at: string | null;
  team_scores: Record<TeamColor, number>;
  winner: Winner | null;
}

export interface PDPrivateState {
  player_id: string;
  player_name: string;
  team: TeamColor;
  is_spy: boolean;
  spy_active: boolean;
  sabotage_charges: number;
}

export interface RoundTeamResult {
  team: TeamColor;
  majority_choice: Decision;
  final_choice: Decision;
  tampered: boolean;
  trust_votes: number;
  betray_votes: number;
  submitted_votes: number;
  team_size: number;
  score_delta: number;
  total_score: number;
}

export interface RoundResult {
  round: number;
  multiplier: number;
  teams: Record<TeamColor, RoundTeamResult>;
  team_scores: Record<TeamColor, number>;
}

export interface TeamAccusationResult {
  accusation_triggered: boolean;
  accused_player_id: string | null;
  accused_player_name: string | null;
  correct: boolean | null;
  score_delta: number;
  spy_neutralized: boolean;
  total_score: number;
}

export interface AccusationResult {
  round: number;
  teams: Record<TeamColor, TeamAccusationResult>;
  team_scores: Record<TeamColor, number>;
  players: PDPlayerInfo[];
}

export interface GameOverData {
  winner: Winner;
  team_scores: Record<TeamColor, number>;
  players: PDPlayerInfo[];
  spies: Record<TeamColor, { player_id: string; player_name: string; exposed: boolean }>;
}
