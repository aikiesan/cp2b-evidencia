"""Municípios com FL med zero: distância por estrada até o hub selecionado mais próximo (B, palha nas usinas)."""
import numpy as np
import pandas as pd

import fl_comum as C

CF = C.CFG
R, QMIN = CF["raios_km"]["med"], CF["q_min"]["med"]
G = C.carregar_grafo("completo")
HUBS = pd.read_pickle(C.CACHE / "hubs.pkl")
LOC = pd.read_pickle(C.CACHE / "locais_nos.pkl")
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
A = pd.read_csv(C.OUT / "alocacao_hubs_codigestao.csv")
sel = A.loc[(A.modo_palha == "usinas") & (A.cenario == "med"), "hub_id"]
mask = HUBS.hub_id.isin(sel).to_numpy()
d_loc = C.Roteador(G, HUBS, LOC).dist(mask, 150) / 1000.0
pos = pd.Series(np.arange(len(LOC)), index=LOC["loc"].to_numpy())
d_of = d_loc[pos.loc[OFw["loc"]].to_numpy()]
zp = np.load(C.CACHE / "palha_usinas.npz")
d_palha = pd.Series(zp["d"], index=zp["loc"]).reindex(OFw["loc"]).to_numpy() / 1000.0
r_palha = tuple(float(x) for x in zp["r_med"])

FL = pd.read_csv(C.OUT / "fl_v5_municipio_substrato.csv")
M = FL[(FL.cenario == "med") & (FL.oferta_L3_m3dia > 0)]
zmax = M.groupby("ibge").FL_codig_alocado.max()
zeros = zmax.index[zmax <= 1e-12]
nome = M.drop_duplicates("ibge").set_index("ibge").municipio
print(f"{sel.nunique()} hubs selecionados (med, palha nas usinas); {len(zeros)} municípios com FL med zero")

ib = OFw["ibge"].astype(int).to_numpy()
rows = []
for s, spec in CF["espacializacao"].items():
    if spec["fonte"] == "ignorar":
        continue
    v = OFw[f"{s}__med"].to_numpy()
    palha = s == "PALHA" and CF["palha"]["modo"] == "usinas"
    d = d_palha if palha else d_of
    r1, r2 = r_palha if palha else R[C.classes_de(s)]
    k = (v > 0) & np.isin(ib, zeros)
    if not k.any():
        continue
    T = pd.DataFrame({"ibge": ib[k], "d": d[k], "v": v[k]}).sort_values("d", kind="stable")
    for i, g in T.groupby("ibge"):
        acum = g.v.cumsum() / g.v.sum()
        rows.append(dict(ibge=i, municipio=nome.get(i, ""), codigo=s,
                         classe="palha_usinas" if palha else C.classes_de(s), oferta_m3dia=g.v.sum(),
                         d_min_km=g.d.min(), d_mediana_km=g.d[acum.to_numpy() >= 0.5].iloc[0], r1_km=r1, r2_km=r2))
Z = pd.DataFrame(rows).round(3)
Z.to_csv(C.OUT / "v52_zeros_distancia_hub.csv", index=False, encoding="utf-8-sig")
P = (Z.groupby(["ibge", "municipio"])
     .agg(n3_m3dia=("oferta_m3dia", "sum"), d_min_km=("d_min_km", "min"),
          folga_km=("d_min_km", lambda x: (x - Z.loc[x.index, "r2_km"]).min()))
     .reset_index().sort_values("d_min_km"))
P["n3_menor_que_qmin"] = P.n3_m3dia < QMIN
pd.set_option("display.width", 200)
print(P.round(1).to_string(index=False))
print(f"\nfolga_km = menor (d_min − r2) entre os substratos: > 0 quer dizer que nenhuma oferta fica a menos de r2"
      f" de um hub selecionado. Q_min med = {QMIN} Nm3 CH4/dia.")
print(f"d_min: mediana {P.d_min_km.median():.1f} km, faixa {P.d_min_km.min():.1f}–{P.d_min_km.max():.1f} km; "
      f"{int(P.n3_menor_que_qmin.sum())} de {len(P)} com N3 abaixo de Q_min")
