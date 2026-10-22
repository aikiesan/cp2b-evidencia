#!/usr/bin/env python3
"""
CP2b v5.1 sensitivity to the literature: the N1 -> N4 cascade with one parameter swapped at a time.

The three evidence libraries (build_evidencia_bmp.py, build_evidencia_geracao.py,
build_evidencia_fde.py) say where the Literature Watch registries agree with the
CP2b parameters and where they do not. This script says how much each
disagreement moves the potential, keeping the CP2b cascade as it is:

  N1  = base × g × ST × SV × BMP          (theoretical)
  N2  = N1 × FC                           (collectable)
  N3a = N2 × FCo                          (after competing uses)
  N3  = N3a − U                           (minus existing energy use; Ideal)
  N4  = N3 × FS × FL                      (storage and logistics; Real)

A swapped parameter is a multiplier on the stage where it enters: g, ST, SV and
BMP on N1, FC on N2, FCo on N3a, FS on N4. The multiplier is the literature value
in CP2b units over the CP2b median, taken from the evidence libraries, so the
numbers here cannot drift from theirs. Each municipality is recomputed from the
snapshot's own levels: N3 = max(N3a' − U, 0), with U unchanged because it is an
energy use already in place, and N4 = N3 × (FS × FL of that municipality).

The scenarios are of three kinds:

  literatura  the literature value, with its low and high ends
  hipótese    an alternative reading the method team has to settle (e.g. the
              dairy g is already the collectable fraction, so FC = 1)
  definição   a reading the article must rule out (days on feed / 365 as FS,
              "not used as fertiliser" as FCo), to show what is at stake

Nothing here changes the platform, the snapshot or the article numbers. A shift
inside the CP2b min-max band is within the uncertainty the article already
reports; one outside it is a limitation to state or a v5.2 item.

CP2b values come only from the v5.1 snapshot with the loader's checksums
(levels and parameters). The script also checks that the snapshot reproduces
the loader's state totals and the cascade identities before using it.

Run from the repo root:
  python3 scripts/build_sensibilidade_cp2b.py

Outputs (outputs/sensibilidade_cp2b/):
  cascata.csv        N1, N2, N3a, U, N3, N4 per substrate and for the state (med)
  sensibilidade.csv  one row per scenario: multipliers and state N1-N4 after the swap
  revisao.csv        per substrate: N4 share and what each evidence library says
  RELATORIO.md       the three tables, the checks and how to read them
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "sensibilidade_cp2b"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F = _load(ROOT / "scripts" / "build_evidencia_fde.py")
G, E = F.G, F.E
B = E.B
fmt = E.fmt

LEVELS = ("n1", "n2", "n3a", "u", "n3", "n4")
COLUMNS = {
    "n1_ch4_nm3_year": "n1",
    "n2_ch4_nm3_year": "n2",
    "n3_before_existing_use_ch4_nm3_year": "n3a",
    "existing_use_subtracted_ch4_nm3_year": "u",
    "n3_ch4_nm3_year": "n3",
    "n4_ch4_nm3_year": "n4",
}
LABELS = {"n1": "N1", "n2": "N2", "n3a": "N3a", "u": "U", "n3": "N3", "n4": "N4"}
# CP2b element -> the cascade stage it enters
STAGE = {"g": "n1", "ST": "n1", "SV": "n1", "g×ST": "n1", "BMP": "n1", "FC": "n2", "FCo": "n3a", "FS": "n4"}
ELEMENTS = ("g", "ST", "SV", "BMP", "FC", "FCo", "FS")
IDENTITY_RTOL = 1e-6

# (key, kind, label, CP2b codes, terms, note)
# term: (library, element, record ids) with library "ger", "fde" or "bmp"; or ("valor", element, (lo, mid, hi)).
# Records of one element are pooled (low = min, high = max, central = mean of centrals); elements multiply.
SCENARIOS = (
    ("leite_g", "literatura", "g do bovino de leite = excreção medida", ("BOV_LEITE",),
     (("ger", "g", ("LIV-20261019-09", "LIV-20261019-02")),),
     "Vale se o g do CP2b for excreção total. Alternativa a leite_fc1."),
    ("leite_fc1", "hipótese", "g do leite já é a fração coletável: FC = 1", ("BOV_LEITE",),
     (("valor", "FC", (1.0, 1.0, 1.0)),),
     "Vale se o g do CP2b já descontar a coleta. Alternativa a leite_g."),
    ("confinado_ms", "literatura", "matéria orgânica fecal do confinado = medida", ("BOV_CONFINADO",),
     (("ger", "g×ST", ("LIV-20261019-05",)), ("ger", "SV", ("LIV-20261019-03",))),
     "Matéria seca fecal × SV medidos, contra g × ST × SV do CP2b."),
    ("confinado_fc", "literatura", "FC do confinado = 0,9 (coleta no alojamento)", ("BOV_CONFINADO",),
     (("fde", "FC", ("FDE-20261017-06",)),), "Tier C; o mesmo 0,9 vale para todos os rebanhos na fonte."),
    ("pasto_g", "literatura", "g do bovino de pasto = inventário nacional", ("BOV_PASTO_MISTO",),
     (("ger", "g", ("LIV-20261019-11",)),), "FC do pasto é 0: muda o N1, não o N4."),
    ("citros_fco", "literatura", "FCo do bagaço de laranja = sobra após a peletização", ("BAGACO_CITROS",),
     (("fde", "FCo", ("FDE-20261018-16",)),), "Fonte de 2004, tier B."),
    ("palha_fs", "literatura", "FS da palha de cana = massa após decomposição no solo", ("PALHA",),
     (("fde", "FS", ("FDE-20261017-19",)),), "Depende do tempo entre a colheita e o enfardamento."),
    ("bagaco_bmp", "literatura", "BMP do bagaço de cana = medido (bruto)", ("BAGACO",),
     (("bmp", "BMP", ("BMP-20261017-01", "BMP-20261017-02", "BMP-20261017-03")),), "Tiers B e C."),
    ("soja_bmp", "literatura", "BMP da palha de soja = medido (bruto)", ("PALHA_SOJA",),
     (("bmp", "BMP", ("BMP-20261017-29",)),), "Um registro, tier C."),
    ("aves_fco_adubo", "definição", "FCo das aves lido como 'fração não usada como adubo'",
     ("AVES_CORTE", "AVES_POSTURA"), (("fde", "FCo", ("FDE-20261018-11",)),),
     "Não é a definição do CP2b (adubo é compatível com a digestão)."),
    ("leite_suinos_fco_adubo", "definição", "FCo de leite e suínos lido como 'fração não usada como adubo'",
     ("BOV_LEITE", "SUINOS"), (("fde", "FCo", ("FDE-20261018-09", "FDE-20261018-10")),),
     "Não é a definição do CP2b (adubo é compatível com a digestão)."),
    ("confinado_fs_dof", "definição", "FS do confinado lido como dias de cocho / 365", ("BOV_CONFINADO",),
     (("fde", "FS", ("FDE-20261017-02",)),), "A DEC-013 proíbe; a base já é o estoque confinado."),
    ("cana_fs_safra", "definição", "FS de vinhaça e torta lido como fração do ano em safra",
     ("VINHACA", "TORTA_FILTRO"), (("fde", "FS", ("FDE-20261017-17", "FDE-20261017-18")),),
     "A DEC-013 proíbe; a safra pesa no dimensionamento da planta."),
)
# Literature scenarios applied together, at their central multipliers, for each dairy reading.
COMBINED = (
    ("literatura_g_total", "Toda a literatura, g do leite = excreção total",
     ("leite_g", "confinado_ms", "confinado_fc", "pasto_g", "citros_fco", "palha_fs", "bagaco_bmp", "soja_bmp")),
    ("literatura_g_coletavel", "Toda a literatura, g do leite = fração coletável (FC = 1)",
     ("leite_fc1", "confinado_ms", "confinado_fc", "pasto_g", "citros_fco", "palha_fs", "bagaco_bmp",
      "soja_bmp")),
)


# ── Snapshot ────────────────────────────────────────────────────────────────


def _verified(key: str) -> tuple[Path | None, str]:
    path = B.CP2B_SNAPSHOT / B.loader_constant("FILES")[key]
    if not path.exists():
        return None, f"sem o snapshot CP2b v5.1 ({path.name})"
    if hashlib.sha256(path.read_bytes()).hexdigest() != B.loader_constant("EXPECTED_SHA256")[key]:
        return None, f"snapshot CP2b recusado: o sha256 de {path.name} não confere com o loader"
    return path, ""


def _f(v) -> float:
    x = E.num(v)
    return 0.0 if x is None or math.isnan(x) else x


def read_levels() -> tuple[list[dict] | None, str]:
    """Rows (municipality × substrate × scenario) with the six levels and FS × FL, or None with the reason."""
    path, why = _verified("levels")
    if path is None:
        return None, why
    rows = []
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            row = {"ibge": str(int(float(r["ibge_code"]))), "codigo": r["substrate"], "cenario": r["scenario"]}
            row.update({k: _f(r.get(col)) for col, k in COLUMNS.items()})
            fsfl = E.num(r.get("fs_x_fl"))
            row["fsfl"] = fsfl if fsfl is not None else (row["n4"] / row["n3"] if row["n3"] else 0.0)
            rows.append(row)
    return rows, f"{path.name} (sha256 conferido)"


def checks(rows: list[dict]) -> list[tuple[str, bool, str]]:
    """The snapshot reproduces the loader's state totals and the cascade identities used to recompute it."""
    out = []
    totals = defaultdict(float)
    for r in rows:
        for lvl in ("n1", "n2", "n3", "n4"):
            totals[(r["cenario"], lvl)] += r[lvl]
    for (scen, lvl), want in B.loader_constant("EXPECTED_STATE_TOTALS").items():
        got = totals[(scen, lvl)]
        ok = math.isclose(got, want, rel_tol=1e-9)
        detail = f"{fmt(got / 1e6, 1)} mi (loader {fmt(want / 1e6, 1)})"
        out.append((f"total do estado {LABELS[lvl]} {scen}", ok, detail))

    def bad(pred):
        return sum(1 for r in rows if not pred(r))

    def close(a, b):
        return math.isclose(a, b, rel_tol=IDENTITY_RTOL, abs_tol=1e-3)

    n = bad(lambda r: close(r["n3"], max(r["n3a"] - r["u"], 0.0)))
    out.append(("N3 = máx(N3a − U, 0) em cada linha", n == 0, f"{n} linhas fora de {len(rows)}"))
    n = bad(lambda r: close(r["n4"], r["n3"] * r["fsfl"]))
    out.append(("N4 = N3 × FS × FL em cada linha", n == 0, f"{n} linhas fora de {len(rows)}"))
    return out


