import type {
  Difficulty,
  GameInfo,
  GuessResponse,
  PlayerCard,
  ResultsResponse,
} from "../types/game";

const BASE = "/api/games";

async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const { headers, ...rest } = options ?? {};
  const res = await fetch(url, {
    ...rest,
    headers: { "Content-Type": "application/json", ...headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function createGame(
  hostName: string
): Promise<{ code: string; host_id: string }> {
  return request(`${BASE}`, {
    method: "POST",
    body: JSON.stringify({ host_name: hostName }),
  });
}

export async function joinGame(
  code: string,
  playerName: string
): Promise<{ player_id: string }> {
  return request(`${BASE}/${code}/join`, {
    method: "POST",
    body: JSON.stringify({ player_name: playerName }),
  });
}

export async function getGameInfo(code: string): Promise<GameInfo> {
  return request(`${BASE}/${code}`);
}

export async function startGame(
  code: string,
  hostId: string,
  difficulty?: Difficulty,
  timerMinutes?: number
): Promise<void> {
  await request(`${BASE}/${code}/start`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
    body: JSON.stringify({
      difficulty: difficulty ?? "medium",
      timer_minutes: timerMinutes ?? 10,
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

export async function endGame(
  code: string,
  hostId: string
): Promise<void> {
  await request(`${BASE}/${code}/end`, {
    method: "POST",
    headers: { "X-Player-Id": hostId },
  });
}
