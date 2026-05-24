interface StatusDotProps {
  tone?: "online" | "warning" | "offline";
}

export function StatusDot({ tone = "online" }: StatusDotProps) {
  return <span className={`status-dot status-dot--${tone}`} aria-hidden="true" />;
}