def cascade(rows: list[dict], scenario: str = "med") -> dict[str, dict[str, float]]:
    """substrate -> level -> state total, for one CP2b scenario."""
    out: dict = defaultdict(lambda: dict.fromkeys(LEVELS, 0.0))
    for r in rows:
        if r["cenario"] == scenario:
            for lvl in LEVELS:
                out[r["codigo"]][lvl] += r[lvl]
    return out


def recompute(rows: list[dict], mult: dict[tuple[str, str], float]) -> dict[str, float]:
    """State N1..N4 (med) with stage multipliers {(code, stage): m}; U and FS × FL per municipality kept."""
    tot = dict.fromkeys(LEVELS, 0.0)
    for r in rows:
        if r["cenario"] != "med":
            continue
        m = {s: mult.get((r["codigo"], s), 1.0) for s in ("n1", "n2", "n3a", "n4")}
        n1 = r["n1"] * m["n1"]
        n2 = r["n2"] * m["n1"] * m["n2"]
        n3a = r["n3a"] * m["n1"] * m["n2"] * m["n3a"]
        n3 = max(n3a - r["u"], 0.0)
        for k, v in (("n1", n1), ("n2", n2), ("n3a", n3a), ("u", r["u"]), ("n3", n3),
                     ("n4", n3 * r["fsfl"] * m["n4"])):
            tot[k] += v
    return tot


