#!/usr/bin/env python3
"""
CP2b v5.1 uncertainty: how wide the state N4 really is, which parameters drive
it, and how stable the municipal ranking is.

The article reports the CP2b min and max scenarios. Those put every parameter
of every substrate at its minimum (or maximum) at the same time, which no
reviewer reads as an interval. This script samples each parameter inside its
own CP2b range instead and recomputes the cascade municipality by municipality,
with the same recomputation the sensitivity script uses (build_sensibilidade_cp2b.py):

  N1 × (g, ST, SV, BMP, direto)   N2 × FC   N3a × FCo   N3 = max(N3a − U, 0)   N4 × (FS, FL)

Each parameter is a multiplier on its stage: the draw over the CP2b median.
Draws are triangular (min, med, max), independent across parameters and
substrates. Independence is an assumption: parameters that share a source move
together, and the CP2b min-max band is the opposite limit, everything moving
together. Both are reported.

Before using the model, the script checks it: every multiplier at min (or max)
must reproduce the snapshot's own min (or max) N4 per substrate. Where it does
not, the CP2b varies something this model does not see (the base, or the
spatial FL per municipality), and the report says so.

Three outputs answer three questions:

  incerteza   state N1-N4 and N4 per substrate: p5, p50, p95 of the draws
  tornado     each parameter at its min and max, the others at the median
              (swing in N4), and its share of the N4 variance in the draws
  ranking     municipal N4: chance of staying in the top 50, rank p5-p95,
              rank in each literature scenario of the sensitivity script, and
              the same by intermediate region (IBGE RGInt)

Nothing here changes the platform, the snapshot or the article numbers.

Run from the repo root (CP2B_MC_N draws, default 5000; fixed seed):
  python3 scripts/build_incerteza_cp2b.py

Outputs (outputs/incerteza_cp2b/):
  incerteza.csv  ·  tornado.csv  ·  ranking.csv  ·  regioes.csv  ·  cenarios_ranking.csv  ·  RELATORIO.md
"""

from __future__ import annotations

import csv
import importlib.util
import math
import os
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "incerteza_cp2b"
SEED = 20261023
TOP = 50
LEVEL_KEYS = ("n1", "n2", "n3a", "n3", "n4")


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load(ROOT / "scripts" / "build_sensibilidade_cp2b.py")
P = _load(ROOT / "scripts" / "pilar2b.py")
E, B = S.E, S.B
fmt, mi = S.fmt, S.mi

# CP2b element -> cascade stage. Elements not listed here are reported as not varied.
STAGE = {"g": "n1", "ST": "n1", "SV": "n1", "BMP": "n1", "direto": "n1",
         "FC": "n2", "FCo": "n3a", "FS": "n4", "FL": "n4"}
NAMES = P.PILAR2B / "analysis" / "outputs" / "sp_digestate_nutrients" / "municipios.csv"
REGIONS = P.PILAR2B / "analysis" / "data" / "02_municipality_summary_SP_2023.csv"


# ── Inputs ──────────────────────────────────────────────────────────────────


def parameters() -> tuple[dict[tuple[str, str], tuple[float, float, float]], list[str], str]:
    """{(code, element): (min, med, max)} for the varied elements, the elements left out, and a note."""
    params, note = E.cp2b_parameters(tuple(STAGE))
    path, _ = S._verified("parameters")
    other = set()
    if path is not None:
        with path.open(encoding="utf-8-sig") as fh:
            other = {r.get("elemento", "") for r in csv.DictReader(fh)} - set(STAGE) - {""}
    params = {k: v for k, v in params.items() if v[1]}
    return params, sorted(other), note


