#!/usr/bin/env python3
"""Etapa 3b — palha de cana nas usinas: calibração dos raios pela distância observada cana → moagem.

Decisão do CHECKPOINT 2 (24/09/2026): a palha vem dos mesmos talhões que abastecem as usinas, e o uso realista
(digestão ou queima) é na usina, junto de vinhaça e torta. Por isso:
1. Destinos da palha: as 160 usinas de SP (mesmos pontos da v4) e as usinas de divisa (config → palha.ufs_divisa)
   dentro do buffer do grafo.
2. Distância POR ESTRADA de cada local com oferta de PALHA até a usina mais próxima (Dijkstra multi-fonte).
3. Percentis ponderados pela oferta de PALHA (N3 med) viram os raios: min P50/P90, med P75/P95, max P90/P99.
4. FL da palha no local = w(d; r1, r2) do cenário. Não depende da variante (co/mono, cobertura/alocação), porque
   a palha deixa de contar para a viabilidade dos hubs da grade.

Uso:    python 03b_palha_usinas.py [completo|sem_track]
Saídas: cache/palha_usinas{suf}.npz, outputs/palha_usinas_calibracao{suf}.csv, outputs/figuras/palha_distancia_usina.png
"""
from __future__ import annotations

import sys

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

import fl_comum as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

VAR = sys.argv[1] if len(sys.argv) > 1 else "completo"
SUF = "" if VAR == "completo" else f"_{VAR}"
log = C.logger(f"03b_palha_usinas{SUF}")
CF = C.CFG
PA = CF["palha"]
TORT = 1.30        # tortuosidade mediana (01_grafo.py), só para comparar com a estimativa prévia euclidiana

G = C.carregar_grafo(VAR)
tree = cKDTree(np.c_[G["x"], G["y"]])
LOC = pd.read_pickle(C.CACHE / "locais_nos.pkl")
if VAR != "completo":
    d, j = tree.query(LOC[["x", "y"]].to_numpy())
    LOC["node"], LOC["conn_m"] = j.astype(np.int64), d
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
PT = pd.read_pickle(C.CACHE / "pontos_fonte.pkl")
mun = C.municipios()

with C.etapa(log, "Usinas de destino (SP + divisa dentro do buffer do grafo)"):
    sp_us = PT[PT.tipo == "usina"][["ref", "nome", "x", "y"]].assign(uf="SP")
    us = gpd.read_file(C.caminho("usinas_etanol")).to_crs(C.CRS)
    buf = mun.union_all().buffer(CF["grafo"]["buffer_estado_km"] * 1000)
    div = us[us.UF.isin(PA["ufs_divisa"]) & us.intersects(buf)]
    div = pd.DataFrame({"ref": [f"usina_divisa:{i}" for i in div.index], "nome": div.Nome.to_numpy(),
                        "x": div.geometry.x.to_numpy(), "y": div.geometry.y.to_numpy(), "uf": div.UF.to_numpy()})
    US = pd.concat([sp_us, div], ignore_index=True)
    d, j = tree.query(US[["x", "y"]].to_numpy())
    US["node"], US["conn_m"] = j.astype(np.int64), d
    log.info(f"  {len(US)} usinas: " + ", ".join(f"{k} {v}" for k, v in US.uf.value_counts().items()))

with C.etapa(log, "Distância por estrada de cada local com palha até a usina mais próxima"):
    Sp = OFw.groupby("loc")[[f"PALHA__{sc}" for sc in C.SC]].sum()
    L = LOC.set_index("loc").loc[Sp.index].reset_index()
    L["hub_fonte"] = -1                                  # a palha nunca nasce no ponto da usina
    rot = C.Roteador(G, US, L)
    d = rot.dist(np.ones(len(US), bool), limite_km=500)
    # qual usina é a mais próxima (para medir a participação das de divisa): Dijkstra só com as de SP
    d_sp = rot.dist((US.uf == "SP").to_numpy(), limite_km=500)
    w = Sp["PALHA__med"].to_numpy()
    m = w > 0
    assert np.isfinite(d[m]).all(), "local com palha sem usina alcançável"
    div_share = float(w[m & (d < d_sp - 1)].sum() / w[m].sum())
    # distância euclidiana × tortuosidade, para comparar com a estimativa prévia
    de, _ = cKDTree(US[["x", "y"]].to_numpy()).query(L[["x", "y"]].to_numpy())


