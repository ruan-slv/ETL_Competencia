# ETL incremental de Recursos Humanos

Este fluxo usa os schemas `HumanResources` e `Person` do AdventureWorks para
carregar um modelo dimensional de funcionários no PostgreSQL. O Airflow agenda
as etapas; o código Python extrai, transforma e carrega os registros.

## Arquivos e responsabilidades

| Arquivo | Responsabilidade |
| --- | --- |
| `dags/carga_incremental_recursos_humanos.py` | Agenda a DAG diária e define as tarefas e dependências no Airflow. |
| `src/etl/carga_incremental_recursos_humanos.py` | Consulta alterações nas tabelas de RH, valida e transforma os dados e atualiza o Data Warehouse. |
| `src/sql/criar_data_warehouse.sql` | Cria dimensões, fatos, controles incrementais e índices no PostgreSQL. |
| `src/sql/indicadores.sql` | Implementa em SQL os dez indicadores definidos para funcionários. |
| `docs/modelo_estrela.mmd` | Diagrama editável dos dois esquemas estrela relacionados. |
| `src/settings.py` | Monta as conexões a partir das variáveis de ambiente do projeto. |

## Fontes do AdventureWorks e privacidade

As fontes principais são:

- `HumanResources.Employee`: cargo, gênero, estado civil, data de contratação,
  situação atual e horas de férias e afastamento.
- `HumanResources.Department` e `HumanResources.EmployeeDepartmentHistory`:
  departamentos, grupos e atribuição atual de cada funcionário.
- `HumanResources.Shift`: turno de trabalho e horários.
- `HumanResources.EmployeePayHistory`: histórico de taxas e frequência de
  pagamento.
- `Person.Person`: nome da pessoa associado ao identificador do funcionário.

O fluxo não extrai identificadores nacionais, login, senha, telefone, endereço,
currículo nem dados demográficos livres. `Person.Person` é usado somente para
nome e sobrenome. As taxas de remuneração são medidas sensíveis; o acesso ao
Data Warehouse deve ser limitado a quem precisa desses indicadores.

## Indicadores (KPIs)

As consultas completas estão em [`../src/sql/indicadores.sql`](../src/sql/indicadores.sql).

1. **Total de funcionários ativos:** conta linhas atuais do quadro usando
   `CurrentFlag`.
2. **Funcionários por departamento:** conta funcionários atuais pela última
   atribuição em aberto no histórico de departamentos.
3. **Funcionários por cargo:** conta funcionários atuais por `JobTitle`.
4. **Distribuição por gênero:** mostra contagens e percentuais por gênero
   registrado; não é uma medida completa de diversidade ou equidade.
5. **Contratações por ano:** conta funcionários pela data de contratação.
6. **Tempo médio de empresa:** calcula os anos entre contratação e data atual
   para funcionários atuais.
7. **Taxa média de remuneração mais recente:** seleciona o último registro
   salarial por funcionário e agrupa por departamento e frequência de pagamento.
   Frequências distintas são apresentadas separadamente, sem conversão ou soma.
8. **Variação da taxa de remuneração:** compara mudanças consecutivas apenas
   quando a frequência de pagamento é a mesma. A taxa não é anualizada.
9. **Horas de férias e afastamento registradas:** calcula as médias dos campos
   `VacationHours` e `SickLeaveHours` por departamento. São saldos do cadastro,
   não comprovação de horas efetivamente utilizadas.
10. **Funcionários por turno:** conta funcionários atuais por nome e horário do
    turno.

### Observação sobre a amostra

O banco AdventureWorks consultado contém 290 funcionários marcados como atuais,
datas de contratação entre 2006 e 2013 e 316 registros de remuneração. No
conjunto observado, todos os funcionários estavam marcados como atuais. Esses
números descrevem a amostra do banco de demonstração e não devem ser
interpretados como indicadores atuais de uma empresa real. A taxa de remuneração
também não deve ser comparada entre frequências diferentes.

## Modelo estrela e granularidade

O diagrama está em [`modelo_estrela.mmd`](./modelo_estrela.mmd). Há duas tabelas
fato que compartilham dimensões, formando dois esquemas estrela relacionados:

- **`fato_quadro_funcionario`:** uma linha por funcionário alterado ou incluído
  na carga, com a situação mais recente extraída, departamento, turno, data de
  contratação, horas registradas e a taxa de remuneração mais recente.