def municipalities() -> dict[str, tuple[str, str]]:
    """ibge -> (name, intermediate region), from PILAR-2b outputs; empty strings when not available."""
    out: dict = defaultdict(lambda: ("", ""))
    names, regions = {}, {}
    if NAMES.exists():
        with NAMES.open(encoding="utf-8-sig") as fh:
            names = {str(int(float(r["cd_mun"]))): r["municipio"] for r in csv.DictReader(fh)}
    if REGIONS.exists():
        with REGIONS.open(encoding="utf-8-sig") as fh:
            regions = {str(int(float(r["ibge_code"]))): r["nm_rgint"] for r in csv.DictReader(fh)}
    for code in set(names) | set(regions):
        out[code] = (names.get(code, ""), regions.get(code, ""))
    return out


# ── The model ───────────────────────────────────────────────────────────────


def med_rows(rows: list[dict]) -> list[tuple]:
    """(ibge, code, n1, n2, n3a, u, fsfl) of the med scenario, the only state the recomputation starts from."""
    return [(r["ibge"], r["codigo"], r["n1"], r["n2"], r["n3a"], r["u"], r["fsfl"])
            for r in rows if r["cenario"] == "med"]


def stage_mult(params: dict, values: dict[tuple[str, str], float]) -> dict[str, tuple[float, float, float, float]]:
    """code -> (m_n1, m_n2, m_n3a, m_n4) for parameter values {(code, element): value}; median elsewhere."""
    out: dict = defaultdict(lambda: [1.0, 1.0, 1.0, 1.0])
    idx = {"n1": 0, "n2": 1, "n3a": 2, "n4": 3}
    for (code, el), v in values.items():
        out[code][idx[STAGE[el]]] *= v / params[(code, el)][1]
    return {k: tuple(v) for k, v in out.items()}


def run(med: list[tuple], mult: dict[str, tuple]) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """State levels, N4 per substrate and N4 per municipality for stage multipliers per substrate."""
    state = dict.fromkeys(LEVEL_KEYS, 0.0)
    by_sub: dict = defaultdict(float)
    by_mun: dict = defaultdict(float)
    one = (1.0, 1.0, 1.0, 1.0)
    for ibge, code, n1, n2, n3a, u, fsfl in med:
        m1, m2, m3, m4 = mult.get(code, one)
        a = m1
        n1x = n1 * a
        a *= m2
        n2x = n2 * a
        a *= m3
        n3ax = n3a * a
        n3x = n3ax - u if n3ax > u else 0.0
        n4x = n3x * fsfl * m4
        state["n1"] += n1x
        state["n2"] += n2x
        state["n3a"] += n3ax
        state["n3"] += n3x
        state["n4"] += n4x
        by_sub[code] += n4x
        by_mun[ibge] += n4x
    return state, by_sub, by_mun


def model_check(rows: list[dict], med: list[tuple], params: dict) -> list[dict]:
    """Per substrate: N4 with every multiplier at min (max) against the snapshot's own min (max) scenario."""
    snap = {s: S.cascade(rows, s) for s in ("min", "max")}
    out = []
    for i, scen in ((0, "min"), (2, "max")):
        _, by_sub, _ = run(med, stage_mult(params, {k: v[i] for k, v in params.items()}))
        for code in sorted(set(by_sub) | set(snap[scen])):
            want = snap[scen].get(code, {}).get("n4", 0.0)
            got = by_sub.get(code, 0.0)
            out.append({"codigo": code, "cenario": scen, "n4_snapshot": want, "n4_modelo": got,
                        "razao": got / want if want else None})
    return out


STAGE_STEPS = (("N1", "n1", None, 0), ("FC", "n2", "n1", 1), ("FCo", "n3a", "n2", 2), ("U", "u", None, None),
               ("FS × FL", "n4", "n3", 3))


