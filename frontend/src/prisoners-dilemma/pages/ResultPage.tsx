import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getGameInfo } from "../api/http";
import { usePD, usePDActions } from "../context/GameContext";

function winnerLabel(winner: "red" | "blue" | "draw" | "nobody" | null) {
  if (winner === "red") return "Red Team Wins";
  if (winner === "blue") return "Blue Team Wins";
  if (winner === "draw") return "Draw";
  if (winner === "nobody") return "Nobody Wins";
  return "Game Over";
}

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = usePD();
  const { setGame, setPhase, setPlayers, setTeamScores } = usePDActions();

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("pd_player_id");
    const storedCode = localStorage.getItem("pd_game_code");
    const isHost = localStorage.getItem("pd_is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
    }
  }, [code, setGame, state.playerId]);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPhase(info.phase);
      setPlayers(info.players);
      setTeamScores(info.team_scores);
    });
  }, [code, setPhase, setPlayers, setTeamScores]);

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <section className="rounded-[36px] border border-white/10 bg-mystery-800/80 p-8 text-center shadow-xl">
          <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Final Result</p>
          <h1 className="mt-3 text-5xl font-bold text-white">{winnerLabel(state.winner)}</h1>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-5">
              <p className="text-sm uppercase tracking-[0.2em] text-red-100">Red Team</p>
              <p className="mt-2 text-4xl font-bold text-white">{state.teamScores.red}</p>
            </div>
            <div className="rounded-2xl border border-blue-400/30 bg-blue-500/10 p-5">
              <p className="text-sm uppercase tracking-[0.2em] text-blue-100">Blue Team</p>
              <p className="mt-2 text-4xl font-bold text-white">{state.teamScores.blue}</p>
            </div>
          </div>
        </section>

        {state.finalSpies && (
          <section className="grid gap-4 sm:grid-cols-2">
            {(["red", "blue"] as const).map((team) => {
              const spy = state.finalSpies?.[team];
              if (!spy) return null;
              return (
                <div key={team} className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
                  <p className="text-sm uppercase tracking-[0.25em] text-mystery-300">{team} spy</p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">{spy.player_name}</h2>
                  <p className="mt-2 text-sm text-mystery-200">
                    {spy.exposed ? "Caught before the end of the game." : "Stayed hidden through the final round."}
                  </p>
                </div>
              );
            })}
          </section>
        )}

        <button
          onClick={() => navigate("/")}
          className="w-full rounded-[28px] bg-mystery-500 px-6 py-4 text-lg font-semibold text-white transition hover:bg-mystery-400"
        >
          New Game
        </button>
      </div>
    </div>
  );
}
