---
tipo: memory-shared
projeto: chatbot-RPinfo
criado_em: 2026-05-22
atualizado_em: 2026-05-22
editores: pm-senior, tech-lead-senior, diretor-pleno
origem: pre-requisito Sprint 002 (guard-rail Direcao 2026-05-22)
---

# SHARED.md - decisoes cross-sprint do projeto chatbot-RPinfo

> Memoria institucional viva do projeto. Cada decisao cross-sprint que afeta multiplas skills ou multiplos cics aqui. Read-if-exists em metodos PM/TL/QA/executoras.

## Decisoes Sprint 001 (consolidadas no fechamento G6)

### D-001 - Caminho B (TL Code-Review seletivo)

**Data:** 2026-05-21.

**Contexto:** Pack canonico declara `tl_review_required: sim|nao` por cand. PM decide na emissao do pack baseado em 3 criterios canonicos (`toca-arquitetura` / `define-padrao` / `mudanca-grande`) + AP-6 (cand sensivel auth/secret/PII/migration/contrato-externo forca `sim`).

**Decisao:** Caminho B substitui Caminho A (TL revisa tudo). Aplicado integralmente a partir da Sprint 001.

**Aprendizado pos-S001 (vide retro veredicto P3):** AP-6 atual usa vocab fechado por keyword no criterio literal — escapou em S1-C03 que tocava superficie sensivel (auth/audit/PII em intent) mas nao tinha keyword exata. Emenda planejada Sprint 002 (BL-008): classificar por contexto-projeto §1.7 Security + intencao, nao so keywords.

### D-002 - Sprint 001 fechada com 1 aprovado-com-ressalva (S1-C03)

**Data G6:** 2026-05-22.

**Contexto:** S1-C03 (auth/RBAC/auditoria) entregue com bug original corrigido + 3 dividas adjacentes detectadas pela QA na lente Security ampliada.

**Decisao:** AP-5 emitir-pack (aprovar-silenciando-lacuna) evitado via aprovado-com-ressalva + divida formal canonica. Dividas TD-001 High (RG-SP), TD-002 Medium (email), TD-003 Medium (false-positive) em `equipe/tech-lead-senior/tech-debt/2026-05-22_sprint-001_cand-S1-C03_divida-gate-2.md` + `tech-debt.md` raiz.

### D-003 - Spike S1-SPK-05 entregue via apenas-harness-margem-inconclusiva

**Data:** 2026-05-22.

**Contexto:** Criterio literal de S1-C05 (sprint-doc linha 166) admite explicitamente entrega apenas-harness com margem inconclusiva quando relatorio oficial RP Info indisponivel. Direcao nao disponibilizou relatorio durante a Sprint 001.

**Decisao:** Veredicto da margem registrado `inconclusiva` ate Direcao disponibilizar relatorio. Reexecucao do harness e trivial via `--relatorio-oficial-path <path>` (BL-006 aguardando Direcao).

### D-004 - Provider LLM em S001: stub-deterministico (zero custo, zero risco)

**Data:** 2026-05-21.

**Contexto:** S1-C04 entregue com provider stub-deterministico (cost=0, latency_p95<50ms, sem alucinacao por construcao) por ser prova controlada.

**Decisao:** Promocao a LLM real (Claude Haiku 4.5 ou equivalente) exige fronteira F-FUT-1: ADR-LLM novo + V5 `ai-engineer-senior > guarda-em-camadas` + parecer Security/LGPD se PII entrar no recorte. Planejado Sprint 002 (BL-004/BL-005).

### D-005 - Sprint 002 aprovada-direcao-parcial (G3 + parecer LGPD)

**Data:** 2026-05-22.

**Contexto:** Apos Gate 1 TL consolidar 10/10 aprovada-tecnicamente, Direcao carimbou G3 sprint plan e autorizou parecer LGPD do ADR-0005 em `aprovacoes/sprint-002.md`. G2 do ADR-0005 LLM ficou PENDENTE - Direcao solicitou estimativa comparativa Sonnet/Haiku/GPT-4o-mini do ai-engineer-senior para finalizar o projeto antes de aprovar provider + orcamento USD.

**Decisao:** Lote 1 parcial liberado (S2-C01 + S2-C02 + S2-C03 sem S2-C06). S2-C06 fica em `Em parecer Direcao` aguardando estimativa AI + carimbo G2 ADR-0005. S2-C07/C08/C09/C10 bloqueadas em cadeia.