def stage_check(rows: list[dict], params: dict) -> list[dict]:
    """Per substrate and stage: the snapshot's min/med and max/med ratio against the model's multiplier.

    N1 is the ratio of N1 totals; FC, FCo and FS × FL are ratios of the stage
    factor (N2/N1, N3a/N2, N4/N3, state totals of the substrate); U is the ratio
    of existing use, which the model keeps at the med value.
    """
    casc = {s: S.cascade(rows, s) for s in ("min", "med", "max")}
    out = []
    for i, scen in ((0, "min"), (2, "max")):
        mult = stage_mult(params, {k: v[i] for k, v in params.items()})
        for code in sorted(casc["med"]):
            med, snap = casc["med"][code], casc[scen].get(code)
            if snap is None:
                continue
            m = mult.get(code, (1.0, 1.0, 1.0, 1.0))
            for name, num, den, idx in STAGE_STEPS:
                if den and (not snap[den] or not med[den]):
                    continue
                a = snap[num] / snap[den] if den else snap[num]
                b = med[num] / med[den] if den else med[num]
                out.append({"codigo": code, "cenario": scen, "etapa": name,
                            "razao_snapshot": a / b if b else None,
                            "razao_modelo": m[idx] if idx is not None else 1.0})
    return out


def triangular(rng: random.Random, lo: float, mode: float, hi: float) -> float:
    return lo if lo == hi else rng.triangular(lo, hi, mode)


def simulate(med: list[tuple], params: dict, n: int, seed: int = SEED) -> dict:
    """n draws: state levels, N4 per substrate and per municipality, and municipal ranks."""
    rng = random.Random(seed)
    keys = sorted(params)
    levels = {k: [] for k in LEVEL_KEYS}
    subs: dict = defaultdict(list)
    munis: dict = defaultdict(list)
    ranks: dict = defaultdict(list)
    top_hits: dict = defaultdict(int)
    _, _, base_mun = run(med, {})
    base_order = ranked(base_mun)
    spearman = []
    for _ in range(n):
        values = {k: triangular(rng, *params[k]) for k in keys}
        state, by_sub, by_mun = run(med, stage_mult(params, values))
        for k in LEVEL_KEYS:
            levels[k].append(state[k])
        for code, v in by_sub.items():
            subs[code].append(v)
        order = ranked(by_mun)
        for ibge, v in by_mun.items():
            munis[ibge].append(v)
            ranks[ibge].append(order[ibge])
            if order[ibge] <= TOP:
                top_hits[ibge] += 1
        spearman.append(spearman_rank(base_order, order))
    return {"n": n, "keys": keys, "levels": levels, "subs": subs, "munis": munis,
            "ranks": ranks, "top": top_hits, "spearman": spearman, "base_order": base_order}


# ── Statistics ──────────────────────────────────────────────────────────────


def quantile(values: list[float], q: float) -> float:
    """Linear interpolation between order statistics (the usual type-7 quantile)."""
    xs = sorted(values)
    if not xs:
        return float("nan")
    h = (len(xs) - 1) * q
    lo = math.floor(h)
    return xs[lo] + (h - lo) * (xs[min(lo + 1, len(xs) - 1)] - xs[lo])


def ranked(values: dict[str, float]) -> dict[str, int]:
    """key -> rank, 1 = largest; ties broken by key so a run is reproducible."""
    order = sorted(values, key=lambda k: (-values[k], k))
    return {k: i + 1 for i, k in enumerate(order)}


def spearman_rank(a: dict[str, int], b: dict[str, int]) -> float:
    keys = [k for k in a if k in b]
    n = len(keys)
    if n < 2:
        return float("nan")
    d2 = sum((a[k] - b[k]) ** 2 for k in keys)
    return 1 - 6 * d2 / (n * (n * n - 1))


def triangular_var(lo: float, mode: float, hi: float) -> float:
    return (lo * lo + mode * mode + hi * hi - lo * mode - lo * hi - mode * hi) / 18


