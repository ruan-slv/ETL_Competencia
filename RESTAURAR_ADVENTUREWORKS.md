# Restaurar o backup AdventureWorks no SQL Server

Este guia explica como restaurar `AdventureWorks2025.bak` no SQL Server do
projeto usando o programa
[`src/fetch_backup/fetch_backup.py`](./src/fetch_backup/fetch_backup.py).

## Como o processo funciona

O arquivo `.bak` contém um backup de banco de dados do SQL Server. O script não
descompacta nem copia o arquivo para o PostgreSQL: ele solicita ao próprio SQL
Server que leia o backup e crie o banco AdventureWorks.

No `docker-compose.yaml`, o backup local
`src/data/AdventureWorks2025.bak` é montado, somente para leitura, no contêiner
SQL Server em:

```text
/var/opt/mssql/backup/AdventureWorks2025.bak
```

Por isso, o comando de restauração precisa ser executado por um ambiente que
consiga conectar ao SQL Server, mas o caminho passado ao SQL Server é o caminho
**dentro do contêiner**, não o caminho do Windows.

O script segue estas etapas:

1. Carrega as configurações de conexão das variáveis de ambiente `SQLSERVER_*`
   definidas pelo Compose.
2. Conecta ao banco de sistema `master`, necessário para restaurar outro banco.
3. Confere se o banco de destino já existe. Sem a opção `--replace`, interrompe
   a execução para evitar substituir dados existentes.
4. Consulta o conteúdo do backup para descobrir os arquivos lógicos de dados e
   de log.
5. Consulta os diretórios de dados e log configurados no SQL Server e prepara os
   destinos dos arquivos da restauração.
6. Executa `RESTORE DATABASE` usando o backup montado no contêiner.
7. Fecha a conexão e informa sucesso ou apresenta o erro ocorrido.

## Pré-requisitos

1. Tenha o Docker Desktop iniciado.
2. Na raiz do projeto, crie o arquivo `.env` a partir de `.env.example` e
   configure senhas próprias. Em particular, defina `SQLSERVER_PASSWORD`.
3. Confirme que `src/data/AdventureWorks2025.bak` existe.
4. O SQL Server do Compose precisa ser da mesma versão (ou mais nova) que gerou
   o backup. `AdventureWorks2025.bak` foi gerado no SQL Server 2025 (versão
   interna `998`), por isso o `docker-compose.yaml` usa a imagem
   `mcr.microsoft.com/mssql/server:2025-latest`. Um SQL Server 2022 (versão
   interna `958`) não consegue restaurar esse arquivo.
5. Inicie os serviços do Compose:

   ```powershell
   docker compose up --build -d
   ```

O SQL Server deve estar iniciado e aceitando conexões antes de executar a
restauração. Para conferir o estado dos contêineres:

```powershell
docker compose ps
```

## Executar a restauração

Na raiz do projeto, execute o programa no contêiner Airflow:

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py
```

O contêiner Airflow recebe as configurações do SQL Server pelo Compose, incluindo
o host `sqlserver`, a porta `1433`, o usuário `sa` e a senha configurada no
`.env`. O script usa por padrão:

- Banco de destino: `AdventureWorks2025`
- Caminho do backup visto pelo SQL Server:
  `/var/opt/mssql/backup/AdventureWorks2025.bak`

Uma restauração concluída exibe uma mensagem de sucesso. Em caso de erro, a
mensagem é impressa no terminal e o processo termina com código diferente de
zero.

## Substituir um banco existente

Por segurança, se `AdventureWorks2025` já existir, a execução normal termina sem
alterá-lo. Para autorizar explicitamente a substituição, use:

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py --replace
```

**Atenção:** substituir o banco encerra as conexões ativas e os dados atuais
desse banco serão substituídos pelo conteúdo do backup.

## Opções

Exiba todas as opções disponíveis com:

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py --help
```

Use outro caminho de backup com `--backup`. Esse caminho precisa existir e estar
acessível **no contêiner SQL Server**:

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py --backup /var/opt/mssql/backup/outro_backup.bak
```

Use outro nome para o banco com `--database`:

```powershell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py --database OutroBanco
```

Essas opções podem ser combinadas com `--replace`, se a substituição for
intencional.

## Depois da restauração

O banco restaurado fica no SQL Server, que é a origem OLTP do projeto. Ele não é
carregado automaticamente no PostgreSQL pelo script de restauração. Depois de
confirmar que o banco está disponível, a ETL pode usar `AdventureWorks2025` como
origem para popular o Data Warehouse no PostgreSQL.

## Problemas comuns

- **Docker não está disponível:** inicie o Docker Desktop e confira novamente
  com `docker compose ps`.
- **O SQL Server ainda não iniciou:** aguarde o serviço `sqlserver` ficar
  saudável antes de rodar o script.
- **Senha ausente ou incorreta:** confira `SQLSERVER_PASSWORD` no `.env`.
- **Backup não encontrado:** confirme o arquivo local em `src/data` e a
  montagem em `/var/opt/mssql/backup/AdventureWorks2025.bak`.
- **O banco já existe:** execute sem `--replace` para preservar o banco atual;
  use a opção somente se realmente quiser substituí-lo.
- **Erro 3169 (`The database was backed up on a server running database version
  ...`):** a instância do SQL Server é mais antiga que a versão que gerou o
  `.bak`. O backup `AdventureWorks2025.bak` exige SQL Server 2025, imagem
  `mcr.microsoft.com/mssql/server:2025-latest`. Atualize a imagem no
  `docker-compose.yaml` e recrie o serviço:

  ```powershell
  docker compose up -d sqlserver
  ```

  O SQL Server atualiza os arquivos de dados do volume `sqlserver_data` para a
  nova versão na primeira inicialização. Essa conversão é irreversível: depois
  dela, o volume não abre mais em uma imagem 2022.
- **O banco ficou em `RESTORING` e não abre:** uma execução anterior da
  restauração foi interrompida no meio. O programa detecta esse estado e, com
  `--replace`, descarta o banco incompleto e restaura novamente:

  ```powershell
  docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py --replace
  ```

  O programa também confere, ao final, se o banco ficou `ONLINE` e consome todos
  os resultados enviados pelo SQL Server durante o `RESTORE`; sem isso a conexão
  podia ser fechada antes do fim da restauração.
- **Falha de conexão pelo contêiner Airflow:** confira se o serviço Airflow e o
  serviço SQL Server estão ativos no mesmo projeto Docker Compose.
