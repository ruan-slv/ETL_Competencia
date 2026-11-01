# Acompanhamento dos requisitos do trabalho

Revisão do enunciado em `README.md`: **31/10/2026**.

## Estimativa de conclusão

A parte técnica está concluída e o commit `ac525b5` foi publicado no GitHub. O
artigo acadêmico ainda não foi iniciado. Mantendo a ponderação anterior de 70%
para preparação técnica e 30% para o artigo, a estimativa global é de
aproximadamente **70%**:

`(70% × 100%) + (30% × 0%) = 70%`

As evidências visuais solicitadas para o artigo — capturas de tela do Airflow e
imagem renderizada do diagrama — ainda não foram produzidas. Elas não alteram o
funcionamento do projeto, mas são necessárias para a redação final.

## Situação dos requisitos do README

| Requisito | Situação | Evidência ou pendência |
| --- | --- | --- |
| Avaliar o modelo OLTP AdventureWorks | Concluído | Análise documentada em [`ANALISE_OLTP.md`](./ANALISE_OLTP.md), com schemas, tabelas, chaves, relacionamentos, volumetria, limitações e implicações para o modelo dimensional. |
| Definir dez indicadores | Concluído | Dez indicadores de funcionários descritos em [`ETL_INCREMENTAL.md`](./ETL_INCREMENTAL.md). |
| Projetar o modelo no padrão Star Schema | Concluído | Dois esquemas estrela relacionados, com granularidades definidas e dimensões compartilhadas. |
| Elaborar o diagrama do modelo estrela | Concluído | Diagrama editável em [`modelo_estrela.mmd`](./modelo_estrela.mmd). A imagem renderizada ainda pode ser gerada para o artigo. |
| Implementar o Data Warehouse no PostgreSQL | Concluído | Tabelas criadas e carga real de 290 funcionários e 316 registros de remuneração validada. |
| Desenvolver o processo ETL com Apache Airflow | Concluído tecnicamente | DAG descoberta e execução completa pelo Airflow, com cinco tarefas bem-sucedidas. Faltam apenas as capturas de tela para o artigo. |
| Garantir carga incremental | Concluído | Primeira carga executada; repetição sem alteração processou zero funcionários, departamentos, turnos e alterações de remuneração. |
| Implementar em SQL as dez KPIs | Concluído | Consultas executadas no PostgreSQL; resultados resumidos em [`RESULTADOS_KPIS.md`](./RESULTADOS_KPIS.md). |
| Manter código e documentação no repositório GitHub | Concluído | Commit `ac525b5` enviado para `origin/main`. A análise OLTP e esta atualização devem ser incluídas no próximo commit. |
| Elaborar e entregar o artigo acadêmico, com até dez páginas | Não iniciado | Ainda faltam introdução, desenvolvimento, resultados, considerações finais e formatação institucional. |

## Validações realizadas

- A DAG `carga_incremental_recursos_humanos_adventureworks` executou com sucesso
  após a recriação do container Airflow; as cinco tarefas concluíram.
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

## Próximas ações

1. Capturar as telas do Airflow (visualização do fluxo e uma execução concluída)
   e, se necessário, renderizar o diagrama de [`modelo_estrela.mmd`](./modelo_estrela.mmd)
   para PNG ou SVG.
2. Redigir o artigo conforme o padrão institucional da Unisales, respeitando o
   limite de dez páginas.
3. Incluir no artigo a análise OLTP, o modelo, a granularidade, o dicionário, a
   estratégia incremental, as decisões técnicas, as dez KPIs e os resultados
   observados.
4. Revisar os resultados, conferir o limite de páginas e preparar a entrega.
5. Após as alterações finais, registrar e enviar o novo commit ao repositório
   GitHub.
