export async function request<T>(
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

export function createLobbyApi(baseUrl: string) {
  return {
    createGame(hostName: string): Promise<{ code: string; host_id: string }> {
      return request(`${baseUrl}`, {
        method: "POST",
        body: JSON.stringify({ host_name: hostName }),
      });
    },

    joinGame(code: string, playerName: string): Promise<{ player_id: string }> {
      return request(`${baseUrl}/${code}/join`, {
        method: "POST",
        body: JSON.stringify({ player_name: playerName }),
      });
    },

    getGameInfo<T>(code: string): Promise<T> {
      return request<T>(`${baseUrl}/${code}`);
    },
  };
}
