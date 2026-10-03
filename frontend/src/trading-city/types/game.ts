import type { GamePhase, PlayerInfo } from "@shared/types/game";

export type { GamePhase, PlayerInfo, WSEvent } from "@shared/types/game";

export const RESOURCES = [
  "grain",
  "livestock",
  "timber",
  "iron",
  "cloth",
  "tools",
  "wine",
  "spices",
] as const;

export type Resource = (typeof RESOURCES)[number];
export type Bundle = Partial<Record<Resource, number>>;

export type RoundPhase =
  | "city_selection"
  | "production"
  | "market_study"
  | "lot_creation"
  | "auction"
  | "projects"
  | "upkeep"
  | "cleanup"
  | "finished";

export type AIStrategyKind = "heuristic" | "passive";
export type AIProjectPriority = "rotating" | "after_humans";

export type ProjectCategory = "city" | "market" | "prestige";
export type MarketLevel = "down" | "neutral" | "up";

export interface ProjectCard {
  id: string;
  name: string;
  category: ProjectCategory;
  cost: Bundle;
  effect: string;
  effect_kind: string;
  vp: number;
  tier: string | null;
  cash_cost: number;
}

export interface BuiltProject extends ProjectCard {
  round_built: number;
}

export interface BuiltMarketProject extends BuiltProject {
  // False once another card replaced this effect on the global board.
  active: boolean;
}

export interface CityView {
  slot: number;
  profile: string;
  name: string;
  city_name: string;
  ai_city_name: string;
  owner_id: string | null;
  owner_name: string | null;
  is_ai: boolean;
  primary_resource: Resource;
  base_production: Bundle;
  base_upkeep: Bundle;
  production: Bundle;
  upkeep: Bundle;
  income: number;
  storage: number | null;
  cash: number;
  shortage: number;
  vp: number;
  score: number;
  projects: BuiltProject[];
  market_projects: BuiltMarketProject[];
}

export interface BidView {
  bidder: number;
  amount: number;
}

export interface AuctionView {
  lot_id: number;
  number: number;
  total: number;
  seller: number;
  contents: Bundle;
  high_bid: number | null;
  high_bidder: number | null;
  min_next_bid: number;
  ends_at: string;
  bids: BidView[];
  passed: number[];
}

export interface AuctionRecord {
  round: number;
  lot_id: number;
  seller: number;
  contents: Bundle;
  winner: number | null;
  price: number | null;
  bids: BidView[];
}

export interface MarketAxisView {
  level: MarketLevel;
  pending_level: MarketLevel;
  card_name: string | null;
  built_by: number | null;
}

export interface ProjectSlotView {
  index: number;
  category: ProjectCategory;
  card: ProjectCard | null;
}

export interface ProjectEvent {
  round: number;
  city: number;
  card: ProjectCard;
  displaced: string | null;
}

export interface PublicState {
  phase: RoundPhase;
  round: number;
  total_rounds: number;
  deadline: string | null;
  server_time: string;
  // Slots that tapped Continue on a summary screen; null when not on one.
  ready: number[] | null;
  cities: CityView[];
  priority: { slot: number; player_id: string | null; name: string; is_ai: boolean }[];
  project_turn_slot: number | null;
  project_turn_player: string | null;
  // Keyed by city slot: built card id, or null for a pass.
  project_actions: Record<string, string | null>;
  project_slots: ProjectSlotView[];
  prestige_tier: string;
  market: Record<Resource, { supply: MarketAxisView; demand: MarketAxisView }>;
  lots_ready: number[];
  auction: AuctionView | null;
  history: AuctionRecord[];
  project_log: ProjectEvent[];
  last_production: Record<string, Bundle>;
  last_upkeep: Record<string, { missing: number; shortage_before: number; shortage_after: number }>;
  discards_pending: number;
  standings: { slot: number; owner_name: string; score: number; vp: number; cash: number }[];
  rules: {
    min_bid: number;
    min_increment: number;
    auction_seconds: number;
    anti_snipe_window_seconds: number;
    anti_snipe_extension_seconds: number;
    cash_per_vp: number | null;
    upkeep_effect_timing: string;
    ai_strategy: AIStrategyKind;
    ai_project_priority: AIProjectPriority;
  };
}

export interface PrivateState {
  player_id: string;
  slot: number | null;
  inventory: Bundle;
  lot_submitted: boolean;
  lot: Bundle | null;
  affordable_projects: number[];
  discard_required: number;
  next_production: Bundle;
  next_upkeep: Bundle;
  last_upkeep: { required: Bundle; paid: Bundle; missing: number; shortage_after: number } | null;
  last_discards: Bundle;
}

export interface TCGameInfo {
  code: string;
  phase: GamePhase;
  players: PlayerInfo[];
  min_players: number;
  max_players: number;
  host_name: string;
  state: PublicState | null;
}
