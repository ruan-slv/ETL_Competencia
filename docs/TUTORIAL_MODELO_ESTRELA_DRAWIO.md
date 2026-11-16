# Tutorial formal: modelagem do esquema estrela no draw.io

## 1. Objetivo

Este documento orienta a construção, no draw.io, de um diagrama do Data
Warehouse de Recursos Humanos do projeto ETL Competência. O diagrama representa
as tabelas e relações implementadas no PostgreSQL e atende à documentação do
modelo dimensional exigida no trabalho.

O modelo contém dois esquemas estrela relacionados: um para o quadro atual de
funcionários e outro para o histórico de remuneração. Ambos compartilham as
dimensões de funcionário e data. Portanto, o desenho deve apresentar as duas
tabelas fato, sem inventar relações que não existem no banco.

## 2. Fontes de referência

Antes de desenhar, consulte:

- [`README.md`](../README.md): contexto do projeto, fontes e finalidade da ETL.
- [`criar_data_warehouse.sql`](../src/sql/criar_data_warehouse.sql): nomes,
  colunas, tipos e chaves implementados.
- [`DICIONARIO_DADOS.md`](./DICIONARIO_DADOS.md): descrição funcional das
  colunas e granularidade.
- [`indicadores.sql`](../src/sql/indicadores.sql): uso analítico das tabelas
  para calcular as KPIs.
- [`modelo_estrela.mmd`](./modelo_estrela.mmd): representação textual das
  entidades e relações do modelo.

O esquema PostgreSQL chama-se `modelo_estrela`. A origem é o AdventureWorks,
com dados dos schemas `HumanResources` e `Person`; o destino analítico é o
PostgreSQL.

## 3. Estrutura conceitual a representar

### 3.1 Dimensões

**DIMENSAO_FUNCIONARIO**

- **PK** `chave_funcionario`
- `codigo_funcionario_origem` (único)
- `primeiro_nome`
- `nome_do_meio`
- `sobrenome`
- `titulo`
- `cargo`
- `genero`
- `estado_civil`
- `salario_fixo`
- `funcionario_atual`

**DIMENSAO_DEPARTAMENTO**

- **PK** `chave_departamento`
- `codigo_departamento_origem` (único; nulo na linha padrão)
- `nome_departamento`
- `grupo_departamento`

**DIMENSAO_TURNO**

- **PK** `chave_turno`
- `codigo_turno_origem` (único; nulo na linha padrão)
- `nome_turno`
- `horario_inicio`
- `horario_fim`

**DIMENSAO_DATA**

- **PK** `chave_data` (formato `AAAAMMDD`)
- `data` (única)
- `ano`
- `trimestre`
- `mes`
- `nome_mes`
- `dia`
- `dia_da_semana`
- `nome_dia_da_semana`

### 3.2 Tabelas fato

**FATO_QUADRO_FUNCIONARIO**

Granularidade: uma linha por funcionário e seu estado mais recente extraído.

- **PK** `chave_registro`
- `codigo_funcionario_origem` (único)
- **FK** `chave_funcionario` → `DIMENSAO_FUNCIONARIO.chave_funcionario`
- **FK** `chave_departamento` → `DIMENSAO_DEPARTAMENTO.chave_departamento`
- **FK** `chave_turno` → `DIMENSAO_TURNO.chave_turno`
- **FK** `chave_data_contratacao` → `DIMENSAO_DATA.chave_data`
- `funcionario_atual`
- `horas_ferias`
- `horas_afastamento`
- `taxa_remuneracao_atual`
- `frequencia_pagamento_atual`

**FATO_HISTORICO_REMUNERACAO**

Granularidade: uma linha por funcionário e instante de alteração da taxa de
remuneração.

- **PK** `chave_evento`
- `codigo_funcionario_origem`
- **FK** `chave_funcionario` → `DIMENSAO_FUNCIONARIO.chave_funcionario`
- **FK** `chave_data_alteracao` → `DIMENSAO_DATA.chave_data`
- `data_alteracao` (timestamp da alteração)
- `taxa_remuneracao`
- `frequencia_pagamento`
- Restrição única: (`codigo_funcionario_origem`, `data_alteracao`)

`codigo_funcionario_origem` na tabela de histórico é identificador natural e
participa da restrição única. A chave estrangeira formal para a dimensão é
`chave_funcionario`.

### 3.3 Relações e cardinalidades

Desenhe cada dimensão no lado “um” e a tabela fato correspondente no lado
muitos:

| Origem (1) | Destino (N) | Colunas relacionadas |
| --- | --- | --- |
| `DIMENSAO_FUNCIONARIO` | `FATO_QUADRO_FUNCIONARIO` | `chave_funcionario` |
| `DIMENSAO_DEPARTAMENTO` | `FATO_QUADRO_FUNCIONARIO` | `chave_departamento` |
| `DIMENSAO_TURNO` | `FATO_QUADRO_FUNCIONARIO` | `chave_turno` |
| `DIMENSAO_DATA` | `FATO_QUADRO_FUNCIONARIO` | `chave_data` → `chave_data_contratacao` |
| `DIMENSAO_FUNCIONARIO` | `FATO_HISTORICO_REMUNERACAO` | `chave_funcionario` |
| `DIMENSAO_DATA` | `FATO_HISTORICO_REMUNERACAO` | `chave_data` → `chave_data_alteracao` |

