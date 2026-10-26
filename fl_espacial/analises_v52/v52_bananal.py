"""Bananal (med, B, palha nas usinas): quanto resíduo, pesado por w(d), cabe em volta dos candidatos a hub."""
import numpy as np
import pandas as pd

import fl_comum as C

IBGE, SC = 3504909, "med"
CF = C.CFG
R, Q = CF["raios_km"][SC], CF["q_min"][SC]
ESP = CF["espacializacao"]
SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
COLS = [f"{s}__{x}" for s in SUBS for x in C.SC]
CLS = list(CF["classes_raio"])
cls_of = {s: C.classes_de(s) for s in SUBS}
SUBS_CO = [s for s in SUBS if s != "PALHA"]           # modo usinas: a palha de cana fica fora da codigestão

# mesmo preparo do 04b_alocacao.py (os índices dos pares dependem dele)
HUBS = pd.read_pickle(C.CACHE / "hubs.pkl")
LOC = pd.read_pickle(C.CACHE / "locais_nos.pkl")
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
for c in COLS:
    if c not in OFw:
        OFw[c] = 0.0
Sloc = OFw.groupby("loc")[COLS].sum()
LOC = LOC.set_index("loc").loc[Sloc.index].reset_index()
NL = len(LOC)
BAC = np.load(C.CACHE / "bacias.npz")
with np.load(C.CACHE / "pares_alocacao.npz") as z:
    PH, PL, PD = z["h"], z["l"], z["d"].astype(np.float64)


def por_classe(tab):
    return np.stack([tab[[f"{s}__{SC}" for s in SUBS_CO if cls_of[s] == c]].sum(axis=1).to_numpy()
                     if any(cls_of[s] == c for s in SUBS_CO) else np.zeros(len(tab)) for c in CLS], axis=1)


V = por_classe(Sloc)
VB = por_classe(OFw[OFw.ibge.astype(int) == IBGE].groupby("loc")[COLS].sum().reindex(Sloc.index, fill_value=0.0))


def pesos(mask):
    return np.stack([C.peso_w(PD[mask], *R[c]) for c in CLS], axis=1)


# alocação gulosa do med, como no 04b; confere com a saída da v5.1
viav = BAC[f"co__{SC}"] >= Q
k = viav[PH]
sel, _, cur = C.cobertura_gulosa(PH[k], PL[k], pesos(k), V, ganho_min=Q)
A = pd.read_csv(C.OUT / "alocacao_hubs_codigestao.csv")
ref = A[(A.modo_palha == "usinas") & (A.cenario == SC)].hub_id
assert sorted(sel) == sorted(ref), "a alocação refeita não bate com a da v5.1: parei"
print(f"alocação med refeita: {len(sel)} hubs, igual à v5.1")

ofB = OFw[OFw.ibge.astype(int) == IBGE]
tot = {s: ofB[f"{s}__{SC}"].sum() for s in SUBS if ofB[f"{s}__{SC}"].sum() > 0}
print(f"\nBananal, oferta N3 med (Nm³ CH4/dia): total {sum(tot.values()):,.1f}; na codigestão (sem palha de cana) "
      f"{VB.sum():,.1f}; Q_min {Q:,}")
partes = [f"{c} {VB[:, i].sum():,.1f} (r {R[c][0]}/{R[c][1]} km)" for i, c in enumerate(CLS)]
print("  por classe de raio: " + "; ".join(partes))
locB = np.flatnonzero(VB.sum(axis=1) > 0)
print(f"  pontos de oferta (células de 1 km ou pontos): {len(locB)}")

# candidatos que alcançam (w > 0) alguma oferta de Bananal
mb = np.isin(PL, locB)
alcanca = (pesos(mb) * (VB[PL[mb]] > 0)).sum(axis=1) > 0
cand = np.unique(PH[mb][alcanca])
print(f"\ncandidatos a hub que alcançam oferta de Bananal: {len(cand)}; viáveis pela bacia de cobertura "
      f"(≥ Q_min): {int(viav[cand].sum())}; selecionados: {len(set(cand) & set(sel))}")

mc = np.isin(PH, cand)                                # só os pares dos candidatos (memória)
ph, pl, Wc = PH[mc], PL[mc], pesos(mc)
ganho0 = np.bincount(ph, weights=(V[pl] * Wc).sum(axis=1), minlength=len(HUBS))
ganhoF = np.bincount(ph, weights=(V[pl] * np.maximum(0.0, Wc - cur[pl])).sum(axis=1), minlength=len(HUBS))
so_B = np.bincount(ph, weights=(VB[pl] * Wc).sum(axis=1), minlength=len(HUBS))
dB = pd.Series(PD[mb][alcanca] / 1000).groupby(PH[mb][alcanca]).min()
T = pd.DataFrame({"hub_id": cand, "tipo": HUBS.tipo.to_numpy()[cand], "d_min_km": dB.reindex(cand).to_numpy(),
                  "bacia_cobertura": BAC[f"co__{SC}"][cand], "viavel": viav[cand],
                  "de_bananal_w": so_B[cand], "ganho_sozinho": ganho0[cand], "ganho_no_fim": ganhoF[cand]})
T["fracao_bananal"] = T.de_bananal_w / T.ganho_sozinho.where(T.ganho_sozinho > 0)
T = T.sort_values("ganho_sozinho", ascending=False)
T.round(3).to_csv(C.OUT / "v52_bananal_candidatos.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 200)
print("\nos 12 candidatos com maior bacia (Nm³ CH4/dia pesados por w; 'ganho_no_fim' = o que acrescentariam depois "
      "da seleção, que para quando nenhum passa de Q_min):")
print(T.head(12).round(1).to_string(index=False))
print(f"\nmaior oferta de Bananal pesada por w que um único candidato junta: {T.de_bananal_w.max():,.1f} "
      f"({100 * T.de_bananal_w.max() / VB.sum():.0f} % da oferta de codigestão do município)")
b = T.iloc[0]
lado = "acima" if b.ganho_sozinho >= Q else "abaixo"
print(f"melhor candidato: bacia {b.ganho_sozinho:,.1f} contra Q_min {Q:,} ({lado}); "
      f"a bacia de cobertura do 04 para ele dá {b.bacia_cobertura:,.1f}")
print(f"maior ganho que ainda sobraria a um candidato depois da seleção: {T.ganho_no_fim.max():,.1f} "
      f"(precisa de {Q:,})")
