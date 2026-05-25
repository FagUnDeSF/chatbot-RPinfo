---
tipo: adr-publico
numero: "0006"
slug: stack-frontend
status: aprovado
data: 2026-05-23
publico_alvo: portfolio
---

# ADR-0006 - Stack frontend

## Contexto

O projeto precisava de uma interface interna para operador unico, consumindo o
backend FastAPI via REST, sem custo de SSR/SEO e com disciplina de testes
equivalente ao backend.

## Decisao

Adotar frontend SPA em `src/frontend/` com:

- React 18+;
- Vite 5+;
- TypeScript 5+ em modo strict;
- ESLint;
- Playwright para E2E;
- npm como gerenciador padrao;
- Node 22 LTS como runtime preferencial.

O frontend consome `/api/v1/qa/ask` e trata estados de sucesso, negativa honesta,
fallback, escalacao, PII boundary, rate limit e erros HTTP.

## Consequencias

- Mantem a UI isolada do monolito backend.
- Evita overhead de SSR para um produto interno sem necessidade de SEO.
- Exige `lint`, `typecheck`, `test:e2e` e `build` verdes antes de declarar PASS.
- Mantem reversibilidade para trocar a camada de apresentacao em sprint futura.

## Status

Aprovado no pacote Sprint 003.
