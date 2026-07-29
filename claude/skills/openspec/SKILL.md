---
name: openspec
description: Gerencia o ciclo Spec-Driven Development (SDD) com OpenSpec. Use para propor, especificar, projetar, implementar e arquivar mudanças seguindo o fluxo propose → design → tasks → apply → archive. Complementar à skill qualidade — abre o ciclo antes de codificar.
version: 1.0.0
user-invocable: true
argument-hint: "[init|update|propose|explore|apply|sync|archive] [change-name]"
---

# OpenSpec — Spec-Driven Development

Guia o ciclo de especificação e desenvolvimento orientado por especificações
usando o OpenSpec. O objetivo é alinhar humano e IA no **que** construir antes
de escrever **como** construir.

## Pré-requisitos

```bash
# Instalação global (uma vez)
npm install -g @fission-ai/openspec@latest

# Inicialização no projeto (uma vez por projeto)
openspec init --tools claude
```

Isso cria a estrutura `openspec/` no projeto e registra os slash commands
`/opsx:*` no Claude Code.

## Comandos

### `/opsx:explore <tópico>`

Pensamento exploratório sem compromisso. Use quando a ideia ainda está difusa.

- O agente examina o codebase, pesa opções e ajuda a clarificar os requisitos
- **Não gera artefatos** — é um bate-papo estruturado

### `/opsx:propose <nome-da-feature>`

Inicia uma mudança nova. Gera **todos** os artefatos de planejamento de uma vez:

1. Lê `openspec/config.yaml` para contexto do projeto (tech stack, regras)
2. Cria `openspec/changes/<nome>/` com `.openspec.yaml`
3. Gera `proposal.md` — intenção, escopo, abordagem
4. Gera `specs/` delta — requisitos no formato Given/When/Then
5. Gera `design.md` — arquitetura técnica e decisões
6. Gera `tasks.md` — checklist granular de implementação

**Pare e aguarde revisão humana** antes de prosseguir.

### `/opsx:apply`

Implementa as tarefas de `tasks.md` sequencialmente:

1. Lê o primeiro item incompleto (`- [ ]`)
2. Edita os arquivos necessários
3. Roda testes e lint
4. Marca o item como concluído (`- [x]`)
5. Repete até todos os itens estarem feitos ou encontrar um bloqueio

Se o humano precisar ajustar o plano durante a execução:
`/opsx:update <nome> - <instrução>` — atualiza artefatos sem tocar no código.

### `/opsx:sync`

Mescla os delta specs da change folder de volta no `openspec/specs/` principal.
Geralmente executado automaticamente pelo archive.

### `/opsx:archive`

Finaliza a mudança:

1. Valida que todos os tasks estão completos
2. Oferece sync dos delta specs (se ainda não foi feito)
3. Move a pasta para `openspec/changes/archive/YYYY-MM-DD-<nome>/`

## Estrutura de diretórios

```text
openspec/
├── config.yaml               # Tech stack + regras de especificação
├── specs/                    # Especificação permanente (fonte da verdade)
│   ├── auth/
│   │   └── spec.md
│   └── ui/
│       └── spec.md
└── changes/                  # Mudanças em andamento
    ├── minha-feature/
    │   ├── .openspec.yaml
    │   ├── proposal.md
    │   ├── specs/
    │   │   └── spec.md
    │   ├── design.md
    │   └── tasks.md
    └── archive/              # Mudanças concluídas (histórico imutável)
```

## Exemplo de `openspec/config.yaml`

```yaml
schema: spec-driven
context: |
  Tech stack: Angular 18, Node.js, Express, Metabase
  Testing: Vitest, Playwright
rules:
  specs:
    - Use Given/When/Then format for scenarios
    - Each spec SHALL reference RFC 2119 keywords
  design:
    - Include sequence diagrams for complex async flows
```

## Regras

- Sempre pare após `/opsx:propose` — o humano precisa revisar antes de aplicar
- Não pule etapas: proposal → specs → design → tasks → apply → archive
- Se o projeto já tem `openspec/`, use `openspec update` para refrescar commands
- Mantenha `config.yaml` atualizado com o tech stack real do projeto
