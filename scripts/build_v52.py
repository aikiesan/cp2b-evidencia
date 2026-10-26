#!/usr/bin/env python3
"""
CP2b v5.2 under construction: what each proposed parameter change does to the potential.

v5.2 is built here, not in PILAR-2b, which stays frozen with v5.1 until the
article is out. Each change is one line of v52/mudancas.csv: a substrate, an
element, its v5.1 range (checked against the snapshot's parameter file), the
proposed range, the Literature Watch records behind it and a status:

  candidata   proposed, waiting for the method team
  aceita      decided (the decisao column names the decision note)
  rejeitada   kept for the record, never applied

The script runs the CP2b model of build_incerteza_cp2b.py (which reproduces
the snapshot's min, med and max row by row) with the v5.1 parameters swapped
for the proposed ones, and reports, for each change alone, for the accepted
changes together and for accepted plus candidates:

  state N1-N4 in the med scenario and N4 in min and max
  N4 per substrate and per municipality, and the municipal ranking against v5.1
  the 90 % interval of N4 from the same draws as the v5.1 uncertainty (same seed,
  so the difference is the change, not the sampling)

The spatial FL follows each municipality's N3 as in the uncertainty model; it is
not re-run. The fl_v5 code is in fl_espacial/, but re-running it needs inputs
kept outside git (OSM roads, shapefiles, registries).

Nothing here changes the platform or the snapshot. When v5.2 closes, the
accepted changes go to PILAR-2b as a patch the maintainers apply themselves.

Run from the repo root (CP2B_MC_N draws, default 20000):
  python3 scripts/build_v52.py

Outputs (outputs/v52/):
  mudancas.csv · impacto.csv · substratos.csv · municipios.csv · conferencia.csv
  RELATORIO.md
"""

from __future__ import annotations

import copy
import csv
import importlib.util
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "v52" / "mudancas.csv"
OUT = ROOT / "outputs" / "v52"
STATUS = ("aceita", "candidata", "rejeitada")
NUMBERS = ("v51_min", "v51_med", "v51_max", "min", "med", "max")
V51_RTOL = 1e-6
TOP = 50


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I = _load(ROOT / "scripts" / "build_incerteza_cp2b.py")  # noqa: E741
S, E = I.S, I.E
fmt, mi = S.fmt, S.mi


# ── Changes ─────────────────────────────────────────────────────────────────


def read_changes(path: Path = CHANGES) -> tuple[list[dict], list[str]]:
    """Well-formed lines of mudancas.csv, and what is wrong with the others."""
    out, problems = [], []
    if not path.exists():
        return [], [f"sem {path.name}"]
    with path.open(encoding="utf-8-sig") as fh:
        for n, r in enumerate(csv.DictReader(fh), start=2):
            cid = (r.get("id") or "").strip() or f"linha {n}"
            vals = {k: E.num(r.get(k)) for k in NUMBERS}
            if r.get("status") not in STATUS:
                problems.append(f"{cid}: status '{r.get('status')}' não é {', '.join(STATUS)}")
            elif r.get("elemento") not in I.STAGE:
                problems.append(f"{cid}: elemento '{r.get('elemento')}' não entra na cascata")
            elif any(v is None for v in vals.values()):
                problems.append(f"{cid}: falta número em {', '.join(k for k, v in vals.items() if v is None)}")
            elif not vals["min"] <= vals["med"] <= vals["max"]:
                problems.append(f"{cid}: v5.2 fora de ordem (mín ≤ med ≤ máx)")
            else:
                out.append({**{k: (r.get(k) or "").strip() for k in r}, **vals, "id": cid})
    seen: dict = {}
    for c in out:
        if c["status"] != "rejeitada":
            seen.setdefault((c["codigo"], c["elemento"]), []).append(c["id"])
    for (code, el), ids in seen.items():
        if len(ids) > 1:
            problems.append(f"{' e '.join(ids)}: duas mudanças ativas em {code} {el}")
    dup = {i for ids in seen.values() if len(ids) > 1 for i in ids}
    return [c for c in out if c["id"] not in dup], problems


