---
tipo: adr-publico
numero: "0001"
slug: arquitetura-aplicacao-ia-readonly-erp
status: aprovado
data: 2026-05-20
publico_alvo: portfolio
---

# ADR-0001 - Arquitetura da aplicacao IA read-only sobre ERP RP Info

## Contexto

O projeto nasce como chat interno com IA sobre dados do ERP RP Info, com
perguntas livres, fonte declarada e negativa honesta quando o dado nao sustenta
a resposta. A decisao precisa favorecer consulta segura, testes incrementais e
isolamento entre regras de dominio, conectores ERP, IA, autenticacao e auditoria.

## Decisao

Adotar monolito modular em Python 3.12 com FastAPI 0.115 e Pydantic v2 como
nucleo da aplicacao.

Limites internos principais:

- `erp_readonly`
- `analytics`
- `ai_orchestration`
- `auth_access`
- `audit`
- `ui_api`

A camada IA opera como orquestrador controlado: toda resposta deve citar a fonte
consultada ou declarar insuficiencia de dado.

## Consequencias

- Reduz coordenacao operacional no inicio.
- Favorece testes de query, acuracia e respostas deterministicas.
- Mantem a arquitetura reversivel para evoluir a camada de apresentacao sem
  reescrever o backend.
- Exige disciplina de tipos, contratos e testes para evitar drift em regras de
  negocio.

## Status

Aprovado como ADR de fundacao.
