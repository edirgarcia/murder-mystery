import type { WWPlayerInfo } from "../types/game";

export default function DeathAnnouncement({ deaths, players }: { deaths: string[]; players: WWPlayerInfo[] }) {
  if (deaths.length === 0) {
    return <p className="text-mystery-300">No one died.</p>;
  }

  const names = deaths
    .map((id) => players.find((p) => p.id === id)?.name ?? id)
    .join(", ");

  return <p className="text-red-300 font-semibold">Died: {names}</p>;
}
