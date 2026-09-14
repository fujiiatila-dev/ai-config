# harden-installer-toolchain

Endurecer o baseline do ai-config, atualizar referências e preparar o instalador para manutenção segura e multiplataforma.

## Validação da implementação

- Suíte Python: 23 testes passando, 1 teste de wrapper incompatível com o
  sistema operacional ignorado.
- `py_compile`, dry-run de PowerShell e Git Bash e `openspec validate --strict`:
  aprovados.
- Gitleaks e Trivy: aprovados, sem segredos ou vulnerabilidades reportadas.
- Semgrep automático: indisponível por erro de certificado TLS ao baixar regras;
  varreduras locais por padrões Python perigosos não encontraram achados.
- Aurum: não aplicável neste ambiente porque o executável não está instalado.
- Headroom: `/readyz` saudável em `127.0.0.1:48731`; baseline Codex validado
  depois do hardening.