def against_v51(changes: list[dict], model) -> tuple[list[dict], list[str]]:
    """Changes whose v5.1 range is the snapshot's and that enter the model; the others, with why."""
    ok, problems = [], []
    for c in changes:
        key = (c["codigo"], c["elemento"])
        cur = model.params.get(key)
        if cur is None:
            why = "zero no cenário de referência" if key in model.dropped else "não está no arquivo de parâmetros"
            problems.append(f"{c['id']}: {c['codigo']} {c['elemento']} {why}")
        elif not np.allclose((c["v51_min"], c["v51_med"], c["v51_max"]), cur, rtol=V51_RTOL, atol=0):
            problems.append(f"{c['id']}: v5.1 {c['v51_min']:g}–{c['v51_med']:g}–{c['v51_max']:g} não confere com "
                            f"o arquivo de parâmetros ({cur[0]:g}–{cur[1]:g}–{cur[2]:g})")
        else:
            ok.append(c)
    return ok, problems


def scenario_sets(changes: list[dict]) -> list[tuple[str, str, list[dict]]]:
    """(key, label, changes): v5.1, each active change alone, accepted, accepted + candidates."""
    active = [c for c in changes if c["status"] != "rejeitada"]
    accepted = [c for c in active if c["status"] == "aceita"]
    out = [("v5.1", "v5.1, sem mudanças", [])]
    out += [(c["id"], f"{c['id']} sozinha ({c['status']})", [c]) for c in active]
    if accepted:
        out.append(("aceitas", "v5.2 com as aceitas", accepted))
    if len(active) > len(accepted) and len(active) > 1:
        out.append(("aceitas+candidatas", "v5.2 com aceitas e candidatas", active))
    return out


# ── The model with the changes ──────────────────────────────────────────────


def values_at(model, changes: list[dict], i: int) -> dict:
    """Every parameter at its min (0), med (1) or max (2), changed ones at their v5.2 value."""
    vals = {k: np.array([v[i]]) for k, v in model.params.items()}
    vals.update({k: np.array([i - 1.0]) for k in model.residuals})
    for c in changes:
        vals[(c["codigo"], c["elemento"])] = np.array([(c["min"], c["med"], c["max"])[i]])
    return vals


def with_dists(model, changes: list[dict]):
    """A view of the model whose draws use the v5.2 triangulars of the changed parameters."""
    d = model.dists()
    for c in changes:
        d[(c["codigo"], c["elemento"])] = (c["min"], c["med"], c["max"])
    view = copy.copy(model)
    view.dists = lambda: dict(d)
    return view


def spearman(r: np.ndarray, r0: np.ndarray) -> float:
    n = len(r0)
    return 1 - 6 * float(((r - r0) ** 2).sum()) / (n * (n * n - 1)) if n > 1 else 1.0


def build(rows, params, changes, problems, n, names) -> dict:
    model = I.Model(rows, params)
    _, mchecks = I.check_model(model)
    applied, bad = against_v51(changes, model)
    problems = problems + bad
    sets = scenario_sets(applied)
    draw_keys = {"v5.1", "aceitas", "aceitas+candidatas"} if n > 0 else set()

    base = {i: model.evaluate(values_at(model, [], i)) for i in range(3)}
    r0 = I.rank_rows(base[1]["mun"])[0]
    top0, top10 = r0 <= TOP, r0 <= 10
    impact, subs, munis = [], [], []
    for key, label, chs in sets:
        res = {i: model.evaluate(values_at(model, chs, i)) for i in range(3)}
        st = {k: float(v[0]) for k, v in res[1]["state"].items()}
        r = I.rank_rows(res[1]["mun"])[0]
        row = {"conjunto": key, "descricao": label, "mudancas": " + ".join(c["id"] for c in chs) or "—",
               **{k: st[k] for k in I.LEVEL_KEYS},
               "n4_min": float(res[0]["state"]["n4"][0]), "n4_max": float(res[2]["state"]["n4"][0]),
               "top10_mantidos": int((top10 & (r <= 10)).sum()), "top50_mantidos": int((top0 & (r <= TOP)).sum()),
               "spearman": spearman(r, r0), "n4_p5": None, "n4_p50": None, "n4_p95": None}
        if key in draw_keys and (key == "v5.1" or chs):
            lv = I.draw(with_dists(model, chs), n)["levels"]["n4"]
            row.update(n4_p5=I.q(lv, .05), n4_p50=I.q(lv, .5), n4_p95=I.q(lv, .95))
        impact.append(row)
        if key != "v5.1" and key == sets[-1][0]:
            for i in np.argsort(-res[1]["sub"][0], kind="stable"):
                subs.append({"codigo": model.codes[i], "n4_v51": float(base[1]["sub"][0][i]),
                             "n4_v52": float(res[1]["sub"][0][i])})
            for j in np.argsort(r, kind="stable"):
                ibge = model.munis[j]
                name, region = names[ibge]
                munis.append({"ibge": ibge, "municipio": name, "rgint": region,
                              "n4_v51": float(base[1]["mun"][0][j]), "n4_v52": float(res[1]["mun"][0][j]),
                              "rank_v51": int(r0[j]), "rank_v52": int(r[j])})

    want = [float(model.snapshot["n4"][i].sum()) for i in range(3)]
    got = [float(base[i]["state"]["n4"][0]) for i in range(3)]
    dev = max(abs(g / w - 1) if w else abs(g) for g, w in zip(got, want))
    chk = S.checks(rows) + mchecks + [
        ("v5.1 sem mudanças reproduz o N4 do snapshot no mín, med e máx (±0,01 %)", dev <= 1e-4,
         f"{' · '.join(mi(g) for g in got)} mi"),
        ("toda linha de mudancas.csv é lida, confere com a v5.1 e entra no modelo", not problems,
         "; ".join(problems) or f"{len(applied)} mudanças"),
    ]
    return {"model": model, "changes": changes, "applied": applied, "impact": impact, "subs": subs,
            "munis": munis, "checks": chk, "n": n}


