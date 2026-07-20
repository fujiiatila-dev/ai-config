# ai-config

Configuração padrão pessoal do Claude Code — skills, subagentes, hooks e settings — para replicar o ambiente de trabalho em qualquer máquina.

## Estrutura

```
claude/                  # espelho de ~/.claude
  CLAUDE.md              # instruções globais (importa @RTK.md)
  RTK.md                 # instruções do RTK (proxy de economia de tokens)
  settings.json          # modelo, permissões, hooks (rtk + impeccable)
  statusline.py          # statusline customizada
  agents/                # subagentes globais
    backend-engineer.md
    frontend-engineer.md
    mcp-engineer.md
    qa.md
    tester.md
    impeccable-manual-edit-applier.md
  skills/
    qualidade/           # skill própria de qualidade
    impeccable/          # skill de design de front-end (terceiro, ver Licenças)
```

## Instalação em uma máquina nova

```bash
git clone https://github.com/fujiiatila-dev/ai-config.git
cd ai-config
./install.sh
```

O script copia os arquivos para `~/.claude/` (fazendo backup do `settings.json` existente).

### Dependências externas (não versionadas aqui)

1. **rtk** (hook de economia de tokens no PreToolUse):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
   ```
2. **Node.js** (necessário para o detector do impeccable no PostToolUse). Instalação sem sudo:
   baixe o binário LTS de https://nodejs.org/dist/, extraia em `~/.local/lib` e crie symlinks de
   `node`, `npm` e `npx` em `~/.local/bin`.
   > O caminho do node no hook do `settings.json` é absoluto (`/home/atila/.local/bin/node`) —
   > ajuste se o usuário/home da máquina for outro.

Depois reinicie o Claude Code.

## Licenças

- `claude/skills/impeccable/` é derivado de [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
  (Apache License 2.0 — ver `claude/skills/impeccable/LICENSE`).
- O restante é configuração pessoal.
