# tool-interoperability Specification

## Purpose
Garantir que as ferramentas do ai-config (Headroom, RTK, uv, pip, Semgrep e
a status line) funcionem em máquinas reais, inclusive atrás de inspeção TLS
e com aliases da Microsoft Store no PATH, e que o `doctor` aponte a causa e a
correção sem alterar nada.

## Requirements

### Requirement: Ferramentas Python funcionam atrás de inspeção TLS sem desativar verificação

O repositório SHALL oferecer um comando que gera, fora do checkout, um bundle
de CA com as raízes Mozilla e as raízes confiáveis do sistema, e SHALL
documentar seu uso por sessão com `SSL_CERT_FILE` e `REQUESTS_CA_BUNDLE`. O
repositório SHALL NOT desativar a verificação TLS nem persistir essas
variáveis no perfil do usuário.

#### Scenario: Proxy Headroom atrás de antivírus com inspeção HTTPS

- **GIVEN** o HTTPS é reassinado por uma CA presente só no repositório do Windows
- **WHEN** o usuário gera o bundle e inicia `headroom proxy` com as duas variáveis
- **THEN** o proxy fica pronto e alcança o provedor com verificação TLS ativa

#### Scenario: Diagnóstico da inspeção

- **WHEN** o `doctor` roda numa máquina com inspeção TLS
- **THEN** ele informa o emissor interceptador e a ação corretiva
- **AND** sem rede o check é marcado como não verificado, sem erro

### Requirement: O doctor aponta configurações locais quebradas ou amplas

O `doctor` SHALL avisar quando a statusLine instalada aponta para um alias
`WindowsApps` ou para um executável inexistente, quando o hook `rtk hook claude`
não está registrado, quando o `rtk` do PATH não é o Rust Token Killer e quando
a allowlist contém `Bash(rtk:*)`, `PowerShell(rtk:*)` ou `Bash(headroom:*)`.

#### Scenario: Allowlist ampla herdada

- **GIVEN** `~/.claude/settings.json` contém `Bash(rtk:*)`
- **WHEN** o usuário roda `doctor`
- **THEN** o aviso explica que comandos reescritos pelo hook ficam aprovados
- **AND** nenhum arquivo é alterado

### Requirement: O placeholder de Python nunca resolve para o alias da Store

O instalador SHALL resolver `{{PYTHON}}` para o interpretador em execução e
SHALL ignorar executáveis em `WindowsApps` ao procurar alternativas.

#### Scenario: Alias da Store antes do Python real no PATH

- **WHEN** `python3` no PATH é o alias `WindowsApps`
- **THEN** a statusLine instalada usa o interpretador real
