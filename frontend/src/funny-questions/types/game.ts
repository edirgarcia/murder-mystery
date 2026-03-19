export type { GamePhase, PlayerInfo, WSEvent } from "@shared/types/game";

export interface FQGameInfo {
  code: string;
  phase: import("@shared/types/game").GamePhase;
  players: import("@shared/types/game").PlayerInfo[];
  min_players: number;
  max_players: number;
  host_name: string;
  scores: Record<string, number>;
  current_round: number;
  round_phase: "voting" | "reveal" | null;
  current_question: string | null;
  shame_holder: string | null;
  voting_ends_at: string | null;
  winner: string | null;
  points_to_win: number;
}

export interface PlayerScoreEntry {
  player_id: string;
  player_name: string;
  score: number;
  has_shame: boolean;
}

export interface RoundResult {
  question: string;
  most_voted: string | null;
  most_voted_name: string | null;
  vote_breakdown: Record<string, string[]>;
  point_deltas: Record<string, number>;
  scores: Record<string, number>;
  shame_holder_name: string | null;
  shame_cleared_name: string | null;
  winner_name: string | null;
}
