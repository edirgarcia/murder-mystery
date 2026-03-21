import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createGame, getGameInfo, joinGame } from "../api/http";
import { usePDActions } from "../context/GameContext";

export default function HomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setGame, setPlayers } = usePDActions();
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
      localStorage.setItem("pd_player_id", host_id);
      localStorage.setItem("pd_game_code", code);
      localStorage.setItem("pd_is_host", "true");
      setGame(code, host_id, hostName, true);
      navigate(`/lobby/${code}`);
    } catch (err: any) {
      setError(err.message);
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
      localStorage.setItem("pd_player_id", player_id);
      localStorage.setItem("pd_game_code", code);
      localStorage.setItem("pd_is_host", "false");
      setGame(code, player_id, name.trim(), false);
      const info = await getGameInfo(code);
      setPlayers(info.players);
      navigate(`/lobby/${code}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(37,99,235,0.18),_transparent_36%),radial-gradient(circle_at_bottom,_rgba(220,38,38,0.18),_transparent_40%)] px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-4xl items-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-5">
            <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Social Strategy</p>
            <h1 className="max-w-xl text-5xl font-bold leading-tight text-white md:text-6xl">
              Trust your team.
              <br />
              Doubt everyone.
            </h1>
            <p className="max-w-xl text-lg leading-8 text-mystery-200">
              Players join on their phones, get split into red and blue teams, then vote to
              trust or betray while hidden spies can tamper with the outcome.
            </p>
            <div className="flex flex-wrap gap-3 text-sm text-mystery-200">
              <span className="rounded-full border border-red-400/30 bg-red-500/10 px-4 py-2">10 rounds</span>
              <span className="rounded-full border border-blue-400/30 bg-blue-500/10 px-4 py-2">2 hidden spies</span>
              <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2">Accuse every round</span>
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-2xl backdrop-blur">
            <div className="space-y-4">
              {!joinCode && (
                <>
                  <button
                    onClick={handleCreate}
                    disabled={loading}
                    className="w-full rounded-2xl bg-mystery-500 px-5 py-4 text-lg font-semibold text-white transition hover:bg-mystery-400 disabled:opacity-50"
                  >
                    {loading ? "..." : "Create Lobby"}
                  </button>

                  <div className="flex items-center gap-3">
                    <hr className="flex-1 border-white/10" />
                    <span className="text-mystery-400 text-sm">or join</span>
                    <hr className="flex-1 border-white/10" />
                  </div>
                </>
              )}

              <input
                type="text"
                placeholder="Your name"
                maxLength={30}
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-mystery-900/80 px-4 py-3 text-lg text-white outline-none focus:border-mystery-400"
              />

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="CODE"
                  maxLength={4}
                  value={joinCode}
                  onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
                  className="flex-1 rounded-2xl border border-white/10 bg-mystery-900/80 px-4 py-3 text-center text-lg tracking-[0.4em] text-white outline-none focus:border-mystery-400"
                />
                <button
                  onClick={handleJoin}
                  disabled={loading}
                  className="rounded-2xl bg-red-500 px-6 py-3 text-lg font-semibold text-white transition hover:bg-red-400 disabled:opacity-50"
                >
                  Join
                </button>
              </div>

              {error && <p className="text-sm text-red-300">{error}</p>}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
