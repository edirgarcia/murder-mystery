interface Props {
  scores: Record<string, number>;
}

export default function ScoreBoard({ scores }: Props) {
  const sorted = Object.entries(scores).sort(([, a], [, b]) => b - a);
  const maxScore = Math.max(...Object.values(scores), 1);

  return (
    <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-4 shadow-xl">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-mystery-200">
          Scores
        </h3>
        <span className="rounded bg-amber-300 px-2 py-1 text-xs font-bold text-mystery-900">
          Basta
        </span>
      </div>
      <div className="space-y-3">
        {sorted.map(([name, score], index) => {
          const percent = Math.max(4, Math.min(100, (score / maxScore) * 100));
          return (
            <div key={name} className="space-y-1">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="min-w-0 truncate text-mystery-100">
                  {index + 1}. {name}
                </span>
                <span className="font-bold tabular-nums text-amber-200">{score}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-mystery-700">
                <div
                  className="h-full rounded-full bg-teal-300"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
        {sorted.length === 0 && (
          <p className="text-sm text-mystery-400">No scores yet</p>
        )}
      </div>
    </div>
  );
}
