## Context

O instalador já centraliza o merge em `tools/aiconfig.py`, enquanto os
wrappers apenas escolhem Python e repassam argumentos. Os testes cobrem o
comportamento de merge, ferramentas, Headroom e hardening, mas não existe uma
camada que valide o próprio checkout antes da primeira escrita. O CI executa
compilação e testes, porém não verifica todos os contratos documentados nos
adapters e no catálogo.

Ver `proposal.md` para a motivação e as delta specs para os contratos
observáveis.

## Goals / Non-Goals

**Goals:**

- Ter uma única implementação de preflight reutilizada pelo comando explícito
  `validate` e pelo caminho normal de instalação.
- Produzir o mesmo resultado semântico em Bash, PowerShell e execução direta
  do Python.
- Manter a validação independente de rede, gerenciadores de pacote e estado
  pessoal dos perfis dos agentes.
- Tornar cada falha acionável, com código estável, caminho relativo e saída
  JSON segura para CI.
- Transformar as garantias de portabilidade e segurança em testes regressivos.

**Non-Goals:**

- Substituir Semgrep, Gitleaks, Trivy ou Codex Security quando uma auditoria
  completa for necessária.
- Reescrever o merge existente ou remover configurações locais.
- Fazer rollback automático de uma instalação parcialmente concluída.
- Fazer o preflight iniciar Headroom, instalar ferramentas ou alterar o
  `config.toml` local do Codex.

## Decisions

### 1. O preflight será um subcomando do motor comum

Adicionar `validate` ao `tools/aiconfig.py`, com `--json` opcional. Os wrappers
aceitarão `--validate` e `validate`, traduzindo ambos para o subcomando comum.
Isso evita duas implementações divergentes e permite que CI execute o mesmo
contrato sem simular uma instalação.

Alternativa rejeitada: criar scripts independentes para Bash, PowerShell e
Python. Isso repetiria regras e recriaria exatamente o drift que a mudança
pretende detectar.

### 2. Validadores puros retornam um relatório estruturado

O núcleo será composto por verificadores sem efeitos colaterais que acumulam
itens com `code`, `severity`, `path`, `message` e `action`. O relatório terá
`schema_version`, `status`, `errors`, `warnings`, `skipped` e `checks`. A saída
humana será uma projeção desse relatório; a saída JSON usará somente caminhos
relativos e nunca imprimirá o conteúdo de um possível segredo.

Alternativa rejeitada: analisar apenas o código de saída de comandos externos.
Isso tornaria a validação dependente do ambiente e deixaria sem cobertura as
regras internas do repositório.

### 3. O preflight será dividido em camadas de custo crescente

As verificações rodarão nesta ordem:

1. estrutura e arquivos referenciados;
2. parse de JSON e TOML portátil, placeholders e catálogo de versões;
3. paridade dos adapters, cobertura do `doctor` e referências do workflow;
4. compilação Python e sintaxe Bash quando os executáveis existirem;
5. higiene de segurança embutida, com padrões de alta confiança e allowlist
   explícita para exemplos/testes.

Ferramentas externas ausentes serão `skipped` ou aviso, nunca instaladas pelo
preflight. Os comandos de auditoria completa continuam explícitos no
`WORKFLOW.md`.

### 4. A instalação falhará somente por erro estrutural obrigatório

`cmd_install` chamará o preflight antes de criar o contexto de escrita. Erros
obrigatórios encerram a operação sem backup, escrita, Headroom ou gerenciador
de pacotes. Avisos e verificações opcionais não impedem a instalação. O
`--dry-run` continuará sendo uma simulação da instalação, mas o novo
`validate` será o caminho recomendado para validar o checkout sem ruído de
destinos locais.

Alternativa rejeitada: fazer `--dry-run` acumular todas as responsabilidades de
validação. Dry-run responde "o que esta máquina faria"; preflight responde
"este repositório é distribuível".

### 5. Regras de caminho e segredo serão conservadoras e explicáveis

O scanner percorrerá somente arquivos versionados/relevantes do checkout,
ignorando `.git`, caches e arquivos gerados. Padrões de credencial exigirão
alta confiança e o relatório exibirá apenas o código da regra. Caminhos
absolutos serão permitidos apenas em documentação explicitamente marcada como
exemplo e em testes que usem diretórios temporários. O conjunto de exceções
ficará centralizado no validador e coberto por testes.