# ── Literature, in CP2b units, from the evidence libraries ──────────────────


def literature() -> dict:
    """What the three libraries give: generation rows, FDE records and BMP records, keyed by record."""
    params, note = E.cp2b_parameters(ELEMENTS)
    ger = {(r["record_id"], r["codigo"], r["elemento"]): r
           for r in G.compare({r["record_id"]: r for r in E.read_registry(G.latest_registry())},
                              G.cp2b_ranges(params))}
    fde = {r["record_id"]: r for r in E.read_registry(F.latest_registry())}
    bmp = {r["record_id"]: r for r in E.read_registry(E.latest_registry())}
    return {"params": G.cp2b_ranges(params), "ger": ger, "fde": fde, "bmp": bmp, "note": note}


def term_value(lib: dict, code: str, term: tuple) -> tuple[float, float, float] | None:
    """(low, central, high) of one term in CP2b units, pooled over its records."""
    source, element, ref = term
    if source == "valor":
        return ref
    vals = []
    for rid in ref:
        if source == "ger":
            row = lib["ger"].get((rid, code, element))
            if row is None:
                continue
            lo, hi = row["literatura_min"], row["literatura_max"]
            vals.append((lo, (lo + hi) / 2, hi))
        elif source == "fde" and rid in lib["fde"]:
            lo, mid, hi = F.bounds(lib["fde"][rid])
            vals.append((lo, mid if mid is not None else (lo + hi) / 2, hi))
        elif source == "bmp" and rid in lib["bmp"]:
            v = E.num(lib["bmp"][rid].get("bmp_nmlch4_gvs"))
            if v is not None:
                vals.append((v, v, v))
    if not vals:
        return None
    return min(v[0] for v in vals), sum(v[1] for v in vals) / len(vals), max(v[2] for v in vals)


