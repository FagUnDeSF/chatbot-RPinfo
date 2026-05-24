import type { AssistantMessage } from "../../types/chat";
import { AssistantReceiptBubble } from "./AssistantReceiptBubble";

interface ChatBubbleAssistantInsuficienciaProps {
  message: AssistantMessage;
}

export function ChatBubbleAssistantInsuficiencia({ message }: ChatBubbleAssistantInsuficienciaProps) {
  return <AssistantReceiptBubble message={message} />;
}
