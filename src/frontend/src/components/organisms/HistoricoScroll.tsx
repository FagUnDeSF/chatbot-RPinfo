import type { ChatController } from "../../types/chat";
import {
  AssistantReceiptBubble,
  ChatBubbleAssistantAttention,
  ChatBubbleAssistantInsuficiencia,
  ChatBubbleAssistantLoading,
  ChatBubbleUser
} from "../molecules";

interface HistoricoScrollProps {
  controller: ChatController;
}

export function HistoricoScroll({ controller }: HistoricoScrollProps) {
  return (
    <main className="history-scroll" aria-label="Historico da consulta">
      <div className="history-scroll__inner">
        {controller.messages.map((message) => {
          if (message.kind === "user") return <ChatBubbleUser key={message.id} message={message} />;
          if (message.kind === "loading") {
            return (
              <ChatBubbleAssistantLoading
                key={message.id}
                startedAt={message.startedAt}
                onCancel={controller.cancel}
              />
            );
          }
          if (message.kind === "attention") {
            return (
              <ChatBubbleAssistantAttention
                key={message.id}
                message={message}
                onRetry={controller.retry}
                onReformulate={controller.reformulate}
              />
            );
          }
          if (message.variant === "insufficient") {
            return <ChatBubbleAssistantInsuficiencia key={message.id} message={message} />;
          }
          return <AssistantReceiptBubble key={message.id} message={message} />;
        })}
      </div>
    </main>
  );
}
