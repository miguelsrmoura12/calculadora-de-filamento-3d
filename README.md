# 🖨️ Calculadora de Orçamento 3D — v21

Aplicativo desktop em Python (Tkinter) para orçar impressões 3D: importa arquivos
`.3mf` fatiados no Bambu Studio, calcula custos e gera um orçamento em PDF.

## O que mudou em relação à v20

- Código separado em módulos: `core.py` (cálculo + leitura de .3mf), `pdf_orcamento.py` (PDF) e `calculadora3d_v21.py` (interface). O cálculo tem testes automatizados.
- **Parâmetros configuráveis** pela tela ⚙ Config (salvos em `config.json`): consumo da impressora, % de desgaste, custo/hora da máquina, % do atacado, arredondamento, nome da empresa, contato e validade.
- Campo **Cliente** (opcional), que aparece no PDF.
- Peso e tempo são **por unidade**; o PDF e os cards mostram total e valor unitário.
- Leitura do `.3mf` soma todas as placas e informa quais arquivos falharam, sem travar a importação.
- Botão **Limpar** e validação de campos (valores zerados ou inválidos geram aviso).
- A pasta `assets` é opcional: sem logo, tudo funciona.

## Como executar

```bash
pip install -r requirements.txt
python calculadora3d_v21.py
```

Requer Python 3.10+ com Tkinter (já incluso no instalador do Windows e do macOS; no Linux: `sudo apt install python3-tk`).

### Gerar o `.exe` (Windows)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets\icone_dt3dstudio.ico --add-data "assets;assets" --name "DT3DStudio_Calculadora" calculadora3d_v21.py
```

Coloque `icone_dt3dstudio.ico` e `icone_dt3dstudio.png` em `assets/` (opcional).

## Fórmula

```
material  = peso_g × preço_bobina_kg ÷ 1000
energia   = horas × consumo_kW × tarifa
desgaste  = material × desgaste%
máquina   = horas × custo_máquina_h
custo     = material + energia + desgaste + máquina
final     = custo × (1 + lucro%)
comercial = final arredondado PARA CIMA ao múltiplo configurado (padrão R$ 5)
atacado   = comercial × atacado% (padrão 90%), arredondado ao real
```

Tempo aceita `2h30`, `2:30`, `150min`, `2h` ou número puro (= horas).

## Testes

```bash
python tests/test_core.py   # ou: pytest tests
```

## Estrutura

```
├── calculadora3d_v21.py   # interface
├── core.py                # cálculo e leitura de .3mf
├── pdf_orcamento.py       # geração do PDF
├── tests/test_core.py
├── assets/                # logo/ícone (opcional)
└── requirements.txt
```
