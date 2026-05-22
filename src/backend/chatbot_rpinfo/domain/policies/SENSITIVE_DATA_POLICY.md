# sensitive_data_policy — guia tecnico

Pacote: `chatbot_rpinfo.domain.policies`
Modulo: `sensitive_data_policy.py`

## O que faz

Bloqueia identificadores sensiveis em campos textuais permitidos (atualmente
`AuditQueryEventRequest.intent`). A policy levanta `SensitiveDataInTextError`
(subclasse de `ValueError`), o que faz o Pydantic devolver `422 Unprocessable
Entity` na borda HTTP. Um exception handler customizado em
`presentation/api.py` redige o valor sensivel da resposta de erro para evitar
eco do dado detectado.

Aplicada em duas camadas:

1. DTO `AuditQueryEventRequest.intent` (Pydantic `field_validator`) — rejeicao
   na borda HTTP.
2. `AuditService.record_query_event` — defense-in-depth para qualquer chamador
   interno futuro.

## Padroes detectados

| kind | regex | exemplo |
|---|---|---|
| `cpf_formatted` | `\d{3}\.\d{3}\.\d{3}-\d{2}` | `000.000.000-00` |
| `cnpj_formatted` | `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` | `00.000.000/0000-00` |
| `phone_or_whatsapp_formatted` | (DDD) + 8 ou 9 digitos com separadores | `(11) 99999-9999` |
| `rg_formatted` | `\d{1,2}\.\d{3}\.\d{3}-[\dXx]` | `12.345.678-9` |
| `numeric_identifier_run` | `\d{7,}` | `00000000000` (CPF cru) ou `5511999999999` (telefone E.164) |

## Trade-off aceito: false-positive em runs >=7 digitos legitimos

A regra `numeric_identifier_run` rejeita qualquer sequencia de **>=7 digitos
consecutivos** como possivel PII (CPF/CNPJ/RG/telefone numericos crus). Essa
regra defensiva pode gerar **false-positive teorico** para identificadores
operacionais legitimos do dominio RP Info: SKUs, numeros de NF, codigos de
produto e codigos de pedido — todos podem ter sequencias >=7 digitos.

Esse trade-off foi **aceito conscientemente pela PM na cand S2-C03 da Sprint
002** atraves do vocabulario fechado de 3 valores (`manter+documentar` /
`refinar-com-contexto-lexico` / `substituir-por-NER-leve`). Caminho escolhido:
**`manter+documentar`**.

Documento formal da decisao:
`equipe/pm-senior/decisoes/2026-05-22_TD-003-trade-off-cobertura-vs-precisao.md`.

Resumo da justificativa PM (3 argumentos):

1. Sem evidencia empirica de false-positive em uso real durante Sprint 001
   (prova controlada, volume desprezivel).
2. Regra defensiva favorece seguranca PII (CG-04) sobre precisao operacional
   durante fundacao.
3. Custo de oportunidade da Sprint 002 (10 cands + ADR-0005 + V5 + USD 30/mes);
   refinamento M-tier ou NER T-tier fragmentaria foco sem evidencia.

## Plano de revisao

Reavaliar a regra quando (qualquer um dos dois gatilhos ocorrer primeiro):

- **(a)** >=3 false-positive observados em uso real em uma janela de 30 dias
  (ex.: logs do `qa_orchestrator` registrando consultas legitimas a SKU/NF/
  codigo-pedido sendo rejeitadas com `422`), OU
- **(b)** primeira sprint pos-go-live amplo (saida da prova controlada para
  uso interno escalado).

Na revisao, considerar:

- **Opcao 2** (descartada agora): `refinar-com-contexto-lexico` — usar
  contexto lexico antes/depois da sequencia + allowlist de prefixos legitimos.
- **Opcao 3** (descartada agora): `substituir-por-NER-leve` — NER local.

## Cross-links

- Decisao PM TD-003:
  `equipe/pm-senior/decisoes/2026-05-22_TD-003-trade-off-cobertura-vs-precisao.md`.
- Divida formal de origem (secao TD-003):
  `equipe/tech-lead-senior/tech-debt/2026-05-22_sprint-001_cand-S1-C03_divida-gate-2.md`.
- Origem do codigo: cand S1-C03 Sprint 001 (commit `fbf980b` —
  `fix(audit): reject sensitive identifiers in audit intent`).
- Cand de materializacao: S2-C05 Sprint 002 (este registro).

## Estado atual

- Status TD-003: `aceito-com-documentacao` (nao "resolvido" — aceito
  conscientemente com trade-off + revisao planejada).
- BL-003 no backlog priorizado: `encerrado-via-manter+documentar` apos S2-C05
  fechar.
- Regex e suite de testes inalteradas em S2-C05 (apenas comentario + este
  documento).
