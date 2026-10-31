# Resultados das KPIs de Recursos Humanos

Resultados calculados no PostgreSQL em **31/10/2026** após a primeira carga
completa dos dados disponíveis no AdventureWorks2025. As contagens são da base
de demonstração e não representam uma organização real.

| # | KPI | Resultado observado |
| --- | --- | --- |
| 1 | Funcionários ativos | 290 funcionários marcados como atuais. |
| 2 | Funcionários por departamento | Production: 179; Sales: 18; Purchasing: 12. Há 16 departamentos na consulta. |
| 3 | Funcionários por cargo | Os três cargos com maior contagem foram Production Technician - WC40: 26; WC50: 26; WC60: 26. A consulta retornou 67 cargos. |
| 4 | Distribuição por gênero | M: 206 (71,03%); F: 84 (28,97%). |
| 5 | Contratações por ano | 2006: 1; 2007: 6; 2008: 74; 2009: 148; 2010: 38; 2011: 16; 2012: 4; 2013: 3. |
| 6 | Tempo médio de empresa | 17,41 anos, calculados até a data de execução. |
| 7 | Taxa média de remuneração mais recente | Média por frequência de pagamento: código 1: 12,12; código 2: 26,09. O código da origem é mantido, sem somar ou converter frequências. |
| 8 | Variação entre taxas consecutivas | Frequência 1: 16 comparações, variação média 1,4844 e acumulada 21,59%; frequência 2: 10 comparações, variação média 8,3282 e acumulada 36,66%. |
| 9 | Horas registradas de férias e afastamento | Média geral: 50,61 horas de férias e 45,31 horas de afastamento. |
| 10 | Funcionários por turno | Day: 176 (07:00–15:00); Evening: 62 (15:00–23:00); Night: 52 (23:00–07:00). |

## Interpretação e limites

- 290 funcionários estão marcados como atuais na amostra.
- As contratações observadas vão de 2006 a 2013; assim, o tempo médio de empresa
  calculado em 2026 descreve o banco de demonstração e pode induzir a uma
  interpretação inadequada sobre uma empresa atual.
- A base consultada não apresenta funcionários desligados para comparar entrada
  e saída; por isso, não foi calculada taxa de rotatividade.
- Os códigos de frequência de pagamento não foram traduzidos em periodicidades
  nem usados para converter a taxa em salário anual.
- Horas de férias e afastamento são campos cadastrados, não registros de horas
  efetivamente utilizadas.

## Validação incremental

A primeira carga processou 16 departamentos, 3 turnos, 290 funcionários e 316
registros de remuneração. Uma execução subsequente, sem alterações nas tabelas
de origem, processou zero registros em todas as categorias. A DAG também foi
executada pelo comando de teste do Airflow e concluiu todas as cinco tarefas com
sucesso.
