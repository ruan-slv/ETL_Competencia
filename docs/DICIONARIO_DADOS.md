# Dicionário de dados do modelo de Recursos Humanos

Schema PostgreSQL: `modelo_estrela`.

## Dimensões

### `dimensao_funcionario`

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `chave_funcionario` | `BIGINT` | Primária | Chave substituta do funcionário. |
| `codigo_funcionario_origem` | `INTEGER` | Única | `BusinessEntityID` do funcionário no SQL Server. |
| `primeiro_nome` | `VARCHAR(100)` | — | Primeiro nome de `Person.Person`. |
| `nome_do_meio` | `VARCHAR(100)` | — | Nome do meio, quando informado. |
| `sobrenome` | `VARCHAR(100)` | — | Sobrenome de `Person.Person`. |
| `titulo` | `VARCHAR(20)` | — | Tratamento ou título cadastrado na origem. |
| `cargo` | `VARCHAR(100)` | — | Cargo atual em `HumanResources.Employee.JobTitle`. |
| `genero` | `CHAR(1)` | — | Valor de gênero cadastrado na origem. |
| `estado_civil` | `CHAR(1)` | — | Estado civil cadastrado na origem. |
| `salario_fixo` | `BOOLEAN` | — | Indica o valor de `SalariedFlag`; não converte a taxa em salário anual. |
| `funcionario_atual` | `BOOLEAN` | — | Indica o valor de `CurrentFlag`. |

### `dimensao_departamento`

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `chave_departamento` | `BIGINT` | Primária | Chave substituta; zero identifica o departamento não informado. |
| `codigo_departamento_origem` | `INTEGER` | Única | `DepartmentID` no SQL Server; nulo na linha padrão. |
| `nome_departamento` | `VARCHAR(100)` | — | Nome do departamento. |
| `grupo_departamento` | `VARCHAR(100)` | — | Grupo ao qual a origem associa o departamento. |

### `dimensao_turno`

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `chave_turno` | `BIGINT` | Primária | Chave substituta; zero identifica o turno não informado. |
| `codigo_turno_origem` | `INTEGER` | Única | `ShiftID` no SQL Server; nulo na linha padrão. |
| `nome_turno` | `VARCHAR(100)` | — | Nome do turno. |
| `horario_inicio` | `TIME` | — | Horário inicial do turno. |
| `horario_fim` | `TIME` | — | Horário final do turno. |

### `dimensao_data`

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `chave_data` | `INTEGER` | Primária | Chave no formato `AAAAMMDD`. |
| `data` | `DATE` | Única | Data completa. |
| `ano` | `SMALLINT` | — | Ano da data. |
| `trimestre` | `SMALLINT` | — | Trimestre de 1 a 4. |
| `mes` | `SMALLINT` | — | Mês de 1 a 12. |
| `nome_mes` | `VARCHAR(20)` | — | Nome do mês em português. |
| `dia` | `SMALLINT` | — | Dia do mês. |
| `dia_da_semana` | `SMALLINT` | — | Dia ISO da semana, de 1 (segunda-feira) a 7 (domingo). |
| `nome_dia_da_semana` | `VARCHAR(20)` | — | Nome do dia da semana em português. |

## Tabelas fato

### `fato_quadro_funcionario`

Granularidade: uma linha por funcionário e seu estado mais recente extraído.

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `chave_registro` | `BIGINT` | Primária | Chave substituta do registro de quadro. |
| `codigo_funcionario_origem` | `INTEGER` | Única | Código natural do funcionário na origem. |
| `chave_funcionario` | `BIGINT` | Estrangeira | Referência a `dimensao_funcionario`. |
| `chave_departamento` | `BIGINT` | Estrangeira | Referência ao departamento mais recente; zero quando não informado. |
| `chave_turno` | `BIGINT` | Estrangeira | Referência ao turno mais recente; zero quando não informado. |
| `chave_data_contratacao` | `INTEGER` | Estrangeira | Referência à data de contratação em `dimensao_data`. |
| `funcionario_atual` | `BOOLEAN` | — | Situação de funcionário na última extração. |
| `horas_ferias` | `SMALLINT` | — | Horas de férias registradas no cadastro. |
| `horas_afastamento` | `SMALLINT` | — | Horas de afastamento registradas no cadastro. |
| `taxa_remuneracao_atual` | `NUMERIC(19,4)` | — | Taxa mais recente associada ao funcionário. |
| `frequencia_pagamento_atual` | `SMALLINT` | — | Código de frequência da taxa mais recente, mantido como na origem. |

### `fato_historico_remuneracao`

Granularidade: uma linha por funcionário e instante de alteração da taxa de
remuneração.

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `chave_evento` | `BIGINT` | Primária | Chave substituta da alteração. |
| `codigo_funcionario_origem` | `INTEGER` | Parte da chave única | Código natural do funcionário. |
| `chave_funcionario` | `BIGINT` | Estrangeira | Referência a `dimensao_funcionario`. |
| `chave_data_alteracao` | `INTEGER` | Estrangeira | Data da alteração em `dimensao_data`. |
| `data_alteracao` | `TIMESTAMP` | Parte da chave única | Instante original da alteração. |
| `taxa_remuneracao` | `NUMERIC(19,4)` | — | Taxa informada em `EmployeePayHistory.Rate`. |
| `frequencia_pagamento` | `SMALLINT` | — | Código `PayFrequency` preservado, sem anualização. |

## Controle de carga

### `controle_incremental_recursos_humanos`

| Campo | Tipo PostgreSQL | Chave | Descrição |
| --- | --- | --- | --- |
| `tabela_origem` | `VARCHAR(100)` | Primária | Nome qualificado da tabela monitorada no SQL Server. |
| `ultima_modificacao` | `TIMESTAMP` | — | Maior `ModifiedDate` persistido para a origem. |
| `atualizado_em` | `TIMESTAMPTZ` | — | Instante em que o marcador foi confirmado no destino. |
