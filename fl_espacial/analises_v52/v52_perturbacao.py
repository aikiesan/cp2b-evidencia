"""Perturbação da oferta (v5.2): quanto o FL municipal e a rede de hubs da variante B mudam com ruído no N3.

Roda numa CÓPIA da pasta (`fl_espacial_v52/`), com o cache da v5.1, e grava só em `outputs/v52_perturbacao/`.
Para cada desenho de ruído e rodada, multiplica a oferta de cada substrato por um fator lognormal de média 1
(por substrato no estado e/ou por município × substrato, o mesmo nos três cenários) e refaz a alocação gulosa
do `04b` (co-digestão, palha nas usinas). O filtro de candidatos (bacia de cobertura ≥ Q_min) acompanha o ruído:
a bacia do `04` de cada candidato é multiplicada pela razão entre a bacia ruidosa e a original, ambas somadas
sobre os pares do `04b`. A rodada 0 de cada cenário, sem ruído, tem de repetir os hubs e o FL municipal da v5.1;
se não repetir, o script para.

Com o fator igual dentro do município, o FL municipal de um substrato só muda se a rede de hubs mudar.

Retoma do ponto em que parou: cada rodada fica em `runs/` e não é refeita.
Uso: python v52_perturbacao.py [rodadas por desenho, padrão 30]
"""
import sys
import time

import numpy as np
import pandas as pd

import fl_comum as C

assert C.HERE.name == "fl_espacial_v52", f"rodando fora da cópia: {C.HERE}"
N_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
SEED0 = 20261026
# nome, CV por substrato no estado, CV por município × substrato
DESENHOS = [("mun10", 0.0, 0.10), ("mun30", 0.0, 0.30), ("sub20_mun20", 0.20, 0.20)]
TOL_FL = 1e-9

OUTP = C.OUT / "v52_perturbacao"
RUNS = OUTP / "runs"
RUNS.mkdir(parents=True, exist_ok=True)

CF = C.CFG
RAIOS, QMIN = CF["raios_km"], CF["q_min"]
ESP = CF["espacializacao"]
SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
COLS = [f"{s}__{sc}" for s in SUBS for sc in C.SC]
CLASSES = list(CF["classes_raio"])
cls_of = {s: C.classes_de(s) for s in SUBS}
ci = {c: i for i, c in enumerate(CLASSES)}
assert CF["palha"]["modo"] == "usinas", "a variante B da v5.1 tem a palha nas usinas"
SUBS_CO = [s for s in SUBS if s != "PALHA"]


def log(texto):
    print(texto, flush=True)


# mesmo preparo do 04b_alocacao.py (os índices dos pares dependem dele)
HUBS = pd.read_pickle(C.CACHE / "hubs.pkl")
LOC = pd.read_pickle(C.CACHE / "locais_nos.pkl")
OFw = pd.read_pickle(C.CACHE / "oferta_wide.pkl")
for c in COLS:
    if c not in OFw:
        OFw[c] = 0.0
Sloc = OFw.groupby("loc")[COLS].sum()
LOC = LOC.set_index("loc").loc[Sloc.index].reset_index()
NL, NH = len(LOC), len(HUBS)
BAC = np.load(C.CACHE / "bacias.npz")
li_rows = pd.Series(np.arange(NL), index=LOC["loc"]).loc[OFw["loc"]].to_numpy()
with np.load(C.CACHE / "pares_alocacao.npz") as z:
    PH, PL, PD = z["h"], z["l"], z["d"].astype(np.float64)
zp = np.load(C.CACHE / "palha_usinas.npz")
D_PALHA_US = pd.Series(zp["d"], index=zp["loc"]).reindex(LOC["loc"]).to_numpy()
R_PALHA_US = {sc: tuple(float(x) for x in zp[f"r_{sc}"]) for sc in C.SC}

IB = OFw["ibge"].astype(int).to_numpy()
MUN, GI = np.unique(IB, return_inverse=True)
NM, NS = len(MUN), len(SUBS)
VROW = {sc: np.stack([OFw[f"{s}__{sc}"].to_numpy(np.float64) for s in SUBS], axis=1) for sc in C.SC}
log(f"{NL:,} locais, {NH:,} hubs, {len(PH):,} pares, {NM} municípios, {NS} substratos")


def fatores(cv_sub, cv_mun, seed):
    """Fator por município × substrato (NM × NS), lognormal de média 1; produto dos dois níveis."""
    rng = np.random.default_rng(seed)
    f = np.ones((NM, NS))
    for cv, forma in ((cv_sub, (1, NS)), (cv_mun, (NM, NS))):
        if cv > 0:
            s2 = np.log1p(cv ** 2)
            f = f * rng.lognormal(-s2 / 2, np.sqrt(s2), size=forma)
    return f


