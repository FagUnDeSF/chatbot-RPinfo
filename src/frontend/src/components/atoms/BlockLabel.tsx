interface BlockLabelProps {
  children: string;
}

export function BlockLabel({ children }: BlockLabelProps) {
  return <span className="block-label">{children}</span>;
}
