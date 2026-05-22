---
tipo: tech-debt-registry
projeto: chatbot-RPinfo
criado_em: 2026-05-22
editor_primario: pm-senior
contribuintes: qa-senior, tech-lead-senior, security-engineer-senior
---

# Tech-Debt Registry — chatbot-RPinfo

> Registro canonico de divida tecnica do projeto. Ressalvas registradas via QA `APROVADO COM RESSALVA` entram aqui antes do PM mover `Em Gate QA -> Em Gate 2`. Cada entrada exige path/secao + data-alvo + responsavel + finding original (File:line+Impact+Fix).

## Convencao de entradas

- **ID:** `TD-NNN`
- **Origem:** cand_id + gate-resultados path
- **Severity:** Critical/High/Medium/Low
- **Action:** Fix immediately / Fix before launch / Fix within sprint / Fix when convenient
- **Data-alvo:** YYYY-MM-DD
- **Responsavel:** skill autora
- **Status:** aberto | em-andamento | encerrado

---

## TD-001 — RG formatado nao coberto pela sensitive_data_policy

- **Origem:** S1-C03 / `equipe/qa-senior/gate-resultados/S1-C03.md` (re-audit 2026-05-22)
- **Severity:** High
- **Action:** Fix within sprint
- **Data-alvo:** Sprint 002 (cand-followup S1-C03-RG ou equivalente proposto pelo PM apos parecer Security/LGPD)
- **Responsavel:** backend-senior (extensao do regex) + apoio security-engineer-senior se parecer LGPD entrar no recorte
- **Status:** aberto

**Finding ancorado:**

- **File:** `src/backend/chatbot_rpinfo/domain/policies/sensitive_data_policy.py:5-17`
- **Impact:** A CG-04 da Sprint 001 lista literalmente "CPF, CNPJ, **documento**, WhatsApp, conversa ou identificador pessoal" como vetores nao-persistiveis sem parecer Security/LGPD. RG eh documento. A policy atual cobre CPF formatado, CNPJ formatado, telefone/WhatsApp formatado e runs de 7+ digitos consecutivos, mas RG no formato SP comum `dd.ddd.ddd-d` (7 digitos separados por pontos + 1 digito final separado por hifen) NAO casa nenhum dos 4 padroes. Reproducao QA 2026-05-22: `POST /api/v1/audit/query-events` com `intent="consulta RG 12.345.678-9"` retornou `201` e o RG bruto apareceu no JSON da resposta + foi persistido em `AuditEvent.intent`.
- **Fix:** Adicionar padrao `_RG_FORMATTED_RE` cobrindo `\d{1,2}\.\d{3}\.\d{3}-\d{1,2}[Xx]?` em `sensitive_data_policy.py:_PATTERNS`. Adicionar caso parametrizado em `tests/backend/test_auth_audit.py::test_query_audit_rejects_sensitive_identifiers_in_intent` com `("audit-sensitive-rg-fmt", "consulta RG 12.345.678-9")`. Considerar tambem RG sem hifen com letra `X` final (variantes regionais).

---

## TD-002 — Email nao coberto pela sensitive_data_policy

- **Origem:** S1-C03 / `equipe/qa-senior/gate-resultados/S1-C03.md` (re-audit 2026-05-22)
- **Severity:** Medium
- **Action:** Fix when convenient (Sprint 002+)
- **Data-alvo:** Sprint 002 (quitado em S2-C04 — antecipado por consolidacao de pareceres cross-skill)
- **Responsavel:** backend-senior (executora) — pareceres cross-skill obrigatorios ja emitidos
- **Status:** **encerrado** (2026-05-22 via cand S2-C04, caminho `incluir-email-na-policy`)

**Finding ancorado (preservado para historico):**

