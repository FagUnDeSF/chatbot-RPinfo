import type { AssistantMessage } from "../../types/chat";
import {
  Badge,
  Icon,
  ProtocolStamp,
  ReceiptDivider,
  Ribbon,
  Tooltip
} from "../atoms";
import { FallbackNote } from "./FallbackNote";
import { PremisesBlock } from "./PremisesBlock";
import { SourceBlock } from "./SourceBlock";

interface AssistantReceiptBubbleProps {
  message: AssistantMessage;
}

export function AssistantReceiptBubble({ message }: AssistantReceiptBubbleProps) {
  const isEscalated = message.variant === "escalated";
  const hasFallback = message.variant === "fallback" || message.headers.fallback !== null;
  const hasDenied = message.headers.escalationDenied !== null;

  return (
    <article
      className={`chat-bubble chat-bubble--assistant receipt receipt--${message.variant}`}
      aria-label="Resposta do assistente"
      aria-live="polite"
    >
      {isEscalated ? <Ribbon /> : null}
      <header className="receipt__header">
        <span>CONSULTA #{message.id.slice(-4).toUpperCase()}</span>
        <span className="receipt__meta">
          {isEscalated ? (
            <Tooltip label="resposta processada com modelo de maior capacidade">
              <span tabIndex={0} className="badge-trigger">
                <Badge>modelo escalado</Badge>
                <Icon name="info" />
              </span>
            </Tooltip>
          ) : null}
          <time>{message.timestamp}</time>
        </span>
      </header>
      <p className="receipt__answer">{message.answer}</p>
      <ReceiptDivider />
      <SourceBlock source={message.source} />
      <PremisesBlock premises={message.premises} />
      {hasFallback ? <FallbackNote type="fallback" /> : null}
      {hasDenied ? <FallbackNote type="denied" /> : null}
      <ProtocolStamp value={message.protocol} />
    </article>
  );
}
