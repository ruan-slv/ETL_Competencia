"""Executa a carga incremental dos indicadores de funcionarios do AdventureWorks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.etl.common import REPOSITORY_ROOT
from src.settings import PostgresConfig, SQLServerConfig

TABELAS_DE_ORIGEM = (
    "HumanResources.Employee",
    "HumanResources.Department",
    "HumanResources.Shift",
    "HumanResources.EmployeeDepartmentHistory",
    "HumanResources.EmployeePayHistory",
    "Person.Person",
)

CONSULTA_MARCADORES = """
SELECT 'HumanResources.Employee' AS tabela_origem, MAX(ModifiedDate) AS ultima_modificacao
FROM HumanResources.Employee
UNION ALL
SELECT 'HumanResources.Department', MAX(ModifiedDate)
FROM HumanResources.Department
UNION ALL
SELECT 'HumanResources.Shift', MAX(ModifiedDate)
FROM HumanResources.Shift
UNION ALL
SELECT 'HumanResources.EmployeeDepartmentHistory', MAX(ModifiedDate)
FROM HumanResources.EmployeeDepartmentHistory
UNION ALL
SELECT 'HumanResources.EmployeePayHistory', MAX(ModifiedDate)
FROM HumanResources.EmployeePayHistory
UNION ALL
SELECT 'Person.Person', MAX(ModifiedDate)
FROM Person.Person
"""

CONSULTA_DEPARTAMENTOS = """
SELECT
    DepartmentID AS codigo_departamento_origem,
    Name AS nome_departamento,
    GroupName AS grupo_departamento
FROM HumanResources.Department AS departamento
WHERE {condicao}
"""

CONSULTA_TURNOS = """
SELECT
    ShiftID AS codigo_turno_origem,
    Name AS nome_turno,
    StartTime AS horario_inicio,
    EndTime AS horario_fim
FROM HumanResources.Shift AS turno
WHERE {condicao}
"""

CONSULTA_FUNCIONARIOS = """
SELECT
    funcionario.BusinessEntityID AS codigo_funcionario_origem,
    pessoa.FirstName AS primeiro_nome,
    pessoa.MiddleName AS nome_do_meio,
    pessoa.LastName AS sobrenome,
    pessoa.Title AS titulo,
    funcionario.JobTitle AS cargo,
    funcionario.Gender AS genero,
    funcionario.MaritalStatus AS estado_civil,
    funcionario.SalariedFlag AS salario_fixo,
    funcionario.CurrentFlag AS funcionario_atual,
    funcionario.HireDate AS data_contratacao,
    departamento.DepartmentID AS codigo_departamento_origem,
    departamento.Name AS nome_departamento,
    departamento.GroupName AS grupo_departamento,
    turno.ShiftID AS codigo_turno_origem,
    turno.Name AS nome_turno,
    turno.StartTime AS horario_inicio,
    turno.EndTime AS horario_fim,
    funcionario.VacationHours AS horas_ferias,
    funcionario.SickLeaveHours AS horas_afastamento,
    remuneracao.Rate AS taxa_remuneracao_atual,
    remuneracao.PayFrequency AS frequencia_pagamento_atual
FROM HumanResources.Employee AS funcionario
JOIN Person.Person AS pessoa
    ON pessoa.BusinessEntityID = funcionario.BusinessEntityID
OUTER APPLY (
    SELECT TOP (1)
        historico.DepartmentID,
        historico.ShiftID
    FROM HumanResources.EmployeeDepartmentHistory AS historico
    WHERE historico.BusinessEntityID = funcionario.BusinessEntityID
    ORDER BY
        CASE WHEN historico.EndDate IS NULL THEN 0 ELSE 1 END,
        historico.StartDate DESC
) AS atribuicao
LEFT JOIN HumanResources.Department AS departamento
    ON departamento.DepartmentID = atribuicao.DepartmentID
