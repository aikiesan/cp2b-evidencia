#!/usr/bin/env python3
"""Etapa 5 — validação, sensibilidade e resultados de planejamento do FL espacial.

Variantes (CHECKPOINT 2, 24/09/2026): B = co-digestão com alocação (principal); A = co-digestão por cobertura
(limite superior); C = monodigestão por cobertura; D = monodigestão com alocação (limite inferior).
Palha de cana: só nas usinas (FL calibrado em 03b); o modo "palha em qualquer hub" é reportado lado a lado.

1. FL_yaml × FL_espacial (A, B, C, D) e prévia do efeito no N4; comparação dos dois modos de palha.
2. Taxa de acerto: % das plantas operantes a ≤ 2 km de um hub viável (a monodigestão é o teste que discrimina).
3. Sensibilidade (med): FL × r2 por classe e FL × Q_min, sem a palha (que vai às usinas); raios da palha.
4. Robustez da rede: grafo completo × sem track/service.
5. Planejamento: curva MCLP da variante B com a palha nas usinas (hubs × fração coberta, 50/80/95%).
6. Mapas.
"""
from __future__ import annotations

import json
import sys

import matplotlib
import numpy as np
import pandas as pd
import yaml
from scipy.spatial import cKDTree

import fl_comum as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402

log = C.logger("05_validacao_sensibilidade")
CF = C.CFG
RAIOS, QMIN = CF["raios_km"], CF["q_min"]
SEN = CF["sensibilidade"]
CLASSES = list(CF["classes_raio"])
ESP = CF["espacializacao"]
SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
SUBS_GRADE = [s for s in SUBS if s != "PALHA"]           # a palha vai às usinas e não entra na viabilidade
COLS = [f"{s}__{sc}" for s in SUBS for sc in C.SC]
cls_of = {s: C.classes_de(s) for s in SUBS}
VAR = {"A": "FL_codigestao", "B": "FL_codig_alocado", "C": "FL_mono", "D": "FL_mono_alocado"}
NOME = {"A": "co-digestão, cobertura", "B": "co-digestão, com alocação", "C": "monodigestão, cobertura",
        "D": "monodigestão, com alocação"}
assert CF["palha"]["modo"] == "usinas", "este script assume a palha nas usinas como modo principal"

# ---------------------------------------------------------------------------
# 0. Dados
# ---------------------------------------------------------------------------
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
ZP = np.load(C.CACHE / "palha_usinas.npz")
D_PALHA = pd.Series(ZP["d"], index=ZP["loc"]).reindex(LOC["loc"]).to_numpy()
R_PALHA = {sc: tuple(float(x) for x in ZP[f"r_{sc}"]) for sc in C.SC}


def estado(sufixo=""):
    e = pd.read_csv(C.OUT / f"fl_estado_substrato{sufixo}.csv")
    a = pd.read_csv(C.OUT / f"fl_estado_alocado{sufixo}.csv").drop(columns="oferta_L3_m3dia")
    return e.merge(a, on=["codigo", "cenario"], how="left")


EST = estado()
EST_QH = estado("_palha_qualquer_hub")
MUNFL = pd.read_csv(C.OUT / "fl_municipio_substrato.csv")
ROT = C.Roteador(G, HUBS, LOC)
hub_xy = np.where((HUBS.origem == "novo").to_numpy()[:, None], np.c_[G["x"][HUBS.node], G["y"][HUBS.node]],
                  HUBS[["x", "y"]].to_numpy())
viav_co = {sc: BAC[f"co__{sc}"] >= QMIN[sc] for sc in C.SC}             # principal: sem a palha
viav_mono = {(s, sc): BAC[f"mono__{s}__{sc}"] >= QMIN[sc] for s in SUBS for sc in C.SC}
mun = C.municipios()
li_rows = pd.Series(np.arange(NL), index=LOC["loc"]).loc[OFw["loc"]].to_numpy()
VMED = {s: OFw[f"{s}__med"].to_numpy() for s in SUBS}

