interface FallbackNoteProps {
  type: "fallback" | "denied";
}

export function FallbackNote({ type }: FallbackNoteProps) {
  const copy =
    type === "fallback"
      ? "resposta gerada por modelo alternativo (degradacao registrada)"
      : "escalacao solicitada nao foi aplicada - resposta no modelo padrao";

  return <p className="fallback-note">{copy}</p>;
}
