"""Perturbação da oferta (v5.2): FL municipal de cada rodada no med, para a incerteza do N4 com a rede de hubs.

Roda na CÓPIA (`fl_espacial_v52/`) depois de `v52_perturbacao.py` e só lê: o `config_fl.yaml`, o
`oferta_wide.pkl` (para refazer a ordem das linhas município × substrato, como no script da perturbação), o
`fl_municipio_alocado.csv` (FL da v5.1) e as rodadas em `outputs/v52_perturbacao/runs/`. Confere os p05 e p95
refeitos com `pert_fl_municipio_substrato.csv` e grava `outputs/v52_perturbacao/pert_fl_rodadas_med.csv`:
uma linha por desenho × município × substrato em que alguma rodada difere da v5.1 em mais de 1e-6 (as ausentes
são iguais à v5.1 em todas as rodadas), com o FL da v5.1 e o de cada rodada.
"""
import sys

import numpy as np
import pandas as pd

import fl_comum as C

assert C.HERE.name == "fl_espacial_v52", f"rodando fora da cópia: {C.HERE}"
N_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DESENHOS = ["mun10", "mun30", "sub20_mun20"]
SC = "med"
TOL_Q = 1e-6
TOL_IGUAL = 1e-6      # as rodadas guardam o FL em float32

OUTP = C.OUT / "v52_perturbacao"
RUNS = OUTP / "runs"

# mesma ordem de linhas de v52_perturbacao.py
ESP = C.CFG["espacializacao"]
SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
NS = len(SUBS)
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
for s in SUBS:
    if f"{s}__{SC}" not in OFw:
        OFw[f"{s}__{SC}"] = 0.0
MUN, GI = np.unique(OFw["ibge"].astype(int).to_numpy(), return_inverse=True)
VROW = np.stack([OFw[f"{s}__{SC}"].to_numpy(np.float64) for s in SUBS], axis=1)
gi, sj = np.nonzero(VROW > 0)
CHAVES = np.unique(GI[gi] * NS + sj)
IBGE, COD = MUN[CHAVES // NS], np.array(SUBS)[CHAVES % NS]

R = pd.read_csv(C.OUT / "fl_municipio_alocado.csv")
R = R[R.cenario == SC]
ref = pd.Series(R.FL_codig_alocado.to_numpy(), index=pd.MultiIndex.from_arrays([R.ibge.astype(int), R.codigo]))
FL0 = ref.reindex(pd.MultiIndex.from_arrays([IBGE, COD])).to_numpy()
assert len(R) == len(CHAVES) and not np.isnan(FL0).any(), "linhas do fl_municipio_alocado ≠ chaves da oferta: parei"

Q = pd.read_csv(OUTP / "pert_fl_municipio_substrato.csv")
saida = []
for nome in DESENHOS:
    FL = np.stack([np.load(RUNS / f"{nome}_{SC}_{k:03d}.npz")["fl"].astype(np.float64)
                   for k in range(1, N_RUNS + 1)])
    assert FL.shape[1] == len(CHAVES), f"[{nome}] {FL.shape[1]} linhas nas rodadas × {len(CHAVES)} chaves: parei"
    d = np.abs(FL - FL0).max(axis=0)
    q = Q[(Q.desenho == nome) & (Q.cenario == SC)]
    pos = pd.Series(np.arange(len(CHAVES)), index=pd.MultiIndex.from_arrays([IBGE, COD]))
    i = pos.reindex(pd.MultiIndex.from_arrays([q.ibge.astype(int), q.codigo])).to_numpy()
    assert not np.isnan(i.astype(float)).any(), f"[{nome}] linha do pert_fl_municipio_substrato fora das chaves: parei"
    i = i.astype(int)
    for col, p in (("p05", .05), ("p95", .95), ("FL_v51", None)):
        mine = FL0[i] if p is None else np.quantile(FL[:, i], p, axis=0)
        dq = float(np.abs(mine - q[col].to_numpy()).max()) if len(q) else 0.0
        assert dq < TOL_Q, f"[{nome}] {col} refeito ≠ pert_fl_municipio_substrato (máx |Δ| {dq:.1e}): parei"
    ok = set(np.flatnonzero(d > 0.01 + TOL_IGUAL)) <= set(i) <= set(np.flatnonzero(d > 0.01 - TOL_IGUAL))
    assert ok, f"[{nome}] linhas com |Δ| > 0,01 não batem com o pert_fl_municipio_substrato: parei"
    keep = np.flatnonzero(d > TOL_IGUAL)
    t = pd.DataFrame({"desenho": nome, "ibge": IBGE[keep], "codigo": COD[keep], "FL_v51": FL0[keep]})
    for k in range(N_RUNS):
        t[f"r{k + 1:02d}"] = FL[k, keep]
    saida.append(t)
    print(f"[{nome}] {N_RUNS} rodadas conferidas com o pert_fl_municipio_substrato; {len(keep):,} de "
          f"{len(CHAVES):,} linhas mudam em alguma rodada")

f = OUTP / "pert_fl_rodadas_med.csv"
pd.concat(saida).round(6).to_csv(f, index=False, encoding="utf-8")
print(f"gravado {f} ({f.stat().st_size / 1e6:.1f} MB)\nFIM")
