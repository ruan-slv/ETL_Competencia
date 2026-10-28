FROM apache/airflow:3.3.2-python3.12

USER root

# A imagem base apache/airflow ja traz o repositorio da Microsoft configurado
# (/etc/apt/sources.list.d/mssql-release.list) e o msodbcsql18 instalado.
# Recriar esse repositorio gera: "Conflicting values set for option Signed-By".
RUN apt-get update \
    && apt-get install -y --no-install-recommends unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

RUN pip install --no-cache-dir pyodbc==5.3.0 psycopg2-binary==2.9.13
