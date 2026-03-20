import type { BaseGameInfo } from "@shared/types/game";

export type Role = "villager" | "werewolf" | "seer" | "witch" | "hunter" | "cupid";

export type NightSubPhase = "cupid" | "werewolves" | "seer" | "witch";

export type DaySubPhase = "announcement" | "discussion" | "voting" | "vote_result" | "hunter_revenge";

export type WinCondition = "villagers" | "werewolves" | "lovers";

export interface WWPlayerInfo {
  id: string;
  name: string;
  alive: boolean;
}

export interface WWGameInfo extends BaseGameInfo {
  players: WWPlayerInfo[];
  night_number: number;
  day_number: number;
  night_sub_phase: NightSubPhase | null;
  day_sub_phase: DaySubPhase | null;
  alive_count: number;
  winner: WinCondition | null;
  phase_ends_at: string | null;
  discussion_seconds: number;
}

export interface WWPrivateState {
  code: string;
  phase: "lobby" | "playing" | "finished";
  night_number: number;
  day_number: number;
  night_sub_phase: NightSubPhase | null;
  day_sub_phase: DaySubPhase | null;
  phase_ends_at: string | null;
  players: WWPlayerInfo[];
  winner: WinCondition | null;
  last_deaths: string[];
  me?: {
    id: string;
    name: string;
    role: Role;
    alive: boolean;
    lover_id: string | null;
  };
  roles?: Record<string, Role>;
}
