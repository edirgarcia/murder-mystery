import { createLobbyApi, request } from "@shared/api/http";
import type {
  AccusationResult,
  GameOverData,
  PDGameInfo,
  PDPrivateState,
  RoundResult,
} from "../types/game";

const BASE = "/prisoners-dilemma/api/pd/games";

const lobby = createLobbyApi(BASE);
export const createGame = lobby.createGame;
export const joinGame = lobby.joinGame;

export async function getGameInfo(code: string): Promise<PDGameInfo> {
  return lobby.getGameInfo<PDGameInfo>(code);
}

export async function startGame(
  code: string,
  hostId: string,
  options?: { voting_seconds?: number; accusation_seconds?: number }
): Promise<void> {
  await request(`${BASE}/${code}/start`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
    body: JSON.stringify(options ?? {}),
  });
}

export async function getPrivateState(code: string, playerId: string): Promise<PDPrivateState> {
  return request(`${BASE}/${code}/me`, {
    headers: { "X-Player-Id": playerId },
  });
}

export async function submitVote(
  code: string,
  playerId: string,
  choice: "trust" | "betray",
  sabotage: boolean
): Promise<void> {
  await request(`${BASE}/${code}/vote`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ choice, sabotage }),
  });
}

export async function submitAccusation(
  code: string,
  playerId: string,
  accuse: boolean,
  targetId: string | null
): Promise<void> {
  await request(`${BASE}/${code}/accuse`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ accuse, target_id: targetId }),
  });
}

export function buildWsUrl(code: string, playerId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/prisoners-dilemma/api/pd/games/${code}/ws?player_id=${playerId}`;
}

export type { RoundResult, AccusationResult, GameOverData };
