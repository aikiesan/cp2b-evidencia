#!/usr/bin/env python3
"""
CP2b v5.1 municipal uncertainty when the hub network moves.

build_incerteza_cp2b.py draws every parameter and lets each municipality's
spatial FL follow only its own N3. The supply perturbation of the fl_v5
(fl_espacial/analises_v52/v52_perturbacao.py) shows that a municipality's FL
also moves when the greedy allocation picks other hubs, because supply changed
somewhere else. This script puts the two together: each parameter draw of
build_incerteza_cp2b.py (same seed, same order) gets one perturbed run of the
allocation, drawn at random, and the FL of every municipality × substrate
moves by what that run changed:

  spatial'(N3) = clip(spatial(N3) + ρ · (FL_run − FL_v51) / (FS × FL of the parameter file), 0, cap)

ρ is the snapshot's FS × FL over the fl_v5 FL B of the row (one value per
substrate: the FS the snapshot used), so the shift is the run's FL change in
the units of the model's spatial factor; cap keeps the row's FL at most 1.
The runs are those of data/fl_v51/pert_fl_rodadas_med.csv (med, three noise
designs, 30 runs each), checked against the manifest. Without the network
term the draws are those of build_incerteza_cp2b.py, and the script checks it.
Nothing here changes the platform or the numbers.

Run from the repo root on the machine with the CP2b v5.1 snapshot
(CP2B_MC_N draws, default 20000; fixed seed):
  python3 scripts/build_incerteza_rede.py

Outputs (outputs/incerteza_rede/):
  ranking_rede.csv · regioes_rede.csv · resumo_rede.csv · conferencia.csv · mapa_rede_amplitude.png · RELATORIO.md
"""
from __future__ import annotations

import csv
import importlib.util
import math
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fl_v51"
OUT = ROOT / "outputs" / "incerteza_rede"
INC_RANKING = ROOT / "outputs" / "incerteza_cp2b" / "ranking.csv"
RUNS = "pert_fl_rodadas_med.csv"
FLV5 = "fl_v5_municipio_substrato.csv"
DESIGNS = (("mun10", "10 % por município"), ("mun30", "30 % por município"),
           ("sub20_mun20", "20 % por substrato × 20 % por município"))
MAP_DESIGN = "mun30"
RHO_TOL = 1e-6          # relative spread allowed in FS × FL / FL B within a substrate (med)
FL_TOL = 1e-6           # FL_v51 of the runs file against the fl_v5 table
ZERO_NM3 = 1.0          # a municipality's N4 below 1 Nm³/year is zero
WIDER = (1.25, 2.0)     # interval width ratios counted in the report
PROB_MOVE = 0.10        # a change in the top-50 probability counted in the report
EPS = 1e-12


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I = _load(ROOT / "scripts" / "build_incerteza_cp2b.py")  # noqa: E741
F = _load(ROOT / "scripts" / "build_fl_espacial.py")
S, M = I.S, F.M
fmt, mi, q = I.fmt, I.mi, I.q
SOURCE = ("Fonte: CP2b v5.1 (snapshot), sorteios de build_incerteza_cp2b.py e rodadas da perturbação do fl_v5 "
          "(data/fl_v51/); malha municipal do IBGE.")


# ── The model with the network term ─────────────────────────────────────────


class RedeModel(I.Model):
    """I.Model with an additive shift of the spatial factor per draw and row (None: the plain model)."""

    shift: np.ndarray | None = None
    cap: np.ndarray | None = None

    def spatial(self, n3: np.ndarray) -> np.ndarray:
        base = super().spatial(n3)
        if self.shift is None:
            return base
        return np.minimum(np.maximum(base + self.shift, 0.0), np.maximum(base, self.cap))


def runs_table(rows: list[dict]) -> tuple[dict[str, dict], int]:
    """{design: {(ibge, code): (FL_v51, array of the runs' FL)}} and the number of runs (columns r01…)."""
    cols = sorted(c for c in rows[0] if c[:1] == "r" and c[1:].isdigit()) if rows else []
    out: dict = defaultdict(dict)
    for r in rows:
        fl = np.array([float(r[c]) for c in cols])
        out[r["desenho"]][(F._ibge(r["ibge"]), r["codigo"])] = (float(r["FL_v51"]), fl)
    return dict(out), len(cols)


