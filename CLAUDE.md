# ai-config — instruções para quem edita este repositório

Repositório de configuração portátil para agentes de IA. O que está aqui é
instalado nas máquinas de trabalho por `install.sh` / `install.ps1`.

## Estrutura

| Pasta | Conteúdo |
| --- | --- |
| `claude/` | tudo que vai para `~/.claude` (settings, instruções, agents, skills, statusline) |
| `adapters/codex/`, `adapters/gemini/`, `adapters/rtk/` | equivalentes para os outros clientes |
| `shared/WORKFLOW.md` | **fonte única** do padrão de trabalho, instalada nos três |
| `tools/aiconfig.py` | motor de instalação e merge; `install.sh`/`install.ps1` só o chamam |
| `versions.json` | referências de versão lidas por `--doctor` |

## Regras ao mexer aqui

1. **O instalador nunca sobrescreve em silêncio.** Qualquer mudança em
   `tools/aiconfig.py` tem de preservar as quatro regras: adiciona o que falta,
   ignora o que já é igual, pergunta no conflito, e nunca remove entrada de
   lista. Valide com `./install.sh --dry-run`.

2. **Nada de caminho absoluto no repositório.** Use os placeholders
   `{{PYTHON}}`, `{{NODE}}`, `{{CLAUDE_HOME}}`, `{{HEADROOM_PORT}}`, resolvidos
   na máquina de destino.

3. **Regra de trabalho vai em `shared/WORKFLOW.md`**, não duplicada em
   `claude/CLAUDE.md`, `adapters/codex/AGENTS.md` ou `adapters/gemini/GEMINI.md`
   — esses três apenas apontam para ele.

4. **Permissões versionadas são só as portáteis.** Nada de caminho de máquina,
   `localhost:<porta>` ou comando de um projeto específico. Isso é
   `settings.local.json`, que o instalador não toca.

5. Não versione credenciais, tokens, histórico de sessão nem memória.

## Antes de commitar

```bash
./install.sh --dry-run     # não pode acusar escrita indevida
./install.sh --doctor      # ferramentas externas
python3 -m py_compile tools/aiconfig.py claude/statusline.py
```
