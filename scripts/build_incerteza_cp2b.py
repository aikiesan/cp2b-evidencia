#!/usr/bin/env python3
"""
CP2b v5.1 uncertainty: how wide the state N4 really is, which parameters drive
it, and how stable the municipal ranking is.

The article reports the CP2b min and max scenarios. Those put every parameter
of every substrate at its minimum (or maximum) at the same time, which no
reviewer reads as an interval. This script samples each parameter inside its
own CP2b range instead and recomputes the cascade municipality by municipality:

  N1  = N1_ref × Π (g, ST, SV, BMP, direto) / ref × base factor
  N2  = N1 × FC_ref × FC / ref × residual
  N3a = N2 × FCo_ref × FCo / ref × residual
  U   = U(N3a), through the row's own points
  N3  = N3a − U
  N4  = N3 × FS × FL × spatial factor(N3)

It is built so that every parameter at its CP2b min, med or max reproduces the
snapshot's min, med or max row by row. Three things in the snapshot are not a
plain multiplier of cp2b_parametros.csv, and the model takes each from the
snapshot itself:

  spatial factor  FS × FL of a row over the FS × FL of the parameter file. It
                  falls with supply (no plant closes where there is little
                  residue), so it is interpolated on the row's N3 between its
                  own min, med and max points.
  existing use    U of a row is interpolated on its N3a between its own min,
                  med and max points, and never above N3a. The report also
                  checks the rule behind it, U = min(existing use, N3a).
  residuals       what the snapshot varies at N1, FC or FCo beyond the
                  parameter file (the base, mostly), per row, as a factor that
                  goes through the row's min, med and max.

Draws are triangular (min, med, max), independent across parameters and
substrates; residuals are drawn as a position t in triangular(−1, 0, 1) that
maps to the row's min, med and max. Independence is an assumption: parameters
that share a source move together, and the CP2b min-max band is the opposite
limit, everything moving together. Both are reported. A substrate whose med is
zero (pasture: FC med 0) is scaled from its max scenario instead.

Outputs answer three questions:

  incerteza   state N1-N4 and N4 per substrate: p5, p50, p95 of the draws
  tornado     each parameter at its min and max, the others at the median
              (swing in N4), and its first-order share of the N4 variance
  ranking     municipal N4: chance of staying in the top 50, rank p5-p95, N4
              p5-p95, rank and N4 in each literature scenario of the sensitivity
              script, and the same by intermediate region (IBGE RGInt)

Nothing here changes the platform, the snapshot or the article numbers.

Run from the repo root (CP2B_MC_N draws, default 20000; fixed seed):
  python3 scripts/build_incerteza_cp2b.py

Outputs (outputs/incerteza_cp2b/):
  incerteza.csv · tornado.csv · ranking.csv · regioes.csv · cenarios_ranking.csv · conferencia_modelo.csv
  RELATORIO.md
"""

from __future__ import annotations

import csv
import importlib.util
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "incerteza_cp2b"
SEED = 20261023
TOP = 50
BATCH = 250
SCEN = ("min", "med", "max")
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
STAGES = ("n1", "n2", "n3a", "n4")
RESIDUAL = {"n1": "base N1 (snapshot)", "n2": "FC (snapshot)", "n3a": "FCo (snapshot)"}
RESIDUAL_TOL = 1e-6
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


def _div(a, b):
    """a / b, with 0 where b is 0."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    out = np.zeros(np.broadcast(a, b).shape)
    np.divide(a, b, out=out, where=b != 0)
    return out


def _pw(t: np.ndarray, k0: np.ndarray, k1: np.ndarray, k2: np.ndarray) -> np.ndarray:
    """Piecewise linear through (−1, k0), (0, k1), (1, k2); t is (D, 1) or (D,), knots (R,)."""
    return np.where(t < 0, k1 + t * (k1 - k0), k1 + t * (k2 - k1))


def _knots(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per row, the three (x, y) points of the scenarios sorted by x."""
    order = np.argsort(x, axis=0, kind="stable")
    return np.take_along_axis(x, order, axis=0), np.take_along_axis(y, order, axis=0)


