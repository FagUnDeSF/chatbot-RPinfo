export function formatTime(date = new Date()): string {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function formatPrintedHeader(timestampMs: number): string {
  const date = new Date(timestampMs);
  const yyyy = String(date.getFullYear());
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

export function createProtocol(date = new Date()): string {
  const stamp = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
    String(date.getHours()).padStart(2, "0"),
    String(date.getMinutes()).padStart(2, "0")
  ].join("");
  const suffix = Math.random().toString(36).slice(2, 7).toUpperCase();
  return `PROTOCOLO ${stamp} - ${suffix}`;
}

export function rowsToAnswer(rows: readonly Record<string, string | number | boolean | null>[]): string {
  if (rows.length === 0) {
    return "Nao tenho dado suficiente para responder com seguranca.";
  }
  const first = rows[0];
  const pairs = Object.entries(first)
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${String(value)}`);
  return `Consulta retornou ${String(rows.length)} linha(s). ${pairs.join(" | ")}.`;
}