# ---------------------------------------------------------------------------
# 1. FL_yaml × FL_espacial, prévia do N4 e comparação dos modos de palha
# ---------------------------------------------------------------------------
with C.etapa(log, "FL_yaml × FL_espacial (A, B, C, D) e modos de palha"):
    sys.path.insert(0, str(C.caminho("metodo")))
    import cp2b_params as P  # noqa: E402

    Y = yaml.safe_load(open(C.caminho("feedstocks_yaml"), encoding="utf-8"))["feedstocks"]
    linhas = []
    for s in P.SUBSTRATOS:
        code = s.get("FL_ref") or (s["yaml"] if s["FL"] in ("yaml", "espacial") else s["FL"])
        fl = Y[code]["fde"]["components"]["fl"]
        linhas.append(dict(codigo=s["codigo"], fluxo=s["fluxo"], yaml_fl=code, FL_yaml_min=fl["min"],
                           FL_yaml_med=fl["medio"], FL_yaml_max=fl["max"], **{f"FS_{k}": v for k, v in s["FS"].items()}))
    CMP = pd.DataFrame(linhas)
    for tab, suf in [(EST, ""), (EST_QH, "_palhaQH")]:
        for k, col in VAR.items():
            p = tab.pivot_table(index="codigo", columns="cenario", values=col)
            for sc in C.SC:
                CMP[f"{k}{suf}_{sc}"] = CMP.codigo.map(p[sc])
    p = EST.pivot_table(index="codigo", columns="cenario", values="FL_codig_sem_lignocel")
    for sc in C.SC:
        CMP[f"sem_lignocel_{sc}"] = CMP.codigo.map(p[sc]) if sc in p else np.nan
    of = EST.pivot_table(index="codigo", columns="cenario", values="oferta_L3_m3dia")
    n4 = []
    for sc in C.SC:
        CMP[f"N3_{sc}_m3dia"] = CMP.codigo.map(of[sc])
        base = CMP[f"N3_{sc}_m3dia"] * CMP[f"FS_{sc}"]
        CMP[f"N4_v4_{sc}_m3dia"] = base * CMP[f"FL_yaml_{sc}"]
        r = {"cenario": sc, "N4_v4": CMP[f"N4_v4_{sc}_m3dia"].sum()}
        for k in VAR:
            for suf in ["", "_palhaQH"]:
                CMP[f"N4_{k}{suf}_{sc}_m3dia"] = base * CMP[f"{k}{suf}_{sc}"]
                r[f"N4_{k}{suf}"] = CMP[f"N4_{k}{suf}_{sc}_m3dia"].sum()
        n4.append(r)
    CMP.to_csv(C.OUT / "comparacao_FL_yaml_espacial.csv", index=False, encoding="utf-8-sig")
    N4 = pd.DataFrame(n4).set_index("cenario") / 1e6
    N4.round(3).to_csv(C.OUT / "previa_N4_variantes_M_m3dia.csv", encoding="utf-8-sig")
    t = CMP.set_index("codigo")[["FL_yaml_med"] + [f"{k}_{sc}" for k in VAR for sc in C.SC]]
    log.info("\n" + t.round(3).to_string())
    q = CMP.set_index("codigo")[[f"{k}{suf}_med" for k in VAR for suf in ["", "_palhaQH"]]]
    log.info("  med — palha nas usinas × palha em qualquer hub (QH):\n" + q.round(3).to_string())
    log.info("  N4 (M Nm³ CH4/dia, sem BOV_PASTO_MISTO):\n" + N4.round(2).to_string())

# ---------------------------------------------------------------------------
# 2. Taxa de acerto das plantas operantes
# ---------------------------------------------------------------------------
GRUPO_MONO = {"pecuaria": ["AVES_CORTE", "AVES_POSTURA", "SUINOS", "BOV_LEITE", "BOV_CONFINADO"],
              "usina": ["VINHACA", "TORTA_FILTRO", "BAGACO"], "ete": ["LODO_ETE"], "aterro": ["RSU_ORGANICO"]}
