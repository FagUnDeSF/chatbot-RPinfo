@echo off
setlocal

"C:\ProjetoRP\chatbot-RPinfo\.venv\Scripts\python.exe" "C:\ProjetoRP\chatbot-RPinfo\observability\llm\cost_monitor_runtime.py" --cadencia weekly --audit-jsonl "C:\ProjetoRP\chatbot-RPinfo\observability\llm\runtime\audit_events.jsonl" --project-path "C:\ProjetoRP\chatbot-RPinfo" --output-dir "C:\ProjetoRP\chatbot-RPinfo\observability\llm\reports"
