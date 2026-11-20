"""DT 3D STUDIO — Calculadora de Orçamento 3D (v21)."""
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core
from pdf_orcamento import brl, gerar_pdf

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json")
LOGO = os.path.join(BASE, "assets", "icone_dt3dstudio.png")
ICONE = os.path.join(BASE, "assets", "icone_dt3dstudio.ico")

EMPRESA_PADRAO = {
    "nome": "DT 3D STUDIO",
    "contato": "Contato: (00) 00000-0000  |  @seuinstagram",
    "validade_dias": 7,
}


def carregar_config():
    cfg = {"empresa": dict(EMPRESA_PADRAO), "params": core.params_para_dict(core.Params())}
    try:
        with open(CFG, encoding="utf-8") as f:
            salvo = json.load(f)
        cfg["empresa"].update(salvo.get("empresa", {}))
        cfg["params"].update(salvo.get("params", {}))
    except (OSError, ValueError):
        pass
    return cfg


def salvar_config(cfg):
    try:
        with open(CFG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as e:
        messagebox.showwarning("Config", f"Não foi possível salvar: {e}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = carregar_config()
        self.title(f"{self.cfg['empresa']['nome']} — Calculadora de Orçamento 3D")
        self.geometry("560x760")
        self.resizable(False, False)
        if os.path.exists(ICONE):
            try:
                self.iconbitmap(ICONE)
            except tk.TclError:
                pass
        self.resultado = None
        self.arquivos = []   # [(nome, peso, horas)]
        self._montar()

    # ---------- interface ----------
    def _montar(self):
        f = ttk.Frame(self, padding=14)
        f.pack(fill="both", expand=True)
        self.v = {k: tk.StringVar() for k in
                  ("cliente", "nome", "peso", "bobina", "qtd", "tempo")}
        self.v["qtd"].set("1")
        self.v["bobina"].set("100")
        self.v_tarifa = tk.StringVar(value=str(self.cfg["params"]["tarifa_kwh"]).replace(".", ","))
        self.v_lucro = tk.StringVar(value=f"{self.cfg['params']['lucro_pct']:g}")

        campos = [
            ("Cliente (opcional)", self.v["cliente"]),
            ("Nome da peça", self.v["nome"]),
            ("Peso por unidade (g)", self.v["peso"]),
            ("Preço da bobina (R$/kg)", self.v["bobina"]),
            ("Quantidade", self.v["qtd"]),
            ("Tempo por unidade (2h30, 2:30, 150min)", self.v["tempo"]),
            ("Tarifa de energia (R$/kWh)", self.v_tarifa),
            ("Lucro desejado (%)", self.v_lucro),
        ]
        for i, (rot, var) in enumerate(campos):
            ttk.Label(f, text=rot).grid(row=i, column=0, sticky="w", pady=3)
            e = ttk.Entry(f, textvariable=var, width=28)
            e.grid(row=i, column=1, sticky="e", pady=3)
            e.bind("<Return>", lambda _e: self.calcular())

        ttk.Label(f, text="Observações").grid(row=len(campos), column=0, sticky="nw", pady=3)
        self.obs = tk.Text(f, width=27, height=4)
        self.obs.grid(row=len(campos), column=1, sticky="e", pady=3)

        bt = ttk.Frame(f)
        bt.grid(row=len(campos) + 1, column=0, columnspan=2, pady=10)
        for txt, cmd in (("📂 Importar .3mf", self.importar),
                         ("Calcular", self.calcular),
                         ("📄 Exportar PDF", self.exportar),
                         ("⚙ Config", self.abrir_config),
                         ("Limpar", self.limpar)):
            ttk.Button(bt, text=txt, command=cmd).pack(side="left", padx=3)

        self.lbl_arq = ttk.Label(f, text="Nenhum arquivo importado", foreground="#666")
        self.lbl_arq.grid(row=len(campos) + 2, column=0, columnspan=2, sticky="w")

        self.card = ttk.Label(f, text="", justify="left", font=("Consolas", 11),
                              relief="groove", padding=12)
        self.card.grid(row=len(campos) + 3, column=0, columnspan=2, sticky="we", pady=10)
        self.after(100, self._card_vazio)

    def _card_vazio(self):
        self.card.config(text="Preencha os dados e clique em Calcular.")

    # ---------- ações ----------
    def importar(self):
        paths = filedialog.askopenfilenames(
            title="Selecione arquivos .3mf fatiados",
            filetypes=[("Bambu 3MF", "*.3mf")])
        erros = []
        for p in paths:
            try:
                peso, horas = core.ler_3mf(p)
                self.arquivos.append((os.path.splitext(os.path.basename(p))[0], peso, horas))
            except Exception as e:
                erros.append(f"{os.path.basename(p)}: {e}")
        if erros:
            messagebox.showwarning("Importação", "\n".join(erros))
        if self.arquivos:
            self.v["nome"].set(" + ".join(a[0] for a in self.arquivos))
            self.v["peso"].set(f"{sum(a[1] for a in self.arquivos):.1f}".replace(".", ","))
            self.v["tempo"].set(core.formatar_tempo(sum(a[2] for a in self.arquivos)))
            self.lbl_arq.config(text=f"{len(self.arquivos)} arquivo(s) importado(s)")

    def _params(self):
        p = core.params_de_dict(self.cfg["params"])
        p.tarifa_kwh = core.parse_num(self.v_tarifa.get(), p.tarifa_kwh)
        p.lucro_pct = core.parse_num(self.v_lucro.get(), p.lucro_pct)
        return p

    def calcular(self):
        try:
            peso = core.parse_num(self.v["peso"].get())
            bobina = core.parse_num(self.v["bobina"].get())
            horas = core.parse_tempo(self.v["tempo"].get())
            qtd = int(core.parse_num(self.v["qtd"].get(), 1))
            if peso <= 0 or bobina <= 0 or horas <= 0:
                raise ValueError("peso, preço da bobina e tempo devem ser maiores que zero")
            r = core.calcular(peso, bobina, horas, qtd, self._params())
        except ValueError as e:
            messagebox.showerror("Dados inválidos", str(e))
            return
        self.resultado = (r, peso * r["qtd"], horas * r["qtd"])
        txt = (f"Material  {brl(r['material']):>12}\n"
               f"Energia   {brl(r['energia']):>12}\n"
               f"Desgaste  {brl(r['desgaste']):>12}\n"
               f"Máquina   {brl(r['maquina']):>12}\n"
               f"Custo/un  {brl(r['custo_unit']):>12}\n"
               f"{'-' * 22}\n"
               f"COMERCIAL {brl(r['comercial_total']):>12}  ({brl(r['comercial_unit'])}/un)\n"
               f"ATACADO   {brl(r['atacado_total']):>12}  ({brl(r['atacado_unit'])}/un)\n"
               f"Lucro est.{brl(r['lucro_total']):>12}")
        self.card.config(text=txt)

    def exportar(self):
        if not self.resultado:
            self.calcular()
            if not self.resultado:
                return
        r, peso_total, horas_total = self.resultado
        nome = self.v["nome"].get().strip() or "orcamento"
        seguro = "".join(ch for ch in nome if ch.isalnum() or ch in " -_")[:40].strip()
        caminho = filedialog.asksaveasfilename(
            defaultextension=".pdf", initialfile=f"Orcamento_{seguro}.pdf",
            filetypes=[("PDF", "*.pdf")])
        if not caminho:
            return
        dados = {
            "nome": nome, "cliente": self.v["cliente"].get().strip(),
            "qtd": r["qtd"], "peso_total": peso_total,
            "tempo_txt": core.formatar_tempo(horas_total),
            "comercial_unit": r["comercial_unit"], "atacado_unit": r["atacado_unit"],
            "comercial_total": r["comercial_total"], "atacado_total": r["atacado_total"],
            "obs": self.obs.get("1.0", "end").strip(),
        }
        try:
            gerar_pdf(caminho, dados, self.cfg["empresa"], LOGO)
            messagebox.showinfo("PDF", "Orçamento exportado com sucesso!")
        except Exception as e:
            messagebox.showerror("PDF", f"Falha ao gerar o PDF:\n{e}")

    def limpar(self):
        for k in ("cliente", "nome", "peso", "tempo"):
            self.v[k].set("")
        self.v["qtd"].set("1")
        self.obs.delete("1.0", "end")
        self.arquivos.clear()
        self.resultado = None
        self.lbl_arq.config(text="Nenhum arquivo importado")
        self._card_vazio()

    def abrir_config(self):
        win = tk.Toplevel(self)
        win.title("Configurações")
        win.resizable(False, False)
        f = ttk.Frame(win, padding=12)
        f.pack()
        rotulos = {
            "potencia_kw": "Consumo da impressora (kW)",
            "desgaste_pct": "Desgaste (% do material)",
            "custo_maquina_h": "Custo da máquina (R$/h)",
            "atacado_pct": "Preço atacado (% do comercial)",
            "multiplo_arredondamento": "Arredondar para múltiplo de (R$)",
        }
        vars_ = {}
        for i, (k, rot) in enumerate(rotulos.items()):
            ttk.Label(f, text=rot).grid(row=i, column=0, sticky="w", pady=3)
            vars_[k] = tk.StringVar(value=str(self.cfg["params"][k]).replace(".", ","))
            ttk.Entry(f, textvariable=vars_[k], width=14).grid(row=i, column=1, padx=6)
        emp = {}
        for j, (k, rot) in enumerate((("nome", "Nome da empresa"),
                                      ("contato", "Contato (rodapé do PDF)"),
                                      ("validade_dias", "Validade (dias)"))):
            ttk.Label(f, text=rot).grid(row=len(rotulos) + j, column=0, sticky="w", pady=3)
            emp[k] = tk.StringVar(value=str(self.cfg["empresa"][k]))
            ttk.Entry(f, textvariable=emp[k], width=32).grid(row=len(rotulos) + j, column=1, padx=6)

        def ok():
            try:
                for k, var in vars_.items():
                    self.cfg["params"][k] = core.parse_num(var.get())
                self.cfg["empresa"]["nome"] = emp["nome"].get()
                self.cfg["empresa"]["contato"] = emp["contato"].get()
                self.cfg["empresa"]["validade_dias"] = int(core.parse_num(emp["validade_dias"].get(), 7))
            except ValueError:
                messagebox.showerror("Config", "Valor numérico inválido.")
                return
            salvar_config(self.cfg)
            self.title(f"{self.cfg['empresa']['nome']} — Calculadora de Orçamento 3D")
            win.destroy()

        ttk.Button(f, text="Salvar", command=ok).grid(
            row=len(rotulos) + 3, column=0, columnspan=2, pady=10)


if __name__ == "__main__":
    App().mainloop()
