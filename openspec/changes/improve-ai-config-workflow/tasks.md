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
