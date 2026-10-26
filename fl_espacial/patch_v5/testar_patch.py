#!/usr/bin/env python3
"""Roda a cascata com o patch v5 SEM alterar os arquivos da v4 e confere o resultado.

Uso (ambiente fixado, Metodo_CP2b/.venv):  .venv/Scripts/python fl_espacial/patch_v5/testar_patch.py
- executa uma cópia temporária de patch_v5/cp2b_cascade.py com HERE = Metodo_CP2b e o cp2b_params.py do patch;
- a saída vai para outputs_v5/ (P.PASTA_SAIDA); outputs/ da v4 não é tocado;
- confere: N1–N3 idênticos à v4; N4 idêntico ao da variante B em outputs_v5/v5_codig_alocado_cp2b_municipio_substrato.csv (06_integracao.py).
"""
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
METODO = AQUI.parent.parent
src = (AQUI / "cp2b_cascade.py").read_text(encoding="utf-8")
alvo = "HERE = Path(__file__).resolve().parent"
assert alvo in src
tmp = AQUI / "_cascata_teste.py"
tmp.write_text(src.replace(alvo, f'HERE = Path(r"{METODO}")'), encoding="utf-8")
sys.path.insert(0, str(AQUI))            # cp2b_params do patch tem precedência
try:
    runpy.run_path(str(tmp), run_name="__main__")
finally:
    tmp.unlink(missing_ok=True)

k = ["ibge", "codigo", "cenario"]
v4 = pd.read_csv(METODO / "outputs" / "cp2b_municipio_substrato.csv").set_index(k).sort_index()
v5 = pd.read_csv(METODO / "outputs_v5" / "cp2b_municipio_substrato.csv").set_index(k).sort_index()
i6 = pd.read_csv(METODO / "outputs_v5" / "v5_codig_alocado_cp2b_municipio_substrato.csv").set_index(k).sort_index()
print("\n== CONFERÊNCIA DO PATCH ==")
for c in ["L1_CH4", "L2_CH4", "L3a_CH4", "L3_CH4"]:
    print(f"{c}: cascata v5 = v4 → desvio máx {np.abs(v5[c] - v4[c]).max():.3e}")
print(f"L4_CH4: cascata v5 = 06_integracao → desvio máx {np.abs(v5.L4_CH4 - i6.L4_CH4).max():.3e} "
      f"(soma {v5.L4_CH4.sum() / 1e9:.4f} × {i6.L4_CH4.sum() / 1e9:.4f} bi Nm³/ano)")
print(f"L4_CH4 v4 (referência): {v4.L4_CH4.sum() / 1e9:.4f} bi Nm³/ano")
