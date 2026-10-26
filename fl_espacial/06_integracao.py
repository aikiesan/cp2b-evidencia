#!/usr/bin/env python3
"""Etapa 6 — integração do FL espacial à cascata (v5) e exportação dos parâmetros para o banco.

Decisões do CHECKPOINT 2 (24/09/2026): variante principal B (co-digestão com alocação); A (co-digestão por
cobertura) = limite superior; D (monodigestão com alocação) = limite inferior; C = sensibilidade. Palha nas usinas
em todas; "B com palha em qualquer hub" sai ao lado para comparação. Banco de produção: nada é aplicado.

1. outputs/fl_v5_{municipio,estado}_substrato.csv — FL consolidado (4 variantes) que a cascata v5 lê.
2. outputs_v5/v5_<variante>_cp2b_*.csv — N4 = N3 × FS × FL por variante, a partir das linhas da v4
   (FS = (FS×FL)_v4 ÷ FL_yaml); idêntico ao que cp2b_cascade.py calcula com FL = "espacial".
3. outputs_v5/v5_reconciliacao_*.csv — N4 v4 × v5 por variante (estado, fluxo, top 20), com e sem lignocelulósicos.
4. outputs/banco/ — triplos fl_* por resíduo (4 variantes), FL municipal, N4 por fluxo, SQL de rascunho (ROLLBACK).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import yaml

import fl_comum as C

log = C.logger("06_integracao")
CF = C.CFG
IN = CF["integracao"]
OUT5 = C.Path(IN["saida_v5"])
OUT5.mkdir(parents=True, exist_ok=True)
BANCO = C.OUT / "banco"
BANCO.mkdir(exist_ok=True)
PFX = IN["prefixo"]
sys.path.insert(0, str(C.caminho("metodo")))
import cp2b_params as P  # noqa: E402

Y = yaml.safe_load(open(C.caminho("feedstocks_yaml"), encoding="utf-8"))["feedstocks"]
G = P.GLOBAIS
VAR_COL = {"codig_alocado": "FL_codig_alocado", "codigestao": "FL_codigestao", "mono": "FL_mono",
           "mono_alocado": "FL_mono_alocado", "codig_alocado_palha_qualquer_hub": "FL_codig_alocado_palhaQH"}
ROTULO = {"codig_alocado": "B", "codigestao": "A", "mono": "C", "mono_alocado": "D",
          "codig_alocado_palha_qualquer_hub": "B (palha em qualquer hub)"}
VP = IN["variante_principal"]
if hasattr(P, "FL_ESPACIAL"):     # cp2b_params.py da v5: a variante da cascata tem de ser a mesma do config
    assert P.FL_ESPACIAL["variante"] == VP, f"cp2b_params.FL_ESPACIAL = {P.FL_ESPACIAL['variante']} ≠ config {VP}"
ordem = [VP] + [v for v in VAR_COL if v != VP]
LIGNO = {"PALHA", "BAGACO", "PALHA_MILHO", "PALHA_SOJA"}

# ---------------------------------------------------------------------------
# 1. Parâmetros de referência (FL do yaml que a v4 usou, FS) e FL consolidado para a cascata v5
# ---------------------------------------------------------------------------
REF = {}
for s in P.SUBSTRATOS:        # funciona com o cp2b_params.py da v4 (FL = chave) e o da v5 (FL = "espacial" + FL_ref)
    code = s.get("FL_ref") or (s["yaml"] if s["FL"] in ("yaml", "espacial") else s["FL"])
    fl = Y[code]["fde"]["components"]["fl"]
    REF[s["codigo"]] = dict(yaml_key=code, fluxo=s["fluxo"], lignocel=s["lignocel"],
                            FL_yaml={"min": fl["min"], "med": fl["medio"], "max": fl["max"]}, FS=s["FS"])

with C.etapa(log, "FL consolidado (palha nas usinas) e leitura da v4"):
    k = ["ibge", "codigo", "cenario"]
    FLm = (pd.read_csv(C.OUT / "fl_municipio_substrato.csv")
           .merge(pd.read_csv(C.OUT / "fl_municipio_alocado.csv").drop(columns="oferta_L3_m3dia"), on=k, how="left")
           .merge(pd.read_csv(C.OUT / "fl_municipio_alocado_palha_qualquer_hub.csv")[k + ["FL_codig_alocado"]]
                  .rename(columns={"FL_codig_alocado": "FL_codig_alocado_palhaQH"}), on=k, how="left"))
    FLe = (pd.read_csv(C.OUT / "fl_estado_substrato.csv")
           .merge(pd.read_csv(C.OUT / "fl_estado_alocado.csv").drop(columns="oferta_L3_m3dia"), on=k[1:], how="left")
           .merge(pd.read_csv(C.OUT / "fl_estado_alocado_palha_qualquer_hub.csv")[k[1:] + ["FL_codig_alocado"]]
                  .rename(columns={"FL_codig_alocado": "FL_codig_alocado_palhaQH"}), on=k[1:], how="left"))
    cols4 = ["FL_codigestao", "FL_codig_alocado", "FL_mono", "FL_mono_alocado"]
    FLm[k + ["municipio"] + cols4 + ["oferta_L3_m3dia"]].to_csv(C.OUT / "fl_v5_municipio_substrato.csv", index=False,
                                                                encoding="utf-8-sig")
    FLe[k[1:] + cols4 + ["oferta_L3_m3dia"]].to_csv(C.OUT / "fl_v5_estado_substrato.csv", index=False,
                                                    encoding="utf-8-sig")
    L = pd.read_csv(C.caminho("n3_municipal"))
    L["FL_yaml"] = [REF[c]["FL_yaml"][sc] for c, sc in zip(L.codigo, L.cenario)]
    L["FS"] = [REF[c]["FS"][sc] for c, sc in zip(L.codigo, L.cenario)]
    chk = np.abs(L.FS * L.FL_yaml - L.FSxFL).max()
    log.info(f"  {len(L):,} linhas v4; conferência FS × FL_yaml = FS×FL da v4: desvio máx {chk:.2e}")
    assert chk < 1e-12
    L = L.merge(FLm[k + list(VAR_COL.values())], on=k, how="left")
    est = FLe.set_index(["codigo", "cenario"])

# ---------------------------------------------------------------------------
# 2. v5 por variante (formato da v4)
# ---------------------------------------------------------------------------
ych = L["y_CH4_biogas"]
pur, slip = G["biometano_pureza_CH4"]["med"], G["perda_metano_upgrading"]["med"]
lv = ["L1", "L2", "L3a", "L3", "L4"]
V5 = {}
for var in ordem:
    col = VAR_COL[var]
    pfx = f"{PFX}{var}_"
    with C.etapa(log, f"v5 — {ROTULO[var]} ({var}) → outputs_v5/{pfx}*"):
        D = L.copy()
        fl = D[col].copy()
        fonte = np.where(fl.notna(), f"espacial_{var}", "").astype(object)    # object: rótulos longos sem corte
        sem = fl.isna() & ~D.codigo.isin(IN["fl_yaml_para"])
        # sem FL municipal = sem oferta N3 no município (L3 = 0): usa o FL estadual espacial só para completar
        assert (D.loc[sem, "L3_CH4"] <= 1e-9).all(), "há N3 > 0 sem FL espacial"
        fl[sem] = [est.at[(c, sc), col] if (c, sc) in est.index else np.nan
                   for c, sc in zip(D.codigo[sem], D.cenario[sem])]
        fonte[sem] = f"espacial_{var}_estado (N3 = 0)"
        y = D.codigo.isin(IN["fl_yaml_para"])
        fl[y], fonte[y] = D.FL_yaml[y], "yaml (não espacializado)"
        fl = fl.fillna(D.FL_yaml)
        D["FL_v5"], D["FL_fonte"] = fl, fonte
        D["FSxFL"] = D.FS * D.FL_v5
        D["L4_CH4"] = D.L3_CH4 * D.FSxFL
        D["L4_biogas_eq"] = D.L4_CH4 / ych
        D["L4_biometano_eq"] = D.L4_CH4 * (1 - slip) / pur
        assert (D.L4_CH4 <= D.L3_CH4 + 1e-9).all() and (D.L4_CH4 >= 0).all()
        D.to_csv(OUT5 / f"{pfx}cp2b_municipio_substrato.csv", index=False, encoding="utf-8-sig")
        Lr = D.rename(columns={f"{c}_CH4": c for c in lv})
        est_n = Lr.groupby("cenario")[lv].sum().T / 1e9
        est_s = Lr[~Lr.lignocel].groupby("cenario")[lv].sum().T / 1e9
        fx = Lr[Lr.cenario == "med"].groupby("fluxo")[lv].sum() / 1e9
        fx["ret_L4_%"] = 100 * fx.L4 / fx.L1
        sub = Lr[Lr.cenario == "med"].groupby(["fluxo", "codigo"])[lv].sum() / 1e9
        mw = Lr.pivot_table(index="ibge", columns="cenario", values=["L1", "L2", "L3", "L4"], aggfunc="sum")
        mw.columns = [f"{a}_CH4_{b}" for a, b in mw.columns]
        est_n.to_csv(OUT5 / f"{pfx}cp2b_estado_niveis_bi_Nm3CH4_ano.csv", encoding="utf-8-sig")
        est_s.to_csv(OUT5 / f"{pfx}cp2b_estado_niveis_sem_lignocel_bi_Nm3CH4_ano.csv", encoding="utf-8-sig")
        fx.to_csv(OUT5 / f"{pfx}cp2b_estado_por_fluxo_med.csv", encoding="utf-8-sig")
        sub.to_csv(OUT5 / f"{pfx}cp2b_estado_por_substrato_med.csv", encoding="utf-8-sig")
        mw.reset_index().to_csv(OUT5 / f"{pfx}cp2b_municipio_resumo.csv", index=False, encoding="utf-8-sig")
        V5[var] = D
        log.info("  N4 (bi Nm³ CH4/ano): " + ", ".join(f"{sc} {est_n.at['L4', sc]:.3f}" for sc in C.SC) +
                 " | sem lignocel.: " + ", ".join(f"{sc} {est_s.at['L4', sc]:.3f}" for sc in C.SC))

# ---------------------------------------------------------------------------
# 3. Reconciliação N4 v4 × v5 por variante (estado, fluxo, top 20), com e sem lignocelulósicos
# ---------------------------------------------------------------------------
with C.etapa(log, "Reconciliação N4 v4 × v5 (com e sem lignocelulósicos)"):
    rows = []
    for base, filtro in [("com lignocel.", np.ones(len(L), bool)), ("sem lignocel.", ~L.lignocel.to_numpy())]:
        for sc in C.SC:
            m = (L.cenario == sc).to_numpy() & filtro
            r = {"base": base, "cenario": sc, "N3_M_m3dia": L.L3_CH4[m].sum() / 1e6 / C.DAYS,
                 "N4_v4_M_m3dia": L.L4_CH4[m].sum() / 1e6 / C.DAYS}
            for var in ordem:
                r[f"N4_{ROTULO[var]}_M_m3dia"] = V5[var].L4_CH4[m].sum() / 1e6 / C.DAYS
                r[f"dif_{ROTULO[var]}_%"] = 100 * (r[f"N4_{ROTULO[var]}_M_m3dia"] / r["N4_v4_M_m3dia"] - 1)
            rows.append(r)
    RE = pd.DataFrame(rows)
    RE.to_csv(OUT5 / f"{PFX}reconciliacao_estado.csv", index=False, encoding="utf-8-sig")

    def por_fluxo(filtro):
        med = (L.cenario == "med").to_numpy() & filtro
        g = L[med].groupby("fluxo")
        RF = pd.DataFrame({"N3_bi": g.L3_CH4.sum() / 1e9, "N4_v4_bi": g.L4_CH4.sum() / 1e9,
                           "FL_efetivo_v4": g.L4_CH4.sum() / (L[med].L3_CH4 * L[med].FS).groupby(L[med].fluxo).sum()})
        for var in ordem:
            Dm = V5[var][med]
            RF[f"N4_{ROTULO[var]}_bi"] = Dm.groupby("fluxo").L4_CH4.sum() / 1e9
            RF[f"dif_{ROTULO[var]}_%"] = 100 * (RF[f"N4_{ROTULO[var]}_bi"] / RF.N4_v4_bi - 1)
            RF[f"FL_efetivo_{ROTULO[var]}"] = Dm.groupby("fluxo").L4_CH4.sum() / (Dm.L3_CH4 * Dm.FS).groupby(Dm.fluxo).sum()
        tot = RF[[c for c in RF.columns if c.endswith("_bi")]].sum()
        RF.loc["TOTAL", tot.index] = tot
        for var in ordem:
            RF.loc["TOTAL", f"dif_{ROTULO[var]}_%"] = 100 * (tot[f"N4_{ROTULO[var]}_bi"] / tot["N4_v4_bi"] - 1)
        return RF

    por_fluxo(np.ones(len(L), bool)).to_csv(OUT5 / f"{PFX}reconciliacao_fluxo_med.csv", encoding="utf-8-sig")
    por_fluxo(~L.lignocel.to_numpy()).to_csv(OUT5 / f"{PFX}reconciliacao_fluxo_med_sem_lignocel.csv", encoding="utf-8-sig")
    mun = C.municipios()[["ibge", "municipio"]].set_index("ibge").municipio
    tops = []
    for base, filtro in [("com lignocel.", np.ones(len(L), bool)), ("sem lignocel.", ~L.lignocel.to_numpy())]:
        med = (L.cenario == "med").to_numpy() & filtro
        TM = pd.DataFrame({"N3_m3dia": L[med].groupby("ibge").L3_CH4.sum() / C.DAYS,
                           "N4_v4_m3dia": L[med].groupby("ibge").L4_CH4.sum() / C.DAYS})
        for var in ordem:
            TM[f"N4_{ROTULO[var]}_m3dia"] = V5[var][med].groupby("ibge").L4_CH4.sum() / C.DAYS
            TM[f"dif_{ROTULO[var]}_%"] = 100 * (TM[f"N4_{ROTULO[var]}_m3dia"] / TM.N4_v4_m3dia - 1)
        TM["municipio"] = TM.index.map(mun)
        tops.append(TM.sort_values("N4_v4_m3dia", ascending=False).head(20).assign(base=base, ranking="top 20 v4"))
        tops.append(TM.sort_values(f"N4_{ROTULO[VP]}_m3dia", ascending=False).head(20)
                    .assign(base=base, ranking=f"top 20 v5 {ROTULO[VP]}"))
    pd.concat(tops).to_csv(OUT5 / f"{PFX}reconciliacao_top20_municipios_med.csv", encoding="utf-8-sig")
    log.info("\n" + RE.round(2).to_string(index=False))

# ---------------------------------------------------------------------------
# 4. Exportação para o banco (nada é aplicado; migração única depois de fechar o método)
# ---------------------------------------------------------------------------
with C.etapa(log, "Exportação para o banco (fl_espacial/outputs/banco)"):
    slug = CF["banco"]["slug_residuos"]
    rows = []
    for c, ref in REF.items():
        e = est.xs(c, level="codigo") if c in est.index.get_level_values("codigo") else None
        comp = Y[ref["yaml_key"]]["fde"]["components"]
        r = dict(codigo_cp2b=c, fluxo=ref["fluxo"], yaml_key=ref["yaml_key"], residuos_codigo=slug.get(c, ""),
                 espacializado=e is not None)
        for var, colv in VAR_COL.items():
            for sc, kk in zip(C.SC, ["min", "medio", "max"]):
                r[f"fl_{var}_{kk}"] = float(e.at[sc, colv]) if e is not None else np.nan
        for sc, kk in zip(C.SC, ["min", "medio", "max"]):
            r[f"fl_yaml_{kk}"] = ref["FL_yaml"][sc]
            r[f"n3_{kk}_m3dia"] = float(e.at[sc, "oferta_L3_m3dia"]) if e is not None else np.nan
            base = comp["fc"][kk] * comp["fco"][kk] * comp["fs"][kk]
            r[f"availability_yaml_{kk}"] = Y[ref["yaml_key"]]["fde"]["availability"][kk]
            r[f"availability_nova_{kk}"] = base * r[f"fl_{VP}_{kk}"] if e is not None else np.nan
        rows.append(r)
    PR = pd.DataFrame(rows)
    comp_ = PR.groupby("yaml_key").codigo_cp2b.transform(lambda x: ", ".join(x) if len(x) > 1 else "")
    PR["nota"] = np.where(comp_ != "", "chave do yaml compartilhada por: " + comp_ +
                          " — o FL espacial vem só do substrato espacializado", "")
    QM = CF["q_min"]
    rp = {sc: tuple(float(x) for x in np.load(C.CACHE / "palha_usinas.npz")[f"r_{sc}"]) for sc in C.SC}
    PR["metodo"] = (f"FL espacial CP2b v5, variante principal {ROTULO[VP]} (co-digestão com alocação): fração do N3 a "
                    f"distância por estrada de um hub selecionado (Q_min {QM['min']}/{QM['med']}/{QM['max']} Nm³ CH4/dia; "
                    "decaimento linear r1–r2 por classe); palha só nas usinas, r1/r2 = " +
                    "; ".join(f"{sc} {r[0]:.1f}/{r[1]:.1f} km" for sc, r in rp.items()) +
                    "; estadual = média ponderada pela oferta N3")
    PR.to_csv(BANCO / "fl_parametros_residuos.csv", index=False, encoding="utf-8-sig")
    FB = FLm.assign(yaml_key=FLm.codigo.map(lambda c: REF[c]["yaml_key"]), residuos_codigo=FLm.codigo.map(slug))
    FB = FB[["ibge", "municipio", "codigo", "yaml_key", "residuos_codigo", "cenario"] + list(VAR_COL.values()) +
            ["oferta_L3_m3dia"]].rename(columns={"codigo": "codigo_cp2b", "oferta_L3_m3dia": "oferta_l3_ch4_m3_dia"}
                                        | {c: c.lower() for c in VAR_COL.values()})
    FB.to_csv(BANCO / "fl_municipio_substrato_banco.csv", index=False, encoding="utf-8-sig")
    nm = []
    for var in ordem:
        g = V5[var].groupby(["ibge", "fluxo", "cenario"]).agg(n3_ch4_m3_ano=("L3_CH4", "sum"),
                                                              n4_ch4_m3_ano=("L4_CH4", "sum")).reset_index()
        nm.append(g.assign(variante_fl=ROTULO[var]))
    g = L.groupby(["ibge", "fluxo", "cenario"]).agg(n4_v4_ch4_m3_ano=("L4_CH4", "sum")).reset_index()
    pd.concat(nm).merge(g, on=["ibge", "fluxo", "cenario"], how="left").to_csv(
        BANCO / "v5_n4_municipio_fluxo.csv", index=False, encoding="utf-8-sig")
    sql = ["-- ==========================================================================",
           "-- RASCUNHO — FL espacial CP2b v5 → residuos.fl_min / fl_medio / fl_max",
           "-- Gerado por fl_espacial/06_integracao.py. NÃO APLICAR AGORA (decisão do CHECKPOINT 2, 24/09/2026):",
           "--   a migração será única, depois de fechar o método (FS, parâmetros provisórios restantes e a",
           "--   nomenclatura CH4 das colunas *_biogas_m3_year). Nesse momento:",
           "--   1. conferir cada slug no banco de produção (SELECT abaixo): UPDATE 0 = slug errado;",
           "--      ORGANICO_RSU e PODA_URBANA só existem em maiúsculas;",
           f"--   2. variante deste arquivo: {ROTULO[VP]} ({VP}); palha só nas usinas.",
           "-- Termina em ROLLBACK: rode, confira 'UPDATE 1' em cada linha e só então troque por COMMIT.",
           "@@MONOTONIA@@",
           "-- ==========================================================================",
           "BEGIN;",
           "SELECT codigo, fl_min, fl_medio, fl_max FROM residuos WHERE codigo IN (" +
           ", ".join(f"'{x}'" for x in PR.loc[PR.espacializado, "residuos_codigo"]) + ") ORDER BY codigo;"]
    for _, r in PR[PR.espacializado].iterrows():
        outras = "; ".join(f"{ROTULO[v]} {r[f'fl_{v}_min']:.3f}/{r[f'fl_{v}_medio']:.3f}/{r[f'fl_{v}_max']:.3f}"
                           for v in VAR_COL if v != VP)
        sql.append(f"-- {r.codigo_cp2b} (yaml {r.yaml_key}); FL yaml atual {r.fl_yaml_min:.2f}/{r.fl_yaml_medio:.2f}/"
                   f"{r.fl_yaml_max:.2f}; {outras}")
        sql.append(f"UPDATE residuos SET fl_min = {r[f'fl_{VP}_min']:.4f}, fl_medio = {r[f'fl_{VP}_medio']:.4f}, "
                   f"fl_max = {r[f'fl_{VP}_max']:.4f}, updated_at = NOW() WHERE codigo = '{r.residuos_codigo}';")
    sql += ["ROLLBACK;  -- trocar por COMMIT só na migração única, depois de conferir", ""]
    (BANCO / "rascunho_update_residuos_fl.sql").write_text("\n".join(sql), encoding="utf-8")
    esp_ = PR[PR.espacializado]
    viol = {ROTULO[v]: int(((esp_[f"fl_{v}_min"] > esp_[f"fl_{v}_medio"]) | (esp_[f"fl_{v}_medio"] > esp_[f"fl_{v}_max"])).sum())
            for v in VAR_COL}
    ruins = esp_[(esp_[f"fl_{VP}_min"] > esp_[f"fl_{VP}_medio"]) | (esp_[f"fl_{VP}_medio"] > esp_[f"fl_{VP}_max"])]
    txt = ("-- Triplos conferidos: todos monotônicos (min ≤ medio ≤ max), como exige a migração 027." if ruins.empty else
           "-- ATENÇÃO: triplos NÃO monotônicos (a migração 027 exige min ≤ medio ≤ max): "
           + ", ".join(ruins.codigo_cp2b))
    f_sql = BANCO / "rascunho_update_residuos_fl.sql"
    f_sql.write_text(f_sql.read_text(encoding="utf-8").replace("@@MONOTONIA@@", txt), encoding="utf-8")
    log.info(f"  {len(esp_)} resíduos com FL espacial; triplos não monotônicos por variante: {viol}")
    log.info("\n" + PR.set_index("codigo_cp2b")[["residuos_codigo", "fl_yaml_medio"] +
                                                [f"fl_{v}_medio" for v in VAR_COL]].round(3).to_string())
log.info("Etapa 6 concluída.")
