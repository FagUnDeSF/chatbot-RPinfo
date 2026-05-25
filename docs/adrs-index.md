---
tipologia: reference
sprint_id: "003"
data_release: 2026-05-25
publico_alvo: portfolio
mantida_por: technical-writer-senior
formato: adr-index
---

# ADRs index

Indice navegavel das decisoes arquiteturais aprovadas do projeto. A fonte
canonica operacional continua na sala do Tech Lead; os arquivos abaixo sao
espelhos publicos sanitizados para portfolio.

| ADR | Status | Tema | Por que importa | Link |
|---|---|---|---|---|
| 0001 | aprovado | Arquitetura da aplicacao IA read-only sobre ERP | Define Python 3.12, FastAPI, Pydantic v2 e monolito modular. | [0001](adr/0001-arquitetura-aplicacao-ia-readonly-erp.md) |
| 0002 | aprovado | Acesso ERP read-only e acuracia | Garante que o ERP RP Info segue fonte primaria e que a aplicacao nao escreve no ERP. | [0002](adr/0002-acesso-dados-erp-readonly-acuracia.md) |
| 0003 | aprovado | Seguranca, autenticacao, LGPD e auditoria | Fixa contas nominativas, RBAC e auditoria sem payload sensivel bruto. | [0003](adr/0003-seguranca-autenticacao-lgpd-auditoria.md) |
| 0004 | aprovado | Hospedagem, CI e observabilidade de kickoff | Define defaults de container, GitHub Actions, secrets fora do repo e logs estruturados. | [0004](adr/0004-hospedagem-ci-observabilidade-kickoff.md) |
| 0005 | aprovado | LLM provider | Decide Haiku 4.5 padrao, Sonnet 4.5 opt-in, budget USD 30 e fallback matrix. | [0005](adr/0005-llm-provider.md) |
| 0006 | aprovado | Stack frontend | Decide React 18 + Vite + TypeScript + Playwright em `src/frontend/`. | [0006](adr/0006-stack-frontend.md) |
| 0007 | aprovado | Alerta `monitorar-custo-llm` | Promove observabilidade LLM para runtime com cron, relatorios e canal de alerta. | [0007](adr/0007-promocao-alerta-monitorar-custo-llm.md) |
| 0008 | aprovado | Retencao audit 5 anos | Formaliza retencao de audit metadado, base legal cumulativa e purge futuro. | [0008](adr/0008-retencao-formal-audit-metadado-5-anos.md) |

## Leitura sugerida

1. Leia ADR-0001 e ADR-0002 para entender por que o projeto e read-only.
2. Leia ADR-0003 antes de avaliar qualquer log, token ou dado pessoal.
3. Leia ADR-0005 junto com [Architecture](architecture.md) para entender a
   promocao a LLM real e a V5 guarda-em-camadas.
4. Leia ADR-0006 se o foco for frontend e DX.
5. Leia ADR-0007 e ADR-0008 para governanca operacional e compliance.

## Evidencias relacionadas

- ADR-0005 foi aprovado apos parecer LGPD com ressalvas absorvidas para a Fase 1.
- ADR-0006 e ADR-0007 foram aprovados no pacote Sprint 003.
- ADR-0008 foi aprovado apos parecer LGPD especifico sobre retencao de audit
  metadado.

## Nota de publicacao

S3-C11 definiu a arvore publica aprovada. Por isso este indice aponta apenas
para espelhos publicos sanitizados em `docs/adr/`.