def tornado(med: list[tuple], params: dict, sim: dict | None) -> list[dict]:
    """One parameter at its min and max, the others at the median.

    The variance share is first order and deterministic: N4 is linear in each
    parameter when the others are fixed, so the slope between the two ends times
    the parameter's triangular variance, over the N4 variance of the draws.
    """
    base = run(med, {})[0]["n4"]
    var_n4 = statistics.pvariance(sim["levels"]["n4"]) if sim and sim["n"] > 1 else 0.0
    out = []
    for key in sorted(params):
        lo, mid, hi = params[key]
        if lo == hi:
            continue
        n4 = [run(med, stage_mult(params, {key: v}))[0]["n4"] for v in (lo, hi)]
        slope = (n4[1] - n4[0]) / (hi - lo)
        out.append({"codigo": key[0], "elemento": key[1], "min": lo, "med": mid, "max": hi,
                    "n4_no_min": n4[0], "n4_no_max": n4[1], "amplitude": abs(n4[1] - n4[0]),
                    "amplitude_pct": 100 * abs(n4[1] - n4[0]) / base if base else None,
                    "parcela_variancia": slope * slope * triangular_var(lo, mid, hi) / var_n4 if var_n4 else None})
    return sorted(out, key=lambda r: -r["amplitude"])


# ── Ranking under the literature scenarios ──────────────────────────────────


def scenario_ranks(med: list[tuple]) -> list[tuple[str, str, dict[str, int]]]:
    """(key, label, municipal rank) for each literature or hypothesis scenario of the sensitivity script."""
    lib = S.literature()
    out = []
    found = {}
    for key, kind, label, codes, terms, _ in S.SCENARIOS:
        mult = S.multipliers(lib, codes, terms)
        found[key] = mult
        if mult is None or kind == "definição":
            continue
        out.append((key, label, _rank_with(med, {k: v[1] for k, v in mult.items()})))
    for key, label, parts in S.COMBINED:
        if any(found.get(p) is None for p in parts):
            continue
        mult: dict = {}
        for p in parts:
            for k, v in found[p].items():
                mult[k] = mult.get(k, 1.0) * v[1]
        out.append((key, label, _rank_with(med, mult)))
    return out


def _rank_with(med: list[tuple], mult: dict[tuple[str, str], float]) -> dict[str, int]:
    idx = {"n1": 0, "n2": 1, "n3a": 2, "n4": 3}
    per: dict = defaultdict(lambda: [1.0, 1.0, 1.0, 1.0])
    for (code, stage), m in mult.items():
        per[code][idx[stage]] *= m
    return ranked(run(med, {k: tuple(v) for k, v in per.items()})[2])


# ── Output ──────────────────────────────────────────────────────────────────


def pct(x: float, base: float) -> str:
    return f"{'+' if x > 0 else ''}{fmt(100 * x / base, 1)} %" if base else "—"


