#!/usr/bin/env python3
"""Etapa 4 — bacias de captação, viabilidade dos hubs e FL espacial.

Uso:  python 04_bacias_fl.py [completo|sem_track]

1. Passada pesada (pandana, contraction hierarchies): para cada hub, todos os nós a ≤ R km por estrada; a oferta
   de cada local (célula de 1 km ou ponto) entra num histograma por faixa de 1 km:
       F[h, j, k] = Σ oferta_j        D[h, j, k] = Σ oferta_j × d_km        (j = substrato × cenário; k = km)
   d = distância na rede + conexão do local + conexão do hub; d = 0 para o resíduo gerado no próprio hub (na fonte).
   Com raios inteiros, a bacia ponderada pelo decaimento linear w(d) sai EXATA dos histogramas:
       Σ oferta·w = Σ_{k<r1} F_k + [r2·Σ_{r1≤k<r2} F_k − Σ_{r1≤k<r2} D_k] / (r2 − r1)
   A passada é retomável (salva progresso a cada 10 lotes).
2. Viabilidade: co-digestão (todos os substratos, cada um no raio da sua classe), co-digestão sem lignocelulósicos
   e monodigestão (cada substrato sozinho); hub viável se bacia ≥ Q_min do cenário.
3. FL: distância de cada local ao hub viável mais próximo (Dijkstra multi-fonte, SciPy); FL = w(d). Como w é
   decrescente, max w entre os hubs viáveis = w(menor d). FL é cobertura: nada é somado duas vezes.
   Palha (modo usinas, decisão do CHECKPOINT 2): fora da viabilidade; FL = w(d até a usina; raios de 03b).

Saídas: cache/hist_{F,D}{suf}.npy, cache/fl_distancias{suf}.npz, cache/bacias{suf}.npz, outputs/hubs_viaveis{suf}.gpkg,
        outputs/fl_{municipio,estado}_substrato[_palha_qualquer_hub]{suf}.csv (modo principal da palha e o outro)
"""
from __future__ import annotations

import json
import os
import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.spatial import cKDTree

import fl_comum as C

VAR = sys.argv[1] if len(sys.argv) > 1 else "completo"
SUF = "" if VAR == "completo" else f"_{VAR}"
LOTES_TESTE = int(os.environ.get("FL_LOTES_TESTE", "0"))     # > 0: só n lotes, arquivos com sufixo _teste
if LOTES_TESTE:
    SUF += "_teste"
log = C.logger(f"04_bacias_fl{SUF}")
CF = C.CFG
RAIOS, QMIN = CF["raios_km"], CF["q_min"]
R2MAX_CEN = max(r[1] for sc in C.SC for r in RAIOS[sc].values())
KMAX = int(max(CF["sensibilidade"]["r2_km"])) if VAR == "completo" else int(R2MAX_CEN)
LOTE = 250

# ---------------------------------------------------------------------------
# 0. Dados
# ---------------------------------------------------------------------------
G = C.carregar_grafo(VAR)
NN = len(G["x"])
HUBS = pd.read_pickle(C.CACHE / "hubs.pkl")
LOC = pd.read_pickle(C.CACHE / "locais_nos.pkl")
if VAR != "completo":   # reassocia hubs e locais aos nós da variante
    t = cKDTree(np.c_[G["x"], G["y"]])
    d, j = t.query(HUBS[["x", "y"]].to_numpy())
    HUBS["node"], HUBS["dist_no_m"] = j.astype(np.int64), d
    HUBS["conn_m"] = np.where(HUBS.origem == "novo", 0.0, d)
    d, j = t.query(LOC[["x", "y"]].to_numpy())
    LOC["node"], LOC["conn_m"] = j.astype(np.int64), d
    del t

ESP = CF["espacializacao"]
SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
COLS = [f"{s}__{sc}" for s in SUBS for sc in C.SC]
J = len(COLS)
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
for c in COLS:
    if c not in OFw:
        OFw[c] = 0.0
