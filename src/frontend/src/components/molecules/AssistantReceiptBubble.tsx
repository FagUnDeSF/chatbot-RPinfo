import type { AssistantMessage } from "../../types/chat";
import { useTypewriter } from "../../hooks/useTypewriter";
import { formatPrintedHeader } from "../../utils/format";
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

  const { visible, isTyping } = useTypewriter(message.answer);
  const printedHeader = `CONSULTA #${String(message.sequenceNumber).padStart(4, "0")} - ${formatPrintedHeader(message.timestampMs)}`;
  const isoTimestamp = new Date(message.timestampMs).toISOString();

  return (
    <article
      className={`chat-bubble chat-bubble--assistant receipt receipt--${message.variant}`}
      aria-label="Resposta do assistente"
      aria-live="polite"
    >
      {isEscalated ? <Ribbon /> : null}
      <header className="receipt__header">
        <span className="receipt__printed-header">{printedHeader}</span>
        <span className="receipt__meta">
          {isEscalated ? (
            <Tooltip label="resposta processada com modelo de maior capacidade">
              <span tabIndex={0} className="badge-trigger">
                <Badge>modelo escalado</Badge>
                <Icon name="info" />
              </span>
            </Tooltip>
          ) : null}
          <time dateTime={isoTimestamp}>{message.timestamp}</time>
        </span>
      </header>
      <p className="receipt__answer">
        {visible}
        {isTyping ? <span className="typewriter-cursor" aria-hidden="true">▍</span> : null}
      </p>
      <ReceiptDivider />
      <SourceBlock source={message.source} />
      <PremisesBlock premises={message.premises} />
      {hasFallback ? <FallbackNote type="fallback" /> : null}
      {hasDenied ? <FallbackNote type="denied" /> : null}
      <ProtocolStamp value={message.protocol} />
    </article>
  );
}
