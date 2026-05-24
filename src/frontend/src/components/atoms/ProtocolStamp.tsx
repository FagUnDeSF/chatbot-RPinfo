interface ProtocolStampProps {
  value: string;
}

export function ProtocolStamp({ value }: ProtocolStampProps) {
  return (
    <span className="protocol-stamp" tabIndex={0} aria-label={`Selo de protocolo ${value}`}>
      {value}
    </span>
  );
}