def link(model: RedeModel, fl_rows: list[dict], runs: dict, n_runs: int) -> dict:
    """Shift matrices per design (runs × rows), the cap per row, ρ per substrate and the checks."""
    n_rows = len(model.sub)
    index = {(model.munis[m], model.codes[s]): j for j, (m, s) in enumerate(zip(model.mun, model.sub))}
    fsfl, n3 = model.snapshot["fsfl"][1], model.snapshot["n3"][1]
    flb = {(F._ibge(r["ibge"]), r["codigo"]): float(r["FL_codig_alocado"]) for r in fl_rows if r["cenario"] == "med"}
    ratios, zero_bad = defaultdict(list), defaultdict(int)
    for key, f in flb.items():
        j = index.get(key)
        if j is None or n3[j] <= 0:
            continue
        if f > EPS:
            ratios[key[1]].append(fsfl[j] / f)
        elif fsfl[j] > EPS:
            zero_bad[key[1]] += 1
    rho, spread_bad = {}, []
    for code, xs in ratios.items():
        lo, hi = min(xs), max(xs)
        if hi - lo <= RHO_TOL * max(abs(hi), EPS) and not zero_bad[code]:
            rho[code] = float(np.mean(xs))
        else:
            spread_bad.append(code)
    spread_bad += [c for c in zero_bad if c not in ratios]
    pref = model.prod[1, model.sub, 3]
    rho_row = np.array([rho.get(model.codes[s], np.nan) for s in model.sub])
    cap = np.where(np.isfinite(rho_row) & (pref > 0), I._div(np.nan_to_num(rho_row), pref), np.inf)
    shifts, missing, no_rho, fl_diff = {}, defaultdict(int), defaultdict(int), 0.0
    for d, _ in DESIGNS:
        mat = np.zeros((n_runs, n_rows))
        for key, (f0, fl) in runs.get(d, {}).items():
            fl_diff = max(fl_diff, abs(f0 - flb.get(key, math.nan)) if key in flb else math.inf)
            j = index.get(key)
            if j is None:
                missing[d] += 1
                continue
            if not np.isfinite(rho_row[j]) or pref[j] <= 0:
                no_rho[d] += 1
                continue
            mat[:, j] = rho_row[j] * (fl - f0) / pref[j]
        shifts[d] = mat
    used = sorted({k[1] for d in runs.values() for k in d})
    chk = [
        {"checagem": "o FS × FL do snapshot é um múltiplo constante do FL B da v5.1 em cada substrato (med)",
         "resultado": not [c for c in used if c in spread_bad or c not in rho],
         "detalhe": f"{len(rho)} substratos com ρ único"
                    + (f"; não: {', '.join(sorted(spread_bad))}" if spread_bad else "")},
        {"checagem": "FL_v51 das rodadas = FL B med da tabela fl_v5", "resultado": fl_diff <= FL_TOL,
         "detalhe": f"máx |Δ| {fl_diff:.1e}"},
        {"checagem": "toda linha das rodadas está no snapshot (med) e tem ρ",
         "resultado": not missing and not no_rho,
         "detalhe": "; ".join(f"{d}: {sum(1 for _ in runs.get(d, {}))} linhas, {missing[d]} fora do snapshot, "
                              f"{no_rho[d]} sem ρ" for d, _ in DESIGNS)},
        {"checagem": "as rodadas trazem os três desenhos", "resultado": all(d in runs for d, _ in DESIGNS)
         and n_runs > 1, "detalhe": f"{n_runs} rodadas por desenho; desenhos: {', '.join(sorted(runs))}"},
    ]
    return {"shifts": shifts, "cap": cap, "rho": rho, "conferencia": chk}


