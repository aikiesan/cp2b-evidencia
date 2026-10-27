#!/usr/bin/env python3
"""
The spatial FL of CP2b v5.1 read from its own outputs: variants, zeros, distances and the C02 effect.

data/fl_v51/ holds aggregated tables written by the fl_v5 code in
fl_espacial/ (run on the team's machine, outside git) and a MANIFESTO.csv with
the sha256 of each one. This script refuses the folder if a hash does not
match, then reports:

  the state FL per substrate under the four variants (A coverage, B allocated,
  C mono, D mono allocated) and how many municipalities each one zeroes
  how far the municipalities with FL med zero are from the nearest selected hub,
  against the collection radius r2 and the hub threshold Q_min
  what the C02 change (bagasse BMP) does to the FL, state and municipality
  the r2, Q_min, network and allocation sensitivities already run by fl_v5
  how state FL, the hub network and the zeroed municipalities move when the
  supply gets lognormal noise (v52_perturbacao.py), if those tables are there
  why Bananal, the one zeroed municipality with supply above Q_min, gets no hub

and draws on the IBGE mesh the municipalities that each variant zeroes and how
much municipal FL moves under the noise (as in build_mapas_incerteza.py;
skipped with a note if the mesh cannot be read).

Nothing here re-runs fl_v5 or changes the platform; the radii and Q_min come
from fl_espacial/config_fl.yaml.

Run from the repo root:
  python3 scripts/build_fl_espacial.py

Outputs (outputs/fl_espacial/):
  estado_variantes.csv · zeros_variantes.csv · zeros_distancia.csv · c02_estado.csv ·
  c02_municipios.csv · perturbacao.csv · perturbacao_zeros_med.csv · conferencia.csv ·
  mapa_zeros_variantes.png · mapa_perturbacao_fl.png · RELATORIO.md
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import math
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fl_v51"
OUT = ROOT / "outputs" / "fl_espacial"
CONFIG = ROOT / "fl_espacial" / "config_fl.yaml"
SCEN = ("min", "med", "max")
VARIANTS = (
    ("FL_codig_alocado", "B · codigestão, alocado"),
    ("FL_codigestao", "A · codigestão, cobertura"),
    ("FL_mono", "C · mono, cobertura"),
    ("FL_mono_alocado", "D · mono, alocado"),
)
NEEDED = {
    "fl_v5_municipio_substrato.csv": ("ibge", "codigo", "cenario", "municipio", *(v for v, _ in VARIANTS),
                                      "oferta_L3_m3dia"),
    "fl_v5_estado_substrato.csv": ("codigo", "cenario", *(v for v, _ in VARIANTS), "oferta_L3_m3dia"),
    "sensibilidade_r2.csv": ("classe", "r1_km", "r2_km", "hubs_viaveis_co", "FL_co", "FL_mono"),
    "sensibilidade_qmin.csv": ("q_min", "hubs_viaveis_co", "FL_co_sem_palha", "FL_mono_sem_palha"),
    "mclp_curva_B.csv": ("hubs", "cobertura_sem_palha", "cobertura_N3_total"),
    "robustez_rede.csv": ("codigo", "cenario", "dif_co", "dif_mono"),
    "fl_alocado_robustez.csv": ("modo_palha", "codigo", "cenario", "dif_codig_maxw", "dif_codig_exclusivo"),
    "c02_fl_delta.csv": ("codigo", "cenario", "FL_codig_alocado_v51", "FL_codig_alocado_c02",
                         "d_FL_codig_alocado", "d_FL_mono_alocado"),
    "c02_fl_municipio_delta.csv": ("ibge", "codigo", "cenario", "FL_codig_alocado_v51", "FL_codig_alocado_c02",
                                   "d_FL_codig_alocado"),
    "v52_zeros_distancia_hub.csv": ("ibge", "municipio", "codigo", "classe", "oferta_m3dia", "d_min_km",
                                    "d_mediana_km", "r1_km", "r2_km"),
}
# Read when listed in the manifest (written by fl_espacial/analises_v52/); without them their sections say so
OPTIONAL = {
    "pert_resumo.csv": ("desenho", "cenario", "rodadas", "linhas_mun_substrato", "linhas_max_abs_d_acima_01",
                        "linhas_p95_p05_acima_01", "hubs_v51", "municipios_zero_v51", "municipios_zero_sempre",
                        "municipios_zero_alguma_vez"),
    "pert_execucoes.csv": ("desenho", "cv_substrato", "cv_municipio", "cenario", "rodada", "hubs", "hubs_v51",
                           "jaccard", "municipios_fl_zero", "municipios_fl_zero_v51", "FL_estado", "FL_estado_v51",
                           "spearman_cob_mun", "top50_em_comum"),
    "pert_fl_estado.csv": ("desenho", "cenario", "codigo", "FL_v51", "p05", "p95"),
    "pert_fl_municipio_total.csv": ("desenho", "cenario", "ibge", "FL_v51", "p05", "p95", "frac_zero", "zero_v51"),
    "v52_bananal_candidatos.csv": ("hub_id", "tipo", "d_min_km", "bacia_cobertura", "viavel", "de_bananal_w",
                                   "ganho_sozinho"),
}
PERT = ("pert_resumo.csv", "pert_execucoes.csv", "pert_fl_estado.csv", "pert_fl_municipio_total.csv")
BANANAL = "3504909"
MAP_DESIGN = "mun30"   # the perturbation map: municipal noise only, the larger CV
# sha256 of the two fl_v5 tables as published with v5.1 (fl_espacial/LEIA-ME.md)
REFERENCE = {"fl_v5_municipio_substrato.csv": "2a7b664b1f20", "fl_v5_estado_substrato.csv": "1bd83a1785ea"}
EPS = 1e-12
MAP_SOURCE = "Fonte: tabelas do fl_v5 (CP2b v5.1) em data/fl_v51/; malha municipal do IBGE."
NEAR_ZERO = 0.01       # municipalities whose largest FL B med is above zero but at most this
C02_SHOWN = 5e-4       # state |ΔFL| below this is not listed


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load(ROOT / "scripts" / "build_mapas_incerteza.py")
fmt = M.fmt


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _ibge(v) -> str:
    return str(int(float(v)))


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load(folder: Path) -> tuple[dict | None, list[dict], str]:
    """{file: rows}, the manifest checks, and why it did not load (empty if it did).

    The NEEDED tables must all be there; an OPTIONAL one is read only if the manifest lists it. A table that is
    there and does not match the manifest refuses the whole folder."""
    man = folder / "MANIFESTO.csv"
    if not man.exists():
        return None, [], f"sem {man.relative_to(ROOT) if man.is_relative_to(ROOT) else man}"
    listed = {r["arquivo"]: r for r in _read(man)}
    chk = []
    for name in NEEDED:
        if name not in listed or not (folder / name).exists():
            return None, chk, f"falta {name} {'no manifesto' if name not in listed else 'na pasta'}"
    tables = {**NEEDED, **{n: c for n, c in OPTIONAL.items() if n in listed}}
    for name in tables:
        p = folder / name
        if not p.exists():
            return None, chk, f"falta {name} na pasta (está no manifesto)"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha != listed[name]["sha256"] or p.stat().st_size != int(listed[name]["bytes"]):
            return None, chk, f"{name} não confere com o MANIFESTO.csv (sha256 ou tamanho)"
        if name in REFERENCE:
            chk.append({"checagem": f"{name} é o publicado com a v5.1 (sha256 {REFERENCE[name]}…)",
                        "resultado": sha.startswith(REFERENCE[name]), "detalhe": f"sha256 {sha[:12]}…"})
    data = {}
    for name, cols in tables.items():
        rows = _read(folder / name)
        missing = [c for c in cols if c not in (rows[0] if rows else {})]
        if missing:
            return None, chk, f"{name} sem as colunas {', '.join(missing)}"
        data[name] = rows
    chk.insert(0, {"checagem": "as tabelas de data/fl_v51 conferem com o MANIFESTO.csv", "resultado": True,
                   "detalhe": f"{len(tables)} arquivos, sha256 e tamanho"})
    return data, chk, ""


def config() -> dict:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return {"q_min": cfg["q_min"], "raios_km": cfg["raios_km"], "classes_raio": cfg["classes_raio"]}


# ── Analysis ────────────────────────────────────────────────────────────────


def zeros(mun: list[dict]) -> tuple[dict, dict]:
    """{(variant, scenario): municipalities whose FL is zero in every substrate with supply}, and the largest FL."""
    top: dict = defaultdict(lambda: defaultdict(float))
    for r in mun:
        if (_num(r["oferta_L3_m3dia"]) or 0) > 0:
            for v, _ in VARIANTS:
                key = (v, r["cenario"])
                top[key][_ibge(r["ibge"])] = max(top[key][_ibge(r["ibge"])], _num(r[v]) or 0.0)
    return {k: {m for m, x in d.items() if x <= EPS} for k, d in top.items()}, top


def distances(rows: list[dict], q_min: float) -> list[dict]:
    """One line per zeroed municipality: supply, nearest selected hub, room left beyond r2, Q_min."""
    by: dict = defaultdict(list)
    for r in rows:
        by[(_ibge(r["ibge"]), r["municipio"])].append(r)
    out = []
    for (ibge, name), items in by.items():
        d = [_num(r["d_min_km"]) for r in items]
        d = [math.inf if x is None else x for x in d]
        supply = sum(_num(r["oferta_m3dia"]) or 0.0 for r in items)
        out.append({"ibge": ibge, "municipio": name, "oferta_m3dia": supply, "d_min_km": min(d),
                    "folga_r2_km": min(x - (_num(r["r2_km"]) or 0.0) for x, r in zip(d, items)),
                    "substratos": len(items), "abaixo_q_min": supply < q_min})
    return sorted(out, key=lambda r: r["d_min_km"])


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2) if n else math.nan


def _quantile(xs: list[float], p: float) -> float:
    """Linear interpolation between order statistics (numpy's default), as v52_perturbacao.py uses."""
    s = sorted(xs)
    if not s:
        return math.nan
    h = (len(s) - 1) * p
    lo = math.floor(h)
    return s[lo] + (h - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


def _true(v) -> bool:
    return str(v).strip().lower() in ("true", "1")


def perturbation(data: dict, zero_sets: dict, names: dict) -> dict | None:
    """Per noise design × scenario: hubs, state FL, zeroed municipalities, how many municipal FLs move; the widest
    state FLs and the municipalities that zero in some run (med); and the checks against the fl_v5 tables."""
    if any(n not in data for n in PERT):
        return None
    ex, summ = data["pert_execucoes.csv"], {(r["desenho"], r["cenario"]): r for r in data["pert_resumo.csv"]}
    designs = list(dict.fromkeys(r["desenho"] for r in ex))
    label = {}
    for r in ex:
        cs, cm = _num(r["cv_substrato"]) or 0.0, _num(r["cv_municipio"]) or 0.0
        label[r["desenho"]] = " × ".join([f"{fmt(100 * cs, 0)} % por substrato"] * (cs > 0)
                                         + [f"{fmt(100 * cm, 0)} % por município"] * (cm > 0))
    by: dict = defaultdict(list)
    for r in ex:
        by[(r["desenho"], r["cenario"])].append(r)
    rows, chk = [], []
    for d in designs:
        for s in SCEN:
            g, sm = by.get((d, s), []), summ.get((d, s))
            if not g or sm is None:
                continue
            fl = [_num(r["FL_estado"]) for r in g]
            rows.append({"desenho": d, "rotulo": label[d], "cenario": s, "rodadas": len(g),
                         "hubs_v51": int(float(g[0]["hubs_v51"])), "hubs_min": min(int(float(r["hubs"])) for r in g),
                         "hubs_max": max(int(float(r["hubs"])) for r in g),
                         "jaccard_mediana": _median([_num(r["jaccard"]) for r in g]),
                         "FL_estado_v51": _num(g[0]["FL_estado_v51"]), "FL_estado_p05": _quantile(fl, .05),
                         "FL_estado_p95": _quantile(fl, .95), "zero_v51": int(float(sm["municipios_zero_v51"])),
                         "zero_min": min(int(float(r["municipios_fl_zero"])) for r in g),
                         "zero_max": max(int(float(r["municipios_fl_zero"])) for r in g),
                         "zero_sempre": int(float(sm["municipios_zero_sempre"])),
                         "zero_alguma_vez": int(float(sm["municipios_zero_alguma_vez"])),
                         "linhas_mun_substrato": int(float(sm["linhas_mun_substrato"])),
                         "linhas_mudam_01": int(float(sm["linhas_max_abs_d_acima_01"])),
                         "linhas_p95_p05_acima_01": int(float(sm["linhas_p95_p05_acima_01"])),
                         "spearman_min": min(_num(r["spearman_cob_mun"]) for r in g),
                         "top50_min": min(int(float(r["top50_em_comum"])) for r in g)})
    bad = [f"{r['desenho']} {r['cenario']}" for r in rows if r["rodadas"] != int(float(summ[(r["desenho"],
                                                                                       r["cenario"])]["rodadas"]))]
    chk.append({"checagem": "perturbação: rodadas por desenho e cenário iguais às do resumo", "resultado": not bad,
                "detalhe": f"{sum(r['rodadas'] for r in rows)} rodadas em {len(rows)} grupos"
                + (f"; diferem: {', '.join(bad)}" if bad else "")})
    base = {}
    for s in SCEN:
        g = [r for r in ex if r["cenario"] == s]
        base[s] = ({r["hubs_v51"] for r in g}, {round(_num(r["FL_estado_v51"]), 9) for r in g},
                   {r["municipios_fl_zero_v51"] for r in g})
    same = all(len(a) == 1 and len(b) == 1 and len(c) == 1 for a, b, c in base.values())
    chk.append({"checagem": "perturbação: hubs, FL estadual e zerados da v5.1 iguais em todos os desenhos",
                "resultado": same, "detalhe": "; ".join(f"{s}: {', '.join(sorted(a))} hubs" for s, (a, _, _)
                                                        in base.items())})
    tot = data["pert_fl_municipio_total.csv"]
    diff = []
    for s in SCEN:
        mine = {_ibge(r["ibge"]) for r in tot if r["cenario"] == s and r["desenho"] == designs[0]
                and _true(r["zero_v51"])}
        if mine != zero_sets.get(("FL_codig_alocado", s), set()):
            diff.append(s)
    chk.append({"checagem": "perturbação: os zerados da v5.1 são os de FL B zero na tabela fl_v5",
                "resultado": not diff,
                "detalhe": "min, med e max" + (f"; diferem em {', '.join(diff)}" if diff else "")})
    widths: dict = defaultdict(dict)
    fl0 = {}
    for r in data["pert_fl_estado.csv"]:
        if r["cenario"] == "med":
            widths[r["codigo"]][r["desenho"]] = (_num(r["p05"]), _num(r["p95"]))
            fl0[r["codigo"]] = _num(r["FL_v51"])
    wide = sorted(widths, key=lambda c: -max(b - a for a, b in widths[c].values()))[:8]
    zrows: dict = {}
    for r in tot:
        if r["cenario"] == "med" and ((_num(r["frac_zero"]) or 0) > 0 or _true(r["zero_v51"])):
            m = _ibge(r["ibge"])
            z = zrows.setdefault(m, {"ibge": m, "municipio": names.get(m, m), "zero_v51": _true(r["zero_v51"]),
                                     **{d: 0.0 for d in designs}})
            z[r["desenho"]] = _num(r["frac_zero"]) or 0.0
    zlist = sorted(zrows.values(), key=lambda z: (-z["zero_v51"], -sum(z[d] for d in designs), z["municipio"]))
    amp = {_ibge(r["ibge"]): (_num(r["p95"]) or 0.0) - (_num(r["p05"]) or 0.0) for r in tot
           if r["cenario"] == "med" and r["desenho"] == MAP_DESIGN}
    return {"designs": designs, "label": label, "rows": rows, "wide": [(c, fl0[c], widths[c]) for c in wide],
            "zeros_med": zlist, "amp": amp, "runs": next((r["rodadas"] for r in rows if r["desenho"] == MAP_DESIGN),
                                                         None), "conferencia": chk}


def bananal(data: dict, cfg: dict, zero_med: set, q_min: float) -> dict | None:
    """Bananal's supply (med) by class from the fl_v5 table and what its candidate hubs gather (notebook run)."""
    cand = data.get("v52_bananal_candidatos.csv")
    if cand is None:
        return None
    cls = {c: k for k, lst in cfg["classes_raio"].items() for c in lst}
    sup: dict = defaultdict(float)
    name = BANANAL
    for r in data["fl_v5_municipio_substrato.csv"]:
        if _ibge(r["ibge"]) == BANANAL and r["cenario"] == "med":
            name = r["municipio"]
            sup["PALHA" if r["codigo"] == "PALHA" else cls.get(r["codigo"], "outros")] += \
                _num(r["oferta_L3_m3dia"]) or 0.0
    co = sum(v for k, v in sup.items() if k != "PALHA")
    best = max(cand, key=lambda r: _num(r["ganho_sozinho"]) or 0.0)
    out = {"municipio": name, "oferta_total": sum(sup.values()), "oferta_codig": co,
           "liquidos": sup.get("liquidos", 0.0), "candidatos": len(cand),
           "viaveis": sum(_true(r["viavel"]) for r in cand), "melhor": _num(best["ganho_sozinho"]) or 0.0,
           "melhor_tipo": best["tipo"], "melhor_d_km": _num(best["d_min_km"]),
           "melhor_de_bananal": _num(best["de_bananal_w"]) or 0.0, "q_min": q_min}
    out["conferencia"] = [{"checagem": "Bananal: FL B med zero, nenhum candidato viável e o melhor abaixo do Q_min",
                           "resultado": BANANAL in zero_med and out["viaveis"] == 0 and out["melhor"] < q_min,
                           "detalhe": f"{out['candidatos']} candidatos; melhor {fmt(out['melhor'], 1)} Nm³/dia"}]
    return out


def build(data: dict, cfg: dict) -> dict:
    mun, est = data["fl_v5_municipio_substrato.csv"], data["fl_v5_estado_substrato.csv"]
    names = {_ibge(r["ibge"]): r["municipio"] for r in mun}
    z, top = zeros(mun)
    state = [{"codigo": r["codigo"], "cenario": r["cenario"], "oferta_L3_m3dia": _num(r["oferta_L3_m3dia"]),
              **{v: _num(r[v]) for v, _ in VARIANTS}} for r in est]
    zrows = [{"cenario": s, "variante": v, "descricao": lab, "municipios_fl_zero": len(z.get((v, s), set())),
              "contra_B": len(z.get((v, s), set())) - len(z.get(("FL_codig_alocado", s), set()))}
             for s in SCEN for v, lab in VARIANTS]
    zero_b = z.get(("FL_codig_alocado", "med"), set())
    near = sorted((m for m, x in top[("FL_codig_alocado", "med")].items() if 0 < x <= NEAR_ZERO),
                  key=lambda m: top[("FL_codig_alocado", "med")][m])
    q_min = cfg["q_min"]["med"]
    dist = distances(data["v52_zeros_distancia_hub.csv"], q_min)

    c02 = data["c02_fl_delta.csv"]
    c02_state = []
    for s in SCEN:
        rs = [r for r in c02 if r["cenario"] == s]
        dB = [abs(_num(r["d_FL_codig_alocado"]) or 0) for r in rs]
        dD = [abs(_num(r["d_FL_mono_alocado"]) or 0) for r in rs]
        c02_state.append({"cenario": s, "max_abs_d_B": max(dB, default=0.0), "max_abs_d_D": max(dD, default=0.0),
                          "substratos_acima": sum(1 for a, b in zip(dB, dD) if max(a, b) >= C02_SHOWN)})
    c02_list = sorted((r for r in c02 if max(abs(_num(r["d_FL_codig_alocado"]) or 0),
                                             abs(_num(r["d_FL_mono_alocado"]) or 0)) >= C02_SHOWN),
                      key=lambda r: (SCEN.index(r["cenario"]), r["codigo"]))
    acc: dict = defaultdict(list)
    for r in data["c02_fl_municipio_delta.csv"]:
        acc[(r["codigo"], r["cenario"])].append(_num(r["d_FL_codig_alocado"]) or 0.0)
    c02_mun = [{"codigo": c, "cenario": s, "linhas": len(v), "municipios_sobem": sum(x > 0 for x in v),
                "municipios_descem": sum(x < 0 for x in v), "d_min": min(v), "d_max": max(v)}
               for (c, s), v in sorted(acc.items(), key=lambda kv: (SCEN.index(kv[0][1]), -len(kv[1])))]

    chk = []
    zd = {r["ibge"] for r in dist}
    chk.append({"checagem": "os municípios da tabela de distâncias são os de FL B med zero", "resultado": zd == zero_b,
                "detalhe": f"{len(zd)} na tabela, {len(zero_b)} com FL B med zero"
                + (f"; diferem: {', '.join(names.get(m, m) for m in sorted(zd ^ zero_b))}" if zd != zero_b else "")})
    bad = [r for r in c02 if abs((_num(r["FL_codig_alocado_c02"]) or 0) - (_num(r["FL_codig_alocado_v51"]) or 0)
                                 - (_num(r["d_FL_codig_alocado"]) or 0)) > 1e-9]
    chk.append({"checagem": "c02_fl_delta: d_FL = FL C02 − FL v5.1", "resultado": not bad,
                "detalhe": f"{len(c02)} linhas" + (f", {len(bad)} não fecham" if bad else "")})
    small = [r for r in data["c02_fl_municipio_delta.csv"] if abs(_num(r["d_FL_codig_alocado"]) or 0) <= 0.01]
    chk.append({"checagem": "c02_fl_municipio_delta só tem |ΔFL| > 0,01", "resultado": not small,
                "detalhe": f"{len(data['c02_fl_municipio_delta.csv'])} linhas"})

    curve = [(int(float(r["hubs"])), _num(r["cobertura_N3_total"]) or 0.0, _num(r["cobertura_sem_palha"]) or 0.0)
             for r in data["mclp_curva_B.csv"]]
    scale = 100.0 if max((c for _, c, _ in curve), default=0) > 1.5 else 1.0
    mclp = [{"meta": t, "hubs_N3_total": next((h for h, c, _ in curve if c / scale >= t), None),
             "hubs_sem_palha": next((h for h, _, c in curve if c / scale >= t), None)} for t in (0.5, 0.8, 0.9, 0.95)]
    mclp_top = (len(curve), max((c for _, c, _ in curve), default=0.0) / scale,
                max((c for _, _, c in curve), default=0.0) / scale)
    rob = []
    for s in SCEN:
        rede = [r for r in data["robustez_rede.csv"] if r["cenario"] == s]
        aloc = [r for r in data["fl_alocado_robustez.csv"] if r["cenario"] == s and r["modo_palha"] == "usinas"]
        rob.append({"cenario": s,
                    "rede_sem_track_co": max((abs(_num(r["dif_co"]) or 0) for r in rede), default=None),
                    "rede_sem_track_mono": max((abs(_num(r["dif_mono"]) or 0) for r in rede), default=None),
                    "alocacao_maxw": max((abs(_num(r["dif_codig_maxw"]) or 0) for r in aloc), default=None),
                    "alocacao_exclusivo": max((abs(_num(r["dif_codig_exclusivo"]) or 0) for r in aloc),
                                              default=None)})
    pert = perturbation(data, z, names)
    ban = bananal(data, cfg, zero_b, q_min)
    chk += (pert or {}).get("conferencia", []) + (ban or {}).get("conferencia", [])
    return {"estado": state, "zeros": zrows, "zero_sets": z, "pert": pert, "bananal": ban,
            "near": [(m, names.get(m, m), top[("FL_codig_alocado", "med")][m]) for m in near],
            "dist": dist, "q_min": q_min,
            "r2": cfg["raios_km"]["med"], "c02_estado": c02_state, "c02_lista": c02_list, "c02_mun": c02_mun,
            "mclp": mclp, "mclp_top": mclp_top, "robustez": rob, "r2_tab": data["sensibilidade_r2.csv"],
            "qmin_tab": data["sensibilidade_qmin.csv"], "conferencia": chk}


# ── Map ─────────────────────────────────────────────────────────────────────


def map_classes(sets: dict) -> tuple[dict[str, float], list[int]]:
    """Med, per municipality: 3 zero in all four variants, 2 zero in B (the one CP2b uses) but not in all,
    1 zero only in other variants, 0 in none; and how many municipalities fall in classes 1–3."""
    z = [sets.get((v, "med"), set()) for v, _ in VARIANTS]
    every, b, any_ = set.intersection(*z), z[0], set.union(*z)
    value = {m: 3.0 if m in every else 2.0 if m in b else 1.0 for m in any_}
    return value, [len(any_ - b), len(b - every), len(every)]


def zero_map(path: Path, res: dict) -> str:
    """Med: the municipalities with FL zero in B, in all four variants, or only in others. Returns a report note."""
    try:
        mesh, origin, sha = M.load_mesh()
    except Exception as e:  # noqa: BLE001 — no mesh is a note, not a failure
        return (f"Mapa não desenhado: a malha do IBGE não pôde ser lida ({type(e).__name__}); rode de novo com "
                "acesso à API do IBGE ou com CP2B_MALHA apontando para a malha municipal.")
    rings = M.polygons(mesh)
    value, n = map_classes(res["zero_sets"])
    values = {c: value.get(c, 0.0) for c in rings}
    classes = ([0.0, 0.5, 1.5, 2.5, math.inf],
               ["em nenhuma", f"só fora da B ({n[0]})", f"na B, não nas 4 ({n[1]})", f"nas 4 ({n[2]})"],
               [M.NEUTRAL, M.RED[0], M.RED[2], M.RED[3]])
    M.single_map(path, rings, values, classes, "Municípios com FL espacial zero no cenário med",
                 f"FL zero em todos os substratos. B (codigestão alocada) é a variante do CP2b: {n[1] + n[2]} "
                 "municípios; A cobertura, C mono, D mono alocada.", "FL zero na variante", None, source=MAP_SOURCE)
    missing = sorted(set(value) - set(rings))
    return (f"Malha: {origin} (sha256 {sha[:12]}…). No mapa, {n[2]} municípios zeram nas quatro variantes, "
            f"{n[1]} na B e não em todas, e {n[0]} só fora da B"
            + (f"; sem polígono: {', '.join(missing)}" if missing else "") + ".")


def pert_map(path: Path, res: dict) -> str:
    """Med: amplitude p05–p95 of each municipality's FL B (all substrates) under the MAP_DESIGN noise."""
    p = res["pert"]
    if not p or not p["amp"]:
        return ""
    try:
        mesh, _, _ = M.load_mesh()
    except Exception as e:  # noqa: BLE001 — no mesh is a note, not a failure
        return f"Mapa da perturbação não desenhado: a malha do IBGE não pôde ser lida ({type(e).__name__})."
    rings = M.polygons(mesh)
    values = {c: p["amp"].get(c) for c in rings}
    classes = ([0.0, 0.01, 0.05, 0.1, 0.2, math.inf], ["< 0,01", "0,01–0,05", "0,05–0,10", "0,10–0,20", "≥ 0,20"],
               [M.BLUE[0], M.BLUE[2], M.BLUE[3], M.BLUE[5], M.BLUE[6]])
    M.single_map(path, rings, values, classes, "Quanto o FL municipal varia com ruído na oferta (med)",
                 f"FL B do município, todos os substratos: amplitude entre os percentis 5 e 95 de {p['runs']} rodadas "
                 f"com ruído de {p['label'][MAP_DESIGN]} × substrato.", "p95 − p05 do FL", "sem oferta",
                 source=MAP_SOURCE)
    n = [sum(1 for v in p["amp"].values() if lo <= v < hi) for lo, hi in zip(classes[0], classes[0][1:])]
    counts = "; ".join(f"{lab}: {k}" for lab, k in zip(classes[1], n))
    return f"No mapa da perturbação ({MAP_DESIGN}, med), municípios por classe de p95 − p05: {counts}."


# ── Report ──────────────────────────────────────────────────────────────────


def _f(x, nd=3) -> str:
    return "—" if x is None else fmt(x, nd)


def _signed(x, nd=4) -> str:
    if x is None:
        return "—"
    x = round(x, nd) + 0.0                    # no "-0,0000"
    return ("+" if x > 0 else "") + fmt(x, nd)


def report_pert(res: dict, map_note: str) -> list[str]:
    p = res["pert"]
    L = ["", "## 6. Perturbação da oferta (B, palha nas usinas)", ""]
    if not p:
        return L + [f"Não rodou: faltam em `data/fl_v51/` as tabelas {', '.join(f'`{n}`' for n in PERT)} "
                    "(`fl_espacial/analises_v52/v52_perturbacao.py`)."]
    L += ["A oferta N3 de cada substrato multiplicada por um fator lognormal de média 1, o mesmo nos três cenários, e "
          "a alocação gulosa refeita (o filtro de candidatos acompanha o ruído). A rodada sem ruído repete os hubs e o "
          "FL municipal da v5.1. Com o fator igual dentro do município, o FL municipal de um substrato só muda se a "
          "rede de hubs mudar.", "",
          "| Ruído | Cenário | Hubs (v5.1 → faixa) | Jaccard mediano | FL estadual v5.1 (p05–p95) | "
          "Zerados v5.1 (faixa) | Zeram sempre | Zeram alguma vez | Linhas mun. × subst. com p95 − p05 > 0,1 | "
          "Spearman mín. | Top-50 mín. |", "|---|---|---|---:|---|---|---:|---:|---|---:|---:|"]
    L += [f"| {r['rotulo']} | {r['cenario']} | {r['hubs_v51']} → {r['hubs_min']}–{r['hubs_max']} | "
          f"{fmt(r['jaccard_mediana'], 2)} | {fmt(r['FL_estado_v51'], 3)} ({fmt(r['FL_estado_p05'], 3)}–"
          f"{fmt(r['FL_estado_p95'], 3)}) | {r['zero_v51']} ({r['zero_min']}–{r['zero_max']}) | {r['zero_sempre']} | "
          f"{r['zero_alguma_vez']} | {fmt(r['linhas_p95_p05_acima_01'], 0)} de {fmt(r['linhas_mun_substrato'], 0)} | "
          f"{fmt(r['spearman_min'], 3)} | {r['top50_min']} |" for r in p["rows"]]
    L += ["", "Jaccard: hubs em comum com a v5.1 sobre a união. Spearman e top-50: ordem dos municípios pela oferta "
          "coberta (N3 × FL), contra a v5.1; inclui o ruído da própria oferta.", "",
          "Substratos com o FL estadual mais largo no med (p05–p95):", "",
          "| Substrato | FL v5.1 | " + " | ".join(p["label"][d] for d in p["designs"]) + " |",
          "|---|---:|" + "---|" * len(p["designs"])]
    L += [f"| {c} | {fmt(f0, 3)} | " + " | ".join(f"{fmt(w[d][0], 3)}–{fmt(w[d][1], 3)}" if d in w else "—"
                                                  for d in p["designs"]) + " |" for c, f0, w in p["wide"]]
    z = p["zeros_med"]
    L += ["", f"Municípios com FL B med zero na v5.1 ou em alguma rodada ({len(z)}): fração das rodadas em que zeram.",
          "", "| Município | Zero na v5.1 | " + " | ".join(p["label"][d] for d in p["designs"]) + " |",
          "|---|---|" + "---:|" * len(p["designs"])]
    L += [f"| {r['municipio']} | {'sim' if r['zero_v51'] else 'não'} | "
          + " | ".join(fmt(r[d], 2) for d in p["designs"]) + " |" for r in z]
    if map_note:
        L += ["", map_note + (" Mapa: `mapa_perturbacao_fl.png`." if map_note.startswith("No mapa") else "")]
    return L


def report_bananal(res: dict) -> list[str]:
    b = res["bananal"]
    L = ["", "## 7. Bananal: oferta acima do Q_min e nenhum hub", ""]
    if not b:
        return L + ["Não rodou: falta `data/fl_v51/v52_bananal_candidatos.csv` "
                    "(`fl_espacial/analises_v52/v52_bananal.py`)."]
    pal = b["oferta_total"] - b["oferta_codig"]
    return L + [
        f"- Oferta N3 med: {fmt(b['oferta_total'], 1)} Nm³/dia; sem a palha de cana ({fmt(pal, 1)}), que vai só às "
        f"usinas, {fmt(b['oferta_codig'], 1)} para a codigestão, "
        f"{fmt(100 * b['liquidos'] / b['oferta_codig'], 0) if b['oferta_codig'] else '—'} % "
        "dela em líquidos (raios de 5/15 km). Fonte: `fl_v5_municipio_substrato.csv`.",
        f"- {b['candidatos']} candidatos a hub alcançam essa oferta; {b['viaveis']} viáveis pela bacia de cobertura "
        f"(Q_min {fmt(b['q_min'], 0)} Nm³/dia).",
        f"- O melhor ({b['melhor_tipo']}, a {_f(b['melhor_d_km'], 1)} km da oferta) junta {fmt(b['melhor'], 1)} "
        f"Nm³/dia pesados por w(d), {fmt(100 * b['melhor'] / b['q_min'], 0)} % do Q_min; "
        f"{fmt(b['melhor_de_bananal'], 1)} vêm do próprio Bananal. Fonte: `v52_bananal_candidatos.csv`."]


def report(res: dict, map_note: str, pert_note: str = "") -> list[str]:
    L = ["# O FL espacial do CP2b v5.1, lido das saídas do fl_v5", "",
         "> Tabelas agregadas de `data/fl_v51/` (conferidas com o `MANIFESTO.csv`), escritas pelo código de "
         "`fl_espacial/`. FL entre 0 e 1; oferta em Nm³ de CH₄ por dia (N3). Nada aqui roda o fl_v5 de novo.", "",
         "## 1. FL estadual por substrato (cenário med)", "",
         "| Substrato | " + " | ".join(lab for _, lab in VARIANTS) + " | Oferta N3 (Nm³/dia) |",
         "|---|" + "---:|" * (len(VARIANTS) + 1)]
    for r in sorted((r for r in res["estado"] if r["cenario"] == "med"), key=lambda r: -(r["oferta_L3_m3dia"] or 0)):
        L.append(f"| {r['codigo']} | " + " | ".join(_f(r[v]) for v, _ in VARIANTS)
                 + f" | {_f(r['oferta_L3_m3dia'], 0)} |")
    L += ["", "## 2. Municípios com FL zero em todos os substratos", "",
          "| Cenário | Variante | Municípios | Contra B |", "|---|---|---:|---:|"]
    L += [f"| {r['cenario']} | {r['descricao']} | {r['municipios_fl_zero']} | {_signed(r['contra_B'], 0)} |"
          for r in res["zeros"]]
    if res["near"]:
        L += ["", "Quase zero no B med (maior FL entre os substratos acima de 0 e até "
              f"{fmt(NEAR_ZERO, 2)}): " + "; ".join(f"{n} ({fmt(x, 4)})" for _, n, x in res["near"]) + "."]
    if map_note:
        L += ["", map_note + (" Mapa: `mapa_zeros_variantes.png`." if map_note.startswith("Malha") else "")]
    d = res["dist"]
    r2 = res["r2"]
    L += ["", "## 3. Por que os municípios zeram, em km (B, med, palha nas usinas)", "",
          f"Distância por estrada do ponto de oferta ao hub selecionado mais próximo. r2 med: líquidos "
          f"{r2['liquidos'][1]} km, sólidos úmidos {r2['solidos_umidos'][1]} km, sólidos secos "
          f"{r2['solidos_secos'][1]} km (palha: o r2 das usinas). Folga = menor (d mínima − r2) entre os "
          f"substratos; acima de zero, nenhuma oferta do município alcança um hub. Q_min med = "
          f"{fmt(res['q_min'], 0)} Nm³/dia.", ""]
    if d:
        fin = [r["d_min_km"] for r in d if math.isfinite(r["d_min_km"])]
        L += [f"- {len(d)} municípios; hub mais próximo a {_f(min(fin, default=None), 1)}–"
              f"{_f(max(fin, default=None), 1)} km (mediana {_f(_median(fin), 1)} km)"
              + (f"; {len(d) - len(fin)} sem hub em 150 km" if len(fin) < len(d) else "") + ".",
              f"- Folga acima de zero em {sum(r['folga_r2_km'] > 0 for r in d)} de {len(d)}; a menor é "
              f"{_f(min(r['folga_r2_km'] for r in d), 1)} km.",
              f"- Oferta própria abaixo do Q_min em {sum(r['abaixo_q_min'] for r in d)} de {len(d)}.", "",
              "| Município | Oferta N3 (Nm³/dia) | Hub mais próximo (km) | Folga além do r2 (km) | Abaixo do Q_min |",
              "|---|---:|---:|---:|---|"]
        L += [f"| {r['municipio']} | {fmt(r['oferta_m3dia'], 1)} | {_f(r['d_min_km'], 1)} | "
              f"{_f(r['folga_r2_km'], 1)} | {'sim' if r['abaixo_q_min'] else 'não'} |" for r in d]
    L += ["", "## 4. A C02 (BMP do bagaço) no FL", "",
          "`04b` rodado de novo com a oferta de bagaço escalada pelo BMP proposto; as bacias de cobertura (filtro "
          "dos candidatos) ficaram as da v5.1, então o efeito é um piso.", "",
          "| Cenário | Máx \\|ΔFL\\| B | Máx \\|ΔFL\\| D | Substratos com \\|Δ\\| ≥ 0,0005 |", "|---|---:|---:|---:|"]
    L += [f"| {r['cenario']} | {fmt(r['max_abs_d_B'], 4)} | {fmt(r['max_abs_d_D'], 4)} | {r['substratos_acima']} |"
          for r in res["c02_estado"]]
    if res["c02_lista"]:
        L += ["", "| Substrato | Cenário | FL B v5.1 | FL B C02 | ΔFL B | ΔFL D |", "|---|---|---:|---:|---:|---:|"]
        L += [f"| {r['codigo']} | {r['cenario']} | {_f(_num(r['FL_codig_alocado_v51']), 4)} | "
              f"{_f(_num(r['FL_codig_alocado_c02']), 4)} | {_signed(_num(r['d_FL_codig_alocado']))} | "
              f"{_signed(_num(r['d_FL_mono_alocado']))} |" for r in res["c02_lista"]]
    n = sum(r["linhas"] for r in res["c02_mun"])
    L += ["", f"No município, {n} linhas município × substrato mudam mais de 0,01 no FL B:", "",
          "| Substrato | Cenário | Linhas | Sobem | Descem | ΔFL mín | ΔFL máx |", "|---|---|---:|---:|---:|---:|---:|"]
    L += [f"| {r['codigo']} | {r['cenario']} | {r['linhas']} | {r['municipios_sobem']} | {r['municipios_descem']} | "
          f"{_signed(r['d_min'], 3)} | {_signed(r['d_max'], 3)} |" for r in res["c02_mun"]]
    L += ["", "## 5. Sensibilidades que o fl_v5 já rodou", "",
          "Cobertura da rede B (curva MCLP): hubs para cobrir cada fração do N3.", "",
          "| Meta | Hubs (N3 total) | Hubs (sem palha) |", "|---:|---:|---:|"]
    L += [f"| {fmt(100 * r['meta'], 0)} % | {r['hubs_N3_total'] or 'não chega'} | "
          f"{r['hubs_sem_palha'] or 'não chega'} |" for r in res["mclp"]]
    n, top_all, top_np = res["mclp_top"]
    L += ["", f"Com os {fmt(n, 0)} candidatos da curva, a cobertura chega a {fmt(100 * top_all, 1)} % do N3 total e "
          f"{fmt(100 * top_np, 1)} % do N3 sem palha (a palha só vai às usinas)."]
    L += ["", "Robustez (maior \\|ΔFL\\| estadual entre os substratos): rede sem trilhas e regra de atribuição.", "",
          "| Cenário | Rede, codigestão | Rede, mono | Atribuição pelo maior w | Atribuição exclusiva |",
          "|---|---:|---:|---:|---:|"]
    L += [f"| {r['cenario']} | {_f(r['rede_sem_track_co'], 4)} | {_f(r['rede_sem_track_mono'], 4)} | "
          f"{_f(r['alocacao_maxw'], 4)} | {_f(r['alocacao_exclusivo'], 4)} |" for r in res["robustez"]]
    L += ["", "FL estadual com outro r2 (por classe) e outro Q_min:", "",
          "| Classe | r1 | r2 | Hubs viáveis | FL codigestão | FL mono |", "|---|---:|---:|---:|---:|---:|"]
    L += [f"| {r['classe']} | {r['r1_km']} | {r['r2_km']} | {r['hubs_viaveis_co']} | {_f(_num(r['FL_co']))} | "
          f"{_f(_num(r['FL_mono']))} |" for r in res["r2_tab"]]
    L += ["", "| Q_min (Nm³/dia) | Hubs viáveis | FL codigestão sem palha | FL mono sem palha |",
          "|---:|---:|---:|---:|"]
    L += [f"| {r['q_min']} | {r['hubs_viaveis_co']} | {_f(_num(r['FL_co_sem_palha']))} | "
          f"{_f(_num(r['FL_mono_sem_palha']))} |" for r in res["qmin_tab"]]
    L += report_pert(res, pert_note) + report_bananal(res)
    L += ["", "## 8. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    L += [f"| {c['checagem']} | {'ok' if c['resultado'] else 'FALHOU'} | {c['detalhe']} |" for c in res["conferencia"]]
    L += ["", "## Como ler", "",
          "- Um município zera quando nenhuma oferta dele fica a menos de r2 de um hub selecionado; um hub só entra "
          "com Q_min de resíduo à sua volta. A seção 3 mede as duas coisas.",
          "- O N4 zero do snapshot (`outputs/fl_variantes/`) conta municípios com N4 abaixo de 1 Nm³/ano; aqui "
          "conta-se FL exatamente zero, e um município com FL quase zero entra lá e não aqui.",
          "- O efeito da C02 no FL estadual vem da tabela 4; o efeito no N4 é o do `build_v52.py`, que mantém o FL "
          "da v5.1. No município, a C02 troca hubs de lugar e o FL de líquidos muda onde a pecuária é dispersa.", ""]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data, chk, why = load(DATA)
    if data is None:
        (OUT / "RELATORIO.md").write_text(f"# O FL espacial do CP2b v5.1\n\nNão rodou: {why}.\n", encoding="utf-8")
        print(f"Sem dados do FL: {why}")
        return
    res = build(data, config())
    res["conferencia"] = chk + res["conferencia"]
    note = zero_map(OUT / "mapa_zeros_variantes.png", res)
    pnote = pert_map(OUT / "mapa_perturbacao_fl.png", res)
    write_csv(OUT / "estado_variantes.csv", res["estado"])
    write_csv(OUT / "zeros_variantes.csv", res["zeros"])
    write_csv(OUT / "zeros_distancia.csv", res["dist"])
    write_csv(OUT / "c02_estado.csv", res["c02_estado"])
    write_csv(OUT / "c02_municipios.csv", res["c02_mun"])
    if res["pert"]:
        write_csv(OUT / "perturbacao.csv", res["pert"]["rows"])
        write_csv(OUT / "perturbacao_zeros_med.csv", res["pert"]["zeros_med"])
    write_csv(OUT / "conferencia.csv", res["conferencia"])
    (OUT / "RELATORIO.md").write_text("\n".join(report(res, note, pnote)) + "\n", encoding="utf-8")
    failed = [c["checagem"] for c in res["conferencia"] if not c["resultado"]]
    print(f"conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
