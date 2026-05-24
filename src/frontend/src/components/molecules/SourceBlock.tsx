import { BlockLabel } from "../atoms";

interface SourceBlockProps {
  source: string;
}

export function SourceBlock({ source }: SourceBlockProps) {
  return (
    <section className="receipt-block" aria-label="Fonte da resposta">
      <BlockLabel>FONTE</BlockLabel>
      <p>{source}</p>
    </section>
  );
}
