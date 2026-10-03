import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "../types/game";

type Send = (message: Record<string, unknown>) => void;

/**
 * Narration lines from the server (intro, round-1 tutorial, milestones).
 *
 * The host dashboard plays the audio and acks each line so the server can move
 * on; phones only show the caption. The server sends `intro_done` when a block
 * of lines ends (or the host skipped).
 */
export function useNarration({ playAudio }: { playAudio: boolean }) {
  const [text, setText] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sendRef = useRef<Send>(() => {});

  const stopAudio = () => {
    audioRef.current?.pause();
    audioRef.current = null;
  };

  const onEvent = useCallback(
    (event: WSEvent) => {
      if (event.event === "intro_narration") {
        setText(event.data.text as string);
        const sound = event.data.sound as string | undefined;
        if (!playAudio || !sound) return;
        stopAudio();
        const ack = () => sendRef.current({ type: "narration_ack" });
        const audio = new Audio(`/trading-city/audio/${sound}`);
        audioRef.current = audio;
        audio.onended = ack;
        audio.onerror = ack;
        audio.play().catch(ack);
      } else if (event.event === "intro_done") {
        stopAudio();
        setText(null);
      }
    },
    [playAudio]
  );

  const skip = useCallback(() => {
    stopAudio();
    sendRef.current({ type: "skip_intro" });
  }, []);

  useEffect(() => stopAudio, []);

  return { text, onEvent, skip, sendRef };
}
