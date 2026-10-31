# Acompanhamento dos requisitos do trabalho

Revisão do enunciado em `README.md`: **31/10/2026**.

## Estimativa de conclusão

**Estimativa atual: aproximadamente 63% do trabalho total.** O README não define
pesos numéricos para os itens, portanto este percentual é uma estimativa de
acompanhamento, não uma nota prevista. Para torná-la transparente, considerei
70% para preparação técnica e evidências do projeto e 30% para o artigo
acadêmico, que o enunciado destaca como parte de peso elevado. A parte técnica
está estimada em 90% concluída; o artigo ainda não foi iniciado:

`(70% × 90%) + (30% × 0%) = 63%`

O percentual técnico não é 100% porque ainda faltam formalizar a análise OLTP no
artigo, capturar as telas solicitadas do Airflow e sincronizar as alterações
locais com o GitHub.

## Situação dos requisitos do README

| Requisito | Situação | Evidência ou pendência |
| --- | --- | --- |
| Avaliar o modelo OLTP AdventureWorks | Parcial | Schemas, tabelas, colunas e distribuições agregadas de Recursos Humanos foram consultados. Falta transformar a avaliação do OLTP em seção acadêmica. |
| Definir dez indicadores | Concluído | Dez indicadores de funcionários descritos em [`ETL_INCREMENTAL.md`](./ETL_INCREMENTAL.md). |
| Projetar o modelo no padrão Star Schema | Concluído | Dois esquemas estrela relacionados, com granularidades definidas e dimensões compartilhadas. |
| Elaborar o diagrama do modelo estrela | Concluído | Diagrama editável em [`modelo_estrela.mmd`](./modelo_estrela.mmd). |
| Implementar o Data Warehouse no PostgreSQL | Concluído | Tabelas criadas e carga real de 290 funcionários e 316 registros de remuneração validada. |
| Desenvolver o processo ETL com Apache Airflow | Concluído tecnicamente | DAG descoberta e execução completa de teste pelo Airflow, com cinco tarefas bem-sucedidas. Ainda faltam capturas de tela para inserir no artigo. |
| Garantir carga incremental | Concluído tecnicamente | Primeira carga executada; repetição sem alteração processou zero funcionários, departamentos, turnos e alterações de remuneração. |
| Implementar em SQL as dez KPIs | Concluído | Consultas executadas no PostgreSQL; resultados resumidos em [`RESULTADOS_KPIS.md`](./RESULTADOS_KPIS.md). |
| Manter código e documentação no repositório GitHub | Parcial | O repositório Git possui remoto GitHub configurado, mas as alterações atuais ainda estão somente na cópia local, sem commit ou envio. |
| Elaborar e entregar o artigo acadêmico, com até dez páginas | Não iniciado | Ainda faltam introdução, desenvolvimento, resultados, considerações finais e formatação institucional. |

## Próximas ações

1. Redigir o artigo conforme o padrão institucional da Unisales, respeitando o
   limite de dez páginas.
2. Incluir a análise OLTP, o modelo, a granularidade, o dicionário, a estratégia
   incremental, as decisões técnicas, as dez KPIs e os resultados observados.
3. Executar a DAG pela interface do Airflow e capturar as telas do fluxo e de
   uma execução concluída.
4. Conferir os resultados no texto, revisar o limite de páginas e preparar a
   entrega.
5. Ao concluir e revisar as alterações, registrá-las e enviá-las ao repositório
   GitHub do trabalho.
