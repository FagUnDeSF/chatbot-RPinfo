import { BlockLabel } from "../atoms";

interface PremisesBlockProps {
  premises: readonly string[];
}

export function PremisesBlock({ premises }: PremisesBlockProps) {
  return (
    <section className="receipt-block" aria-label="Premissas da resposta">
      <BlockLabel>PREMISSAS</BlockLabel>
      <ul>
        {premises.map((premise) => (
          <li key={premise}>{premise}</li>
        ))}
      </ul>
    </section>
  );
}
