import type { ChatController } from "../../types/chat";
import { InitialHint, InputArea, QuickPromptChips } from "../molecules";

interface InputComposerProps {
  controller: ChatController;
}

export function InputComposer({ controller }: InputComposerProps) {
  return (
    <section className="input-composer" aria-label="Nova pergunta">
      {controller.messages.length === 0 ? <InitialHint hint={controller.hint} /> : null}
      <InputArea
        draft={controller.draft}
        isSubmitting={controller.isSubmitting}
        onDraftChange={controller.setDraft}
        onSubmit={controller.submit}
      />
      <QuickPromptChips onPick={controller.setDraft} />
    </section>
  );
}
