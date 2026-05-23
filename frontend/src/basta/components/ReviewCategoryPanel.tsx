import type { ReviewCategory } from "../types/game";

interface Props {
  review: ReviewCategory;
  currentPlayerId: string | null;
  layout?: "phone" | "dashboard";
  vetoedKeys?: Set<string>;
  onVeto?: (targetPlayerId: string) => void;
}

export default function ReviewCategoryPanel({
  review,
  currentPlayerId,
  layout = "phone",
  vetoedKeys,
  onVeto,
}: Props) {
  const isDashboard = layout === "dashboard";

  return (
    <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-4 shadow-xl sm:p-5">
      <div
        className={`mb-5 flex gap-4 ${
          isDashboard ? "items-center justify-between" : "flex-col"
        }`}
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-mystery-400">
            Category {review.category_index + 1} of {review.category_count}
          </p>
          <h2 className="mt-1 text-3xl font-black text-mystery-100">
            {review.category}
          </h2>
        </div>
        <div
          className={
            isDashboard
              ? "text-right"
              : "flex items-end justify-between gap-4"
          }
        >
          {!isDashboard && (
            <p className="pb-1 text-sm font-bold text-rose-200">
              {review.vetoes_required} vetoes needed
            </p>
          )}
          <div className="text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-mystery-400">
              Letter
            </p>
            <p className="text-5xl font-black leading-none text-amber-200">
              {review.letter}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {review.answers.map((answer) => {
          const hasAnswer = Boolean(answer.answer.trim());
          const isMine = answer.player_id === currentPlayerId;
          const vetoKey = `${review.category}:${answer.player_id}`;
          const alreadyVetoed = vetoedKeys?.has(vetoKey) ?? false;
          return (
            <div
              key={answer.player_id}
              className={`rounded-lg border border-mystery-700 bg-mystery-900 p-3 ${
                isDashboard
                  ? "grid items-center gap-4 md:grid-cols-[180px_minmax(0,1fr)_120px]"
                  : "space-y-3"
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-mystery-200">
                  {answer.player_name}
                </p>
              </div>

              <div className="min-w-0">
                <p className="truncate text-2xl font-black text-mystery-100 md:text-xl">
                  {hasAnswer ? answer.answer : "-"}
                </p>
              </div>

              <div className={isDashboard ? "text-right" : "flex items-center justify-between"}>
                <p className="text-xs font-bold text-rose-200">
                  {answer.veto_count}/{review.vetoes_required} vetoes
                </p>
              </div>

              {onVeto && (
                <button
                  onClick={() => onVeto(answer.player_id)}
                  disabled={isMine || !hasAnswer || alreadyVetoed}
                  className="w-full rounded-lg bg-rose-300 px-4 py-3 text-sm font-black text-mystery-900 transition hover:bg-rose-200 disabled:bg-mystery-700 disabled:text-mystery-400"
                >
                  {alreadyVetoed ? "Vetoed" : "Veto"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
