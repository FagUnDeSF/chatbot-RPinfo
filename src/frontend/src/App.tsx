import { ChatScreenTemplate } from "./components/templates/ChatScreenTemplate";
import { createDemoState } from "./fixtures/demoStates";
import { useChatController } from "./hooks/useChatController";

export function App() {
  const params = new URLSearchParams(window.location.search);
  const demoState = createDemoState(params.get("state"));
  const controller = useChatController(demoState);

  return <ChatScreenTemplate controller={controller} />;
}