- **File:** `src/backend/chatbot_rpinfo/domain/policies/sensitive_data_policy.py:12-17`
- **Impact:** A CG-04 nao cita email literalmente, mas cita "identificador pessoal". A LGPD enquadra email como dado pessoal quando associado a pessoa natural. Reproducao QA 2026-05-22: `intent="contato joao@empresa.com.br"` retornou `201` e o email apareceu persistido. Severity rebaixada de HIGH para MEDIUM porque CG-04 nao cita literalmente; aguarda parecer Security/LGPD.
- **Fix aplicado:** Adicionado `_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")` em `_PATTERNS` (entrada `("email", _EMAIL_RE)` posicionada antes de `("numeric_identifier_run", ...)`). Suite de teste adversarial estendida com 5 variantes (canonical, plus-addressing, subdomain, exotic-TLD, uppercase). Suite atual 36 PASS, coverage 97%.

**Cross-link aos pareceres consolidados (decisao S2-C02 vocab fechado `incluir-email-na-policy`):**

- Parecer Security-Engineer-Senior: `equipe/security-engineer-senior/pareceres/2026-05-22_TD-002-email-audit-log.md` (veredito `aprovada-seguranca`).
- Parecer Security-LGPD: `equipe/security-lgpd/pareceres/2026-05-22_TD-002-email-audit-log.md` (veredito `CONFORME COM RESSALVA`; ressalva fechada pelos 4 criterios objetivos do §6.3 do parecer).
- Commit + SHA da quitacao: ver `equipe/backend-senior/execucoes/2026-05-22_commits-S2-C04.md`.
- Pack-F (entregavel + handoff): `equipe/pm-senior/prompt-packs/sprint-002/pack-F.md`.

---

## TD-003 — False-positive em runs de 7+ digitos legitimos (SKU, ID de pedido)

- **Origem:** S1-C03 / `equipe/qa-senior/gate-resultados/S1-C03.md` (re-audit 2026-05-22)
- **Severity:** Medium
- **Action:** Fix when convenient (Sprint 002+ se houver demanda de produto)
- **Data-alvo:** Sprint 003 OR quando primeira consulta legitima for bloqueada em uso real
- **Responsavel:** backend-senior + apoio pm-senior para decisao produto
- **Status:** aberto

**Finding ancorado:**

- **File:** `src/backend/chatbot_rpinfo/domain/policies/sensitive_data_policy.py:10` (`_DIGIT_RUN_RE = re.compile(r"\d{7,}")`)
- **Impact:** O padrao defensivo de bloquear runs >=7 digitos consecutivos eh conservador e tambem bloqueia identificadores legitimos do dominio (SKU >=7 digitos, ID de pedido, codigo de barras EAN-13, codigo de NF). Reproducao QA 2026-05-22: `intent="consulta SKU 12345678 em estoque"` retornou `422` apesar de NAO conter identificador pessoal. Bloquear consulta legitima por excesso de cautela degrada UX da auditoria. Severity MEDIUM porque (a) defense-in-depth deliberado, (b) sem incidente real ainda, (c) reescrita do `intent` resolve sem perda funcional.
- **Fix:** Decisao produto: (a) manter regex agressiva + documentar no contexto-projeto pm-senior §1.5 que `intent` nao deve conter codigos numericos longos; OR (b) refinar regex com contexto lexico (palavra "CPF"/"CNPJ"/"telefone" proxima ao run); OR (c) substituir por named-entity-recognition leve. Decisao PM antes de implementar.

---

## Historico

- 2026-05-22 — Registry criado por qa-senior na re-audit de S1-C03 (TD-001/002/003 abertos como ressalvas do veredito APROVADO COM RESSALVA).
- 2026-05-22 — TD-002 encerrado por backend-senior via cand S2-C04 Sprint 002 (caminho `incluir-email-na-policy` consolidado entre Security-Engineer + Security-LGPD). Cross-link aos 2 pareceres + commit SHA via `equipe/backend-senior/execucoes/2026-05-22_commits-S2-C04.md`.