def build(rows, params, other, param_note, levels_note, n, names) -> tuple[dict[str, list[dict]], list[str]]:
    med = med_rows(rows)
    base_state, base_sub, base_mun = run(med, {})
    chk = S.checks(rows)
    mcheck = model_check(rows, med, params)
    scheck = stage_check(rows, params)
    sim = simulate(med, params, n)
    torn = tornado(med, params, sim)
    scen = scenario_ranks(med)
    band = {s: sum(c["n4"] for c in S.cascade(rows, s).values()) for s in ("min", "max")}
    lv = sim["levels"]

    inc = [{"nivel": S.LABELS[k], "base_med": base_state[k], "p5": quantile(lv[k], .05), "p50": quantile(lv[k], .5),
            "p95": quantile(lv[k], .95), "media": statistics.fmean(lv[k])} for k in LEVEL_KEYS]
    inc += [{"nivel": f"N4 {code}", "base_med": base_sub.get(code, 0.0), "p5": quantile(v, .05),
             "p50": quantile(v, .5), "p95": quantile(v, .95), "media": statistics.fmean(v)}
            for code, v in sorted(sim["subs"].items(), key=lambda kv: -base_sub.get(kv[0], 0.0))]

    base_order = sim["base_order"]
    rank_rows = []
    for ibge, r0 in sorted(base_order.items(), key=lambda kv: kv[1]):
        name, region = names[ibge]
        row = {"ibge": ibge, "municipio": name, "rgint": region, "n4_med": base_mun[ibge], "rank_med": r0,
               "rank_p5": quantile(sim["ranks"][ibge], .05), "rank_p95": quantile(sim["ranks"][ibge], .95),
               "prob_top50": sim["top"][ibge] / n}
        row.update({f"rank_{key}": order.get(ibge) for key, _, order in scen})
        rank_rows.append(row)

    scen_rows = []
    top0 = {k for k, r in base_order.items() if r <= TOP}
    top10 = {k for k, r in base_order.items() if r <= 10}
    for key, label, order in scen:
        moved = sorted(top0, key=lambda k: -abs(order[k] - base_order[k]))[:3]
        scen_rows.append({"cenario": key, "descricao": label,
                          "top10_mantidos": len(top10 & {k for k, r in order.items() if r <= 10}),
                          "top50_mantidos": len(top0 & {k for k, r in order.items() if r <= TOP}),
                          "spearman": spearman_rank(base_order, order),
                          "maiores_mudancas_top50": "; ".join(
                              f"{names[k][0] or k} {base_order[k]}→{order[k]}" for k in moved)})

    reg_sum: dict = defaultdict(lambda: [0.0] * n)
    reg_base: dict = defaultdict(float)
    for ibge, vals in sim["munis"].items():
        region = names[ibge][1] or "sem região"
        reg_base[region] += base_mun.get(ibge, 0.0)
        acc = reg_sum[region]
        for i, v in enumerate(vals):
            acc[i] += v
    total = base_state["n4"]
    reg_rows = [{"rgint": reg, "n4_med": reg_base[reg], "parcela": reg_base[reg] / total if total else None,
                 "p5": quantile(v, .05), "p95": quantile(v, .95),
                 "amplitude_relativa": (quantile(v, .95) - quantile(v, .05)) / reg_base[reg] if reg_base[reg] else None}
                for reg, v in sorted(reg_sum.items(), key=lambda kv: -reg_base[kv[0]])]

    tables = {"incerteza.csv": inc, "tornado.csv": torn, "ranking.csv": rank_rows, "regioes.csv": reg_rows,
              "cenarios_ranking.csv": scen_rows, "conferencia_modelo.csv": mcheck,
              "conferencia_etapas.csv": scheck}
    lines = report(base_state, band, inc, torn, scen_rows, reg_rows, rank_rows, sim, chk, mcheck, scheck, other,
                   param_note, levels_note, names)
    return tables, lines


