interface Props {
  name: string;
}

export default function CharacterCard({ name }: Props) {
  return (
    <div className="bg-gradient-to-br from-mystery-700 to-mystery-800 rounded-2xl p-6 text-center shadow-xl border border-mystery-600">
      <p className="text-mystery-400 text-xs uppercase tracking-widest mb-1">
        Your Clue Card
      </p>
      <h2 className="text-3xl font-bold text-mystery-200">{name}</h2>
    </div>
  );
}
