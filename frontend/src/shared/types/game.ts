export type GamePhase = "lobby" | "generating" | "playing" | "finished";

export interface PlayerInfo {
  id: string;
  name: string;
}

export interface WSEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface BaseGameInfo {
  code: string;
  phase: GamePhase;
  players: PlayerInfo[];
  min_players: number;
  max_players: number;
  host_name: string;
}
