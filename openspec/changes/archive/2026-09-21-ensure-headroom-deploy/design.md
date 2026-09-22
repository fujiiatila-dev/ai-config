## Context

O instalador delega configuração e preparação de ferramentas a
`tools/aiconfig.py`, mas não controla o ciclo de vida da deploy Headroom. O
Codex possui um hook local que chama `headroom init hook ensure`; em uma
máquina Windows reiniciada, a deploy pode estar parada e o comando excede o
timeout de 15 segundos.

## Goals / Non-Goals

**Goals:**

- Reutilizar uma única implementação portátil para detectar e recuperar a
  deploy `init-user`.
- Executar a recuperação depois da sincronização da configuração em Bash e
  PowerShell, com falha parcial e mensagem acionável se Headroom não existir.
- Instalar um hook Codex sem caminho absoluto no repositório e com timeout
  suficiente para o cold start.
- Preservar o merge seguro: arquivos diferentes continuam gerando conflito e
  nenhuma entrada de lista existente é removida.

**Non-Goals:**

- Instalar Headroom ou configurar o proxy global automaticamente.
- Criar persistência de serviço do Windows, tarefa agendada ou daemon próprio.
- Alterar configurações locais, credenciais ou permissões não gerenciadas.

## Decisions

1. **Healthcheck em script Python portátil.** `tools/headroom_healthcheck.py`
   será a fonte única da lógica de status/start/revalidação e será copiado para
   o diretório do Codex. O instalador chamará a cópia do repositório com o
   mesmo Python; o hook chamará a cópia instalada. Isso evita duplicar a
   interpretação de `Status:`/`Healthy:` em shells diferentes.

2. **Start somente quando necessário.** O script considera saudável apenas a
   combinação `Status: running` e `Healthy: yes`. Para `stopped` ou estado não
   saudável executa `install start --profile init-user`, aguardando no máximo
   o tempo necessário para o cold start e confirmando o status depois. Estado
   ilegível, executável ausente ou falha de start vira aviso/erro explícito,
   sem mascarar o status.

3. **Hook único com ensure opcional.** A fonte `adapters/codex/hooks.json`
   chama o script com `--ensure --marker`, com timeout de 60 segundos. Assim a
   recuperação ocorre antes do `init hook ensure` e o hook não depende de
   sintaxe de shell específica do Windows.

4. **Compatibilidade com hooks existentes.** O merge de hooks continuará
   unindo e preservando entradas, mas reconhecerá o comando de healthcheck como
   recuperação prioritária e o inserirá antes de um `headroom init hook ensure`
   existente no mesmo matcher. Instalações antigas continuam tendo o comando
   legado, agora precedido pelo reparo; não há remoção silenciosa.

5. **Substituição de placeholders.** O comando versionado usará
   `{{PYTHON}}`, `{{CODEX_HOME}}` e `{{HEADROOM}}`; o motor resolve esses
   valores na máquina de destino. Nenhum caminho absoluto será armazenado no
   repositório.

## Risks / Trade-offs

- [Headroom não está instalado] → manter a instalação de configuração
  utilizável, emitir aviso e deixar `--doctor` indicar a dependência ausente.
- [Cold start acima de 60 segundos] → o hook retorna erro explícito em vez de
  travar indefinidamente; o instalador revalida e reporta falha parcial.
- [Hook local tem personalização conflitante] → usar a política existente de
  conflito (`--keep-existing`, `--prefer-repo` ou pergunta), preservando o
  comportamento atual.

## Migration Plan

Executar o instalador normalmente. Ele fará backup antes de atualizar arquivos
gerenciados, copiará o healthcheck e mesclará o hook. Em caso de rollback,
restaurar o backup gerado e remover o hook/arquivo copiado após confirmar que
não é usado por outra configuração.
