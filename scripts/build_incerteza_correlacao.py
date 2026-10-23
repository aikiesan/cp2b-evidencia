#!/usr/bin/env python3
"""
CP2b v5.1 uncertainty when parameters move together.

build_incerteza_cp2b.py draws every parameter independently; the CP2b min-max
band moves all of them together. The true interval sits between the two, and
where depends on which parameters share a source. This script redraws the same
model with groups of parameters correlated through a Gaussian copula:

  z_k = √ρ · z_group + √(1 − ρ) · ε_k,   u_k = Φ(z_k),   x_k = F⁻¹_k(u_k)

F_k is the same triangular (min, med, max) as in build_incerteza_cp2b.py, so
each parameter keeps its own range and shape; only the joint movement
changes. Residuals (what the snapshot varies outside the parameter file) are
drawn the same way, as the position t in triangular(−1, 0, 1).

Structures:

  independente  each parameter alone (ρ = 0); the interval of build_incerteza
  substrato     every parameter of a substrate together (one source per substrate)
  elemento      one element across substrates together (all BMP, all FC, …:
                one lab method or one reading of the definition)
  cana          the four sugarcane residues together, the rest independent
  tudo          everything together; at ρ = 1 the extremes are the CP2b band

Every parameter raises N4, so ρ = 1 in a group means the group sits at the
same quantile of its ranges. Nothing here changes the platform or the numbers.

Run from the repo root (CP2B_MC_N draws per configuration, default 20000):
  python3 scripts/build_incerteza_correlacao.py

Outputs (outputs/incerteza_correlacao/):
  correlacao.csv · conferencia.csv · RELATORIO.md
"""

from __future__ import annotations

import csv
import importlib.util
import math
import os
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "incerteza_correlacao"
INC_CSV = ROOT / "outputs" / "incerteza_cp2b" / "incerteza.csv"
SEED = 20261024
CANE = ("PALHA", "BAGACO", "TORTA_FILTRO", "VINHACA")


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I = _load(ROOT / "scripts" / "build_incerteza_cp2b.py")  # noqa: E741
S, fmt, mi = I.S, I.fmt, I.mi

# (key, description, group of a (code, element) key, values of ρ)
STRUCTURES = (
    ("independente", "cada parâmetro sozinho", lambda c, e: (c, e), (0.0,)),
    ("substrato", "todos os parâmetros de um substrato juntos", lambda c, e: c, (0.5, 1.0)),
    ("elemento", "o mesmo elemento em todos os substratos (todos os BMP, todos os FC, …)", lambda c, e: e, (0.5, 1.0)),
    ("cana", "palha, bagaço, torta e vinhaça juntos; o resto independente",
     lambda c, e: "cana" if c in CANE else (c, e), (1.0,)),
    ("tudo", "todos juntos", lambda c, e: "tudo", (0.5, 1.0)),
)

_erf = np.vectorize(math.erf, otypes=[float])


def phi(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + _erf(z / math.sqrt(2.0)))


def tri_ppf(u: np.ndarray, lo: float, mode: float, hi: float) -> np.ndarray:
    """Inverse CDF of the triangular (lo, mode, hi)."""
    u = np.asarray(u, float)
    if hi == lo:
        return np.full(u.shape, lo)
    f = (mode - lo) / (hi - lo)
    left = lo + np.sqrt(np.clip(u, 0, 1) * (hi - lo) * (mode - lo))
    right = hi - np.sqrt(np.clip(1 - u, 0, 1) * (hi - lo) * (hi - mode))
    return np.where(u < f, left, right)


def at_quantile(model, u: float) -> float:
    """State N4 with every parameter and residual at the same quantile u of its distribution."""
    vals = {k: tri_ppf(np.array([u]), *d) for k, d in model.dists().items()}
    return float(model.evaluate(vals)["state"]["n4"][0])


