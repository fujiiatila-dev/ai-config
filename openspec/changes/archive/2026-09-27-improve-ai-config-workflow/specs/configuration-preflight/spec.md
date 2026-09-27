## Purpose

Fornecer uma verificação determinística e somente leitura que prove que o
`ai-config` pode ser distribuído com segurança e coerência entre agentes,
plataformas e shells.

## ADDED Requirements

### Requirement: Preflight é somente leitura

O comando de validação SHALL executar a partir da raiz do repositório, SHALL
ser determinístico e SHALL NOT escrever configurações de usuário, instalar
ferramentas, iniciar serviços ou modificar o checkout.

#### Scenario: Preflight sem alterações

- **WHEN** o usuário executa a validação em um checkout válido
- **THEN** o comando termina com código zero e não altera arquivos, ferramentas
  ou processos externos

#### Scenario: Preflight detecta erro

- **WHEN** uma regra obrigatória falha
- **THEN** o comando termina com código diferente de zero e informa o arquivo,
  a regra e uma ação corretiva

### Requirement: Contratos do repositório são verificados

O preflight SHALL verificar a validade e a cobertura dos arquivos declarados
como parte da distribuição, incluindo JSON, TOML, Python, wrappers, adapters,
placeholders, catálogo de versões, comandos do `doctor` e referências ao
workflow compartilhado.

#### Scenario: Referência de origem ausente

- **WHEN** um mapa de instalação aponta para um arquivo que não existe
- **THEN** a validação reporta um erro com o caminho relativo da origem

#### Scenario: Referência de versão sem doctor

- **WHEN** `versions.json` contém uma ferramenta sem uma checagem correspondente
- **THEN** a validação reporta um erro de cobertura do `doctor`

#### Scenario: Placeholder não resolvido

- **WHEN** um template instalado contém um placeholder desconhecido ou inválido
- **THEN** a validação reporta o arquivo e o token que precisa ser corrigido

### Requirement: Higiene de portabilidade e segurança é verificada

O preflight SHALL rejeitar credenciais, tokens, caminhos absolutos de máquina,
endpoints não-loopback e dados de sessão nos arquivos versionados, permitindo
apenas exceções explícitas e documentadas para exemplos ou testes.

#### Scenario: Caminho local versionado

- **WHEN** um arquivo versionado contém um caminho específico da máquina do
  mantenedor
- **THEN** a validação falha e informa como substituir o valor por um
  placeholder ou configuração local

#### Scenario: Credencial detectada

- **WHEN** um arquivo versionado contém um padrão de segredo ou credencial
- **THEN** a validação falha sem imprimir o valor sensível no relatório

#### Scenario: Headroom exposto

- **WHEN** uma configuração aponta o proxy Headroom para um endereço diferente
  de loopback
- **THEN** a validação falha e exige `127.0.0.1` ou `localhost` conforme o
  contrato documentado

### Requirement: Relatório serve para humanos e CI

O comando SHALL oferecer saída legível por padrão e uma opção JSON estável,
contendo status, versão do relatório, contagens por severidade, identificadores
de regra e caminhos relativos. O JSON SHALL NOT conter segredos nem caminhos
absolutos da máquina.

#### Scenario: Relatório JSON válido

- **WHEN** o usuário executa a validação com a opção JSON
- **THEN** a saída é um único documento JSON parseável e o código de saída
  distingue sucesso de erro

#### Scenario: Aviso não bloqueante

- **WHEN** uma ferramenta opcional está ausente mas os contratos do repositório
  são válidos
- **THEN** a validação registra um aviso acionável e não o trata como erro

### Requirement: Dependências externas não são instaladas pelo preflight

O preflight SHALL usar apenas runtimes e comandos já disponíveis, SHALL
identificar verificações opcionais que não puder executar e SHALL deixar a
instalação ou atualização de ferramentas para os comandos explícitos existentes.

#### Scenario: Ferramenta opcional ausente

- **WHEN** Bash, ShellCheck ou uma ferramenta de segurança opcional não está
  disponível
- **THEN** a validação registra a verificação como ignorada ou aviso, sem
  instalar a ferramenta nem falhar por causa dessa ausência isolada