with C.etapa(log, "Taxa de acerto (plantas operantes a ≤ 2 km de hub viável)"):
    PL = pd.read_csv(C.OUT / "plantas_validacao_sp.csv")      # uma linha por planta (03_hubs.py)
    raio = CF["validacao"]["raio_acerto_km"] * 1000
    pxy = PL[["x", "y"]].to_numpy()
    _, PL["hub_proximo"] = cKDTree(hub_xy).query(pxy)

    def acerto(viavel):
        idx = np.flatnonzero(viavel)
        if len(idx) == 0:
            return np.zeros(len(PL), bool)
        d, _ = cKDTree(hub_xy[idx]).query(pxy)
        return d <= raio

    for sc in C.SC:
        PL[f"acerto_co_{sc}"] = acerto(viav_co[sc])
        mono = np.full(len(PL), np.nan)
        for tipo, subs in GRUPO_MONO.items():
            m = (PL.tipo == tipo).to_numpy()
            if m.any():
                mono[m] = acerto(np.any([viav_mono[(s, sc)] for s in subs], axis=0))[m]
        PL[f"acerto_mono_{sc}"] = mono
        PL[f"bacia_co_{sc}"] = BAC[f"co__{sc}"][PL.hub_proximo.to_numpy(int)]
    PL.to_csv(C.OUT / "validacao_plantas.csv", index=False, encoding="utf-8-sig")
    rows = []
    for tipo, g in list(PL.groupby("tipo")) + [("todas (com tipo)", PL[PL.tipo != "sem_tipo"]), ("todas", PL)]:
        r = {"tipo": tipo, "n": len(g)}
        for sc in C.SC:
            r[f"co_{sc}_%"] = 100 * g[f"acerto_co_{sc}"].mean()
            r[f"mono_{sc}_%"] = 100 * g[f"acerto_mono_{sc}"].mean() if g[f"acerto_mono_{sc}"].notna().any() else np.nan
        r["bacia_co_med_mediana"] = g.bacia_co_med.median()
        rows.append(r)
    TA = pd.DataFrame(rows)
    TA.to_csv(C.OUT / "validacao_taxa_acerto.csv", index=False, encoding="utf-8-sig")
    log.info("\n" + TA.round(1).to_string(index=False))
    erros = PL[PL.tipo.isin(GRUPO_MONO) & (PL.acerto_mono_med == 0)]
    log.info("  erros da monodigestão (med):\n" + erros[["fonte", "nome", "municipio", "tipo"]].to_string(index=False))

# ---------------------------------------------------------------------------
# 3. Sensibilidade (cenário med) — sem a palha, que vai às usinas com raio próprio
# ---------------------------------------------------------------------------
with C.etapa(log, "Histogramas → bacias para a sensibilidade"):
    BH = C.Bacias(np.load(C.CACHE / "hist_F.npy", mmap_mode="r"), np.load(C.CACHE / "hist_D.npy", mmap_mode="r"))
    BMED = {s: BAC[f"mono__{s}__med"] for s in SUBS}


def fl_estado(d, subs, radii):
    """FL estadual ponderado pela oferta med para um conjunto de substratos; radii: s → (r1, r2)."""
    num = den = 0.0
    for s in subs:
        v = VMED[s]
        num += (v * C.peso_w(d[s][li_rows] if isinstance(d, dict) else d[li_rows], *radii[s])).sum()
        den += v.sum()
    return num / den if den > 0 else np.nan


with C.etapa(log, "Sensibilidade ao raio r2 (5–60 km), por classe (sem a palha)"):
    rows = []
    for c in CLASSES:
        rat = RAIOS["med"][c][0] / RAIOS["med"][c][1]
        subs_c = [s for s in SUBS_GRADE if cls_of[s] == c]
        for r2 in SEN["r2_km"]:
            r1 = int(np.clip(np.floor(r2 * rat + 0.5), 1, r2 - 1))      # arredonda meios para cima
            radii = {s: ((r1, r2) if cls_of[s] == c else tuple(RAIOS["med"][cls_of[s]])) for s in SUBS_GRADE}
            bs = {s: (BH.col(COLS.index(f"{s}__med"), r1, r2) if cls_of[s] == c else BMED[s]) for s in SUBS_GRADE}
            lim = max(r[1] for r in radii.values())
            viav = sum(bs.values()) >= QMIN["med"]
            d_co = ROT.dist(viav, lim)
            d_mo = {s: ROT.dist(bs[s] >= QMIN["med"], r2) for s in subs_c}
            rows.append(dict(classe=c, r1_km=r1, r2_km=r2, hubs_viaveis_co=int(viav.sum()),
                             FL_co=fl_estado(d_co, subs_c, radii), FL_mono=fl_estado(d_mo, subs_c, radii),
                             FL_co_todos_sem_palha=fl_estado(d_co, SUBS_GRADE, radii)))
    SR = pd.DataFrame(rows)
    SR.to_csv(C.OUT / "sensibilidade_r2.csv", index=False, encoding="utf-8-sig")
    log.info("\n" + SR.round(3).to_string(index=False))