def run(model, group_of, rho: float, n: int, seed: int, r0: np.ndarray) -> dict:
    """n correlated draws: state N4, Spearman per draw and how often each municipality stays in the top 50."""
    rng = np.random.default_rng(seed)
    dists = model.dists()
    keys = sorted(dists)
    groups = sorted({repr(group_of(*k)) for k in keys})
    gi = np.array([groups.index(repr(group_of(*k))) for k in keys])
    n_mun = len(model.munis)
    n4 = np.empty(n)
    rho_s = np.empty(n)
    top = np.zeros(n_mun)
    for start in range(0, n, I.BATCH):
        d = min(I.BATCH, n - start)
        z = math.sqrt(rho) * rng.standard_normal((d, len(groups)))[:, gi] + \
            math.sqrt(1 - rho) * rng.standard_normal((d, len(keys)))
        u = phi(z)
        out = model.evaluate({k: tri_ppf(u[:, j], *dists[k]) for j, k in enumerate(keys)})
        n4[start:start + d] = out["state"]["n4"]
        ranks = I.rank_rows(out["mun"])
        rho_s[start:start + d] = (1 - 6 * ((ranks - r0) ** 2).sum(1) / (n_mun * (n_mun ** 2 - 1))
                                  if n_mun > 1 else 1.0)
        top += (ranks <= I.TOP).sum(0)
    return {"n4": n4, "spearman": rho_s, "p_top": top / n, "groups": len(groups)}


def q(a, p) -> float:
    return float(np.quantile(a, p))


def build(rows, params, n: int) -> tuple[list[dict], list[dict], list[str]]:
    model = I.Model(rows, params)
    med = float(model.at(1)["state"]["n4"][0])
    band = {s: float(model.snapshot["n4"][I.SCEN.index(s)].sum()) for s in ("min", "max")}
    r0 = I.rank_rows(model.at(1)["mun"])[0]
    top0 = r0 <= I.TOP
    out, sims = [], {}
    for k, (key, desc, group_of, rhos) in enumerate(STRUCTURES):
        for j, rho in enumerate(rhos):
            t0 = time.time()
            sim = run(model, group_of, rho, n, SEED + 10 * k + j, r0)
            sims[(key, rho)] = sim
            v = sim["n4"]
            out.append({"estrutura": key, "descricao": desc, "rho": rho, "grupos": sim["groups"],
                        "n4_p5": q(v, .05), "n4_p50": q(v, .5), "n4_p95": q(v, .95), "n4_media": float(v.mean()),
                        "p5_rel": q(v, .05) / med - 1, "p95_rel": q(v, .95) / med - 1,
                        "spearman_p50": q(sim["spearman"], .5), "spearman_p5": q(sim["spearman"], .05),
                        "top50_90pct": int((sim["p_top"][top0] >= 0.9).sum()), "top50_n": int(top0.sum())})
            print(f"  {key} ρ={rho}: {time.time() - t0:.0f} s")

    chk = []
    ind = sims[("independente", 0.0)]["n4"]
    ref = None
    if INC_CSV.exists():
        with INC_CSV.open(encoding="utf-8") as fh:
            ref = next((r for r in csv.DictReader(fh) if r["nivel"] == S.LABELS["n4"]), None)
    if ref:
        dev = max(abs(q(ind, .05) / float(ref["p5"]) - 1), abs(q(ind, .95) / float(ref["p95"]) - 1))
        chk.append({"checagem": "independente reproduz o p5 e o p95 de build_incerteza_cp2b (±1 %)",
                    "resultado": dev <= 0.01, "detalhe": f"maior desvio {fmt(100 * dev, 2)} %"})
    else:
        chk.append({"checagem": "independente reproduz o p5 e o p95 de build_incerteza_cp2b (±1 %)",
                    "resultado": "sem incerteza.csv", "detalhe": "rode build_incerteza_cp2b.py antes"})
    allv = sims[("tudo", 1.0)]["n4"]
    exp5, exp95 = at_quantile(model, 0.05), at_quantile(model, 0.95)
    dev = max(abs(q(allv, .05) / exp5 - 1), abs(q(allv, .95) / exp95 - 1))
    chk.append({"checagem": "tudo, ρ = 1: p5 e p95 = N4 com tudo no quantil 5 % e 95 % (±1 %)",
                "resultado": dev <= 0.01, "detalhe": f"{mi(exp5)}–{mi(exp95)} mi; maior desvio {fmt(100 * dev, 2)} %"})
    lo, hi = at_quantile(model, 0.0), at_quantile(model, 1.0)
    dev = max(abs(lo / band["min"] - 1), abs(hi / band["max"] - 1))
    chk.append({"checagem": "quantil 0 e 1 de tudo = faixa mín–máx do snapshot (±0,1 %)",
                "resultado": dev <= 0.001,
                "detalhe": f"{mi(lo)}–{mi(hi)} mi contra {mi(band['min'])}–{mi(band['max'])}"})
    return out, chk, report(out, chk, med, band, n)


