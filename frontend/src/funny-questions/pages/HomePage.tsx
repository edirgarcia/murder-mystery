import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createGame, joinGame, getGameInfo } from "../api/http";
import { useFQActions } from "../context/GameContext";

export default function HomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setGame, setPlayers } = useFQActions();
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState(searchParams.get("join")?.toUpperCase() ?? "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    const hostName = name.trim() || "Host";
    setLoading(true);
    setError("");
    try {
      const { code, host_id } = await createGame(hostName);
      localStorage.setItem("fq_player_id", host_id);
      localStorage.setItem("fq_game_code", code);
      localStorage.setItem("fq_is_host", "true");
      setGame(code, host_id, hostName, true);
      navigate(`/lobby/${code}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin() {
    if (!name.trim()) return setError("Enter your name");
    if (!joinCode.trim()) return setError("Enter a game code");
    setLoading(true);
    setError("");
    try {
      const code = joinCode.trim().toUpperCase();
      const { player_id } = await joinGame(code, name.trim());
      localStorage.setItem("fq_player_id", player_id);
      localStorage.setItem("fq_game_code", code);
      localStorage.setItem("fq_is_host", "false");
      setGame(code, player_id, name.trim(), false);
      const info = await getGameInfo(code);
      setPlayers(info.players);
      navigate(`/lobby/${code}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-mystery-300 mb-2">
            Funny Questions
          </h1>
          <p className="text-mystery-400 text-lg">Vote. Shame. Win.</p>
        </div>

        <div className="bg-mystery-800 rounded-2xl p-6 space-y-4 shadow-xl">
          {!joinCode && (
            <>
              <button
                onClick={handleCreate}
                disabled={loading}
                className="w-full py-3 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition disabled:opacity-50"
              >
                {loading ? "..." : "Create Game"}
              </button>

              <div className="flex items-center gap-3">
                <hr className="flex-1 border-mystery-600" />
                <span className="text-mystery-400 text-sm">or join</span>
                <hr className="flex-1 border-mystery-600" />
              </div>
            </>
          )}

          <input
            type="text"
            placeholder="Your name"
            maxLength={30}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-mystery-700 text-white placeholder-mystery-400 outline-none focus:ring-2 focus:ring-mystery-500 text-lg"
          />

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="CODE"
              maxLength={4}
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              className="flex-1 px-4 py-3 rounded-xl bg-mystery-700 text-white placeholder-mystery-400 outline-none focus:ring-2 focus:ring-mystery-500 text-lg tracking-widest text-center uppercase"
            />
            <button
              onClick={handleJoin}
              disabled={loading}
              className="px-6 py-3 rounded-xl bg-mystery-600 hover:bg-mystery-500 text-white font-semibold text-lg transition disabled:opacity-50"
            >
              Join
            </button>
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
