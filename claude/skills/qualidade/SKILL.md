---
name: qualidade
description: Audita o projeto atual com aurum check, corrige os problemas apontados e reporta o score antes/depois. Use quando o usuário pedir auditoria de qualidade, "rodar o padrão", verificar o score, ou antes de finalizar uma entrega. Meta padrão - score >= 70%.
---

# Auditoria de qualidade (aurum)

Audite o projeto atual contra o padrão FreedomAI e melhore o score.

## Passos

1. **Baseline**: rode a partir da raiz do projeto:
   ```powershell
   $env:PYTHONUTF8='1'; aurum check . --json
   ```
   Se `aurum` não resolver no PATH (`where.exe aurum` / `which aurum`), pare e
   informe que o gate não pôde ser executado; a instalação correta (via
   `uv tool install` do repositório generalrodolfao/standards) está no
   `TOOLS.md` do ai-config. Não instale o pacote `aurum` do PyPI (é outro
   projeto) e não declare score.
   Falso positivo conhecido na v0.4.0: `GIT-IGNORE-005` reprova `.gitignore`
   com `!.env.example`; não remova a negação, registre como falso positivo.
   Guarde o score e a lista de checks `failed`.

2. **Triagem**: separe os checks reprovados em:
   - **Corrigíveis com conteúdo real** (testes faltando, README sem exemplos,
     lint não configurado): corrija escrevendo código/config de verdade,
     coerente com o projeto.
   - **Auto-fix** (`aurum check . --fix` gera arquivos de template): use apenas
     para scaffolding (ex.: `.pre-commit-config.yaml`, estrutura de pastas) e
     **revise cada arquivo gerado** — nunca deixe template genérico sem adaptar.
   - **Não aplicáveis** ao tipo do projeto: liste como ignorados com
     justificativa de uma linha cada.

3. **Complementos do padrão** (além do aurum):
   - Rode a suíte de testes e o lint do projeto, se existirem (veja comandos
     no CLAUDE.md/AGENTS.md do projeto). Falhas aqui contam como reprovação.
   - Confira que `.env` está no `.gitignore` e que não há segredos commitados.

4. **Re-auditoria**: rode `aurum check .` de novo e compare com o baseline.

5. **Relatório final** (sempre em português):
   - Score antes → depois (meta: ≥ 70%).
   - O que foi corrigido (lista curta).
   - Checks ignorados e por quê.
   - Se a meta não foi atingida, o que falta e o esforço estimado.

## Regras

- Não sobrescreva arquivos existentes com templates do `--fix` sem comparar antes.
- Correções devem ser reais: não crie testes vazios ou docs placeholder só
  para passar no check — isso viola o propósito do padrão.
- Se o projeto não tiver `CLAUDE.md`/`AGENTS.md`, sugira rodar
  `powershell -File .\scripts\init-projeto.ps1` (quando o projeto fornecer esse script).
