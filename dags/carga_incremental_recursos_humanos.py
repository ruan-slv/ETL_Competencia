"""DAG que agenda e encadeia a carga incremental de indicadores de RH."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow.sdk import dag, get_current_context, task

from src.etl.carga_incremental_recursos_humanos import (
    _executar_carga,
    _executar_extracao,
    preparar_data_warehouse,
    transformar_dados,
)
from src.settings import PostgresConfig


@dag(
    dag_id="carga_incremental_recursos_humanos_adventureworks",
    description=(
        "Atualiza o modelo estrela e os indicadores de funcionarios "
        "a partir dos schemas HumanResources e Person."
    ),
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["adventureworks", "etl", "incremental", "recursos-humanos"],
)
def carga_incremental_recursos_humanos_adventureworks():
    @task
    def preparar_modelo_estrela() -> None:
        engine_destino = PostgresConfig.from_env().create_engine()
        try:
            preparar_data_warehouse(engine_destino)
        finally:
            engine_destino.dispose()

    @task
    def obter_identificador_execucao() -> str:
        return str(get_current_context()["run_id"])

    @task
    def extrair_alteracoes(identificador_execucao: str) -> str:
        return str(_executar_extracao(identificador_execucao))

    @task
    def transformar_dados_extraidos(caminho_arquivo: str) -> str:
        return str(transformar_dados(Path(caminho_arquivo)))

    @task
    def carregar_data_warehouse(caminho_arquivo: str) -> None:
        caminho_transformado = Path(caminho_arquivo)
        contagens = _executar_carga(caminho_transformado)
        caminho_extraido = caminho_transformado.with_name(
            caminho_transformado.name.replace("transformacao_", "extracao_", 1)
        )
        caminho_extraido.unlink(missing_ok=True)
        caminho_transformado.unlink(missing_ok=True)
        print(f"Registros processados nesta execução: {contagens}")

    preparar = preparar_modelo_estrela()
    identificador = obter_identificador_execucao()
    arquivo_extraido = extrair_alteracoes(identificador)
    arquivo_transformado = transformar_dados_extraidos(arquivo_extraido)
    carga = carregar_data_warehouse(arquivo_transformado)
    preparar >> identificador >> arquivo_extraido >> arquivo_transformado >> carga


dag_carga_incremental_recursos_humanos = (
    carga_incremental_recursos_humanos_adventureworks()
)