# ── Report ──────────────────────────────────────────────────────────────────


def _cell(text) -> str:
    """Free text for a table cell: a pipe would split it."""
    return (text or "").replace("|", "/")


def _range(c: dict, pre: str = "") -> str:
    return "–".join(f"{c[pre + k]:g}".replace(".", ",") for k in ("min", "med", "max"))


def report(res: dict, levels_note: str, param_note: str) -> list[str]:
    imp = {r["conjunto"]: r for r in res["impact"]}
    b = imp["v5.1"]
    pct = I.pct
    lines = [
        "# CP2b v5.2 em construção: o que cada mudança faz no N4", "",
        f"> Níveis: {levels_note} · Parâmetros: {param_note.rstrip('.')}.",
        "> Volumes em milhões de Nm³ de CH₄ por ano. O modelo de `build_incerteza_cp2b.py` (que reproduz o "
        "snapshot v5.1 linha a linha) com os parâmetros de `v52/mudancas.csv` no lugar dos da v5.1. O FL "
        "espacial acompanha o N3 de cada município; o modelo do FL não é refeito. Nada aqui muda a plataforma.",
        "", "## 1. Mudanças", "",
        "| Id | Status | Substrato | Elemento | v5.1 mín–med–máx | v5.2 mín–med–máx | Registros (tier) | Decisão |",
        "|---|---|---|---|---|---|---|---|"]
    for c in res["changes"]:
        lines.append(f"| {c['id']} | {c['status']} | {c['codigo']} | {c['elemento']} | {_range(c, 'v51_')} | "
                     f"{_range(c)} | {_cell(c.get('registros'))} ({_cell(c.get('tier'))}) | "
                     f"{_cell(c.get('decisao')) or '—'} |")
    if not res["changes"]:
        lines.append("| — | | | | | | | |")
    lines += ["", "Justificativas:", ""]
    lines += [f"- **{c['id']}**: {c.get('justificativa') or '—'}" for c in res["changes"]] or ["- —"]

    lines += ["", "## 2. N4 do estado", "",
              f"v5.1: {mi(b['n4'])} mi no med; faixa do snapshot {mi(b['n4_min'])}–{mi(b['n4_max'])}.", "",
              "| Conjunto | N3 med | N4 med | ΔN4 med | N4 mín | N4 máx | N4 p5–p95 | Top 10 | Top 50 | Spearman |",
              "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|"]
    for r in res["impact"]:
        band = f"{mi(r['n4_p5'])}–{mi(r['n4_p95'])}" if r["n4_p5"] is not None else "—"
        lines.append(f"| {r['descricao']} | {mi(r['n3'])} | {mi(r['n4'])} | {pct(r['n4'] - b['n4'], b['n4'])} | "
                     f"{mi(r['n4_min'])} | {mi(r['n4_max'])} | {band} | {r['top10_mantidos']} | "
                     f"{r['top50_mantidos']} | {fmt(r['spearman'], 3)} |")

    if res["subs"]:
        last = res["impact"][-1]["descricao"]
        lines += ["", f"## 3. Por substrato ({last}, med)", "",
                  "| Substrato | N4 v5.1 | N4 v5.2 | Δ |", "|---|---:|---:|---:|"]
        lines += [f"| {s['codigo']} | {mi(s['n4_v51'])} | {mi(s['n4_v52'])} | "
                  f"{pct(s['n4_v52'] - s['n4_v51'], s['n4_v51'])} |"
                  for s in res["subs"] if s["n4_v51"] or s["n4_v52"]]
        mun = res["munis"]
        enter = [m for m in mun if m["rank_v52"] <= TOP < m["rank_v51"]]
        leave = [m for m in mun if m["rank_v51"] <= TOP < m["rank_v52"]]
        lines += ["", f"## 4. Ranking municipal ({last})", "",
                  "Entram no top 50: " + ("; ".join(f"{m['municipio'] or m['ibge']} {m['rank_v51']}→{m['rank_v52']}"
                                                    for m in enter) or "nenhum") + ".",
                  "Saem do top 50: " + ("; ".join(f"{m['municipio'] or m['ibge']} {m['rank_v51']}→{m['rank_v52']}"
                                                  for m in leave) or "nenhum") + ".", "",
                  "| # v5.2 | Município | Região | N4 v5.1 | N4 v5.2 | Δ | # v5.1 |",
                  "|---:|---|---|---:|---:|---:|---:|"]
        lines += [f"| {m['rank_v52']} | {m['municipio'] or m['ibge']} | {m['rgint']} | {fmt(m['n4_v51'] / 1e6, 2)} | "
                  f"{fmt(m['n4_v52'] / 1e6, 2)} | {pct(m['n4_v52'] - m['n4_v51'], m['n4_v51'])} | {m['rank_v51']} |"
                  for m in mun[:20]]

    lines += ["", "## 5. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    for name, ok, detail in res["checks"]:
        word = ok if isinstance(ok, str) else ("ok" if ok else "FALHOU")
        lines.append(f"| {name} | {word} | {detail} |")
    lines += ["", "## Como ler", "",
              "- Uma mudança candidata não é a v5.2: o relatório mostra o tamanho dela para o time decidir. Só as "
              "aceitas, com a decisão escrita, vão para o PILAR-2b depois da submissão.",
              "- O p5–p95 usa os mesmos sorteios (mesma semente) da incerteza da v5.1; a linha v5.1 reproduz "
              "`outputs/incerteza_cp2b/`. A diferença entre as linhas é a mudança, não o sorteio.",
              f"- {res['n']} sorteios por conjunto com p5–p95; mudanças sozinhas só no med, mín e máx.",
              "- Top 10, top 50 e Spearman comparam o ranking do med de cada conjunto com o da v5.1.",
              "- O FL espacial de cada município é interpolado no N3 dele, como na incerteza. Uma mudança que mexe "
              "muito no N3 de um município pequeno pode abrir ou fechar um hub que o fl_v5 trataria de outro jeito."]
    return lines


def write_csv(path: Path, rows: list[dict]) -> None:
    if rows:
        S.write_csv(path, rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    title = "# CP2b v5.2 em construção: o que cada mudança faz no N4\n\n"
    rows, levels_note = S.read_levels()
    params, _, param_note = I.parameters()
    if rows is None or not params:
        why = levels_note if rows is None else param_note
        (OUT / "RELATORIO.md").write_text(
            f"{title}Não rodou: {why}. O modelo precisa dos níveis e dos parâmetros do snapshot v5.1 com o sha256 "
            "do loader.\n", encoding="utf-8")
        print(f"Sem v5.2: {why}")
        return
    changes, problems = read_changes()
    n = int(os.environ.get("CP2B_MC_N", "20000"))
    res = build(rows, params, changes, problems, n, I.municipalities())
    write_csv(OUT / "mudancas.csv", res["changes"])
    write_csv(OUT / "impacto.csv", res["impact"])
    write_csv(OUT / "substratos.csv", res["subs"])
    write_csv(OUT / "municipios.csv", res["munis"])
    write_csv(OUT / "conferencia.csv", [{"checagem": a, "resultado": b, "detalhe": c} for a, b, c in res["checks"]])
    lines = report(res, levels_note, param_note)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [ln.split("|")[1].strip() for ln in lines if "| FALHOU |" in ln]
    print(f"{len(res['applied'])} mudanças · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
