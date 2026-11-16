"""Gera a versão DOCX do artigo a partir de CONSTRUÇÃO_ARTIGO/artigo.md.

Uso:
    .\\.venv\\Scripts\\python.exe "CONSTRUÇÃO_ARTIGO/gerar_docx.py"
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE_DIR = Path(__file__).resolve().parent
ORIGEM = BASE_DIR / "artigo.md"
DESTINO = BASE_DIR / "artigo.docx"

FONTE = "Times New Roman"
TAMANHO_TEXTO = Pt(12)
TAMANHO_TABELA = Pt(8.5)
TAMANHO_LEGENDA = Pt(10)


def _configurar_documento(documento: Document) -> None:
    secao = documento.sections[0]
    secao.page_width = Cm(21)
    secao.page_height = Cm(29.7)
    secao.top_margin = Cm(3)
    secao.bottom_margin = Cm(2)
    secao.left_margin = Cm(3)
    secao.right_margin = Cm(2)

    normal = documento.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = TAMANHO_TEXTO
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for nome in ("List Bullet", "List Number"):
        estilo = documento.styles[nome]
        estilo.font.name = FONTE
        estilo.font.size = TAMANHO_TEXTO


def _adicionar_numero_pagina(documento: Document) -> None:
    paragrafo = documento.sections[0].footer.paragraphs[0]
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragrafo.add_run()
    run.font.name = FONTE
    run.font.size = Pt(10)
    campo_ini = OxmlElement("w:fldChar")
    campo_ini.set(qn("w:fldCharType"), "begin")
    instrucao = OxmlElement("w:instrText")
    instrucao.set(qn("xml:space"), "preserve")
    instrucao.text = "PAGE"
    campo_fim = OxmlElement("w:fldChar")
    campo_fim.set(qn("w:fldCharType"), "end")
    run._r.append(campo_ini)
    run._r.append(instrucao)
    run._r.append(campo_fim)


def _adicionar_cabecalho(documento: Document) -> None:
    paragrafo = documento.sections[0].header.paragraphs[0]
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragrafo.add_run("ETL incremental e Data Warehouse — AdventureWorks")
    run.font.name = FONTE
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    run.italic = True


def _sombrear_celula(celula, cor: str = "E7E6E6") -> None:
    propriedades = celula._tc.get_or_add_tcPr()
    sombreamento = OxmlElement("w:shd")
    sombreamento.set(qn("w:val"), "clear")
    sombreamento.set(qn("w:color"), "auto")
    sombreamento.set(qn("w:fill"), cor)
    propriedades.append(sombreamento)


def _margens_celula(tabela) -> None:
    propriedades = tabela._tbl.tblPr
    margens = OxmlElement("w:tblCellMar")
    for lado, largura in (("top", 20), ("left", 57), ("bottom", 20), ("right", 57)):
        elemento = OxmlElement(f"w:{lado}")
        elemento.set(qn("w:w"), str(largura))
        elemento.set(qn("w:type"), "dxa")
        margens.append(elemento)
    propriedades.append(margens)


def _repetir_cabecalho(linha) -> None:
    propriedades = linha._tr.get_or_add_trPr()
    repeticao = OxmlElement("w:tblHeader")
    repeticao.set(qn("w:val"), "true")
    propriedades.append(repeticao)


def _nao_quebrar_linha(linha) -> None:
    propriedades = linha._tr.get_or_add_trPr()
    sem_quebra = OxmlElement("w:cantSplit")
    sem_quebra.set(qn("w:val"), "true")
    propriedades.append(sem_quebra)


def _adicionar_execucoes(paragrafo, texto: str, tamanho=Pt(12)) -> None:
    padrao = re.compile(r"(\*\*.+?\*\*|`.+?`|\*[^*]+?\*)")
    posicao = 0
    for correspondencia in padrao.finditer(texto):
        if correspondencia.start() > posicao:
            run = paragrafo.add_run(texto[posicao : correspondencia.start()])
            run.font.name = FONTE
            run.font.size = tamanho
        trecho = correspondencia.group(0)
        run = paragrafo.add_run()
        run.font.size = tamanho
        if trecho.startswith("**"):
            conteudo = trecho[2:-2]
            if conteudo.startswith("`") and conteudo.endswith("`"):
                run.text = conteudo[1:-1]
                run.font.name = "Consolas"
                run.font.size = Pt(tamanho.pt - 1)
            else:
                run.text = conteudo.replace("`", "")
                run.font.name = FONTE
            run.bold = True
        elif trecho.startswith("`"):
            run.text = trecho[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(tamanho.pt - 1)
        else:
            run.text = trecho[1:-1]
            run.italic = True
            run.font.name = FONTE
        posicao = correspondencia.end()
    if posicao < len(texto):
        run = paragrafo.add_run(texto[posicao:])
        run.font.name = FONTE
        run.font.size = tamanho


def _paragrafo_texto(
    documento: Document,
    texto: str,
    *,
    recuo: bool = True,
    espacamento: float | None = None,
    alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY,
) -> None:
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = alinhamento
    if recuo:
        paragrafo.paragraph_format.first_line_indent = Cm(1.25)
    if espacamento is not None:
        paragrafo.paragraph_format.line_spacing = espacamento
    _adicionar_execucoes(paragrafo, texto)


def _titulo(documento: Document, texto: str) -> None:
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragrafo.paragraph_format.space_after = Pt(12)
    run = paragrafo.add_run(texto)
    run.bold = True
    run.font.name = FONTE
    run.font.size = Pt(14)


def _secao(documento: Document, texto: str) -> None:
    paragrafo = documento.add_paragraph()
    paragrafo.paragraph_format.space_before = Pt(6)
    paragrafo.paragraph_format.space_after = Pt(3)
    paragrafo.paragraph_format.keep_with_next = True
    run = paragrafo.add_run(texto)
    run.bold = True
    run.font.name = FONTE
    run.font.size = TAMANHO_TEXTO


def _legenda(documento: Document, texto: str) -> None:
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragrafo.paragraph_format.space_before = Pt(6)
    paragrafo.paragraph_format.space_after = Pt(3)
    paragrafo.paragraph_format.keep_with_next = True
    paragrafo.paragraph_format.line_spacing = 1
    run = paragrafo.add_run(texto)
    run.bold = True
    run.font.name = FONTE
    run.font.size = TAMANHO_LEGENDA


def _fonte_tabela(documento: Document, texto: str) -> None:
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragrafo.paragraph_format.space_after = Pt(12)
    paragrafo.paragraph_format.line_spacing = 1
    run = paragrafo.add_run(texto)
    run.italic = True
    run.font.name = FONTE
    run.font.size = TAMANHO_TABELA


def _tabela(documento: Document, linhas: list[list[str]]) -> None:
    colunas = max(len(linha) for linha in linhas)
    tabela = documento.add_table(rows=len(linhas), cols=colunas)
    tabela.style = "Table Grid"
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabela.autofit = False
    _margens_celula(tabela)

    larguras = Cm(16) / colunas
    if colunas == 3:
        if linhas[0][0] == "Tabela":
            pesos = [2.6, 1.0, 3.4] if linhas[0][1] == "Linhas" else [1.6, 2.5, 1.5]
        else:
            pesos = [0.5, 2.2, 2.4]
        total = sum(pesos)
        larguras = [Cm(16 * peso / total) for peso in pesos]
        for indice_coluna, largura in enumerate(larguras):
            tabela.columns[indice_coluna].width = largura

    for indice_linha, valores in enumerate(linhas):
        linha = tabela.rows[indice_linha]
        for indice_coluna in range(colunas):
            texto = valores[indice_coluna] if indice_coluna < len(valores) else ""
            celula = linha.cells[indice_coluna]
            if colunas == 3 and isinstance(larguras, list):
                celula.width = larguras[indice_coluna]
            paragrafo = celula.paragraphs[0]
            paragrafo.paragraph_format.line_spacing = 1
            paragrafo.paragraph_format.space_after = Pt(0)
            if indice_linha == 0:
                paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                paragrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _adicionar_execucoes(paragrafo, texto, tamanho=TAMANHO_TABELA)
            if indice_linha == 0:
                for run in paragrafo.runs:
                    run.bold = True
                _sombrear_celula(celula)
            if indice_linha < len(linhas) - 1:
                paragrafo.paragraph_format.keep_with_next = True
        _nao_quebrar_linha(linha)
        if indice_linha == 0:
            _repetir_cabecalho(linha)


def _imagem(documento: Document, caminho: Path) -> None:
    if not caminho.exists():
        _paragrafo_texto(documento, f"[Imagem não encontrada: {caminho.name}]")
        return
    paragrafo = documento.add_paragraph()
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragrafo.paragraph_format.space_before = Pt(3)
    paragrafo.paragraph_format.space_after = Pt(3)
    largura = Cm(12.5) if "Diagrama" in caminho.name else Cm(15.5)
    paragrafo.add_run().add_picture(str(caminho), width=largura)


def _codigo(documento: Document, linhas: list[str]) -> None:
    for indice, linha in enumerate(linhas):
        paragrafo = documento.add_paragraph()
        paragrafo.paragraph_format.line_spacing = 1
        paragrafo.paragraph_format.space_after = Pt(0)
        paragrafo.paragraph_format.space_before = Pt(6) if indice == 0 else Pt(0)
        paragrafo.paragraph_format.left_indent = Cm(1)
        run = paragrafo.add_run(linha if linha else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(8.5)
    documento.add_paragraph().paragraph_format.space_after = Pt(0)


def _links_como_texto(texto: str) -> str:
    return re.sub(r"<(https?://[^>]+)>", r"\1", texto)


def gerar() -> None:
    linhas = ORIGEM.read_text(encoding="utf-8").splitlines()
    documento = Document()
    _configurar_documento(documento)
    _adicionar_cabecalho(documento)
    _adicionar_numero_pagina(documento)

    em_resumo = False
    em_referencias = False
    em_codigo = False
    bloco_codigo: list[str] = []
    indice = 0

    while indice < len(linhas):
        linha = linhas[indice].rstrip()
        indice += 1

        if linha.startswith("```"):
            if em_codigo:
                _codigo(documento, bloco_codigo)
                bloco_codigo = []
                em_codigo = False
            else:
                em_codigo = True
            continue
        if em_codigo:
            bloco_codigo.append(linha)
            continue

        if not linha.strip():
            continue

        if linha.startswith("# "):
            _titulo(documento, linha[2:].strip())
            continue

        if linha.startswith("## "):
            texto = linha[3:].strip()
            _secao(documento, texto)
            em_resumo = texto.lower() in {"resumo", "abstract"}
            em_referencias = texto.lower() == "referências"
            continue

        if linha.startswith("### "):
            _secao(documento, linha[4:].strip())
            continue

        if linha.startswith("|"):
            bloco = [linha]
            while indice < len(linhas) and linhas[indice].startswith("|"):
                bloco.append(linhas[indice])
                indice += 1
            linhas_tabela: list[list[str]] = []
            for item in bloco:
                celulas = [celula.strip() for celula in item.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", celula) for celula in celulas):
                    continue
                linhas_tabela.append(celulas)
            _tabela(documento, linhas_tabela)
            continue

        if linha.startswith("!["):
            correspondencia = re.search(r"\]\(([^)]+)\)", linha)
            if correspondencia:
                _imagem(documento, (BASE_DIR / correspondencia.group(1)).resolve())
            continue

        if linha.startswith("- "):
            paragrafo = documento.add_paragraph(style="List Bullet")
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragrafo.paragraph_format.space_after = Pt(0)
            _adicionar_execucoes(paragrafo, _links_como_texto(linha[2:].strip()))
            continue

        texto = _links_como_texto(linha.strip())

        if texto.startswith("**Figura") or texto.startswith("**Quadro"):
            _legenda(documento, texto.replace("**", ""))
            continue

        if texto.startswith("*Fonte:"):
            _fonte_tabela(documento, texto.strip("*"))
            continue

        if texto.startswith("**Palavras-chave") or texto.startswith("**Keywords"):
            paragrafo = documento.add_paragraph()
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragrafo.paragraph_format.line_spacing = 1
            paragrafo.paragraph_format.space_after = Pt(12)
            _adicionar_execucoes(paragrafo, texto)
            continue

        if texto.startswith("**[Nome do estudante]**") or texto.startswith("[Curso]") or texto.startswith("[E-mail"):
            paragrafo = documento.add_paragraph()
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragrafo.paragraph_format.space_after = Pt(0)
            _adicionar_execucoes(paragrafo, texto)
            continue

        if em_referencias:
            paragrafo = documento.add_paragraph()
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragrafo.paragraph_format.line_spacing = 1
            paragrafo.paragraph_format.space_after = Pt(6)
            _adicionar_execucoes(paragrafo, texto)
            continue

        if em_resumo:
            _paragrafo_texto(documento, texto, recuo=False, espacamento=1)
            continue

        _paragrafo_texto(documento, texto)

    documento.core_properties.title = (
        "Construção de um Data Warehouse com ETL incremental e Apache Airflow"
    )
    documento.core_properties.subject = "Data Warehouse, Star Schema, ETL incremental, Airflow"
    documento.core_properties.author = "[Nome do estudante]"
    documento.save(DESTINO)
    print(f"Documento gerado: {DESTINO}")


if __name__ == "__main__":
    gerar()
