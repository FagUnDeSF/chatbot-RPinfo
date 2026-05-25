---
tipo: adr-publico
numero: "0005"
slug: llm-provider
status: aprovado
data: 2026-05-22
publico_alvo: portfolio
---

# ADR-0005 - LLM provider

## Contexto

O chatbot evoluiu de stub deterministico para uso de LLM real. A decisao precisava
controlar custo, latencia, governanca LGPD e falhas de modelo sem criar fallback
silencioso entre modelos.

## Decisao

Adotar Anthropic Claude Haiku 4.5 como modelo padrao e Sonnet 4.5 apenas por
escalacao explicita. O budget mensal inicial para LLM e USD 30.

Regras principais:

- nao ha fallback silencioso de Haiku para Sonnet;
- falha do provider retorna insuficiencia, fallback deterministico ou erro
  explicito;
- chamadas LLM registram metadados de auditoria, custo e latencia;
- dados pessoais devem ser bloqueados ou redigidos antes de chegar ao LLM;
- uso B2B futuro exige nova camada juridica e operacional.

## Consequencias

- Permite demonstrar IA real sem perder controle de custo.
- Mantem a experiencia honesta quando o modelo ou os dados nao sustentam
  resposta.
- Exige monitoramento de budget, cache, latencia e taxa de fallback.
- Mantem ressalvas LGPD visiveis para fases futuras.

## Status

Aprovado apos parecer LGPD com ressalvas absorvidas para a Fase 1.
