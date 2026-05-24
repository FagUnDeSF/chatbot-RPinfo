import type { UserMessage } from "../../types/chat";

interface ChatBubbleUserProps {
  message: UserMessage;
}

export function ChatBubbleUser({ message }: ChatBubbleUserProps) {
  return (
    <article className="chat-bubble chat-bubble--user" aria-label="Pergunta do operador">
      <p>{message.question}</p>
      <time>{message.timestamp}</time>
    </article>
  );
}
