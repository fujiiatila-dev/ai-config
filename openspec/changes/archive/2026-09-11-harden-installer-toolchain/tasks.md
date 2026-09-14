## 1. Ferramentas e diagnóstico

- [x] 1.1 Adicionar as flags `--update-tools` e `--harden-codex` ao motor Python e aos helps dos wrappers Bash/PowerShell, mantendo `--skip-tools` e `--dry-run` como bloqueios de efeitos colaterais.
- [x] 1.2 Fazer o catálogo `versions.json` dirigir comandos versionados de OpenSpec, Semgrep, Gitleaks e Trivy, com `install` para ausentes e `upgrade` somente quando `--update-tools` for usado.
- [x] 1.3 Reduzir e limitar as tentativas de descoberta de versão, garantindo que CLIs travadas não prendam o `doctor` e que o processo continue com versão desconhecida.
- [x] 1.4 Validar `HEADROOM_PORT`, usar o valor efetivo no probe `/readyz` e tornar o diagnóstico da porta e de ferramentas ausentes acionável.

## 2. Baseline seguro do Codex

- [x] 2.1 Atualizar `adapters/codex/config.toml.example` com defaults restritos de sandbox e aprovação, sem incluir credenciais, caminhos absolutos ou permissões de projeto.
- [x] 2.2 Implementar hardening explícito com backup, preservação de chaves desconhecidas e remoção limitada da confiança exata na raiz do perfil quando a seção só contiver `trust_level`.
- [x] 2.3 Fazer o `doctor` detectar sandbox elevada, política ausente/insegura e confiança ampla, emitindo avisos sem alterar arquivos.

## 3. Workflow e documentação

- [x] 3.1 Corrigir `shared/WORKFLOW.md` para usar o cliente correto no OpenSpec e documentar comandos equivalentes para Bash e PowerShell.
- [x] 3.2 Alinhar `adapters/codex/AGENTS.md`, `adapters/gemini/GEMINI.md`, `README.md`, `HEADROOM.md` e `CONFIGURATION_MAP.md` com as flags, versões, porta e política de segurança atualizadas.
- [x] 3.3 Atualizar referências de versão e data de verificação sem alterar as mudanças locais já presentes em `versions.json` e `tests/test_installer.py`.

## 4. Regressão e entrega

- [x] 4.1 Adicionar testes para comandos de instalação/upgrade por gerenciador, ausência de upgrade no modo padrão, timeout do `doctor`, validação de porta e hardening do Codex.
- [x] 4.2 Rodar compilação, suíte Python, `--dry-run` nos wrappers e validação OpenSpec; corrigir regressões sem instalar dependências globais durante os testes.
- [x] 4.3 Rodar auditorias locais de segurança e qualidade aplicáveis, registrar checks não aplicáveis e confirmar o estado final do Headroom/Codex.