**Handoff consultivo emitido:** `handoffs/2026-05-22_pm-senior_para_ai-engineer-senior_estimativa-custo-llm-comparativa-sprint-002.md` pedindo analise comparativa 3 providers x 3 cenarios de volume + recomendacao tecnica + cross-link inv 189 LGPD (transferencia internacional Art. 46).

### D-005b - G2 ADR-0005 carimbado: Haiku 4.5 padrao + Sonnet 4.5 escalation opt-in + USD 30/mes

**Data:** 2026-05-22.

**Contexto:** AI engineer-senior entregou parecer comparativo Sonnet/Haiku/GPT-4o-mini em `equipe/ai-engineer-senior/pareceres/2026-05-22_estimativa-custo-llm-sonnet-haiku-gpt4omini.md`. Recomendacao tecnica: Haiku 4.5 padrao + Sonnet 4.5 escalation opt-in (AP-2 categoria especifica LLM CRITICAL impede fallback silencioso cross-modelo).

**Decisao Direcao consolidada:**

| Item | Valor decidido |
|---|---|
| Provider | Anthropic (Claude family) |
| Modelo padrao | Claude Haiku 4.5 |
| Modelo escalation opt-in | Claude Sonnet 4.5 (NAO fallback silencioso - exige sinal explicito + gate eval) |
| Orcamento mensal | USD 30/mes |
| Threshold cache target | >= 70% (alerta amarelo < 60%) |
| Validade da estimativa | 90 dias (revisar 2026-08-22) |

**Trecho literal Direcao:** "Vou colocar um total de U$30.00 na api do claude, esse vai ser o orçamento mensal para esse projeto na parte de llm utilizando haiku + Sonnet"

**Implicacao operacional:**
- TL fixa Haiku 4.5 padrao no ADR-0005 (S2-C06).
- Sonnet 4.5 declarado no ADR-0005 como escalation opt-in.
- USD 30/mes vira `cost-absoluto-budget-violado` threshold em S2-C08.
- DPA Anthropic Enterprise eh acao Direcao/Comercial - prerequisito de S2-C07.

### D-007 - TD-003 decidida via `manter+documentar` (Sprint 002 S2-C03)

**Data:** 2026-05-22.

**Contexto:** PM auto-executou S2-C03 conforme pack-C. Trade-off cobertura-vs-precisao em runs >=7 digitos legitimos (TD-003 Medium origem S1-C03) decidido em vocabulario fechado 3 valores.

**Decisao:** caminho `manter+documentar`. Justificativa em `equipe/pm-senior/decisoes/2026-05-22_TD-003-trade-off-cobertura-vs-precisao.md`:

1. Sem evidencia empirica de false-positive em uso real S001 (volume desprezivel em prova controlada).
2. Regra defensiva favorece seguranca PII sobre precisao operacional - trade-off correto durante fundacao.
3. Custo de oportunidade: Sprint 002 com 10 cands incluindo promocao LLM real + USD 30/mes budget + 2 didaticas; refinamento M-tier ou NER T-tier fragmentaria foco sem evidencia.

**Encaminhamento:** S2-C05 destravada com caminho `manter+documentar` -> P leve (apenas comentario em codigo + nota README; sem alteracao de regex/testes).

**Plano de revisao (gatilho):** primeira ocorrencia entre (a) false-positive em uso real (>=3 chamadas em 30 dias com intent contendo run >=7 digitos legitimo rejeitado por 422) OR (b) primeira sprint pos-go-live amplo.

**Status TD-003:** `aceito-com-documentacao` (nao "resolvido" - eh aceito conscientemente com trade-off).
**Status BL-003 backlog:** `encerrado-via-manter+documentar`.

### D-008 - TD-002 decidida via `incluir-email-na-policy` (consolidacao S2-C02)

**Data:** 2026-05-22.

**Contexto:** Pareceres cross-skill emitidos em paralelo (CG-09) por security-engineer-senior + security-lgpd sobre TD-002 email em audit log.

**Decisao consolidada (100% alinhamento entre as 2 skills):** `incluir-email-na-policy`.

**Pareceres:**
- security-engineer-senior: veredito `aprovada-seguranca` + decisao `incluir-email-na-policy` (path: `equipe/security-engineer-senior/pareceres/2026-05-22_TD-002-email-audit-log.md`). Caminho `excluir-email-motivado` avaliado em steelman formal e rejeitado por 7 eixos tecnicos.
- security-lgpd: veredito `CONFORME COM RESSALVA` + decisao `incluir-email-na-policy` (path: `equipe/security-lgpd/pareceres/2026-05-22_TD-002-email-audit-log.md`). Fundamentacao: email = dado pessoal Art. 5 I LGPD; persistir excede minimo necessario Art. 6 III; alternativa falha 3 de 4 filtros do No-Workarounds-Gate. Ressalva fecha quando S2-C04 implementa regex + teste adversarial.

