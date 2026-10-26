#!/usr/bin/env python3
"""Etapa 7 — reconciliação oficial N4 v4 × v5 depois de rodar a cascata v5 (cp2b_cascade.py com FL = "espacial").

Lê a base N3 (n3_municipal: linhas da v4, com o bagaço de citros nas fábricas desde a v5.1) e outputs_v5/cp2b_municipio_substrato.csv (cascata v5, variante
principal) e grava, com e sem lignocelulósicos:
  outputs_v5/reconciliacao_v4_v5_estado.csv      níveis N1–N4 por cenário
  outputs_v5/reconciliacao_v4_v5_fluxo_med.csv   N3 e N4 por fluxo (med)
  outputs_v5/reconciliacao_v4_v5_top20_med.csv   20 maiores municípios em N4 (v4 e v5)
Confere: N1–N3 da v5 iguais aos da base (tolerância relativa 1e-9: a cascata recalcula o citros nas fábricas); N4 da v5 idêntico ao da variante principal em 06_integracao.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import fl_comum as C

log = C.logger("07_reconciliacao_v5")
IN = C.CFG["integracao"]
OUT5 = C.Path(IN["saida_v5"])
k = ["ibge", "codigo", "cenario"]
v4 = pd.read_csv(C.caminho("n3_municipal")).set_index(k).sort_index()
v5 = pd.read_csv(OUT5 / "cp2b_municipio_substrato.csv").set_index(k).sort_index()
i6 = pd.read_csv(OUT5 / f"{IN['prefixo']}{IN['variante_principal']}_cp2b_municipio_substrato.csv").set_index(k).sort_index()
lv = ["L1_CH4", "L2_CH4", "L3a_CH4", "L3_CH4", "L4_CH4"]

with C.etapa(log, "Conferências"):
    d13 = {c: float((np.abs(v5[c] - v4[c]) / v4[c].abs().clip(lower=1.0)).max()) for c in lv[:4]}
    d4 = float(np.abs(v5.L4_CH4 - i6.L4_CH4).max())
    log.info(f"  N1–N3 v5 × base, desvio relativo máx: {d13}; N4 cascata × 06_integracao: {d4:.3e} Nm³/ano")
    assert max(d13.values()) < 1e-9 and d4 < 1e-3

A = v4.reset_index()
B = v5.reset_index()
bases = {"com lignocel.": np.ones(len(A), bool), "sem lignocel.": ~A.lignocel.to_numpy()}

with C.etapa(log, "Reconciliação por estado, fluxo e município"):
    rows = []
    for base, f in bases.items():
        for sc in C.SC:
            m = (A.cenario == sc).to_numpy() & f
            r = {"base": base, "cenario": sc}
            for c in lv:
                r[f"{c[:-4]}_v4_M_m3dia"] = A.loc[m, c].sum() / 1e6 / C.DAYS
            r["L4_v5_M_m3dia"] = B.loc[m, "L4_CH4"].sum() / 1e6 / C.DAYS
            r["dif_L4_%"] = 100 * (r["L4_v5_M_m3dia"] / r["L4_v4_M_m3dia"] - 1)
            r["L4_v4_bi_ano"], r["L4_v5_bi_ano"] = A.loc[m, "L4_CH4"].sum() / 1e9, B.loc[m, "L4_CH4"].sum() / 1e9
            rows.append(r)
    RE = pd.DataFrame(rows)
    RE.to_csv(OUT5 / "reconciliacao_v4_v5_estado.csv", index=False, encoding="utf-8-sig")

    fx = []
    for base, f in bases.items():
        m = (A.cenario == "med").to_numpy() & f
        g4, g5 = A[m].groupby("fluxo"), B[m].groupby("fluxo")
        t = pd.DataFrame({"N3_M_m3dia": g4.L3_CH4.sum() / 1e6 / C.DAYS, "N4_v4_M_m3dia": g4.L4_CH4.sum() / 1e6 / C.DAYS,
                          "N4_v5_M_m3dia": g5.L4_CH4.sum() / 1e6 / C.DAYS})
        t["dif_N4_%"] = 100 * (t.N4_v5_M_m3dia / t.N4_v4_M_m3dia - 1)
        tot = t.sum()
        tot["dif_N4_%"] = 100 * (tot.N4_v5_M_m3dia / tot.N4_v4_M_m3dia - 1)
        t.loc["TOTAL"] = tot
        fx.append(t.assign(base=base))
    pd.concat(fx).to_csv(OUT5 / "reconciliacao_v4_v5_fluxo_med.csv", encoding="utf-8-sig")

    mun = C.municipios().set_index("ibge").municipio
    tops = []
    for base, f in bases.items():
        m = (A.cenario == "med").to_numpy() & f
        T = pd.DataFrame({"N3_m3dia": A[m].groupby("ibge").L3_CH4.sum() / C.DAYS,
                          "N4_v4_m3dia": A[m].groupby("ibge").L4_CH4.sum() / C.DAYS,
                          "N4_v5_m3dia": B[m].groupby("ibge").L4_CH4.sum() / C.DAYS})
        T["dif_N4_%"] = 100 * (T.N4_v5_m3dia / T.N4_v4_m3dia - 1)
        T["municipio"] = T.index.map(mun)
        T["posicao_v4"] = T.N4_v4_m3dia.rank(ascending=False, method="min").astype(int)
        T["posicao_v5"] = T.N4_v5_m3dia.rank(ascending=False, method="min").astype(int)
        tops.append(T.sort_values("N4_v4_m3dia", ascending=False).head(20).assign(base=base, ranking="top 20 v4"))
        tops.append(T.sort_values("N4_v5_m3dia", ascending=False).head(20).assign(base=base, ranking="top 20 v5"))
    pd.concat(tops).to_csv(OUT5 / "reconciliacao_v4_v5_top20_med.csv", encoding="utf-8-sig")
    log.info("\n" + RE[["base", "cenario", "L3_v4_M_m3dia", "L4_v4_M_m3dia", "L4_v5_M_m3dia", "dif_L4_%"]]
             .round(2).to_string(index=False))
log.info("Etapa 7 concluída.")
