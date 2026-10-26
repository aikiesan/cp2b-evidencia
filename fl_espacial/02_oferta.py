#!/usr/bin/env python3
"""Etapa 2 — espacializar a oferta mobilizável (N3) por substrato e cenário, preservando o total municipal.

N3 municipal (Nm³ CH4/ano ÷ 365) é distribuído dentro do município conforme config_fl.yaml → espacializacao:
  usina (ponto)  vinhaça ∝ capacidade de etanol; torta/bagaço ∝ classe de capacidade (mesma alocação da v4)
  pixel          área MapBiomas 2024 da classe (grade auxiliar de 100 m alinhada à de 1 km)
  aves/suínos/bovinos  pontos GEDAVE/granjas, peso = capacidade/plantel/rebanho, agregados na célula de 1 km
  urbano         área urbana
  ete (ponto)    partes iguais entre as ETEs ativas não-lagoa do município
  fabrica_suco   bagaço de citros (v5.1): um ponto por município com fábrica de suco concentrado, no centroide da
                 área urbana; o N3 já vem realocado às fábricas na base de 00_fabricas_suco.py
Fallback (listado): outros pontos do mesmo cadastro → centroide da área agropecuária → centroide municipal.

LGPD: do cadastro bovino só são lidas as colunas de config (coordenadas, município, finalidade, sistema, rebanho);
nenhum ponto individual é gravado — só células de 1 km e municípios.

Saídas: outputs/grade_oferta_1km.gpkg (camadas celulas, pontos), outputs/oferta_totais_verificacao.csv,
        outputs/oferta_fallback_casos.csv, outputs/figuras/oferta_*.png, cache/oferta_*.pkl, cache/grade_meta.json
"""
from __future__ import annotations

import json

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

import fl_comum as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402

log = C.logger("02_oferta")
CF = C.CFG
MB = CF["mapbiomas"]
PEC = CF["pecuaria"]
ESP = CF["espacializacao"]

# ---------------------------------------------------------------------------
# 0. N3 municipal e base municipal
# ---------------------------------------------------------------------------
with C.etapa(log, "N3 municipal (Nm³ CH4/dia)"):
    L = pd.read_csv(C.caminho("n3_municipal"), usecols=["ibge", "codigo", "cenario", "L3_CH4"])
    L["n3"] = L["L3_CH4"] / C.DAYS
    N3 = L.pivot_table(index="ibge", columns=["codigo", "cenario"], values="n3", aggfunc="sum").fillna(0.0)
    mun = C.municipios().reset_index(drop=True)
    mun["midx"] = np.arange(1, len(mun) + 1, dtype=np.int32)          # 0 = fora de SP
    ibge_of = dict(zip(mun.midx, mun.ibge))
    midx_of = dict(zip(mun.ibge, mun.midx))
    key2ibge = dict(zip(mun.municipio.map(C.norm), mun.ibge))
    N3 = N3.reindex(mun.ibge).fillna(0.0)
    SUBS = [s for s in ESP if ESP[s]["fonte"] != "ignorar"]
    log.info(f"  {len(mun)} municípios; substratos espacializados: {len(SUBS)}; ignorado: "
             f"{[s for s in ESP if ESP[s]['fonte'] == 'ignorar']}")

# ---------------------------------------------------------------------------
# 1. Grades: 1 km (oferta) e 100 m (auxiliar), alinhadas
# ---------------------------------------------------------------------------
G1 = C.grade_sp(CF["grade"]["celula_oferta_m"], mun)
F = int(round(G1.passo / CF["grade"]["raster_base_m"]))
R100 = G1.passo / F
NX, NY = G1.nx * F, G1.ny * F
YTOP = G1.y0 + G1.ny * G1.passo
TR = from_origin(G1.x0, YTOP, R100, R100)
NCELL = G1.nx * G1.ny
json.dump({"grade_1km": G1.to_dict(), "raster_m": R100}, open(C.CACHE / "grade_meta.json", "w"))
log.info(f"Grade 1 km: {G1.nx} × {G1.ny}; raster auxiliar {R100:.0f} m: {NX} × {NY}")


def px_xy(r, c):
    return G1.x0 + (c + 0.5) * R100, YTOP - (r + 0.5) * R100


