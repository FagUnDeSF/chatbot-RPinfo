interface InitialHintProps {
  hint: string;
}

export function InitialHint({ hint }: InitialHintProps) {
  return <p className="initial-hint">{hint}</p>;
}
