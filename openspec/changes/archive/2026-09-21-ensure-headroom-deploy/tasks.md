## 1. Healthcheck e integração no instalador

- [x] 1.1 Criar `tools/headroom_healthcheck.py` com leitura de `Status:` e
  `Healthy:`, start condicional, revalidação, modo dry-run e execução opcional
  do `init hook ensure`.
- [x] 1.2 Integrar o healthcheck ao fluxo comum de `tools/aiconfig.py` após a
  sincronização das configurações, preservando `--dry-run`, `--skip-tools`,
  avisos e códigos de saída do instalador.
- [x] 1.3 Instalar o script no destino do Codex com a política existente de
  backup/merge e adicionar os placeholders necessários sem caminhos absolutos.

## 2. Hook e merge portátil do Codex

- [x] 2.1 Adicionar `adapters/codex/hooks.json` com o healthcheck + ensure e
  timeout de 60 segundos.
- [x] 2.2 Ajustar o merge de hooks para priorizar o healthcheck antes de um
  ensure Headroom legado, sem remover entradas locais, e cobrir esse contrato
  com testes.

## 3. Regressão e documentação

- [x] 3.1 Adicionar testes unitários para status saudável, deploy parada,
  deploy não saudável, falha de start, ausência do executável e dry-run.
- [x] 3.2 Atualizar README/HEADROOM com a garantia de deploy, o comportamento
  best-effort quando Headroom não está instalado e o novo hook.
- [x] 3.3 Validar JSON/Python, executar a suíte, `--dry-run`, `--doctor` e
  `aurum check .`, registrando limitações de ambiente quando aplicável.