with C.etapa(log, "Sensibilidade ao limiar Q_min (250–10.000 Nm³ CH4/dia, sem a palha)"):
    radii = {s: tuple(RAIOS["med"][cls_of[s]]) for s in SUBS_GRADE}
    lim = max(r[1] for r in RAIOS["med"].values())
    rows = []
    for q in SEN["q_min"]:
        viav = BAC["co__med"] >= q
        d_co = ROT.dist(viav, lim)
        d_mo = {s: ROT.dist(BMED[s] >= q, radii[s][1]) for s in SUBS_GRADE}
        r = dict(q_min=q, hubs_viaveis_co=int(viav.sum()), FL_co_sem_palha=fl_estado(d_co, SUBS_GRADE, radii),
                 FL_mono_sem_palha=fl_estado(d_mo, SUBS_GRADE, radii))
        for c in CLASSES:
            subs_c = [s for s in SUBS_GRADE if cls_of[s] == c]
            r[f"FL_co_{c}"] = fl_estado(d_co, subs_c, radii)
            r[f"FL_mono_{c}"] = fl_estado(d_mo, subs_c, radii)
        rows.append(r)
    SQ = pd.DataFrame(rows)
    SQ.to_csv(C.OUT / "sensibilidade_qmin.csv", index=False, encoding="utf-8-sig")
    log.info("\n" + SQ.round(3).to_string(index=False))

with C.etapa(log, "Sensibilidade dos raios da palha (usinas)"):
    tab = pd.read_csv(C.OUT / "palha_usinas_calibracao.csv", nrows=6).set_index("percentil").rede_km
    opcoes = {f"{a}/{b}": (tab[a], tab[b]) for a, b in [("P25", "P75"), ("P50", "P90"), ("P75", "P95"),
                                                         ("P90", "P99"), ("P50", "P99")]}
    opcoes |= {f"sólidos secos {sc} ({r[0]}/{r[1]} km)": tuple(r) for sc, r in
               ((sc, RAIOS[sc]["solidos_secos"]) for sc in C.SC)}
    v = VMED["PALHA"]
    SP_ = pd.DataFrame([{"raios": k, "r1_km": r1, "r2_km": r2,
                         "FL_palha_med": float((v * C.peso_w(D_PALHA[li_rows], r1, r2)).sum() / v.sum())}
                        for k, (r1, r2) in opcoes.items()])
    SP_.to_csv(C.OUT / "sensibilidade_palha_usinas.csv", index=False, encoding="utf-8-sig")
    log.info("\n" + SP_.round(3).to_string(index=False))