def draw(model: RedeModel, n: int, shift: np.ndarray | None = None, cap: np.ndarray | None = None,
         seed: int = I.SEED) -> dict:
    """The loop of I.draw (same generator, keys and batches), with one run of `shift` per draw from a second
    generator; without `shift` the draws are those of build_incerteza_cp2b.py."""
    rng, pick = np.random.default_rng(seed), np.random.default_rng(seed + 1)
    dists = model.dists()
    keys = sorted(dists)
    munis, state = np.empty((n, len(model.munis))), np.empty(n)
    try:
        for start in range(0, n, I.BATCH):
            d = min(I.BATCH, n - start)
            vals = {}
            for k in keys:
                lo, mode, hi = dists[k]
                vals[k] = np.full(d, mode) if lo == hi else rng.triangular(lo, mode, hi, d)
            if shift is not None:
                model.shift, model.cap = shift[pick.integers(0, shift.shape[0], d)], cap
            out = model.evaluate(vals)
            munis[start:start + d] = out["mun"]
            state[start:start + d] = out["state"]["n4"]
    finally:
        model.shift = model.cap = None
    return {"munis": munis, "state": state}


# ── Summaries ───────────────────────────────────────────────────────────────


def municipal(sim: dict, r0: np.ndarray, onehot: np.ndarray) -> dict:
    """Per municipality: p5, p95, P(top 50), P(N4 > 0); state and region p5–p95; p5 of the draws' Spearman."""
    x = sim["munis"]
    reg = x @ onehot
    ranks = I.rank_rows(x)
    n_mun = x.shape[1]
    rho = 1 - 6 * ((ranks - r0) ** 2).sum(1) / (n_mun * (n_mun ** 2 - 1)) if n_mun > 1 else np.ones(len(x))
    return {"p5": np.quantile(x, .05, axis=0), "p95": np.quantile(x, .95, axis=0),
            "top50": (ranks <= I.TOP).mean(0), "pos": (x >= ZERO_NM3).mean(0),
            "state": (q(sim["state"], .05), q(sim["state"], .95)), "spearman_p5": q(rho, .05),
            "reg": (np.quantile(reg, .05, axis=0), np.quantile(reg, .95, axis=0))}


def build(rows, params, data: dict, n: int, names: dict) -> dict:
    model = RedeModel(rows, params)
    runs, n_runs = runs_table(data[RUNS])
    lk = link(model, data[FLV5], runs, n_runs)
    base_mun = model.at(1)["mun"][0]
    r0 = I.rank_rows(base_mun)[0]
    zero = (base_mun < ZERO_NM3) & (np.bincount(model.mun, model.snapshot["n3"][1], len(model.munis)) > 0)
    regions = [names[m][1] or "sem região" for m in model.munis]
    reg_names = sorted(set(regions))
    onehot = np.array([[1.0 if r == g else 0.0 for g in reg_names] for r in regions])
    plain = municipal(draw(model, n), r0, onehot)
    res = {d: municipal(draw(model, n, lk["shifts"][d], lk["cap"]), r0, onehot) for d, _ in DESIGNS}

    chk = [{"checagem": c, "resultado": ok, "detalhe": det} for c, ok, det in S.checks(rows)] + lk["conferencia"]
    chk.append(sim_check(model, plain, n))
    width0 = plain["p95"] - plain["p5"]
    has = base_mun >= ZERO_NM3
    ranking, summary = [], []
    for j in np.argsort(r0, kind="stable"):
        ibge = model.munis[j]
        row = {"ibge": ibge, "municipio": names[ibge][0], "rgint": names[ibge][1], "n4_med": float(base_mun[j]),
               "rank_med": int(r0[j]), "n4_p5": float(plain["p5"][j]), "n4_p95": float(plain["p95"][j]),
               "prob_top50": float(plain["top50"][j]), "prob_n4_pos": float(plain["pos"][j])}
        for d, _ in DESIGNS:
            r = res[d]
            row.update({f"n4_p5_{d}": float(r["p5"][j]), f"n4_p95_{d}": float(r["p95"][j]),
                        f"razao_amplitude_{d}": float((r["p95"][j] - r["p5"][j]) / width0[j]) if width0[j] > 0
                        else None, f"prob_top50_{d}": float(r["top50"][j]), f"prob_n4_pos_{d}": float(r["pos"][j])})
        ranking.append(row)
    for d, label in DESIGNS:
        r = res[d]
        ratio = (r["p95"] - r["p5"])[has & (width0 > 0)] / width0[has & (width0 > 0)]
        summary.append({"desenho": d, "rotulo": label, "rodadas": n_runs,
                        "linhas_com_rede": int((np.abs(lk["shifts"][d]) > 0).any(0).sum()),
                        "n4_estado_p5": r["state"][0], "n4_estado_p95": r["state"][1],
                        "n4_estado_p5_sem_rede": plain["state"][0], "n4_estado_p95_sem_rede": plain["state"][1],
                        "municipios_com_n4": int(has.sum()), "razao_amplitude_mediana": float(np.median(ratio)),
                        "razao_amplitude_p90": float(np.quantile(ratio, .9)),
                        **{f"municipios_razao_acima_{fmt(w, 2)}": int((ratio >= w).sum()) for w in WIDER},
                        "municipios_top50_muda_01": int((np.abs(r["top50"] - plain["top50"]) > PROB_MOVE).sum()),
                        "top50_certos_sem_rede": int((plain["top50"] >= 0.9).sum()),
                        "top50_certos": int((r["top50"] >= 0.9).sum()),
                        "spearman_p5_sem_rede": plain["spearman_p5"], "spearman_p5": r["spearman_p5"],
                        "zerados": int(zero.sum()), "zerados_prob_pos_mediana_sem_rede":
                            float(np.median(plain["pos"][zero])) if zero.any() else None,
                        "zerados_prob_pos_mediana": float(np.median(r["pos"][zero])) if zero.any() else None,
                        "zerados_prob_pos_acima_05": int((r["pos"][zero] > 0.5).sum())})
    reg_base = base_mun @ onehot
    reg_rows = []
    for i in np.argsort(-reg_base, kind="stable"):
        if reg_base[i] <= 0:
            continue
        row = {"rgint": reg_names[i], "n4_med": float(reg_base[i]),
               "amplitude_relativa": float((plain["reg"][1][i] - plain["reg"][0][i]) / reg_base[i])}
        row.update({f"amplitude_relativa_{d}": float((res[d]["reg"][1][i] - res[d]["reg"][0][i]) / reg_base[i])
                    for d, _ in DESIGNS})
        reg_rows.append(row)
    return {"ranking": ranking, "resumo": summary, "regioes": reg_rows, "conferencia": chk, "rho": lk["rho"],
            "zeros": [(names[model.munis[j]][0] or model.munis[j], float(plain["pos"][j]),
                       {d: float(res[d]["pos"][j]) for d, _ in DESIGNS}) for j in np.flatnonzero(zero)],
            "n": n, "runs": n_runs}