Sloc = OFw.groupby("loc")[COLS].sum()
LOC = LOC.set_index("loc").loc[Sloc.index].reset_index()
NL = len(LOC)
S = Sloc.to_numpy(dtype=np.float64)                       # (NL, J) Nm³ CH4/dia
LI = pd.Series(np.arange(NL), index=LOC["loc"])
conn_loc = LOC.conn_m.to_numpy()
conn_hub = HUBS.conn_m.to_numpy()
hub_fonte = LOC.hub_fonte.to_numpy()
NH = len(HUBS)
LIGNO = {"PALHA", "BAGACO", "PALHA_MILHO", "PALHA_SOJA"}   # mesma marcação `lignocel` de cp2b_params.py
cls_of = {s: C.classes_de(s) for s in SUBS}
log.info(f"Variante {VAR}: {NN:,} nós; {NH:,} hubs; {NL:,} locais de oferta; {J} colunas (substrato × cenário); "
         f"raio da passada {KMAX} km")


def csr_de(chaves, n):
    ordem = np.argsort(chaves, kind="stable")
    cnt = np.bincount(chaves, minlength=n)
    return ordem, cnt, np.r_[0, np.cumsum(cnt)[:-1]]


def expandir(chaves, ordem, cnt, ptr):
    """Para cada chave (nó), repete a linha por item associado; devolve (índice da linha, item)."""
    c = cnt[chaves]
    rep = np.repeat(np.arange(len(chaves)), c)
    off = np.arange(len(rep)) - np.repeat(np.cumsum(c) - c, c)
    return rep, ordem[np.repeat(ptr[chaves], c) + off]


ORD_L, CNT_L, PTR_L = csr_de(LOC.node.to_numpy(), NN)
ORD_H, CNT_H, PTR_H = csr_de(HUBS.node.to_numpy(), NN)

# ---------------------------------------------------------------------------
# 1. Passada pesada → histogramas
# ---------------------------------------------------------------------------
fF, fD = C.CACHE / f"hist_F{SUF}.npy", C.CACHE / f"hist_D{SUF}.npy"
fP = C.CACHE / f"hist_progresso{SUF}.json"
assinatura = dict(var=VAR, kmax=KMAX, nh=NH, nl=NL, j=J, lote=LOTE, oferta=float(S.sum()),
                  nos=C.assinatura_nos(HUBS, LOC))
src = np.unique(HUBS.node.to_numpy())
NB = int(np.ceil(len(src) / LOTE))
if LOTES_TESTE:
    NB = LOTES_TESTE
prog = json.load(open(fP)) if fP.exists() else {}
deps = [C.CACHE / "hubs.pkl", C.CACHE / "locais_nos.pkl", C.CACHE / "oferta_wide.pkl"]
if fF.exists() and "assinatura" in prog and C.cache_confere(prog["assinatura"], assinatura, fP, deps):
    if prog["assinatura"] != assinatura:          # cache anterior ao hash de nós, mais novo que as dependências
        log.info("  cache de histogramas sem hash de nós, gerado depois dos hubs/locais atuais: aceito e atualizado")
        prog["assinatura"] = assinatura
        json.dump(prog, open(fP, "w"))
    F, D = np.load(fF), np.load(fD)
    feito = prog["lotes"]
    log.info(f"Retomando passada: {feito}/{NB} lotes já feitos")
else:
    F = np.zeros((NH, J, KMAX), dtype=np.float32)
    D = np.zeros((NH, J, KMAX), dtype=np.float32)
    feito = 0
