## Why

O uso diário do Headroom e do RTK falhava em máquinas Windows por causas que o
`doctor` não mostrava:

- **Headroom não sobe atrás de inspeção TLS.** Antivírus (AVG/Avast Web Shield)
  e proxies corporativos reassinam o HTTPS com uma CA que existe só no
  repositório do sistema. O venv do Headroom valida contra o bundle
  Mozilla/`certifi`; o `litellm` baixa o encoding do `tiktoken` na partida e o
  proxy morre com `CERTIFICATE_VERIFY_FAILED`. O mesmo erro quebra
  `headroom update`, `uv tool upgrade`, `pip install semgrep` e o
  `--update-tools`.
- **statusLine quebrada.** `{{PYTHON}}` era resolvido com `which("python3")`,
  que no Windows encontra o alias da Microsoft Store (`WindowsApps`). O alias
  sai com código 9009 e a status line some.
- **`doctor` mostra `?` na versão** de ferramentas Python (Semgrep leva ~4 s
  sem o check online e ~100 s com ele; Headroom passa de 3 s a frio).
- **Allowlist ampla demais.** `Bash(rtk:*)`/`PowerShell(rtk:*)` combinados com
  o hook que reescreve `docker ps` → `rtk docker ps` aprovam qualquer comando
  que o RTK saiba envolver. `Bash(headroom:*)` aprova `headroom init --global`
  e `headroom install`, justamente o que a documentação proíbe.
- **winget falha** quando a origem `msstore` rejeita o certificado reassinado.

## What Changes

- Novo subcomando `ca-bundle` (`--ca-bundle` nos wrappers): gera, fora do
  repositório, um PEM com `certifi` + raízes confiáveis do Windows, para uso
  por sessão em `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`. Nunca desativa a
  verificação TLS.
- `doctor` passa a detectar inspeção TLS, alias da Store na statusLine,
  hook RTK ausente/binário RTK errado e permissões amplas de `rtk`/`headroom`.
- Sondagem de versão com prazo por ferramenta e check online do Semgrep
  desligado.
- `{{PYTHON}}` resolve para o interpretador que roda o instalador e nunca para
  um alias `WindowsApps`.
- Semgrep via `pip --use-feature=truststore`; winget com `--source winget`.
- Permissões portáteis de `rtk`/`headroom` restritas a subcomandos de leitura.
- `versions.json` atualizado para a toolchain de 2026-09-27.
- aurum com canal de instalação documentado; Impeccable vendorizado atualizado
  para 4.3.1 com o hook do launcher e `.gitattributes` para scripts `sh`.
- Documentação reorganizada com um guia de uso das ferramentas (`TOOLS.md`).

## Non-goals

- Instalar ou atualizar RTK, Headroom ou aurum automaticamente.
- Persistir `SSL_CERT_FILE` ou qualquer variável de rede no perfil do usuário.
- Remover entradas existentes do `settings.json` local (o merge nunca remove).
