import type { KeyboardEvent } from "react";

import { Button, Icon, QuestionTextarea } from "../atoms";

interface InputAreaProps {
  draft: string;
  isSubmitting: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => Promise<void>;
}

export function InputArea({ draft, isSubmitting, onDraftChange, onSubmit }: InputAreaProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void onSubmit();
    }
  };

  return (
    <form
      className="input-area"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit();
      }}
    >
      <QuestionTextarea
        label="Pergunta ao ChatRP Info"
        value={draft}
        placeholder="Pergunte sobre margem, ruptura, CMV, mix, giro, fornecedor, encarte..."
        disabled={isSubmitting}
        onChange={(event) => onDraftChange(event.target.value)}
        onKeyDown={handleKeyDown}
        autoFocus
      />
      <Button type="submit" disabled={isSubmitting || draft.trim().length < 3}>
        <Icon name="send" />
        Perguntar
      </Button>
    </form>
  );
}
