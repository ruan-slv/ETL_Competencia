# Artigo acadêmico

Esta pasta contém o artigo do trabalho, com estrutura alinhada ao enunciado do
`README.md` e limite de **10 páginas**.

## Arquivos

| Arquivo | Descrição |
| --- | --- |
| `artigo.md` | Fonte editável em Markdown. |
| `artigo.docx` | Versão formatada para entrega (A4, margens 3/2/3/2 cm, Times New Roman 12, espaçamento 1,5). |
| `artigo.pdf` | Pré-visualização gerada a partir do DOCX. |
| `gerar_docx.py` | Converte `artigo.md` em `artigo.docx` e reaplica a formatação. |

## Antes de entregar

1. Substituir os campos `[Nome do estudante]`, `[Curso]` e
   `[E-mail institucional]` no início de `artigo.md`.
2. Conferir se o template institucional da Unisales exige capa, folha de
   aprovação, cabeçalho ou numeração específica.
3. Revisar o texto, as legendas e a ortografia.
4. Regerar o DOCX e o PDF após qualquer alteração.

## Como regerar

Na raiz do projeto, com o ambiente virtual disponível:

```powershell
.\.venv\Scripts\python.exe "CONSTRUÇÃO_ARTIGO\gerar_docx.py"
```

Para gerar o PDF, abra o DOCX no Word/LibreOffice e exporte, ou use:

```powershell
& 'C:\Program Files\LibreOffice\program\soffice.exe' --headless `
  --convert-to pdf --outdir "CONSTRUÇÃO_ARTIGO" "CONSTRUÇÃO_ARTIGO\artigo.docx"
```

A versão atual foi conferida com o LibreOffice e possui 10 páginas. Pequenas
alterações de fonte ou de template podem mudar a paginação; verifique novamente
antes da entrega.

## Estrutura do artigo

- Resumo e Abstract
- 1 Introdução
- 2 Referencial teórico (Data Warehouse, ETL incremental e Airflow)
- 3 Desenvolvimento
  - 3.1 Análise do modelo OLTP
  - 3.2 Modelo multidimensional e granularidade
  - 3.3 Dicionário de dados
  - 3.4 Indicadores
  - 3.5 Estratégia de ETL incremental
  - 3.6 Pipeline no Apache Airflow
  - 3.7 Implementação SQL dos indicadores
  - 3.8 Resultados
- 4 Considerações finais
- Referências

## Evidências utilizadas

- `docs/images/ETL_Competencia_Diagrama.drawio.png` — diagrama do modelo estrela.
- `docs/images/Airflow_Executado.png` — execução da DAG no Airflow.
- `docs/RESULTADOS_KPIS.md` — resultados dos dez indicadores.
- `docs/DICIONARIO_DADOS.md` — dicionário completo.
- `src/sql/indicadores.sql` — consultas SQL dos indicadores.
