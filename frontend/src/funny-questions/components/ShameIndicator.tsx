interface Props {
  name: string;
}

export default function ShameIndicator({ name }: Props) {
  return (
    <div className="bg-red-900/30 border border-red-800 rounded-xl p-3 text-center">
      <p className="text-red-400 text-sm font-semibold">
        {name} holds the Mark of Shame
      </p>
    </div>
  );
}
