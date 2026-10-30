Objetivo

Esta atividade tem como objetivo avaliar individualmente a capacidade do estudante de aplicar, de forma prática e autônoma, os seguintes conceitos abordados ao longo da disciplina:

- Construção de processos ETL (Extract, Transform, Load);
- Implementação de ETL incremental;
- Modelagem de dados multidimensional (Star Schema);
- Reconhecimento de padrões em dados;
- Orquestração de pipelines utilizando Apache Airflow;
- Produção de escrita técnica no formato acadêmico.

Esta atividade reutiliza o contexto do Produto 1, porém deve ser desenvolvida individualmente, demonstrando domínio conceitual e técnico do estudante.
Enunciado

O objetivo deste trabalho é projetar e implementar individualmente um Data Warehouse baseado no conjunto de dados AdventureWorks, aplicando modelagem multidimensional e engenharia de dados com Apache Airflow.

O estudante deverá:

- Avaliar o modelo de dados original (OLTP);
- Elaborar 10 indicadores (métricas/KPIs) relevantes para análise;
- Propor um modelo multidimensional seguindo obrigatoriamente o padrão Star Schema;
- Implementar o Data Warehouse no PostgreSQL;
- Desenvolver processos ETL utilizando o Apache Airflow para popular o Data Warehouse;
- Implementar carga incremental obrigatória, processando apenas dados novos ou modificados;
- Implementar, via SQL, os cálculos dos indicadores definidos.

O trabalho é individual e deverá ser entregue no formato de artigo acadêmico conforme o padrão institucional da Unisales.

O artigo deverá ter no máximo 10 páginas.
Atividades

O estudante deverá:

- Analisar o modelo de dados AdventureWorks (OLTP);
- Definir 10 indicadores (métricas/KPIs) relevantes ao domínio analisado;
- Projetar um modelo multidimensional no padrão Star Schema;
- Elaborar o diagrama do modelo estrela (Draw.io, PlantUML ou ferramenta similar);
- Implementar o Data Warehouse no PostgreSQL;
- Desenvolver os processos ETL no Apache Airflow; (print dos fluxos)
- Garantir que a ETL seja incremental;
- Criar um repositório no GitHub contendo:
    - Código das DAGs;
    - Scripts de criação do Data Warehouse;
    - Scripts SQL dos indicadores;
    - Documentação técnica;
- Elaborar o artigo acadêmico conforme padrão Unisales, contendo:
    - Introdução
    - Desenvolvimento
    - data etl
    - modelo de dados
    - indicadores
    - resultados dos indicadores
    - Considerações Finais

Estrutura do Desenvolvimento (Artigo)

O capítulo de Desenvolvimento deverá conter obrigatoriamente:

- O modelo multidimensional proposto (diagrama estrela);
- Definição da granularidade da tabela fato;
- Dicionário de dados do modelo multidimensional;
- Estratégia de ETL incremental adotada;
- Descrição detalhada do fluxo da pipeline no Apache Airflow;
- Imagens das DAGs configuradas;
- Explicação das tarefas (tasks) e dependências;
- Justificativa técnica das decisões de modelagem;
- Link para o repositório GitHub com o código-fonte;
- Scripts SQL que comprovem a implementação e o cálculo dos indicadores.

Observações Importantes

- O modelo deve obrigatoriamente seguir o padrão Star Schema.
- A ETL deve ser incremental.
- O uso do Apache Airflow é obrigatório.
- Não é necessário desenvolver dashboard.
- O artigo possui peso elevado na avaliação, sendo fundamental para demonstrar compreensão conceitual e domínio técnico.

Execução local com Docker Compose
---------------------------------

O ambiente local inclui SQL Server como origem OLTP, PostgreSQL como destino do Data Warehouse e Apache Airflow para orquestração. O banco de metadados do Airflow fica em uma instância PostgreSQL separada.

O SQL Server usa a imagem `mcr.microsoft.com/mssql/server:2025-latest` porque o
backup `AdventureWorks2025.bak` foi gerado no SQL Server 2025 e não pode ser
restaurado em uma instância 2022.

1. Copie `.env.example` para `.env` e defina senhas próprias para os três serviços.
2. Inicie os contêineres com `docker compose up --build`.
3. Acesse o Airflow em `http://localhost:8080`. As credenciais iniciais são exibidas nos logs do contêiner Airflow.

O backup `src/data/AdventureWorks2025.bak` é disponibilizado no contêiner SQL Server em `/var/opt/mssql/backup/AdventureWorks2025.bak`, mas não é restaurado automaticamente. Restaure-o no SQL Server antes de executar a ETL. Os diretórios `dags/` e `src/` são montados no Airflow; adicione as DAGs em `dags/`.

Para restaurar o backup após iniciar os contêineres, execute o programa pelo Airflow:

```shell
docker compose exec airflow python /opt/airflow/project/src/fetch_backup/fetch_backup.py
```

O programa usa as variáveis `SQLSERVER_*` do Compose e o caminho do backup montado
no contêiner SQL Server. Se o banco `AdventureWorks2025` já existir, a restauração
é interrompida para evitar sobrescrita; para substituí-lo explicitamente, acrescente
`--replace` ao comando. O caminho visto pelo SQL Server pode ser alterado com
`--backup` ou pela variável `SQLSERVER_BACKUP_PATH`.

### ETL do SQL Server para o PostgreSQL

Depois de restaurar `AdventureWorks2025`, execute as três etapas abaixo na raiz
do projeto. Os CSVs brutos e transformados são gravados em `src/data/csv/raw/` e
`src/data/csv/transformed/`.

```powershell
docker compose exec airflow python -m src.etl.extract
docker compose exec airflow python -m src.etl.transform
docker compose exec airflow python -m src.etl.load
```

A extração inclui todas as tabelas de usuário, preserva os valores como texto no
CSV (valores binários são representados em hexadecimal) e grava um manifesto com
a correspondência entre schemas e colunas. A transformação normaliza os nomes
de colunas para `snake_case`, sem alterar os
valores; a carga lê os CSVs transformados e substitui as tabelas de destino no
PostgreSQL. Os schemas de origem são mantidos como schemas no destino. Como os
dados são carregados como `TEXT`, essa carga é uma etapa de aterrissagem, não um
modelo dimensional tipado.

O diretório `src/` precisa estar montado com permissão de escrita no contêiner
Airflow para que os arquivos CSV possam ser gerados.