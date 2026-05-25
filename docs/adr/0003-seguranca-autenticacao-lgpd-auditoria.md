---
tipo: adr-publico
numero: "0003"
slug: seguranca-autenticacao-lgpd-auditoria
status: aprovado
data: 2026-05-20
publico_alvo: portfolio
---

# ADR-0003 - Seguranca, autenticacao, LGPD e auditoria do chat interno

## Contexto

O produto consulta dados de ERP e pode lidar com informacoes comerciais,
operacionais e pessoais. A fundacao deve proteger menor privilegio,
auditabilidade e ausencia de persistencia indevida de dado pessoal.

## Decisao

Adotar autenticacao interna com contas nominativas, RBAC minimo por perfil e
auditoria de metadados sem payload sensivel bruto.

Perfis iniciais:

- `direcao`
- `comercial`
- `prevencao`
- `admin-tecnico`

Metadados de auditoria incluem usuario, horario, intencao, fonte consultada,
tipo de resposta e flag de insuficiencia de dado. Logs nao devem registrar
segredos, prompts brutos ou dados pessoais sem parecer proprio.

## Consequencias

- Reduz risco de vazamento em um projeto conectado ao ERP.
- Mantem publicacao publica compativel com ausencia de segredos e dumps.
- Permite migrar para SSO no futuro sem quebrar a regra de usuario nominativo.
- Historico de conversa ou dado pessoal segue bloqueado ate parecer LGPD.

## Status

Aprovado como ADR de fundacao.