LEFT JOIN HumanResources.Shift AS turno
    ON turno.ShiftID = atribuicao.ShiftID
OUTER APPLY (
    SELECT TOP (1)
        historico_remuneracao.Rate,
        historico_remuneracao.PayFrequency
    FROM HumanResources.EmployeePayHistory AS historico_remuneracao
    WHERE historico_remuneracao.BusinessEntityID =
        funcionario.BusinessEntityID
    ORDER BY historico_remuneracao.RateChangeDate DESC
) AS remuneracao
WHERE EXISTS (
    SELECT 1
    FROM HumanResources.Employee AS funcionario_alterado
    WHERE funcionario_alterado.BusinessEntityID =
        funcionario.BusinessEntityID
        AND ({condicao_funcionario})
)
OR EXISTS (
    SELECT 1
    FROM Person.Person AS pessoa_alterada
    WHERE pessoa_alterada.BusinessEntityID = funcionario.BusinessEntityID
        AND ({condicao_pessoa})
)
OR EXISTS (
    SELECT 1
    FROM HumanResources.EmployeeDepartmentHistory AS historico_alterado
    WHERE historico_alterado.BusinessEntityID =
        funcionario.BusinessEntityID
        AND ({condicao_historico_departamento})
)
OR EXISTS (
    SELECT 1
    FROM HumanResources.EmployeePayHistory AS remuneracao_alterada
    WHERE remuneracao_alterada.BusinessEntityID =
        funcionario.BusinessEntityID
        AND ({condicao_historico_remuneracao})
)
OR EXISTS (
    SELECT 1
    FROM HumanResources.EmployeeDepartmentHistory AS atribuicao_alterada
    JOIN HumanResources.Department AS departamento_alterado
        ON departamento_alterado.DepartmentID =
            atribuicao_alterada.DepartmentID
    LEFT JOIN HumanResources.Shift AS turno_alterado
        ON turno_alterado.ShiftID = atribuicao_alterada.ShiftID
    WHERE atribuicao_alterada.BusinessEntityID =
        funcionario.BusinessEntityID
        AND atribuicao_alterada.EndDate IS NULL
        AND (
            ({condicao_departamento})
            OR ({condicao_turno})
        )
)
"""

CONSULTA_HISTORICO_REMUNERACAO = """
SELECT
    BusinessEntityID AS codigo_funcionario_origem,
    RateChangeDate AS data_alteracao,
    Rate AS taxa_remuneracao,
    PayFrequency AS frequencia_pagamento
