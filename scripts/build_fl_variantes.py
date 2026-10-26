#!/usr/bin/env python3
"""
How much of the CP2b v5.1 N4 depends on which spatial FL is used, and why
26 municipalities get N4 zero.

The snapshot's cp2b_fl_municipio_substrato.csv carries, per municipality ×
substrate × scenario, five spatial FL variants and the N3 supply per day:

  fl_codig_alocado          B · co-digestion, allocated to a hub
  fl_codigestao             A · co-digestion, coverage
  fl_mono                   C · mono-digestion, coverage
  fl_mono_alocado           D · mono-digestion, allocated
  fl_codig_alocado_palhaqh  B with straw going to any hub

This script reads which variant the snapshot used (the one where FS × FL of
the levels file divided by FL is one FS per substrate and scenario, and FL
zero gives FS × FL zero), checks that it reproduces the snapshot N4, and then
recomputes N4 = N3 × FS × FL with each of the other variants. It also asks
whether FL zero follows a supply threshold: for the variant used, does every
row with FL zero have less supply than every row with FL above zero?

Nothing here changes the platform or the numbers.

Run from the repo root:
  python3 scripts/build_fl_variantes.py

Outputs (outputs/fl_variantes/):
  variantes.csv · substratos.csv · municipios_zero.csv · limiar.csv · conferencia.csv · RELATORIO.md
"""

from __future__ import annotations

import csv
import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "fl_variantes"
VARIANTS = (
    ("fl_codig_alocado", "B · codigestão, alocado"),
    ("fl_codigestao", "A · codigestão, cobertura"),
    ("fl_mono", "C · mono, cobertura"),
    ("fl_mono_alocado", "D · mono, alocado"),
    ("fl_codig_alocado_palhaqh", "B · palha em qualquer hub"),
)
SUPPLY = "oferta_l3_ch4_m3_dia"
SCEN = ("min", "med", "max")
EPS = 1e-9
FS_TOL = 1e-6          # relative spread allowed in FS × FL / FL within a substrate and scenario
ZERO_NM3 = 1.0         # a municipality's N4 below 1 Nm³/year is zero (the model's float noise is ~1e-12)


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I = _load(ROOT / "scripts" / "build_incerteza_cp2b.py")  # noqa: E741
S, fmt, mi = I.S, I.fmt, I.mi


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def read_fl() -> tuple[dict | None, list[str], str]:
    """{(ibge, code, scenario): {variant: FL or None, SUPPLY: m³/day or None}}, the variants found, and a note."""
    path, why = S._verified("fl")
    if path is None:
        return None, [], why
    with path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        found = [v for v, _ in VARIANTS if v in cols]
        out = {}
        for r in reader:
            key = (str(int(float(r["ibge"]))), r["codigo_cp2b"], r["cenario"])
            out[key] = {**{v: _num(r.get(v)) for v in found}, SUPPLY: _num(r.get(SUPPLY))}
    return out, found, ""


def identify(rows: list[dict], fl: dict, variants: list[str]) -> dict:
    """{(code, scenario): (variant or None, FS or None, note)}: the variant whose FL reproduces FS × FL."""
    groups: dict = defaultdict(list)
    for r in rows:
        if (r["n3"] or 0) > EPS:
            f = fl.get((r["ibge"], r["codigo"], r["cenario"]))
            groups[(r["codigo"], r["cenario"])].append((r["fsfl"] or 0.0, f))
    out = {}
    for key, items in sorted(groups.items()):
        found = (None, None, "nenhuma variante reproduz o FS × FL")
        if all(f is None for _, f in items):
            found = (None, None, "sem linha no arquivo do FL")
        for v in variants:
            pairs = [(fsfl, f[v]) for fsfl, f in items if f is not None and f.get(v) is not None]
            if len(pairs) < len(items):
                continue
            fs = [fsfl / x for fsfl, x in pairs if x > EPS]
            zero_ok = all(fsfl <= EPS for fsfl, x in pairs if x <= EPS)
            if fs and zero_ok and max(fs) - min(fs) <= FS_TOL * max(fs):
                found = (v, sum(fs) / len(fs), "")
                break
            if not fs and zero_ok:
                found = (v, None, "FL zero em todas as linhas")
                break
        out[key] = found
    return out