def oferta_classes(sc, F):
    """Oferta por local e classe de raio, sem a palha de cana (vai às usinas), com o fator aplicado."""
    v = VROW[sc] * F[GI]
    V = np.zeros((NL, len(CLASSES)))
    for j, s in enumerate(SUBS):
        if s in SUBS_CO and v[:, j].any():
            V[:, ci[cls_of[s]]] += np.bincount(li_rows, weights=v[:, j], minlength=NL)
    return V


def bacia_pares(sc, V, lote=5_000_000):
    """Σ oferta × w(d) por candidato, sobre os pares do 04b (em lotes, para caber na memória)."""
    b = np.zeros(NH)
    for a in range(0, len(PH), lote):
        ph, pl, pd_ = PH[a:a + lote], PL[a:a + lote], PD[a:a + lote]
        for c in CLASSES:
            r1, r2 = RAIOS[sc][c]
            k = pd_ < r2 * 1000
            b += np.bincount(ph[k], weights=V[pl[k], ci[c]] * C.peso_w(pd_[k], r1, r2), minlength=NH)
    return b


# chaves (município, substrato) com oferta, por cenário; FL da palha nas usinas não depende da rede
CHAVES, W_PALHA = {}, {}
for sc in C.SC:
    m = VROW[sc] > 0
    gi, sj = np.nonzero(m)
    k = np.unique(GI[gi] * NS + sj)
    CHAVES[sc] = k
    W_PALHA[sc] = C.peso_w(D_PALHA_US[li_rows], *R_PALHA_US[sc])


def fl_municipal(sc, cur, F):
    """FL por (município, substrato) com oferta, FL total por município e FL estadual por substrato."""
    v = VROW[sc] * F[GI]
    w = np.empty_like(v)
    for j, s in enumerate(SUBS):
        w[:, j] = W_PALHA[sc] if s == "PALHA" else cur[li_rows, ci[cls_of[s]]]
    chave = GI[:, None] * NS + np.arange(NS)[None, :]
    vw = np.where(v > 0, v * np.nan_to_num(w), 0.0)        # como o 04b, w só conta onde há oferta
    num = np.bincount(chave.ravel(), weights=vw.ravel(), minlength=NM * NS)
    den = np.bincount(chave.ravel(), weights=v.ravel(), minlength=NM * NS)
    k = CHAVES[sc]
    fl = num[k] / den[k]
    cob_m = num.reshape(NM, NS).sum(axis=1)
    of_m = den.reshape(NM, NS).sum(axis=1)
    den_s = den.reshape(NM, NS).sum(axis=0)
    est = num.reshape(NM, NS).sum(axis=0) / np.where(den_s > 0, den_s, np.nan)
    return fl, cob_m, of_m, est


def rodada(sc, F, pb0):
    V = oferta_classes(sc, F)
    pb = bacia_pares(sc, V)
    bac = BAC[f"co__{sc}"] * np.where(pb0 > 0, pb / np.where(pb0 > 0, pb0, 1.0), 1.0)
    viav = bac >= QMIN[sc]
    k = viav[PH]
    W = np.stack([C.peso_w(PD[k], *RAIOS[sc][c]) for c in CLASSES], axis=1)
    sel, _, cur = C.cobertura_gulosa(PH[k], PL[k], W, V, ganho_min=QMIN[sc])
    return sel, cur, int(viav.sum())


# ---------------------------------------------------------------------------
# 1. Rodada 0 (sem ruído): tem de repetir a v5.1
# ---------------------------------------------------------------------------
A = pd.read_csv(C.OUT / "alocacao_hubs_codigestao.csv")
A = A[A.modo_palha == "usinas"]
FLref = pd.read_csv(C.OUT / "fl_municipio_alocado.csv")
UM = np.ones((NM, NS))
BASE, PB0 = {}, {}
for sc in C.SC:
    t = time.time()
    V0 = oferta_classes(sc, UM)
    PB0[sc] = bacia_pares(sc, V0)
    cand = np.unique(PH)
    b04 = BAC[f"co__{sc}"][cand]
    rel = np.abs(PB0[sc][cand] - b04) / np.maximum(b04, 1.0)
    vira = int(((PB0[sc][cand] >= QMIN[sc]) != (b04 >= QMIN[sc])).sum())
    sel, cur, nv = rodada(sc, UM, PB0[sc])
    ref = A[A.cenario == sc].sort_values("ordem").hub_id.tolist()
    assert sel == ref, f"[{sc}] a alocação refeita não repete a da v5.1 ({len(sel)} × {len(ref)} hubs): parei"
    fl, cob_m, of_m, est = fl_municipal(sc, cur, UM)
    R = FLref[FLref.cenario == sc]
    kref = (R.ibge.astype(int).map(pd.Series(np.arange(NM), index=MUN)).to_numpy() * NS
            + R.codigo.map({s: j for j, s in enumerate(SUBS)}).to_numpy())
    mine = pd.Series(fl, index=CHAVES[sc]).reindex(kref).to_numpy()
    dmax = float(np.nanmax(np.abs(mine - R.FL_codig_alocado.to_numpy())))
    assert len(R) == len(CHAVES[sc]) and dmax < TOL_FL, f"[{sc}] FL municipal ≠ v5.1 (máx |Δ| {dmax:.2e}): parei"
    BASE[sc] = dict(sel=sel, fl=fl, cob_m=cob_m, of_m=of_m, est=est, viav=nv)
    log(f"[{sc}] rodada 0 = v5.1: {len(sel)} hubs, {nv:,} candidatos viáveis, FL municipal máx |Δ| {dmax:.1e}; "
        f"bacia pelos pares × bacia do 04: |Δ| relativo mediano {np.median(rel):.1e}, máx {rel.max():.1e}, "
        f"{vira} candidatos mudariam de lado sem a razão ({time.time() - t:.0f} s)")