def sim_check(model, plain: dict, n: int) -> dict:
    """Without the network term the draws are those of build_incerteza_cp2b.py (its ranking.csv, same N)."""
    if n != int(os.environ.get("CP2B_MC_N_REF", "20000")) or not INC_RANKING.exists():
        return {"checagem": "sem a rede, o sorteio repete o de outputs/incerteza_cp2b (informativo: outro N)",
                "resultado": True, "detalhe": f"{n} sorteios"}
    with INC_RANKING.open(encoding="utf-8-sig") as fh:
        ref = {r["ibge"]: (float(r["n4_p5"]), float(r["n4_p95"])) for r in csv.DictReader(fh)}
    worst = 0.0
    for j, m in enumerate(model.munis):
        if m in ref:
            for mine, theirs in zip((plain["p5"][j], plain["p95"][j]), ref[m]):
                worst = max(worst, abs(mine - theirs) / max(abs(theirs), 1.0))
    return {"checagem": "sem a rede, o sorteio repete o de outputs/incerteza_cp2b (n4_p5 e n4_p95)",
            "resultado": worst <= 1e-9 and set(ref) == set(model.munis),
            "detalhe": f"{len(ref)} municípios, máx |Δ| relativo {worst:.1e}"}


# ── Map and report ──────────────────────────────────────────────────────────


def ratio_classes():
    return ([0.0, 1.05, 1.25, 1.5, 2.0, math.inf], ["< 1,05", "1,05–1,25", "1,25–1,5", "1,5–2", "≥ 2"],
            [M.BLUE[0], M.BLUE[2], M.BLUE[3], M.BLUE[5], M.BLUE[6]])


