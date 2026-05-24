import type { AttentionMessage } from "../../types/chat";
import { Button, Icon } from "../atoms";

interface ChatBubbleAssistantAttentionProps {
  message: AttentionMessage;
  onRetry: (question: string) => void;
  onReformulate: (question: string) => void;
}

export function ChatBubbleAssistantAttention({
  message,
  onRetry,
  onReformulate
}: ChatBubbleAssistantAttentionProps) {
  const handleAction = () => {
    if (message.variant === "pii") {
      onReformulate(message.question);
      return;
    }
    onRetry(message.question);
  };

  return (
    <article className="chat-bubble chat-bubble--assistant receipt receipt--attention" role="alert">
      <div className="attention-copy">
        <Icon name="attention" />
        <p>{message.message}</p>
      </div>
      {message.actionLabel ? (
        <Button type="button" variant="secondary" onClick={handleAction}>
          {message.actionLabel}
        </Button>
      ) : null}
      <time>{message.timestamp}</time>
    </article>
  );
}
