import { StatusDot } from "../atoms";
import { MetadataStrip } from "../molecules";

interface HeaderProps {
  statusLabel: string;
}

export function Header({ statusLabel }: HeaderProps) {
  return (
    <header className="app-header">
      <div>
        <h1>ChatRP Info</h1>
        <MetadataStrip />
      </div>
      <p className="header-status" aria-label={statusLabel}>
        <StatusDot />
        {statusLabel}
      </p>
    </header>
  );
}