# ---------------------------------------------------------------------------
# 2. Rodadas com ruído (retoma o que já está em runs/)
# ---------------------------------------------------------------------------
tarefas = [(d, k, sc) for d in DESENHOS for k in range(1, N_RUNS + 1) for sc in C.SC]
t0, feitas = time.time(), 0
for n, ((nome, cvs, cvm), k, sc) in enumerate(tarefas, 1):
    f = RUNS / f"{nome}_{sc}_{k:03d}.npz"
    if f.exists():
        continue
    seed = SEED0 + 1000 * [d[0] for d in DESENHOS].index(nome) + k
    F = fatores(cvs, cvm, seed)
    sel, cur, nv = rodada(sc, F, PB0[sc])
    fl, cob_m, of_m, est = fl_municipal(sc, cur, F)
    np.savez(f, sel=np.array(sel, dtype=np.int32), fl=fl.astype(np.float32), cob_m=cob_m, of_m=of_m, est=est,
             viav=nv, seed=seed)
    feitas += 1
    el = time.time() - t0
    log(f"{n}/{len(tarefas)} {nome} {sc} rodada {k}: {len(sel)} hubs ({len(BASE[sc]['sel'])} na v5.1), "
        f"{nv:,} viáveis; {el / 60:.1f} min, faltam ~{el / feitas * (len(tarefas) - n) / 60:.0f} min")


# ---------------------------------------------------------------------------
# 3. Agregação
# ---------------------------------------------------------------------------
def postos(x):
    return pd.Series(x).rank(method="average").to_numpy()


def q(a, p):
    return np.quantile(a, p, axis=0)


