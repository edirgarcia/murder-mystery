export type { GamePhase, PlayerInfo, WSEvent } from "@shared/types/game";

export interface CategoryResult {
  category: string;
  answers: Record<string, string>;
  points: Record<string, number>;
  invalid_players: string[];
  vetoed_players: string[];
}

export interface ReviewAnswer {
  player_id: string;
  player_name: string;
  answer: string;
  veto_count: number;
}

export interface ReviewCategory {
  round: number;
  letter: string | null;
  category_index: number;
  category_count: number;
  category: string;
  review_seconds: number;
  vetoes_required: number;
  answers: ReviewAnswer[];
}

export interface RoundResult {
  letter: string;
  categories: string[];
  category_results: CategoryResult[];
  round_points: Record<string, number>;
  scores: Record<string, number>;
  winner_name: string | null;
}

export interface BastaGameInfo {
  code: string;
  phase: import("@shared/types/game").GamePhase;
  players: import("@shared/types/game").PlayerInfo[];
  min_players: number;
  max_players: number;
  host_name: string;
  scores: Record<string, number>;
  current_round: number;
  round_phase: "answering" | "review" | "reveal" | null;
  categories: string[];
  current_letter: string | null;
  current_review_category: string | null;
  current_review_index: number | null;
  current_review_answers: ReviewAnswer[];
  review_seconds: number;
  vetoes_required: number;
  round_ends_at: string | null;
  submissions_in: number;
  winner: string | null;
  rounds_to_play: number;
  round_seconds: number;
  host_paced: boolean;
  last_round_result: RoundResult | null;
}

export interface PlayerScoreEntry {
  player_id: string;
  player_name: string;
  score: number;
}