def n4_with(rows: list[dict], fl: dict, ident: dict, variant: str | None) -> list[float]:
    """N4 of each row with `variant` in place of the FL used; the snapshot N4 where it cannot be recomputed."""
    out = []
    for r in rows:
        used, fs, _ = ident.get((r["codigo"], r["cenario"]), (None, None, ""))
        f = fl.get((r["ibge"], r["codigo"], r["cenario"])) or {}
        x = f.get(variant or used) if used else None
        if used is None or x is None:
            out.append(r["n4"] or 0.0)
        else:
            out.append((r["n3"] or 0.0) * (fs or 0.0) * x)
    return out


def threshold(rows: list[dict], fl: dict, ident: dict) -> tuple[list[dict], bool]:
    """For the variant used: does FL zero follow the supply, by row and by municipality?"""
    mun_supply: dict = defaultdict(float)
    same: dict = defaultdict(set)
    for (ibge, code, scen), f in fl.items():
        if f.get(SUPPLY) is not None:
            mun_supply[(ibge, scen)] += f[SUPPLY]
            same[(ibge, scen)].add(round(f[SUPPLY], 6))
    n_rows: dict = defaultdict(int)
    for (ibge, _, scen) in fl:
        n_rows[(ibge, scen)] += 1
    repeated = any(n > 1 for n in n_rows.values()) and all(len(s) == 1 for s in same.values())
    out = []
    by: dict = defaultdict(list)
    for r in rows:
        if (r["n3"] or 0) > EPS:
            by[(r["codigo"], r["cenario"])].append(r)
    for (code, scen), items in sorted(by.items()):
        used = ident.get((code, scen), (None,))[0]
        if used is None:
            continue
        row_on, row_off, mun_on, mun_off = [], [], [], []
        for r in items:
            f = fl.get((r["ibge"], code, scen)) or {}
            x, s = f.get(used), f.get(SUPPLY)
            if x is None or s is None:
                continue
            m = s if repeated else mun_supply[(r["ibge"], scen)]
            (row_on if x > EPS else row_off).append(s)
            (mun_on if x > EPS else mun_off).append(m)
        if not row_off:
            continue
        out.append({"codigo": code, "cenario": scen, "variante": used, "linhas_fl_zero": len(row_off),
                    "linhas_fl_positivo": len(row_on),
                    "oferta_linha_max_fl_zero": max(row_off),
                    "oferta_linha_min_fl_positivo": min(row_on, default=None),
                    "separa_por_linha": not row_on or max(row_off) < min(row_on),
                    "oferta_municipio_max_fl_zero": max(mun_off),
                    "oferta_municipio_min_fl_positivo": min(mun_on, default=None),
                    "separa_por_municipio": not mun_on or max(mun_off) < min(mun_on)})
    return out, repeated


