## Contexto verificado (2026-09-27, Windows 11)

| Sintoma | Causa observada |
| --- | --- |
| `headroom proxy` não fica pronto | `tiktoken` → `requests` → `CERTIFICATE_VERIFY_FAILED` (CA "AVG Web/Mail Shield Root") |
| `uv tool upgrade headroom-ai` falha | `invalid peer certificate: UnknownIssuer` |
| `pip install semgrep` falha | mesmo erro; com truststore passa |
| `winget upgrade` falha | origem `msstore` com cert pinning (`0x8a15005e`) |
| statusLine vazia | `WindowsApps/python3.EXE` sai com 9009 |
| `doctor` mostra `?` | orçamento único de 3 s para `--version` |

Teste ponta a ponta: com `SSL_CERT_FILE` e `REQUESTS_CA_BUNDLE` apontando para
o bundle gerado, `headroom proxy` fica pronto em ~28 s e `POST /v1/messages`
volta `401 invalid x-api-key` da Anthropic (conectividade real). Sem o bundle o
processo termina antes do `/readyz`.

## Decisões

### Bundle de CA por sessão, fora do repositório

`httpx` lê `SSL_CERT_FILE`; `requests` lê somente `REQUESTS_CA_BUNDLE`. O
Headroom usa os dois, então a documentação define ambos. O bundle é
`certifi` (vendorizado pelo pip, sem dependência nova) + certificados de
`ROOT`/`CA` do Windows válidos para autenticação de servidor. O arquivo fica em
`~/.config/ai-config/ca-bundle.pem` (ou `AICONFIG_CA_BUNDLE`), é específico da
máquina e não é versionado. Fora do Windows o comando não gera nada e indica o
bundle do sistema.

Alternativa preferível quando o usuário controla o antivírus: excluir os
domínios dos provedores da inspeção HTTPS. Documentada, não automatizada.

### Detecção no `doctor`

A sondagem TLS faz um handshake com `api.anthropic.com:443` duas vezes: com o
contexto padrão do sistema e com um contexto que só conhece `certifi`. Sistema
ok e `certifi` falhando indica inspeção; o emissor é mostrado para o usuário
saber qual produto intercepta. Sem rede, o check é `skipped`. A variável
`AICONFIG_DOCTOR_OFFLINE=1` desliga a sondagem (usada nos testes).

### Permissões

O merge nunca remove entradas; por isso a allowlist nova é restrita e o
`doctor` avisa sobre as regras amplas já instaladas, com a ação corretiva.