def multipliers(lib: dict, codes, terms) -> dict[tuple[str, str], tuple[float, float, float]] | None:
    """{(code, stage): (low, central, high)} for one scenario, or None if a term or a CP2b median is missing."""
    out: dict = {}
    for code in codes:
        for term in terms:
            value = term_value(lib, code, term)
            rng = lib["params"].get((code, term[1]))
            if value is None or not rng or not rng[1]:
                return None
            key = (code, STAGE[term[1]])
            prev = out.get(key, (1.0, 1.0, 1.0))
            out[key] = tuple(p * v / rng[1] for p, v in zip(prev, value))
    return out


def run_scenarios(rows: list[dict], lib: dict) -> list[dict]:
    base = recompute(rows, {})
    band = {s: sum(c["n4"] for c in cascade(rows, s).values()) for s in ("min", "max")}
    found = {}
    out = []
    for key, kind, label, codes, terms, note in SCENARIOS:
        mult = multipliers(lib, codes, terms)
        found[key] = mult
        out.append(_row(rows, base, band, key, kind, label, codes, mult, note))
    for key, label, parts in COMBINED:
        if any(found.get(p) is None for p in parts):
            mult = None
        else:
            mult = {}
            for p in parts:
                for k, v in found[p].items():
                    prev = mult.get(k, (1.0, 1.0, 1.0))
                    mult[k] = tuple(a * b for a, b in zip(prev, v))
        codes = sorted({c for p in parts for c, _ in (found.get(p) or {})})
        out.append(_row(rows, base, band, key, "combinado", label, codes, mult, " + ".join(parts)))
    return out


def _row(rows, base, band, key, kind, label, codes, mult, note) -> dict:
    row = {"cenario": key, "tipo": kind, "descricao": label, "substratos": " · ".join(codes), "nota": note,
           "multiplicadores": "", "n4_baixo": None, "n4_alto": None, "dentro_faixa_cp2b": ""}
    if mult is None:
        row.update({lvl: None for lvl in LEVELS})
        row["multiplicadores"] = "sem dado (registro ou parâmetro ausente)"
        return row
    mid = {k: v[1] for k, v in mult.items()}
    after = recompute(rows, mid)
    row.update(after)
    row.update({f"delta_{lvl}": after[lvl] - base[lvl] for lvl in ("n1", "n2", "n3", "n4")})
    if any(v[0] != v[2] for v in mult.values()):
        ends = [recompute(rows, {k: v[i] for k, v in mult.items()})["n4"] for i in (0, 2)]
        row["n4_baixo"], row["n4_alto"] = min(ends), max(ends)
    row["multiplicadores"] = "; ".join(f"{c} {LABELS[s]} ×{_m(v)}" for (c, s), v in sorted(mult.items()))
    row["dentro_faixa_cp2b"] = "sim" if band["min"] <= after["n4"] <= band["max"] else "não"
    return row


def _m(v: tuple[float, float, float]) -> str:
    if v[0] == v[2]:
        return fmt(v[1], 2)
    return f"{fmt(v[1], 2)} ({fmt(v[0], 2)}–{fmt(v[2], 2)})"


# ── Review per substrate ────────────────────────────────────────────────────


def _status(verdicts: list[str]) -> str:
    v = [x for x in verdicts if x]
    if not v:
        return "—"
    off = [x for x in v if x in ("acima", "abaixo")]
    if not off:
        return f"confere ({len(v)})"
    return f"diverge: {len(off)} de {len(v)} ({', '.join(sorted(set(off)))})"


