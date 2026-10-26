#!/usr/bin/env python3
"""Etapa 3 — hubs candidatos e associação ao grafo.

Existentes: usinas (EPE 2018), ETEs ativas não-lagoa, fábricas de suco (v5.1, RAIS; 00_fabricas_suco.py) e
plantas de biogás operantes (MapBiomas 10.1, ANP, PILAR).
Novos: centroides de uma grade de 2 km dentro de SP, a ≤ 2 km de uma via do grafo, fora de UCs de proteção
integral (estaduais e federais) e terras indígenas. O hub novo é posicionado no nó viário mais próximo.
Toda célula/ponto de oferta e todo hub são associados ao nó mais próximo (distância de conexão reportada).

Saídas: cache/hubs.pkl, cache/locais_nos.pkl, outputs/plantas_operantes_sp.csv, outputs/hubs_conexao_resumo.csv
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

import fl_comum as C

log = C.logger("03_hubs")
CF = C.CFG
HB = CF["hubs"]

G = C.carregar_grafo("completo")
NX, NY = G["x"], G["y"]
tree_nos = cKDTree(np.c_[NX, NY])
mun = C.municipios()
sp = mun.union_all()
shapely.prepare(sp)
PT = pd.read_pickle(C.CACHE / "pontos_fonte.pkl")
LOC = pd.read_pickle(C.CACHE / "oferta_locais.pkl")

# ---------------------------------------------------------------------------
# 1. Plantas de biogás operantes em SP (hubs existentes e base de validação)
# ---------------------------------------------------------------------------
with C.etapa(log, "Plantas de biogás operantes (MapBiomas, ANP, PILAR)"):
    ete_pts = PT[PT.tipo == "ete"]
    us_pts = PT[PT.tipo == "usina"]
    t_ete, t_us = cKDTree(ete_pts[["x", "y"]].to_numpy()), cKDTree(us_pts[["x", "y"]].to_numpy())

    mb = gpd.read_file(C.caminho("biogas_mapbiomas"))
    mb = mb[(mb.Estado == "SP") & (mb.Situacao == "Em operação")].to_crs(C.CRS)
    mbx, mby = mb.geometry.x.to_numpy(), mb.geometry.y.to_numpy()
    d_ete, _ = t_ete.query(np.c_[mbx, mby])
    d_us, _ = t_us.query(np.c_[mbx, mby])
    tipo = np.select([mb.Categoria.eq("Agropecuária"),
                      mb.Categoria.eq("RSU ou Esgoto") & (d_ete <= 1500), mb.Categoria.eq("RSU ou Esgoto"),
                      mb.Categoria.eq("Indústria") & (d_us <= 3000)],
                     ["pecuaria", "ete", "aterro", "usina"], default="industria")
    P1 = pd.DataFrame({"fonte": "MapBiomas 10.1", "nome": mb.Municipio.to_numpy(), "municipio": mb.Municipio.to_numpy(),
                       "categoria_fonte": mb.Categoria.to_numpy(), "tipo": tipo, "x": mbx, "y": mby})

    anp = pd.read_csv(C.caminho("biogas_anp"))
    anp = anp[(anp.uf == "SP") & (anp.status == "operating")]
    anp = anp[~((anp.lat.round(5) == -23.65008) & (anp.lon.round(5) == -46.64810))]   # coordenada sentinela (SP capital)
    g = gpd.GeoSeries(gpd.points_from_xy(anp.lon, anp.lat), crs=4326).to_crs(C.CRS)
    TIPO_ANP = {"landfill_gas": "aterro", "msw_forsu": "aterro", "sewage_sludge": "ete", "vinasse_filtercake": "usina",
                "vinasse_filtercake_manure": "usina", "agro_industrial": "industria"}
    P2 = pd.DataFrame({"fonte": "ANP", "nome": anp.plant_name.to_numpy(), "municipio": anp.municipality.to_numpy(),
                       "categoria_fonte": anp.feedstock.to_numpy(), "tipo": anp.feedstock.map(TIPO_ANP).fillna("industria").to_numpy(),
                       "x": g.x.to_numpy(), "y": g.y.to_numpy()})

    pb = gpd.read_file(C.caminho("biogas_pilar"))
    pb = pb[(pb.TIPO_PLANT == "Biogás") & (pb.STATUS == "Operacional")].to_crs(C.CRS)
    P3 = pd.DataFrame({"fonte": "PILAR Plantas_Biogas_SP", "nome": pb.SUBTIPO.to_numpy(), "municipio": "",
                       "categoria_fonte": pb.FONTE_DADO.to_numpy(), "tipo": "sem_tipo",
                       "x": pb.geometry.x.to_numpy(), "y": pb.geometry.y.to_numpy()})

    # deduplicação: MapBiomas e ANP (com tipo) têm precedência; ponto a ≤ 500 m de um já aceito é a mesma planta
    PL = pd.concat([P1, P2, P3], ignore_index=True)
    PL = PL[shapely.contains_xy(sp.buffer(1000), PL.x, PL.y)].reset_index(drop=True)
    keep, pos = [], np.empty((0, 2))
    for i, r in PL.iterrows():
        if len(pos) and np.min(np.hypot(pos[:, 0] - r.x, pos[:, 1] - r.y)) <= 500:
            continue
        keep.append(i)
        pos = np.vstack([pos, [r.x, r.y]])
    PL = PL.loc[keep].reset_index(drop=True)
    PL["planta_id"] = np.arange(len(PL))
    PL.to_csv(C.OUT / "plantas_operantes_sp.csv", index=False, encoding="utf-8-sig")
    log.info("  pontos de plantas (hubs existentes) por fonte e tipo:\n" + PL.groupby(["fonte", "tipo"]).size().to_string())

    # Base de VALIDAÇÃO: uma linha por planta. A ANP tem precedência, com o tipo corrigido como na v4; um registro
    # do MapBiomas no mesmo município a ≤ 5 km de uma planta ANP é a mesma planta (as coordenadas diferem entre fontes).
    VL = CF["validacao"]
    P2v = P2.copy()
    P2v["tipo"] = [VL["reclassificacao_anp"].get(pid, t) for pid, t in zip(anp.plant_id, P2v.tipo)]
    dup = np.zeros(len(P1), bool)
    for _, a in P2v.iterrows():
        mesmo = (P1.municipio.map(C.norm) == C.norm(a.municipio)).to_numpy()
        dup |= mesmo & (np.hypot(P1.x - a.x, P1.y - a.y).to_numpy() <= VL["duplicata_mesmo_municipio_km"] * 1000)
    PV = pd.concat([P2v, P1[~dup], P3], ignore_index=True)
    PV = PV[shapely.contains_xy(sp.buffer(1000), PV.x, PV.y)].reset_index(drop=True)
    keep, pos = [], np.empty((0, 2))
    for i, r in PV.iterrows():
        if len(pos) and np.min(np.hypot(pos[:, 0] - r.x, pos[:, 1] - r.y)) <= 500:
            continue
        keep.append(i)
        pos = np.vstack([pos, [r.x, r.y]])
    PV = PV.loc[keep].reset_index(drop=True)
    PV.to_csv(C.OUT / "plantas_validacao_sp.csv", index=False, encoding="utf-8-sig")
    log.info(f"  base de validação: {len(PV)} plantas ({int(dup.sum())} registros do MapBiomas eram duplicatas de "
             f"plantas ANP)\n" + PV.groupby(["fonte", "tipo"]).size().to_string())

# ---------------------------------------------------------------------------
# 2. Hubs existentes
# ---------------------------------------------------------------------------
fab_pts = PT[PT.tipo == "fabrica_suco"]
H = [pd.DataFrame({"tipo": "usina", "ref": us_pts.ref, "nome": us_pts.nome, "x": us_pts.x, "y": us_pts.y}),
     pd.DataFrame({"tipo": "ete", "ref": ete_pts.ref, "nome": ete_pts.nome, "x": ete_pts.x, "y": ete_pts.y}),
     pd.DataFrame({"tipo": "fabrica_suco", "ref": fab_pts.ref, "nome": fab_pts.nome, "x": fab_pts.x, "y": fab_pts.y}),
     pd.DataFrame({"tipo": "biogas", "ref": "planta:" + PL.planta_id.astype(str), "nome": PL.nome, "x": PL.x, "y": PL.y})]
HE = pd.concat(H, ignore_index=True)
HE["origem"] = "existente"

# ---------------------------------------------------------------------------
# 3. Hubs novos: grade de 2 km
# ---------------------------------------------------------------------------
with C.etapa(log, "Grade de 2 km: dentro de SP, perto de via, fora das exclusões"):
    G2 = C.grade_sp(CF["grade"]["celula_hub_m"], mun)
    cid = np.arange(G2.nx * G2.ny)
    cx, cy = G2.centro(cid)
    dentro = shapely.contains_xy(sp, cx, cy)
    cid, cx, cy = cid[dentro], cx[dentro], cy[dentro]
    n0 = len(cid)
    # exclusões
    exc = []
    for p in CF["caminhos"]["exclusoes"]:
        e = gpd.read_file(p, bbox=tuple(gpd.GeoSeries([sp], crs=C.CRS).to_crs(4674).total_bounds)).to_crs(C.CRS)
        exc.append(e.geometry.make_valid())
    exc = shapely.union_all(np.concatenate([np.asarray(e) for e in exc]))
    shapely.prepare(exc)
    fora_exc = ~shapely.contains_xy(exc, cx, cy)
    # distância a uma via: nós + pontos a cada 250 m ao longo das arestas (cordas)
    u, v, comp = G["u"], G["v"], G["comp"]
    ns = np.maximum(1, np.ceil(comp / 250).astype(int))
    rep = np.repeat(np.arange(len(u)), ns)
    frac = (np.arange(len(rep)) - np.repeat(np.cumsum(ns) - ns, ns) + 0.5) / np.repeat(ns, ns)
    sx = NX[u[rep]] + frac * (NX[v[rep]] - NX[u[rep]])
    sy = NY[u[rep]] + frac * (NY[v[rep]] - NY[u[rep]])
    t_via = cKDTree(np.c_[np.r_[NX, sx], np.r_[NY, sy]])
    d_via, _ = t_via.query(np.c_[cx, cy], distance_upper_bound=HB["dist_max_via_m"] + 1)
    perto = d_via <= HB["dist_max_via_m"]
    ok = fora_exc & perto
    log.info(f"  {n0:,} centroides em SP; em exclusões: {int((~fora_exc).sum()):,}; a > 2 km de via: {int((~perto).sum()):,}; "
             f"candidatos: {int(ok.sum()):,}")
    del t_via, sx, sy, rep, frac
    HN = pd.DataFrame({"tipo": "grade", "ref": "grade:" + pd.Series(cid[ok]).astype(str), "nome": "", "x": cx[ok], "y": cy[ok]})
    HN["origem"] = "novo"

# ---------------------------------------------------------------------------
# 4. Associação ao grafo
# ---------------------------------------------------------------------------
with C.etapa(log, "Associação de hubs e locais de oferta ao nó mais próximo"):
    HUBS = pd.concat([HE, HN], ignore_index=True)
    d, j = tree_nos.query(HUBS[["x", "y"]].to_numpy())
    HUBS["node"] = j.astype(np.int64)
    HUBS["dist_no_m"] = d
    # hub novo fica no nó (conexão 0); hub existente mantém a posição real (conexão = distância ao nó)
    HUBS["conn_m"] = np.where(HUBS.origem == "novo", 0.0, d)
    HUBS["hub_id"] = np.arange(len(HUBS))
    d, j = tree_nos.query(LOC[["x", "y"]].to_numpy())
    LOC["node"], LOC["conn_m"] = j.astype(np.int64), d
    # oferta "na fonte": ponto de oferta com o mesmo ref de um hub existente (usina ↔ usina, ETE ↔ ETE, fábrica ↔ fábrica)
    ref2hub = dict(zip(HUBS.ref, HUBS.hub_id))
    LOC["hub_fonte"] = LOC.ref.map(ref2hub).fillna(-1).astype(np.int64)
    HUBS.to_pickle(C.CACHE / "hubs.pkl")
    LOC.to_pickle(C.CACHE / "locais_nos.pkl")

    def q(s):
        return pd.Series({"n": len(s), "mediana_m": s.median(), "P95_m": s.quantile(0.95), "max_m": s.max()})

    R = pd.concat({"hub:" + k: q(g.dist_no_m) for k, g in HUBS.groupby("tipo")} |
                  {"oferta:" + k: q(g.conn_m) for k, g in LOC.groupby("tipo")}, axis=1).T
    R.round(0).to_csv(C.OUT / "hubs_conexao_resumo.csv", encoding="utf-8-sig")
    log.info("  distância ao nó mais próximo:\n" + R.round(0).to_string())
    log.info(f"  hubs: {len(HUBS):,} ({(HUBS.origem == 'existente').sum()} existentes + {(HUBS.origem == 'novo').sum():,} "
             f"da grade); nós-fonte distintos: {HUBS.node.nunique():,}; locais de oferta na fonte: "
             f"{int((LOC.hub_fonte >= 0).sum())}")
log.info("Etapa 3 concluída.")
