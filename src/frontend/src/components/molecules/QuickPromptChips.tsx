interface QuickPromptChipsProps {
  onPick: (value: string) => void;
}

const prompts = [
  "Margem por loja",
  "Ruptura D-1",
  "CMV semanal",
  "Giro hortifruti"
] as const;

export function QuickPromptChips({ onPick }: QuickPromptChipsProps) {
  return (
    <div className="quick-prompts" aria-label="Consultas rapidas">
      {prompts.map((prompt) => (
        <button type="button" key={prompt} onClick={() => onPick(prompt)}>
          {prompt}
        </button>
      ))}
    </div>
  );
}