A dimensão data tem dois papéis no diagrama: data de contratação e data da
alteração de remuneração. Ela pode ser desenhada como uma única tabela com dois
conectores, identificando o papel em cada relação, ou como duas cópias visuais
da dimensão com os nomes `DIMENSAO_DATA (contratação)` e
`DIMENSAO_DATA (alteração)`. Se usar cópias visuais, indique que ambas
representam a mesma dimensão física `modelo_estrela.dimensao_data`.

Não conecte diretamente `FATO_HISTORICO_REMUNERACAO` a departamento ou turno:
essas FKs não existem nessa tabela. A KPI de remuneração por departamento
relaciona o histórico ao quadro por `codigo_funcionario_origem` e obtém o
departamento por `FATO_QUADRO_FUNCIONARIO`.

## 4. Procedimento no draw.io

1. Abra [app.diagrams.net](https://app.diagrams.net/) e escolha onde salvar o
   arquivo. Use o repositório do projeto ou outro local definido para os
   artefatos do trabalho.
2. Crie um diagrama em branco e atribua um título, por exemplo,
   **Modelo estrela — Recursos Humanos AdventureWorks**.
3. Ative a biblioteca de formas de banco de dados ou entidade-relacionamento.
   Caso não esteja disponível, use retângulos com título e lista de atributos.
4. Crie seis caixas: quatro dimensões (`DIMENSAO_FUNCIONARIO`,
   `DIMENSAO_DEPARTAMENTO`, `DIMENSAO_TURNO`, `DIMENSAO_DATA`) e duas fatos
   (`FATO_QUADRO_FUNCIONARIO`, `FATO_HISTORICO_REMUNERACAO`).
5. Dentro de cada caixa, liste os atributos da seção 3. Marque visualmente
   `PK`, `FK` e restrições únicas. Mantenha os nomes das colunas iguais aos do
   SQL, para que o desenho possa ser conferido contra o banco.
6. Posicione `FATO_QUADRO_FUNCIONARIO` no centro do primeiro esquema estrela e
   distribua ao redor suas quatro dimensões. Posicione
   `FATO_HISTORICO_REMUNERACAO` como segundo fato, próximo das dimensões
   funcionário e data.
7. Ligue as tabelas conforme a matriz de cardinalidade. Use cardinalidade
   `1` no lado da dimensão e `N` no lado da fato. Identifique os nomes das
   FKs junto aos conectores, especialmente os dois papéis de data.
8. Use cores consistentes para distinguir dimensões e fatos. Inclua uma
   legenda, por exemplo: azul para dimensões, laranja para fatos, `PK` para
   chave primária e `FK` para chave estrangeira.
9. Acrescente uma nota com as granularidades das duas fatos e outra nota:
   **As duas estrelas compartilham dimensões de funcionário e data.**
10. Acrescente uma nota separada para
    `controle_incremental_recursos_humanos`, se desejar documentar o fluxo
    operacional da ETL. Identifique-a como tabela de controle, fora do modelo
    dimensional e sem conectores para as fatos.
11. Revise o diagrama usando a lista de verificação da seção 5.
12. Salve o arquivo editável como `.drawio` e exporte uma cópia em PDF ou PNG
    para inserir no artigo ou relatório. Mantenha o arquivo editável para
    futuras atualizações.

## 5. Lista de verificação do modelo

- [ ] Todas as seis tabelas dimensionais/fato têm nomes correspondentes ao SQL.
- [ ] Cada tabela exibe suas chaves primária e estrangeiras corretas.
- [ ] `FATO_QUADRO_FUNCIONARIO` representa um registro atual por funcionário.
- [ ] `FATO_HISTORICO_REMUNERACAO` representa cada instante de alteração.
- [ ] As cardinalidades são um-para-muitos, da dimensão para a fato.
- [ ] A dimensão data está ligada às datas de contratação e alteração nos
      respectivos fatos.
- [ ] Departamento e turno estão ligados somente a
      `FATO_QUADRO_FUNCIONARIO`.
- [ ] Não foi criada uma relação direta entre histórico de remuneração e
      departamento/turno.
- [ ] A tabela de controle incremental está separada do esquema estrela.
- [ ] Os nomes e atributos podem ser conferidos em
      [`criar_data_warehouse.sql`](../src/sql/criar_data_warehouse.sql).

## 6. Entrega e validação

Entregue o diagrama editável (`.drawio`) e uma exportação legível (PDF ou PNG).
No artigo, descreva o objetivo analítico, as duas granularidades, as dimensões
compartilhadas e as relações entre dimensões e fatos. A representação visual
deve ser consistente com as tabelas usadas pelas dez KPIs em
[`indicadores.sql`](../src/sql/indicadores.sql).

O diagrama documenta a estrutura dimensional; ele não substitui a validação da
ETL. A execução da DAG e as consultas das KPIs devem ser verificadas
separadamente no Airflow e no PostgreSQL.
