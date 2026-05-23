import { request, createLobbyApi } from "@shared/api/http";
import type { BastaGameInfo, PlayerScoreEntry } from "../types/game";

const BASE = "/basta/api/ba/games";

const lobby = createLobbyApi(BASE);
export const createGame = lobby.createGame;
export const joinGame = lobby.joinGame;

export async function getGameInfo(code: string): Promise<BastaGameInfo> {
  return lobby.getGameInfo<BastaGameInfo>(code);
}

export async function startGame(
  code: string,
  hostId: string,
  options: {
    categories?: string[];
    rounds_to_play?: number;
    round_seconds?: number;
    host_paced?: boolean;
  }
): Promise<void> {
  await request(`${BASE}/${code}/start`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
    body: JSON.stringify(options),
  });
}

export async function submitAnswers(
  code: string,
  playerId: string,
  answers: Record<string, string>,
  autoSubmit = false
): Promise<void> {
  await request(`${BASE}/${code}/answers`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ answers, auto_submit: autoSubmit }),
  });
}

export async function saveDraft(
  code: string,
  playerId: string,
  answers: Record<string, string>
): Promise<void> {
  await request(`${BASE}/${code}/draft`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ answers }),
  });
}

export async function vetoAnswer(
  code: string,
  playerId: string,
  category: string,
  targetPlayerId: string
): Promise<void> {
  await request(`${BASE}/${code}/veto`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({
      category,
      target_player_id: targetPlayerId,
    }),
  });
}

export async function nextRound(code: string, hostId: string): Promise<void> {
  await request(`${BASE}/${code}/next`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
  });
}

export async function resetGame(code: string, hostId: string): Promise<void> {
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
  return `${protocol}//${host}/basta/api/ba/games/${code}/ws?player_id=${playerId}`;
}
