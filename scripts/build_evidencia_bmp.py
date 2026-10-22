#!/usr/bin/env python3
"""
BMP evidence library: the Literature Watch registry against the CP2b ranges.

The team's daily "PILAR-2b Literature Watch" routine keeps REGISTRY_bmp.csv on
Google Drive: one row per measured BMP, with the test conditions, the source
(DOI, URL, ABNT citation), a quality tier (A/B/C) and the routine's own note on
how far to trust the value. A dated copy lives in data/literature_watch/
so this comparison is reproducible.

For each record whose BMP the registry normalised to NmL CH4 / g VS, the script
places the value against two ranges for the same substrate code:
  - CP2b v5.1, element "BMP" of cp2b_parametros.csv (the article's min/med/max),
    read only from the snapshot with the loader's checksum;
  - feedstocks.yaml, the platform's reference (bmp min/medio/max).

Only raw substrates are placed against the ranges; pretreated and co-digested
records are listed, not judged. A value outside a range is evidence to check,
not an error in the range. Nothing here changes the platform or the CP2b numbers.

Run from the repo root:
  python3 scripts/build_evidencia_bmp.py

Outputs (outputs/evidencia_bmp/):
  evidencia.csv   one row per registry record, with both ranges and the verdicts
  resumo.csv      one row per substrate code
  RELATORIO.md    summary, records outside a range, substrates outside CP2b
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import statistics
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "data" / "literature_watch"
OUT = ROOT / "outputs" / "evidencia_bmp"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load(ROOT / "scripts" / "pilar2b.py")
B = P.reconciliation()
FEEDSTOCKS = P.FEEDSTOCKS


def num(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def fmt(v: float | None, nd: int = 0) -> str:
    if v is None:
        return "—"
    return f"{v:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def latest_registry() -> Path:
    files = sorted(REGISTRY_DIR.glob("REGISTRY_bmp_v*.csv"))
    if not files:
        raise FileNotFoundError(f"no REGISTRY_bmp_v*.csv in {REGISTRY_DIR}")
    return files[-1]


def read_registry(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def cp2b_parameters(elements: tuple[str, ...]) -> tuple[dict[tuple[str, str], tuple[float, float, float]], str]:
    """{(code, element): (min, med, max)} from cp2b_parametros.csv, and a note on where it came from."""
    path = B.CP2B_SNAPSHOT / B.loader_constant("FILES")["parameters"]
    if not path.exists():
        return {}, "Sem o snapshot CP2b v5.1: a coluna CP2b fica vazia."
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != B.loader_constant("EXPECTED_SHA256")["parameters"]:
        return {}, "Snapshot CP2b recusado: o sha256 de cp2b_parametros.csv não confere com o loader."
    out = {}
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r.get("elemento") in elements:
                lo, med, hi = num(r.get("min")), num(r.get("med")), num(r.get("max"))
                if None not in (lo, med, hi):
                    out[(r["codigo"], r["elemento"])] = (lo, med, hi)
    return out, f"CP2b v5.1, {path.name} (sha256 conferido)."


def cp2b_bmp() -> tuple[dict[str, tuple[float, float, float]], str]:
    """{code: (min, med, max)} of the CP2b element "BMP", and a note on where it came from."""
    params, note = cp2b_parameters(("BMP",))
    return {code: v for (code, _), v in params.items()}, note


def yaml_bmp() -> dict[str, tuple[float, float, float]]:
    data = yaml.safe_load(FEEDSTOCKS.read_text(encoding="utf-8"))["feedstocks"]
    out = {}
    for code, f in data.items():
        b = (f or {}).get("bmp") or {}
        lo, med, hi = num(b.get("min")), num(b.get("medio")), num(b.get("max"))
        if None not in (lo, med, hi):
            out[code] = (lo, med, hi)
    return out


def place(value: float | None, rng: tuple[float, float, float] | None) -> str:
    if value is None or rng is None:
        return ""
    if value < rng[0]:
        return "abaixo"
    if value > rng[2]:
        return "acima"
    return "dentro"


def span(lo: float | None, hi: float | None) -> str:
    return "—" if lo is None else (fmt(lo) if lo == hi else f"{fmt(lo)}–{fmt(hi)}")


def rng_text(rng: tuple[float, float, float] | None) -> str:
    return f"{fmt(rng[0])}–{fmt(rng[2])} (med {fmt(rng[1])})" if rng else ""


def evidence(records: list[dict], cp2b: dict, yml: dict) -> list[dict]:
    rows = []
    for r in records:
        code = r.get("feedstock_code", "")
        value = num(r.get("bmp_nmlch4_gvs"))
        raw = r.get("substrate_condition") == "raw"
        rows.append({
            "record_id": r.get("record_id", ""),
            "codigo": code,
            "condicao": r.get("substrate_condition", ""),
            "bmp_nml_gsv": value,
            "valor_original": f"{r.get('bmp_value', '')} {r.get('bmp_unit', '')}".strip(),
            "tier": r.get("tier", ""),
            "pais": r.get("country", ""),
            "fonte": r.get("source_key", ""),
            "doi": r.get("doi", ""),
            "url": r.get("url", ""),
            "faixa_cp2b": rng_text(cp2b.get(code)),
            "situacao_cp2b": place(value, cp2b.get(code)) if raw else "",
            "faixa_feedstocks_yaml": rng_text(yml.get(code)),
            "situacao_feedstocks_yaml": place(value, yml.get(code)) if raw else "",
            "ja_no_pilar": r.get("in_pilar_refs", ""),
            "nota_da_rotina": r.get("confidence_note", ""),
        })
    return rows


def summary(rows: list[dict], codes: list[str], cp2b: dict, yml: dict) -> list[dict]:
    out = []
    for code in codes:
        mine = [r for r in rows if r["codigo"] == code]
        raw = [r["bmp_nml_gsv"] for r in mine if r["condicao"] == "raw" and r["bmp_nml_gsv"] is not None]
        out.append({
            "codigo": code,
            "registros": len(mine),
            "brutos_comparaveis": len(raw),
            "mediana_bruto": statistics.median(raw) if raw else None,
            "min_bruto": min(raw) if raw else None,
            "max_bruto": max(raw) if raw else None,
            "tier_a": sum(r["tier"] == "A" for r in mine),
            "faixa_cp2b": rng_text(cp2b.get(code)),
            "fora_cp2b": sum(r["situacao_cp2b"] in ("abaixo", "acima") for r in mine),
            "faixa_feedstocks_yaml": rng_text(yml.get(code)),
            "fora_feedstocks_yaml": sum(r["situacao_feedstocks_yaml"] in ("abaixo", "acima") for r in mine),
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def report(rows, summ_in, summ_out, registry: Path, note: str) -> list[str]:
    L = [
        "# Evidência de BMP: Literature Watch × CP2b × feedstocks.yaml",
        "",
        f"> Registro: `{registry.relative_to(ROOT).as_posix()}` ({len(rows)} registros) · {note}",
        "> BMP em NmL CH₄/g SV, como o registro normalizou. Só substrato bruto é comparado às faixas.",
        "> Valor fora da faixa é evidência a conferir, não erro da faixa. Nada aqui muda a plataforma.",
        "",
        "## Substratos do CP2b com registro",
        "",
        "| Código | Registros | Brutos comparáveis | Mediana bruto | Mín–máx bruto | Tier A "
        "| Faixa CP2b | Fora CP2b | Faixa feedstocks.yaml | Fora yaml |",
        "|---|---:|---:|---:|---|---:|---|---:|---|---:|",
    ]
    for s in summ_in:
        L.append(f"| {s['codigo']} | {s['registros']} | {s['brutos_comparaveis']} | {fmt(s['mediana_bruto'])} "
                 f"| {span(s['min_bruto'], s['max_bruto'])} | {s['tier_a']} "
                 f"| {s['faixa_cp2b'] or '—'} | {s['fora_cp2b'] if s['faixa_cp2b'] else '—'} "
                 f"| {s['faixa_feedstocks_yaml'] or '—'} | {s['fora_feedstocks_yaml']} |")
    if any(s["codigo"] == "VINHACA" for s in summ_in):
        L += ["", "O CP2b calcula a vinhaça direto por m³ de etanol (elemento \"direto\"), sem BMP por g SV. "
              "Para a vinhaça, a comparação por g SV é só com o feedstocks.yaml."]

    out = [r for r in rows if r["situacao_cp2b"] in ("abaixo", "acima")
           or r["situacao_feedstocks_yaml"] in ("abaixo", "acima")]
    L += ["", "## Registros brutos fora de uma faixa", ""]
    if not out:
        L.append("Nenhum.")
    for r in out:
        pairs = (("CP2b", "situacao_cp2b"), ("yaml", "situacao_feedstocks_yaml"))
        where = ", ".join(f"{lab} {r[k]}" for lab, k in pairs if r[k] in ("abaixo", "acima"))
        link = f"https://doi.org/{r['doi']}" if r["doi"] else (r["url"] or "sem link")
        L += [f"- **{r['codigo']} · {fmt(r['bmp_nml_gsv'])} NmL/g SV** ({where}) · tier {r['tier']} · {r['pais']} · "
              f"{r['fonte']} · {link}",
              f"  - Nota da rotina: {r['nota_da_rotina']}"]

    L += ["", "## Substratos fora do CP2b (candidatos, sem faixa no artigo)", "",
          "| Código | Registros | Brutos comparáveis | Mediana bruto | Faixa feedstocks.yaml |",
          "|---|---:|---:|---:|---|"]
    for s in summ_out:
        L.append(f"| {s['codigo']} | {s['registros']} | {s['brutos_comparaveis']} | {fmt(s['mediana_bruto'])} "
                 f"| {s['faixa_feedstocks_yaml'] or '—'} |")

    nc = [r for r in rows if r["bmp_nml_gsv"] is None]
    L += ["", "## Sem valor normalizado no registro (por DQO, biogás ou base de CNTP não confirmada)", ""]
    L += [f"- {r['codigo']} · {r['valor_original']} · {r['fonte']}" for r in nc] or ["Nenhum."]

    L += ["", "## Como ler", "",
          "- Os valores, DOIs e notas são os do registro do Literature Watch, com a verificação que a rotina "
          "registrou. Antes de citar um valor, abra a fonte.",
          "- Tier A/B/C é a nota de qualidade da rotina (protocolo, réplicas, controle positivo).",
          "- `ja_no_pilar` diz se a fonte já está no corpus de referências da plataforma."]
    return L


def main() -> None:
    registry = latest_registry()
    records = read_registry(registry)
    cp2b, note = cp2b_bmp()
    yml = yaml_bmp()
    rows = evidence(records, cp2b, yml)
    subs = B.loader_constant("SUBSTRATES")
    codes = list(dict.fromkeys(r["codigo"] for r in rows))
    summ_in = summary(rows, [c for c in codes if c in subs], cp2b, yml)
    summ_out = summary(rows, [c for c in codes if c not in subs], cp2b, yml)
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "evidencia.csv", rows)
    write_csv(OUT / "resumo.csv", summ_in + summ_out)
    (OUT / "RELATORIO.md").write_text("\n".join(report(rows, summ_in, summ_out, registry, note)) + "\n",
                                      encoding="utf-8")
    print(f"{len(rows)} registros · {note}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
