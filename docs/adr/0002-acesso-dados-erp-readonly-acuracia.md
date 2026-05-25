---
tipo: adr-publico
numero: "0002"
slug: acesso-dados-erp-readonly-acuracia
status: aprovado
data: 2026-05-20
publico_alvo: portfolio
---

# ADR-0002 - Acesso a dados ERP em modo read-only e validacao de acuracia

## Contexto

O ERP RP Info e a fonte operacional primaria. O chatbot deve consultar dados
operacionais sem automatizar escrita e sem transformar hipoteses de analise em
promessa de acuracia antes de conferencia oficial.

## Decisao

Todo acesso ao ERP passa por uma camada obrigatoria `erp_readonly`, com:

- usuario read-only dedicado quando disponivel;
- wrapper que force transacao read-only quando necessario;
- lista positiva de consultas;
- timeout;
- limite de linhas;
- trilha de auditoria.

Persistencia propria, quando existir, guarda apenas metadados tecnicos, historico
permitido e cache controlado. Qualquer dado pessoal exige parecer Security/LGPD.

## Consequencias

- Reduz risco de dano operacional no ERP.
- Torna a negativa honesta tecnicamente verificavel.
- Mantem regras de estoque, margem e demais analises como hipoteses ate
  comparacao com relatorios oficiais.
- Escrita automatizada no ERP fica proibida sem novo ADR e nova aprovacao.

## Status

Aprovado como ADR de fundacao.
