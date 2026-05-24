import { useEffect, useState } from "react";

import { Button, Skeleton } from "../atoms";

interface ChatBubbleAssistantLoadingProps {
  startedAt: number;
  onCancel: () => void;
  now?: number;
}

const LOADING_COPIES = [
  "Consultando ERP...",
  "Lendo tabelas margens-2026-05...",
  "Ainda consultando...",
  "Conferindo premissas com a direcao..."
] as const;
const ROTATION_INTERVAL_MS = 4_000;

export function ChatBubbleAssistantLoading({
  startedAt,
  onCancel,
  now = Date.now()
}: ChatBubbleAssistantLoadingProps) {
  const [copyIndex, setCopyIndex] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setCopyIndex((prev) => (prev + 1) % LOADING_COPIES.length);
    }, ROTATION_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, []);

  const elapsedSeconds = Math.floor((now - startedAt) / 1_000);
  const showCancel = elapsedSeconds >= 20;
  const copy = LOADING_COPIES[copyIndex];

  return (
    <article className="chat-bubble chat-bubble--assistant receipt receipt--loading" aria-label="Resposta em progresso">
      <div role="status" aria-label="Consultando ERP">
        <Skeleton />
        <p key={copyIndex} className="loading-copy loading-copy--glitch">{copy}</p>
      </div>
      {showCancel ? (
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
      ) : null}
    </article>
  );
}