def report(base, band, inc, torn, scen_rows, reg_rows, rank_rows, sim, chk, mcheck, scheck, other, param_note,
           levels_note, names) -> list[str]:
    n4 = inc[4]
    var_total = sum(r["parcela_variancia"] or 0 for r in torn)
    off = [r for r in mcheck if r["razao"] is not None and r["n4_snapshot"] > 1e3 and abs(r["razao"] - 1) > 0.01]
    L = [
        "# Incerteza do N4 do CP2b v5.1 e estabilidade do ranking municipal",
        "",
        f"> Níveis: {levels_note} · Parâmetros: {param_note}",
        f"> {sim['n']} sorteios, semente {SEED}; volumes em milhões de Nm³ de CH₄ por ano. Cada parâmetro é sorteado "
        "numa triangular (mín, med, máx) do próprio CP2b, independente dos outros, e a cascata é refeita município "
        "a município. Nada aqui muda a plataforma.",
        "",
        "## 1. Quanto o N4 do estado pode variar",
        "",
        "| Nível | CP2b med | p5 | p50 | p95 |",
        "|---|---:|---:|---:|---:|",
    ]
    L += [f"| {r['nivel']} | {mi(r['base_med'])} | {mi(r['p5'])} | {mi(r['p50'])} | {mi(r['p95'])} |"
          for r in inc[:5]]
    L += ["",
          f"Intervalo de 90 % do N4: {mi(n4['p5'])}–{mi(n4['p95'])} mi ({pct(n4['p5'] - base['n4'], base['n4'])} a "
          f"{pct(n4['p95'] - base['n4'], base['n4'])} do med). Faixa mín–máx do CP2b, com todos os parâmetros "
          f"juntos no mínimo ou no máximo: {mi(band['min'])}–{mi(band['max'])} mi. As duas são os dois limites: "
          "parâmetros independentes e parâmetros que andam todos juntos.", "",
          "| Substrato | CP2b med | p5 | p95 | Amplitude p5–p95 / med |", "|---|---:|---:|---:|---:|"]
    for r in inc[5:]:
        rel = (r["p95"] - r["p5"]) / r["base_med"] if r["base_med"] else None
        L.append(f"| {r['nivel'][3:]} | {mi(r['base_med'])} | {mi(r['p5'])} | {mi(r['p95'])} | "
                 f"{fmt(100 * rel, 0) + ' %' if rel is not None else '—'} |")

    L += ["", "## 2. Quais parâmetros pesam (tornado)", "",
          "Cada linha põe um parâmetro no mínimo e no máximo do CP2b, com todos os outros na mediana. A última "
          "coluna é a parcela de primeira ordem da variância do N4 nos sorteios: a inclinação entre os dois extremos "
          "ao quadrado vezes a variância da triangular do parâmetro, sobre a variância do N4. Somadas, as parcelas "
          f"dão {fmt(100 * var_total, 0)} %; o resto vem da interação entre parâmetros do mesmo substrato.", "",
          "| Substrato | Parâmetro | mín–med–máx | N4 no mín | N4 no máx | Amplitude | % da variância |",
          "|---|---|---|---:|---:|---:|---:|"]
    for r in torn[:20]:
        L.append(f"| {r['codigo']} | {r['elemento']} | {fmt(r['min'], 3)}–{fmt(r['med'], 3)}–{fmt(r['max'], 3)} "
                 f"| {mi(r['n4_no_min'])} | {mi(r['n4_no_max'])} | {fmt(r['amplitude_pct'], 1)} % "
                 f"| {fmt(100 * (r['parcela_variancia'] or 0), 1)} |")
    if len(torn) > 20:
        L.append(f"\nOs outros {len(torn) - 20} parâmetros estão em `tornado.csv`.")

    top = [r for r in rank_rows if r["rank_med"] <= TOP]
    sure = sum(1 for r in top if r["prob_top50"] >= 0.9)
    L += ["", "## 3. Estabilidade do ranking municipal", "",
          f"Nos sorteios, {sure} dos {TOP} maiores municípios ficam no top {TOP} em pelo menos 90 % das vezes. "
          f"Spearman do ranking inteiro contra o med: mediana {fmt(quantile(sim['spearman'], .5), 3)}, p5 "
          f"{fmt(quantile(sim['spearman'], .05), 3)}.", "",
          "| # | Município | Região intermediária | N4 med | Rank p5–p95 | P(top 50) |", "|---:|---|---|---:|---|---:|"]
    for r in rank_rows[:20]:
        L.append(f"| {r['rank_med']} | {r['municipio'] or r['ibge']} | {r['rgint'] or '—'} | {mi(r['n4_med'], 2)} "
                 f"| {fmt(r['rank_p5'], 0)}–{fmt(r['rank_p95'], 0)} | {fmt(100 * r['prob_top50'], 0)} % |")
    edge = [r for r in rank_rows if 0.1 <= r["prob_top50"] < 0.9]
    if edge:
        L += ["", f"Na fronteira do top {TOP} (entre 10 % e 90 % de chance): "
              + "; ".join(f"{r['municipio'] or r['ibge']} ({fmt(100 * r['prob_top50'], 0)} %)" for r in edge[:15])
              + ("; …" if len(edge) > 15 else "") + "."]
    L += ["", "Nos cenários de literatura da sensibilidade (valor central):", "",
          "| Cenário | Top 10 mantidos | Top 50 mantidos | Spearman | Maiores mudanças no top 50 |",
          "|---|---:|---:|---:|---|"]
    L += [f"| {r['cenario']} | {r['top10_mantidos']} | {r['top50_mantidos']} | {fmt(r['spearman'], 3)} "
          f"| {r['maiores_mudancas_top50']} |" for r in scen_rows]
    L += ["", "Por região intermediária do IBGE:", "",
          "| Região | % do N4 | N4 med | p5 | p95 | Amplitude p5–p95 / med |", "|---|---:|---:|---:|---:|---:|"]
    L += [f"| {r['rgint']} | {fmt(100 * (r['parcela'] or 0), 1)} | {mi(r['n4_med'])} | {mi(r['p5'])} | "
          f"{mi(r['p95'])} | {fmt(100 * (r['amplitude_relativa'] or 0), 0)} % |" for r in reg_rows]

    L += ["", "## 4. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    L += [f"| {name} | {'ok' if ok else 'FALHOU'} | {detail} |" for name, ok, detail in chk]
    L.append(f"| modelo reproduz o mín e o máx do snapshot por substrato (±1 %) | {'ok' if not off else 'não'} | "
             + ("todos os substratos" if not off else "; ".join(
                 f"{r['codigo']} {r['cenario']} ×{fmt(r['razao'], 3)}" for r in off)) + " |")
    if off:
        L += ["", "Onde o modelo não reproduz o snapshot, o CP2b varia algo que não está em `cp2b_parametros.csv` "
              "como multiplicador (a base, ou o FL espacial de cada município). Nesses substratos o intervalo acima "
              "é o dos parâmetros, não o do CP2b inteiro. Detalhe em `conferencia_modelo.csv`."]
        bad = [r for r in scheck if r["razao_snapshot"] is not None
               and not math.isclose(r["razao_snapshot"], r["razao_modelo"], rel_tol=0.01)]
        if bad:
            L += ["", "Onde está a diferença, etapa por etapa (razão do cenário sobre o med; snapshot × modelo):", "",
                  "| Substrato | Cenário | Etapa | Snapshot | Modelo |", "|---|---|---|---:|---:|"]
            L += [f"| {r['codigo']} | {r['cenario']} | {r['etapa']} | {fmt(r['razao_snapshot'], 3)} "
                  f"| {fmt(r['razao_modelo'], 3)} |" for r in bad]
    if other:
        L += ["", f"Elementos do arquivo de parâmetros não sorteados: {', '.join(other)}."]

    L += ["", "## Como ler", "",
          "- O intervalo de 90 % supõe parâmetros independentes. Parâmetros com a mesma fonte (por exemplo o FC de "
          "vários rebanhos) andam juntos na vida real; por isso o intervalo verdadeiro fica entre este e a faixa "
          "mín–máx do CP2b, mais perto deste quanto mais independentes forem as fontes.",
          "- A triangular dá peso à mediana do CP2b. Ela não diz que a mediana está certa: a sensibilidade "
          "(`outputs/sensibilidade_cp2b/`) é que testa a mediana contra a literatura.",
          "- U e o FL espacial de cada município ficam como estão no med; só o multiplicador do FL do arquivo de "
          "parâmetros, quando existe, é sorteado.",
          "- Rank 1 = maior N4 municipal (soma dos substratos). Cenários de definição ficam fora do ranking, porque "
          "não são leituras possíveis do CP2b."]
    return L


def write_csv(path: Path, rows: list[dict]) -> None:
    if rows:
        S.write_csv(path, rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, levels_note = S.read_levels()
    params, other, param_note = parameters()
    if rows is None or not params:
        why = levels_note if rows is None else param_note
        (OUT / "RELATORIO.md").write_text(
            "# Incerteza do N4 do CP2b v5.1 e estabilidade do ranking municipal\n\n"
            f"Não rodou: {why}. O sorteio precisa dos níveis e dos parâmetros do snapshot v5.1 com o sha256 do "
            "loader.\n", encoding="utf-8")
        print(f"Sem incerteza: {why}")
        return
    n = int(os.environ.get("CP2B_MC_N", "5000"))
    tables, lines = build(rows, params, other, param_note, levels_note, n, municipalities())
    for name, table in tables.items():
        write_csv(OUT / name, table)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [name for name, ok, _ in S.checks(rows) if not ok]
    print(f"{n} sorteios · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
