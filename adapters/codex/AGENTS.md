# Codex — configuração compartilhada

O padrão de trabalho é mantido em `WORKFLOW.md`, instalado na mesma pasta.
Leia-o antes de começar; ele é a fonte única para OpenSpec, qualidade,
segurança, RTK e Headroom.

@WORKFLOW.md

Antes de sincronizar, valide o checkout (`./install.sh --validate` ou
`.\install.ps1 --validate`) e revise o `--dry-run`. A instalação efetiva repete
o preflight antes de escrever no perfil do Codex.

## Configuração do Codex

O instalador oferece um baseline portátil e restrito em
`config.toml.example`. Para sincronizar sem atualizar ferramentas:

```bash
./install.sh --keep-existing
```

No Windows PowerShell:

```powershell
.\install.ps1 --keep-existing
```

Atualizações globais exigem `--update-tools`. O hardening exige
`--harden-codex`, cria backup antes da escrita e remove somente uma confiança
exata na raiz do perfil quando a seção contém apenas `trust_level`. Confianças
de projetos específicos, credenciais, sessões, memória e arquivos locais não
são copiados para este repositório.