def px_cell(r, c):
    return ((NY - 1 - r) // F) * G1.nx + (c // F)


with C.etapa(log, "Raster de municípios (100 m)"):
    MUN = rasterize(zip(mun.geometry, mun.midx), out_shape=(NY, NX), transform=TR, fill=0, dtype="uint16")


def lookup_mun(x, y):
    c = np.floor((np.asarray(x) - G1.x0) / R100).astype(np.int64)
    r = np.floor((YTOP - np.asarray(y)) / R100).astype(np.int64)
    ok = (r >= 0) & (r < NY) & (c >= 0) & (c < NX)
    out = np.zeros(len(c), dtype=np.int32)
    out[ok] = MUN[r[ok], c[ok]]
    return out


with C.etapa(log, "MapBiomas 2024 → grade de 100 m (vizinho mais próximo)"):
    LU = np.zeros((NY, NX), dtype=np.uint8)
    with rasterio.open(C.caminho("mapbiomas_2024")) as src:
        reproject(rasterio.band(src, 1), LU, dst_transform=TR, dst_crs=C.CRS, resampling=Resampling.nearest)
    vals, cnts = np.unique(LU[MUN > 0], return_counts=True)
    log.info("  classes em SP (km²): " + ", ".join(f"{v}: {n * R100 ** 2 / 1e6:,.0f}" for v, n in zip(vals, cnts)))

with C.etapa(log, "MapBiomas 2ª safra 2024 (janela SP, leitura a ~90 m) → grade de 100 m"):
    LU2 = np.zeros((NY, NX), dtype=np.uint8)
    b = gpd.GeoSeries([shapely.box(*mun.total_bounds)], crs=C.CRS).to_crs(4326).total_bounds
    with rasterio.open(C.caminho("mapbiomas_2a_safra_2024")) as src:
        win = from_bounds(b[0] - 0.05, b[1] - 0.05, b[2] + 0.05, b[3] + 0.05, src.transform).round_offsets().round_lengths()
        k = MB["fator_leitura_2a_safra"]
        arr = src.read(1, window=win, out_shape=(int(win.height // k), int(win.width // k)), resampling=Resampling.nearest)
        wtr = src.window_transform(win) * rasterio.Affine.scale(win.width / arr.shape[1], win.height / arr.shape[0])
        reproject(arr, LU2, src_transform=wtr, src_crs=src.crs, dst_transform=TR, dst_crs=C.CRS,
                  resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
        del arr
    vals, cnts = np.unique(LU2[MUN > 0], return_counts=True)
    log.info("  2ª safra em SP (km²): " + ", ".join(f"{v}: {n * R100 ** 2 / 1e6:,.0f}" for v, n in zip(vals, cnts)))
    both = np.unique(LU[(LU2 == 1) & (MUN > 0)], return_counts=True)
    log.info("  classe 1ª safra sob valor 1 da 2ª safra: " + ", ".join(f"{v}: {n}" for v, n in zip(*both)))

with C.etapa(log, "Áreas urbanas → grade de 100 m"):
    urb = gpd.read_file(C.caminho("areas_urbanas")).to_crs(C.CRS)
    URB = rasterize(((g, 1) for g in urb.geometry if g is not None and not g.is_empty), out_shape=(NY, NX),
                    transform=TR, fill=0, dtype="uint8")
    log.info(f"  {len(urb):,} polígonos; área urbana em SP {((URB > 0) & (MUN > 0)).sum() * R100 ** 2 / 1e6:,.0f} km²")


def contagem(mask):
    """Pixels da máscara por (município, célula de 1 km) → DataFrame midx, cell, n."""
    r, c = np.nonzero(mask & (MUN > 0))
    mu = MUN[r, c].astype(np.int64)
    k = mu * NCELL + px_cell(r, c)
    uk, n = np.unique(k, return_counts=True)
    return pd.DataFrame({"midx": (uk // NCELL).astype(np.int32), "cell": uk % NCELL, "w": n.astype(float)})


def centroides(mask):
    """Centroide da máscara por município (ponto dentro do município): dict midx → (x, y)."""
    r, c = np.nonzero(mask & (MUN > 0))
    mu = MUN[r, c]
    o = np.argsort(mu, kind="stable")
    r, c, mu = r[o], c[o], mu[o]
    x, y = px_xy(r, c)
    ms, start, cnt = np.unique(mu, return_index=True, return_counts=True)
    mx, my = np.add.reduceat(x, start) / cnt, np.add.reduceat(y, start) / cnt
    inside = lookup_mun(mx, my) == ms
    out = {}
    for i, m in enumerate(ms):
        if inside[i]:
            out[int(m)] = (mx[i], my[i])
        else:  # centroide caiu fora (município não convexo): pixel mais próximo dele
            s = slice(start[i], start[i] + cnt[i])
            j = np.argmin((x[s] - mx[i]) ** 2 + (y[s] - my[i]) ** 2)
            out[int(m)] = (x[s][j], y[s][j])
    return out


with C.etapa(log, "Centroides de fallback (área agropecuária, área urbana, município)"):
    CENT_AGRO = centroides(np.isin(LU, MB["agropecuaria"]))
    CENT_URB = centroides(URB > 0)
    rp = mun.geometry.representative_point()
    CENT_MUN = {m: (p.x, p.y) for m, p in zip(mun.midx, rp)}
    log.info(f"  com área agropecuária: {len(CENT_AGRO)}; com área urbana: {len(CENT_URB)}")

# ---------------------------------------------------------------------------
# 2. Pesos por substrato: tabela (midx, loc, w) + registro de fallback
# ---------------------------------------------------------------------------
# Locais: células (loc = id da célula ≥ 0) e pontos (loc = −1, −2, … → tabela PONTOS)
PONTOS = []          # dicts: loc, tipo, ref, nome, x, y, ibge
FALLBACK = []        # dicts: ibge, codigo, nivel


def novo_ponto(tipo, ref, nome, x, y, ibge):
    loc = -(len(PONTOS) + 1)
    PONTOS.append(dict(loc=loc, tipo=tipo, ref=ref, nome=nome, x=x, y=y, ibge=ibge))
    return loc


def w_pontos(midx, x, y, w):
    """Pontos → células de 1 km (agregado; nenhum ponto individual sai daqui)."""
    df = pd.DataFrame({"midx": midx, "cell": G1.ids(x, y), "w": w})
    return df.groupby(["midx", "cell"], as_index=False).w.sum()


def fallback_loc(midx, prefer="agro"):
    for nivel, tab in ((prefer, CENT_AGRO if prefer == "agro" else CENT_URB), ("municipio", CENT_MUN)):
        if midx in tab:
            x, y = tab[midx]
            return nivel, int(G1.ids([x], [y])[0])
    raise RuntimeError(midx)


def completar(cod, W, niveis, prefer="agro"):
    """Garante peso para todo município com N3 > 0; W: lista [(nome_nivel, DataFrame midx, cell|loc, w)]."""
    need = set(mun.midx[(N3[cod].max(axis=1) > 0).to_numpy()])
    partes = []
    for nome, df in zip(niveis, W):
        df = df[df.midx.isin(need) & (df.w > 0)]
        tem = set(df.midx)
        partes.append(df)
        for m in tem:
            if nome != niveis[0]:
                FALLBACK.append(dict(ibge=ibge_of[m], codigo=cod, nivel=nome))
        need -= tem
    for m in sorted(need):
        nivel, cell = fallback_loc(m, prefer)
        FALLBACK.append(dict(ibge=ibge_of[m], codigo=cod, nivel=f"centroide_{nivel}"))
        partes.append(pd.DataFrame({"midx": [m], "cell": [cell], "w": [1.0]}))
    return pd.concat(partes, ignore_index=True)


PESOS = {}

# --- 2a. Usinas (mesma alocação da v4) ---
with C.etapa(log, "Usinas: réplica da alocação v4 e verificação contra cp2b_usinas_alocacao.csv"):
    mun4674 = gpd.read_file(C.caminho("municipios"))
    mun4674["ibge"] = mun4674["CD_MUN"].astype(int)
    us = gpd.read_file(C.caminho("usinas_etanol"))
    us = us[us.UF == "SP"].to_crs(mun4674.crs)
    us = gpd.sjoin_nearest(us.to_crs(31983), mun4674[["ibge", "geometry"]].to_crs(31983), how="left",
                           max_distance=5000, distance_col="dist_m").to_crs(mun4674.crs)
    CLS = {"Menor que 1.500.000": 1.0, "Entre 1.500.000 e 2.500.000": 2.0, "Entre 2.500.000 e 3.500.000": 3.0,
           "Entre 3.500.000 e 4.500.000": 4.0, "Entre 4.500.000 e 5.500.000": 5.0, "Maior que 5.500.000": 6.5}
    us["w_cana"] = us["Classecap"].map(CLS).fillna(0)
    us["w_etanol"] = us["Cpanhm3d"].fillna(0) + us["Cphidrm3d"].fillna(0)
    us = us[us.ibge.notna()].copy()
    us["ibge"] = us["ibge"].astype(int)
    v4 = pd.read_csv(C.caminho("usinas_alocacao_v4"))
    chk = (len(v4) == len(us)) and np.allclose(v4.w_cana, us.w_cana) and np.allclose(v4.w_etanol, us.w_etanol) \
        and (v4.ibge.to_numpy() == us.ibge.to_numpy()).all()
    log.info(f"  {len(us)} usinas; idêntica à v4: {chk}")
    assert chk, "alocação de usinas diverge da v4"
    us = us.to_crs(C.CRS).reset_index(drop=True)
    us["loc"] = [novo_ponto("usina", f"usina:{i}", r.Nome, r.geometry.x, r.geometry.y, r.ibge)
                 for i, r in us.iterrows()]
    us["midx"] = us.ibge.map(midx_of)
    for cod in [s for s in SUBS if ESP[s]["fonte"] == "usina"]:
        wcol = ESP[cod]["peso"]
        a = us[["midx", "loc", wcol]].rename(columns={"loc": "cell", wcol: "w"})
        igual = us[["midx", "loc"]].rename(columns={"loc": "cell"}).assign(w=1.0)   # usinas sem capacidade informada
        PESOS[cod] = completar(cod, [a, igual], ["usina_peso", "usina_partes_iguais"])

# --- 2b. ETEs ---
with C.etapa(log, "ETEs ativas não-lagoa"):
    ete = gpd.read_file(C.caminho("etes")).to_crs(C.CRS)
    ete = ete[(ete.ETE_DS_STA == CF["etes"]["status_ativo"]) & ~ete.ETE_DS_TI.isin(CF["etes"]["tipos_lagoa"])]
    ete = ete[ete.ETE_MUN_CD.isin(midx_of)].reset_index(drop=True)
    ete["midx"] = ete.ETE_MUN_CD.map(midx_of)
    ete["loc"] = [novo_ponto("ete", f"ete:{r.ETE_CD}", r.ETE_NM, r.geometry.x, r.geometry.y, int(r.ETE_MUN_CD))
                  for _, r in ete.iterrows()]
    log.info(f"  {len(ete)} ETEs ativas não-lagoa em {ete.midx.nunique()} municípios")
    PESOS["LODO_ETE"] = completar("LODO_ETE", [ete[["midx", "loc"]].rename(columns={"loc": "cell"}).assign(w=1.0)],
                                  ["ete_partes_iguais"], prefer="urbano")

# --- 2b'. Fábricas de suco (v5.1) ---
with C.etapa(log, "Fábricas de suco concentrado (00_fabricas_suco.py): um ponto por município, no centroide urbano"):
    fab = pd.read_csv(C.caminho("fabricas_suco"))
    fab["midx"] = fab.ibge.map(midx_of)
    xy = [CENT_URB.get(m, CENT_MUN[m]) for m in fab.midx]
    fab["loc"] = [novo_ponto("fabrica_suco", f"fabrica_suco:{r.ibge}", f"fábricas de suco — {r.municipio}", x, y, int(r.ibge))
                  for r, (x, y) in zip(fab.itertuples(), xy)]
    log.info(f"  {len(fab)} municípios com fábrica ({int(fab.n_estabelecimentos.sum())} estabelecimentos); "
             f"sem área urbana (centroide municipal): {int(sum(m not in CENT_URB for m in fab.midx))}")
    for cod in [s for s in SUBS if ESP[s]["fonte"] == "fabrica_suco"]:
        PESOS[cod] = completar(cod, [fab[["midx", "loc"]].rename(columns={"loc": "cell"}).assign(w=1.0)],
                               ["fabrica_suco"], prefer="urbano")

# --- 2c. Pixels MapBiomas ---
with C.etapa(log, "Substratos por pixel (MapBiomas)"):
    for cod in [s for s in SUBS if ESP[s]["fonte"] == "pixel"]:
        cls = ESP[cod]["classes"]
        cls = cls if isinstance(cls, list) else [cls]
        partes = []
        for c in cls:
            if c == "segunda_safra_milho":
                partes.append(contagem(np.isin(LU2, MB[c])))
            else:
                partes.append(contagem(np.isin(LU, MB[c])))
        w = pd.concat(partes).groupby(["midx", "cell"], as_index=False).w.sum()
        PESOS[cod] = completar(cod, [w], ["pixel_classe"])
        log.info(f"  {cod}: classes {cls}; {len(w):,} pares município×célula")

# --- 2d. Urbano ---
with C.etapa(log, "RSU e poda por área urbana"):
    WURB = contagem(URB > 0)
    for cod in [s for s in SUBS if ESP[s]["fonte"] == "urbano"]:
        PESOS[cod] = completar(cod, [WURB], ["area_urbana"], prefer="urbano")


def municipio_ponto(nomes, x, y, fonte):
    """Município do cadastro (nome) se o ponto estiver a ≤ tolerância dele; nome sem casamento → espacial."""
    nm = pd.Series(nomes).map(lambda s: key2ibge.get(C.norm(s))).astype(float).to_numpy()
    esp = lookup_mun(x, y)
    esp_ibge = np.array([ibge_of.get(m, np.nan) for m in esp], dtype=float)
    out = np.where(pd.notna(nm), nm, esp_ibge)
    dif = pd.notna(nm) & (esp_ibge != nm)
    tol = PEC["tolerancia_municipio_km"] * 1000
    longe = np.zeros(len(x), dtype=bool)
    if dif.any():
        geo = mun.set_index("ibge").geometry
        idx = np.flatnonzero(dif)
        dist = shapely.distance(shapely.points(x[idx], y[idx]), np.asarray(geo.loc[nm[idx].astype(int)]))
        longe[idx] = dist > tol
    out[longe] = np.nan
    log.info(f"  [{fonte}] {len(x):,} pontos; nome sem casamento: {int(pd.isna(nm).sum()):,} (usado o espacial); "
             f"fora do município declarado mas ≤ {tol / 1000:.0f} km: {int((dif & ~longe).sum()):,}; "
             f"descartados (> {tol / 1000:.0f} km ou fora de SP): {int(np.isnan(out).sum()):,}")
    return out


def pontos_validos(lat, lon):
    lat = pd.to_numeric(pd.Series(lat).astype(str).str.replace(",", ".", regex=False), errors="coerce").to_numpy()
    lon = pd.to_numeric(pd.Series(lon).astype(str).str.replace(",", ".", regex=False), errors="coerce").to_numpy()
    ok = (lat > -26) & (lat < -19) & (lon > -54) & (lon < -44)
    from pyproj import Transformer

    x = np.full(len(lat), np.nan)
    y = np.full(len(lat), np.nan)
    x[ok], y[ok] = Transformer.from_crs(4326, C.CRS, always_xy=True).transform(lon[ok], lat[ok])
    return ok, x, y


# --- 2e. Aves (GEDAVE) ---
with C.etapa(log, "Aves (GEDAVE): corte e postura"):
    av = pd.read_excel(C.caminho("aves_gedave"))
    av.columns = [C.norm(c) for c in av.columns]
    cap = pd.to_numeric(av["capacidademaximaalojamento"], errors="coerce").fillna(0).to_numpy()
    ok, x, y = pontos_validos(av["latitude"], av["longitude"])
    ok &= (cap > 0) & (cap < PEC["aves_capacidade_sentinela"])
    log.info(f"  {len(av):,} estabelecimentos; válidos (coordenada em SP, 0 < capacidade < sentinela): {int(ok.sum()):,}")
    ib = municipio_ponto(av["nomemunicipio"].to_numpy()[ok], x[ok], y[ok], "aves")
    A = pd.DataFrame({"midx": pd.Series(ib).map(midx_of), "x": x[ok], "y": y[ok], "w": cap[ok],
                      "cls": av["classificacaoestabelecimento"].to_numpy()[ok]}).dropna(subset=["midx"])
    A["midx"] = A.midx.astype(int)
    todos = w_pontos(A.midx, A.x, A.y, A.w)
    for cod in [s for s in SUBS if ESP[s]["fonte"] == "aves"]:
        g = A[A.cls.isin(PEC[ESP[cod]["grupo"]])]
        log.info(f"  {cod}: {len(g):,} estabelecimentos, capacidade {g.w.sum():,.0f}")
        PESOS[cod] = completar(cod, [w_pontos(g.midx, g.x, g.y, g.w), todos], ["gedave_grupo", "gedave_qualquer_ave"])

# --- 2f. Suínos (farms_for_gee; plantel estimado, usado só como peso) ---
with C.etapa(log, "Suínos (farms_for_gee.csv)"):
    fa = pd.read_csv(C.caminho("suinos_farms"))
    fa = fa[fa.tipo_animal.map(C.norm) == "suinos"]
    ok, x, y = pontos_validos(fa.latitude, fa.longitude)
    w = pd.to_numeric(fa.plantel, errors="coerce").fillna(0).to_numpy()
    ok &= w > 0
    ib = municipio_ponto(fa.municipio.to_numpy()[ok], x[ok], y[ok], "suínos")
    S = pd.DataFrame({"midx": pd.Series(ib).map(midx_of), "x": x[ok], "y": y[ok], "w": w[ok]}).dropna(subset=["midx"])
    S["midx"] = S.midx.astype(int)
    log.info(f"  {len(S):,} granjas, plantel estimado {S.w.sum():,.0f}")
    PESOS["SUINOS"] = completar("SUINOS", [w_pontos(S.midx, S.x, S.y, S.w)], ["granjas_suinos"])

# --- 2g. Bovinos (GEDAVE, LGPD: só colunas autorizadas) ---
with C.etapa(log, "Bovinos (GEDAVE 03/11/2025; só colunas autorizadas)"):
    bov = pd.read_csv(C.caminho("bovinos_gedave"), encoding="latin-1", usecols=PEC["bovinos_colunas_lgpd"],
                      dtype=str, low_memory=False)
    saldo = pd.to_numeric(bov.SALDO_GERAL, errors="coerce").fillna(0).to_numpy()
    ok, x, y = pontos_validos(bov.LATITUDE, bov.LONGITUDE)
    ok &= saldo > 0
    log.info(f"  {len(bov):,} linhas; com rebanho > 0: {int((saldo > 0).sum()):,}; e coordenada em SP: {int(ok.sum()):,}")
    ib = municipio_ponto(bov.NOME_MUN.to_numpy()[ok], x[ok], y[ok], "bovinos")
    B = pd.DataFrame({"midx": pd.Series(ib).map(midx_of), "x": x[ok], "y": y[ok], "w": saldo[ok],
                      "fin": bov.FINALIDADE_PRINCIPAL.to_numpy()[ok], "sis": bov.SISTEMA_PRODUCAO.to_numpy()[ok]})
    B = B.dropna(subset=["midx"])
    B["midx"] = B.midx.astype(int)
    del bov
    todos = w_pontos(B.midx, B.x, B.y, B.w)
    grupos = {"leite": B.fin.isin(PEC["bov_leite_finalidade"]), "confinado": B.sis.isin(PEC["bov_confinado_sistema"])}
    for cod in [s for s in SUBS if ESP[s]["fonte"] == "bovinos"]:
        g = B[grupos[ESP[cod]["grupo"]]]
        log.info(f"  {cod}: {len(g):,} registros, rebanho {g.w.sum():,.0f}")
        PESOS[cod] = completar(cod, [w_pontos(g.midx, g.x, g.y, g.w), todos], ["gedave_grupo", "gedave_qualquer_bovino"])
    del B, g, todos

# ---------------------------------------------------------------------------
# 3. Distribuição: oferta(loc, município, substrato, cenário) = N3(m) × w / Σw(m)
# ---------------------------------------------------------------------------
with C.etapa(log, "Distribuição do N3 e verificação de fechamento"):
    partes = []
    for cod in SUBS:
        W = PESOS[cod].groupby(["midx", "cell"], as_index=False).w.sum()
        W["share"] = W.w / W.groupby("midx").w.transform("sum")
        W["ibge"] = W.midx.map(ibge_of)
        for sc in C.SC:
            n3 = W.ibge.map(N3[(cod, sc)])
            partes.append(pd.DataFrame({"loc": W.cell.to_numpy(), "ibge": W.ibge.to_numpy(), "codigo": cod,
                                        "cenario": sc, "oferta": (n3 * W.share).to_numpy()}))
    OF = pd.concat(partes, ignore_index=True)
    OF = OF[OF.oferta > 0]
    OFw = OF.pivot_table(index=["loc", "ibge"], columns=["codigo", "cenario"], values="oferta", aggfunc="sum").fillna(0.0)
    OFw.columns = [f"{a}__{b}" for a, b in OFw.columns]
    OFw = OFw.reset_index()
    # verificação estadual e municipal
    tot_m = N3.sum()
    tot_g = OF.groupby(["codigo", "cenario"]).oferta.sum()
    V = pd.DataFrame({"municipal_m3dia": tot_m, "grade_m3dia": tot_g}).fillna(0.0)
    V.index.names = ["codigo", "cenario"]
    V["dif_rel"] = (V.grade_m3dia - V.municipal_m3dia) / V.municipal_m3dia.where(V.municipal_m3dia > 0)
    V["espacializado"] = [c in SUBS for c in V.index.get_level_values(0)]
    pm = OF.groupby(["ibge", "codigo", "cenario"]).oferta.sum()
    ref = N3.melt(ignore_index=False, value_name="n3").reset_index().set_index(["ibge", "codigo", "cenario"]).n3
    ref = ref[ref.index.get_level_values("codigo").isin(SUBS)]
    dm = (pm.reindex(ref.index).fillna(0) - ref).abs() / ref.where(ref > 0)
    max_dif_mun = float(dm.max())
    tol = CF["tolerancia_fechamento"]
    ok_est = bool((V.loc[V.espacializado, "dif_rel"].abs().fillna(0) <= tol).all())
    log.info(f"  fechamento estadual ≤ {tol:.2%}: {ok_est}; maior desvio municipal: {max_dif_mun:.2e}")
    assert ok_est and max_dif_mun <= tol
    V.round(6).to_csv(C.OUT / "oferta_totais_verificacao.csv", encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 4. Locais e gravação
# ---------------------------------------------------------------------------
with C.etapa(log, "Locais (células e pontos) e gravação"):
    PT = pd.DataFrame(PONTOS)
    cells = np.unique(OFw.loc[OFw["loc"] >= 0, "loc"])
    cx, cy = G1.centro(cells)
    LOC = pd.concat([pd.DataFrame({"loc": cells, "tipo": "celula", "ref": "", "nome": "", "x": cx, "y": cy}),
                     PT[PT["loc"].isin(OFw["loc"])].drop(columns="ibge")], ignore_index=True)
    LOC["cell1k"] = G1.ids(LOC.x, LOC.y)
    LOC.to_pickle(C.CACHE / "oferta_locais.pkl")
    OFw.to_pickle(C.CACHE / "oferta_wide.pkl")
    PT.to_pickle(C.CACHE / "pontos_fonte.pkl")
    FB = pd.DataFrame(FALLBACK).drop_duplicates()
    FB["municipio"] = FB.ibge.map(dict(zip(mun.ibge, mun.municipio)))
    FB["N3_med_m3dia"] = [N3.at[i, (c, "med")] for i, c in zip(FB.ibge, FB.codigo)]
    FB.sort_values(["codigo", "nivel", "N3_med_m3dia"], ascending=[True, True, False]).to_csv(
        C.OUT / "oferta_fallback_casos.csv", index=False, encoding="utf-8-sig")
    cols = [c for c in OFw.columns if "__" in c]
    ag = OFw[OFw["loc"] >= 0].groupby("loc")[cols].sum()
    gcel = gpd.GeoDataFrame(ag.reset_index(), geometry=G1.poligonos(ag.index.to_numpy()), crs=C.CRS)
    gcel = gcel.rename(columns={"loc": "cell_id"})
    (C.OUT / "grade_oferta_1km.gpkg").unlink(missing_ok=True)
    gcel.to_file(C.OUT / "grade_oferta_1km.gpkg", layer="celulas", driver="GPKG")
    ap = OFw[OFw["loc"] < 0].groupby("loc")[cols].sum().reset_index().merge(PT, on="loc")
    gpt = gpd.GeoDataFrame(ap.drop(columns=["x", "y"]), geometry=gpd.points_from_xy(ap.x, ap.y), crs=C.CRS)
    gpt.to_file(C.OUT / "grade_oferta_1km.gpkg", layer="pontos", driver="GPKG")
    log.info(f"  {len(cells):,} células com oferta; {len(ap)} pontos (usinas/ETEs/fábricas de suco); {len(OFw):,} linhas local×município")

# ---------------------------------------------------------------------------
# 5. Mapas rápidos (palha, aves, lodo) — med
# ---------------------------------------------------------------------------
with C.etapa(log, "Mapas rápidos"):
    contorno = mun.dissolve().boundary
    ext = (G1.x0, G1.x0 + G1.nx * G1.passo, G1.y0, G1.y0 + G1.ny * G1.passo)

    def raster_1km(cols_):
        s = OFw[OFw["loc"] >= 0].groupby("loc")[cols_].sum().sum(axis=1)
        s = s[s > 0]
        a = np.full(NCELL, np.nan)
        a[s.index.to_numpy()] = s.to_numpy()
        return np.flipud(a.reshape(G1.ny, G1.nx))

    def mapa(arr, titulo, arq, pts=None):
        fig, ax = plt.subplots(figsize=(11, 7.2), dpi=150)
        mun.boundary.plot(ax=ax, color="#bbbbbb", linewidth=0.15)
        if arr is not None:
            v = np.sort(arr[np.isfinite(arr) & (arr > 0)])
            vmin = v[np.searchsorted(np.cumsum(v) / v.sum(), 0.01)]      # abaixo de vmin: só 1% da oferta
            im = ax.imshow(arr, extent=ext, origin="upper", cmap="viridis",
                           norm=LogNorm(vmin=vmin, vmax=v.max(), clip=True), interpolation="nearest")
            fig.colorbar(im, ax=ax, shrink=0.7, extend="min",
                         label="N3 med, Nm³ CH4/dia por célula de 1 km² (escala cortada: abaixo = 1% da oferta)")
        if pts is not None:
            for (lab, d, cor, mk) in [p for p in pts if len(p[1])]:
                ax.scatter(d.x, d.y, s=np.clip(d.v / d.v.max() * 120, 3, 120), c=cor, marker=mk, alpha=0.75,
                                 edgecolors="k", linewidths=0.2, label=lab)
            ax.legend(loc="lower left", fontsize=8)
        contorno.plot(ax=ax, color="k", linewidth=0.5)
        ax.set_title(titulo, fontsize=11)
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(C.FIG / arq)
        plt.close(fig)

    mapa(raster_1km(["PALHA__med"]), "Palha de cana — N3 (med) espacializado pelos pixels de cana (MapBiomas 2024)",
         "oferta_palha_med.png")
    mapa(raster_1km(["AVES_CORTE__med", "AVES_POSTURA__med"]),
         "Aves (corte + postura) — N3 (med) pelos estabelecimentos GEDAVE, agregado em 1 km", "oferta_aves_med.png")
    lod = OFw[["loc", "LODO_ETE__med"]].groupby("loc").sum().reset_index().rename(columns={"LODO_ETE__med": "v"})
    lod = lod[lod.v > 0]
    lp = lod[lod["loc"] < 0].merge(PT[["loc", "x", "y"]], on="loc")
    lc = lod[lod["loc"] >= 0].copy()
    lc["x"], lc["y"] = G1.centro(lc["loc"].to_numpy())
    mapa(None, "Lodo de ETE — N3 (med): partes iguais entre ETEs ativas não-lagoa; ▲ = fallback (centroide urbano)",
         "oferta_lodo_med.png", pts=[("ETE ativa não-lagoa", lp, "#1f77b4", "o"), ("fallback", lc, "#d62728", "^")])

log.info("Etapa 2 concluída.")