with C.etapa(log, "Figuras de sensibilidade"):
    cores = {"liquidos": "#1f77b4", "solidos_umidos": "#2ca02c", "solidos_secos": "#d62728"}
    rot = {"liquidos": "líquidos", "solidos_umidos": "sólidos úmidos", "solidos_secos": "sólidos secos (sem palha)"}
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), dpi=150, sharey=True)
    for c in CLASSES:
        g = SR[SR.classe == c]
        ax[0].plot(g.r2_km, g.FL_co, "-o", color=cores[c], ms=3, label=f"{rot[c]} — co-digestão")
        ax[0].plot(g.r2_km, g.FL_mono, "--s", color=cores[c], ms=3, label=f"{rot[c]} — mono")
        ax[0].axvline(RAIOS["med"][c][1], color=cores[c], lw=0.6, ls=":")
        ax[1].plot(SQ.q_min, SQ[f"FL_co_{c}"], "-o", color=cores[c], ms=3, label=f"{rot[c]} — co-digestão")
        ax[1].plot(SQ.q_min, SQ[f"FL_mono_{c}"], "--s", color=cores[c], ms=3, label=f"{rot[c]} — mono")
    ax[1].axvline(QMIN["med"], color="k", lw=0.6, ls=":")
    ax[1].set_xscale("log")
    ax[0].set_xlabel("r2 da classe (km); r1 = r2 × (r1/r2 do cenário med); pontilhado = r2 med")
    ax[1].set_xlabel("Q_min (Nm³ CH4/dia, escala log); pontilhado = Q_min med")
    ax[0].set_ylabel("FL estadual, cobertura (ponderado pela oferta N3 med)")
    ax[0].set_title("FL × raio de captação (palha nas usinas, fora da curva)")
    ax[1].set_title("FL × limiar de viabilidade do hub")
    for a in ax:
        a.grid(alpha=0.3)
        a.set_ylim(0, 1.02)
    ax[1].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(C.FIG / "sensibilidade_raio_qmin.png")
    plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Robustez da rede (sem track/service) — modo principal da palha nos dois grafos
# ---------------------------------------------------------------------------
f_st = C.OUT / "fl_estado_substrato_sem_track.csv"
if f_st.exists():
    with C.etapa(log, "Robustez: grafo completo × sem track/service"):
        a = EST.set_index(["codigo", "cenario"])[["FL_codigestao", "FL_mono"]]
        b = pd.read_csv(f_st).set_index(["codigo", "cenario"])[["FL_codigestao", "FL_mono"]]
        RB = a.join(b, rsuffix="_sem_track")
        RB["dif_co"] = RB.FL_codigestao_sem_track - RB.FL_codigestao
        RB["dif_mono"] = RB.FL_mono_sem_track - RB.FL_mono
        m1 = MUNFL.set_index(["ibge", "codigo", "cenario"])[["FL_codigestao", "FL_mono"]]
        m2 = pd.read_csv(C.OUT / "fl_municipio_substrato_sem_track.csv").set_index(["ibge", "codigo", "cenario"])[
            ["FL_codigestao", "FL_mono"]]
        dm = (m2 - m1).abs()
        RB.round(4).to_csv(C.OUT / "robustez_rede.csv", encoding="utf-8-sig")
        log.info("\n" + RB.round(3).to_string())
        log.info(f"  máx |ΔFL| estadual: co {RB.dif_co.abs().max():.4f}, mono {RB.dif_mono.abs().max():.4f}; "
                 f"|ΔFL| municipal P95: co {dm.FL_codigestao.quantile(.95):.4f}, mono {dm.FL_mono.quantile(.95):.4f}")
else:
    log.info("Robustez da rede: aguardando 04_bacias_fl.py sem_track")

