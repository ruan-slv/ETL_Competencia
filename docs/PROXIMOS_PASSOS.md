# Próximos passos para usar o projeto

Este documento descreve o que fazer depois que o ambiente Docker Compose já
está no ar, seguindo a ordem necessária para popular o Data Warehouse e
executar a ETL incremental.

Os comandos abaixo consideram o **PowerShell** na raiz do projeto
(`C:\Users\ruang\OneDrive\Desktop\ETL_Competencia`).

## Estado esperado antes de começar

| Item | Como conferir | Resultado esperado |
| --- | --- | --- |
| Docker Desktop em execução | `docker compose ps` | quatro containers `Up`; `postgres`, `airflow-db` e `sqlserver` como `healthy` |
| Airflow respondendo | `http://localhost:8080` | tela de login do Airflow |
| DAG carregada | `docker compose exec airflow airflow dags list` | `carga_incremental_recursos_humanos_adventureworks` |
| Backup disponível | `docker compose exec -T sqlserver ls -lh /var/opt/mssql/backup/` | `AdventureWorks2025.bak` (aprox. 48 MB) |
| `.env` preenchido | `Get-Content .env` | todas as variáveis com valor, sem campos vazios |

Se algum item não estiver de acordo, consulte a seção
[Diagnóstico](#diagnóstico-rápido) antes de continuar.

> O arquivo `.env` contém as senhas locais e não é versionado. O usuário do
> PostgreSQL é o valor de `POSTGRES_USER`; nos exemplos deste documento usamos
> `etl_user`, que é o valor atualmente configurado. Ajuste os comandos se o seu
> `.env` usar outro usuário.

## Passo 1 — Restaurar o AdventureWorks no SQL Server

O backup é disponibilizado ao container, mas **não é restaurado
automaticamente**. A restauração é feita pelo programa
[`../src/fetch_backup/fetch_backup.py`](../src/fetch_backup/fetch_backup.py),
executado dentro do container do Airflow (que já tem `pyodbc` e o driver ODBC
instalados):

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py
```

Resultado esperado:

```text
Banco 'AdventureWorks2025' restaurado com sucesso.
```

Comportamento do programa:

- Usa as variáveis `SQLSERVER_*` definidas no `docker-compose.yaml`.
- Lê o backup em `/var/opt/mssql/backup/AdventureWorks2025.bak`, que é o
  caminho visto pelo container do SQL Server.
- Se o banco `AdventureWorks2025` já existir, **interrompe** para evitar
  sobrescrita.

Opções úteis:

| Opção | Descrição |
| --- | --- |
| `--replace` | Substitui um banco de mesmo nome, encerrando as conexões ativas |
| `--database <nome>` | Restaura com outro nome de banco |
| `--backup <caminho>` | Usa outro arquivo `.bak` (caminho visto pelo SQL Server) |

Para refazer a restauração:

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py --replace
```

> O backup `AdventureWorks2025.bak` foi gerado no SQL Server 2025 e exige a
> imagem `mcr.microsoft.com/mssql/server:2025-latest`. Em uma instância 2022 a
> restauração falha com erro de versão.

### Conferir a restauração

```powershell
"SELECT name, state_desc FROM sys.databases`nGO`n" |
  docker compose exec -T sqlserver sh -c 'SQLCMDPASSWORD=$MSSQL_SA_PASSWORD /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C'
```

O banco `AdventureWorks2025` deve aparecer com estado `ONLINE`. A senha é lida
da variável `MSSQL_SA_PASSWORD` já definida dentro do container, portanto não é
necessário digitá-la.

## Passo 2 — Preparar o Data Warehouse

O schema `modelo_estrela` é criado automaticamente pela primeira tarefa da DAG
(`preparar_modelo_estrela`), que executa
[`../src/sql/criar_data_warehouse.sql`](../src/sql/criar_data_warehouse.sql).

Há duas formas de fazer isso.

### Opção A — Pela DAG (recomendado)

Basta executar a DAG no Passo 3: a tarefa `preparar_modelo_estrela` roda antes
da extração e cria/atualiza as tabelas.

### Opção B — Manualmente, pela linha de comando

O comando abaixo executa a preparação, a extração, a transformação e a carga
completa:

```powershell
docker compose exec airflow python -m src.etl.carga_incremental_recursos_humanos
```

Resultado esperado:

```text
Carga incremental concluída: {...}
```

> Não execute o `criar_data_warehouse.sql` com `psql -f` a partir do host: o
> arquivo **não está montado** no container do PostgreSQL. Use uma das opções
> acima, que leem o SQL a partir do container do Airflow.

## Passo 3 — Despausar e executar a DAG

### Pela interface web

1. Acesse `http://localhost:8080`.
2. Entre como usuário `admin`. A senha é gerada na primeira inicialização e
   aparece nos logs; para consultá-la:

   ```powershell
   docker compose logs airflow | Select-String "Password for user 'admin'"
   ```

3. Localize a DAG `carga_incremental_recursos_humanos_adventureworks`.
4. Despause a DAG (botão de liga/desliga).
5. Clique em **Trigger** para iniciar uma execução manual.
6. Acompanhe as cinco tarefas na visão de grafo.

### Pela linha de comando

```powershell
docker compose exec airflow airflow dags unpause carga_incremental_recursos_humanos_adventureworks
docker compose exec airflow airflow dags trigger carga_incremental_recursos_humanos_adventureworks
```

A DAG também está agendada como `@daily`, mas `catchup=False`, portanto
execuções antigas não são disparadas retroativamente.

## Passo 4 — Validar a carga

### Verificar o resultado da execução

```powershell
docker compose exec airflow airflow dags list-runs -d carga_incremental_recursos_humanos_adventureworks
```

Na interface, as cinco tarefas devem terminar com estado **success**:

1. `preparar_modelo_estrela`
2. `obter_identificador_execucao`
3. `extrair_alteracoes`
4. `transformar_dados_extraidos`
5. `carregar_data_warehouse`

### Conferir as tabelas no PostgreSQL

```powershell
docker compose exec -T postgres psql -U etl_user -d dw -c @"
SELECT 'dimensao_funcionario' AS tabela, COUNT(*) FROM modelo_estrela.dimensao_funcionario
UNION ALL SELECT 'dimensao_departamento', COUNT(*) FROM modelo_estrela.dimensao_departamento
UNION ALL SELECT 'dimensao_turno', COUNT(*) FROM modelo_estrela.dimensao_turno
UNION ALL SELECT 'dimensao_data', COUNT(*) FROM modelo_estrela.dimensao_data
UNION ALL SELECT 'fato_quadro_funcionario', COUNT(*) FROM modelo_estrela.fato_quadro_funcionario
UNION ALL SELECT 'fato_historico_remuneracao', COUNT(*) FROM modelo_estrela.fato_historico_remuneracao;
"@
```

### Executar as dez KPIs

```powershell
Get-Content src/sql/indicadores.sql -Raw |
  docker compose exec -T postgres psql -U etl_user -d dw
```

Os resultados observados estão documentados em
[`RESULTADOS_KPIS.md`](./RESULTADOS_KPIS.md).

### Confirmar o comportamento incremental

Execute a DAG uma segunda vez sem alterar dados na origem. O esperado é que a
carga processe zero registros novos, pois os marcadores de `ModifiedDate`
ficam na tabela `modelo_estrela.controle_incremental_recursos_humanos`:

```powershell
docker compose exec airflow python -m src.etl.carga_incremental_recursos_humanos
```

## Passo 5 (opcional) — Cópia de aterrissagem em CSV

Esse fluxo é uma cópia completa das tabelas para CSV e **não substitui** a
carga incremental exigida no trabalho. Depois de restaurar o AdventureWorks:

```powershell
docker compose exec airflow python -m src.etl.extract
docker compose exec airflow python -m src.etl.transform
docker compose exec airflow python -m src.etl.load
```

Os arquivos são gravados em `src/data/csv/raw/` e `src/data/csv/transformed/`.
Mais detalhes no [`../README.md`](../README.md).

## Diagnóstico rápido

| Sintoma | Causa provável | Ação |
| --- | --- | --- |
| `service "airflow-db" has no container to start` | containers ainda não criados ou removidos | use `docker compose up -d`, não `start` |
| `dependency failed to start: container ... is unhealthy` | variáveis vazias no `.env` ou volume inicializado com configuração inválida | preencha o `.env`, rode `docker compose down -v` e suba de novo |
| `role "etl" does not exist` | o usuário do PostgreSQL é outro | confira `POSTGRES_USER` no `.env` e ajuste o `-U` |
| Airflow não abre em `localhost:8080` | container ainda inicializando ou porta ocupada | `docker compose logs airflow` e `docker compose ps` |
| DAG não aparece | erro de importação | `docker compose exec airflow airflow dags list-import-errors` |
| Restauração falha por versão | imagem do SQL Server incompatível com o backup | use `mcr.microsoft.com/mssql/server:2025-latest` |
| `Banco 'AdventureWorks2025' já existe` | restauração repetida | acrescente `--replace` |

Comandos gerais de apoio:

```powershell
docker compose ps
docker compose logs -f postgres
docker compose logs -f airflow
docker compose exec airflow airflow dags list-import-errors
```

## Cuidados com os dados

- `docker compose down` remove os containers, mas **preserva os volumes**.
- `docker compose down -v` remove **também os volumes** e apaga o Data
  Warehouse, o banco do Airflow e a instância do SQL Server. Use apenas quando
  quiser recomeçar do zero.
- O `.env` é ignorado pelo Git (`.gitignore`); não versione senhas.
- O modo `standalone` do Airflow é exclusivo para desenvolvimento local.

## Referências

- [`../README.md`](../README.md) — visão geral e comandos do projeto.
- [`ETL_INCREMENTAL.md`](./ETL_INCREMENTAL.md) — estratégia incremental,
  modelo, granularidade e descrição da pipeline.
- [`DICIONARIO_DADOS.md`](./DICIONARIO_DADOS.md) — dicionário de dados.
- [`RESULTADOS_KPIS.md`](./RESULTADOS_KPIS.md) — resultados das dez KPIs.
- [`STATUS_TRABALHO.md`](./STATUS_TRABALHO.md) — acompanhamento dos requisitos.
