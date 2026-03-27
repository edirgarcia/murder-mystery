import { request, createLobbyApi } from "@shared/api/http";
import type { FQGameInfo, PlayerScoreEntry } from "../types/game";

const BASE = "/funny-questions/api/fq/games";

const lobby = createLobbyApi(BASE);
export const createGame = lobby.createGame;
export const joinGame = lobby.joinGame;

export async function getGameInfo(code: string): Promise<FQGameInfo> {
  return lobby.getGameInfo<FQGameInfo>(code);
}

export async function startGame(
  code: string,
  hostId: string,
  options?: { categories?: string[]; max_spice?: number; points_to_win?: number; host_paced?: boolean }
): Promise<void> {
  await request(`${BASE}/${code}/start`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
    body: JSON.stringify(options ?? {}),
  });
}

export async function vote(
  code: string,
  playerId: string,
  votedFor: string
): Promise<void> {
  await request(`${BASE}/${code}/vote`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ voted_for: votedFor }),
  });
}

export async function nextQuestion(
  code: string,
  hostId: string
): Promise<void> {
  await request(`${BASE}/${code}/next`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
  });
}

export async function resetGame(
  code: string,
  hostId: string
): Promise<void> {
  await request(`${BASE}/${code}/reset`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
  });
}

export async function getScores(code: string): Promise<PlayerScoreEntry[]> {
  return request(`${BASE}/${code}/scores`);
}

export function buildWsUrl(code: string, playerId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/funny-questions/api/fq/games/${code}/ws?player_id=${playerId}`;
}
