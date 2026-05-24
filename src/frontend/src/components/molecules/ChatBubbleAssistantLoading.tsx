import { Button, Skeleton } from "../atoms";

interface ChatBubbleAssistantLoadingProps {
  startedAt: number;
  onCancel: () => void;
  now?: number;
}

export function ChatBubbleAssistantLoading({
  startedAt,
  onCancel,
  now = Date.now()
}: ChatBubbleAssistantLoadingProps) {
  const elapsedSeconds = Math.floor((now - startedAt) / 1_000);
  const copy = elapsedSeconds >= 8 ? "Ainda consultando..." : "Consultando ERP...";
  const showCancel = elapsedSeconds >= 20;

  return (
    <article className="chat-bubble chat-bubble--assistant receipt receipt--loading" aria-label="Resposta em progresso">
      <div role="status" aria-label="Consultando ERP">
        <Skeleton />
        <p className="loading-copy">{copy}</p>
      </div>
      {showCancel ? (
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
      ) : null}
    </article>
  );
}