def _interp(v: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Piecewise linear in v through each row's three points, flat outside them."""
    x0, x1, x2 = xs
    y0, y1, y2 = ys
    a = y0 + _div(v - x0, x1 - x0) * (y1 - y0)
    b = y1 + _div(v - x1, x2 - x1) * (y2 - y1)
    return np.where(v <= x0, y0, np.where(v <= x1, np.where(x1 > x0, a, y1),
                                          np.where(v <= x2, np.where(x2 > x1, b, y2), y2)))


class Model:
    """The CP2b cascade per row (municipality × substrate), rebuilt from the snapshot's three scenarios."""

    def __init__(self, rows: list[dict], params: dict[tuple[str, str], tuple[float, float, float]]):
        table: dict = {}
        for r in rows:
            if r["cenario"] in SCEN:
                table.setdefault((r["ibge"], r["codigo"]), [None, None, None])[SCEN.index(r["cenario"])] = r
        keys = sorted(table)
        self.codes = sorted({c for _, c in keys})
        self.munis = sorted({m for m, _ in keys})
        n_rows, n_sub = len(keys), len(self.codes)
        ci = {c: i for i, c in enumerate(self.codes)}
        mi_ = {m: i for i, m in enumerate(self.munis)}
        self.sub = np.array([ci[c] for _, c in keys], dtype=int)
        self.mun = np.array([mi_[m] for m, _ in keys], dtype=int)
        lv = {k: np.zeros((3, n_rows)) for k in ("n1", "n2", "n3a", "u", "n3", "n4", "fsfl")}
        for j, key in enumerate(keys):
            for s, r in enumerate(table[key]):
                if r is not None:
                    for k in lv:
                        lv[k][s, j] = r[k]
        self.snapshot = lv

        # As in the file: index 0, 1, 2 is the snapshot's min, med and max scenario.
        self.params = {k: tuple(v) for k, v in params.items() if k[0] in ci and k[1] in STAGE}
        # Reference scenario per substrate: med, or max when the med N3a is zero (pasture: FC med 0).
        n3a_tot = np.stack([np.bincount(self.sub, lv["n3a"][s], n_sub) for s in range(3)])
        self.ref = np.array([2 if n3a_tot[1, i] == 0 and n3a_tot[2, i] > 0 else 1 for i in range(n_sub)], dtype=int)
        ref_row = self.ref[self.sub]
        cols = np.arange(n_rows)

        # A parameter that is zero in its substrate's reference scenario cannot scale it: it is dropped,
        # and what the snapshot does at that stage goes into the residual.
        self.dropped = sorted(k for k, v in self.params.items()
                              if STAGE[k[1]] != "n4" and v[self.ref[ci[k[0]]]] == 0)
        for k in self.dropped:
            del self.params[k]
        # Products of the parameter file by stage and scenario (n4: absolute FS × FL).
        prod = np.ones((3, n_sub, 4))
        for (c, el), v in self.params.items():
            for s in range(3):
                prod[s, ci[c], STAGES.index(STAGE[el])] *= v[s]
        self.prod = prod

        # Stage values of the snapshot per row and scenario: N1, N2/N1, N3a/N2.
        stage = np.stack([lv["n1"], _div(lv["n2"], lv["n1"]), _div(lv["n3a"], lv["n2"])])   # (3 stages, 3 scen, R)
        self.base = stage[:, ref_row, cols]                                                   # (3, R) at ref
        # Residual knots: snapshot stage ratio to ref over the parameter-file ratio to ref.
        knots = np.ones((3, 3, n_rows))
        self.residuals: dict = {}
        upstream = (None, lv["n1"], lv["n2"])          # a stage ratio is undefined where its input is zero
        for st in range(3):
            pref = prod[ref_row, self.sub, st]
            for s in range(3):
                ratio = _div(stage[st, s], self.base[st])
                pr = _div(prod[s, self.sub, st], pref)
                ok = (self.base[st] > 0) & (pr > 0)
                if upstream[st] is not None:
                    ok &= upstream[st][s] > 0
                knots[st, s] = np.where(ok, _div(ratio, pr), 1.0)
            for i, c in enumerate(self.codes):
                m = self.sub == i
                if np.any(np.abs(knots[st, :, m] - 1) > RESIDUAL_TOL):
                    self.residuals[(c, RESIDUAL[STAGES[st]])] = st
        self.knots = knots

        # Existing use, interpolated on N3a, and the spatial factor (FS × FL of the row over that of the
        # parameter file), interpolated on N3: both go through the row's own min, med and max points.
        self.exist = lv["u"].max(axis=0)
        self.u_knots = _knots(lv["n3a"], lv["u"])
        self.sp_knots = _knots(lv["n3"], _div(lv["fsfl"], prod[:, self.sub, 3]))

        # Rows sorted by municipality and by substrate, for fast sums.
        self._mun_order = np.argsort(self.mun, kind="stable")
        self._mun_starts = np.searchsorted(self.mun[self._mun_order], np.arange(len(self.munis)))
        self._sub_order = np.argsort(self.sub, kind="stable")
        self._sub_starts = np.searchsorted(self.sub[self._sub_order], np.arange(n_sub))

    # Distributions: parameters on their own scale, residuals as t in [−1, 1].
    def dists(self) -> dict:
        out = {}
        for k, (a, med, b) in self.params.items():
            lo, hi = min(a, b), max(a, b)
            out[k] = (lo, min(max(med, lo), hi), hi)
        out.update({k: (-1.0, 0.0, 1.0) for k in self.residuals})
        return out

    def spatial(self, n3: np.ndarray) -> np.ndarray:
        return _interp(n3, *self.sp_knots)

    def existing_use(self, n3a: np.ndarray) -> np.ndarray:
        return np.minimum(_interp(n3a, *self.u_knots), n3a)

    def evaluate(self, values: dict | None = None, extra: dict | None = None) -> dict:
        """State levels (D,), N4 per substrate (D, S) and per municipality (D, M).

        values: {key: array (D,)} for any parameter or residual, the median (t = 0) elsewhere.
        extra: {(code, stage): multiplier} applied on top, as the sensitivity scenarios do.
        """
        values = values or {}
        d = max([len(np.atleast_1d(v)) for v in values.values()] or [1])
        n_sub = len(self.codes)
        mult = np.ones((d, n_sub, 4))
        for (c, el), v in self.params.items():
            i, st = self.codes.index(c), STAGES.index(STAGE[el])
            x = np.broadcast_to(np.asarray(values.get((c, el), v[1]), float), (d,))
            if st < 3:
                mult[:, i, st] *= x / v[self.ref[i]]
            else:
                mult[:, i, st] *= x
        for (c, stage), m in (extra or {}).items():
            if c in self.codes:
                mult[:, self.codes.index(c), STAGES.index(stage)] *= m
        res = np.ones((3, d, len(self.sub)))
        for st in range(3):
            res[st] = self.knots[st, 1]
        for key, st in self.residuals.items():
            rows = self.sub == self.codes.index(key[0])
            t = np.broadcast_to(np.asarray(values.get(key, 0.0), float), (d,))[:, None]
            k = self.knots[st][:, rows]
            res[st][:, rows] = _pw(t, k[0], k[1], k[2])
        m = mult[:, self.sub, :]                                                             # (D, R, 4)
        n1 = self.base[0] * m[..., 0] * res[0]
        n2 = n1 * self.base[1] * m[..., 1] * res[1]
        n3a = n2 * self.base[2] * m[..., 2] * res[2]
        n3 = n3a - self.existing_use(n3a)
        n4 = n3 * m[..., 3] * self.spatial(n3)
        return {"state": {"n1": n1.sum(1), "n2": n2.sum(1), "n3a": n3a.sum(1), "n3": n3.sum(1), "n4": n4.sum(1)},
                "sub": np.add.reduceat(n4[:, self._sub_order], self._sub_starts, axis=1),
                "mun": np.add.reduceat(n4[:, self._mun_order], self._mun_starts, axis=1),
                "rows": n4}

    def at(self, i: int) -> dict:
        """Every parameter at its min (0), med (1) or max (2); residuals at t = −1, 0, 1."""
        vals = {k: np.array([v[i]]) for k, v in self.params.items()}
        vals.update({k: np.array([i - 1.0]) for k in self.residuals})
        return self.evaluate(vals)

    def residual_range(self, key) -> tuple[float, float, float]:
        """The residual factor of a substrate at min, med and max (substrate totals)."""
        st = self.residuals[key]
        rows = self.sub == self.codes.index(key[0])
        w = self.snapshot["n1"][1][rows] + 1e-12
        return tuple(float(np.average(self.knots[st, s][rows], weights=w)) for s in range(3))


def check_model(model: Model) -> tuple[list[dict], list[tuple[str, bool, str]]]:
    """Per substrate and scenario: the model's N4 against the snapshot's; and the U rule."""
    out = []
    worst = 0.0
    for i, scen in enumerate(SCEN):
        got = model.at(i)["sub"][0]
        want = np.bincount(model.sub, model.snapshot["n4"][i], len(model.codes))
        for c, g, w in zip(model.codes, got, want):
            r = g / w if w else (1.0 if g == 0 else None)
            out.append({"codigo": c, "cenario": scen, "n4_snapshot": w, "n4_modelo": g, "razao": r})
            if w > 1e3:
                worst = max(worst, abs((r or 0) - 1))
    lv = model.snapshot
    u_rule = np.abs(lv["u"] - np.minimum(model.exist, lv["n3a"]))
    bad = u_rule > 1e-6 * np.maximum(1.0, lv["u"])
    share = float(u_rule.sum() / lv["u"].sum()) if lv["u"].sum() else 0.0
    checks = [("modelo reproduz mín, med e máx do snapshot por substrato (±0,1 %)", worst <= 1e-3,
               f"maior desvio {fmt(100 * worst, 3)} %"),
              ("U = mín(uso existente, N3a) em cada linha e cenário (informativo: o modelo interpola o U)",
               "vale" if not bad.any() else "não vale", f"{int(bad.sum())} linhas fora; {fmt(100 * share, 2)} % do U")]
    return out, checks


def draw(model: Model, n: int, seed: int = SEED) -> dict:
    """n draws in batches: state levels, N4 per substrate and per municipality, municipal ranks."""
    rng = np.random.default_rng(seed)
    dists = model.dists()
    keys = sorted(dists)
    n_mun = len(model.munis)
    levels = {k: np.empty(n) for k in LEVEL_KEYS}
    subs = np.empty((n, len(model.codes)))
    munis = np.empty((n, n_mun))
    for start in range(0, n, BATCH):
        d = min(BATCH, n - start)
        vals = {}
        for k in keys:
            lo, mode, hi = dists[k]
            vals[k] = np.full(d, mode) if lo == hi else rng.triangular(lo, mode, hi, d)
        out = model.evaluate(vals)
        for k in LEVEL_KEYS:
            levels[k][start:start + d] = out["state"][k]
        subs[start:start + d] = out["sub"]
        munis[start:start + d] = out["mun"]
    ranks = rank_rows(munis)
    base = model.at(1)["mun"]
    r0 = rank_rows(base)[0]
    spearman = 1 - 6 * ((ranks - r0) ** 2).sum(1) / (n_mun * (n_mun ** 2 - 1)) if n_mun > 1 else np.ones(n)
    return {"n": n, "levels": levels, "subs": subs, "munis": munis, "ranks": ranks, "r0": r0,
            "spearman": spearman}


def rank_rows(x: np.ndarray) -> np.ndarray:
    """Rank of each column in each row, 1 = largest; ties broken by column order (ibge)."""
    x = np.atleast_2d(x)
    order = np.argsort(-x, axis=1, kind="stable")
    ranks = np.empty_like(order)
    np.put_along_axis(ranks, order, np.arange(1, x.shape[1] + 1)[None, :].repeat(x.shape[0], 0), axis=1)
    return ranks


def triangular_var(lo: float, mode: float, hi: float) -> float:
    return (lo * lo + mode * mode + hi * hi - lo * mode - lo * hi - mode * hi) / 18


def tornado(model: Model, var_n4: float) -> list[dict]:
    """Each parameter (and residual) at its min and max, the others at the median.

    The variance share is first order: the slope between the two ends squared
    times the variance of the parameter's triangular, over the N4 variance of
    the draws. It is exact where N4 is linear in the parameter.
    """
    base = float(model.at(1)["state"]["n4"][0])
    out = []
    for key, (lo, mode, hi) in sorted(model.dists().items()):
        if lo == hi:
            continue
        n4 = model.evaluate({key: np.array([lo, hi])})["state"]["n4"]
        slope = (n4[1] - n4[0]) / (hi - lo)
        shown = model.residual_range(key) if key in model.residuals else (lo, mode, hi)
        out.append({"codigo": key[0], "elemento": key[1], "min": shown[0], "med": shown[1], "max": shown[2],
                    "n4_no_min": float(n4[0]), "n4_no_max": float(n4[1]), "amplitude": float(abs(n4[1] - n4[0])),
                    "amplitude_pct": 100 * float(abs(n4[1] - n4[0])) / base if base else None,
                    "parcela_variancia": float(slope * slope * triangular_var(lo, mode, hi) / var_n4)
                    if var_n4 else None})
    return sorted(out, key=lambda r: -r["amplitude"])


# ── Ranking under the literature scenarios ──────────────────────────────────


def scenario_ranks(model: Model) -> list[tuple[str, str, np.ndarray, np.ndarray]]:
    """(key, label, municipal ranks, municipal N4) for each literature or hypothesis scenario of the
    sensitivity script."""
    lib = S.literature()
    out = []
    found = {}
    for key, kind, label, codes, terms, _ in S.SCENARIOS:
        mult = S.multipliers(lib, codes, terms)
        found[key] = mult
        if mult is None or kind == "definição":
            continue
        mun = model.evaluate(extra={k: v[1] for k, v in mult.items()})["mun"]
        out.append((key, label, rank_rows(mun)[0], mun[0]))
    for key, label, parts in S.COMBINED:
        if any(found.get(p) is None for p in parts):
            continue
        mult: dict = {}
        for p in parts:
            for k, v in found[p].items():
                mult[k] = mult.get(k, 1.0) * v[1]
        mun = model.evaluate(extra=mult)["mun"]
        out.append((key, label, rank_rows(mun)[0], mun[0]))
    return out


# ── Output ──────────────────────────────────────────────────────────────────


def q(a, p) -> float:
    return float(np.quantile(a, p))


def pct(x: float, base: float) -> str:
    return f"{'+' if x > 0 else ''}{fmt(100 * x / base, 1)} %" if base else "—"


def build(rows, params, other, param_note, levels_note, n, names) -> tuple[dict[str, list[dict]], list[str]]:
    model = Model(rows, params)
    chk = S.checks(rows)
    mcheck, mchecks = check_model(model)
    med = model.at(1)
    base_state = {k: float(v[0]) for k, v in med["state"].items()}
    base_sub, base_mun = med["sub"][0], med["mun"][0]
    sim = draw(model, n)
    lv = sim["levels"]
    torn = tornado(model, float(np.var(lv["n4"])) if n > 1 else 0.0)
    scen = scenario_ranks(model)
    band = {s: float(model.snapshot["n4"][SCEN.index(s)].sum()) for s in ("min", "max")}

    inc = [{"nivel": S.LABELS[k], "base_med": base_state[k], "p5": q(lv[k], .05), "p50": q(lv[k], .5),
            "p95": q(lv[k], .95), "media": float(lv[k].mean())} for k in LEVEL_KEYS]
    for i in np.argsort(-base_sub, kind="stable"):
        v = sim["subs"][:, i]
        inc.append({"nivel": f"N4 {model.codes[i]}", "base_med": float(base_sub[i]), "p5": q(v, .05),
                    "p50": q(v, .5), "p95": q(v, .95), "media": float(v.mean())})

    r0 = sim["r0"]
    ranks = sim["ranks"]
    rank_out = []
    for j in np.argsort(r0, kind="stable"):
        ibge = model.munis[j]
        name, region = names[ibge]
        row = {"ibge": ibge, "municipio": name, "rgint": region, "n4_med": float(base_mun[j]),
               "n4_p5": q(sim["munis"][:, j], .05), "n4_p95": q(sim["munis"][:, j], .95), "rank_med": int(r0[j]),
               "rank_p5": q(ranks[:, j], .05), "rank_p95": q(ranks[:, j], .95),
               "prob_top50": float((ranks[:, j] <= TOP).mean())}
        row.update({f"rank_{key}": int(order[j]) for key, _, order, _ in scen})
        row.update({f"n4_{key}": float(mun[j]) for key, _, _, mun in scen})
        rank_out.append(row)

    scen_rows = []
    top0, top10 = r0 <= TOP, r0 <= 10
    n_mun = len(model.munis)
    for key, label, order, _ in scen:
        moved = [j for j in np.argsort(-np.abs(order - r0) * top0, kind="stable")[:3] if top0[j]]
        rho = 1 - 6 * float(((order - r0) ** 2).sum()) / (n_mun * (n_mun ** 2 - 1)) if n_mun > 1 else 1.0
        scen_rows.append({"cenario": key, "descricao": label,
                          "top10_mantidos": int((top10 & (order <= 10)).sum()),
                          "top50_mantidos": int((top0 & (order <= TOP)).sum()), "spearman": rho,
                          "maiores_mudancas_top50": "; ".join(
                              f"{names[model.munis[j]][0] or model.munis[j]} {r0[j]}→{order[j]}" for j in moved)})

    regions = [names[m][1] or "sem região" for m in model.munis]
    reg_names = sorted(set(regions))
    onehot = np.array([[1.0 if r == g else 0.0 for g in reg_names] for r in regions])
    reg_draws = sim["munis"] @ onehot
    reg_base = base_mun @ onehot
    total = base_state["n4"]
    reg_rows = [{"rgint": g, "n4_med": float(reg_base[i]), "parcela": float(reg_base[i]) / total if total else None,
                 "p5": q(reg_draws[:, i], .05), "p95": q(reg_draws[:, i], .95),
                 "amplitude_relativa": (q(reg_draws[:, i], .95) - q(reg_draws[:, i], .05)) / float(reg_base[i])
                 if reg_base[i] else None}
                for i, g in sorted(enumerate(reg_names), key=lambda kv: -reg_base[kv[0]])]

    tables = {"incerteza.csv": inc, "tornado.csv": torn, "ranking.csv": rank_out, "regioes.csv": reg_rows,
              "cenarios_ranking.csv": scen_rows, "conferencia_modelo.csv": mcheck}
    lines = report(model, base_state, band, inc, torn, scen_rows, reg_rows, rank_out, sim, chk + mchecks, other,
                   param_note, levels_note)
    return tables, lines


def report(model, base, band, inc, torn, scen_rows, reg_rows, rank_out, sim, chk, other, param_note,
           levels_note) -> list[str]:
    n4 = inc[4]
    var_total = sum(r["parcela_variancia"] or 0 for r in torn)
    L = [
        "# Incerteza do N4 do CP2b v5.1 e estabilidade do ranking municipal",
        "",
        f"> Níveis: {levels_note} · Parâmetros: {param_note}",
        f"> {sim['n']} sorteios, semente {SEED}; volumes em milhões de Nm³ de CH₄ por ano. Cada parâmetro é sorteado "
        "numa triangular (mín, med, máx) do próprio CP2b, independente dos outros, e a cascata é refeita município "
        "a município. O FL espacial acompanha o N3 de cada município, o U acompanha o N3a, e o que o "
        "snapshot varia fora do arquivo de parâmetros entra como fator residual. Com tudo no mín, med ou máx, o "
        "modelo reproduz o snapshot linha a linha (seção 4). Nada aqui muda a plataforma.",
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
    ref_max = [c for c, r in zip(model.codes, model.ref) if r == 2]
    if ref_max:
        L += ["", f"Med zero no CP2b, escalados a partir do cenário máx: {', '.join(ref_max)}. O p95 deles mostra "
              "quanto o máx do CP2b pesa quando o FC (ou outro fator) deixa de ser zero."]

    L += ["", "## 2. Quais parâmetros pesam (tornado)", "",
          "Cada linha põe um parâmetro no mínimo e no máximo do CP2b, com todos os outros na mediana. A última "
          "coluna é a parcela de primeira ordem da variância do N4 nos sorteios: a inclinação entre os dois extremos "
          "ao quadrado vezes a variância da triangular do parâmetro, sobre a variância do N4. Somadas, as parcelas "
          f"dão {fmt(100 * var_total, 0)} %; o resto vem da interação entre parâmetros e do FL espacial. Linhas "
          "\"(snapshot)\" são o que o CP2b varia fora do arquivo de parâmetros; a faixa delas é o fator médio do "
          "substrato no mín, med e máx.", "",
          "| Substrato | Parâmetro | mín–med–máx | N4 no mín | N4 no máx | Amplitude | % da variância |",
          "|---|---|---|---:|---:|---:|---:|"]
    for r in torn[:20]:
        L.append(f"| {r['codigo']} | {r['elemento']} | {fmt(r['min'], 3)}–{fmt(r['med'], 3)}–{fmt(r['max'], 3)} "
                 f"| {mi(r['n4_no_min'])} | {mi(r['n4_no_max'])} | {fmt(r['amplitude_pct'], 1)} % "
                 f"| {fmt(100 * (r['parcela_variancia'] or 0), 1)} |")
    if len(torn) > 20:
        L.append(f"\nOs outros {len(torn) - 20} parâmetros estão em `tornado.csv`.")

    top = [r for r in rank_out if r["rank_med"] <= TOP]
    sure = sum(1 for r in top if r["prob_top50"] >= 0.9)
    L += ["", "## 3. Estabilidade do ranking municipal", "",
          f"Nos sorteios, {sure} dos {TOP} maiores municípios ficam no top {TOP} em pelo menos 90 % das vezes. "
          f"Spearman do ranking inteiro contra o med: mediana {fmt(q(sim['spearman'], .5), 3)}, p5 "
          f"{fmt(q(sim['spearman'], .05), 3)}.", "",
          "| # | Município | Região intermediária | N4 med | N4 p5–p95 | Rank p5–p95 | P(top 50) |",
          "|---:|---|---|---:|---|---|---:|"]
    for r in rank_out[:20]:
        L.append(f"| {r['rank_med']} | {r['municipio'] or r['ibge']} | {r['rgint'] or '—'} | {mi(r['n4_med'], 2)} "
                 f"| {mi(r['n4_p5'], 2)}–{mi(r['n4_p95'], 2)} | {fmt(r['rank_p5'], 0)}–{fmt(r['rank_p95'], 0)} "
                 f"| {fmt(100 * r['prob_top50'], 0)} % |")
    edge = [r for r in rank_out if 0.1 <= r["prob_top50"] < 0.9]
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
    L += [f"| {name} | {ok if isinstance(ok, str) else 'ok' if ok else 'FALHOU'} | {detail} |"
          for name, ok, detail in chk]
    if model.residuals:
        L += ["", "Fatores residuais (o que o snapshot varia fora de `cp2b_parametros.csv`), fator médio do "
              "substrato no mín, med e máx: " + "; ".join(
                  f"{c} {lab} " + "–".join(fmt(x, 3) for x in model.residual_range((c, lab)))
                  for c, lab in sorted(model.residuals)) + "."]
    if model.dropped:
        L += ["", "Parâmetros zero no cenário de referência do substrato, que não podem servir de multiplicador "
              "(a variação do snapshot nessa etapa fica no fator residual): "
              + ", ".join(f"{c} {el}" for c, el in model.dropped) + "."]
    if other:
        L += ["", f"Elementos do arquivo de parâmetros não sorteados: {', '.join(other)}."]

    L += ["", "## Como ler", "",
          "- O intervalo de 90 % supõe parâmetros independentes. Parâmetros com a mesma fonte (por exemplo o FC de "
          "vários rebanhos) andam juntos na vida real; por isso o intervalo verdadeiro fica entre este e a faixa "
          "mín–máx do CP2b, mais perto deste quanto mais independentes forem as fontes.",
          "- A triangular dá peso à mediana do CP2b. Ela não diz que a mediana está certa: a sensibilidade "
          "(`outputs/sensibilidade_cp2b/`) é que testa a mediana contra a literatura.",
          "- O FL espacial de cada município é interpolado no N3 dele entre os seus pontos mín, med e máx do "
          "snapshot. Entre esses pontos a interpolação é linear, e o FL de um município depende só da oferta dele, "
          "não da dos vizinhos; as duas coisas são aproximações.",
          "- Nos cenários do ranking o FL espacial responde ao N3 do cenário; por isso o N4 de um cenário aqui pode "
          "diferir um pouco do da sensibilidade, que mantém o FS × FL de cada município.",
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
    n = int(os.environ.get("CP2B_MC_N", "20000"))
    tables, lines = build(rows, params, other, param_note, levels_note, n, municipalities())
    for name, table in tables.items():
        write_csv(OUT / name, table)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [ln.split("|")[1].strip() for ln in lines if "| FALHOU |" in ln]
    print(f"{n} sorteios · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
