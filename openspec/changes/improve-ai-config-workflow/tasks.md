## 1. Modelo e regras do preflight

- [x] 1.1 Criar o relatório estruturado do preflight, com severidade, códigos
  de regra, caminhos relativos, ações corretivas, `schema_version` e saída
  humana/JSON sem valores sensíveis.
- [x] 1.2 Implementar as verificações de estrutura, arquivos referenciados,
  JSON/TOML, placeholders, catálogo de versões e cobertura do `doctor`.
- [x] 1.3 Implementar as verificações de paridade entre adapters e
  `shared/WORKFLOW.md`, incluindo comandos equivalentes e arquivos gerenciados.
- [x] 1.4 Implementar as verificações portáteis de caminhos, endpoints,
  credenciais, sessões, memória e permissões específicas, com allowlist
  documentada para exemplos e testes.
- [x] 1.5 Adicionar verificações opcionais de compilação Python e sintaxe Bash,
  registrando ferramentas ausentes como `skipped` ou aviso.

## 2. Integração com o instalador

- [x] 2.1 Adicionar o subcomando `validate` e a opção `--json` ao motor comum,
  com códigos de saída estáveis e sem efeitos colaterais.
- [x] 2.2 Executar o preflight obrigatório antes da primeira escrita de
  `cmd_install`, preservando as políticas atuais de conflito, backup, dry-run,
  Headroom e instalação de ferramentas.
- [x] 2.3 Expor `--validate`/`validate` de forma equivalente em `install.sh` e
  `install.ps1`, atualizando o help e repassando argumentos/códigos de saída.

## 3. Regressão automatizada

- [x] 3.1 Cobrir relatório válido, erro estrutural, JSON inválido, placeholder
  desconhecido e arquivo ausente sem alterar o checkout.
- [x] 3.2 Cobrir detecção de caminho absoluto, segredo, endpoint exposto e
  configuração legítima de teste sem vazar o valor no relatório.
- [x] 3.3 Cobrir `--json`, ferramentas opcionais ausentes e paridade dos dois
  wrappers, incluindo que nenhum instalador global é iniciado.
- [x] 3.4 Cobrir que uma falha de preflight impede qualquer escrita, backup,
  Headroom ou preparação de ferramentas.

## 4. CI e documentação

- [x] 4.1 Adicionar o gate de contrato ao workflow de CI e manter compilação,
  suíte multiplataforma e sintaxe dos wrappers.
- [x] 4.2 Atualizar README, CONFIGURATION_MAP, `WORKFLOW.md`, adapters e
  instruções OpenSpec com o fluxo `validate → dry-run → apply → doctor →
  security → quality → commit`.
- [x] 4.3 Documentar os códigos de saída, o formato JSON, as verificações
  opcionais e o tratamento de limitações do ambiente.

## 5. Verificação da entrega

- [x] 5.1 Rodar preflight, suíte de testes, compilação Python, sintaxe Bash,
  dry-run e doctor em Windows.
- [x] 5.2 Rodar os equivalentes Bash e as auditorias de segurança disponíveis,
  registrando explicitamente o que o ambiente não suportar.
- [ ] 5.3 Rodar `aurum check .`, revisar o diff e confirmar que a branch não
  contém credenciais, caminhos absolutos ou arquivos gerados.

## 6. Interoperabilidade Headroom/Claude/Codex

- [x] 6.1 Remover `ANTHROPIC_BASE_URL`, o provider global do Codex, os hooks de
  inicialização e o healthcheck que tornavam o proxy obrigatório.
- [x] 6.2 Instalar um perfil `headroom.config.toml` opt-in para Codex com SSE e
  manter Claude opt-in por `headroom wrap claude --tool-search true`.
- [x] 6.3 Fazer o preflight rejeitar novas rotas/hooks duráveis e o `doctor`
  detectá-los sem imprimir valores, iniciar ou reiniciar processos.
- [x] 6.4 Documentar atualização, desativação do Kompress no Windows,
  concorrência suportada, fallback direto e recuperação da configuração legada.
- [ ] 6.5 Rodar preflight, testes, dry-run, doctor, segurança e qualidade e
  confirmar que o instalador não chama nenhum comando Headroom.

## 7. Recuperação de sessões do Codex