def report(out, chk, med, band, n) -> list[str]:
    def pct(x):
        return f"{'+' if x > 0 else ''}{fmt(100 * x, 1)} %"

    L = [
        "# Incerteza do N4 do CP2b v5.1 com parâmetros correlacionados",
        "",
        f"> {n} sorteios por configuração; volumes em milhões de Nm³ de CH₄ por ano. O mesmo modelo de "
        "`build_incerteza_cp2b.py` (que reproduz o mín, o med e o máx do snapshot), com grupos de parâmetros "
        "sorteados juntos por uma cópula gaussiana de correlação ρ. Cada parâmetro mantém a sua triangular "
        "(mín, med, máx) do CP2b; muda só o quanto eles andam juntos. Nada aqui muda a plataforma.",
        "",
        f"N4 med do CP2b: {mi(med)}. Faixa mín–máx do snapshot: {mi(band['min'])}–{mi(band['max'])}.",
        "",
        "## 1. Intervalo de 90 % do N4 do estado",
        "",
        "| Estrutura | O que anda junto | ρ | p5 | p50 | p95 | p5–p95 contra o med | Spearman p5 | "
        "Top 50 com ≥ 90 % |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for r in out:
        L.append(f"| {r['estrutura']} | {r['descricao']} | {fmt(r['rho'], 1)} | {mi(r['n4_p5'])} | "
                 f"{mi(r['n4_p50'])} | {mi(r['n4_p95'])} | {pct(r['p5_rel'])} a {pct(r['p95_rel'])} | "
                 f"{fmt(r['spearman_p5'], 3)} | {r['top50_90pct']} de {r['top50_n']} |")
    L += ["", "## 2. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    for c in chk:
        ok = c["resultado"]
        L.append(f"| {c['checagem']} | {ok if isinstance(ok, str) else 'ok' if ok else 'FALHOU'} | {c['detalhe']} |")
    L += ["", "## Como ler", "",
          "- ρ = 0 é a leitura de `build_incerteza_cp2b.py`. Com ρ = 1 num grupo, o grupo inteiro fica no mesmo "
          "quantil das suas faixas em cada sorteio; tudo com ρ = 1 vai de ponta a ponta da faixa mín–máx do "
          "CP2b.",
          "- `elemento` é a correlação mais defensável para o BMP (o mesmo método de laboratório) e para FC, FS e "
          "FL (a mesma leitura da definição); `substrato` é a correlação de quem tira todos os fatores de um "
          "substrato da mesma fonte; `cana` mede só o peso de a cana andar junta.",
          "- O Spearman p5 e o top 50 dizem se o ranking municipal aguenta a correlação: quando tudo sobe ou desce "
          "junto, o ranking tende a ficar mais estável que o total, porque os municípios andam juntos.",
          "- O intervalo de cada estrutura é o que se tem se aquela correlação for verdadeira; não há aqui uma "
          "estimativa de qual ρ é o real.",
          ""]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, levels_note = S.read_levels()
    params, _, param_note = I.parameters()
    if rows is None or not params:
        why = levels_note if rows is None else param_note
        (OUT / "RELATORIO.md").write_text("# Incerteza do N4 do CP2b v5.1 com parâmetros correlacionados\n\n"
                                          f"Não rodou: {why}.\n", encoding="utf-8")
        print(f"Sem correlação: {why}")
        return
    n = int(os.environ.get("CP2B_MC_N", "20000"))
    out, chk, lines = build(rows, params, n)
    I.write_csv(OUT / "correlacao.csv", out)
    I.write_csv(OUT / "conferencia.csv", chk)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [c["checagem"] for c in chk if c["resultado"] is False]
    print(f"{n} sorteios por configuração · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
