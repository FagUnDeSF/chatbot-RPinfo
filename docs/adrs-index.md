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
canonica continua em `equipe/tech-lead-senior/adrs/`; este arquivo e a trilha de
leitura para portfolio.

| ADR | Status | Tema | Por que importa | Link |
|---|---|---|---|---|
| 0001 | aprovado | Arquitetura da aplicacao IA read-only sobre ERP | Define Python 3.12, FastAPI, Pydantic v2 e monolito modular. | [0001](../equipe/tech-lead-senior/adrs/0001-arquitetura-aplicacao-ia-readonly-erp.md) |
| 0002 | aprovado | Acesso ERP read-only e acuracia | Garante que o ERP RP Info segue fonte primaria e que a aplicacao nao escreve no ERP. | [0002](../equipe/tech-lead-senior/adrs/0002-acesso-dados-erp-readonly-acuracia.md) |
| 0003 | aprovado | Seguranca, autenticacao, LGPD e auditoria | Fixa contas nominativas, RBAC e auditoria sem payload sensivel bruto. | [0003](../equipe/tech-lead-senior/adrs/0003-seguranca-autenticacao-lgpd-auditoria.md) |
| 0004 | aprovado | Hospedagem, CI e observabilidade de kickoff | Define defaults de container, GitHub Actions, secrets fora do repo e logs estruturados. | [0004](../equipe/tech-lead-senior/adrs/0004-hospedagem-ci-observabilidade-kickoff.md) |
| 0005 | aprovado | LLM provider | Decide Haiku 4.5 padrao, Sonnet 4.5 opt-in, budget USD 30 e fallback matrix. | [0005](../equipe/tech-lead-senior/adrs/0005-llm-provider.md) |
| 0006 | aprovado | Stack frontend | Decide React 18 + Vite + TypeScript + Playwright em `src/frontend/`. | [0006](../equipe/tech-lead-senior/adrs/0006-stack-frontend.md) |
| 0007 | aprovado | Alerta `monitorar-custo-llm` | Promove observabilidade LLM para runtime com cron, relatorios e canal de alerta. | [0007](../equipe/tech-lead-senior/adrs/0007-promocao-alerta-monitorar-custo-llm.md) |
| 0008 | aprovado | Retencao audit 5 anos | Formaliza retencao de audit metadado, base legal cumulativa e purge futuro. | [0008](../equipe/tech-lead-senior/adrs/0008-retencao-formal-audit-metadado-5-anos.md) |

## Leitura sugerida

1. Leia ADR-0001 e ADR-0002 para entender por que o projeto e read-only.
2. Leia ADR-0003 antes de avaliar qualquer log, token ou dado pessoal.
3. Leia ADR-0005 junto com `equipe/ai-engineer-senior/guarda-em-camadas-V5.md`
   para entender a promocao a LLM real.
4. Leia ADR-0006 se o foco for frontend e DX.
5. Leia ADR-0007 e ADR-0008 para governanca operacional e compliance.

## Pareceres relacionados

- LGPD ADR-0005: `equipe/security-lgpd/pareceres/2026-05-22_parecer-lgpd-adr-0005-llm.md`
- LGPD Fase 1 v1: `equipe/security-lgpd/pareceres/2026-05-22_parecer-lgpd-fase-1-uso-proprio.md`
- LGPD Fase 1 v2: `equipe/security-lgpd/pareceres/2026-05-22_parecer-lgpd-fase-1-uso-proprio-rev2.md`
- LGPD ADR-0008: `equipe/security-lgpd/pareceres/2026-05-23_parecer-lgpd-adr-0008-retencao-audit-5-anos.md`

## Nota de publicacao

Este indice e portfolio-friendly, mas a publicacao publica final depende do
security review S3-C11. Se S3-C11 recomendar retirar `equipe/**` do GitHub
publico, os links internos deste arquivo devem ser ajustados para espelhos
publicos ou resumos em `docs/`.