Alternativa rejeitada: proibir toda ocorrência de `C:\`, `/Users/` ou URLs. Isso
quebraria instruções legítimas de uso e exemplos portáveis.

### 6. CI terá um job de contrato além da suíte

O workflow existente manterá a matriz de testes. Será acrescentada uma etapa
de contrato que executa `python tools/aiconfig.py validate --json`, verifica a
sintaxe dos wrappers e preserva o teste de compilação. O CI não instalará
ferramentas globais apenas para executar o preflight; scans externos podem
continuar em jobs separados quando forem configurados.

### 7. A documentação será atualizada junto do contrato

README, mapa de configuração, `WORKFLOW.md`, help dos wrappers e delta specs
usarão a mesma sequência operacional. A validação verificará os pontos que
podem ser determinados sem um parser Markdown completo, enquanto o conteúdo
explicativo continuará sendo revisado por humanos.

### 8. Headroom não fará parte do caminho padrão dos provedores

O baseline do Claude não conterá `ANTHROPIC_BASE_URL`; o baseline do Codex não
selecionará `model_provider = "headroom"`. O instalador não executará
`headroom init`, `headroom install start` ou healthchecks de recuperação e não
instalará hooks que façam isso. Assim, uma falha do proxy não afeta uma sessão
normal dos agentes.

Alternativa rejeitada: manter o deployment persistente e apenas reiniciá-lo
quando `/readyz` falhar. Uma porta saudável não prova que o executor interno
consegue concluir requisições, e reinicialização concorrente pode duplicar
workers ou disputar o listener.

### 9. A ativação será explícita e isolada por agente

Claude usará `headroom wrap claude`, que injeta a rota somente no processo
filho e oferece a opção `--tool-search true`. Codex receberá um arquivo
`headroom.config.toml` separado, ativado apenas por `codex --profile headroom`.
Esse provider desabilitará WebSocket para evitar a classe de encerramentos de
stream observada no transporte proxyado.

Alternativa rejeitada: `headroom wrap codex` como padrão documentado. Além da
variável de sessão, esse wrapper registra MCP no config ativo; o perfil separado
torna a alteração de roteamento visível, reversível e independente do baseline.

### 10. Estabilidade terá prioridade sobre taxa de compressão

No Windows, as receitas opt-in desabilitarão Kompress e seu fallback, mantendo
somente compressores estruturais/passthrough. A concorrência não será elevada
automaticamente: o limite Anthropic já é derivado da CPU e aumentar paralelismo
durante vazamento de threads agrava a contenção. O `doctor` será passivo e
omitirá os valores de URLs ao relatar variáveis, hooks ou provider persistentes.

Alternativa rejeitada: recomendar `HEADROOM_MAX_CONCURRENCY=16`. Essa variável
não corresponde à interface atual; as opções suportadas têm semânticas distintas
e só devem ser ajustadas a partir de métricas.

### 11. Rollouts serão a fonte durável da recuperação de sessões

A recuperação do Codex será um comando separado e opt-in. Ela descobrirá todos
os rollouts em `~/.codex/sessions`, preservará os registros suplementares do
índice, fará backup consistente dos bancos SQLite pela API de backup e somente
então reconstruirá o índice. Threads já existentes serão associadas à raiz de
projeto mais específica, inclusive quando o Windows gravar caminhos com o
prefixo estendido `\\?\`.

Rollouts de execuções e subagentes ausentes da tabela de threads continuarão
indexados, mas não serão inseridos artificialmente no banco da interface. Isso
preserva todo o material recuperável sem inventar títulos, recência ou demais
campos internos. A operação será idempotente e verificará novamente o estado
depois de escrever.

Alternativa rejeitada: gerar novas conversas copiando mensagens dos JSONL. Isso
perderia metadados, duplicaria históricos e poderia alterar a ordem dos turnos;
o defeito observado é de índice/associação, não de conteúdo.

## Risks / Trade-offs

- **Falsos positivos em higiene de segurança** → padrões de alta confiança,
  allowlist pequena e testes para exemplos legítimos; mensagens sem valores.
- **Diferenças de Bash no Windows** → sintaxe Bash será uma verificação
  opcional; o contrato principal será executado pelo Python em todos os jobs.
- **Preflight bloquear uma instalação existente** → somente erros estruturais
  novos bloqueiam; o usuário pode corrigir a fonte e usar backup, sem opção de
  ignorar silenciosamente uma violação de segurança.
- **Relatório JSON virar API rígida cedo demais** → publicar `schema_version`
  desde a primeira versão e testar apenas os campos contratuais.
- **Drift futuro na documentação** → adicionar a validação ao CI e manter o
  fluxo de mudança OpenSpec como requisito de alterações comportamentais.
- **Configuração legada permanecer após atualizar o repo** → o `doctor` detecta
  as rotas/hooks sem expor valores e a documentação fornece `unwrap` e inspeção
  manual; a política de merge impede remoção silenciosa do perfil do usuário.
- **Menor economia com Kompress desativado** → aceitar a perda de compressão ML
  no Windows em troca de não bloquear o caminho até o provedor; a ativação
  futura exige evidência de estabilidade.

## Migration Plan

1. Implementar o relatório e os validadores sem alterar o comportamento do
   instalador.
2. Adicionar testes de sucesso, erro, ausência de ferramentas e ausência de
   efeitos colaterais.
3. Ligar o preflight ao início da instalação e aos dois wrappers.
4. Atualizar CI e documentação.
5. Rodar `validate`, suíte, dry-run, doctor, auditorias disponíveis e `aurum`
   na branch.
6. Para rollback, reverter a branch. Backups de instalações de usuário
   continuam sob o diretório de backup existente; o novo preflight não cria
   alterações que precisem ser revertidas.
7. Remover hooks/healthcheck Headroom do checkout, instalar o perfil Codex
   opt-in e validar que Claude/Codex padrão funcionem com o proxy desligado.
8. Auditar e recuperar o índice/associações das sessões locais, validar uma
   sessão conhecida e reiniciar a interface para recarregar a barra lateral.