- [x] 7.1 Auditar rollouts, índice, banco de threads e estado de migração sem
  alterar ou copiar o conteúdo das conversas para o repositório.
- [x] 7.2 Implementar backup transacional, reconstrução idempotente do índice e
  associação pela raiz de projeto mais específica, preservando títulos.
- [x] 7.3 Cobrir caminhos estendidos do Windows, metadados suplementares,
  idempotência e preservação de rollouts técnicos com testes automatizados.
- [x] 7.4 Aplicar a recuperação local, validar a sessão solicitada e documentar
  a necessidade de reiniciar a interface uma vez.
- [x] 7.5 Migrar providers Headroom gravados no histórico para OpenAI com backup
  integral dos rollouts e validar o bootstrap real da TUI sem enviar mensagem.

### Registro da verificação — 2026-09-21

- 5.1: `install.ps1 --validate --json`, a suíte de 40 testes (1 skip esperado),
  `py_compile`, `install.ps1 --dry-run` e `install.ps1 --doctor` passaram. O
  doctor confirmou o proxy Headroom em `127.0.0.1:48731` e o baseline seguro do
  Codex.
- 5.2: `install.sh --validate --json` e a sintaxe nativa do Git Bash passaram.
  Gitleaks 8.30.1 não encontrou vazamentos; Trivy 0.72.0 não reportou
  vulnerabilidades nem arquivos de dependência. Semgrep 1.172.0 não encontrou
  achados no `ci.yml` após os pins das actions. O download de `config=auto` pelo
  cliente Python continua falhando por `SSLCertVerificationError`; a mesma
  configuração foi obtida com `curl` usando TLS do Schannel e executada
  localmente, sem desativar validação TLS. Codex Security autenticou, mas os
  scans completo e diferencial foram interrompidos pelo limite de custo da
  sessão (aproximadamente US$ 2,31 e US$ 2,00); não há relatório remoto
  conclusivo e isso não deve ser apresentado como um scan completo.
- 5.3: `openspec validate --all --strict`, `git diff --check`, o preflight e a
  revisão do diff confirmaram a higiene estrutural; não há credenciais,
  caminhos absolutos ou arquivos gerados versionados fora do change OpenSpec.
  `aurum check . --json` não pôde ser executado: o executável não está no PATH,
  o caminho alternativo documentado não existe e o pacote público PyPI
  `aurum` é um projeto diferente. A task permanece aberta; o change não deve
  ser arquivado nem a branch mergeada antes de obter o `aurum` correto e o
  score de qualidade.
- 6.5: o preflight passou sem avisos; 37 testes passaram (1 skip Bash esperado
  no Windows); `py_compile`, `openspec validate --strict`, dry-run, apply e
  doctor passaram. Gitleaks não encontrou segredos, Trivy não encontrou
  manifests vulneráveis e Semgrep não encontrou achados em `tools/aiconfig.py`.
  O scan amplo manteve 63 alertas preexistentes nos scripts vendorizados da
  skill Impeccable. Headroom foi atualizado para 0.38.0, a porta 48731 ficou
  fechada e o doctor confirmou ausência de vínculo global. Chamadas mínimas de
  Claude e Codex padrão retornaram `DIRECT_OK` com o proxy desligado; o Codex
  confirmou `provider: openai`. A task segue aberta somente porque o executável
  Aurum e seu fallback documentado não existem.
- 7.1–7.5: 45 rollouts foram preservados e reindexados; 39 threads de usuário
  foram reassociadas a três projetos e a sessão solicitada foi confirmada no
  rollout, no índice e no banco. Seis rollouts técnicos permanecem indexados,
  sem promoção artificial para a tabela de conversas. O backup transacional
  ficou fora do repositório em `~/.codex/backups/session-recovery-*`. Os dois
  testes novos passaram; Semgrep executou 290 regras nesses arquivos sem
  achados, Gitleaks não encontrou segredos e Trivy não encontrou manifests de
  dependência vulneráveis. O gate Aurum segue indisponível tanto no PATH quanto
  no fallback documentado. Foram migrados 32 rollouts e 34 threads de
  `headroom` para `openai`; a TUI carregou o título, modelo, diretório e
  transcript da sessão solicitada sem repetir o erro de provider.
