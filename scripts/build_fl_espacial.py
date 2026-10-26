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

and draws the municipalities that each variant zeroes on the IBGE mesh (as in
build_mapas_incerteza.py; skipped with a note if the mesh cannot be read).

Nothing here re-runs fl_v5 or changes the platform; the radii and Q_min come
from fl_espacial/config_fl.yaml.

Run from the repo root:
  python3 scripts/build_fl_espacial.py

Outputs (outputs/fl_espacial/):
  estado_variantes.csv · zeros_variantes.csv · zeros_distancia.csv · c02_estado.csv ·
  c02_municipios.csv · conferencia.csv · mapa_zeros_variantes.png · RELATORIO.md
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
# sha256 of the two fl_v5 tables as published with v5.1 (fl_espacial/LEIA-ME.md)
REFERENCE = {"fl_v5_municipio_substrato.csv": "2a7b664b1f20", "fl_v5_estado_substrato.csv": "1bd83a1785ea"}
EPS = 1e-12
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
    """{file: rows}, the manifest checks, and why it did not load (empty if it did)."""
    man = folder / "MANIFESTO.csv"
    if not man.exists():
        return None, [], f"sem {man.relative_to(ROOT) if man.is_relative_to(ROOT) else man}"
    listed = {r["arquivo"]: r for r in _read(man)}
    chk = []
    for name in NEEDED:
        p = folder / name
        if name not in listed or not p.exists():
            return None, chk, f"falta {name} {'no manifesto' if name not in listed else 'na pasta'}"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha != listed[name]["sha256"] or p.stat().st_size != int(listed[name]["bytes"]):
            return None, chk, f"{name} não confere com o MANIFESTO.csv (sha256 ou tamanho)"
        if name in REFERENCE:
            chk.append({"checagem": f"{name} é o publicado com a v5.1 (sha256 {REFERENCE[name]}…)",
                        "resultado": sha.startswith(REFERENCE[name]), "detalhe": f"sha256 {sha[:12]}…"})
    data = {}
    for name, cols in NEEDED.items():
        rows = _read(folder / name)
        missing = [c for c in cols if c not in (rows[0] if rows else {})]
        if missing:
            return None, chk, f"{name} sem as colunas {', '.join(missing)}"
        data[name] = rows
    chk.insert(0, {"checagem": "as tabelas de data/fl_v51 conferem com o MANIFESTO.csv", "resultado": True,
                   "detalhe": f"{len(NEEDED)} arquivos, sha256 e tamanho"})
    return data, chk, ""


def config() -> dict:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return {"q_min": cfg["q_min"], "raios_km": cfg["raios_km"]}


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
    return {"estado": state, "zeros": zrows, "zero_sets": z, "near": [(m, names.get(m, m),
            top[("FL_codig_alocado", "med")][m]) for m in near], "dist": dist, "q_min": q_min,
            "r2": cfg["raios_km"]["med"], "c02_estado": c02_state, "c02_lista": c02_list, "c02_mun": c02_mun,
            "mclp": mclp, "robustez": rob, "r2_tab": data["sensibilidade_r2.csv"],
            "qmin_tab": data["sensibilidade_qmin.csv"], "conferencia": chk}


# ── Map ─────────────────────────────────────────────────────────────────────


def zero_map(path: Path, res: dict) -> str:
    """Med: in how many of the four variants each municipality has FL zero. Returns a note for the report."""
    try:
        mesh, origin, sha = M.load_mesh()
    except Exception as e:  # noqa: BLE001 — no mesh is a note, not a failure
        return f"Mapa não desenhado: a malha do IBGE não pôde ser lida ({type(e).__name__})."
    rings = M.polygons(mesh)
    count: dict = defaultdict(int)
    for v, _ in VARIANTS:
        for m in res["zero_sets"].get((v, "med"), set()):
            count[m] += 1
    values = {c: float(count.get(c, 0)) for c in rings}
    classes = ([0.0, 0.5, 1.5, 2.5, 3.5, math.inf], ["nenhuma", "1", "2", "3", "as 4"],
               [M.NEUTRAL, *M.RED])
    M.single_map(path, rings, values, classes, "Municípios com FL espacial zero no cenário med",
                 "Em quantas das quatro variantes do fl_v5 (A, B, C, D) o FL é zero em todos os substratos.",
                 "Variantes com FL zero", None)
    return f"Malha: {origin} (sha256 {sha[:12]}…)."


# ── Report ──────────────────────────────────────────────────────────────────


def _f(x, nd=3) -> str:
    return "—" if x is None else fmt(x, nd)


def _signed(x, nd=4) -> str:
    return "—" if x is None else ("+" if x > 0 else "") + fmt(x, nd)


def report(res: dict, map_note: str) -> list[str]:
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
    L += [f"| {fmt(100 * r['meta'], 0)} % | {r['hubs_N3_total'] or '—'} | {r['hubs_sem_palha'] or '—'} |"
          for r in res["mclp"]]
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
    L += ["", "## 6. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
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
    write_csv(OUT / "estado_variantes.csv", res["estado"])
    write_csv(OUT / "zeros_variantes.csv", res["zeros"])
    write_csv(OUT / "zeros_distancia.csv", res["dist"])
    write_csv(OUT / "c02_estado.csv", res["c02_estado"])
    write_csv(OUT / "c02_municipios.csv", res["c02_mun"])
    write_csv(OUT / "conferencia.csv", res["conferencia"])
    (OUT / "RELATORIO.md").write_text("\n".join(report(res, note)) + "\n", encoding="utf-8")
    failed = [c["checagem"] for c in res["conferencia"] if not c["resultado"]]
    print(f"conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