def review(rows: list[dict], lib: dict) -> list[dict]:
    casc = cascade(rows)
    state_n4 = sum(c["n4"] for c in casc.values())
    ger = list(lib["ger"].values())
    fde = F.compare(lib["fde"], F.with_fc_fco(lib["params"]))
    bmp = E.evidence(list(lib["bmp"].values()), {c: v for (c, e), v in lib["params"].items() if e == "BMP"}, {})
    out = []
    for code, (_, sector, ligno) in B.loader_constant("SUBSTRATES").items():
        c = casc.get(code, dict.fromkeys(LEVELS, 0.0))
        lots = [r["lotes_por_ano_implicitos"] for r in ger if r["codigo"] == code and r["lotes_por_ano_implicitos"]]
        out.append({
            "codigo": code, "setor": sector, "lignocelulosico": ligno, "n4": c["n4"],
            "parcela_n4": c["n4"] / state_n4 if state_n4 else None,
            "geracao": _status([r["situacao"] for r in ger if r["codigo"] == code])
            + (f"; lotes/ano implícitos {', '.join(lots)}" if lots else ""),
            "bmp": _status([r["situacao_cp2b"] for r in bmp if r["codigo"] == code]),
            "fc": _status([r["situacao"] for r in fde if r["codigo"] == code and r["fator"] == "FC"]),
            "fco": _status([r["situacao"] for r in fde if r["codigo"] == code and r["fator"] in ("FCo", F.FC_FCO)]),
            "fs": _status([r["situacao"] for r in fde if r["codigo"] == code and r["fator"] == "FS"]),
            "cenarios": ", ".join(k for k, _, _, codes, _, _ in SCENARIOS if code in codes),
        })
    return sorted(out, key=lambda r: -r["n4"])


# ── Output ──────────────────────────────────────────────────────────────────


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def mi(x: float | None, nd: int = 1) -> str:
    return "—" if x is None else fmt(x / 1e6, nd)


def pct(x: float | None, base: float) -> str:
    if x is None or not base:
        return "—"
    return f"{'+' if x > 0 else ''}{fmt(100 * x / base, 1)} %"


