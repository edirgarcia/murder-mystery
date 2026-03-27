import { request, createLobbyApi } from "@shared/api/http";
import type {
  Difficulty,
  GameInfo,
  GuessResponse,
  PlayerCard,
  ResultsResponse,
} from "../types/game";

const BASE = "/murder-mystery/api/mm/games";

const lobby = createLobbyApi(BASE);
export const createGame = lobby.createGame;
export const joinGame = lobby.joinGame;

export async function getGameInfo(code: string): Promise<GameInfo> {
  return lobby.getGameInfo<GameInfo>(code);
}

export async function startGame(
  code: string,
  hostId: string,
  difficulty?: Difficulty,
  roundMinutes?: number
): Promise<void> {
  await request(`${BASE}/${code}/start`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
    body: JSON.stringify({
      difficulty: difficulty ?? "medium",
      round_minutes: roundMinutes ?? 5,
    }),
  });
}

export async function getCard(
  code: string,
  playerId: string
): Promise<PlayerCard> {
  return request(`${BASE}/${code}/card`, {
    headers: { "X-Player-Id": playerId },
  });
}

export async function makeGuess(
  code: string,
  playerId: string,
  suspectName: string
): Promise<GuessResponse> {
  return request(`${BASE}/${code}/guess`, {
    method: "POST",
    headers: { "X-Player-Id": playerId },
    body: JSON.stringify({ suspect_name: suspectName }),
  });
}

export async function getResults(code: string): Promise<ResultsResponse> {
  return request(`${BASE}/${code}/results`);
}

export async function beginGame(
  code: string,
  hostId: string
): Promise<void> {
  await request(`${BASE}/${code}/begin`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
  });
}

export async function advanceRound(
  code: string,
  hostId: string
): Promise<void> {
  await request(`${BASE}/${code}/advance`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
  });
}

export async function endGame(
  code: string,
  hostId: string
): Promise<void> {
  await request(`${BASE}/${code}/end`, {
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

export function buildWsUrl(code: string, playerId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/murder-mystery/api/mm/games/${code}/ws?player_id=${playerId}`;
}