- **`fato_historico_remuneracao`:** uma linha por funcionário e instante de
  alteração da taxa de remuneração. A combinação de funcionário e data/hora da
  alteração é única.

Dimensões:

- **`dimensao_funcionario`:** código de origem, nome, cargo, gênero, estado
  civil, tipo de remuneração e situação atual.
- **`dimensao_departamento`:** código, nome e grupo do departamento.
- **`dimensao_turno`:** código, nome e horários do turno.
- **`dimensao_data`:** chave no formato `AAAAMMDD`, data, ano, trimestre, mês e
  dia da semana. É reutilizada para contratação e mudança de remuneração.

O dicionário detalhado com campos, tipos, chaves e significados está em
[`DICIONARIO_DADOS.md`](./DICIONARIO_DADOS.md). A dimensão zero de departamento
e turno significa “Não informado”.

## Etapas da DAG e dependências

A DAG `carga_incremental_recursos_humanos_adventureworks` executa diariamente,
com uma execução ativa por vez e sem backfill automático:

1. **`preparar_modelo_estrela`:** cria o schema, as dimensões, as tabelas fato,
   os índices e a tabela de controle. Pode ser repetida sem apagar os dados.
2. **`obter_identificador_execucao`:** obtém o identificador do Airflow para
   separar arquivos temporários concorrentes.
3. **`extrair_alteracoes`:** lê os marcadores persistidos, consulta as datas
   máximas de `ModifiedDate` e extrai funcionários afetados, departamentos,
   turnos e alterações de remuneração.
4. **`transformar_dados_extraidos`:** valida códigos, datas, horários, valores
   decimais e campos booleanos antes da carga.
5. **`carregar_data_warehouse`:** atualiza dimensões e fatos e grava os novos
   marcadores na mesma transação PostgreSQL.

As dependências são sequenciais: preparação → identificação → extração →
transformação → carga. Caminhos de arquivos pequenos trafegam pelo XCom; os
registros são escritos em JSON local, evitando transmitir conjuntos maiores pelo
XCom. O Compose monta `src/data/temporarios/` com permissão de escrita no
contêiner Airflow.

Para documentar a execução no artigo, habilite a DAG na interface do Airflow e
capture a visualização do fluxo e o histórico de uma execução concluída.

## Estratégia incremental

`controle_incremental_recursos_humanos` mantém um marcador independente para
cada tabela observada: funcionário, departamento, turno, histórico de
departamento, histórico de remuneração e pessoa. Na primeira execução, sem
marcadores, os registros são carregados. Depois, o processo consulta os registros
alterados desde o último marcador e atualiza o estado mais recente dos
funcionários afetados. Alterações de histórico salarial também são inseridas ou
atualizadas por funcionário e data/hora.

O limite inferior usa `ModifiedDate` estritamente maior que o marcador anterior,
evitando reprocessar em todas as execuções as linhas empatadas no último
instante. As chaves naturais e `ON CONFLICT` também permitem repetir uma carga
sem duplicar fatos. Dados e marcadores são confirmados na mesma transação no
PostgreSQL. Uma falha reverte ambos. Como ocorre com qualquer marcador baseado
somente em data/hora, duas alterações distintas com o mesmo `ModifiedDate`
máximo podem não ser distinguidas; para garantias contra esse caso e para
detectar exclusões físicas seria necessário Change Tracking, CDC ou reconciliação.

## Execução local

Com SQL Server, PostgreSQL, banco do Airflow e Airflow ativos, e o banco
`AdventureWorks2025` restaurado:

1. Acesse `http://localhost:8080`.
2. Habilite e execute `carga_incremental_recursos_humanos_adventureworks`.
3. Confira a execução e as tarefas na interface do Airflow.
4. Consulte os indicadores no PostgreSQL, schema `modelo_estrela`.

Para executar as mesmas etapas sem o agendador:

```powershell
docker compose exec airflow python -m src.etl.carga_incremental_recursos_humanos
```

Os scripts antigos `src.etl.extract`, `src.etl.transform` e `src.etl.load`
continuam sendo uma cópia completa e opcional de aterrissagem CSV. Eles não
fazem parte desta carga dimensional incremental.