def pct_pond(x, peso, ps):
    o = np.argsort(x)
    cw = np.cumsum(peso[o]) / peso.sum()
    return {p: float(x[o][np.searchsorted(cw, p / 100.0)]) for p in ps}


with C.etapa(log, "Percentis ponderados pela oferta de PALHA (N3 med) e raios"):
    ps = [25, 50, 75, 90, 95, 99]
    pr = pct_pond(d[m] / 1000, w[m], ps)
    pe = pct_pond(de[m] * TORT / 1000, w[m], ps)
    RAIOS = {sc: (round(pr[a], 1), round(pr[b], 1)) for sc, (a, b) in PA["percentis_raio"].items()}
    assert all(r2 > r1 for r1, r2 in RAIOS.values()), f"percentis coincidentes: {RAIOS}"
    FL = {}
    for sc in C.SC:
        ws = Sp[f"PALHA__{sc}"].to_numpy()
        FL[sc] = float((ws * C.peso_w(d, *RAIOS[sc])).sum() / ws.sum())
    np.savez(C.CACHE / f"palha_usinas{SUF}.npz", loc=L["loc"].to_numpy(), d=d, d_sp=d_sp,
             **{f"r_{sc}": np.array(RAIOS[sc]) for sc in C.SC})
    T = pd.DataFrame({"percentil": [f"P{p}" for p in ps], "rede_km": [pr[p] for p in ps],
                      "euclid_x_1_30_km": [pe[p] for p in ps],
                      "estimativa_previa_km": [PA["estimativa_previa_km"].get(f"P{p}") for p in ps]})
    R = pd.DataFrame([{"cenario": sc, "percentis": "/".join(f"P{p}" for p in PA["percentis_raio"][sc]),
                       "r1_km": RAIOS[sc][0], "r2_km": RAIOS[sc][1], "FL_palha_estado": FL[sc]} for sc in C.SC])
    with open(C.OUT / f"palha_usinas_calibracao{SUF}.csv", "w", encoding="utf-8-sig", newline="") as f:
        T.round(2).to_csv(f, index=False)
        f.write("\n")
        R.round(4).to_csv(f, index=False)
        f.write(f"\nparticipacao_palha_com_usina_mais_proxima_na_divisa,{div_share:.4f}\n")
    log.info("\n" + T.round(1).to_string(index=False) + "\n\n" + R.round(3).to_string(index=False))
    log.info(f"  palha cuja usina mais próxima fica na divisa ({'/'.join(PA['ufs_divisa'])}): "
             f"{100 * div_share:.1f}% da oferta med")

with C.etapa(log, "Figura: distribuição ponderada da distância até a usina"):
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=150)
    for x, lab, cor, ls in [(d[m] / 1000, "por estrada (rede OSM)", "#1f77b4", "-"),
                            (de[m] * TORT / 1000, "euclidiana × 1,30", "#7f7f7f", "--")]:
        o = np.argsort(x)
        ax.plot(x[o], np.cumsum(w[m][o]) / w[m].sum(), ls, color=cor, label=lab)
    for sc, cor in zip(C.SC, ["#d62728", "#2ca02c", "#9467bd"]):
        r1, r2 = RAIOS[sc]
        ax.axvspan(r1, r2, color=cor, alpha=0.08)
        ax.text((r1 + r2) / 2, 0.04 + 0.06 * C.SC.index(sc), f"{sc}: r1 {r1:.0f} – r2 {r2:.0f} km (FL {FL[sc]:.2f})",
                ha="center", fontsize=7, color=cor)
    ax.set_xlim(0, max(60, pr[99] * 1.1))
    ax.set_xlabel("distância da célula com cana até a usina mais próxima (km)")
    ax.set_ylabel("fração acumulada da oferta de palha (N3 med)")
    ax.set_title("Palha de cana → usina mais próxima (SP + divisa)")
    ax.grid(alpha=0.3)
    ax.legend(loc="center right", fontsize=8)
    fig.tight_layout()
    fig.savefig(C.FIG / f"palha_distancia_usina{SUF}.png")
    plt.close(fig)
log.info("Etapa 3b concluída.")
