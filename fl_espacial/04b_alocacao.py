#!/usr/bin/env python3
"""Etapa 4b — FL com alocação (sem sobreposição de bacias), co-digestão e monodigestão, três cenários.

Na variante de cobertura (04_bacias_fl.py) a viabilidade é testada bacia a bacia: o mesmo resíduo torna viáveis
vários hubs vizinhos. Aqui cada resíduo é contado UMA vez: hubs entram em ordem gulosa (maior resíduo coberto a
mais primeiro) e um hub só entra se o resíduo que ele acrescenta — Σ oferta × aumento de w, já descontado o que
hubs anteriores cobrem — for ≥ Q_min do cenário. FL do local = w obtido.
Candidatos: hubs viáveis (cobertura) entre os existentes + grade de 4 km (subconjunto da grade de 2 km).
Palha (modo usinas, CHECKPOINT 2): fora da alocação; FL = w(d até a usina; raios de 03b_palha_usinas.py).
Robustez: (a) max w(d) só sobre os hubs selecionados, por Dijkstra (coincide por construção); (b) atribuição
exclusiva iterada (cada resíduo só no hub selecionado de maior w; hubs com bacia exclusiva < Q_min saem).

Saídas: cache/pares_alocacao.npz, outputs/fl_{municipio,estado}_alocado[_palha_qualquer_hub].csv,
        outputs/alocacao_hubs_codigestao.csv, outputs/fl_alocado_robustez.csv, outputs/fl_alocado_robustez_poda.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import fl_comum as C

log = C.logger("04b_alocacao")
CF = C.CFG
RAIOS, QMIN = CF["raios_km"], CF["q_min"]
ESP = CF["espacializacao"]
SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
COLS = [f"{s}__{sc}" for s in SUBS for sc in C.SC]
CLASSES = list(CF["classes_raio"])
cls_of = {s: C.classes_de(s) for s in SUBS}
R_M = 1000 * max(r[1] for sc in C.SC for r in RAIOS[sc].values())

G = C.carregar_grafo("completo")
HUBS = pd.read_pickle(C.CACHE / "hubs.pkl")
LOC = pd.read_pickle(C.CACHE / "locais_nos.pkl")
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
for c in COLS:
    if c not in OFw:
        OFw[c] = 0.0
Sloc = OFw.groupby("loc")[COLS].sum()
LOC = LOC.set_index("loc").loc[Sloc.index].reset_index()
S = Sloc.to_numpy()
NL, NH = len(LOC), len(HUBS)
BAC = np.load(C.CACHE / "bacias.npz")
li_rows = pd.Series(np.arange(NL), index=LOC["loc"]).loc[OFw["loc"]].to_numpy()

g2 = C.grade_sp(CF["grade"]["celula_hub_m"])
cid = pd.to_numeric(HUBS.ref.str.replace("grade:", "", regex=False), errors="coerce")
sub = (HUBS.origem == "existente").to_numpy() | (((cid % g2.nx) % 2 == 0) & ((cid // g2.nx) % 2 == 0)).to_numpy()

# ---------------------------------------------------------------------------
# 1. Pares hub–local até o maior r2 dos cenários (subconjunto de candidatos)
# ---------------------------------------------------------------------------
fP = C.CACHE / "pares_alocacao.npz"
assert R_M < np.iinfo(np.uint16).max, "distâncias dos pares são gravadas em uint16 (metros)"
ASSIN = dict(nh=NH, nl=NL, r_m=R_M, nos=C.assinatura_nos(HUBS, LOC))
ok_cache = False
if fP.exists():
    with np.load(fP) as z:
        salva = json.loads(str(z["assinatura"])) if "assinatura" in z.files else {k: v for k, v in ASSIN.items() if k != "nos"}
        deps = [C.CACHE / "hubs.pkl", C.CACHE / "locais_nos.pkl", C.CACHE / "oferta_wide.pkl"]
        if C.cache_confere(salva, ASSIN, fP, deps):
            PH, PL, PD = z["h"], z["l"], z["d"].astype(np.float64)
            ok_cache, legado = True, "assinatura" not in z.files
    if ok_cache:
        log.info(f"Pares lidos do cache: {len(PH):,}")
        if legado:     # cache anterior à assinatura, gerado depois dos hubs/locais atuais: regrava com assinatura
            np.savez(fP, h=PH, l=PL, d=np.round(PD).astype(np.uint16), assinatura=json.dumps(ASSIN))
    else:
        log.info("Cache de pares não confere com os hubs/locais atuais: recalculando")
if not ok_cache:
    with C.etapa(log, f"Pares hub–local a ≤ {R_M / 1000:.0f} km para {int(sub.sum()):,} candidatos"):
        net = C.rede_pandana(G)
        hn = HUBS.node.to_numpy()
        conn_h, conn_l, fonte = HUBS.conn_m.to_numpy(), LOC.conn_m.to_numpy(), LOC.hub_fonte.to_numpy()
        ordL = np.argsort(LOC.node.to_numpy(), kind="stable")
        cntL = np.bincount(LOC.node.to_numpy(), minlength=len(G["x"]))
        ptrL = np.r_[0, np.cumsum(cntL)[:-1]]
        hs = np.flatnonzero(sub)
        partes = []
        for b in range(0, len(hs), 250):
            hb = hs[b:b + 250]
            nodes = np.unique(hn[hb])
            df = net.nodes_in_range(nodes, R_M)
            s_ = df["source"].to_numpy(np.int64)
            t_ = df["destination"].to_numpy(np.int64)
            w_ = df["m"].to_numpy(np.float64)
            m = cntL[t_] > 0
            s_, t_, w_ = s_[m], t_[m], w_[m]
            # nó-fonte → hubs do lote naquele nó (expansão vetorizada)
            kb = np.searchsorted(nodes, hn[hb])
            hb_ord = hb[np.argsort(kb, kind="stable")]
            cntB = np.bincount(kb, minlength=len(nodes))
            ptrB = np.r_[0, np.cumsum(cntB)[:-1]]
            k = np.searchsorted(nodes, s_)
            c = cntB[k]
            rep = np.repeat(np.arange(len(k)), c)
            hub = hb_ord[np.repeat(ptrB[k], c) + (np.arange(len(rep)) - np.repeat(np.cumsum(c) - c, c))]
            t2, w2 = t_[rep], w_[rep]
            c = cntL[t2]
            rep = np.repeat(np.arange(len(t2)), c)
            li = ordL[np.repeat(ptrL[t2], c) + (np.arange(len(rep)) - np.repeat(np.cumsum(c) - c, c))]
            hub = hub[rep]
            d = w2[rep] + conn_l[li] + conn_h[hub]
            d[fonte[li] == hub] = 0.0
            k = d < R_M
            partes.append((hub[k].astype(np.int32), li[k].astype(np.int32), np.round(d[k]).astype(np.uint16)))
        PH = np.concatenate([p[0] for p in partes])
        PL = np.concatenate([p[1] for p in partes])
        PD = np.concatenate([p[2] for p in partes])
        o = np.argsort(PH, kind="stable")
        PH, PL, PD = PH[o], PL[o], PD[o]
        np.savez(fP, h=PH, l=PL, d=PD, assinatura=json.dumps(ASSIN))
        PD = PD.astype(np.float64)
        log.info(f"  {len(PH):,} pares")

# ---------------------------------------------------------------------------
# 2. Alocação gulosa por cenário e modo de palha: co-digestão (3 classes de raio) e monodigestão (cada substrato)
#    Modo "usinas" (principal, CHECKPOINT 2): a palha fica fora da alocação e recebe o FL calibrado em 03b.
# ---------------------------------------------------------------------------
MODO = CF["palha"]["modo"]
MODOS = [MODO] + [m for m in ("usinas", "qualquer_hub") if m != MODO]
SUF_MODO = {MODO: "", **{m: f"_palha_{m}" for m in MODOS if m != MODO}}
zp = np.load(C.CACHE / "palha_usinas.npz")
D_PALHA_US = pd.Series(zp["d"], index=zp["loc"]).reindex(LOC["loc"]).to_numpy()
R_PALHA_US = {sc: tuple(float(x) for x in zp[f"r_{sc}"]) for sc in C.SC}
ci = {c: i for i, c in enumerate(CLASSES)}


def subs_modo(m):
    return [s for s in SUBS if not (m == "usinas" and s == "PALHA")]


cob_co, sel_co, cob_mo, sel_mo, hubs_co = {}, {}, {}, {}, []
with C.etapa(log, "Alocação gulosa (co-digestão × 2 modos de palha, monodigestão; 3 cenários)"):
    for sc in C.SC:
        for m in MODOS:
            viav = BAC[f"co{SUF_MODO[m]}__{sc}"] >= QMIN[sc]
            k = viav[PH]
            W = np.stack([C.peso_w(PD[k], *RAIOS[sc][c]) for c in CLASSES], axis=1)
            V = np.stack([S[:, [COLS.index(f"{s}__{sc}") for s in subs_modo(m) if cls_of[s] == c]].sum(axis=1)
                          if any(cls_of[s] == c for s in subs_modo(m)) else np.zeros(NL) for c in CLASSES], axis=1)
            sel, curva, cur = C.cobertura_gulosa(PH[k], PL[k], W, V, ganho_min=QMIN[sc])
            cob_co[(m, sc)], sel_co[(m, sc)] = cur, sel
            hubs_co.append(pd.DataFrame({"modo_palha": m, "cenario": sc, "ordem": np.arange(1, len(sel) + 1),
                                         "hub_id": sel, "cobertura_acum": curva,
                                         "bacia_sobreposta": BAC[f"co{SUF_MODO[m]}__{sc}"][sel]}))
            log.info(f"  [{sc}] co-digestão, palha {m}: {len(sel):,} hubs; cobertura "
                     f"{100 * (curva[-1] if len(curva) else 0):.1f}% da oferta alocável")
        for s in SUBS:
            j = COLS.index(f"{s}__{sc}")
            Vs = S[:, [j]]
            viav_s = BAC[f"mono__{s}__{sc}"] >= QMIN[sc]
            k = viav_s[PH] & (Vs[PL, 0] > 0)
            Ws = C.peso_w(PD[k], *RAIOS[sc][cls_of[s]])[:, None]
            sel_s, _, cur_s = C.cobertura_gulosa(PH[k], PL[k], Ws, Vs, ganho_min=QMIN[sc])
            cob_mo[(s, sc)], sel_mo[(s, sc)] = cur_s[:, 0], sel_s
        log.info(f"  [{sc}] monodigestão concluída")


def fl_local(m, s, sc, li, variante):
    """FL por local: palha no modo usinas = w(d até a usina); demais = w obtido na alocação."""
    if m == "usinas" and s == "PALHA":
        return C.peso_w(D_PALHA_US[li], *R_PALHA_US[sc])
    return cob_co[(m, sc)][li, ci[cls_of[s]]] if variante == "co" else cob_mo[(s, sc)][li]


# ---------------------------------------------------------------------------
# 3. FL municipal e estadual (um conjunto de arquivos por modo de palha)
# ---------------------------------------------------------------------------
with C.etapa(log, "FL com alocação por município e estado"):
    for m in MODOS:
        recs = []
        for s in SUBS:
            for sc in C.SC:
                v = OFw[f"{s}__{sc}"].to_numpy()
                mk = v > 0
                li = li_rows[mk]
                recs.append(pd.DataFrame({"ibge": OFw["ibge"].to_numpy()[mk], "codigo": s, "cenario": sc,
                                          "oferta_L3_m3dia": v[mk], "cob_co": v[mk] * fl_local(m, s, sc, li, "co"),
                                          "cob_mo": v[mk] * fl_local(m, s, sc, li, "mono")}))
        R = pd.concat(recs).groupby(["ibge", "codigo", "cenario"], as_index=False).sum()
        R["FL_codig_alocado"] = R.cob_co / R.oferta_L3_m3dia
        R["FL_mono_alocado"] = R.cob_mo / R.oferta_L3_m3dia
        R.drop(columns=["cob_co", "cob_mo"]).to_csv(C.OUT / f"fl_municipio_alocado{SUF_MODO[m]}.csv", index=False,
                                                    encoding="utf-8-sig")
        E = R.groupby(["codigo", "cenario"])[["oferta_L3_m3dia", "cob_co", "cob_mo"]].sum()
        E["FL_codig_alocado"], E["FL_mono_alocado"] = E.cob_co / E.oferta_L3_m3dia, E.cob_mo / E.oferta_L3_m3dia
        E = E.drop(columns=["cob_co", "cob_mo"]).reset_index()
        E.to_csv(C.OUT / f"fl_estado_alocado{SUF_MODO[m]}.csv", index=False, encoding="utf-8-sig")
        P = E.pivot_table(index="codigo", columns="cenario", values=["FL_codig_alocado", "FL_mono_alocado"])
        viol = {c: int(((P[(c, "min")] > P[(c, "med")] + 1e-9) | (P[(c, "med")] > P[(c, "max")] + 1e-9)).sum())
                for c in ["FL_codig_alocado", "FL_mono_alocado"]}
        log.info(f"  [palha {m}] substratos com FL_min ≤ FL_med ≤ FL_max violado (estado): {viol}\n"
                 + P.round(3).to_string())
    pd.concat(hubs_co).merge(HUBS[["hub_id", "tipo", "ref", "x", "y"]], on="hub_id").to_csv(
        C.OUT / "alocacao_hubs_codigestao.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 4. Robustez (CHECKPOINT 2): tolerância = |ΔFL| estadual por substrato; acima dela, reportar as duas versões.
#    (a) max w(d) SÓ sobre os hubs selecionados, por Dijkstra independente da contabilidade gulosa, sem refazer a
#        viabilidade. Coincide por construção (o FL alocado já é o max w sobre os selecionados); confirma a conta.
#    (b) atribuição EXCLUSIVA: cada resíduo (local × classe de raio) vai só ao hub selecionado de maior w; hubs cuja
#        bacia exclusiva (Σ oferta × w) fique abaixo de Q_min saem, e a atribuição se repete até estabilizar. Testa se
#        os hubs selecionados continuam com escala quando o resíduo não é compartilhado.
# ---------------------------------------------------------------------------
def poda_exclusiva(sel, W, V, qmin):
    """Devolve (hubs mantidos, w obtido por local e coluna) após a poda iterativa por bacia exclusiva < qmin."""
    manter = np.array(sorted(sel), dtype=np.int64)
    while True:
        if len(manter) == 0:                                     # nenhum hub (ou todos podados): FL = 0
            return manter, np.zeros(V.shape)
        k = np.isin(PH, manter)
        ph, pl, w = PH[k], PL[k], W(k)
        cur = np.zeros(V.shape)
        bacia = np.zeros(NH)
        for c in range(V.shape[1]):
            o = np.lexsort((-w[:, c], pl))                       # por local, maior w primeiro
            prim = np.r_[True, pl[o][1:] != pl[o][:-1]]
            i = o[prim]
            cur[pl[i], c] = w[i, c]
            bacia += np.bincount(ph[i], weights=V[pl[i], c] * w[i, c], minlength=NH)
        fracos = manter[bacia[manter] < qmin]
        if len(fracos) == 0:
            return manter, cur
        manter = np.setdiff1d(manter, fracos)


with C.etapa(log, "Robustez: (a) max w(d) sobre os selecionados (Dijkstra); (b) atribuição exclusiva iterada"):
    ROT = C.Roteador(G, HUBS, LOC)
    tol = CF["variantes"]["tolerancia_robustez_alocacao"]
    rows, poda = [], []
    for m in MODOS:
        for sc in C.SC:
            lim = max(r[1] for r in RAIOS[sc].values())
            viav_sel = np.zeros(NH, bool)
            viav_sel[sel_co[(m, sc)]] = True
            d_co = ROT.dist(viav_sel, lim)
            V = np.stack([S[:, [COLS.index(f"{s}__{sc}") for s in subs_modo(m) if cls_of[s] == c]].sum(axis=1)
                          if any(cls_of[s] == c for s in subs_modo(m)) else np.zeros(NL) for c in CLASSES], axis=1)
            mant, cur_ex = poda_exclusiva(sel_co[(m, sc)],
                                          lambda k: np.stack([C.peso_w(PD[k], *RAIOS[sc][c]) for c in CLASSES], axis=1),
                                          V, QMIN[sc])
            poda.append(dict(modo_palha=m, cenario=sc, variante="co", selecionados=len(sel_co[(m, sc)]),
                             mantidos_exclusivo=len(mant)))
            for s in subs_modo(m):
                v = OFw[f"{s}__{sc}"].to_numpy()
                mk = v > 0
                if not mk.any():
                    continue
                li = li_rows[mk]
                vv = v[mk] / v[mk].sum()
                r1, r2 = RAIOS[sc][cls_of[s]]
                a = (vv * cob_co[(m, sc)][li, ci[cls_of[s]]]).sum()
                b = (vv * C.peso_w(d_co[li], r1, r2)).sum()
                e = (vv * cur_ex[li, ci[cls_of[s]]]).sum()
                vs = np.zeros(NH, bool)
                vs[sel_mo[(s, sc)]] = True
                d_mo = ROT.dist(vs, r2)
                Vs = S[:, [COLS.index(f"{s}__{sc}")]]
                mant_s, cur_s = poda_exclusiva(sel_mo[(s, sc)], lambda k: C.peso_w(PD[k], r1, r2)[:, None], Vs, QMIN[sc])
                am = (vv * cob_mo[(s, sc)][li]).sum()
                bm = (vv * C.peso_w(d_mo[li], r1, r2)).sum()
                em = (vv * cur_s[li, 0]).sum()
                if m == MODO:
                    poda.append(dict(modo_palha=m, cenario=sc, variante=f"mono:{s}", selecionados=len(sel_mo[(s, sc)]),
                                     mantidos_exclusivo=len(mant_s)))
                rows.append(dict(modo_palha=m, codigo=s, cenario=sc,
                                 FL_codig_alocado=a, FL_codig_maxw_sel=b, dif_codig_maxw=b - a,
                                 FL_codig_exclusivo=e, dif_codig_exclusivo=e - a,
                                 FL_mono_alocado=am, FL_mono_maxw_sel=bm, dif_mono_maxw=bm - am,
                                 FL_mono_exclusivo=em, dif_mono_exclusivo=em - am))
    RB = pd.DataFrame(rows)
    RB.to_csv(C.OUT / "fl_alocado_robustez.csv", index=False, encoding="utf-8-sig")
    PO = pd.DataFrame(poda)
    PO.to_csv(C.OUT / "fl_alocado_robustez_poda.csv", index=False, encoding="utf-8-sig")
    dcols = ["dif_codig_maxw", "dif_mono_maxw", "dif_codig_exclusivo", "dif_mono_exclusivo"]
    log.info("  máx |ΔFL| estadual: " + "; ".join(f"{c} {RB[c].abs().max():.4f}" for c in dcols))
    log.info("  poda por bacia exclusiva (co-digestão):\n" + PO[PO.variante == "co"].to_string(index=False))
    big = RB[(RB[dcols].abs() > tol).any(axis=1)]
    log.info(f"  casos com |ΔFL| > {tol}: {len(big)}" + ("" if big.empty else "\n" + big.round(4).to_string(index=False)))
log.info("Etapa 4b concluída.")
