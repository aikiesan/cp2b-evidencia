#!/usr/bin/env python3
"""
Manure generation evidence: the Literature Watch livestock registry against CP2b.

The daily "PILAR-2b Literature Watch" routine keeps REGISTRY_livestock_generation.csv
on Google Drive: manure output per head, solids, nitrogen, slaughterhouse and dairy
by-products, each with its source, basis and a quality tier. A dated copy lives in
data/literature_watch/.

The registry's units are free text (g/bird/day, kg DM/head/day, kg DM/bird per
flock, % TS wet basis), so the comparison with CP2b is an explicit map below:
one entry per registry record, with the number quoted from the record, the factor
to the CP2b unit and the CP2b element it speaks to (g, ST, SV, or g × ST, the dry
matter per head). The test checks that every quoted number is in the record's
text, so the map cannot drift from the registry.

CP2b ranges come only from the v5.1 snapshot with the loader's checksum. For
broiler litter the registry gives dry matter per bird per flock while CP2b gives
it per housed bird per year, so the script reports the flocks per year that would
make the two agree instead of a verdict.

A value outside a range is evidence to check, not an error in the range. Nothing
here changes the platform or the CP2b numbers.

Run from the repo root:
  python3 scripts/build_evidencia_geracao.py

Outputs (outputs/evidencia_geracao/):
  comparacao.csv  one row per mapped record, literature and CP2b in CP2b units
  RELATORIO.md    the comparison, unmapped records and substrates outside CP2b
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "data" / "literature_watch"
OUT = ROOT / "outputs" / "evidencia_geracao"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E = _load(ROOT / "scripts" / "build_evidencia_bmp.py")
fmt = E.fmt

KG_DAY_TO_T_YEAR = 365 / 1000
G_DAY_TO_T_YEAR = 365 / 1e6
PCT = 0.01
KG_TO_T = 1 / 1000

# CP2b element -> how it reads in the report
ELEMENTS = {
    "g": "g (t / cab / ano, fresco)",
    "ST": "ST (fração do fresco)",
    "SV": "SV (fração de ST)",
    "g×ST": "matéria seca (t MS / cab / ano)",
    "g×ST/lote": "matéria seca por lote (t MS / ave)",
}
# (CP2b code, element, record_id, number(s) quoted from the record, low, high, factor to CP2b unit, note)
MAP = (
    ("AVES_POSTURA", "g", "LIV-20261017-12", "94.8-113.8", 94.8, 113.8, G_DAY_TO_T_YEAR,
     "dejeto fresco, coleta de 24 h; média 106"),
    ("AVES_POSTURA", "g", "LIV-20261017-14", "113", 113, 113, G_DAY_TO_T_YEAR, "dejeto fresco"),
    ("AVES_POSTURA", "ST", "LIV-20261017-15", "22.27", 22.27, 22.27, PCT, ""),
    ("AVES_POSTURA", "SV", "LIV-20261017-15", "VS/TS ≈ 76%", 76, 76, PCT, ""),
    ("AVES_POSTURA", "g×ST", "LIV-20261017-14", "26 g DM/bird/day", 26, 26, G_DAY_TO_T_YEAR, ""),
    ("AVES_CORTE", "ST", "LIV-20261017-01", "64.3", 64.3, 64.3, PCT,
     "cama na retirada, RS/SC, n = 165; faixa 34–85 %"),
    ("AVES_CORTE", "g×ST/lote", "LIV-20261017-07", "1.87 kg DM/bird", 1.87, 1.87, KG_TO_T,
     "lote de 42 dias, cama nova; inclui a maravalha"),
    ("AVES_CORTE", "g×ST/lote", "LIV-20261017-03", "1.49", 1.49, 1.49, KG_TO_T, "primeiro lote, cama nova"),
    ("BOV_LEITE", "g", "LIV-20261019-09", "45-48", 45, 48, KG_DAY_TO_T_YEAR, "fezes + urina, vaca"),
    ("BOV_LEITE", "g", "LIV-20261019-02", "35.6-66.0", 35.6, 66.0, KG_DAY_TO_T_YEAR,
     "fezes + urina, vaca em lactação, compost barn (MG)"),
    ("BOV_LEITE", "ST", "LIV-20261019-07", "17.8", 17.8, 17.8, PCT, ""),
    ("BOV_LEITE", "SV", "LIV-20261019-07", "79.93", 79.93, 79.93, PCT, ""),
    ("BOV_LEITE", "SV", "LIV-20261019-08", "79.1-83.4", 79.1, 83.4, PCT, "afluente do biodigestor"),
    ("BOV_CONFINADO", "g", "LIV-20261019-10", "30-35", 30, 35, KG_DAY_TO_T_YEAR, "fezes + urina"),
    ("BOV_CONFINADO", "ST", "LIV-20261019-03", "18.25-18.60", 18.25, 18.60, PCT, ""),
    ("BOV_CONFINADO", "SV", "LIV-20261019-03", "VS/TS ≈ 86-88%", 86, 88, PCT, ""),
    ("BOV_CONFINADO", "g×ST", "LIV-20261019-05", "2.39 / 2.30", 2.30, 2.39, KG_DAY_TO_T_YEAR,
     "só fezes (sem urina), terminação com 75 % de concentrado"),
    ("BOV_PASTO_MISTO", "g", "LIV-20261019-11", "24", 24, 24, KG_DAY_TO_T_YEAR,
     "inventário nacional de GEE, bovino de corte em geral"),
)
# Records that speak to a CP2b substrate but cannot be put in its units, and why.
NOT_COMPARABLE = {
    "LIV-20261018-12": ("SUINOS", "volume de chorume com água de lavagem, sem ST: não dá para comparar com excreta "
                                  "fresca a ST 8–12 %"),
    "LIV-20261018-13": ("SUINOS", "idem, por matriz no ciclo completo"),
    "LIV-20261019-12": ("SUINOS", "idem, por categoria (média 8,6 L/animal/dia)"),
}


def latest_registry() -> Path:
    files = sorted(REGISTRY_DIR.glob("REGISTRY_livestock_generation_v*.csv"))
    if not files:
        raise FileNotFoundError(f"no REGISTRY_livestock_generation_v*.csv in {REGISTRY_DIR}")
    return files[-1]


def cp2b_ranges(params: dict) -> dict[tuple[str, str], tuple[float, float, float]]:
    """The CP2b g, ST and SV ranges, plus g × ST (dry matter per head) as min×min, med×med, max×max."""
    out = dict(params)
    for code in {c for c, _ in params}:
        g, st = params.get((code, "g")), params.get((code, "ST"))
        if g and st:
            out[(code, "g×ST")] = tuple(a * b for a, b in zip(g, st))
            out[(code, "g×ST/lote")] = out[(code, "g×ST")]
    return out


def verdict(lo: float, hi: float, rng: tuple[float, float, float] | None) -> str:
    if rng is None:
        return ""
    if hi < rng[0]:
        return "abaixo"
    if lo > rng[2]:
        return "acima"
    if lo >= rng[0] and hi <= rng[2]:
        return "dentro"
    return "sobrepõe"


def compare(records: dict[str, dict], cp2b: dict) -> list[dict]:
    rows = []
    for code, el, rid, _quote, lo, hi, factor, note in MAP:
        r = records[rid]
        lit_lo, lit_hi = lo * factor, hi * factor
        rng = cp2b.get((code, el))
        row = {
            "codigo": code, "elemento": el, "record_id": rid,
            "literatura_min": lit_lo, "literatura_max": lit_hi,
            "cp2b_min": rng[0] if rng else None, "cp2b_med": rng[1] if rng else None,
            "cp2b_max": rng[2] if rng else None,
            "literatura_sobre_cp2b_med": ((lit_lo + lit_hi) / 2 / rng[1]) if rng and rng[1] else None,
            "situacao": "", "lotes_por_ano_implicitos": "",
            "base": r.get("basis", ""), "regiao": r.get("region", ""), "tier": r.get("tier", ""),
            "fonte": r.get("source_key", ""), "doi": r.get("doi", ""), "url": r.get("url", ""), "nota": note,
        }
        if el == "g×ST/lote":
            if rng:
                a, b = fmt(rng[1] / lit_hi, 1), fmt(rng[1] / lit_lo, 1)
                row["lotes_por_ano_implicitos"] = a if a == b else f"{a}–{b}"
            row["literatura_sobre_cp2b_med"] = None
        else:
            row["situacao"] = verdict(lit_lo, lit_hi, rng)
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _v(x: float | None) -> str:
    if x is None:
        return "—"
    return fmt(x, 4) if abs(x) < 1 else fmt(x, 2)


def report(rows, records: dict[str, dict], registry: Path, note: str, subs: dict) -> list[str]:
    L = [
        "# Evidência de geração de dejetos: Literature Watch × CP2b",
        "",
        f"> Registro: `{registry.relative_to(ROOT).as_posix()}` ({len(records)} registros) · {note}",
        "> Tudo na unidade do CP2b. Matéria seca = g × ST; a faixa do CP2b é mín×mín a máx×máx.",
        "> Valor fora da faixa é evidência a conferir, não erro da faixa. Nada aqui muda a plataforma.",
        "",
        "## Comparação",
        "",
        "| Substrato | Elemento | Literatura | CP2b mín–máx (med) | Lit ÷ CP2b med | Situação | Base | Tier "
        "| Região | Fonte |",
        "|---|---|---|---|---:|---|---|---|---|---|",
    ]
    for r in rows:
        lit = _v(r["literatura_min"]) if r["literatura_min"] == r["literatura_max"] else \
            f"{_v(r['literatura_min'])}–{_v(r['literatura_max'])}"
        cp = (f"{_v(r['cp2b_min'])}–{_v(r['cp2b_max'])} ({_v(r['cp2b_med'])})"
              if r["cp2b_med"] is not None else "—")
        ratio = fmt(r["literatura_sobre_cp2b_med"], 2) if r["literatura_sobre_cp2b_med"] else "—"
        sit = r["situacao"] or (f"{r['lotes_por_ano_implicitos']} lotes/ano implícitos"
                                if r["lotes_por_ano_implicitos"] else "—")
        link = f"https://doi.org/{r['doi']}" if r["doi"] else r["url"]
        L.append(f"| {r['codigo']} | {ELEMENTS[r['elemento']]} | {lit} | {cp} | {ratio} | {sit} "
                 f"| {r['base']}{'; ' + r['nota'] if r['nota'] else ''} | {r['tier']} | {r['regiao']} | {link} |")

    L += ["", "Cama de frango: o registro dá matéria seca por ave e por lote; o CP2b, por ave alojada e por ano. "
          "A coluna Situação diz quantos lotes por ano fariam os dois baterem. Confira esse número com a "
          "rotina de produção de SP antes de concluir.",
          "", "## Registros que tocam o CP2b mas não dão para comparar", ""]
    L += [f"- {code} · {rid} · {records[rid].get('value', '')} {records[rid].get('unit', '')}: {why}"
          for rid, (code, why) in NOT_COMPARABLE.items()]

    used = {m[2] for m in MAP} | set(NOT_COMPARABLE)
    rest = [r for rid, r in records.items() if rid not in used]
    covered = {m[0] for m in MAP} | {code for code, _ in NOT_COMPARABLE.values()}
    missing = sorted(c for c, v in subs.items() if v[1] == "livestock" and c not in covered)
    L += ["", "## Outros registros (nitrogênio, cama, abate, laticínio)", "",
          "Não entram na conta do CP2b. O nitrogênio serve ao protótipo de digestato; abate, soro de queijo, "
          "caprinos, ovinos e codornas são substratos que o CP2b não modela.", "",
          "| Registro | Material | Parâmetro | Valor | Unidade | Tier | Região |", "|---|---|---|---|---|---|---|"]
    for r in rest:
        L.append(f"| {r['record_id']} | {r.get('feedstock_pt', '')} | {r.get('parameter', '')} | {r.get('value', '')} "
                 f"| {r.get('unit', '')} | {r.get('tier', '')} | {r.get('region', '')} |")
    L += ["", "## Como ler", "",
          "- Números, DOIs e notas são os do registro do Literature Watch, com a verificação que a rotina "
          "registrou. Antes de citar, abra a fonte.",
          "- Fezes + urina e só fezes são bases diferentes; a coluna Base diz qual é qual.",
          f"- Substratos de pecuária do CP2b sem nenhum registro aqui: {', '.join(missing) or 'nenhum'}."]
    return L


def main() -> None:
    registry = latest_registry()
    records = {r["record_id"]: r for r in E.read_registry(registry)}
    params, note = E.cp2b_parameters(("g", "ST", "SV"))
    rows = compare(records, cp2b_ranges(params))
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "comparacao.csv", rows)
    subs = E.B.loader_constant("SUBSTRATES")
    (OUT / "RELATORIO.md").write_text("\n".join(report(rows, records, registry, note, subs)) + "\n", encoding="utf-8")
    print(f"{len(records)} registros, {len(rows)} comparados · {note}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
