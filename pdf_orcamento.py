"""Geração do PDF do orçamento (ReportLab)."""
import os
from datetime import date, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def brl(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_pdf(caminho, dados, empresa, logo_path=None):
    """dados: dict com nome, qtd, peso_total, tempo_txt, comercial_unit,
    atacado_unit, comercial_total, atacado_total, obs, cliente."""
    W, H = A4
    c = canvas.Canvas(caminho, pagesize=A4)
    azul = colors.HexColor("#1f3a5f")
    cinza = colors.HexColor("#555555")

    # Cabeçalho
    c.setFillColor(azul)
    c.rect(0, H - 35 * mm, W, 35 * mm, fill=1, stroke=0)
    x_txt = 20 * mm
    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 15 * mm, H - 30 * mm, 24 * mm, 24 * mm,
                        preserveAspectRatio=True, mask="auto")
            x_txt = 45 * mm
        except Exception:
            pass
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x_txt, H - 18 * mm, empresa.get("nome", "Orçamento"))
    c.setFont("Helvetica", 10)
    c.drawString(x_txt, H - 25 * mm, "Orçamento de impressão 3D")

    # Dados gerais
    hoje = date.today()
    validade = hoje + timedelta(days=int(empresa.get("validade_dias", 7)))
    y = H - 50 * mm
    linhas = []
    if dados.get("cliente"):
        linhas.append(("Cliente", dados["cliente"]))
    linhas += [
        ("Peça(s)", dados["nome"]),
        ("Data", hoje.strftime("%d/%m/%Y")),
        ("Quantidade", str(dados["qtd"])),
        ("Peso total", f"{dados['peso_total']:.1f} g"),
        ("Tempo total", dados["tempo_txt"]),
    ]
    c.setFillColor(colors.black)
    for rotulo, valor in linhas:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, rotulo + ":")
        c.setFont("Helvetica", 11)
        c.drawString(55 * mm, y, str(valor)[:70])
        y -= 7 * mm

    # Cards de preço
    y -= 8 * mm
    for titulo, unit, total, cor in (
        ("Preço comercial", dados["comercial_unit"], dados["comercial_total"], azul),
        ("Preço atacado", dados["atacado_unit"], dados["atacado_total"],
         colors.HexColor("#2e7d32")),
    ):
        c.setFillColor(cor)
        c.roundRect(20 * mm, y - 28 * mm, W - 40 * mm, 28 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 11)
        c.drawString(26 * mm, y - 8 * mm, titulo)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(26 * mm, y - 20 * mm, brl(total))
        c.setFont("Helvetica", 10)
        if dados["qtd"] > 1:
            c.drawRightString(W - 26 * mm, y - 20 * mm, f"{brl(unit)} por unidade")
        y -= 36 * mm

    # Observações
    if dados.get("obs"):
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "Observações")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        for linha in dados["obs"].splitlines():
            while linha:
                c.drawString(20 * mm, y, linha[:95])
                linha = linha[95:]
                y -= 5 * mm

    # Validade e rodapé
    c.setFillColor(cinza)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(20 * mm, 30 * mm,
                 f"Orçamento válido até {validade.strftime('%d/%m/%Y')}.")
    c.setStrokeColor(azul)
    c.line(20 * mm, 24 * mm, W - 20 * mm, 24 * mm)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, 18 * mm, empresa.get("contato", ""))
    c.save()
