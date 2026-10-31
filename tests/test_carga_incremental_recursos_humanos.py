import json
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from src.etl.carga_incremental_recursos_humanos import (
    _condicao_de_alteracao,
    _transformar_funcionario,
    transformar_dados,
)


class TesteCargaIncrementalRecursosHumanos(unittest.TestCase):
    def test_condicao_de_alteracao_usa_marcador_da_origem_correta(self):
        tabela = "HumanResources.Employee"
        fotografia = datetime(2013, 7, 1)
        marcador = datetime(2013, 6, 1)
        parametros = {}

        condicao = _condicao_de_alteracao(
            "funcionario",
            tabela,
            {tabela: marcador},
            {tabela: fotografia},
            parametros,
        )

        self.assertIn("fotografia_funcionario", condicao)
        self.assertIn("marcador_funcionario", condicao)
        self.assertIn("ModifiedDate >", condicao)
        self.assertEqual(parametros["marcador_funcionario"], marcador)
        self.assertEqual(parametros["fotografia_funcionario"], fotografia)

    def test_primeira_execucao_seleciona_registros_da_tabela(self):
        tabela = "HumanResources.Shift"
        parametros = {}

        condicao = _condicao_de_alteracao(
            "turno",
            tabela,
            {},
            {tabela: datetime(2013, 7, 1)},
            parametros,
        )

        self.assertIn("turno.ModifiedDate <=", condicao)
        self.assertNotIn("marcador_turno", parametros)

    def test_transformacao_preserva_tipo_dos_dados_de_funcionario(self):
        funcionario = _transformar_funcionario(
            {
                "codigo_funcionario_origem": 10,
                "data_contratacao": "2012-01-15T00:00:00",
                "codigo_departamento_origem": 2,
                "codigo_turno_origem": 1,
                "salario_fixo": True,
                "funcionario_atual": True,
                "horas_ferias": 40,
                "horas_afastamento": 20,
                "horario_inicio": "07:00:00",
                "horario_fim": "15:00:00",
                "taxa_remuneracao_atual": Decimal("25.5000"),
                "frequencia_pagamento_atual": 2,
            }
        )

        self.assertEqual(funcionario["data_contratacao"], "2012-01-15")
        self.assertTrue(funcionario["salario_fixo"])
        self.assertEqual(funcionario["horas_ferias"], 40)
        self.assertEqual(funcionario["horario_inicio"], "07:00:00")
        self.assertEqual(
            Decimal(funcionario["taxa_remuneracao_atual"]),
            Decimal("25.5000"),
        )

    def test_transformacao_preserva_instante_da_alteracao_salarial(self):
        with TemporaryDirectory() as diretorio_temporario:
            caminho_extracao = Path(diretorio_temporario) / "extracao_execucao.json"
            caminho_extracao.write_text(
                json.dumps(
                    {
                        "fotografias": {},
                        "departamentos": [],
                        "turnos": [],
                        "funcionarios": [],
                        "historico_remuneracao": [
                            {
                                "codigo_funcionario_origem": 10,
                                "data_alteracao": "2012-01-15T08:30:00",
                                "taxa_remuneracao": "25.5",
                                "frequencia_pagamento": 2,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            caminho_transformacao = transformar_dados(caminho_extracao)
            dados = json.loads(
                caminho_transformacao.read_text(encoding="utf-8")
            )

        self.assertEqual(
            dados["historico_remuneracao"][0]["data_alteracao"],
            "2012-01-15T08:30:00",
        )


if __name__ == "__main__":
    unittest.main()
