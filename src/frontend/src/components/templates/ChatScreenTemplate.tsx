import type { ChatController } from "../../types/chat";
import { FooterDiscreto, Header, HistoricoScroll, InputComposer } from "../organisms";

interface ChatScreenTemplateProps {
  controller: ChatController;
}

export function ChatScreenTemplate({ controller }: ChatScreenTemplateProps) {
  return (
    <div className="app-shell">
      <Header statusLabel={controller.statusLabel} />
      <HistoricoScroll controller={controller} />
      <InputComposer controller={controller} />
      <FooterDiscreto />
    </div>
  );
}
