#!/usr/bin/env python3
"""Etapa 1 — grafo viário OSM (Geofabrik Sudeste, jan/2026), SP + buffer, distância por estrada (EPSG:5880).

Nós = extremidades das vias e vértices compartilhados por mais de uma via (interseções reais do OSM);
arestas = trechos entre nós consecutivos, peso = comprimento em metros. Grafo não direcionado; só o maior
componente conexo. Gera duas versões: completa e sem track/service (sensibilidade).
Fator de tortuosidade: 5.000 pares OD a 1–60 km (validação e plano B).

Saídas: cache/grafo_completo.npz, cache/grafo_sem_track.npz, outputs/grafo_resumo.csv,
        outputs/tortuosidade_pares.csv, outputs/tortuosidade_resumo.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyogrio
import shapely
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

import fl_comum as C

log = C.logger("01_grafo")
G = C.CFG["grafo"]
TT = G["tortuosidade"]

with C.etapa(log, "Recorte: SP + buffer"):
    mun = C.municipios()
    sp = mun.union_all()
    buf = sp.buffer(G["buffer_estado_km"] * 1000)
    shapely.prepare(sp)
    shapely.prepare(buf)
    to_ll = Transformer.from_crs(C.CRS, 4326, always_xy=True)
    bx, by = shapely.get_coordinates(buf.envelope).T
    lx, ly = to_ll.transform(bx, by)
    bbox_ll = (lx.min(), ly.min(), lx.max(), ly.max())
    log.info(f"  SP {sp.area / 1e6:,.0f} km²; buffer {G['buffer_estado_km']} km → {buf.area / 1e6:,.0f} km²; "
             f"bbox {np.round(bbox_ll, 3).tolist()}")

with C.etapa(log, "Leitura OSM (fclass filtradas, bbox)"):
    fcl = G["fclass_completo"]
    where = "fclass IN (" + ",".join(f"'{f}'" for f in fcl) + ")"
    df = pyogrio.read_dataframe(C.caminho("osm_roads"), columns=["fclass"], where=where, bbox=bbox_ll)
    df = df.explode(index_parts=False, ignore_index=True)
    log.info(f"  {len(df):,} vias no bbox (após explode)")

with C.etapa(log, "Vértices → EPSG:5880 e recorte ao buffer"):
    coords, widx = shapely.get_coordinates(np.asarray(df.geometry), return_index=True)
    to_m = Transformer.from_crs(4326, C.CRS, always_xy=True)
    X, Y = to_m.transform(coords[:, 0], coords[:, 1])
    lines = shapely.linestrings(np.c_[X, Y], indices=widx)
    keep_way = shapely.intersects(lines, buf)
    kv = keep_way[widx]
    coords, X, Y, widx = coords[kv], X[kv], Y[kv], widx[kv]
    fclass_way = df["fclass"].to_numpy()
    log.info(f"  {int(keep_way.sum()):,} vias e {len(X):,} vértices dentro do buffer")
    del lines, df

with C.etapa(log, "Nós (extremidades + vértices compartilhados) e arestas"):
    q = np.round((coords + [180.0, 90.0]) * 1e7).astype(np.int64)  # precisão nativa do OSM (1e-7 grau)
    key = q[:, 0] * 2_000_000_000 + q[:, 1]
    first = np.r_[True, widx[1:] != widx[:-1]]
    last = np.r_[widx[1:] != widx[:-1], True]
    uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    is_node = first | last | (cnt[inv] >= 2)
    seg = np.hypot(np.diff(X, prepend=X[0]), np.diff(Y, prepend=Y[0]))
    seg[first] = 0.0
    cum = np.cumsum(seg)
    ni = np.flatnonzero(is_node)
    same = widx[ni[1:]] == widx[ni[:-1]]
    a, b = ni[:-1][same], ni[1:][same]
    u, v = inv[a], inv[b]
    comp = cum[b] - cum[a]
    ecls = fclass_way[widx[a]]
    ok = u != v
    u, v, comp, ecls = u[ok], v[ok], comp[ok], ecls[ok]
    # coordenadas de cada chave única (primeira ocorrência)
    first_occ = np.full(len(uk), -1, dtype=np.int64)
    first_occ[inv[::-1]] = np.arange(len(inv))[::-1]
    UX, UY = X[first_occ], Y[first_occ]
    log.info(f"  {len(ni):,} vértices-nó; {len(u):,} arestas brutas")
    del coords, q, key, seg, cum, X, Y


def montar(u, v, comp, ecls, nome):
    """Remove duplicatas, mantém o maior componente conexo, reindexa e grava o grafo."""
    lo, hi = np.minimum(u, v), np.maximum(u, v)
    e = pd.DataFrame({"lo": lo, "hi": hi, "m": comp, "fclass": ecls}).sort_values("m")
    e = e.drop_duplicates(["lo", "hi"], keep="first")
    used, rel = np.unique(np.r_[e.lo.to_numpy(), e.hi.to_numpy()], return_inverse=True)
    ne = len(e)
    uu, vv = rel[:ne], rel[ne:]
    n = len(used)
    A = coo_matrix((np.ones(ne), (uu, vv)), shape=(n, n))
    ncomp, lab = connected_components(A, directed=False)
    big = np.bincount(lab).argmax()
    kn = lab == big
    ke = kn[uu]
    tot_km, kept_km = e.m.sum() / 1e3, e.m.to_numpy()[ke].sum() / 1e3
    newid = np.cumsum(kn) - 1
    out = dict(x=UX[used][kn], y=UY[used][kn], u=newid[uu[ke]].astype(np.int32), v=newid[vv[ke]].astype(np.int32),
               comp=e.m.to_numpy()[ke], fclass=e.fclass.to_numpy()[ke].astype(str))
    np.savez_compressed(C.CACHE / f"grafo_{nome}.npz", **out)
    km_cls = pd.Series(out["comp"]).groupby(out["fclass"]).sum() / 1e3
    log.info(f"  [{nome}] {n:,} nós, {ne:,} arestas, {ncomp:,} componentes; maior: {int(kn.sum()):,} nós "
             f"({100 * kn.mean():.2f}%), {int(ke.sum()):,} arestas; extensão {kept_km:,.0f} de {tot_km:,.0f} km "
             f"(descartado {tot_km - kept_km:,.0f} km = {100 * (1 - kept_km / tot_km):.2f}%)")
    return out, dict(variante=nome, nos=int(kn.sum()), arestas=int(ke.sum()), componentes=int(ncomp),
                     extensao_km=round(kept_km, 1), descartado_km=round(tot_km - kept_km, 1),
                     descartado_pct=round(100 * (1 - kept_km / tot_km), 3),
                     **{f"km_{k}": round(float(x), 1) for k, x in km_cls.items()})


with C.etapa(log, "Grafo completo"):
    Gc, rc = montar(u, v, comp, ecls, "completo")
with C.etapa(log, "Grafo sem track/service"):
    m = ~np.isin(ecls, G["fclass_excluir_variante_sem_track"])
    Gs, rs = montar(u[m], v[m], comp[m], ecls[m], "sem_track")
pd.DataFrame([rc, rs]).T.to_csv(C.OUT / "grafo_resumo.csv", header=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Fator de tortuosidade
# ---------------------------------------------------------------------------
with C.etapa(log, f"Tortuosidade: sorteio de {TT['n_pares']} pares a {TT['dist_min_km']}–{TT['dist_max_km']} km"):
    rng = np.random.default_rng(C.SEED)
    insp = shapely.contains_xy(sp, Gc["x"], Gc["y"])
    ids_sp = np.flatnonzero(insp)
    tree = cKDTree(np.c_[Gc["x"][ids_sp], Gc["y"][ids_sp]])
    o_all, d_all = [], []
    while len(o_all) < TT["n_pares"]:
        k = 4 * TT["n_pares"]
        o = ids_sp[rng.integers(0, len(ids_sp), k)]
        dist = rng.uniform(TT["dist_min_km"], TT["dist_max_km"], k) * 1000
        ang = rng.uniform(0, 2 * np.pi, k)
        tx, ty = Gc["x"][o] + dist * np.cos(ang), Gc["y"][o] + dist * np.sin(ang)
        dd, j = tree.query(np.c_[tx, ty])
        d = ids_sp[j]
        e = np.hypot(Gc["x"][d] - Gc["x"][o], Gc["y"][d] - Gc["y"][o])
        ok = (dd <= TT["tolerancia_destino_m"]) & (e >= TT["dist_min_km"] * 1000) & (e <= TT["dist_max_km"] * 1000)
        o_all += o[ok].tolist()
        d_all += d[ok].tolist()
    o, d = np.array(o_all[:TT["n_pares"]]), np.array(d_all[:TT["n_pares"]])
    eu = np.hypot(Gc["x"][d] - Gc["x"][o], Gc["y"][d] - Gc["y"][o])

with C.etapa(log, "Tortuosidade: distâncias na rede (pandana, grafo completo)"):
    net = C.rede_pandana(Gc)
    rede = np.asarray(net.shortest_path_lengths(o, d), dtype=float)
    del net

with C.etapa(log, "Tortuosidade: mesmos pares no grafo sem track/service"):
    ts = cKDTree(np.c_[Gs["x"], Gs["y"]])
    c_o, so = ts.query(np.c_[Gc["x"][o], Gc["y"][o]])
    c_d, sd = ts.query(np.c_[Gc["x"][d], Gc["y"][d]])
    net = C.rede_pandana(Gs)
    rede_s = np.asarray(net.shortest_path_lengths(so, sd), dtype=float) + c_o + c_d
    del net

bins = TT["faixas_km"]
P = pd.DataFrame({"euclid_km": eu / 1e3, "rede_km": rede / 1e3, "rede_sem_track_km": rede_s / 1e3})
P["razao"] = P.rede_km / P.euclid_km
P["razao_sem_track"] = P.rede_sem_track_km / P.euclid_km
P["faixa_km"] = pd.cut(P.euclid_km, bins, right=False).astype(str)
P.to_csv(C.OUT / "tortuosidade_pares.csv", index=False, encoding="utf-8-sig")


def resumo(g):
    return pd.Series({"n": len(g), "razao_mediana": g.razao.median(), "razao_P10": g.razao.quantile(0.10),
                      "razao_P90": g.razao.quantile(0.90), "sem_track_mediana": g.razao_sem_track.median(),
                      "sem_track_P10": g.razao_sem_track.quantile(0.10),
                      "sem_track_P90": g.razao_sem_track.quantile(0.90)})


R = P.groupby("faixa_km", sort=False).apply(resumo, include_groups=False)
R = R.loc[sorted(R.index, key=lambda s: float(s.strip("[").split(",")[0]))]
R.loc["todos"] = resumo(P)
R.round(3).to_csv(C.OUT / "tortuosidade_resumo.csv", encoding="utf-8-sig")
log.info("\n" + R.round(3).to_string())
log.info(f"Pares com razão < 1 (erro de geometria): {(P.razao < 0.999).sum()}")
