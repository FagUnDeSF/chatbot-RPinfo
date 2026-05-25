---
tipologia: reference
criada_em: 2026-05-21
mantida_por: technical-writer-senior
status: proposta-kickoff
---

# Documentacao - chatbot-RPinfo

Este diretorio organiza a documentacao viva do projeto chatbot-RPinfo.

## Trilhos obrigatorios

| Trilha | Path | Tipologia Diataxis | Dono primario | Uso |
|---|---|---|---|---|
| Produto | `docs/product/` | explanation + reference | pm-senior | PRD, historias e escopo aprovado. |
| Planejamento | `docs/planning/` | reference | pm-senior | Plano de sprints e roadmap operacional. |
| ADRs | `docs/adr/` | explanation | tech-lead-senior | Decisoes tecnicas aprovadas ou propostas. |
| Runbooks | `docs/runbooks/` | how-to | technical-writer-senior + devops-senior | Procedimentos operacionais do chat. |
| Releases | `docs/releases/` | reference | pm-senior + technical-writer-senior | Notas de release por sprint no formato Keep a Changelog. |
| Manual | `docs/manual/` | tutorial + how-to | technical-writer-senior | Uso do chat por Decio, comercial e prevencao. |

## Trilhos por contexto

| Trilha | Path | Quando usar |
|---|---|---|
| Getting started | `docs/getting-started.md` | Primeiro setup local backend + frontend. |
| Arquitetura | `docs/architecture.md` | Leitura portfolio-ready da arquitetura, V5, frontend e observabilidade. |
| ADRs index | `docs/adrs-index.md` | Navegacao publica das decisoes arquiteturais aprovadas. |
| API | `docs/api/` | Quando contratos HTTP, OpenAPI ou exemplos de payload forem publicados. |
| Integracoes | `docs/integration/` | Quando o projeto documentar RP Info, planilhas de concorrencia, WhatsApp ou outras fontes externas. |
| Seguranca | `docs/security/` | Quando Security publicar threat model, controles LGPD ou politicas de auditoria. |

## Arquivos de navegacao

- `README.md` na raiz: entrada portfolio-ready do repositorio.
- `CHANGELOG.md` na raiz: entregas por sprint em formato Keep a Changelog.
- `docs/sidebar.json`: mapa mecanico para navegacao e auditoria de links.
- `docs/glossario.md`: termos de dominio e produto, mantidos pela TW em fluxo proprio.

Adicionada por `technical-writer-senior > estrutura-documental-kickoff` em 2026-05-21.
