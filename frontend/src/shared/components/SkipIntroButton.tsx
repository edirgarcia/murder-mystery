interface SkipIntroButtonProps {
  onSkip: () => void;
}

/**
 * Small text link shown over the intro narration overlay so a host who has
 * already played can skip the instructions.
 */
export default function SkipIntroButton({ onSkip }: SkipIntroButtonProps) {
  return (
    <button
      onClick={onSkip}
      className="fixed bottom-6 right-6 z-[51] text-sm text-mystery-400 underline underline-offset-4 transition hover:text-mystery-200"
    >
      Skip intro
    </button>
  );
}