**Implicacao operacional:**
- S2-C02 Encerrada.
- S2-C04 destravada -> Pack F emitido para backend-senior com C-MUST-DO consolidado (regex `_EMAIL_RE` + teste parametrizado >=4 variantes + suite >=24 PASS + tech-debt TD-002 status encerrado).
- TD-002 status pos-Gate 2 da S2-C04: `encerrado` (sai do tech-debt vivo).
- BL-002 backlog status `em-execucao-com-decisao-consolidada` ate Gate 2 S2-C04 fechar.

### D-009 - Sprint 002 Lote 1 retornos consolidados (estado intermediario)

**Data:** 2026-05-22.

**Contexto:** 6 retornos Lote 1 processados em batch pela PM.

| Cand | Estado pos-batch |
|---|---|
| S2-C01 | Em Gate QA (backend 31 PASS cov 97% + 4 vetores RG-SP) |
| S2-C02 | Encerrada (pareceres SE + LGPD 100% alinhados) |
| S2-C03 | Encerrada (decisao PM manter+documentar - D-007) |
| S2-C04 | Em execucao backend-senior (Pack F caminho incluir-email-na-policy) |
| S2-C05 | Em Gate QA (backend 27 PASS P leve documental) |
| S2-C06 | Parcialmente entregue - 3 pendencias: parecer LGPD ADR-0005 + V5 cross-security + DPA Anthropic Enterprise |

**ADR-0005 status:** `proposto` (decisao tecnica integral + carimbo G2 Direcao tecnico capturado; transicao para `aprovado` aguarda parecer LGPD ADR-0005 anexado).
**V5 guarda-em-camadas status:** `provisorio` (AI BLOQUEADA-SESSAO ate V5 cross-security-resposta do SE chegar via gestao-controle-aplicado subtipo controle-llm-guardrails).

### D-010 - Sala security-lgpd criada mid-sprint POR AUTORIZACAO EXPLICITA DA DIRECAO (caminho canonico V3)

**Data:** 2026-05-22.
**Esclarecimento Direcao:** 2026-05-22 ("ele criou a pasta porque eu autorizei").

**Contexto:** Durante execucao do parecer LGPD S2-C02 (TD-002 email em audit log), `security-lgpd` detectou que a pasta `equipe/security-lgpd/` ainda nao estava configurada no projeto chatbot-RPinfo. Skill emitiu primeiro handoff de bloqueio `AP-12-sala-ausente`. Direcao autorizou explicitamente a criacao da sala mid-sprint via canal separado (nao registrado no handoff inicial da skill). A skill criou a sala (7 sub-pastas + stub contexto-projeto.md) e auto-declarou no §5.3 do log canonico como "excecao AP-12 universal MEDIUM" por nao saber da autorizacao Direcao.

**Reclassificacao apos esclarecimento Direcao:**

- **NAO eh excecao AP-12** nem divida de procedimento MEDIUM.
- **EH caminho canonico V3 destravado por autorizacao Direcao explicita.** AP-11 universal PM ("PARA + abre handoff para Direcao/PM de setup, aguarda configuracao explicita") foi cumprido literalmente - a configuracao explicita veio da Direcao via canal separado, nao via setup-projeto CLI.

**Padrao operacional confirmado:**

Quando uma skill detectar `AP-12 sala ausente`, o caminho canonico V3 e PARAR e abrir handoff para Direcao/PM. A Direcao tem 2 caminhos canonicos para destravar:

1. **Via `setup-projeto --skills-adicionar <skill> --idempotente`** (CLI) - caminho mais deterministico, gera registro formal no setup do projeto.
2. **Via autorizacao explicita mid-sprint** - canal separado declarando que Direcao autoriza criacao manual; skill cria sala canonica + ato passa a constar em memory/SHARED.md + verificacao opcional de conformidade pos-hoc.

Ambos caminhos sao aceitaveis em V3. A escolha entre eles e da Direcao (geralmente CLI eh preferida por audit; autorizacao mid-sprint eh aceitavel para destravamento rapido com verificacao posterior).

**Dividas rebaixadas a verificacao de conformidade Low opcional:**

