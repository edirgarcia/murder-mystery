interface Props {
  scores: Record<string, number>;
  shameHolder: string | null;
  pointsToWin: number;
}

export default function ScoreBoard({ scores, shameHolder, pointsToWin }: Props) {
  const sorted = Object.entries(scores).sort(([, a], [, b]) => b - a);
  const maxScore = Math.max(...Object.values(scores), 1);

  return (
    <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-mystery-200 font-bold text-lg">Scoreboard</h3>
        <span className="text-mystery-400 text-sm font-medium">First to {pointsToWin}</span>
      </div>
      <div className="space-y-3">
        {sorted.map(([name, score], i) => {
          const pct = Math.min(100, (score / pointsToWin) * 100);
          const isLeader = i === 0 && score > 0;
          const isShamed = name === shameHolder;

          return (
            <div key={name}>
              <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-medium text-mystery-100">
                    {isLeader ? "\u{1F451}" : ""} {name}
                  </span>
                  {isShamed && (
                    <span className="text-xs bg-red-900/50 text-red-400 px-2 py-0.5 rounded-full font-semibold">
                      SHAME
                    </span>
                  )}
                </div>
                <span className="text-mystery-100 font-bold text-xl tabular-nums">
                  {score}
                </span>
              </div>
              <div className="w-full h-5 bg-mystery-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${
                    isShamed
                      ? "bg-red-500/60"
                      : isLeader
                        ? "bg-gradient-to-r from-mystery-500 to-mystery-300"
                        : "bg-mystery-500"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      {/* Goal line indicator */}
      <div className="mt-3 flex items-center gap-2 text-mystery-400 text-xs">
        <div className="flex-1 border-t border-mystery-600 border-dashed" />
        <span>{pointsToWin} pts to win</span>
        <div className="flex-1 border-t border-mystery-600 border-dashed" />
      </div>
    </div>
  );
}
