---
tipo: scheduler-config
projeto: chatbot-RPinfo
sprint: 003
cand: S3-C04
status: ativo
data: 2026-05-24
---

# Windows Task Scheduler - monitorar-custo-llm

Scheduler escolhido: Windows Task Scheduler, porque o ambiente alvo da Fase 1 e single-user localhost em Windows. Linux cron continua alternativa equivalente quando o runtime migrar para host Linux; APScheduler in-process fica rejeitado para esta fase porque depende do backend estar de pe.

## Tasks

| Task | Cadencia | Wrapper |
|---|---|---|
| `chatbot-RPinfo-monitorar-custo-llm-continuous` | A cada 15 minutos | `observability\llm\scheduler\run_continuous.cmd` |
| `chatbot-RPinfo-monitorar-custo-llm-weekly` | Toda terca-feira 09:00 | `observability\llm\scheduler\run_weekly.cmd` |
| `chatbot-RPinfo-monitorar-custo-llm-monthly` | Dia 1 de cada mes 08:00 | `observability\llm\scheduler\run_monthly.cmd` |

## Instalar ou atualizar

```powershell
schtasks /Create /F /SC MINUTE /MO 15 /TN "chatbot-RPinfo-monitorar-custo-llm-continuous" /TR "C:\ProjetoRP\chatbot-RPinfo\observability\llm\scheduler\run_continuous.cmd"
schtasks /Create /F /SC WEEKLY /D TUE /ST 09:00 /TN "chatbot-RPinfo-monitorar-custo-llm-weekly" /TR "C:\ProjetoRP\chatbot-RPinfo\observability\llm\scheduler\run_weekly.cmd"
schtasks /Create /F /SC MONTHLY /D 1 /ST 08:00 /TN "chatbot-RPinfo-monitorar-custo-llm-monthly" /TR "C:\ProjetoRP\chatbot-RPinfo\observability\llm\scheduler\run_monthly.cmd"
```

## Verificar

```powershell
schtasks /Query /TN "chatbot-RPinfo-monitorar-custo-llm-continuous" /FO LIST
schtasks /Query /TN "chatbot-RPinfo-monitorar-custo-llm-weekly" /FO LIST
schtasks /Query /TN "chatbot-RPinfo-monitorar-custo-llm-monthly" /FO LIST
```

## Rollback

```powershell
schtasks /Delete /TN "chatbot-RPinfo-monitorar-custo-llm-continuous" /F
schtasks /Delete /TN "chatbot-RPinfo-monitorar-custo-llm-weekly" /F
schtasks /Delete /TN "chatbot-RPinfo-monitorar-custo-llm-monthly" /F
```

Remover as tasks nao apaga `thresholds.yaml`, templates, reports ja emitidos ou `observability\llm\runtime\audit_events.jsonl`.
