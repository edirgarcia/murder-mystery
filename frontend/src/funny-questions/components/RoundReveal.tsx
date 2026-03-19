import type { RoundResult } from "../types/game";

interface Props {
  result: RoundResult;
}

export default function RoundReveal({ result }: Props) {
  // Build vote counts: {target_name: number_of_votes}
  const voteCounts = Object.entries(result.vote_breakdown)
    .map(([target, voters]) => ({ target, count: voters.length, voters }))
    .filter((e) => e.count > 0)
    .sort((a, b) => b.count - a.count);

  const maxVotes = Math.max(...voteCounts.map((e) => e.count), 1);
  const totalVotes = voteCounts.reduce((sum, e) => sum + e.count, 0);

  return (
    <div className="space-y-5">
      {/* Question */}
      <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl text-center">
        <p className="text-mystery-400 text-xs uppercase tracking-widest mb-2">
          The Question Was
        </p>
        <p className="text-mystery-100 text-xl font-bold leading-snug">
          {result.question}
        </p>
      </div>

      {/* Vote results bar chart */}
      <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl">
        <h4 className="text-mystery-200 font-bold text-lg mb-4">Who Got Votes?</h4>
        <div className="space-y-3">
          {voteCounts.map(({ target, count, voters }, i) => {
            const pct = (count / maxVotes) * 100;
            const isTop = i === 0;
            return (
              <div key={target}>
                <div className="flex justify-between items-end mb-1">
                  <span className={`font-semibold ${isTop ? "text-mystery-100 text-lg" : "text-mystery-200"}`}>
                    {target}
                    {isTop && result.most_voted_name === target ? " \u{1F3AF}" : ""}
                  </span>
                  <span className="text-mystery-300 font-bold text-lg tabular-nums">
                    {count} vote{count !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="w-full h-8 bg-mystery-700 rounded-lg overflow-hidden relative">
                  <div
                    className={`h-full rounded-lg transition-all duration-700 ease-out ${
                      isTop
                        ? "bg-gradient-to-r from-mystery-500 to-mystery-300"
                        : "bg-mystery-600"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                  <span className="absolute inset-0 flex items-center px-3 text-xs text-mystery-200 font-medium">
                    {voters.join(", ")}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
        {totalVotes === 0 && (
          <p className="text-mystery-400 text-center py-4">No votes this round!</p>
        )}
      </div>

      {/* Point deltas */}
      <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl">
        <h4 className="text-mystery-200 font-bold text-lg mb-3">Points This Round</h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
          {Object.entries(result.point_deltas)
            .sort(([, a], [, b]) => b - a)
            .map(([name, delta]) => (
              <div key={name} className="flex justify-between items-center">
                <span className="text-mystery-200 font-medium">{name}</span>
                <span
                  className={`font-bold text-lg tabular-nums ${
                    delta > 0
                      ? "text-green-400"
                      : delta < 0
                        ? "text-red-400"
                        : "text-mystery-500"
                  }`}
                >
                  {delta > 0 ? `+${delta}` : delta}
                </span>
              </div>
            ))}
        </div>
      </div>

      {/* Shame cleared */}
      {result.shame_cleared_name && !result.shame_holder_name && (
        <div className="bg-green-900/30 border border-green-700 rounded-2xl p-5 text-center shadow-xl">
          <p className="text-3xl mb-2">{"\u{1F389}"}</p>
          <p className="text-green-300 font-bold text-xl">
            {result.shame_cleared_name} is freed from Shame!
          </p>
          <p className="text-green-400/70 text-sm mt-1">
            Back in the game and can earn points again
          </p>
        </div>
      )}

      {/* Shame passed */}
      {result.shame_cleared_name && result.shame_holder_name && (
        <div className="bg-red-900/30 border border-red-700 rounded-2xl p-5 text-center shadow-xl">
          <p className="text-3xl mb-2">{"\u{1F504}"}</p>
          <p className="text-red-300 font-bold text-xl">
            Shame passes from {result.shame_cleared_name} to {result.shame_holder_name}!
          </p>
          <p className="text-red-400/70 text-sm mt-1">
            {result.shame_holder_name} can't earn points until shame is cleared
          </p>
        </div>
      )}

      {/* New shame (no previous holder) */}
      {result.shame_holder_name && !result.shame_cleared_name && (
        <div className="bg-red-900/30 border border-red-700 rounded-2xl p-5 text-center shadow-xl">
          <p className="text-3xl mb-2">{"\u{1F608}"}</p>
          <p className="text-red-300 font-bold text-xl">
            {result.shame_holder_name} has the Mark of Shame!
          </p>
          <p className="text-red-400/70 text-sm mt-1">
            Can't earn points until shame is cleared
          </p>
        </div>
      )}
    </div>
  );
}
