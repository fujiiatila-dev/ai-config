## Context

Ver `proposal.md`. Os wrappers foram simplificados para chamar o motor Python,
mas a etapa de ferramentas foi removida junto com a duplicação. O repositório
já possui uma spec permanente, testes e CI multiplataforma para o contrato do
instalador.

## Goals / Non-Goals

**Goals:**

- Manter Bash e PowerShell finos, com lógica comum no motor Python.
- Instalar configuração e ferramentas recomendadas por padrão.
- Fazer `--skip-tools`, `--dry-run`, mensagens e códigos de saída funcionarem
  igualmente nos dois wrappers.
- Preservar o padrão compartilhado completo em todos os agentes.

**Non-Goals:**

- Instalar ou autenticar Codex Security automaticamente.
- Tornar ferramentas externas obrigatórias para o funcionamento básico das
  configurações.
- Automatizar RTK, Headroom e aurum, que têm canais de instalação próprios.

## Decisions

1. **Centralizar preparação no Python.** `cmd_install` executará a sincronização
   e, salvo `--skip-tools`/`--dry-run`, chamará uma rotina data-driven para
   OpenSpec, Semgrep, Gitleaks e Trivy. Isso evita nova divergência entre os
   wrappers. Restaurar os blocos duplicados foi rejeitado por manutenção.
2. **Usar gerenciadores já disponíveis.** OpenSpec usa npm; Semgrep usa o
   interpretador atual com `-m pip`; Gitleaks e Trivy selecionam winget,
   Chocolatey ou Homebrew conforme disponibilidade. Ausência gera aviso e
   orientação manual sem desfazer a configuração já instalada.
3. **Diagnóstico sem rede.** O `doctor` usa chaves explícitas de
   `versions.json`; Codex Security é detectado por executável ou metadados npm
   locais, sem download.
4. **Testar o motor, não duplicações de wrapper.** Testes unitários simulam
   comandos e plataformas. Wrappers recebem testes estreitos de propagação de
   argumentos/códigos.

## Risks / Trade-offs

- [Gerenciador retorna sucesso mas o PATH atual não é atualizado] → orientar
  reinício do terminal e confirmar pelo `doctor`.
- [Linux sem Homebrew não instala binários de segurança] → registrar falha
  parcial e fornecer links oficiais; a configuração permanece utilizável.
- [Instalações globais surpreendem usuários existentes] → manter
  `--skip-tools`, documentá-lo no help e nunca instalar durante `--dry-run`.

## Migration Plan

Restaurar primeiro o contrato e os testes no checkout atual, validar nos três
sistemas pelo CI e então reinstalar localmente. O rollback é a reversão do
commit; configurações já mescladas e ferramentas já instaladas permanecem
válidas.
