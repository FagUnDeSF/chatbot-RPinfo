---
tipologia: how-to
sprint_id: "003"
data_release: 2026-05-25
publico_alvo: portfolio
mantida_por: technical-writer-senior
formato: getting-started
---

# Getting started

Este guia coloca o backend FastAPI e o frontend React/Vite em modo local. Use
stub deterministico para primeiro teste: ele nao chama a API Anthropic e evita
qualquer dependencia de segredo real.

## Pre-requisitos

- Windows com PowerShell.
- Python 3.12.
- Node 22 LTS ou Node 20 LTS.
- Repositorio clonado em `C:\ProjetoRP\chatbot-RPinfo`.

## 1. Preparar o backend

```powershell
cd C:\ProjetoRP\chatbot-RPinfo
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Se a venv ainda nao existir:

```powershell
cd C:\ProjetoRP\chatbot-RPinfo
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 2. Configurar variaveis locais

Nao grave valores reais em arquivos versionados. Para teste local com stub:

```powershell
$env:APP_ENV = "local"
$env:USE_STUB_DETERMINISTICO = "true"
$env:INTERNAL_AUTH_DIRECAO_TOKEN = [guid]::NewGuid().ToString("N")
$env:INTERNAL_AUTH_COMERCIAL_TOKEN = [guid]::NewGuid().ToString("N")
$env:INTERNAL_AUTH_PREVENCAO_TOKEN = [guid]::NewGuid().ToString("N")
$env:INTERNAL_AUTH_ADMIN_TECNICO_TOKEN = [guid]::NewGuid().ToString("N")
```

Para usar LLM real, defina `ANTHROPIC_API_KEY` no ambiente autorizado e mantenha
o budget da ADR-0005. Nao coloque o valor em README, changelog, logs ou commits.

## 3. Rodar o backend

```powershell
cd C:\ProjetoRP\chatbot-RPinfo
.\.venv\Scripts\python.exe -m uvicorn chatbot_rpinfo.main:app --reload --host 127.0.0.1 --port 8000
```

Valide o health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 4. Testar uma query pela API

```powershell
$headers = @{
  "X-Internal-Username" = "rp-prevencao"
  "X-Internal-Token" = $env:INTERNAL_AUTH_PREVENCAO_TOKEN
  "Idempotency-Key" = "local-qa-001"
}
$body = @{ question = "Qual o risco de estoque parado da loja 2?" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/qa/ask `
  -Headers $headers `
  -Body $body `
  -ContentType "application/json"
```

Resposta esperada em stub: `answer_type=answered`, fonte `erp_readonly.fixture`
e premissas sobre SKU/loja. Se a pergunta nao tiver intent conhecida, o sistema
deve responder negativa honesta com `reason=intent_nao_reconhecido`.

## 5. Rodar o frontend

Em outro terminal:

```powershell
cd C:\ProjetoRP\chatbot-RPinfo\src\frontend
npm install
npm run dev
```

Abra `http://127.0.0.1:5173`. O frontend usa o proxy dev-only do Vite para falar
com o backend local, conforme a correcao S3-C02.

## 6. Validar qualidade local

Backend:

```powershell
cd C:\ProjetoRP\chatbot-RPinfo
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy -p chatbot_rpinfo
```

Frontend:

```powershell
cd C:\ProjetoRP\chatbot-RPinfo\src\frontend
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

## Troubleshooting

| Sintoma | Causa provavel | Acao |
|---|---|---|
| `401 Unauthorized` | Header `X-Internal-Token` nao bate com a variavel de ambiente do perfil. | Redefina o token no mesmo terminal do backend e reinicie o servidor. |
| `422 Unprocessable Entity` | Pergunta contem identificador sensivel ou payload invalido. | Remova CPF, CNPJ, RG, email, telefone ou cartao da pergunta. |
| Frontend nao conecta | Backend fora do ar ou porta 8000 ocupada. | Reinicie o backend e confirme `http://127.0.0.1:8000/health`. |
| Playwright falha na primeira execucao | Browsers ainda nao instalados. | Rode `npx playwright install` dentro de `src/frontend`. |
