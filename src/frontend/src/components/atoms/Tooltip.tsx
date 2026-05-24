import type { ReactNode } from "react";

interface TooltipProps {
  label: string;
  children: ReactNode;
}

export function Tooltip({ label, children }: TooltipProps) {
  return (
    <span className="tooltip">
      {children}
      <span role="tooltip" className="tooltip__panel">
        {label}
      </span>
    </span>
  );
}
