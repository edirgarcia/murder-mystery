import { createLobbyApi, request } from "@shared/api/http";
import type {
  AIProjectPriority,
  AIStrategyKind,
  Bundle,
  PrivateState,
  PublicState,
  TCGameInfo,
} from "../types/game";

const BASE = "/trading-city/api/tc/games";

const lobby = createLobbyApi(BASE);
export const createGame = lobby.createGame;
export const joinGame = lobby.joinGame;

export function getGameInfo(code: string): Promise<TCGameInfo> {
  return lobby.getGameInfo<TCGameInfo>(code);
}

export interface StartOptions {
  total_rounds: number;
  auction_seconds: number;
  lot_creation_seconds: number;
  project_turn_seconds: number;
  ai_strategy: AIStrategyKind;
  ai_project_priority: AIProjectPriority;
}

function post<T = unknown>(code: string, path: string, playerId: string, body?: unknown): Promise<T> {
  return request<T>(`${BASE}/${code}/${path}`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify(body ?? {}),
  });
}

export const startGame = (code: string, hostId: string, options: StartOptions) =>
  post(code, "start", hostId, options);

export function getState(
  code: string,
  playerId: string
): Promise<{ public: PublicState; private: PrivateState | null }> {
  return request(`${BASE}/${code}/state`, { headers: { "X-Player-Id": playerId } });
}

export const claimCity = (code: string, playerId: string, slot: number) =>
  post(code, "claim", playerId, { slot });

export const submitLot = (code: string, playerId: string, contents: Bundle) =>
  post(code, "lot", playerId, { contents });

export const placeBid = (code: string, playerId: string, amount: number) =>
  post(code, "bid", playerId, { amount });

export const passAuction = (code: string, playerId: string) => post(code, "auction-pass", playerId);

export const buildProject = (code: string, playerId: string, slotIndex: number) =>
  post(code, "build", playerId, { slot_index: slotIndex });

export const passProject = (code: string, playerId: string) => post(code, "project-pass", playerId);

export const markReady = (code: string, playerId: string) => post(code, "ready", playerId);

export const discard = (code: string, playerId: string, contents: Bundle) =>
  post(code, "discard", playerId, { contents });

export function buildWsUrl(code: string, playerId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${BASE}/${code}/ws?player_id=${playerId}`;
}
