const BUILD_VERSION =
  (import.meta.env.VITE_BUILD_VERSION as string | undefined) ?? "v0.1.0";

export function FooterDiscreto() {
  return (
    <footer className="footer-discreto">
      <div className="footer-discreto__lines">
        <p>(c) Rede Fagundes - uso interno - nao compartilhar fora da direcao</p>
        <p>turno NOITE - loja-mae 01 (sede) - build {BUILD_VERSION}</p>
      </div>
      <a href="mailto:suporte@rpinfo.local">suporte operacional</a>
    </footer>
  );
}
