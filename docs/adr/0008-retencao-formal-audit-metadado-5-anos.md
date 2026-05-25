---
tipo: adr-publico
numero: "0008"
slug: retencao-formal-audit-metadado-5-anos
status: aprovado
data: 2026-05-23
publico_alvo: portfolio
---

# ADR-0008 - Retencao formal do audit metadado por 5 anos

## Contexto

O chatbot registra metadados de auditoria para responsabilizacao, seguranca e
diagnostico. Antes desta decisao, a retencao desses metadados nao tinha prazo
formal declarado.

## Decisao

Adotar retencao formal de 5 anos para metadados de auditoria, contados a partir
do `created_at` do evento, com purge automatizado a ser implementado em sprint
futura.

A decisao se ancora em base legal cumulativa:

- Marco Civil da Internet para registros de aplicacao;
- LGPD para responsabilizacao, prestacao de contas e eliminacao ao fim do
  tratamento;
- Codigo Civil para prazo prescricional de reparacao civil.

Suspensao de purge por ordem judicial deve ser suportada quando aplicavel.

## Consequencias

- Remove retencao indefinida implicita.
- Cria base clara para futura implementacao de job purge.
- Mantem minimizacao LGPD como restricao operacional.
- Uso B2B futuro continua condicionado a revisoes juridicas e operacionais
  adicionais.

## Status

Aprovado apos parecer LGPD especifico, com ressalvas preservadas para
implementacao futura do purge.