def report(casc, chk, scen, rev, levels_note, lib_note, band) -> list[str]:
    state = {lvl: sum(c[lvl] for c in casc.values()) for lvl in LEVELS}
    L = [
        "# Sensibilidade do CP2b v5.1 à literatura (N1 → N4)",
        "",
        f"> Níveis: {levels_note} · Parâmetros: {lib_note}",
        "> Cenário med do CP2b; volumes em milhões de Nm³ de CH₄ por ano. Cada cenário troca um parâmetro pelo valor "
        "da literatura na etapa onde ele entra e refaz a cascata município a município, com U e FS × FL de cada "
        "município mantidos. Nada aqui muda a plataforma.",
        "",
        "## 1. Cascata do CP2b v5.1 (med)",
        "",
        "| Substrato | N1 | N2 | N3a | U | N3 (Ideal) | N4 (Real) | % do N4 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for code, c in sorted(casc.items(), key=lambda kv: -kv[1]["n4"]):
        L.append(f"| {code} | " + " | ".join(mi(c[lvl]) for lvl in LEVELS)
                 + f" | {fmt(100 * c['n4'] / state['n4'], 1) if state['n4'] else '—'} |")
    L.append("| **Estado** | " + " | ".join(f"**{mi(state[lvl])}**" for lvl in LEVELS) + " | 100 |")

    L += ["", "## 2. Conferência do snapshot", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    L += [f"| {name} | {'ok' if ok else 'FALHOU'} | {detail} |" for name, ok, detail in chk]

    L += ["", "## 3. Sensibilidade", "",
          f"N4 do estado hoje: {mi(state['n4'])} mi Nm³/ano; faixa do próprio CP2b, cenários min e max: "
          f"{mi(band['min'])}–{mi(band['max'])} mi. A coluna \"Na faixa\" diz se o N4 depois da troca fica "
          "dentro dela. A faixa é larga; um cenário dentro dela ainda pode mudar o N4 de forma que o artigo "
          "precisa comentar.", "",
          "| Cenário | Tipo | O que muda | Multiplicador (med, faixa) | N1 | N2 | N3 | N4 | ΔN4 | N4 na faixa da "
          "literatura | Na faixa |",
          "|---|---|---|---|---:|---:|---:|---:|---:|---|---|"]
    for r in scen:
        if r["n4"] is None:
            L.append(f"| {r['cenario']} | {r['tipo']} | {r['descricao']} | {r['multiplicadores']} "
                     "| — | — | — | — | — | — | — |")
            continue
        ends = f"{mi(r['n4_baixo'])}–{mi(r['n4_alto'])}" if r["n4_baixo"] is not None else "—"
        L.append(f"| {r['cenario']} | {r['tipo']} | {r['descricao']} | {r['multiplicadores']} "
                 f"| {mi(r['n1'])} | {mi(r['n2'])} | {mi(r['n3'])} | {mi(r['n4'])} "
                 f"| {pct(r['delta_n4'], state['n4'])} | {ends} | {r['dentro_faixa_cp2b']} |")
    L += ["", "Notas dos cenários:", ""]
    L += [f"- **{r['cenario']}**: {r['nota']}" for r in scen]

    L += ["", "## 4. Revisão por substrato", "",
          "O que as três bibliotecas de evidência dizem de cada substrato, do maior N4 para o menor. \"Confere\" "
          "= todo registro comparável cai dentro da faixa do CP2b ou se sobrepõe a ela; \"diverge\" = algum fica "
          "inteiro acima ou abaixo.", "",
          "| Substrato | % do N4 | Geração (g, ST, SV) | BMP | FC | FCo | FS | Cenários |",
          "|---|---:|---|---|---|---|---|---|"]
    for r in rev:
        share = fmt(100 * r["parcela_n4"], 1) if r["parcela_n4"] is not None else "—"
        L.append(f"| {r['codigo']} | {share} | {r['geracao']} | {r['bmp']} | {r['fc']} | {r['fco']} | {r['fs']} "
                 f"| {r['cenarios'] or '—'} |")
    bare = [r["codigo"] for r in rev if all(r[k] == "—" for k in ("geracao", "bmp", "fc", "fco", "fs"))]
    L += ["", f"Sem nenhum registro comparável: {', '.join(bare) or 'nenhum'}."]

    L += ["", "## Como ler", "",
          "- O multiplicador é o valor da literatura (na unidade do CP2b) sobre a mediana do CP2b, tirado das "
          "bibliotecas de evidência. Registros do mesmo elemento entram juntos (faixa = menor e maior; centro = "
          "média dos centros); elementos diferentes se multiplicam.",
          "- U fica como está porque é uso energético já instalado; se o N3a cai abaixo de U, o N3 do município "
          "fica em zero, como no CP2b.",
          "- Cenários do tipo definição não são propostas: mostram o tamanho do erro de quem ler FS ou FCo com "
          "outra definição. Servem para a frase dos Métodos.",
          "- leite_g e leite_fc1 são alternativas; por isso há dois combinados.",
          "- O FL (espacial, por município) e o U não têm registro comparável no Literature Watch; ficam como "
          "estão em todos os cenários.",
          "- Números, DOIs e notas vêm dos registros do Literature Watch. Antes de citar, abra a fonte."]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, levels_note = read_levels()
    lib = literature()
    if rows is None or not lib["params"]:
        why = levels_note if rows is None else lib["note"]
        (OUT / "RELATORIO.md").write_text(
            "# Sensibilidade do CP2b v5.1 à literatura (N1 → N4)\n\n"
            f"Não rodou: {why}. A cascata e a sensibilidade precisam dos níveis e dos parâmetros do snapshot v5.1 "
            "com o sha256 do loader.\n", encoding="utf-8")
        print(f"Sem cascata: {why}")
        return
    casc = cascade(rows)
    chk = checks(rows)
    scen = run_scenarios(rows, lib)
    rev = review(rows, lib)
    write_csv(OUT / "cascata.csv", [{"codigo": k, **v} for k, v in sorted(casc.items())])
    write_csv(OUT / "sensibilidade.csv", scen)
    write_csv(OUT / "revisao.csv", rev)
    band = {s: sum(c["n4"] for c in cascade(rows, s).values()) for s in ("min", "max")}
    (OUT / "RELATORIO.md").write_text("\n".join(report(casc, chk, scen, rev, levels_note, lib["note"], band)) + "\n",
                                      encoding="utf-8")
    failed = [name for name, ok, _ in chk if not ok]
    print(f"{len(scen)} cenários · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
