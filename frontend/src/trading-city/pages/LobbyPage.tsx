import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { useSessionRestore } from "@shared/hooks/useRestoreSession";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import PlayerList from "@shared/components/PlayerList";
import type { WSEvent } from "@shared/types/game";
import { buildWsUrl, getGameInfo, startGame, type StartOptions } from "../api/http";
import { useTC } from "../context/GameContext";

type NumericOption = "total_rounds" | "auction_seconds" | "lot_creation_seconds" | "project_turn_seconds";

const OPTIONS: { key: NumericOption; label: string; values: number[]; unit: string }[] = [
  { key: "total_rounds", label: "Rounds", values: [4, 6, 8], unit: "" },
  { key: "lot_creation_seconds", label: "Lot building", values: [45, 60, 90], unit: "s" },
  { key: "auction_seconds", label: "Auction timer", values: [15, 20, 30], unit: "s" },
  { key: "project_turn_seconds", label: "Project turn", values: [20, 30, 45], unit: "s" },
];

// Playtest switches for the unresolved AI rules (spec §57).
const AI_CHOICES = [
  {
    key: "ai_strategy",
    label: "AI cities",
    choices: [
      { value: "heuristic", label: "Trade & build", hint: "AI sells surplus, bids for what it needs, chases one project" },
      { value: "passive", label: "Passive", hint: "AI only produces and pays upkeep" },
    ],
  },
  {
    key: "ai_project_priority",
    label: "AI project turns",
    choices: [
      { value: "rotating", label: "In rotation", hint: "All 8 cities share the priority order" },
      { value: "after_humans", label: "After humans", hint: "Humans always pick projects first" },
    ],
  },
] as const;

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state, setGame, setPlayers, setPhase } = useTC();
  const [options, setOptions] = useState<StartOptions>({
    total_rounds: 8,
    lot_creation_seconds: 60,
    auction_seconds: 20,
    project_turn_seconds: 30,
    ai_strategy: "heuristic",
    ai_project_priority: "rotating",
  });
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useSessionRestore("tc", code, state.playerId, setGame);

  const goToGame = useCallback(() => {
    navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`, { replace: true });
  }, [code, navigate, state.isHost]);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code)
      .then((info) => {
        setPlayers(info.players);
        setPhase(info.phase);
        if (info.phase === "playing") goToGame();
        if (info.phase === "finished") navigate(`/result/${code}`, { replace: true });
      })
      .catch(() => navigate("/", { replace: true }));
  }, [code, goToGame, navigate, setPhase, setPlayers]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      if (event.event === "player_joined" && code) {
        getGameInfo(code).then((info) => setPlayers(info.players));
      }
      if (event.event === "game_started") {
        setPhase("playing");
        goToGame();
      }
    },
    [code, goToGame, setPhase, setPlayers]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    setError("");
    try {
      await startGame(code, state.playerId, options);
    } catch (err: any) {
      setError(err.message);
      setStarting(false);
    }
  }

  const canStart = state.players.length >= 2 && !starting;

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
          <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Lobby Code</p>
              <h1 className="mt-2 text-6xl font-bold tracking-[0.35em] text-white">{code}</h1>
              <p className="mt-3 max-w-xl text-mystery-200">
                Up to 8 merchants. Any city nobody claims is run by an AI counterpart, so the world
                economy is the same size no matter how many play.
              </p>
            </div>
            {state.isHost && (
              <div className="rounded-3xl bg-white p-4">
                <QRCodeSVG value={`${window.location.origin}/trading-city/?join=${code}`} size={256} />
              </div>
            )}
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
          <div className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-white">Players</h2>
              <span className="rounded-full bg-mystery-700 px-3 py-1 text-sm text-mystery-200">
                {state.players.length} / 8
              </span>
            </div>
            <PlayerList players={state.players} />
            {state.players.length < 2 && (
              <p className="mt-4 text-sm text-amber-200">At least 2 players are required to start.</p>
            )}
            {!state.isHost && (
              <p className="mt-4 text-sm text-mystery-300">Waiting for the host to start…</p>
            )}
          </div>

          {state.isHost && (
            <div className="space-y-6">
              <div className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
                <h3 className="text-lg font-semibold text-white">Game Settings</h3>
                <div className="mt-4 space-y-4">
                  {OPTIONS.map((opt) => (
                    <div key={opt.key}>
                      <p className="mb-2 text-sm uppercase tracking-[0.25em] text-mystery-300">{opt.label}</p>
                      <div className="flex gap-2">
                        {opt.values.map((value) => (
                          <button
                            key={value}
                            onClick={() => setOptions((o) => ({ ...o, [opt.key]: value }))}
                            className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                              options[opt.key] === value
                                ? "bg-amber-600 text-white"
                                : "bg-mystery-700 text-mystery-200 hover:bg-mystery-600"
                            }`}
                          >
                            {value}
                            {opt.unit}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {AI_CHOICES.map((opt) => {
                    const selected = opt.choices.find((c) => c.value === options[opt.key]);
                    return (
                      <div key={opt.key}>
                        <p className="mb-2 text-sm uppercase tracking-[0.25em] text-mystery-300">{opt.label}</p>
                        <div className="flex gap-2">
                          {opt.choices.map((choice) => (
                            <button
                              key={choice.value}
                              onClick={() => setOptions((o) => ({ ...o, [opt.key]: choice.value }))}
                              className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                                options[opt.key] === choice.value
                                  ? "bg-teal-600 text-white"
                                  : "bg-mystery-700 text-mystery-200 hover:bg-mystery-600"
                              }`}
                            >
                              {choice.label}
                            </button>
                          ))}
                        </div>
                        {selected && <p className="mt-1 text-xs text-mystery-400">{selected.hint}</p>}
                      </div>
                    );
                  })}
                </div>
              </div>

              <button
                onClick={handleStart}
                disabled={!canStart}
                className="w-full rounded-[28px] bg-gradient-to-r from-amber-600 to-teal-600 px-6 py-4 text-lg font-semibold text-white shadow-xl transition hover:opacity-95 disabled:opacity-40"
              >
                {starting ? "Starting..." : "Open the Markets"}
              </button>
            </div>
          )}
        </section>

        {error && <p className="text-center text-sm text-red-300">{error}</p>}
      </div>
    </div>
  );
}
