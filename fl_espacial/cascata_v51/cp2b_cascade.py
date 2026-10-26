#!/usr/bin/env python3
"""Método CP2b v5 — cascata teórico → técnico → mobilizável → acessível (SP, 645 municípios).

Base volumétrica primária: Nm³ CH4. Biogás e biometano são derivados e rotulados.
v5: substratos com FL="espacial" usam o FL por município × cenário de fl_espacial/ (P.FL_ESPACIAL); saída em
P.PASTA_SAIDA (outputs_v5/), sem tocar em outputs/ da v4. Ambiente: Metodo_CP2b/requirements.txt (pandas 2.2).
v5.1: bagaço de citros nas fábricas de suco (laranja PAM total × peso RAIS de fl_espacial/00_fabricas_suco.py).
Executar:  python cp2b_cascade.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

import cp2b_params as P

HERE = Path(__file__).resolve().parent
ESD = HERE.parent
MNT = ESD.parent
PRIM = ESD / "00_Primary_Data_Sources_PILAR2b"
RES = ESD / "Resultados em Mapas-20260807T123054Z-1-001" / "analysis"
BENCH = ESD / "Benchmarks_Brasil"
REPO = MNT / "Pilar2b" / "cp2b-workspace" / "NewLook"
MASTER = REPO / "data" / "canonical_parameters" / "SP_master_residue_streams_2023_FINAL.csv"
YAML = REPO / "data" / "canonical_parameters" / "feedstocks.yaml"
SHP = REPO / "backend" / "data" / "shapefiles"
INFRA = PRIM / "SHAPEFILES_MAPBIOMAS_10.1" / "INFRAESTRUTURA"
OUT = HERE / getattr(P, "PASTA_SAIDA", "outputs")
OUT.mkdir(parents=True, exist_ok=True)
SC = ["min", "med", "max"]
DAYS = 365
ANO = P.ANO_PAM_PPM


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"\s*\((SP)\)\s*$|\s*-\s*SP$", "", s.strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                         errors="coerce")


# ---------------------------------------------------------------------------
# 0. Parâmetros
# ---------------------------------------------------------------------------
Y = yaml.safe_load(open(YAML, encoding="utf-8"))["feedstocks"]


def tri(d, scale=1.0):
    return {"min": d["min"] * scale, "med": d["medio"] * scale, "max": d["max"] * scale}


def resolve(sub):
    r = dict(sub)
    if "direto" not in sub:
        if isinstance(sub["g"], str):
            gb = Y[sub["g"]]["generation"]
            r["g"] = tri(gb["t_per_head_yr"] if "t_per_head_yr" in gb else gb["t_per_capita_yr"])
        v = Y[sub["yaml"]]
        q = sub.get("quim_override", {})
        r["ST"] = q.get("ST") or sub.get("ts_override") or tri(v["ts"], 0.01)
        r["SV"] = q.get("SV") or tri(v["vs_of_ts"], 0.01)
        r["BMP"] = q.get("BMP") or tri(v["bmp"])
    fl = sub["FL"]
    if fl == "espacial":   # v5: FL municipal vem de fl_espacial/; o do yaml fica como referência
        r["FL_espacial"] = True
        code = sub.get("FL_ref") or sub["yaml"]
    else:
        code = sub["yaml"] if fl == "yaml" else fl
    r["FL"] = tri(Y[code]["fde"]["components"]["fl"]) if isinstance(code, str) else fl
    return r


SUBS = [resolve(s) for s in P.SUBSTRATOS]

rows = []
for s in SUBS:
    for e in (["direto"] if "direto" in s else ["g", "ST", "SV", "BMP"]) + ["FC", "FCo", "FS", "FL"]:
        v = s[e]
        unid = {"g": s.get("g_unid"), "direto": s.get("g_unid"), "ST": "fração", "SV": "fração de ST",
                "BMP": "Nm³ CH4 / t SV"}.get(e, "fração")
        fonte = s.get(f"fonte_{e}") or ("feedstocks.yaml" if e in ("ST", "SV", "BMP", "FL") else "cp2b")
        if e in ("ST", "SV", "BMP") and (s.get("quim_override") or (e == "ST" and s.get("ts_override"))):
            fonte = "override cp2b: " + s.get("nota_quim", "")
        if e == "FL" and s.get("FL_espacial"):
            fonte = (f"espacial ({P.FL_ESPACIAL['variante']}), por município: {P.FL_ESPACIAL['arquivo']}; "
                     "valores mostrados = feedstocks.yaml (referência v4)")
        if isinstance(v, str):
            rows.append(dict(codigo=s["codigo"], fluxo=s["fluxo"], elemento=e, min=None, med=None, max=None,
                             unidade="municipal", fonte=fonte, status=s["status"]))
        else:
            rows.append(dict(codigo=s["codigo"], fluxo=s["fluxo"], elemento=e, min=v["min"], med=v["med"], max=v["max"],
                             unidade=unid, fonte=fonte, status=s["status"]))
    rows.append(dict(codigo=s["codigo"], fluxo=s["fluxo"], elemento="u (usos excludentes) / notas", min=None, med=None,
                     max=None, unidade="texto", fonte=s["u"], status=s["status"]))
pd.DataFrame(rows).to_csv(OUT / "cp2b_parametros_BASISDATEN.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 1. Base municipal
# ---------------------------------------------------------------------------
mun = gpd.read_file(SHP / "SP_Municipios_2024.shp")
mun["ibge"] = mun["CD_MUN"].astype(int)
A = pd.DataFrame({"ibge": mun["ibge"], "municipio": mun["NM_MUN"], "rgint": mun["CD_RGINT"].astype(int),
                  "nome_rgint": mun["NM_RGINT"]})
A["key"] = A["municipio"].map(norm)
key2ibge = dict(zip(A["key"], A["ibge"]))
m = pd.read_csv(MASTER).rename(columns={"CD_GEOCODI": "ibge"})
A = A.merge(m[["ibge", "populacao_total_hab", "pop_atendida_coleta_hab", "rdo_rpu_coletado_t"]], on="ibge", how="left")
A["pop"] = A["populacao_total_hab"].fillna(0)

# PAM 2024
pam = pd.read_csv(PRIM / "PAM_1612_1613_2008_2024_long.csv")
pam = pam[(pam.year == ANO) & (pam.ibge_code // 100000 == 35)]
pam_conf = int((pam.flag == "confidential").sum())
pw = pam.pivot_table(index="ibge_code", columns="crop", values="production_tons", aggfunc="sum").fillna(0)
pw = pw.rename(columns={"sugarcane": "cana_t", "corn": "milho_t", "soybean": "soja_t", "coffee": "cafe_t",
                        "citrus": "laranja_t"})
A = A.merge(pw, left_on="ibge", right_index=True, how="left")


# PPM 3939 2024
def ppm_table(fname, year, skip=4):
    t = pd.read_excel(PRIM / "04_IBGE_Tabelas" / fname, header=None) if "3939" in fname else \
        pd.read_excel(PRIM / fname, header=None)
    yr = t.iloc[3].ffill()
    return t, yr


t39, yr39 = ppm_table("TABELA_3939_PPM_2008A2024.xlsx", ANO)
cols = {}
for i in range(t39.shape[1]):
    if str(yr39[i]).startswith(str(ANO)):
        cols[str(t39.iloc[4, i]).strip()] = i
ppm = t39.iloc[5:, [1] + [cols[k] for k in ["Bovino", "Suíno - total", "Galináceos - total", "Galináceos - galinhas"]]].copy()
ppm.columns = ["ibge", "bov_total", "suinos_cab", "galinaceos_total", "galinhas"]
ppm = ppm[pd.to_numeric(ppm.ibge, errors="coerce").notna()]
ppm["ibge"] = ppm["ibge"].astype(int)
for c in ppm.columns[1:]:
    ppm[c] = pd.to_numeric(ppm[c], errors="coerce").fillna(0)
A = A.merge(ppm, on="ibge", how="left")

t94 = pd.read_excel(PRIM / "TABELA_94_VACAS_ORDENHADAS_PPM_2008_A2024.xlsx", header=None)
c94 = [i for i in range(t94.shape[1]) if str(t94.iloc[3, i]) == str(ANO)][0]
vac = t94.iloc[4:, [1, c94]].copy()
vac.columns = ["ibge", "vacas_ordenhadas"]
vac = vac[pd.to_numeric(vac.ibge, errors="coerce").notna()]
vac["ibge"] = vac["ibge"].astype(int)
vac["vacas_ordenhadas"] = pd.to_numeric(vac["vacas_ordenhadas"], errors="coerce").fillna(0)
A = A.merge(vac, on="ibge", how="left")
A = A.fillna({c: 0 for c in ["cana_t", "milho_t", "soja_t", "cafe_t", "laranja_t", "bov_total", "suinos_cab",
                             "galinaceos_total", "galinhas", "vacas_ordenhadas"]})

# Bovinos por sistema (GEDAVE agregado, sem dados pessoais)
gb = pd.read_csv(HERE / "inputs" / "gedave_bovinos_agregado_municipio_sistema.csv")
gb["ibge"] = gb["NOME_MUN"].map(lambda x: key2ibge.get(norm(x)))
gb_nm = gb[gb.ibge.isna()].NOME_MUN.unique().tolist()
conf = gb[gb.SISTEMA_PRODUCAO == "Confinado"].groupby("ibge").cabecas.sum()
A["bov_conf_gedave"] = A["ibge"].map(conf).fillna(0)
A["bov_leite_cab"] = np.minimum(A["vacas_ordenhadas"], A["bov_total"])
A["bov_conf_cab"] = np.minimum(A["bov_conf_gedave"], (A["bov_total"] - A["bov_leite_cab"]).clip(lower=0))
A["bov_pasto_cab"] = (A["bov_total"] - A["bov_leite_cab"] - A["bov_conf_cab"]).clip(lower=0)

# Aves corte × postura
A["aves_postura_cab"] = np.minimum(A["galinhas"], A["galinaceos_total"])
A["aves_corte_cab"] = (A["galinaceos_total"] - A["aves_postura_cab"]).clip(lower=0)

# Usinas (EPE 2018 via MapBiomas): cana moída e etanol UNICA 2020/21 alocados às usinas
us = gpd.read_file(next((INFRA / "structure_ethanol_plant").glob("*.shp")))
us = us[us.UF == "SP"].to_crs(mun.crs)
us = gpd.sjoin_nearest(us.to_crs(31983), mun[["ibge", "geometry"]].to_crs(31983), how="left",
                       max_distance=5000, distance_col="dist_m").to_crs(mun.crs)  # pontos na divisa/costa
CLS = {"Menor que 1.500.000": 1.0, "Entre 1.500.000 e 2.500.000": 2.0, "Entre 2.500.000 e 3.500.000": 3.0,
       "Entre 3.500.000 e 4.500.000": 4.0, "Entre 4.500.000 e 5.500.000": 5.0, "Maior que 5.500.000": 6.5}
us["w_cana"] = us["Classecap"].map(CLS).fillna(0)
us["w_etanol"] = us["Cpanhm3d"].fillna(0) + us["Cphidrm3d"].fillna(0)
usinas_sem_mun = int(us.ibge.isna().sum())
us = us[us.ibge.notna()]
us["ibge"] = us["ibge"].astype(int)
wc = us.groupby("ibge").w_cana.sum() / us.w_cana.sum()
we = us.groupby("ibge").w_etanol.sum() / us.w_etanol.sum()
CM, ET = P.GLOBAIS["cana_moida_SP_t"], P.GLOBAIS["etanol_SP_m3"]
A["cana_moida_t"] = A["ibge"].map(wc).fillna(0) * CM["med"]
A["etanol_m3"] = A["ibge"].map(we).fillna(0) * ET["med"]
A["n_usinas"] = A["ibge"].map(us.groupby("ibge").size()).fillna(0).astype(int)
escala = {"cana_moida_t": {s: CM[s] / CM["med"] for s in SC}, "etanol_m3": {s: ET[s] / ET["med"] for s in SC}}
us[["Nome", "Cidade", "ibge", "Tipo", "Situacao", "Classecap", "w_cana", "w_etanol"]].to_csv(
    OUT / "cp2b_usinas_alocacao.csv", index=False, encoding="utf-8-sig")

# Fábricas de suco (v5.1): laranja da PAM (total SP) alocada às fábricas de suco concentrado ∝ vínculos RAIS
# (fl_espacial/00_fabricas_suco.py). O bagaço de citros é resíduo da extração do suco, não do pomar.
fab = pd.read_csv(HERE / P.FL_ESPACIAL["fabricas_suco"])
wf = fab.set_index("ibge").w
assert abs(wf.sum() - 1) < 1e-9 and wf.index.isin(A.ibge).all()
A["laranja_fabrica_t"] = A["ibge"].map(wf).fillna(0) * A["laranja_t"].sum()

# SNIS 2022 (arquivo tem uma coluna a mais por linha que o cabeçalho → index_col=False)
snis = pd.read_csv(PRIM / "03_SNIS_Series" / "2022_SNIS_ConsolidadoMunicipio-20260716124911.csv", sep=";",
                   encoding="utf-16-le", low_memory=False, index_col=False, dtype=str)
col = lambda p: [c for c in snis.columns if c.startswith(p)][0]
sn = pd.DataFrame({"ibge": pd.to_numeric(snis[col("Código do IBGE")], errors="coerce"),
                   "co119": num(snis[col("CO119")]), "co164": num(snis[col("CO164")]),
                   "in016": num(snis[col("IN016_AE")]), "in056": num(snis[col("IN056_AE")])})
sn = sn.dropna(subset=["ibge"])
sn["ibge"] = sn["ibge"].astype(int)
sn = sn.groupby("ibge", as_index=False).max()
A = A.merge(sn, on="ibge", how="left")

# RSU: massa coletada SNIS 2022 (CO119); lacunas → master; lacunas → per capita (Atlas) × cobertura mediana
def kg_dia(p):
    for lim, v in P.GLOBAIS["rsu_kg_hab_dia_faixas"]:
        if p <= lim:
            return v
rsu = A["co119"].where(A["co119"] > 0)
A["fonte_rsu"] = np.where(rsu.notna(), "SNIS 2022 CO119", "")
m_rsu = A["rdo_rpu_coletado_t"].where(A["rdo_rpu_coletado_t"] > 0)
A.loc[rsu.isna() & m_rsu.notna(), "fonte_rsu"] = "master SNIS"
rsu = rsu.fillna(m_rsu)
cov = (A["co164"].where(A["co164"] > 0) / A["pop"]).clip(0, 1)
cov = cov.fillna((A["pop_atendida_coleta_hab"].where(A["pop_atendida_coleta_hab"] > 0) / A["pop"]).clip(0, 1))
pc = A["pop"].map(kg_dia) * A["pop"] * DAYS / 1000 * cov.fillna(cov.median())
A.loc[rsu.isna(), "fonte_rsu"] = "per capita Atlas × cobertura"
A["rsu_coletado_t"] = rsu.fillna(pc)

# Esgoto: atendimento × tratamento × fração de ETEs compatíveis com digestão (não-lagoa, ativas)
ete = gpd.read_file(SHP / "ETEs_2019_SP.shp")
ete = ete[ete.ETE_DS_STA == "Ativa"]
ete["ad"] = ~ete["ETE_DS_TI"].isin(["Sistemas de Lagoas", "Processos Simplificados"])
fad = ete.groupby("ETE_MUN_CD").ad.mean()
A["frac_ete_digestao"] = A["ibge"].map(fad)
A["fonte_ete"] = np.where(A.frac_ete_digestao.notna(), "ANA/Atlas Esgotos 2019 (contagem)", "média estadual")
A["frac_ete_digestao"] = A["frac_ete_digestao"].fillna(ete.ad.mean())
esg = (A["in056"] / 100).clip(0, 1) * (A["in016"] / 100).clip(0, 1)
A["indice_tratamento"] = esg.fillna(esg.median())
A["esgoto_fc"] = A["indice_tratamento"] * A["frac_ete_digestao"]

# GEDAVE aves: fração da capacidade em área de atuação Comercial ou Reprodução
av = pd.read_excel(PRIM / "Relatorio_0082803826_granjas_aves_UNICAMP.xlsx")
av["cap"] = pd.to_numeric(av["Capacidade Máxima Alojamento"], errors="coerce").fillna(0)
av = av[av.cap < 9_999_999]
av["com"] = av["Área se Atuação Estabelecimento"].isin(["Comercial", "Reprodução"])
av["ibge"] = av["Nome Município"].map(lambda x: key2ibge.get(norm(x)))
ga = av.groupby("ibge").apply(lambda d: d.loc[d.com, "cap"].sum() / d.cap.sum() if d.cap.sum() > 0 else np.nan,
                              include_groups=False)
share_est = av.loc[av.com, "cap"].sum() / av.cap.sum()
A["aves_share_com"] = A["ibge"].map(ga).fillna(share_est)


def fc_municipal(tag, s):
    if tag == "aves_fc":
        return (A["aves_share_com"] * P.AVES_COLETA[s]).clip(0, 1)
    if tag == "esgoto_fc":
        return A["esgoto_fc"].clip(0, 1)
    raise KeyError(tag)


# FL espacial (v5): FL por município × substrato × cenário; município sem oferta (N3 = 0) usa o FL estadual
FLESP = {}
if any(s.get("FL_espacial") for s in SUBS):
    fe = pd.read_csv(HERE / P.FL_ESPACIAL["arquivo"])
    fe_est = pd.read_csv(HERE / P.FL_ESPACIAL["arquivo_estado"]).set_index(["codigo", "cenario"])
    colfl = {"codig_alocado": "FL_codig_alocado", "codigestao": "FL_codigestao", "mono": "FL_mono",
             "mono_alocado": "FL_mono_alocado"}[P.FL_ESPACIAL["variante"]]
    for (c, sc), g in fe.groupby(["codigo", "cenario"]):
        FLESP[(c, sc)] = A["ibge"].map(g.set_index("ibge")[colfl]).fillna(fe_est.at[(c, sc), colfl]).to_numpy()

# ---------------------------------------------------------------------------
# 2. Cascata N1–N3a
# ---------------------------------------------------------------------------
recs = []
for s in SUBS:
    act = A[s["atividade"]].astype(float)
    for sc in SC:
        k = escala.get(s["atividade"], {}).get(sc, 1.0)
        if "direto" in s:
            p1 = act * k * s["direto"][sc]
        else:
            p1 = act * k * s["g"][sc] * s["ST"][sc] * s["SV"][sc] * s["BMP"][sc]
        fc = fc_municipal(s["FC"].split(":")[1], sc) if isinstance(s["FC"], str) else s["FC"][sc]
        p2 = p1 * fc
        fl = FLESP.get((s["codigo"], sc), s["FL"][sc]) if s.get("FL_espacial") else s["FL"][sc]
        recs.append(pd.DataFrame({"ibge": A["ibge"], "rgint": A["rgint"], "codigo": s["codigo"], "fluxo": s["fluxo"],
                                  "setor": s["setor"], "lignocel": s["lignocel"], "cenario": sc, "L1": p1, "L2": p2,
                                  "L3a": p2 * s["FCo"][sc], "FSxFL": s["FS"][sc] * fl}))
L = pd.concat(recs, ignore_index=True)

# ---------------------------------------------------------------------------
# 3. Uso energético existente (U)
# ---------------------------------------------------------------------------
G = P.GLOBAIS
ibge2rg = dict(zip(A["ibge"], A["rgint"]))
kw2ch4 = G["fator_capacidade_ute"] * 8760 / (G["pci_ch4_kwh_m3"] * G["eta_eletrica"])
usos = []
plants = pd.read_csv(RES / "data" / "05_biogas_plants_brazil.csv")
plants = plants[plants.uf == "SP"]
vol = pd.read_csv(RES / "data" / "05e_anp_biometano_plant_volume_monthly.csv")
vol = vol[vol.uf == "SP"]
vol["date"] = pd.to_datetime(vol["date"])
v12 = vol[vol.date > vol.date.max() - pd.DateOffset(months=12)].groupby("plant_id").vol_biogas_m3d.mean()
FEED = {"landfill_gas": ("rsu", "aterro"), "msw_forsu": ("rsu", "aterro"), "sewage_sludge": ("sewage", "esgoto"),
        "vinasse_filtercake": ("sugarcane", "agro"), "vinasse_filtercake_manure": ("sugarcane", "agro")}
RECLASS = {"sp_zeg_jambeiro": ("rsu", "aterro", "aterro Engep/Multilixo, biometano ZEG — confirmado 23/09"),
           "sp_cri_geo_elias_fausto": (None, None, "resíduos industriais — fora dos fluxos (confirmado 23/09)")}
for _, r in plants.iterrows():
    if r.plant_id not in v12.index:
        continue
    fluxo, tipo = FEED.get(r.feedstock, (None, None))
    nota = "ANP, média 12 meses do biogás processado"
    if r.plant_id in RECLASS:
        fluxo, tipo, n2 = RECLASS[r.plant_id]
        nota += "; " + n2
    ch4 = v12[r.plant_id] * DAYS * (G["ch4_frac_biogas"][tipo] if tipo else 0.55)
    usos.append(dict(origem="ANP", planta=r.plant_name, municipio=r.municipality, fluxo=fluxo, ch4_m3_ano=ch4, nota=nota))

siga = pd.read_csv(BENCH / "siga-empreendimentos-geracao.csv", sep=";", encoding="utf-8", low_memory=False)
for c in siga.select_dtypes("object"):
    siga[c] = siga[c].astype(str).map(lambda x: x.encode("latin-1", "ignore").decode("utf-8", "ignore") if "Ã" in x else x)
siga = siga[(siga.SigUFPrincipal == "SP") & (siga.DscFaseUsina == "Operação") &
            siga.NomFonteCombustivel.str.contains("Biog", case=False, na=False)].copy()
siga["kw"] = pd.to_numeric(siga.MdaPotenciaFiscalizadaKw.astype(str).str.replace(",", "."), errors="coerce")
SMAP = {"Biogás - RU": "rsu", "Biogás-AGR": "sugarcane", "Biogás - RA": "livestock"}
for _, r in siga.iterrows():
    fluxo = SMAP.get(r.NomFonteCombustivel.strip())
    nota = "SIGA/ANEEL, potência fiscalizada × FC 0,70 ÷ (9,97 kWh/m³ × η 0,35)"
    if "Springer" in r.NomEmpreendimento:
        fluxo, nota = None, nota + "; levedura (indústria) — fora do escopo"
    if "São João" in r.NomEmpreendimento:
        nota += "; antigo Aterro São João (Leste/SP), RSU — confirmado 23/09"
    usos.append(dict(origem="SIGA", planta=r.NomEmpreendimento, municipio=r.DscMuninicpios.split(",")[0],
                     fluxo=fluxo, ch4_m3_ano=r.kw * kw2ch4, nota=nota))
gd = pd.read_csv(RES / "data" / "05g_aneel_biogas_gd_plants.csv")
gd = gd[gd.uf == "SP"]
GMAP = {"animal_manure_agro": "livestock", "msw_landfill": "rsu", "agricultural_residues": "sugarcane"}
for _, r in gd.iterrows():
    fl_gd = None if "CRI GEO" in str(r.operator).upper() else GMAP.get(r.feedstock)
    usos.append(dict(origem="ANEEL GD", planta=r.operator, municipio=r.municipality, fluxo=fl_gd,
                     ch4_m3_ano=r.elec_capacity_kw * kw2ch4 * (0.5 / G["fator_capacidade_ute"]),
                     nota="ANEEL GD, FC 0,50", ibge=r.ibge_code))
U = pd.DataFrame(usos)
if "ibge" not in U:
    U["ibge"] = np.nan
U["ibge"] = U["ibge"].fillna(U["municipio"].map(lambda x: key2ibge.get(norm(x))))
U["rgint"] = U["ibge"].map(ibge2rg)
U.to_csv(OUT / "cp2b_uso_energetico_existente.csv", index=False, encoding="utf-8-sig")

# Alocação: pecuária e cana (resíduo já está na usina) no município da planta; RSU e lodo na região
# intermediária (aterros/ETEs recebem de vários municípios). Fallback: região intermediária.
L["U"] = 0.0
med = L[L.cenario == "med"]
nao_alocado, alocacoes = 0.0, []
for _, u in U[U.fluxo.notna() & U.ibge.notna()].iterrows():
    fl = ["swine", "cattle", "poultry"] if u.fluxo == "livestock" else [u.fluxo]
    nivel = "municipio" if u.fluxo in ("livestock", "sugarcane") else "rgint"
    base = med[(med.ibge == u.ibge) & med.fluxo.isin(fl)] if nivel == "municipio" else \
        med[(med.rgint == u.rgint) & med.fluxo.isin(fl)]
    if base.L3a.sum() <= 0 and nivel == "municipio":
        nivel = "rgint"
        base = med[(med.rgint == u.rgint) & med.fluxo.isin(fl)]
    tot = base.L3a.sum()
    if tot <= 0:
        nao_alocado += u.ch4_m3_ano
        continue
    alocacoes.append(dict(planta=u.planta, fluxo=u.fluxo, nivel=nivel, ch4=u.ch4_m3_ano))
    wmap = dict(zip(zip(base.ibge, base.codigo), base.L3a / tot))
    keys = list(zip(L.ibge, L.codigo))
    L["U"] += np.array([wmap.get(k, 0.0) for k in keys]) * u.ch4_m3_ano

L["L3"] = (L["L3a"] - L["U"]).clip(lower=0)
L["U_efetivo"] = L["L3a"] - L["L3"]
L["L4"] = L["L3"] * L["FSxFL"]

# Bases derivadas
ych4 = {s_["codigo"]: (P.GLOBAIS["vinhaca_ch4_no_biogas"]["med"] if s_["codigo"] == "VINHACA"
                       else Y[s_["yaml"]]["ch4_pct"] / 100) for s_ in SUBS}
L["y_CH4_biogas"] = L["codigo"].map(ych4)
pur, slip = P.GLOBAIS["biometano_pureza_CH4"]["med"], P.GLOBAIS["perda_metano_upgrading"]["med"]
for lv_ in ["L1", "L2", "L3", "L4"]:
    L[f"{lv_}_biogas_eq"] = L[lv_] / L["y_CH4_biogas"]
    L[f"{lv_}_biometano_eq"] = L[lv_] * (1 - slip) / pur
L.rename(columns={c: f"{c}_CH4" for c in ["L1", "L2", "L3a", "L3", "L4", "U", "U_efetivo"]}).to_csv(
    OUT / "cp2b_municipio_substrato.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 4. Agregações
# ---------------------------------------------------------------------------
lv = ["L1", "L2", "L3a", "L3", "L4"]
est = L.groupby("cenario")[lv + ["U_efetivo"]].sum().T / 1e9
est_sem = L[~L.lignocel].groupby("cenario")[lv].sum().T / 1e9
fx = L[L.cenario == "med"].groupby("fluxo")[lv + ["U_efetivo"]].sum() / 1e9
fx["ret_L3_%"] = 100 * fx.L3 / fx.L1
fx["share_L3_%"] = 100 * fx.L3 / fx.L3.sum()
sub = L[L.cenario == "med"].groupby(["fluxo", "codigo"])[lv].sum() / 1e9
mw = L.pivot_table(index="ibge", columns="cenario", values=["L1", "L2", "L3", "L4"], aggfunc="sum")
mw.columns = [f"{a}_CH4_{b}" for a, b in mw.columns]
ms = L[~L.lignocel].pivot_table(index="ibge", columns="cenario", values=["L3", "L4"], aggfunc="sum")
ms.columns = [f"{a}_CH4_{b}_sem_lignocel" for a, b in ms.columns]
mw = A[["ibge", "municipio", "rgint", "nome_rgint"]].merge(mw.reset_index(), on="ibge").merge(ms.reset_index(), on="ibge")
mw.to_csv(OUT / "cp2b_municipio_resumo.csv", index=False, encoding="utf-8-sig")
est.to_csv(OUT / "cp2b_estado_niveis_bi_Nm3CH4_ano.csv", encoding="utf-8-sig")
est_sem.to_csv(OUT / "cp2b_estado_niveis_sem_lignocel_bi_Nm3CH4_ano.csv", encoding="utf-8-sig")
fx.to_csv(OUT / "cp2b_estado_por_fluxo_med.csv", encoding="utf-8-sig")
sub.to_csv(OUT / "cp2b_estado_por_substrato_med.csv", encoding="utf-8-sig")
A.drop(columns=["key"]).to_csv(OUT / "cp2b_atividade_municipal.csv", index=False, encoding="utf-8-sig")
bases = []
md = L[L.cenario == "med"]
for lv_ in ["L1", "L2", "L3", "L4"]:
    ch4 = md[lv_].sum()
    bases.append({"nivel": lv_, "CH4_bi_Nm3_ano": ch4 / 1e9, "CH4_M_Nm3_dia": ch4 / DAYS / 1e6,
                  "biogas_eq_M_Nm3_dia": md[f"{lv_}_biogas_eq"].sum() / DAYS / 1e6,
                  "biometano_eq_M_Nm3_dia": md[f"{lv_}_biometano_eq"].sum() / DAYS / 1e6,
                  "y_CH4_medio_ponderado": ch4 / md[f"{lv_}_biogas_eq"].sum(),
                  "eletricidade_GWh_ano": ch4 * G["pci_ch4_kwh_m3"] * G["eta_eletrica_motor"]["med"] / 1e6})
pd.DataFrame(bases).to_csv(OUT / "cp2b_bases_volumetricas_med.csv", index=False, encoding="utf-8-sig")

diag = {
    "ano_PAM_PPM": ANO, "municipios": int(A.ibge.nunique()), "pam_celulas_confidenciais": pam_conf,
    "cana_PAM_t": int(A.cana_t.sum()), "cana_moida_UNICA_t": int(A.cana_moida_t.sum()),
    "etanol_UNICA_m3": int(A.etanol_m3.sum()), "usinas_SP": int(len(us)), "usinas_sem_municipio": usinas_sem_mun,
    "municipios_com_usina": int((A.n_usinas > 0).sum()),
    "laranja_PAM_t": int(A.laranja_t.sum()), "municipios_com_fabrica_suco": int((A.laranja_fabrica_t > 0).sum()),
    "bov_total_PPM": int(A.bov_total.sum()), "vacas_ordenhadas": int(A.bov_leite_cab.sum()),
    "bov_confinado_GEDAVE": int(A.bov_conf_cab.sum()), "bov_pasto_misto": int(A.bov_pasto_cab.sum()),
    "gedave_bov_nomes_sem_match": gb_nm,
    "aves_corte": int(A.aves_corte_cab.sum()), "aves_postura": int(A.aves_postura_cab.sum()),
    "aves_share_comercial_estado": round(float(share_est), 4),
    "rsu_coletado_t": int(A.rsu_coletado_t.sum()), "rsu_fontes": A.fonte_rsu.value_counts().to_dict(),
    "indice_tratamento_pond": round(float((A.indice_tratamento * A["pop"]).sum() / A["pop"].sum()), 3),
    "frac_ete_digestao_pond": round(float((A.frac_ete_digestao * A["pop"]).sum() / A["pop"].sum()), 3),
    "esgoto_fc_pond": round(float((A.esgoto_fc * A["pop"]).sum() / A["pop"].sum()), 3),
    "uso_existente_alocavel_bi": round(float(U.loc[U.fluxo.notna(), "ch4_m3_ano"].sum() / 1e9), 4),
    "uso_existente_nao_alocado_bi": round(nao_alocado / 1e9, 4),
    "fl_espacial": (P.FL_ESPACIAL["variante"] if FLESP else None),
}
json.dump(diag, open(OUT / "cp2b_diagnostico.json", "w"), indent=1, ensure_ascii=False)
pd.set_option("display.width", 220)
print("\n== ESTADO (bi Nm³ CH4/ano) ==\n", est.round(3))
print("\n== ESTADO sem lignocelulósicos ==\n", est_sem.round(3))
print("\n== BASES (med) ==\n", pd.DataFrame(bases).round(3).to_string())
print("\n== POR FLUXO (med) ==\n", fx.round(3))
print("\n== POR SUBSTRATO (med) ==\n", sub.round(3))
print("\n== DIAGNÓSTICO ==\n", json.dumps(diag, indent=1, ensure_ascii=False))
print("\n== ALOCAÇÃO U ==\n", pd.DataFrame(alocacoes).to_string())