if feito < NB:
    with C.etapa(log, f"Passada pesada: {len(src):,} nós-fonte em {NB} lotes de {LOTE}, raio {KMAX} km"):
        net = C.rede_pandana(G)
        t0 = time.perf_counter()
        for b in range(feito, NB):
            sn = src[b * LOTE:(b + 1) * LOTE]
            df = net.nodes_in_range(sn, KMAX * 1000.0)
            if b == feito:
                log.info(f"  1º lote: {len(df):,} pares nó-nó para {len(sn)} fontes")
            s_ = df["source"].to_numpy(np.int64)
            t_ = df["destination"].to_numpy(np.int64)
            w_ = df["m"].to_numpy(np.float64)            # coluna = nome da impedância (rede_pandana)
            del df
            m = CNT_L[t_] > 0
            s_, t_, w_ = s_[m], t_[m], w_[m]
            r, hub = expandir(s_, ORD_H, CNT_H, PTR_H)
            t_, w_ = t_[r], w_[r]
            r, li = expandir(t_, ORD_L, CNT_L, PTR_L)
            hub, d = hub[r], w_[r] + conn_loc[li] + conn_hub[hub[r]]
            d[hub_fonte[li] == hub] = 0.0
            k = d < KMAX * 1000.0
            hub, li, d = hub[k], li[k], d[k]
            hb, hl = np.unique(hub, return_inverse=True)
            row = hl * KMAX + (d // 1000.0).astype(np.int64)
            shape = (len(hb) * KMAX, NL)
            Fb = csr_matrix((np.ones(len(row)), (row, li)), shape=shape) @ S
            Db = csr_matrix((d / 1000.0, (row, li)), shape=shape) @ S
            F[hb] = Fb.reshape(len(hb), KMAX, J).transpose(0, 2, 1)
            D[hb] = Db.reshape(len(hb), KMAX, J).transpose(0, 2, 1)
            if (b + 1) % 10 == 0 or b + 1 == NB:
                el = time.perf_counter() - t0
                eta = el / (b + 1 - feito) * (NB - b - 1)
                log.info(f"  lote {b + 1}/{NB}  ({el / 60:.1f} min; faltam ~{eta / 60:.0f} min)")
                np.save(fF, F)
                np.save(fD, D)
                json.dump({"assinatura": assinatura, "lotes": b + 1}, open(fP, "w"))
        del net

# ---------------------------------------------------------------------------
# 2. Bacias e viabilidade
#    Dois modos para a palha de cana (config → palha.modo; o outro é gravado lado a lado):
#      usinas       a palha só vai para as usinas (FL calibrado em 03b_palha_usinas.py) e NÃO conta para a
#                   viabilidade dos hubs da grade — decisão do CHECKPOINT 2 (24/09/2026);
#      qualquer_hub a palha entra na bacia de todos os hubs e vai ao hub viável mais próximo (raios de sólidos secos).
# ---------------------------------------------------------------------------
BH = C.Bacias(F, D)
del F, D
MODO = CF["palha"]["modo"]
MODOS = [MODO] + [m for m in ("usinas", "qualquer_hub") if m != MODO]
SUF_MODO = {MODO: "", **{m: f"_palha_{m}" for m in MODOS if m != MODO}}


def raios(s, sc):
    return RAIOS[sc][cls_of[s]]


def subs_viab(modo):
    return [s for s in SUBS if not (modo == "usinas" and s == "PALHA")]


with C.etapa(log, "Bacias por substrato e cenário; viabilidade"):
    BAC = {}
    for s in SUBS:
        for sc in C.SC:
            r1, r2 = raios(s, sc)
            BAC[(s, sc)] = BH.col(COLS.index(f"{s}__{sc}"), r1, r2)
    bac_co = {(m, sc): sum(BAC[(s, sc)] for s in subs_viab(m)) for m in MODOS for sc in C.SC}
    bac_sl = {sc: sum(BAC[(s, sc)] for s in SUBS if s not in LIGNO) for sc in C.SC}
    viav_co = {k: v >= QMIN[k[1]] for k, v in bac_co.items()}
    viav_sl = {sc: bac_sl[sc] >= QMIN[sc] for sc in C.SC}
    viav_mono = {(s, sc): BAC[(s, sc)] >= QMIN[sc] for s in SUBS for sc in C.SC}
    np.savez_compressed(C.CACHE / f"bacias{SUF}.npz",
                        **{f"co__{sc}": bac_co[(MODO, sc)] for sc in C.SC},
                        **{f"co{SUF_MODO[m]}__{sc}": bac_co[(m, sc)] for m in MODOS[1:] for sc in C.SC},
                        **{f"sl__{sc}": bac_sl[sc] for sc in C.SC},
                        **{f"mono__{s}__{sc}": BAC[(s, sc)] for s in SUBS for sc in C.SC})
    for sc in C.SC:
        log.info(f"  [{sc}] Q_min {QMIN[sc]:,}: viáveis co-digestão " +
                 "; ".join(f"palha {m}: {int(viav_co[(m, sc)].sum()):,} ({100 * viav_co[(m, sc)].mean():.1f}%)"
                           for m in MODOS) +
                 f"; sem lignocel. {int(viav_sl[sc].sum()):,}; mono (nº de hubs): "
                 + ", ".join(f"{s} {int(viav_mono[(s, sc)].sum()):,}" for s in SUBS))

# ---------------------------------------------------------------------------
# 3. Distância ao hub viável mais próximo (Dijkstra multi-fonte) e FL
# ---------------------------------------------------------------------------
dist_locais = C.Roteador(G, HUBS, LOC).dist
# distâncias da palha na rede desta variante; raios SEMPRE os calibrados no grafo completo (senão a robustez de
# rede ficaria anulada por construção: raios recalibrados na própria distribuição deixam o FL invariante)
zp = np.load(C.CACHE / f"palha_usinas{SUF.replace('_teste', '')}.npz")
D_PALHA_US = pd.Series(zp["d"], index=zp["loc"]).reindex(LOC["loc"]).to_numpy()   # NaN = local sem palha
zr = np.load(C.CACHE / "palha_usinas.npz")
R_PALHA_US = {sc: tuple(float(x) for x in zr[f"r_{sc}"]) for sc in C.SC}
log.info("Palha nas usinas — raios (km): " + "; ".join(f"{sc} {r[0]:.1f}/{r[1]:.1f}" for sc, r in R_PALHA_US.items()))


def fl_de(d, s, sc):
    r1, r2 = raios(s, sc)
    return C.peso_w(d, r1, r2)


DIST = {}
with C.etapa(log, "Dijkstra multi-fonte: co-digestão (dois modos de palha), sem lignocel. e monodigestão"):
    for sc in C.SC:
        lim = max(r[1] for r in RAIOS[sc].values())
        for m in MODOS:
            DIST[f"co{SUF_MODO[m]}__{sc}"] = dist_locais(viav_co[(m, sc)], lim)
        DIST[f"sl__{sc}"] = dist_locais(viav_sl[sc], lim)
        for s in SUBS:
            DIST[f"mono__{s}__{sc}"] = dist_locais(viav_mono[(s, sc)], raios(s, sc)[1])
    np.savez_compressed(C.CACHE / f"fl_distancias{SUF}.npz", loc=LOC["loc"].to_numpy(), palha_usinas=D_PALHA_US,
                        **DIST)

# ---------------------------------------------------------------------------
# 4. FL municipal e estadual (um conjunto de arquivos por modo de palha)
# ---------------------------------------------------------------------------
mun = C.municipios()[["ibge", "municipio"]]
li_rows = LI.loc[OFw["loc"]].to_numpy()


def fl_modo(modo):
    recs = []
    for s in SUBS:
        for sc in C.SC:
            v = OFw[f"{s}__{sc}"].to_numpy()
            m = v > 0
            if not m.any():
                continue
            li, vv, ib = li_rows[m], v[m], OFw["ibge"].to_numpy()[m]
            if modo == "usinas" and s == "PALHA":        # mesma regra em todas as variantes
                fl_co = fl_mo = C.peso_w(D_PALHA_US[li], *R_PALHA_US[sc])
            else:
                fl_co = fl_de(DIST[f"co{SUF_MODO[modo]}__{sc}"][li], s, sc)
                fl_mo = fl_de(DIST[f"mono__{s}__{sc}"][li], s, sc)
            fl_sl = fl_de(DIST[f"sl__{sc}"][li], s, sc) if s not in LIGNO else np.full(len(li), np.nan)
            recs.append(pd.DataFrame({"ibge": ib, "codigo": s, "cenario": sc, "oferta_L3_m3dia": vv,
                                      "cob_co": vv * fl_co, "cob_mono": vv * fl_mo, "cob_sl": vv * fl_sl}))
    R = pd.concat(recs).groupby(["ibge", "codigo", "cenario"], as_index=False).sum(min_count=1)
    R["FL_codigestao"] = R.cob_co / R.oferta_L3_m3dia
    R["FL_mono"] = R.cob_mono / R.oferta_L3_m3dia
    R["FL_codig_sem_lignocel"] = R.cob_sl / R.oferta_L3_m3dia
    R = R.rename(columns={"cob_co": "oferta_coberta_m3dia", "cob_mono": "oferta_coberta_mono_m3dia"})
    R = R.merge(mun, on="ibge", how="left")
    cols_out = ["ibge", "municipio", "codigo", "cenario", "FL_codigestao", "FL_mono", "oferta_L3_m3dia",
                "oferta_coberta_m3dia", "oferta_coberta_mono_m3dia", "FL_codig_sem_lignocel"]
    R[cols_out].to_csv(C.OUT / f"fl_municipio_substrato{SUF_MODO[modo]}{SUF}.csv", index=False, encoding="utf-8-sig")
    E = (R.groupby(["codigo", "cenario"])[["oferta_L3_m3dia", "oferta_coberta_m3dia", "oferta_coberta_mono_m3dia",
                                           "cob_sl"]].sum(min_count=1)
         .rename(columns={"oferta_L3_m3dia": "oferta", "oferta_coberta_m3dia": "co",
                          "oferta_coberta_mono_m3dia": "mono", "cob_sl": "sl"}).reset_index())
    E["FL_codigestao"], E["FL_mono"], E["FL_codig_sem_lignocel"] = E.co / E.oferta, E.mono / E.oferta, E.sl / E.oferta
    E = E.rename(columns={"oferta": "oferta_L3_m3dia"})[["codigo", "cenario", "oferta_L3_m3dia", "FL_codigestao",
                                                         "FL_mono", "FL_codig_sem_lignocel"]]
    E.to_csv(C.OUT / f"fl_estado_substrato{SUF_MODO[modo]}{SUF}.csv", index=False, encoding="utf-8-sig")
    fl_cols = ["FL_codigestao", "FL_mono", "FL_codig_sem_lignocel"]
    fora = int(((R[fl_cols] < -1e-9) | (R[fl_cols] > 1 + 1e-9)).sum().sum())
    P = R.pivot_table(index=["ibge", "codigo"], columns="cenario", values=fl_cols)
    viol = {c: int(((P[(c, "min")] > P[(c, "med")] + 1e-9) | (P[(c, "med")] > P[(c, "max")] + 1e-9)).sum())
            for c in fl_cols}
    log.info(f"  [palha {modo}] FL fora de [0, 1]: {fora}; violações de FL_min ≤ FL_med ≤ FL_max: {viol}")
    Ew = E.pivot_table(index="codigo", columns="cenario", values=["FL_codigestao", "FL_mono"])
    log.info(f"  [palha {modo}] FL estadual (co-digestão | mono):\n" + Ew.round(3).to_string())


with C.etapa(log, "FL por município × substrato × cenário"):
    for m in MODOS:
        fl_modo(m)

# ---------------------------------------------------------------------------
# 5. Hubs viáveis (GeoPackage) — modo principal da palha, com a viabilidade do outro modo ao lado
# ---------------------------------------------------------------------------
with C.etapa(log, "hubs_viaveis.gpkg"):
    out = HUBS[["hub_id", "tipo", "origem", "ref", "nome", "x", "y", "dist_no_m"]].copy()
    for sc in C.SC:
        out[f"bacia_co_{sc}"] = bac_co[(MODO, sc)]
        out[f"viavel_co_{sc}"] = viav_co[(MODO, sc)]
        for m in MODOS[1:]:
            out[f"viavel_co{SUF_MODO[m]}_{sc}"] = viav_co[(m, sc)]
        out[f"bacia_sl_{sc}"] = bac_sl[sc]
        out[f"viavel_sl_{sc}"] = viav_sl[sc]
        out[f"n_mono_viavel_{sc}"] = np.sum([viav_mono[(s, sc)] for s in subs_viab(MODO)], axis=0)
    for s in SUBS:
        out[f"mono_{s}_med"] = BAC[(s, "med")]
    out["biometano_ref_med"] = bac_co[(MODO, "med")] >= CF["biometano_referencia_m3dia"]
    gdf = gpd.GeoDataFrame(out, geometry=gpd.points_from_xy(out.x, out.y), crs=C.CRS)
    f = C.OUT / f"hubs_viaveis{SUF}.gpkg"
    f.unlink(missing_ok=True)
    gdf.to_file(f, layer="hubs", driver="GPKG")
    log.info(f"  hubs co-digestão med ≥ {CF['biometano_referencia_m3dia']:,} Nm³ CH4/dia (referência biometano): "
             f"{int(out.biometano_ref_med.sum()):,}")
log.info("Etapa 4 concluída.")