def build(rows: list[dict], fl: dict, variants: list[str], names) -> dict:
    ident = identify(rows, fl, variants)
    used_n4 = n4_with(rows, fl, ident, None)
    per_variant = {v: n4_with(rows, fl, ident, v) for v in variants}

    def state(vals, scen):
        return sum(x for r, x in zip(rows, vals) if r["cenario"] == scen)

    def by_mun(vals, scen):
        acc: dict = defaultdict(float)
        for r, x in zip(rows, vals):
            if r["cenario"] == scen:
                acc[r["ibge"]] += x
        return acc

    snap = {s: sum(r["n4"] or 0.0 for r in rows if r["cenario"] == s) for s in SCEN}
    chk = []
    for s in SCEN:
        got = state(used_n4, s)
        dev = abs(got / snap[s] - 1) if snap[s] else abs(got)
        chk.append({"checagem": f"a variante identificada reproduz o N4 do snapshot, {s} (±0,01 %)",
                    "resultado": dev <= 1e-4, "detalhe": f"{mi(got)} contra {mi(snap[s])} mi"})
    open_ = [k for k, (v, _, _) in ident.items() if v is None]
    chk.append({"checagem": "toda combinação de substrato e cenário com N3 tem a variante identificada",
                "resultado": not open_, "detalhe": "; ".join(f"{c} {s}: {ident[(c, s)][2]}" for c, s in open_)
                or f"{len(ident)} combinações"})

    var_rows, sub_rows = [], []
    for s in SCEN:
        base_mun = by_mun(used_n4, s)
        zero_used = {m for m, x in base_mun.items() if x < ZERO_NM3}
        for v, label in VARIANTS:
            if v not in per_variant:
                continue
            mun = by_mun(per_variant[v], s)
            zero = {m for m, x in mun.items() if x < ZERO_NM3}
            var_rows.append({"cenario": s, "variante": v, "descricao": label, "n4": state(per_variant[v], s),
                             "n4_rel_usada": state(per_variant[v], s) / state(used_n4, s) - 1
                             if state(used_n4, s) else None,
                             "municipios_n4_zero": len(zero), "zero_que_abre": len(zero_used - zero),
                             "zero_novos": len(zero - zero_used)})
            acc: dict = defaultdict(lambda: [0.0, 0.0])
            for r, x, y in zip(rows, used_n4, per_variant[v]):
                if r["cenario"] == s:
                    acc[r["codigo"]][0] += x
                    acc[r["codigo"]][1] += y
            for code, (a, b) in sorted(acc.items()):
                sub_rows.append({"cenario": s, "variante": v, "codigo": code, "n4_usada": a, "n4_variante": b,
                                 "variante_usada": ident.get((code, s), (None,))[0] or ""})

    base = by_mun(used_n4, "med")
    zero_med = sorted(m for m, x in base.items() if x < ZERO_NM3)
    n3_med = defaultdict(float)
    supply = defaultdict(float)
    for r in rows:
        if r["cenario"] == "med":
            n3_med[r["ibge"]] += r["n3"] or 0.0
            supply[r["ibge"]] += ((fl.get((r["ibge"], r["codigo"], "med")) or {}).get(SUPPLY) or 0.0)
    mun_var = {v: by_mun(per_variant[v], "med") for v in per_variant}
    mun_rows = []
    for m in zero_med:
        name, region = names[m]
        mun_rows.append({"ibge": m, "municipio": name, "rgint": region, "n3_med": n3_med[m],
                         "oferta_med_m3_dia": supply[m], **{f"n4_{v}": mun_var[v][m] for v in per_variant}})
    lim, repeated = threshold(rows, fl, ident)
    return {"ident": ident, "variantes": var_rows, "substratos": sub_rows, "municipios": mun_rows,
            "limiar": lim, "repetida": repeated, "conferencia": chk, "variants": list(per_variant)}