def ratio_map(path: Path, res: dict) -> str:
    """How much wider each municipality's N4 interval gets with the network (MAP_DESIGN). Returns a note."""
    values = {r["ibge"]: r[f"razao_amplitude_{MAP_DESIGN}"] for r in res["ranking"] if r["n4_med"] >= ZERO_NM3}
    classes = ratio_classes()
    n = [sum(1 for v in values.values() if v is not None and M.classify(v, classes[0]) == i)
         for i in range(len(classes[1]))]
    counts = "; ".join(f"{lab}: {k}" for lab, k in zip(classes[1], n))
    try:
        mesh, _, _ = M.load_mesh()
    except Exception as e:  # noqa: BLE001 — no mesh is a note, not a failure
        return f"Mapa não desenhado: a malha do IBGE não pôde ser lida ({type(e).__name__}). Por classe: {counts}."
    rings = M.polygons(mesh)
    label = dict(DESIGNS)[MAP_DESIGN]
    M.single_map(path, rings, {c: values.get(c) for c in rings}, classes,
                 "Quanto a rede de hubs alarga o intervalo municipal do N4 (med)",
                 f"Amplitude p5–p95 do N4 com a rede ({res['runs']} rodadas, ruído de {label} × substrato) sobre a "
                 "amplitude só com os parâmetros.", "Razão das amplitudes", "N4 med zero", source=SOURCE)
    return f"No mapa ({MAP_DESIGN}), municípios por classe da razão: {counts}. Mapa: `mapa_rede_amplitude.png`."


def _r(x, nd=2) -> str:
    return "—" if x is None else fmt(x, nd)


def report(res: dict, notes: list[str], map_note: str) -> list[str]:
    L = ["# Incerteza municipal do N4 com a rede de hubs (CP2b v5.1)", "",
         "> " + " · ".join(notes), "",
         f"Cada um dos {fmt(res['n'], 0)} sorteios de parâmetros do `build_incerteza_cp2b.py` (mesma semente, mesma "
         "ordem) recebe uma rodada da perturbação da oferta do fl_v5, sorteada entre as "
         f"{res['runs']} de cada desenho, e o FL espacial de cada município × substrato se desloca pelo que essa "
         "rodada mudou no med. Sem a rede, os sorteios são os do `build_incerteza_cp2b.py`. Volumes em milhões de "
         "Nm³ de CH₄ por ano.", "", "## 1. Estado", "",
         "| Ruído | N4 p5–p95 só parâmetros | N4 p5–p95 com a rede |", "|---|---|---|"]
    L += [f"| {r['rotulo']} | {mi(r['n4_estado_p5_sem_rede'])}–{mi(r['n4_estado_p95_sem_rede'])} | "
          f"{mi(r['n4_estado_p5'])}–{mi(r['n4_estado_p95'])} |" for r in res["resumo"]]
    r0 = res["resumo"][0]
    L += ["", "## 2. Municípios", "",
          f"Municípios com N4 med acima de zero: {r0['municipios_com_n4']}. Razão: amplitude p5–p95 com a rede "
          "sobre a amplitude só com os parâmetros.", "",
          "| Ruído | Razão mediana (p90) | Razão ≥ 1,25 | Razão ≥ 2 | P(top-50) muda > 0,1 | "
          "Top-50 com P ≥ 0,9 (sem → com) | Spearman p5 (sem → com) |", "|---|---|---:|---:|---:|---|---|"]
    L += [f"| {r['rotulo']} | {_r(r['razao_amplitude_mediana'])} ({_r(r['razao_amplitude_p90'])}) | "
          f"{r['municipios_razao_acima_1,25']} | {r['municipios_razao_acima_2,00']} | "
          f"{r['municipios_top50_muda_01']} | {r['top50_certos_sem_rede']} → {r['top50_certos']} | "
          f"{_r(r['spearman_p5_sem_rede'], 3)} → {_r(r['spearman_p5'], 3)} |" for r in res["resumo"]]
    key = f"razao_amplitude_{MAP_DESIGN}"
    top = sorted((r for r in res["ranking"] if r["n4_med"] >= ZERO_NM3 and r[key] is not None),
                 key=lambda r: -r[key])[:10]
    L += ["", f"Os 10 municípios cujo intervalo mais alarga ({dict(DESIGNS)[MAP_DESIGN]}):", "",
          "| Município | Região | N4 med | p5–p95 só parâmetros | p5–p95 com a rede | Razão |",
          "|---|---|---:|---|---|---:|"]
    L += [f"| {r['municipio'] or r['ibge']} | {r['rgint'] or '—'} | {mi(r['n4_med'], 2)} | {mi(r['n4_p5'], 2)}–"
          f"{mi(r['n4_p95'], 2)} | {mi(r[f'n4_p5_{MAP_DESIGN}'], 2)}–{mi(r[f'n4_p95_{MAP_DESIGN}'], 2)} | "
          f"{_r(r[key])} |" for r in top]
    if map_note:
        L += ["", map_note]
    L += ["", "## 3. Regiões intermediárias", "", "Amplitude p5–p95 sobre o N4 med da região.", "",
          "| Região | N4 med | Só parâmetros | " + " | ".join(lab for _, lab in DESIGNS) + " |",
          "|---|---:|---:|" + "---:|" * len(DESIGNS)]
    L += [f"| {g['rgint']} | {mi(g['n4_med'])} | {fmt(100 * g['amplitude_relativa'], 0)} % | "
          + " | ".join(f"{fmt(100 * g[f'amplitude_relativa_{d}'], 0)} %" for d, _ in DESIGNS) + " |"
          for g in res["regioes"]]
    L += ["", "## 4. Municípios com N4 med zero", "",
          f"Probabilidade de N4 acima de {fmt(ZERO_NM3, 0)} Nm³/ano nos sorteios ({len(res['zeros'])} municípios).",
          "", "| Município | Só parâmetros | " + " | ".join(lab for _, lab in DESIGNS) + " |",
          "|---|---:|" + "---:|" * len(DESIGNS)]
    L += [f"| {name} | {fmt(p0, 2)} | " + " | ".join(fmt(pd[d], 2) for d, _ in DESIGNS) + " |"
          for name, p0, pd in sorted(res["zeros"], key=lambda z: (-max(z[2].values()), z[0]))]
    L += ["", "## 5. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    L += [f"| {c['checagem']} | {'ok' if c['resultado'] else 'FALHOU'} | {c['detalhe']} |"
          for c in res["conferencia"]]
    L += ["", "## Como ler", "",
          "- O deslocamento vem do med: a rodada muda o FL de cada linha no ponto med, e o sorteio aplica a mesma "
          "mudança qualquer que seja o N3 dele. O FL fica entre 0 e 1.",
          "- Só o FL vem das rodadas. O ruído que a perturbação pôs na oferta não entra no N3 dos sorteios: ele "
          "serviu para mover a rede de hubs, e a incerteza do N3 já está nos parâmetros.",
          "- Os sorteios de parâmetros e de rodadas são independentes. A rede responde à oferta, então parte da "
          "variação que ela traz pode se sobrepor à dos parâmetros; a razão é um teto para o efeito somado.",
          "- A palha de cana vai às usinas e não depende da rede; as linhas dela não se movem."]
    return L


