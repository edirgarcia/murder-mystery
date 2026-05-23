import type { RoundResult } from "../types/game";

interface Props {
  result: RoundResult;
}

export default function RoundResultTable({ result }: Props) {
  const players = Object.keys(result.scores);

  return (
    <div className="overflow-hidden rounded-lg border border-mystery-700 bg-mystery-800 shadow-xl">
      <div className="flex items-center justify-between border-b border-mystery-700 px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-mystery-400">Letter</p>
          <h3 className="text-3xl font-black text-amber-200">{result.letter}</h3>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-mystery-400">Round</p>
          <p className="text-lg font-semibold text-mystery-100">Results</p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="bg-mystery-900/70 text-left text-xs uppercase tracking-wide text-mystery-300">
              <th className="w-40 px-4 py-3 font-semibold">Category</th>
              {players.map((player) => (
                <th key={player} className="px-4 py-3 font-semibold">
                  {player}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.category_results.map((category) => (
              <tr key={category.category} className="border-t border-mystery-700">
                <td className="px-4 py-3 font-semibold text-mystery-100">
                  {category.category}
                </td>
                {players.map((player) => {
                  const answer = category.answers[player] || "-";
                  const points = category.points[player] ?? 0;
                  const isInvalid = category.invalid_players.includes(player);
                  return (
                    <td key={player} className="px-4 py-3 align-top">
                      <div className="max-w-[180px] truncate text-mystery-100" title={answer}>
                        {answer}
                      </div>
                      <div
                        className={`mt-1 text-xs font-bold ${
                          points > 0 ? "text-teal-200" : isInvalid ? "text-rose-200" : "text-mystery-400"
                        }`}
                      >
                        {points}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-mystery-600 bg-mystery-900/70">
              <td className="px-4 py-3 font-bold text-mystery-100">Total</td>
              {players.map((player) => (
                <td key={player} className="px-4 py-3 font-black text-amber-200">
                  {result.round_points[player] ?? 0}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
