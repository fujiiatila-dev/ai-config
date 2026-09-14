## Purpose

Manter as instruções compartilhadas executáveis e coerentes entre agentes,
plataformas e shells, sem fazer um cliente assumir o lugar de outro.

## ADDED Requirements

### Requirement: OpenSpec identifica o cliente correto

O workflow compartilhado SHALL explicar que o valor de `--tools` depende do
cliente em execução e SHALL fornecer exemplos específicos para Claude Code,
Codex e Gemini, sem prescrever um único agente como padrão universal.

#### Scenario: Fluxo no Codex
- **WHEN** um usuário segue o exemplo de OpenSpec no Codex
- **THEN** o exemplo usa `openspec init --tools codex`

#### Scenario: Fluxo no Claude Code
- **WHEN** um usuário segue o exemplo de OpenSpec no Claude Code
- **THEN** o exemplo usa `openspec init --tools claude`

#### Scenario: Fluxo no Gemini
- **WHEN** um usuário segue o exemplo de OpenSpec no Gemini
- **THEN** o exemplo usa `openspec init --tools gemini`

### Requirement: Comandos documentados cobrem Bash e PowerShell

As instruções SHALL fornecer sintaxe equivalente para variáveis de ambiente,
auditoria de qualidade e comandos de segurança nos shells Bash e PowerShell.

#### Scenario: Auditoria em PowerShell
- **WHEN** o usuário executa a auditoria no Windows PowerShell
- **THEN** consegue definir `PYTHONUTF8` e rodar `aurum check .` sem usar atribuição Unix

#### Scenario: Auditoria em Bash
- **WHEN** o usuário executa a auditoria em Bash
- **THEN** consegue usar a forma `PYTHONUTF8=1 aurum check .`

### Requirement: Headroom usa uma porta documentada e parametrizável

Os exemplos de Headroom SHALL usar a porta configurada por `HEADROOM_PORT`,
com fallback explícito para a porta de referência do repositório, e SHALL
manter o proxy limitado a loopback.

#### Scenario: Porta padrão
- **WHEN** `HEADROOM_PORT` não está definida
- **THEN** os exemplos usam a porta padrão documentada pelo ai-config

#### Scenario: Porta personalizada
- **WHEN** `HEADROOM_PORT` está definida
- **THEN** init, proxy, doctor e configuração do Codex usam o mesmo valor
