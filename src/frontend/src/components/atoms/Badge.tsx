interface BadgeProps {
  children: string;
}

export function Badge({ children }: BadgeProps) {
  return <span className="badge badge--escalado">{children}</span>;
}
