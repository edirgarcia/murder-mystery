interface Props {
  question: string;
  round: number;
}

export default function QuestionCard({ question, round }: Props) {
  return (
    <div className="bg-gradient-to-br from-mystery-700 to-mystery-800 rounded-2xl p-6 text-center shadow-xl border border-mystery-600">
      <p className="text-mystery-400 text-xs uppercase tracking-widest mb-2">
        Round {round}
      </p>
      <h2 className="text-2xl font-bold text-mystery-200 leading-relaxed">
        {question}
      </h2>
    </div>
  );
}
