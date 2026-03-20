import { createLobbyApi, request } from "@shared/api/http";
import type { WWGameInfo, WWPrivateState } from "../types/game";

const BASE = "/werewolf/api/ww/games";

const lobby = createLobbyApi(BASE);
export const createGame = lobby.createGame;
export const joinGame = lobby.joinGame;

export async function getGameInfo(code: string): Promise<WWGameInfo> {
  return lobby.getGameInfo<WWGameInfo>(code);
}

export async function startGame(
  code: string,
  hostId: string,
  discussionSeconds: number
): Promise<void> {
  await request(`${BASE}/${code}/start`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
    body: JSON.stringify({ discussion_seconds: discussionSeconds }),
  });
}

export async function submitNightAction(
  code: string,
  playerId: string,
  payload: { action: string; target?: string; target2?: string }
): Promise<void> {
  await request(`${BASE}/${code}/night-action`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify(payload),
  });
}

export async function submitVote(
  code: string,
  playerId: string,
  target: string
): Promise<void> {
  await request(`${BASE}/${code}/vote`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ target }),
  });
}

export async function getPlayerState(code: string, playerId: string): Promise<WWPrivateState> {
  return request(`${BASE}/${code}/state`, {
    headers: { "X-Player-Id": playerId },
  });
}

export function buildWsUrl(code: string, playerId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/werewolf/api/ww/games/${code}/ws?player_id=${playerId}`;
}