- **TDP-001 (Low - opcional)** - Verificar conformidade da sala com template canonico per-skill (inv 151). Decisao Direcao em Sprint 003 sobre re-executar setup-projeto canonico OR aceitar estado atual. Path: `equipe/tech-lead-senior/tech-debt/2026-05-22_sprint-002_excecao-ap-12-sala-security-lgpd.md`.
- **TDP-002 (Low)** - Auditar outras skills sem sala configurada (caso analogo latente). Independente da autorizacao Direcao.
- **BL-011 + BL-012** rebaixados em `equipe/pm-senior/backlog-priorizado.md`.

**Aprendizado estrutural (D-010 atualizado):** AP-11 universal PM aceita 2 caminhos para "configuracao explicita" - `setup-projeto` CLI OU autorizacao Direcao mid-sprint. Skills que criarem sala mid-sprint sem autorizacao Direcao + sem auto-declaracao + sem divida formal nomeada = NAO aceitavel (AP-11 violado). Skills que criarem sala mid-sprint com autorizacao Direcao (caso aqui) = caminho canonico V3 valido.

### D-006 - Padrao operacional: carimbo Direcao parcial e licito

**Data:** 2026-05-22.

**Contexto:** Sprint 002 mostrou que Direcao pode carimbar G3 sprint plan sem carimbar simultaneamente todos os gates derivados (G2 ADR ou parecer cross-skill).

**Decisao:** Em V3, sprint pode entrar em `aprovado-direcao-parcial` com gates pendentes nomeados explicitamente. Cands cujas dependencias estao satisfeitas executam; cands que dependem de gate pendente ficam bloqueadas no controle-cands com estado `Em parecer Direcao` ou `Bloqueada` ate destravamento. PM emite handoff consultivo cross-skill para suprir input que destrava o gate pendente. Sem essa salvaguarda, sprint inteira ficaria parada por causa de 1 gate.

## CGs canonicas do projeto (transversais)

Confirmadas como CGs S001 + adicionadas em S002:

- **CG-01** - Nenhuma cand pode escrever, alterar ou executar acao no ERP RP Info (S001+).
- **CG-02** - Todo acesso ao ERP passa por camada read-only ou wrapper que force transacao read-only, timeout e limite de linhas (S001+).
- **CG-03** - Nenhum segredo, dump, `.env` ou amostra sensivel pode entrar em repositorio publico (S001+).
- **CG-04** - CPF, CNPJ, documento, WhatsApp, conversa ou identificador pessoal nao podem ser persistidos sem parecer Security/LGPD (S001+).
- **CG-05** - Toda resposta sem dado suficiente deve declarar negativa honesta e motivo da insuficiencia (S001+).
- **CG-06** - Margem e estoque fantasma nao podem ser vendidos como acurados antes de comparacao contra relatorio oficial (S001+).
- **CG-07** - Concorrencia e encarte ficam fora desta sprint, salvo apenas placeholders de escopo condicionado (S001+).
- **CG-08** (NOVO S002) - Nenhuma promocao a producao sem ADR novo + carimbo Direcao (decisao Direcao 2026-05-22).
- **CG-09** (NOVO S002) - Parecer Security/LGPD obrigatorio antes de qualquer extensao de policy PII (decisao Direcao 2026-05-22).

## Componente educacional ativo no projeto

A partir da Sprint 002, cands que estabelecem disciplina nova devem incluir material didatico estruturado para a Direcao (Decio) como evidencia esperada. Decisao Direcao 2026-05-22: "Quero aprender mais a fundo esse processo para conhecimento proprio mesmo".

Aplicacao em S002:
- BL-009 (AI engineering processo qa_orchestrator).
- BL-010 (ML engineering processo eval/drift/retraining).

Aplicacao em sprints futuras: replicar para outras disciplinas conforme estrearem no projeto.

## Convencoes de organizacao

- Aceites Gate 2: `equipe/pm-senior/aceites/YYYY-MM-DD_sprint-NNN_cand-<id>_gate-2.md`.
- Dividas tecnicas formais: `equipe/tech-lead-senior/tech-debt/YYYY-MM-DD_sprint-NNN_cand-<id>_divida-gate-2.md`.
- Tech-debt raiz (consolidacao QA): `tech-debt.md` (raiz do projeto).
- Retros publicadas: `equipe/pm-senior/retros/retro-sprint-NNN.md` (imutaveis).
- Retro estrutural por sprint: `equipe/pm-senior/retros/sprint-NNN/blocos/*.md`.
- Spikes: `spikes/<slug>/` (`harness/`, `outputs/`, `premissas.md`, `README.md`).
