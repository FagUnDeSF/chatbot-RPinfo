---
tipo: adr-publico
numero: "0004"
slug: hospedagem-ci-observabilidade-kickoff
status: aprovado
data: 2026-05-20
publico_alvo: portfolio
---

# ADR-0004 - Hospedagem, CI e observabilidade de kickoff

## Contexto

O projeto precisa ser reproduzivel e seguro antes de uma decisao definitiva de
provedor, SLA ou residencia de dados. O repositorio pode ser publico, entao
segredos, dumps e amostras sensiveis devem ficar fora dele.

## Decisao

Adotar containerizacao simples para a aplicacao Python, CI em GitHub Actions,
secrets fora do repositorio, separacao minima entre `dev` e `staging`, e logs
estruturados JSON com redacao de dados sensiveis.

Sub-decisoes:

- provedor gerenciado final fica pendente ate decisao operacional;
- GitHub Actions e o default de CI;
- checks devem cobrir lint, typecheck, testes e higiene de secrets;
- logs estruturados devem incluir correlation id e flags de fonte/insuficiencia.

## Consequencias

- Mantem o projeto deployavel sem escolher cloud prematuramente.
- Reduz risco de vazamento em repositorio publico.
- Cria base para DevOps e Security refinarem esteira, monitoramento e deploy.
- Provedor final, custo recorrente e topologia de producao seguem pendentes.

## Status

Aprovado como ADR de fundacao.