FROM HumanResources.EmployeePayHistory AS remuneracao
WHERE {condicao}
"""


def _caminho_dados_temporarios(identificador_execucao: str, etapa: str) -> Path:
    identificador_seguro = hashlib.sha256(
        identificador_execucao.encode("utf-8")
    ).hexdigest()[:20]
    diretorio = (
        REPOSITORY_ROOT
        / "src"
        / "data"
        / "temporarios"
        / "recursos_humanos"
    )
    diretorio.mkdir(parents=True, exist_ok=True)
    return diretorio / f"{etapa}_{identificador_seguro}.json"


def preparar_data_warehouse(engine_destino: Engine) -> None:
    caminho_sql = (
        REPOSITORY_ROOT / "src" / "sql" / "criar_data_warehouse.sql"
    )
    comandos = caminho_sql.read_text(encoding="utf-8").split(";")
    with engine_destino.begin() as conexao:
        for comando in comandos:
            if comando.strip():
                conexao.exec_driver_sql(comando)


def _ler_marcadores_destino(engine_destino: Engine) -> dict[str, datetime]:
    with engine_destino.connect() as conexao:
        linhas = conexao.execute(
            text(
                """
                SELECT tabela_origem, ultima_modificacao
                FROM modelo_estrela.controle_incremental_recursos_humanos
                """
            )
        ).mappings()
        return {
            str(linha["tabela_origem"]): linha["ultima_modificacao"]
            for linha in linhas
        }


def _consultar_fotografias_origem(
    engine_origem: Engine,
) -> dict[str, datetime | None]:
    with engine_origem.connect() as conexao:
        linhas = conexao.execute(text(CONSULTA_MARCADORES)).mappings()
        fotografias = {
            str(linha["tabela_origem"]): linha["ultima_modificacao"]
            for linha in linhas
        }

    tabelas_ausentes = set(TABELAS_DE_ORIGEM) - fotografias.keys()
    if tabelas_ausentes:
        raise RuntimeError(
            "Não foi possível consultar os marcadores das tabelas: "
            + ", ".join(sorted(tabelas_ausentes))
        )
    return fotografias


def _condicao_de_alteracao(
    alias: str,
    tabela_origem: str,
    marcadores: dict[str, datetime],
    fotografias: dict[str, datetime | None],
    parametros: dict[str, datetime],
) -> str:
    fotografia = fotografias[tabela_origem]
    if fotografia is None:
        return "1 = 0"

    nome_parametro_fotografia = f"fotografia_{alias}"
    parametros[nome_parametro_fotografia] = fotografia
    condicao = f"{alias}.ModifiedDate <= :{nome_parametro_fotografia}"
    marcador = marcadores.get(tabela_origem)
    if marcador is not None:
        nome_parametro_marcador = f"marcador_{alias}"
        parametros[nome_parametro_marcador] = marcador
        condicao += f" AND {alias}.ModifiedDate > :{nome_parametro_marcador}"
    return condicao


def _consultar_registros(
    engine_origem: Engine,
    consulta: str,
    parametros: dict[str, datetime],
) -> list[dict[str, Any]]:
    with engine_origem.connect() as conexao:
        return [
            dict(linha)
            for linha in conexao.execute(text(consulta), parametros).mappings()
        ]


def extrair_alteracoes(
    engine_origem: Engine,
    engine_destino: Engine,
    identificador_execucao: str,
) -> Path:
    marcadores = _ler_marcadores_destino(engine_destino)
    fotografias = _consultar_fotografias_origem(engine_origem)
    parametros_departamentos: dict[str, datetime] = {}
    parametros_turnos: dict[str, datetime] = {}
    parametros_funcionarios: dict[str, datetime] = {}
    parametros_remuneracoes: dict[str, datetime] = {}

    def condicao(
        alias: str,
        tabela: str,
        parametros: dict[str, datetime],
    ) -> str:
        return _condicao_de_alteracao(
            alias, tabela, marcadores, fotografias, parametros
        )

    consulta_funcionarios = CONSULTA_FUNCIONARIOS.format(
        condicao_funcionario=condicao(
            "funcionario_alterado",
            "HumanResources.Employee",
            parametros_funcionarios,
        ),
        condicao_pessoa=condicao(
            "pessoa_alterada", "Person.Person", parametros_funcionarios
        ),
        condicao_historico_departamento=condicao(
            "historico_alterado",
            "HumanResources.EmployeeDepartmentHistory",
            parametros_funcionarios,
        ),
        condicao_historico_remuneracao=condicao(
            "remuneracao_alterada",
            "HumanResources.EmployeePayHistory",
            parametros_funcionarios,
        ),
        condicao_departamento=condicao(
            "departamento_alterado",
            "HumanResources.Department",
            parametros_funcionarios,
        ),
        condicao_turno=condicao(
            "turno_alterado", "HumanResources.Shift", parametros_funcionarios
        ),
    )
    dados = {
        "fotografias": fotografias,
        "departamentos": _consultar_registros(
            engine_origem,
            CONSULTA_DEPARTAMENTOS.format(
                condicao=condicao(
                    "departamento",
                    "HumanResources.Department",
                    parametros_departamentos,
                )
            ),
            parametros_departamentos,
        ),
        "turnos": _consultar_registros(
            engine_origem,
            CONSULTA_TURNOS.format(
                condicao=condicao(
                    "turno", "HumanResources.Shift", parametros_turnos
                )
            ),
            parametros_turnos,
        ),
        "funcionarios": _consultar_registros(
            engine_origem, consulta_funcionarios, parametros_funcionarios
        ),
        "historico_remuneracao": _consultar_registros(
            engine_origem,
            CONSULTA_HISTORICO_REMUNERACAO.format(
                condicao=condicao(
                    "remuneracao",
                    "HumanResources.EmployeePayHistory",
                    parametros_remuneracoes,
                )
            ),
            parametros_remuneracoes,
        ),
    }

    caminho_dados = _caminho_dados_temporarios(
        identificador_execucao, "extracao"
    )
    caminho_dados.write_text(
        json.dumps(dados, default=_converter_para_json, ensure_ascii=False),
        encoding="utf-8",
    )
    return caminho_dados


def _converter_para_json(valor: Any) -> str:
    if isinstance(valor, (date, datetime, time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    raise TypeError(
        f"Tipo não serializável na extração: {type(valor).__name__}."
    )


def _converter_inteiro(
    valor: Any, campo: str, opcional: bool = False
) -> int | None:
    if valor is None and opcional:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"O campo {campo} deve conter um número inteiro.") from erro


def _converter_decimal(valor: Any, campo: str) -> Decimal:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as erro:
        raise ValueError(f"O campo {campo} deve conter um número decimal.") from erro
    if not numero.is_finite():
        raise ValueError(f"O campo {campo} deve conter um número finito.")
    return numero


def _converter_booleano(valor: Any, campo: str) -> bool:
    if valor is True or valor == 1:
        return True
    if valor is False or valor == 0:
        return False
    raise ValueError(f"O campo {campo} deve conter um valor booleano.")


def _converter_data(valor: Any, campo: str) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    try:
        return date.fromisoformat(str(valor)[:10]).isoformat()
    except (TypeError, ValueError) as erro:
        raise ValueError(f"O campo {campo} deve conter uma data válida.") from erro


def _converter_data_hora(valor: Any, campo: str) -> str:
    if isinstance(valor, datetime):
        return valor.isoformat()
    try:
        return datetime.fromisoformat(str(valor)).isoformat()
    except (TypeError, ValueError) as erro:
        raise ValueError(
            f"O campo {campo} deve conter uma data e hora válidas."
        ) from erro


def _converter_horario(valor: Any, campo: str) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, time):
        return valor.isoformat()
    try:
        return time.fromisoformat(str(valor)).isoformat()
    except (TypeError, ValueError) as erro:
        raise ValueError(f"O campo {campo} deve conter um horário válido.") from erro


def _transformar_funcionario(registro: dict[str, Any]) -> dict[str, Any]:
    funcionario = dict(registro)
    funcionario["codigo_funcionario_origem"] = _converter_inteiro(
        funcionario.get("codigo_funcionario_origem"),
        "codigo_funcionario_origem",
    )
    funcionario["codigo_departamento_origem"] = _converter_inteiro(
        funcionario.get("codigo_departamento_origem"),
        "codigo_departamento_origem",
        opcional=True,
    )
    funcionario["codigo_turno_origem"] = _converter_inteiro(
        funcionario.get("codigo_turno_origem"),
        "codigo_turno_origem",
        opcional=True,
    )
    funcionario["data_contratacao"] = _converter_data(
        funcionario.get("data_contratacao"), "data_contratacao"
    )
    funcionario["salario_fixo"] = _converter_booleano(
        funcionario.get("salario_fixo"), "salario_fixo"
    )
    funcionario["funcionario_atual"] = _converter_booleano(
        funcionario.get("funcionario_atual"), "funcionario_atual"
    )
    funcionario["horas_ferias"] = _converter_inteiro(
        funcionario.get("horas_ferias"), "horas_ferias"
    )
    funcionario["horas_afastamento"] = _converter_inteiro(
        funcionario.get("horas_afastamento"), "horas_afastamento"
    )
    funcionario["horario_inicio"] = _converter_horario(
        funcionario.get("horario_inicio"), "horario_inicio"
    )
    funcionario["horario_fim"] = _converter_horario(
        funcionario.get("horario_fim"), "horario_fim"
    )
    funcionario["taxa_remuneracao_atual"] = (
        None
        if funcionario.get("taxa_remuneracao_atual") is None
        else str(
            _converter_decimal(
                funcionario["taxa_remuneracao_atual"],
                "taxa_remuneracao_atual",
            )
        )
    )
    funcionario["frequencia_pagamento_atual"] = _converter_inteiro(
        funcionario.get("frequencia_pagamento_atual"),
        "frequencia_pagamento_atual",
        opcional=True,
    )
    return funcionario


def transformar_dados(caminho_entrada: Path) -> Path:
    dados = json.loads(caminho_entrada.read_text(encoding="utf-8"))
    secoes_obrigatorias = {
        "fotografias",
        "departamentos",
        "turnos",
        "funcionarios",
        "historico_remuneracao",
    }
    if not isinstance(dados, dict) or not secoes_obrigatorias.issubset(dados):
        raise ValueError("A extração não contém todas as seções obrigatórias.")
    if not isinstance(dados["fotografias"], dict):
        raise ValueError("A seção de fotografias da extração é inválida.")
    for nome_secao in secoes_obrigatorias - {"fotografias"}:
        if not isinstance(dados[nome_secao], list) or not all(
            isinstance(registro, dict) for registro in dados[nome_secao]
        ):
            raise ValueError(f"A seção {nome_secao} da extração é inválida.")

    funcionarios = [
        _transformar_funcionario(registro)
        for registro in dados["funcionarios"]
    ]
    historico_remuneracao = []
    for registro in dados["historico_remuneracao"]:
        historico = dict(registro)
        historico["codigo_funcionario_origem"] = _converter_inteiro(
            historico.get("codigo_funcionario_origem"),
            "codigo_funcionario_origem",
        )
        historico["data_alteracao"] = _converter_data_hora(
            historico.get("data_alteracao"), "data_alteracao"
        )
        historico["taxa_remuneracao"] = str(
            _converter_decimal(
                historico.get("taxa_remuneracao"), "taxa_remuneracao"
            )
        )
        historico["frequencia_pagamento"] = _converter_inteiro(
            historico.get("frequencia_pagamento"), "frequencia_pagamento"
        )
        historico_remuneracao.append(historico)

    dados_transformados = {
        "fotografias": dados["fotografias"],
        "departamentos": [
            {
                **registro,
                "codigo_departamento_origem": _converter_inteiro(
                    registro.get("codigo_departamento_origem"),
                    "codigo_departamento_origem",
                ),
            }
            for registro in dados["departamentos"]
        ],
        "turnos": [
            {
                **registro,
                "codigo_turno_origem": _converter_inteiro(
                    registro.get("codigo_turno_origem"),
                    "codigo_turno_origem",
                ),
            }
            for registro in dados["turnos"]
        ],
        "funcionarios": funcionarios,
        "historico_remuneracao": historico_remuneracao,
    }
    caminho_transformado = caminho_entrada.with_name(
        caminho_entrada.name.replace("extracao_", "transformacao_", 1)
    )
    caminho_transformado.write_text(
        json.dumps(
            dados_transformados,
            default=_converter_para_json,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return caminho_transformado


def _inserir_ou_atualizar_dimensao(
    conexao: Any,
    consulta: str,
    registros: list[dict[str, Any]],
) -> None:
    if registros:
        conexao.execute(text(consulta), registros)


def _registros_de_datas(dados: dict[str, Any]) -> list[dict[str, Any]]:
    datas = {
        date.fromisoformat(funcionario["data_contratacao"])
        for funcionario in dados["funcionarios"]
    }
    datas.update(
        date.fromisoformat(remuneracao["data_alteracao"][:10])
        for remuneracao in dados["historico_remuneracao"]
    )
    nomes_dos_meses = (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    )
    nomes_dos_dias = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    )
    return [
        {
            "chave_data": int(data_atual.strftime("%Y%m%d")),
            "data": data_atual.isoformat(),
            "ano": data_atual.year,
            "trimestre": (data_atual.month - 1) // 3 + 1,
            "mes": data_atual.month,
            "nome_mes": nomes_dos_meses[data_atual.month - 1],
            "dia": data_atual.day,
            "dia_da_semana": data_atual.isoweekday(),
            "nome_dia_da_semana": nomes_dos_dias[data_atual.weekday()],
        }
        for data_atual in datas
    ]


def _carregar_registros(
    engine_destino: Engine, dados: dict[str, Any]
) -> dict[str, int]:
    fotografias = {
        tabela: (
            datetime.fromisoformat(marcador)
            if isinstance(marcador, str)
            else marcador
        )
        for tabela, marcador in dados["fotografias"].items()
    }
    with engine_destino.begin() as conexao:
        _inserir_ou_atualizar_dimensao(
            conexao,
            """
            INSERT INTO modelo_estrela.dimensao_departamento (
                codigo_departamento_origem, nome_departamento,
                grupo_departamento
            ) VALUES (
                :codigo_departamento_origem, :nome_departamento,
                :grupo_departamento
            )
            ON CONFLICT (codigo_departamento_origem) DO UPDATE SET
                nome_departamento = EXCLUDED.nome_departamento,
                grupo_departamento = EXCLUDED.grupo_departamento
            """,
            dados["departamentos"],
        )
        _inserir_ou_atualizar_dimensao(
            conexao,
            """
            INSERT INTO modelo_estrela.dimensao_turno (
                codigo_turno_origem, nome_turno, horario_inicio, horario_fim
            ) VALUES (
                :codigo_turno_origem, :nome_turno, :horario_inicio, :horario_fim
            )
            ON CONFLICT (codigo_turno_origem) DO UPDATE SET
                nome_turno = EXCLUDED.nome_turno,
                horario_inicio = EXCLUDED.horario_inicio,
                horario_fim = EXCLUDED.horario_fim
            """,
            dados["turnos"],
        )
        _inserir_ou_atualizar_dimensao(
            conexao,
            """
            INSERT INTO modelo_estrela.dimensao_funcionario (
                codigo_funcionario_origem, primeiro_nome, nome_do_meio,
                sobrenome, titulo, cargo, genero, estado_civil,
                salario_fixo, funcionario_atual
            ) VALUES (
                :codigo_funcionario_origem, :primeiro_nome, :nome_do_meio,
                :sobrenome, :titulo, :cargo, :genero, :estado_civil,
                :salario_fixo, :funcionario_atual
            )
            ON CONFLICT (codigo_funcionario_origem) DO UPDATE SET
                primeiro_nome = EXCLUDED.primeiro_nome,
                nome_do_meio = EXCLUDED.nome_do_meio,
                sobrenome = EXCLUDED.sobrenome,
                titulo = EXCLUDED.titulo,
                cargo = EXCLUDED.cargo,
                genero = EXCLUDED.genero,
                estado_civil = EXCLUDED.estado_civil,
                salario_fixo = EXCLUDED.salario_fixo,
                funcionario_atual = EXCLUDED.funcionario_atual
            """,
            dados["funcionarios"],
        )
        datas = _registros_de_datas(dados)
        _inserir_ou_atualizar_dimensao(
            conexao,
            """
            INSERT INTO modelo_estrela.dimensao_data (
                chave_data, data, ano, trimestre, mes, nome_mes,
                dia, dia_da_semana, nome_dia_da_semana
            ) VALUES (
                :chave_data, :data, :ano, :trimestre, :mes, :nome_mes,
                :dia, :dia_da_semana, :nome_dia_da_semana
            )
            ON CONFLICT (chave_data) DO NOTHING
            """,
            datas,
        )

        funcionarios = dados["funcionarios"]
        if funcionarios:
            resultado = conexao.execute(
                text(
                    """
                    INSERT INTO modelo_estrela.fato_quadro_funcionario (
                        codigo_funcionario_origem, chave_funcionario,
                        chave_departamento, chave_turno, chave_data_contratacao,
                        funcionario_atual, horas_ferias, horas_afastamento,
                        taxa_remuneracao_atual, frequencia_pagamento_atual
                    )
                    VALUES (
                        :codigo_funcionario_origem,
                        (
                            SELECT chave_funcionario
                            FROM modelo_estrela.dimensao_funcionario
                            WHERE codigo_funcionario_origem =
                                :codigo_funcionario_origem
                        ),
                        CASE
                            WHEN :codigo_departamento_origem IS NULL THEN 0
                            ELSE (
                                SELECT chave_departamento
                                FROM modelo_estrela.dimensao_departamento
                                WHERE codigo_departamento_origem =
                                    :codigo_departamento_origem
                            )
                        END,
                        CASE
                            WHEN :codigo_turno_origem IS NULL THEN 0
                            ELSE (
                                SELECT chave_turno
                                FROM modelo_estrela.dimensao_turno
                                WHERE codigo_turno_origem = :codigo_turno_origem
                            )
                        END,
                        CAST(
                            TO_CHAR(
                                CAST(:data_contratacao AS DATE), 'YYYYMMDD'
                            ) AS INTEGER
                        ),
                        :funcionario_atual,
                        :horas_ferias,
                        :horas_afastamento,
                        :taxa_remuneracao_atual,
                        :frequencia_pagamento_atual
                    )
                    ON CONFLICT (codigo_funcionario_origem) DO UPDATE SET
                        chave_funcionario = EXCLUDED.chave_funcionario,
                        chave_departamento = EXCLUDED.chave_departamento,
                        chave_turno = EXCLUDED.chave_turno,
                        chave_data_contratacao =
                            EXCLUDED.chave_data_contratacao,
                        funcionario_atual = EXCLUDED.funcionario_atual,
                        horas_ferias = EXCLUDED.horas_ferias,
                        horas_afastamento = EXCLUDED.horas_afastamento,
                        taxa_remuneracao_atual =
                            EXCLUDED.taxa_remuneracao_atual,
                        frequencia_pagamento_atual =
                            EXCLUDED.frequencia_pagamento_atual
                    """
                ),
                funcionarios,
            )
            if resultado.rowcount != len(funcionarios):
                raise RuntimeError(
                    "A quantidade de funcionários gravados não corresponde "
                    "à quantidade extraída."
                )

        historico_remuneracao = dados["historico_remuneracao"]
        if historico_remuneracao:
            resultado = conexao.execute(
                text(
                    """
                    INSERT INTO modelo_estrela.fato_historico_remuneracao (
                        codigo_funcionario_origem, chave_funcionario,
                        chave_data_alteracao, data_alteracao,
                        taxa_remuneracao, frequencia_pagamento
                    )
                    VALUES (
                        :codigo_funcionario_origem,
                        (
                            SELECT chave_funcionario
                            FROM modelo_estrela.dimensao_funcionario
                            WHERE codigo_funcionario_origem =
                                :codigo_funcionario_origem
                        ),
                        CAST(
                            TO_CHAR(
                                CAST(:data_alteracao AS DATE), 'YYYYMMDD'
                            ) AS INTEGER
                        ),
                        CAST(:data_alteracao AS TIMESTAMP),
                        :taxa_remuneracao,
                        :frequencia_pagamento
                    )
                    ON CONFLICT (
                        codigo_funcionario_origem, data_alteracao
                    ) DO UPDATE SET
                        chave_funcionario = EXCLUDED.chave_funcionario,
                        chave_data_alteracao = EXCLUDED.chave_data_alteracao,
                        taxa_remuneracao = EXCLUDED.taxa_remuneracao,
                        frequencia_pagamento = EXCLUDED.frequencia_pagamento
                    """
                ),
                historico_remuneracao,
            )
            if resultado.rowcount != len(historico_remuneracao):
                raise RuntimeError(
                    "A quantidade de alterações de remuneração gravadas não "
                    "corresponde à quantidade extraída."
                )

        for tabela_origem, ultima_modificacao in fotografias.items():
            if ultima_modificacao is None:
                continue
            conexao.execute(
                text(
                    """
                    INSERT INTO modelo_estrela.controle_incremental_recursos_humanos (
                        tabela_origem, ultima_modificacao
                    ) VALUES (:tabela_origem, :ultima_modificacao)
                    ON CONFLICT (tabela_origem) DO UPDATE SET
                        ultima_modificacao = GREATEST(
                            modelo_estrela.controle_incremental_recursos_humanos.ultima_modificacao,
                            EXCLUDED.ultima_modificacao
                        ),
                        atualizado_em = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "tabela_origem": tabela_origem,
                    "ultima_modificacao": ultima_modificacao,
                },
            )

    return {
        "departamentos": len(dados["departamentos"]),
        "turnos": len(dados["turnos"]),
        "funcionarios": len(funcionarios),
        "alteracoes_remuneracao": len(historico_remuneracao),
    }


