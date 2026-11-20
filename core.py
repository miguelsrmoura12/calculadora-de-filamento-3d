"""Lógica de cálculo e leitura de .3mf (sem interface gráfica)."""
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict


@dataclass
class Params:
    tarifa_kwh: float = 0.88        # R$/kWh
    potencia_kw: float = 0.10       # consumo médio da impressora (kW)
    desgaste_pct: float = 10.0      # % do custo de material
    custo_maquina_h: float = 2.00   # R$/h
    lucro_pct: float = 50.0
    atacado_pct: float = 90.0       # preço atacado = comercial x %
    multiplo_arredondamento: float = 5.0


def parse_num(texto, padrao=0.0):
    """Converte '1.234,56' / '12,5' / '12.5' em float."""
    t = str(texto).strip().replace("R$", "").replace(" ", "")
    if not t:
        return padrao
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t)


def parse_tempo(texto):
    """Aceita '2h30', '2:30', '150min', '2h', '45m' ou número puro (= horas).
    Retorna horas (float)."""
    t = str(texto).strip().lower().replace(" ", "")
    if not t:
        return 0.0
    m = re.fullmatch(r"(\d+)[h:](\d{1,2})(?:m(?:in)?)?", t)
    if m:
        return int(m[1]) + int(m[2]) / 60
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)h", t)
    if m:
        return float(m[1].replace(",", "."))
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)m(?:in)?", t)
    if m:
        return float(m[1].replace(",", ".")) / 60
    return float(t.replace(",", "."))


def formatar_tempo(horas):
    total_min = round(horas * 60)
    return f"{total_min // 60}h{total_min % 60:02d}"


def ler_3mf(caminho):
    """Lê peso (g) e tempo (h) de um .3mf fatiado no Bambu Studio.
    Soma todas as placas (plates). Levanta ValueError se não achar dados."""
    try:
        with zipfile.ZipFile(caminho) as z:
            nome_cfg = next((n for n in z.namelist()
                             if n.lower().endswith("slice_info.config")), None)
            if not nome_cfg:
                raise ValueError("arquivo sem dados de fatiamento "
                                 "(fatie no Bambu Studio antes de exportar)")
            raiz = ET.fromstring(z.read(nome_cfg))
    except zipfile.BadZipFile:
        raise ValueError("não é um .3mf válido")

    peso = 0.0
    segundos = 0.0
    for plate in raiz.iter("plate"):
        meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
        segundos += float(meta.get("prediction") or 0)
        p_plate = float(meta.get("weight") or 0)
        if not p_plate:  # fallback: soma dos filamentos usados
            p_plate = sum(float(f.get("used_g") or 0)
                          for f in plate.iter("filament"))
        peso += p_plate

    if peso <= 0 and segundos <= 0:
        raise ValueError("peso e tempo não encontrados no arquivo")
    return peso, segundos / 3600


def arredondar_cima(valor, multiplo):
    if multiplo <= 0:
        return round(valor, 2)
    return math.ceil(valor / multiplo - 1e-9) * multiplo


def calcular(peso_g, preco_bobina_kg, horas, qtd, p: Params):
    """Peso e tempo são POR UNIDADE; o resultado traz unitário e total."""
    qtd = max(int(qtd), 1)
    material = peso_g * preco_bobina_kg / 1000
    energia = horas * p.potencia_kw * p.tarifa_kwh
    desgaste = material * p.desgaste_pct / 100
    maquina = horas * p.custo_maquina_h
    custo = material + energia + desgaste + maquina
    final = custo * (1 + p.lucro_pct / 100)
    comercial = arredondar_cima(final, p.multiplo_arredondamento)
    atacado = round(comercial * p.atacado_pct / 100)
    return {
        "material": material, "energia": energia, "desgaste": desgaste,
        "maquina": maquina, "custo_unit": custo, "preco_final_unit": final,
        "comercial_unit": comercial, "atacado_unit": atacado,
        "comercial_total": comercial * qtd, "atacado_total": atacado * qtd,
        "lucro_total": (final - custo) * qtd, "qtd": qtd,
    }


def params_de_dict(d):
    validos = Params.__dataclass_fields__
    return Params(**{k: float(v) for k, v in d.items() if k in validos})


def params_para_dict(p: Params):
    return asdict(p)
