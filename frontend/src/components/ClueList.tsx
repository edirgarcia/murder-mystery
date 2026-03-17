import type { ClueInfo } from "../types/game";

interface Props {
  clues: ClueInfo[];
}

export default function ClueList({ clues }: Props) {
  return (
    <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl">
      <h3 className="text-mystery-300 font-semibold mb-3 text-sm uppercase tracking-wider">
        Your Clues
      </h3>
      <ul className="space-y-2">
        {clues.map((clue, i) => (
          <li
            key={i}
            className="bg-mystery-700/50 rounded-xl px-4 py-3 text-mystery-200 text-sm leading-relaxed"
          >
            {clue.text}
          </li>
        ))}
      </ul>
    </div>
  );
}