def carregar_data_warehouse(
    engine_destino: Engine, caminho_entrada: Path
) -> dict[str, int]:
    dados = json.loads(caminho_entrada.read_text(encoding="utf-8"))
    if not isinstance(dados, dict) or "fotografias" not in dados:
        raise ValueError("A transformação não contém os marcadores de origem.")
    return _carregar_registros(engine_destino, dados)


def _executar_extracao(identificador_execucao: str) -> Path:
    engine_origem = SQLServerConfig.from_env().create_engine()
    engine_destino = PostgresConfig.from_env().create_engine()
    try:
        return extrair_alteracoes(
            engine_origem, engine_destino, identificador_execucao
        )
    finally:
        engine_origem.dispose()
        engine_destino.dispose()


def _executar_carga(caminho_entrada: Path) -> dict[str, int]:
    engine_destino = PostgresConfig.from_env().create_engine()
    try:
        return carregar_data_warehouse(engine_destino, caminho_entrada)
    finally:
        engine_destino.dispose()


def main() -> int:
    load_dotenv(REPOSITORY_ROOT / ".env")
    analisador = argparse.ArgumentParser(
        description=(
            "Executa a carga incremental dos indicadores de funcionarios."
        )
    )
    analisador.add_argument(
        "--execucao",
        default=datetime.now().isoformat(),
        help="Identificador da execução para separar os arquivos temporários.",
    )
    argumentos = analisador.parse_args()
    engine_destino = PostgresConfig.from_env().create_engine()
    try:
        preparar_data_warehouse(engine_destino)
    except (OSError, SQLAlchemyError) as erro:
        print(f"Falha ao preparar o Data Warehouse: {erro}", file=sys.stderr)
        return 1
    finally:
        engine_destino.dispose()

    try:
        caminho_extraido = _executar_extracao(argumentos.execucao)
        caminho_transformado = transformar_dados(caminho_extraido)
        contagens = _executar_carga(caminho_transformado)
        caminho_extraido.unlink(missing_ok=True)
        caminho_transformado.unlink(missing_ok=True)
    except (OSError, RuntimeError, ValueError, SQLAlchemyError) as erro:
        print(f"Falha na carga incremental de Recursos Humanos: {erro}", file=sys.stderr)
        return 1

    print(f"Carga incremental concluída: {contagens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
