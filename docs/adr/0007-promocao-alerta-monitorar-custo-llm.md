---
tipo: adr-publico
numero: "0007"
slug: promocao-alerta-monitorar-custo-llm
status: aprovado
data: 2026-05-23
publico_alvo: portfolio
---

# ADR-0007 - Promocao do alerta monitorar-custo-llm a runtime de producao

## Contexto

Com LLM real e budget mensal definido, o projeto precisava transformar o alerta
de custo LLM de configuracao versionada em rotina operacional. Sem isso,
anomalias de custo, latencia, cache ou fallback seriam descobertas tarde.

## Decisao

Promover o alerta `monitorar-custo-llm` para runtime operacional, com:

- execucao continuous a cada 15 minutos;
- relatorio weekly trend;
- relatorio monthly deep-dive;
- thresholds versionados;
- canal humano de alerta;
- recomendacoes em vocabulario fechado;
- plano de reversao para desabilitar a rotina sem perder configuracao.

O alerta nao executa fallback automatico de modelo e nao altera comportamento de
produto sozinho.

## Consequencias

- Da visibilidade proativa ao budget de USD 30/mes.
- Preserva a regra anti-fallback-silencioso.
- Mantem reversibilidade se o alerta gerar ruido operacional.
- Exige validacao empirica do caminho end-to-end antes de declarar operacao
  estavel.

## Status

Aprovado no pacote Sprint 003.
