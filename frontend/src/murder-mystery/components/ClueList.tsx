import type { ClueInfo } from "../types/game";

interface Props {
  clues: ClueInfo[];
  currentRound: number;
}

export default function ClueList({ clues, currentRound }: Props) {
  // Group clues by round
  const rounds = new Map<number, ClueInfo[]>();
  for (const clue of clues) {
    const r = clue.round ?? 1;
    if (!rounds.has(r)) rounds.set(r, []);
    rounds.get(r)!.push(clue);
  }

  const sortedRounds = [...rounds.keys()].sort((a, b) => a - b);

  return (
    <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl">
      <h3 className="text-mystery-300 font-semibold mb-3 text-sm uppercase tracking-wider">
        Your Clues
      </h3>
      <div className="space-y-4">
        {sortedRounds.map((round) => (
          <div key={round}>
            {sortedRounds.length > 1 && (
              <p className="text-mystery-400 text-xs uppercase tracking-wider mb-2">
                Round {round}
              </p>
            )}
            <ul className="space-y-2">
              {rounds.get(round)!.map((clue, i) => (
                <li
                  key={`${round}-${i}`}
                  className={`rounded-xl px-4 py-3 text-mystery-200 text-sm leading-relaxed ${
                    round === currentRound
                      ? "bg-mystery-600/60 ring-1 ring-mystery-400/30"
                      : "bg-mystery-700/50"
                  }`}
                >
                  {clue.text}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