def report(res: dict) -> list[str]:
    def pct(x):
        return "—" if x is None else f"{'+' if x > 0 else ''}{fmt(100 * x, 1)} %"

    L = ["# O FL espacial do CP2b v5.1: quanto do N4 depende da variante",
         "",
         "> Snapshot v5.1; volumes em milhões de Nm³ de CH₄ por ano. N4 = N3 × FS × FL, com o FL de cada "
         "variante do arquivo `cp2b_fl_municipio_substrato.csv` no lugar do FL usado. O FS é o do snapshot: "
         "FS × FL dividido pelo FL usado. Nada aqui muda a plataforma.", ""]
    used = defaultdict(list)
    for (code, scen), (v, _, _) in res["ident"].items():
        if scen == "med":
            used[v or "nenhuma"].append(code)
    L += ["## 1. Qual variante o snapshot usa (cenário med)", ""]
    L += [f"- {v}: {', '.join(sorted(c))}" for v, c in sorted(used.items())]
    L += ["", "## 2. N4 do estado com cada variante", "",
          "| Cenário | Variante | N4 | Contra a usada | Municípios com N4 zero | Zeros que abrem | Zeros novos |",
          "|---|---|---:|---|---:|---:|---:|"]
    for r in res["variantes"]:
        L.append(f"| {r['cenario']} | {r['descricao']} (`{r['variante']}`) | {mi(r['n4'])} | "
                 f"{pct(r['n4_rel_usada'])} | {r['municipios_n4_zero']} | {r['zero_que_abre']} | {r['zero_novos']} |")
    L += ["", "## 3. Os municípios com N4 med zero", ""]
    if res["municipios"]:
        vs = res["variants"]
        L += ["| Município | Região | N3 | Oferta (m³ CH₄/dia) | " + " | ".join(f"`{v}`" for v in vs) + " |",
              "|---|---|---:|---:|" + "---:|" * len(vs)]
        for r in sorted(res["municipios"], key=lambda r: -r["n3_med"]):
            L.append(f"| {r['municipio'] or r['ibge']} | {r['rgint']} | {mi(r['n3_med'], 2)} | "
                     f"{fmt(r['oferta_med_m3_dia'], 0)} | " + " | ".join(mi(r[f"n4_{v}"], 2) for v in vs) + " |")
    else:
        L.append("Nenhum município com N4 med zero.")
    L += ["", "## 4. O FL zero segue um limiar de oferta?", "",
          ("Oferta repetida em todas as linhas de um município (é a oferta do município). " if res["repetida"]
           else "Oferta por linha; a do município é a soma das linhas. ") +
          "\"Separa\" quer dizer que toda linha com FL zero tem menos oferta que toda linha com FL acima de zero.", "",
          "| Substrato | Cenário | Linhas FL 0 / > 0 | Linha: máx com FL 0 | Linha: mín com FL > 0 | Separa | "
          "Município: máx com FL 0 | Município: mín com FL > 0 | Separa |",
          "|---|---|---|---:|---:|---|---:|---:|---|"]
    for r in res["limiar"]:
        L.append(f"| {r['codigo']} | {r['cenario']} | {r['linhas_fl_zero']} / {r['linhas_fl_positivo']} | "
                 f"{fmt(r['oferta_linha_max_fl_zero'], 1)} | {fmt(r['oferta_linha_min_fl_positivo'], 1)} | "
                 f"{'sim' if r['separa_por_linha'] else 'não'} | {fmt(r['oferta_municipio_max_fl_zero'], 1)} | "
                 f"{fmt(r['oferta_municipio_min_fl_positivo'], 1)} | {'sim' if r['separa_por_municipio'] else 'não'} |")
    if not res["limiar"]:
        L.append("Nenhuma linha com N3 tem FL zero na variante usada.")
    L += ["", "## 5. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    for c in res["conferencia"]:
        L.append(f"| {c['checagem']} | {'ok' if c['resultado'] else 'FALHOU'} | {c['detalhe']} |")
    L += ["", "## Como ler", "",
          "- A variante usada é lida dos números, não do texto: é a que dá um só FS por substrato e cenário. Se a "
          "conferência falhar, os números das outras variantes não valem.",
          "- \"Zeros que abrem\" são municípios com N4 zero na variante usada que passam a ter N4 na outra; "
          "\"zeros novos\", o contrário.",
          "- Se o FL zero separa pela oferta, há um limiar de oferta mínima entre os dois valores da tabela 4; se "
          "não separa, o FL zero vem de outra regra (distância ao hub, alocação), e a tabela 3 diz o quanto cada "
          "variante devolve.",
          "- O N3 e o FS não mudam; só o FL. Variantes de mono-digestão e de cobertura respondem a outra pergunta "
          "(planta própria, ou raio sem alocar), e não são correções da usada.", ""]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, note = S.read_levels()
    fl, variants, fl_note = (None, [], "") if rows is None else read_fl()
    if rows is None or fl is None or not variants:
        why = note if rows is None else fl_note or "o arquivo do FL não tem nenhuma das variantes"
        (OUT / "RELATORIO.md").write_text(f"# O FL espacial do CP2b v5.1\n\nNão rodou: {why}.\n", encoding="utf-8")
        print(f"Sem FL: {why}")
        return
    res = build(rows, fl, variants, I.municipalities())
    I.write_csv(OUT / "variantes.csv", res["variantes"])
    I.write_csv(OUT / "substratos.csv", res["substratos"])
    I.write_csv(OUT / "municipios_zero.csv", res["municipios"])
    I.write_csv(OUT / "limiar.csv", res["limiar"])
    I.write_csv(OUT / "conferencia.csv", res["conferencia"])
    (OUT / "RELATORIO.md").write_text("\n".join(report(res)) + "\n", encoding="utf-8")
    failed = [c["checagem"] for c in res["conferencia"] if not c["resultado"]]
    print(f"conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
