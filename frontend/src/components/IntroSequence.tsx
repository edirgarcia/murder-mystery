import { useState, useEffect, useRef } from "react";

interface IntroSequenceProps {
  playerNames: string[];
  murderWeapon: string;
  onComplete: () => void;
}

export default function IntroSequence({
  playerNames,
  murderWeapon,
  onComplete,
}: IntroSequenceProps) {
  const [visibleUpTo, setVisibleUpTo] = useState(-1);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const nameStaggerMs = 400;
  const nameBlockDuration = playerNames.length * nameStaggerMs;

  const beatDelays = [
    0,                                    // 0: "A Murder Mystery"
    2500,                                 // 1: "Tonight's guests:"
    3500,                                 // 2: Player names (staggered from here)
    3500 + nameBlockDuration + 2000,      // 3: "gathered for an evening..."
    3500 + nameBlockDuration + 4500,      // 4: "But one among them..."
    3500 + nameBlockDuration + 7500,      // 5: "The weapon: X"
    3500 + nameBlockDuration + 10500,     // 6: "Someone here is the killer."
    3500 + nameBlockDuration + 13000,     // 7: "Examine your clues..."
  ];

  const totalDuration = beatDelays[beatDelays.length - 1] + 2500;

  useEffect(() => {
    beatDelays.forEach((delay, i) => {
      const t = setTimeout(() => setVisibleUpTo(i), delay);
      timersRef.current.push(t);
    });
    const endTimer = setTimeout(onComplete, totalDuration);
    timersRef.current.push(endTimer);
    return () => timersRef.current.forEach(clearTimeout);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const beat = (index: number, anim: string) =>
    visibleUpTo >= index ? anim : "opacity-0";

  return (
    <div className="fixed inset-0 z-50 bg-mystery-900 flex items-center justify-center px-6">
      <div className="max-w-lg text-center space-y-6">
        {/* Title */}
        <h1
          className={`text-5xl font-bold text-mystery-200 ${beat(0, "animate-fade-in-up")}`}
        >
          A Murder Mystery
        </h1>

        {/* Guest intro */}
        <p
          className={`text-sm uppercase tracking-widest text-mystery-400 ${beat(1, "animate-fade-in")}`}
        >
          Tonight's guests
        </p>

        {/* Player names - staggered */}
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2">
          {playerNames.map((name, i) => (
            <span
              key={name}
              className={`text-xl font-semibold text-mystery-300 opacity-0 ${
                visibleUpTo >= 2 ? "animate-fade-in-up" : ""
              }`}
              style={
                visibleUpTo >= 2
                  ? { animationDelay: `${i * nameStaggerMs}ms` }
                  : undefined
              }
            >
              {name}
            </span>
          ))}
        </div>

        {/* Gathering */}
        <p
          className={`text-mystery-400 italic ${beat(3, "animate-fade-in")}`}
        >
          gathered for an evening of intrigue...
        </p>

        {/* Dark turn */}
        <p
          className={`text-red-400 font-semibold text-lg ${beat(4, "animate-fade-in-up")}`}
        >
          But one among them harbors a deadly secret.
        </p>

        {/* Weapon reveal */}
        <div className={`${beat(5, "animate-fade-in-up")}`}>
          <p className="text-sm uppercase tracking-widest text-mystery-400 mb-1">
            The weapon
          </p>
          <p
            className={`text-4xl font-bold text-red-400 ${
              visibleUpTo >= 5 ? "animate-pulse-glow" : ""
            }`}
          >
            {murderWeapon}
          </p>
        </div>

        {/* Killer line */}
        <p
          className={`text-mystery-200 text-lg ${beat(6, "animate-fade-in")}`}
        >
          Someone here is the killer.
        </p>

        {/* Call to action */}
        <p
          className={`text-mystery-300 font-semibold text-lg ${beat(7, "animate-fade-in-up")}`}
        >
          Examine your clues. Find the truth.
        </p>
      </div>
    </div>
  );
}