# ---------------------------------------------------------------------------
# 5. Planejamento: curva MCLP da variante B com a palha nas usinas (med)
#    A palha é coberta pelas usinas (FL calibrado, constante); a MCLP gulosa escolhe hubs (existentes + grade de
#    4 km, viáveis sem a palha) para cobrir o resto do N3. Duas bases: N3 total e N3 sem palha.
# ---------------------------------------------------------------------------
with C.etapa(log, "MCLP da variante B com a palha nas usinas (med)"):
    Z = np.load(C.CACHE / "pares_alocacao.npz")          # pares hub–local ordenados por hub (04b_alocacao.py)
    R_M = 1000 * max(r[1] for sc in C.SC for r in RAIOS[sc].values())
    assert "assinatura" in Z.files and json.loads(str(Z["assinatura"])) == dict(
        nh=NH, nl=NL, r_m=R_M, nos=C.assinatura_nos(HUBS, LOC)), "pares_alocacao.npz não confere: rode 04b_alocacao.py"
    h, li, d = Z["h"].astype(np.int64), Z["l"].astype(np.int64), Z["d"].astype(float)
    m = viav_co["med"][h]
    h, li, d = h[m], li[m], d[m]
    Wc = np.stack([C.peso_w(d, *RAIOS["med"][c]) for c in CLASSES], axis=1)
    V = np.stack([S[:, [COLS.index(f"{s}__med") for s in SUBS_GRADE if cls_of[s] == c]].sum(axis=1)
                  for c in CLASSES], axis=1)
    sel, curva, _ = C.cobertura_gulosa(h, li, Wc, V, meta=1.0)
    v_sp, v_p = V.sum(), VMED["PALHA"].sum()
    cob_palha = float((VMED["PALHA"] * C.peso_w(D_PALHA[li_rows], *R_PALHA["med"])).sum())
    tot = pd.Series(curva * v_sp + cob_palha) / (v_sp + v_p)
    curva_df = pd.DataFrame({"hubs": np.arange(1, len(curva) + 1), "cobertura_sem_palha": curva,
                             "cobertura_N3_total": tot.to_numpy()})
    curva_df.to_csv(C.OUT / "mclp_curva_B.csv", index=False, encoding="utf-8-sig")

    def n_hubs(c, meta):
        ok = np.flatnonzero(c >= meta)
        return int(ok[0] + 1) if len(ok) else np.nan

    # ponto em que a variante B para: primeiro hub cujo ganho marginal (resíduo acrescentado) fica abaixo de Q_min;
    # a sequência gulosa é a mesma da B (mesmos candidatos, pesos e oferta), então a B é o trecho inicial da curva
    ganho = np.diff(np.r_[0.0, curva]) * v_sp
    abaixo = np.flatnonzero(ganho < QMIN["med"])
    k_b = int(abaixo[0]) if len(abaixo) else len(curva)
    AH_ = pd.read_csv(C.OUT / "alocacao_hubs_codigestao.csv")
    n_b = int(((AH_.modo_palha == "usinas") & (AH_.cenario == "med")).sum())
    MC = pd.DataFrame([{"meta": mt, "hubs_N3_sem_palha": n_hubs(curva, mt),
                        "hubs_N3_total_com_palha_nas_usinas": n_hubs(tot.to_numpy(), mt),
                        "dentro_da_variante_B": bool(n_hubs(tot.to_numpy(), mt) <= k_b) if np.isfinite(
                            n_hubs(tot.to_numpy(), mt)) else False} for mt in SEN["mclp_metas"]])
    MC["cobertura_max_sem_palha"] = curva[-1]
    MC["cobertura_max_N3_total"] = tot.iloc[-1]
    MC["palha_coberta_pelas_usinas_%N3"] = 100 * cob_palha / (v_sp + v_p)
    MC["B_hubs"] = k_b
    MC["B_cobertura_sem_palha"] = curva[k_b - 1] if k_b else 0.0
    MC["B_cobertura_N3_total"] = tot.iloc[k_b - 1] if k_b else cob_palha / (v_sp + v_p)
    assert k_b == n_b, f"parada da B na curva ({k_b}) ≠ hubs selecionados no 04b ({n_b})"
    MC.to_csv(C.OUT / "mclp.csv", index=False, encoding="utf-8-sig")
    HUBS.iloc[sel][["hub_id", "tipo", "ref", "x", "y"]].assign(ordem=np.arange(1, len(sel) + 1),
                                                               cobertura_sem_palha=curva).to_csv(
        C.OUT / "mclp_hubs_selecionados.csv", index=False, encoding="utf-8-sig")
    log.info(f"  palha coberta pelas usinas: {100 * cob_palha / (v_sp + v_p):.1f}% do N3 med; candidatos viáveis "
             f"{len(np.unique(h)):,}\n" + MC.round(4).to_string(index=False))
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    ax.plot(curva_df.hubs, curva_df.cobertura_sem_palha, color="#1f77b4", label="N3 sem palha")
    ax.plot(curva_df.hubs, curva_df.cobertura_N3_total, color="#d62728", label="N3 total (palha nas usinas)")
    for mt in SEN["mclp_metas"]:
        ax.axhline(mt, color="#999999", lw=0.6, ls=":")
    ax.axvline(k_b, color="k", lw=0.8, ls="--")
    ax.text(k_b, 0.05, f" variante B para aqui\n ({k_b} hubs; ganho < Q_min)", fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("número de hubs (ordem gulosa; existentes + grade de 4 km, viáveis sem a palha)")
    ax.set_ylabel("fração coberta (Σ oferta × w)")
    ax.set_title("Variante B, cenário med — curva de cobertura (MCLP gulosa)")
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(C.FIG / "mclp_curva_B.png")
    plt.close(fig)

# ---------------------------------------------------------------------------
# 6. Mapas
# ---------------------------------------------------------------------------
with C.etapa(log, "Mapas de FL e de hubs"):
    al = pd.read_csv(C.OUT / "fl_municipio_alocado.csv")
    al = al[al.cenario == "med"]
    mf = MUNFL[MUNFL.cenario == "med"]
    ag = pd.DataFrame({"of": mf.groupby("ibge").oferta_L3_m3dia.sum(),
                       "A": mf.groupby("ibge").oferta_coberta_m3dia.sum(),
                       "C": mf.groupby("ibge").oferta_coberta_mono_m3dia.sum(),
                       "B": (al.oferta_L3_m3dia * al.FL_codig_alocado).groupby(al.ibge).sum(),
                       "D": (al.oferta_L3_m3dia * al.FL_mono_alocado).groupby(al.ibge).sum()})
    gm = mun.merge(ag, left_on="ibge", right_index=True, how="left")
    for k in VAR:
        gm[f"FL_{k}"] = gm[k] / gm["of"]
    fig, ax = plt.subplots(2, 2, figsize=(15, 10.5), dpi=150)
    for a, k in zip(ax.ravel(), ["B", "A", "D", "C"]):
        gm.plot(column=f"FL_{k}", ax=a, cmap="RdYlGn", vmin=0, vmax=1, linewidth=0.1, edgecolor="#777777",
                legend=True, legend_kwds={"shrink": 0.6, "label": "FL municipal (todos os substratos, ponderado pela oferta)"},
                missing_kwds={"color": "#eeeeee"})
        a.set_title(f"{k} — {NOME[k]}{' (principal)' if k == 'B' else ''}; palha nas usinas; med")
        a.set_axis_off()
    fig.tight_layout()
    fig.savefig(C.FIG / "fl_municipal_med.png")
    plt.close(fig)

    g2 = C.grade_sp(CF["grade"]["celula_hub_m"], mun)
    grade = HUBS.origem.eq("novo").to_numpy()
    cid = pd.to_numeric(HUBS.ref.str.replace("grade:", "", regex=False), errors="coerce").to_numpy()
    ext = (g2.x0, g2.x0 + g2.nx * g2.passo, g2.y0, g2.y0 + g2.ny * g2.passo)

    def raster_hubs(valor, mask):
        a = np.full(g2.nx * g2.ny, np.nan)
        k = grade & mask
        a[cid[k].astype(np.int64)] = valor[k]
        return np.flipud(a.reshape(g2.ny, g2.nx))

    AH = pd.read_csv(C.OUT / "alocacao_hubs_codigestao.csv")
    AH = AH[(AH.modo_palha == "usinas") & (AH.cenario == "med")]
    fig, ax = plt.subplots(figsize=(11, 7.4), dpi=150)
    mun.boundary.plot(ax=ax, color="#cccccc", linewidth=0.15)
    ax.imshow(raster_hubs(np.ones(NH), ~viav_co["med"]), extent=ext, cmap="Greys", vmin=0, vmax=3, interpolation="nearest")
    b = BAC["co__med"]
    im = ax.imshow(raster_hubs(b, viav_co["med"]), extent=ext, cmap="viridis", alpha=0.55,
                   norm=LogNorm(vmin=QMIN["med"], vmax=np.nanmax(b)), interpolation="nearest")
    fig.colorbar(im, ax=ax, shrink=0.65, label="bacia co-digestão med sem palha (Nm³ CH4/dia), hubs viáveis (A)")
    xy = hub_xy[AH.hub_id.to_numpy()]
    ax.scatter(xy[:, 0], xy[:, 1], s=7, color="k", label=f"hubs selecionados na variante B ({len(AH)})")
    ok = PL.acerto_mono_med.to_numpy() == 1
    tip = PL.tipo.isin(GRUPO_MONO).to_numpy()
    ax.scatter(PL.x[tip & ok], PL.y[tip & ok], s=22, facecolors="none", edgecolors="#ff7f0e", linewidths=0.9,
               label=f"planta: monodigestão viável a ≤ 2 km ({int((tip & ok).sum())})")
    ax.scatter(PL.x[tip & ~ok], PL.y[tip & ~ok], s=24, marker="x", color="#d62728", linewidths=1.0,
               label=f"planta: monodigestão não viável ({int((tip & ~ok).sum())})")
    mun.dissolve().boundary.plot(ax=ax, color="k", linewidth=0.5)
    ax.legend(loc="lower left", fontsize=8)
    ax.set_title("Hubs — cenário med: viáveis em A (cor) e selecionados em B (pontos); cinza = não viável")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(C.FIG / "hubs_viaveis_codigestao_med.png")
    plt.close(fig)

    painel = ["VINHACA", "SUINOS", "BOV_LEITE", "AVES_CORTE", "RSU_ORGANICO", "LODO_ETE"]
    fig, axs = plt.subplots(2, 3, figsize=(16, 8.4), dpi=150)
    for a, s in zip(axs.ravel(), painel):
        mun.boundary.plot(ax=a, color="#dddddd", linewidth=0.1)
        vv = viav_mono[(s, "med")]
        a.imshow(raster_hubs(np.ones(NH), vv), extent=ext, cmap="Blues", vmin=0, vmax=1.2, interpolation="nearest")
        ex = vv & ~grade
        a.scatter(hub_xy[ex, 0], hub_xy[ex, 1], s=4, color="#d62728")
        fl = EST[(EST.codigo == s) & (EST.cenario == "med")].FL_mono.iloc[0]
        a.set_title(f"{s}: {int(vv.sum()):,} hubs viáveis em mono (FL C med = {fl:.2f})", fontsize=9)
        mun.dissolve().boundary.plot(ax=a, color="k", linewidth=0.4)
        a.set_axis_off()
    fig.suptitle("Monodigestão, cenário med: hubs viáveis por substrato (azul = grade de 2 km; vermelho = hub existente)")
    fig.tight_layout()
    fig.savefig(C.FIG / "hubs_viaveis_mono_med.png")
    plt.close(fig)

    t = CMP.set_index("codigo").loc[SUBS]
    fig, axs = plt.subplots(2, 1, figsize=(12, 8.6), dpi=150, sharex=True)
    x = np.arange(len(t))
    for ax, fam, nome in [(axs[0], ["A", "B"], "co-digestão"), (axs[1], ["C", "D"], "monodigestão")]:
        series = [("FL_yaml", "FL yaml (v4)", "#7f7f7f"), (fam[0], f"{fam[0]} — {NOME[fam[0]]}", "#2ca02c"),
                  (fam[1], f"{fam[1]} — {NOME[fam[1]]}", "#1f77b4")]
        for i, (col, lab, cor) in enumerate(series):
            med = t[f"{col}_med"].to_numpy()
            err = np.vstack([med - t[f"{col}_min"].to_numpy(), t[f"{col}_max"].to_numpy() - med])
            ax.bar(x + (i - 1) * 0.27, med, 0.27, yerr=err, capsize=2, color=cor, label=lab, error_kw={"lw": 0.7})
        ax.set_ylabel("FL (barra = med; traço = min–max)")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(axis="y", alpha=0.3)
        ax.set_title(f"FL por substrato — {nome}: yaml (v4) × espacial (palha nas usinas em todas as variantes)")
    axs[1].set_xticks(x, t.index, rotation=45, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(C.FIG / "fl_yaml_vs_espacial.png")
    plt.close(fig)
log.info("Etapa 5 concluída.")
