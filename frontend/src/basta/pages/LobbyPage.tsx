import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import PlayerList from "@shared/components/PlayerList";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import type { WSEvent } from "@shared/types/game";
import { buildWsUrl, getGameInfo, startGame } from "../api/http";
import { useBasta, useBastaActions } from "../context/GameContext";

const DEFAULT_CATEGORIES = [
  "Nombre",
  "Apellido",
  "Ciudad o pais",
  "Animal",
  "Comida",
  "Color",
  "Cosa",
  "Planta",
];

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useBasta();
  const { setGame, setPlayers, addPlayer, setPhase, setConfig, setError } = useBastaActions();
  const [selectedCategories, setSelectedCategories] = useState(DEFAULT_CATEGORIES);
  const [roundsToPlay, setRoundsToPlay] = useState(5);
  const [roundSeconds, setRoundSeconds] = useState(15);
  const [hostPaced, setHostPaced] = useState(false);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("ba_player_id");
    const storedCode = localStorage.getItem("ba_game_code");
    const isHost = localStorage.getItem("ba_is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
    }
  }, [code, state.playerId, setGame]);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setConfig(info.categories, info.rounds_to_play, info.round_seconds, info.host_paced);
      if (info.categories.length > 0) {
        setSelectedCategories(info.categories);
      }
      if (info.phase === "playing") {
        setPhase("playing");
        navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`);
      }
    });
  }, [code]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "player_joined":
          addPlayer({
            id: event.data.player_id as string,
            name: event.data.player_name as string,
          });
          break;
        case "game_started":
          setPhase("playing");
          setConfig(
            event.data.categories as string[],
            event.data.rounds_to_play as number,
            event.data.round_seconds as number,
            event.data.host_paced as boolean
          );
          navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`);
          break;
      }
    },
    [code, navigate, addPlayer, setPhase, setConfig, state.isHost]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    try {
      await startGame(code, state.playerId, {
        categories: selectedCategories,
        rounds_to_play: roundsToPlay,
        round_seconds: roundSeconds,
        host_paced: hostPaced,
      });
    } catch (e: any) {
      setError(e.message);
      setStarting(false);
    }
  }

  function toggleCategory(category: string) {
    setSelectedCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category]
    );
  }

  const canStart = state.players.length >= 2 && selectedCategories.length > 0 && !starting;

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
              Game code
            </p>
            <h1 className="text-7xl font-black tracking-[0.2em] text-amber-200">
              {code}
            </h1>
          </div>

          <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-mystery-100">
                Players ({state.players.length})
              </h2>
              <span className="text-sm font-semibold text-mystery-400">Min 2</span>
            </div>
            <PlayerList players={state.players} />
          </div>

          {state.isHost && (
            <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-5 shadow-xl">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-mystery-300">
                  Categories
                </h2>
                <span className="text-sm font-semibold text-mystery-400">
                  {selectedCategories.length}/{DEFAULT_CATEGORIES.length}
                </span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {DEFAULT_CATEGORIES.map((category) => {
                  const checked = selectedCategories.includes(category);
                  return (
                    <label
                      key={category}
                      className={`flex min-h-12 items-center gap-3 rounded-lg border px-3 py-2 transition ${
                        checked
                          ? "border-amber-300 bg-amber-300/10 text-mystery-100"
                          : "border-mystery-700 bg-mystery-900 text-mystery-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={starting}
                        onChange={() => toggleCategory(category)}
                        className="h-5 w-5 accent-amber-300"
                      />
                      <span className="font-semibold">{category}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <aside className="space-y-5">
          {state.isHost && (
            <div className="rounded-lg bg-white p-3">
              <QRCodeSVG value={`${window.location.origin}/basta/?join=${code}`} size={312} />
            </div>
          )}

          {state.isHost && (
            <div className="space-y-5 rounded-lg border border-mystery-700 bg-mystery-800 p-5 shadow-xl">
              <div>
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-mystery-300">
                  Rounds
                </h3>
                <div className="grid grid-cols-3 gap-2">
                  {[5, 8, 10].map((value) => (
                    <button
                      key={value}
                      onClick={() => setRoundsToPlay(value)}
                      disabled={starting}
                      className={`rounded-lg px-3 py-2 font-bold transition ${
                        roundsToPlay === value
                          ? "bg-amber-300 text-mystery-900"
                          : "bg-mystery-700 text-mystery-200 hover:bg-mystery-600"
                      }`}
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-mystery-300">
                  Seconds
                </h3>
                <div className="grid grid-cols-3 gap-2">
                  {[10, 15, 20].map((value) => (
                    <button
                      key={value}
                      onClick={() => setRoundSeconds(value)}
                      disabled={starting}
                      className={`rounded-lg px-3 py-2 font-bold transition ${
                        roundSeconds === value
                          ? "bg-teal-300 text-mystery-900"
                          : "bg-mystery-700 text-mystery-200 hover:bg-mystery-600"
                      }`}
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setHostPaced(!hostPaced)}
                disabled={starting}
                className="flex w-full items-center justify-between rounded-lg bg-mystery-900 px-4 py-3"
              >
                <span className="font-semibold text-mystery-100">Host-paced reveals</span>
                <span
                  className={`h-6 w-11 rounded-full p-0.5 transition ${
                    hostPaced ? "bg-amber-300" : "bg-mystery-600"
                  }`}
                >
                  <span
                    className={`block h-5 w-5 rounded-full bg-white transition ${
                      hostPaced ? "translate-x-5" : ""
                    }`}
                  />
                </span>
              </button>

              <button
                onClick={handleStart}
                disabled={!canStart}
                className="w-full rounded-lg bg-amber-300 px-4 py-4 text-lg font-black text-mystery-900 transition hover:bg-amber-200 disabled:opacity-40"
              >
                {starting ? "Starting..." : "Start Game"}
              </button>
            </div>
          )}

          {!state.isHost && (
            <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-5 text-center shadow-xl">
              <p className="text-lg font-semibold text-mystery-100">Waiting for host</p>
            </div>
          )}

          {state.error && <p className="text-center text-sm text-rose-200">{state.error}</p>}
        </aside>
      </div>
    </div>
  );
}