def write_csv(path: Path, rows: list[dict]) -> None:
    F.write_csv(path, rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    title = "# Incerteza municipal do N4 com a rede de hubs (CP2b v5.1)\n\n"
    rows, levels_note = S.read_levels()
    params, _, param_note = I.parameters()
    data, chk, why = F.load(DATA)
    if data is not None and RUNS not in data:
        why = f"falta {RUNS} no manifesto de data/fl_v51 (fl_espacial/analises_v52/v52_pert_exporta.py)"
    if rows is None or not params:
        why = "; ".join(x for x in (levels_note if rows is None else param_note, why) if x)
    if why:
        (OUT / "RELATORIO.md").write_text(f"{title}Não rodou: {why}.\n", encoding="utf-8")
        print(f"Sem incerteza com a rede: {why}")
        return
    n = int(os.environ.get("CP2B_MC_N", "20000"))
    res = build(rows, params, data, n, I.municipalities())
    res["conferencia"] = chk + res["conferencia"]
    note = ratio_map(OUT / "mapa_rede_amplitude.png", res)
    write_csv(OUT / "ranking_rede.csv", res["ranking"])
    write_csv(OUT / "regioes_rede.csv", res["regioes"])
    write_csv(OUT / "resumo_rede.csv", res["resumo"])
    write_csv(OUT / "conferencia.csv", res["conferencia"])
    lines = report(res, [f"Níveis: {levels_note}", f"Parâmetros: {param_note}", f"{fmt(n, 0)} sorteios"], note)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [c["checagem"] for c in res["conferencia"] if not c["resultado"]]
    print(f"{n} sorteios · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
