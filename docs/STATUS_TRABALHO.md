# Acompanhamento dos requisitos do trabalho

Revisão do enunciado em `README.md`: **31/10/2026**.
Última atualização deste acompanhamento: **16/11/2026**.

## Estimativa de conclusão

A parte técnica está concluída e as evidências visuais foram produzidas: captura
da execução da DAG no Airflow e diagrama do modelo estrela renderizado. O artigo
acadêmico possui uma versão completa em
[`../CONSTRUÇÃO_ARTIGO/artigo.md`](../CONSTRUÇÃO_ARTIGO/artigo.md), com versões
em DOCX e PDF de **10 páginas**. Falta apenas a revisão final, a identificação do
autor e a adequação ao template institucional.

Mantendo a ponderação de 70% para a preparação técnica e 30% para o artigo, a
estimativa global é de aproximadamente **90%**:

`(70% × 100%) + (30% × 65%) = 89,5% ≈ 90%`

## Situação dos requisitos do README

| Requisito | Situação | Evidência ou pendência |
| --- | --- | --- |
| Avaliar o modelo OLTP AdventureWorks | Concluído | Análise documentada em [`ANALISE_OLTP.md`](./ANALISE_OLTP.md), com schemas, tabelas, chaves, relacionamentos, volumetria, limitações e implicações para o modelo dimensional. |
| Definir dez indicadores | Concluído | Dez indicadores de funcionários descritos em [`ETL_INCREMENTAL.md`](./ETL_INCREMENTAL.md) e no artigo. |
| Projetar o modelo no padrão Star Schema | Concluído | Dois esquemas estrela relacionados, com granularidades definidas e dimensões compartilhadas. |
| Elaborar o diagrama do modelo estrela | Concluído | Diagrama editável em [`modelo_estrela.mmd`](./modelo_estrela.mmd) e imagem renderizada em [`images/ETL_Competencia_Diagrama.drawio.png`](./images/ETL_Competencia_Diagrama.drawio.png). |
| Implementar o Data Warehouse no PostgreSQL | Concluído | Tabelas criadas e carga real de 290 funcionários e 316 registros de remuneração validada. |
| Desenvolver o processo ETL com Apache Airflow | Concluído | DAG descoberta e execução completa pelo Airflow, com cinco tarefas bem-sucedidas; captura em [`images/Airflow_Executado.png`](./images/Airflow_Executado.png). |
| Garantir carga incremental | Concluído | Primeira carga executada; repetição sem alteração processou zero funcionários, departamentos, turnos e alterações de remuneração. |
| Implementar em SQL as dez KPIs | Concluído | Consultas executadas no PostgreSQL; resultados em [`RESULTADOS_KPIS.md`](./RESULTADOS_KPIS.md). |
| Manter código e documentação no repositório GitHub | Concluído | Repositório <https://github.com/ruan-slv/ETL_Competencia>. O artigo e o diagrama ainda precisam ser incluídos no próximo commit. |
| Elaborar e entregar o artigo acadêmico, com até dez páginas | Em revisão | Versão completa em [`../CONSTRUÇÃO_ARTIGO/artigo.docx`](../CONSTRUÇÃO_ARTIGO/artigo.docx) e [`../CONSTRUÇÃO_ARTIGO/artigo.pdf`](../CONSTRUÇÃO_ARTIGO/artigo.pdf), com 10 páginas. Faltam nome, curso, e-mail, conferência do template Unisales e revisão textual. |

## Validações realizadas

- A DAG `carga_incremental_recursos_humanos_adventureworks` executou com sucesso;
  a captura de 15/11/2026 registra as cinco tarefas no estado `success`.
- O comando manual do README executou a carga incremental sem erros e retornou
  `0` funcionários, `0` departamentos, `0` turnos e `0` alterações de
  remuneração, confirmando o comportamento incremental.
- O Data Warehouse contém 290 funcionários, 316 registros de histórico de
  remuneração, 17 departamentos (16 + “Não informado”), 4 turnos (3 + “Não
  informado”) e 178 datas.
- Os dez indicadores de [`../src/sql/indicadores.sql`](../src/sql/indicadores.sql)
  foram executados no PostgreSQL sem erro.
- Os quatro testes unitários de
  [`../tests/test_carga_incremental_recursos_humanos.py`](../tests/test_carga_incremental_recursos_humanos.py)
  passaram com `python -m unittest discover -s tests -v`.
- O artigo foi gerado a partir de `CONSTRUÇÃO_ARTIGO/artigo.md` e convertido
  para PDF; a contagem final ficou em **10 páginas**.

## Próximas ações

1. Preencher nome, curso e e-mail do autor no início do artigo.
2. Conferir o template institucional da Unisales (capa, folha de estilo,
   cabeçalho e referências) e ajustar o DOCX se necessário.
3. Revisar o texto e as imagens; gerar a versão final em PDF.
4. Registrar e enviar o novo commit com o artigo, o diagrama e esta atualização.
5. Entregar o artigo e o link do repositório conforme as regras da disciplina.
