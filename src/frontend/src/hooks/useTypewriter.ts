import { useEffect, useState } from "react";

interface UseTypewriterOptions {
  baseCharsPerSecond?: number;
  fastCharsPerSecond?: number;
  shortThresholdChars?: number;
  longThresholdChars?: number;
  skipBelowChars?: number;
  accelerateAfterMs?: number;
}

interface UseTypewriterResult {
  visible: string;
  isTyping: boolean;
}

export function useTypewriter(text: string, options: UseTypewriterOptions = {}): UseTypewriterResult {
  const baseCharsPerSecond = options.baseCharsPerSecond ?? 80;
  const fastCharsPerSecond = options.fastCharsPerSecond ?? 120;
  const shortThresholdChars = options.shortThresholdChars ?? 100;
  const longThresholdChars = options.longThresholdChars ?? 500;
  const skipBelowChars = options.skipBelowChars ?? 50;
  const accelerateAfterMs = options.accelerateAfterMs ?? 2000;

  const [visible, setVisible] = useState<string>(text);
  const [isTyping, setIsTyping] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      setVisible(text);
      setIsTyping(false);
      return;
    }
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || text.length < skipBelowChars) {
      setVisible(text);
      setIsTyping(false);
      return;
    }

    let index = 0;
    const startedAt = performance.now();
    const initialSpeed =
      text.length <= shortThresholdChars ? fastCharsPerSecond : baseCharsPerSecond;
    let charsPerSecond = initialSpeed;
    setVisible("");
    setIsTyping(true);

    const interval = window.setInterval(() => {
      const elapsed = performance.now() - startedAt;
      if (text.length >= longThresholdChars && elapsed >= accelerateAfterMs) {
        charsPerSecond = fastCharsPerSecond;
      }
      const step = Math.max(1, Math.round(charsPerSecond / 60));
      index = Math.min(text.length, index + step);
      setVisible(text.slice(0, index));
      if (index >= text.length) {
        setIsTyping(false);
        window.clearInterval(interval);
      }
    }, 1000 / 60);

    return () => {
      window.clearInterval(interval);
    };
  }, [
    text,
    baseCharsPerSecond,
    fastCharsPerSecond,
    shortThresholdChars,
    longThresholdChars,
    skipBelowChars,
    accelerateAfterMs
  ]);

  return { visible, isTyping };
}
