---
tipologia: reference
sprint_id: "001-003"
data_release: 2026-05-25
publico_alvo: portfolio
mantida_por: technical-writer-senior
formato: keep-a-changelog
---

# Changelog

Formato inspirado em Keep a Changelog. Este arquivo resume entregas por sprint
para leitura externa; os detalhes completos continuam nos artefatos de PM, TL,
QA e demais skills.

## Sprint 003 - Interface chat, governanca operacional e portfolio

### Added

- Interface React + Vite + TypeScript em `src/frontend/`, com estados de chat,
  tratamento de headers `X-LLM-*`, erros 422/403/500 e testes Playwright.
- ADR-0006 para a stack frontend.
- ADR-0007 para promover `monitorar-custo-llm` a runtime de producao com cron,
  relatorios e canal de alerta.
- ADR-0008 para retencao formal de audit metadado por 5 anos.
- Documentacao portfolio-ready: README, getting-started, arquitetura, changelog
  e indice navegavel de ADRs.

### Changed

- S3-C02 fechou com aprovacao Gate 2 PM em 2026-05-25, mantendo ressalva de
  validacao NVDA humana reagendada para Sprint 004+.
- O alerta LLM deixou de ser apenas configurado e entrou em trilha formal de
  runtime real via S3-C04.

### Security

- CG-10 exige security review S3-C11 antes de publicacao publica do portfolio.
- A Fase 2 B2B segue bloqueada por pre-requisitos LGPD e contratuais.

## Sprint 002 - LLM real, observabilidade e educacional

### Added

- Claude Haiku 4.5 como modelo padrao do `qa_orchestrator`, com Sonnet 4.5
  apenas por escalacao opt-in.
- ADR-0005 para provider LLM, budget mensal USD 30, cache target e fallback
  matrix.
- V5 guarda-em-camadas do NIVEL-0 ao NIVEL-5, incluindo PII boundary,
  content policy, audit de 19 campos e anti-fallback-silencioso.
- Observabilidade LLM com cinco thresholds e templates de relatorio.
- Materiais didaticos de AI Engineering e ML Engineering em `case-study/`.
- Spike ML para eval continuo, drift detection, retraining triggers e canary.

### Changed

- O projeto saiu do stub deterministico puro e materializou LLM real em Fase 1,
  com eval golden real 2/2 PASS e custo observado de aproximadamente USD
  0.00103 por chamada.
- O processo passou a exigir output literal de testes apos a QA detectar
  declaracao de PASS sem execucao em uma entrega intermediaria.

### Security

- Pareceres LGPD Fase 1 v1 e v2 liberaram uso proprio com ressalvas e
  mantiveram bloqueio formal da Fase 2 B2B.
- Bloqueio Fase 2 foi reafirmado nos artefatos de LLM, observabilidade e
  materiais didaticos.

## Sprint 001 - Fundacao read-only e prova controlada

### Added

- Backend FastAPI/Python 3.12 com Pydantic v2.
- Camada `erp_readonly` com allowlist, timeout, limite de linhas e fonte
  declarada.
- Auth interna, RBAC por perfil e auditoria sem payload sensivel bruto.
- Orquestrador Q&A inicial com stub deterministico, resposta com fonte/premissas
  e negativa honesta.
- Harness de acuracia para estoque/margem com hashes deterministicos.
- ADRs 0001 a 0004 cobrindo arquitetura, dados ERP read-only, seguranca e
  hospedagem/CI/observabilidade de kickoff.

### Fixed

- QA identificou lacunas na policy de dados sensiveis em S1-C03; backend
  corrigiu o caso bloqueante e a re-auditoria aprovou com ressalva.

### Security

- Nenhuma rotina automatizada ganhou permissao de escrita no ERP.
- Persistencia de dado pessoal ficou bloqueada sem parecer Security/LGPD.
- LLM real foi explicitamente condicionado a ADR, V5 e parecer LGPD futuros.

## Referencias

- Retro Sprint 001: `equipe/pm-senior/retros/retro-sprint-001.md`
- Retro Sprint 002: `equipe/pm-senior/retros/retro-sprint-002.md`
- Sprint 003: `equipe/pm-senior/sprints/sprint-003.md`
- Controle Sprint 003: `equipe/pm-senior/controle-cands/sprint-003.md`
