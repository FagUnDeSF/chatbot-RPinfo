# Spike S1-SPK-05 - Acuracia de estoque-fantasma e margem

Spike tecnico data-engineer-senior (Sprint 001, Cand S1-C05). Reclassificada de M para T pelo Gate 1 TL (sprint-doc linha 236). Objetivo: construir harness controlado reproduzivel com amostra pequena para deixar evidencia tecnica do que e validavel hoje e do que depende de relatorio oficial.

Criterio de aceite literal (sprint-doc linha 166): "harness controlado de estoque fantasma e margem executa sobre amostra pequena, declara fonte/premissas e compara contra relatorio oficial quando disponivel; se o relatorio oficial nao estiver disponivel, entrega apenas harness/amostra e marca margem como inconclusiva".

## Via tomada

`apenas-harness-margem-inconclusiva` (criterio admite explicitamente). Relatorio oficial RP Info nao disponibilizado na aprovacao Direcao da sprint (2026-05-20); pack-E §"Dependencias" linha 87 confirma pendente.

## Fronteira preservada

- Consumo da amostra exclusivamente via `chatbot_rpinfo.application.services.erp_readonly_service.ErpReadonlyService` + `InMemoryErpReadonlyRepository` com allowlist estendida pela fixture do spike. Sem driver direto. Sem expansao de allowlist runtime no backend (a fixture vive isolada no spike).
- Queries allowlisted do spike: `inventory_risk_spike_S1_C05`, `sales_summary_spike_S1_C05`.
- Service aplica validacao canonica de allowlist + `erp_readonly_max_rows` + auditoria + idempotency-key (mesma rota do endpoint `POST /api/v1/erp-readonly/query`).
- Sem PII regulado. SKUs sao codigos sinteticos (`SKU-S1SPK05-NNN`); store_id e inteiro 1..3; sem nome de loja, sem CPF/CNPJ, sem dado pessoal.

## Premissas literais por metrica

### estoque_fantasma

- **Fonte:** query `inventory_risk_spike_S1_C05` (source `erp_readonly.fixture.spike_S1_C05.inventory`). Colunas consumidas: `sku`, `store_id`, `stock`, `days_without_sale`.
- **Regra:** SKU classificado como fantasma se `stock > 0 AND days_without_sale >= threshold_dias_sem_venda`.
- **Janela temporal:** snapshot unico em `2026-05-21` (`SPIKE_AS_OF_DATE`).
- **Filtros:** nenhum filtro a montante; a regra opera sobre a amostra inteira (10 linhas).
- **Threshold default:** 90 dias - hipotese tecnica do spike, **NAO regra oficial**. Direcao podera ajustar quando relatorio oficial chegar.
- **Veredicto:** `inconclusiva` no run default. O harness reporta a contagem e a lista de SKUs candidatos sob a hipotese tecnica; o veredicto final (validado/divergente) depende de comparacao com relatorio oficial.

### margem

- **Fonte:** query `sales_summary_spike_S1_C05` (source `erp_readonly.fixture.spike_S1_C05.sales`). Colunas consumidas: `store_id`, `period`, `gross_sales`. Colunas ausentes para calculo: `cmv`, `net_sales`.
- **Regra:** `margem = (gross_sales - cmv) / gross_sales`; requer CMV por loja/periodo.
- **Janela temporal:** snapshot unico em `2026-05-21`.
- **Filtros:** nenhum filtro a montante.
- **Veredicto:** `inconclusiva`. Dois motivos literais registrados no output:
  1. CMV ausente nas colunas da query allowlisted (somente `gross_sales` por loja/periodo).
  2. Relatorio oficial RP Info indisponivel para conferencia; criterio literal admite entrega apenas-harness com margem inconclusiva.

## Comando reproduzivel

Pre-requisito: `.venv` ativada com `pip install -e .[dev]` ja aplicado.

```powershell
.venv\Scripts\python.exe spikes\S1-SPK-05-acuracia-estoque-margem\harness\run_harness.py `
    --output-dir spikes/S1-SPK-05-acuracia-estoque-margem/outputs
```

Com relatorio oficial disponivel (uso futuro):

```powershell
.venv\Scripts\python.exe spikes\S1-SPK-05-acuracia-estoque-margem\harness\run_harness.py `
    --output-dir spikes/S1-SPK-05-acuracia-estoque-margem/outputs `
    --relatorio-oficial-path <path>.csv `
    --threshold-dias-sem-venda 90
```

> O spike usa diretorio com tracos (`S1-SPK-05-...`), invalido como identificador Python. O `run_harness.py` injeta o diretorio pai de `harness/` no `sys.path` automaticamente; idem para o teste pytest, via `conftest.py` na raiz do spike.

Teste reproduzivel via pytest:

```powershell
.venv\Scripts\python.exe -m pytest spikes/S1-SPK-05-acuracia-estoque-margem/harness/test_harness.py -v
```

## Estrutura do output

Cada execucao grava em `outputs/<YYYYMMDDTHHMMSSZ>/`:

- `result.json` - payload canonico com `spike_id`, `cand`, `timestamp_utc`, `threshold_dias_sem_venda`, `amostras` (hash SHA-256 por amostra, fonte, `read_only`), `relatorio_oficial` (status + motivo), `metricas` (lista com `metric_name`, `fonte`, `premissas`, `veredicto`, `valor`, `motivo`).
- `result.csv` - linha por metrica com `metric_name`, `veredicto`, `query_name`, `source`, `motivo`.

## CG aplicaveis (sprint-doc §3)

- CG-01: nenhuma escrita no ERP - harness so consome via service read-only.
- CG-02: acesso via camada read-only - validado por roteamento atraves de `ErpReadonlyService`.
- CG-03: sem segredo, dump ou amostra sensivel - fixture sintetica; output sem PII; sem `.env` no spike.
- CG-06: margem e estoque-fantasma nao podem ser vendidos como acurados antes de relatorio oficial - veredicto `inconclusiva` reflete explicitamente.
- CG-07: concorrencia e encarte fora do escopo - nao tocados.

## Pendencias

- **Relatorio oficial RP Info:** quando a Direcao disponibilizar, reexecutar o harness com `--relatorio-oficial-path` apontando para `.csv` ou `.json` contendo, no minimo, `store_id`, `period`, `gross_sales_oficial`, `cmv_oficial`, `n_skus_fantasma_oficial` por loja/periodo. O harness retornara veredicto comparado.
- **Expansao da allowlist real do backend** (queries `inventory_risk_*` e `sales_summary_*` com CMV em prod) **nao foi necessaria** nesta cand: o spike usa fixture isolada (cobre via apenas-harness-margem-inconclusiva). Se Direcao promover spike a entregavel formal, abrir handoff complementar para `backend-senior` para incluir CMV na allowlist runtime.