ex, est_rows, mun_rows, tot_rows, hub_rows, res = [], [], [], [], [], []
for nome, cvs, cvm in DESENHOS:
    for sc in C.SC:
        B = BASE[sc]
        Z = [np.load(RUNS / f"{nome}_{sc}_{k:03d}.npz") for k in range(1, N_RUNS + 1)]
        FL = np.stack([z["fl"].astype(np.float64) for z in Z])
        COB = np.stack([z["cob_m"] for z in Z])
        OFM = np.stack([z["of_m"] for z in Z])
        EST = np.stack([z["est"] for z in Z])
        tem = B["of_m"] > 0
        flm0 = np.where(tem, B["cob_m"] / np.where(tem, B["of_m"], 1), np.nan)
        FLM = COB / np.where(OFM > 0, OFM, np.nan)
        # município zerado = FL 0 em todos os substratos com oferta (como no builder)
        mun_k = CHAVES[sc] // NS
        zero0 = np.bincount(mun_k, weights=(B["fl"] > 0), minlength=NM) == 0
        ZERO = np.stack([np.bincount(mun_k, weights=(fl > 0), minlength=NM) == 0 for fl in FL])
        zero0 &= tem
        ZERO &= tem
        top0 = set(np.argsort(-B["cob_m"])[:50])
        s0 = set(B["sel"])
        for k, z in enumerate(Z, 1):
            s = set(z["sel"].tolist())
            ex.append(dict(desenho=nome, cv_substrato=cvs, cv_municipio=cvm, cenario=sc, rodada=k,
                           semente=int(z["seed"]), candidatos_viaveis=int(z["viav"]), hubs=len(s),
                           hubs_v51=len(s0), hubs_em_comum=len(s & s0), jaccard=len(s & s0) / len(s | s0),
                           municipios_fl_zero=int(ZERO[k - 1].sum()), municipios_fl_zero_v51=int(zero0.sum()),
                           FL_estado=float(COB[k - 1].sum() / OFM[k - 1].sum()),
                           FL_estado_v51=float(B["cob_m"].sum() / B["of_m"].sum()),
                           spearman_cob_mun=float(np.corrcoef(postos(COB[k - 1][tem]), postos(B["cob_m"][tem]))[0, 1]),
                           top50_em_comum=len(top0 & set(np.argsort(-COB[k - 1])[:50]))))
        for j, s in enumerate(SUBS):
            if np.isfinite(B["est"][j]):
                e = EST[:, j]
                est_rows.append(dict(desenho=nome, cenario=sc, codigo=s, FL_v51=B["est"][j], media=e.mean(),
                                     p05=q(e, .05), p95=q(e, .95), dp=e.std(ddof=1)))
        d = FL - B["fl"]
        mx = np.abs(d).max(axis=0)
        for i in np.flatnonzero(mx > 0.01):
            kk = CHAVES[sc][i]
            mun_rows.append(dict(desenho=nome, cenario=sc, ibge=int(MUN[kk // NS]), codigo=SUBS[kk % NS],
                                 FL_v51=B["fl"][i], media=FL[:, i].mean(), p05=q(FL[:, i], .05),
                                 p95=q(FL[:, i], .95), max_abs_d=mx[i], frac_zero=(FL[:, i] == 0).mean(),
                                 frac_d_acima_01=(np.abs(d[:, i]) > 0.1).mean()))
        for i in np.flatnonzero(tem):
            tot_rows.append(dict(desenho=nome, cenario=sc, ibge=int(MUN[i]), FL_v51=flm0[i],
                                 media=np.nanmean(FLM[:, i]), p05=q(FLM[:, i], .05), p95=q(FLM[:, i], .95),
                                 frac_zero=ZERO[:, i].mean(), zero_v51=bool(zero0[i])))
        cont = pd.Series(np.concatenate([z["sel"] for z in Z])).value_counts()
        for h in sorted(set(cont.index) | s0):
            hub_rows.append(dict(desenho=nome, cenario=sc, hub_id=int(h), tipo=HUBS.tipo.iat[int(h)],
                                 na_v51=h in s0, frac_rodadas=cont.get(h, 0) / N_RUNS))
        res.append(dict(desenho=nome, cenario=sc, rodadas=N_RUNS, linhas_mun_substrato=len(CHAVES[sc]),
                        linhas_max_abs_d_acima_001=int((mx > 0.01).sum()),
                        linhas_max_abs_d_acima_01=int((mx > 0.1).sum()),
                        linhas_p95_p05_acima_01=int((q(FL, .95) - q(FL, .05) > 0.1).sum()),
                        hubs_v51_em_todas=int(sum(cont.get(h, 0) == N_RUNS for h in s0)),
                        hubs_v51=len(s0), hubs_fora_v51_alguma_vez=int(sum(h not in s0 for h in cont.index)),
                        municipios_zero_v51=int(zero0.sum()),
                        municipios_zero_min=int(ZERO.sum(axis=1).min()),
                        municipios_zero_max=int(ZERO.sum(axis=1).max()),
                        municipios_zero_alguma_vez=int(ZERO.any(axis=0).sum()),
                        municipios_zero_sempre=int(ZERO.all(axis=0).sum())))

for nome, linhas in (("pert_execucoes", ex), ("pert_fl_estado", est_rows), ("pert_fl_municipio_substrato", mun_rows),
                     ("pert_fl_municipio_total", tot_rows), ("pert_hubs", hub_rows), ("pert_resumo", res)):
    pd.DataFrame(linhas).round(6).to_csv(OUTP / f"{nome}.csv", index=False, encoding="utf-8")
X = pd.DataFrame(ex)
G = X.groupby(["desenho", "cenario"], sort=False).agg(
    hubs_v51=("hubs_v51", "first"), hubs_min=("hubs", "min"), hubs_max=("hubs", "max"),
    jaccard_med=("jaccard", "median"), zero_v51=("municipios_fl_zero_v51", "first"),
    zero_min=("municipios_fl_zero", "min"), zero_max=("municipios_fl_zero", "max"),
    FL_estado_v51=("FL_estado_v51", "first"), FL_estado_p05=("FL_estado", lambda x: x.quantile(.05)),
    FL_estado_p95=("FL_estado", lambda x: x.quantile(.95)), spearman_min=("spearman_cob_mun", "min"),
    top50_min=("top50_em_comum", "min"))
pd.set_option("display.width", 250)
log("\nPor desenho e cenário (rodadas com ruído):\n" + G.round(3).to_string())
log("\n" + pd.DataFrame(res).set_index(["desenho", "cenario"]).to_string())
log(f"\nsaídas em {OUTP} (runs/ fica fora do repositório)\nFIM")
