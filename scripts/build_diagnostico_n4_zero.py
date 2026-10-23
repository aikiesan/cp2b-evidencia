#!/usr/bin/env python3
"""
Where the CP2b v5.1 cascade zeroes the municipalities whose N4 is zero.

For each municipality with state-wide N4 zero in the med scenario, this script
reads the snapshot rows (municipality × substrate) and reports the levels N1,
N2, N3a, U, N3 and N4, the FS × FL of each substrate, and the first stage
that brings the total to zero:

  N1 = 0            no generation in the base
  N2 = 0            FC (collection) zero
  N3a = 0           FCo (competing use) zero
  N3 = 0            existing use takes everything (U = N3a)
  N4 = 0            FS × FL zero (the spatial FL: too little supply for a plant)

It also says whether the min and max scenarios zero the same municipality.
Nothing here changes the platform or the numbers.

Run from the repo root:
  python3 scripts/build_diagnostico_n4_zero.py

Outputs (outputs/diagnostico_n4_zero/):
  municipios.csv · substratos.csv · RELATORIO.md
"""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "diagnostico_n4_zero"
LEVELS = ("n1", "n2", "n3a", "u", "n3", "n4")
STAGES = (("n1", "N1 = 0: sem geração na base"), ("n2", "N2 = 0: FC zero"), ("n3a", "N3a = 0: FCo zero"),
          ("n3", "N3 = 0: o uso existente leva tudo"), ("n4", "N4 = 0: FS × FL zero (FL espacial)"))
EPS = 1e-9


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I = _load(ROOT / "scripts" / "build_incerteza_cp2b.py")  # noqa: E741
S, fmt, mi = I.S, I.fmt, I.mi


def where_zero(levels: dict) -> str:
    """The first stage of the cascade whose total is zero, or '' if N4 is not zero."""
    return next((label for key, label in STAGES if (levels[key] or 0.0) <= EPS), "")


def build(rows: list[dict], names) -> tuple[list[dict], list[dict], list[str]]:
    tot: dict = defaultdict(lambda: defaultdict(float))       # (ibge, scen) -> level -> sum
    by_sub: dict = defaultdict(dict)                          # (ibge, code) -> scen -> row
    for r in rows:
        for k in LEVELS:
            tot[(r["ibge"], r["cenario"])][k] += r[k] or 0.0
        by_sub[(r["ibge"], r["codigo"])][r["cenario"]] = r
    zero = sorted(m for (m, s), v in tot.items() if s == "med" and v["n4"] <= EPS)

    mun_rows, sub_rows = [], []
    for m in zero:
        lv = tot[(m, "med")]
        name, region = names[m]
        mun_rows.append({"ibge": m, "municipio": name, "rgint": region,
                         **{f"{k}_med": lv[k] for k in LEVELS},
                         "onde_zera": where_zero(lv),
                         "n4_min": tot[(m, "min")]["n4"], "n4_max": tot[(m, "max")]["n4"]})
        for (mm, code), scen in sorted(by_sub.items()):
            r = scen.get("med")
            if mm != m or r is None or (r["n1"] or 0) <= EPS:
                continue
            sub_rows.append({"ibge": m, "municipio": name, "codigo": code, **{k: r[k] for k in LEVELS},
                             "fsfl": r["fsfl"], "onde_zera": where_zero(r),
                             "n4_max": (scen.get("max") or {}).get("n4")})
    return mun_rows, sub_rows, report(mun_rows, sub_rows)


def report(mun_rows, sub_rows) -> list[str]:
    L = ["# Onde o CP2b v5.1 zera o N4 de um município", "",
         "> Snapshot v5.1, cenário med; volumes em milhões de Nm³ de CH₄ por ano. Para cada município com N4 "
         "zero, a primeira etapa da cascata cujo total é zero. Nada aqui muda a plataforma.", ""]
    if not mun_rows:
        return L + ["Nenhum município tem N4 med zero.", ""]
    count: dict = defaultdict(int)
    for r in mun_rows:
        count[r["onde_zera"]] += 1
    L += [f"{len(mun_rows)} municípios com N4 med zero. Onde zeram:", ""]
    L += [f"- {label}: {count[label]}" for _, label in STAGES if count[label]]
    L += ["", "| Município | Região | N1 | N3a | U | N3 | N4 | Onde zera | N4 no máx |",
          "|---|---|---:|---:|---:|---:|---:|---|---:|"]
    for r in sorted(mun_rows, key=lambda r: -r["n1_med"]):
        L.append(f"| {r['municipio'] or r['ibge']} | {r['rgint']} | {mi(r['n1_med'], 2)} | {mi(r['n3a_med'], 2)} | "
                 f"{mi(r['u_med'], 2)} | {mi(r['n3_med'], 2)} | {mi(r['n4_med'], 2)} | {r['onde_zera']} | "
                 f"{mi(r['n4_max'], 2)} |")
    agg: dict = defaultdict(lambda: defaultdict(float))
    stage: dict = defaultdict(lambda: defaultdict(int))
    for r in sub_rows:
        for k in ("n1", "n3", "n4"):
            agg[r["codigo"]][k] += r[k] or 0.0
        agg[r["codigo"]]["fsfl_max"] = max(agg[r["codigo"]]["fsfl_max"], r["fsfl"] or 0.0)
        stage[r["codigo"]][r["onde_zera"]] += 1
    L += ["", "## Por substrato, somando esses municípios", "",
          "| Substrato | N1 | N3 | Maior FS × FL | Onde zera (linhas) |", "|---|---:|---:|---:|---|"]
    for code, v in sorted(agg.items(), key=lambda kv: -kv[1]["n1"]):
        where = "; ".join(f"{label.split(':')[0]} {n}" for label, n in sorted(stage[code].items()) if label)
        L.append(f"| {code} | {mi(v['n1'], 2)} | {mi(v['n3'], 2)} | {fmt(v['fsfl_max'], 3)} | {where} |")
    L += ["", "## Como ler", "",
          "- \"N4 = 0: FS × FL zero\" com N3 positivo quer dizer que o resíduo existe e sobra depois do uso "
          "existente, mas o CP2b não conta planta ali: é o FL espacial, escolha de método.",
          "- \"N3 = 0\" quer dizer que o uso existente leva todo o N3a; \"N2 = 0\" ou \"N3a = 0\", que a "
          "premissa de coleta ou de uso concorrente zera o substrato.",
          "- A coluna \"N4 no máx\" diz se o município volta a ter N4 no cenário máximo do CP2b.", ""]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, note = S.read_levels()
    if rows is None:
        (OUT / "RELATORIO.md").write_text(f"# Onde o CP2b v5.1 zera o N4 de um município\n\nNão rodou: {note}.\n",
                                          encoding="utf-8")
        print(f"Sem diagnóstico: {note}")
        return
    mun_rows, sub_rows, lines = build(rows, I.municipalities())
    I.write_csv(OUT / "municipios.csv", mun_rows)
    I.write_csv(OUT / "substratos.csv", sub_rows)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(mun_rows)} municípios com N4 med zero")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
