#!/usr/bin/env python3
"""
Availability factor evidence: the Literature Watch FDE registry against CP2b.

The daily "PILAR-2b Literature Watch" routine keeps REGISTRY_fde_factors.csv on
Google Drive: values the literature gives for FC, FCo, FS and FL, each with the
definition the source uses, a quality tier and the stream it speaks to. A dated
copy lives in data/literature_watch/.

The registry labels a number FC, FCo, FS or FL by what it resembles; the source
often means something else. CP2b reads them as:

  FC   technical collection efficiency of the base A
  FCo  fraction left after competing uses; fertiliser use of manure and vinasse
       is compatible with digestion (the digestate goes back to the field)
  FS   mass retained after a documented loss (DEC-013), never days of supply / 365
  FL   a spatial fraction per municipality (fl_v5), not a distance

Crop residues keep the straw left on the soil for agronomic reasons in FC, not
in FCo, so a removable fraction from the literature is compared with FC × FCo
(min×min, med×med, max×max).

So each record is read by hand below. MAP holds the records whose definition is
the CP2b one; they are placed against the CP2b range. CONTEXT holds the records
that touch a CP2b substrate with another definition (a share of farms, days on
feed, a harvest window, a haul distance in km, "not used as fertiliser"), with
the reason they are not compared. Streams CP2b does not model are listed apart.

CP2b ranges come only from the v5.1 snapshot with the loader's checksum. A value
outside a range is evidence to check, not an error in the range. Nothing here
changes the platform or the CP2b numbers.

Run from the repo root:
  python3 scripts/build_evidencia_fde.py

Outputs (outputs/evidencia_fde/):
  comparacao.csv  one row per MAP entry, literature and CP2b side by side
  contexto.csv    one row per CONTEXT entry, with the reason it is not compared
  RELATORIO.md    both, plus the streams outside CP2b
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "data" / "literature_watch"
OUT = ROOT / "outputs" / "evidencia_fde"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load(ROOT / "scripts" / "build_evidencia_geracao.py")
E = G.E
fmt, num = E.fmt, E.num

FACTORS = ("FC", "FCo", "FS", "FL")
FC_FCO = "FC×FCo"
# Registry stream -> CP2b substrate codes it can speak to (empty: CP2b does not model it)
STREAMS = {
    "bovinos": ("BOV_LEITE", "BOV_CONFINADO", "BOV_PASTO_MISTO"),
    "suinos": ("SUINOS",),
    "aves": ("AVES_CORTE", "AVES_POSTURA"),
    "palha_cana": ("PALHA",),
    "vinhaca": ("VINHACA",),
    "torta_filtro": ("TORTA_FILTRO",),
    "milho": ("PALHA_MILHO",),
    "soja": ("PALHA_SOJA",),
    "cafe": ("CASCA_CAFE",),
    "citros": ("BAGACO_CITROS",),
    "poda_urbana": ("PODA_URBANA",),
    "silvicultura": (),
    "aquicultura": (),
}

# Same definition as CP2b: (record_id, CP2b code, CP2b factor, what the source measures)
MAP = (
    ("FDE-20261017-06", "BOV_CONFINADO", "FC", "eficiência de coleta no alojamento, 90 % para todos os rebanhos"),
    ("FDE-20261017-07", "SUINOS", "FC", "eficiência de coleta no alojamento, 90 % para todos os rebanhos"),
    ("FDE-20261018-13", "SUINOS", "FCo", "estabelecimentos que tratam dejeto sem biodigestor (Censo 2006); "
                                         "conta estabelecimentos, não massa"),
    ("FDE-20261017-20", "VINHACA", "FCo", "destilarias de SP sem digestão (8 de 165 digerem); fertirrigação "
                                          "compatível"),
    ("FDE-20261017-13", "PALHA", FC_FCO, "fração recolhível; o resto fica no solo por função agronômica"),
    ("FDE-20261017-15", "PALHA", FC_FCO, "recolhimento observado em usinas de SP (9 % e 27 %; caso potencial 50 %)"),
    ("FDE-20261017-19", "PALHA", "FS", "massa que resta após a decomposição no solo antes do enfardamento: o "
                                       "registro chama de FC, mas é retenção de massa após perda (DEC-013)"),
    ("FDE-20261018-01", "PALHA_MILHO", FC_FCO, "fração removível sem perda de produtividade"),
    ("FDE-20261018-02", "PALHA_MILHO", FC_FCO, "fração acima da cobertura do plantio direto"),
    ("FDE-20261018-03", "PALHA_MILHO", FC_FCO, "remoção sustentável × fração sem uso concorrente"),
    ("FDE-20261018-04", "PALHA_SOJA", FC_FCO, "remoção sustentável; sem uso concorrente"),
    ("FDE-20261018-05", "CASCA_CAFE", "FCo", "fração ainda sem uso (adubo, combustível de secador)"),
    ("FDE-20261018-16", "BAGACO_CITROS", "FCo", "fração ainda sem uso: o resíduo vira polpa cítrica peletizada "
                                                "para ração"),
    ("FDE-20261018-19", "BAGACO_CITROS", "FS", "massa retida após 90 dias de ensilagem"),
)

_DOF = ("dias de cocho / 365. A base do CP2b é o estoque confinado (GEDAVE), cabeças presentes, não animais "
        "que passam pelo cocho no ano; DOF/365 só cabe numa base de fluxo anual. E pela DEC-013 o FS nunca "
        "é dias / 365.")
_HERD = "no CP2b a parcela confinada está na base A (estoque confinado GEDAVE), não no FC."
_FERT = ("fração não usada como adubo. No CP2b o adubo é compatível com a digestão (o digestato volta ao "
         "campo), por isso o FCo fica perto de 1.")
_KM = ("distância em km. O FL do CP2b é uma fração espacial por município (fl_v5), não um raio; só dá para "
       "comparar sabendo o raio que o fl_v5 usa.")
_SEASON = ("fração do ano em safra. A geração anual não muda com a safra; pela DEC-013 o FS do CP2b é "
           "retenção de massa. A safra pesa no dimensionamento da planta (fator de capacidade, estoque), não "
           "no potencial anual.")
# Same substrate, other definition: (record_id, CP2b codes, CP2b factor to show or None, why it is not compared)
CONTEXT = (
    ("FDE-20261017-01", ("BOV_CONFINADO",), None, "45 % do abate de SP passou por confinamento; " + _HERD),
    ("FDE-20261017-04", ("BOV_CONFINADO",), None, "parcela de estabelecimentos que confinam, não de cabeças; " + _HERD),
    ("FDE-20261017-02", ("BOV_CONFINADO",), "FS", _DOF),
    ("FDE-20261017-03", ("BOV_CONFINADO",), "FS", _DOF),
    ("FDE-20261017-05", ("BOV_CONFINADO",), "FS", _DOF),
    ("FDE-20261017-06", ("BOV_LEITE",), "FC",
     "eficiência de coleta do esterco alojado. O FC do leite no CP2b vale para todas as vacas ordenhadas e "
     "também desconta o tempo fora do alojamento, por isso fica abaixo."),
    ("FDE-20261018-08", ("BOV_LEITE",), "FC",
     "parcela dos sistemas de leite de SP: 0,36 % confinado, 5,53 % intensivo a pasto, 19,25 % semiextensivo, "
     "74,84 % extensivo. Não é FC, mas um FC de 0,5 sobre todas as vacas ordenhadas pede coleta grande fora "
     "do confinamento (sala de ordenha, cocho na seca)."),
    ("FDE-20261018-12", ("BOV_LEITE",), "FC",
     "vacas no cocho na seca (maio a outubro) e no pasto nas águas, numa fazenda (Embrapa, São Carlos). É "
     "fração do ano alojada: no CP2b isso pesa no FC do leite, não no FS (DEC-013)."),
    ("FDE-20261017-08", ("AVES_CORTE", "AVES_POSTURA"), None,
     "o FC das aves no CP2b é municipal: fração comercial do GEDAVE × 0,90. O termo de coleta 0,90 é o mesmo "
     "da fonte."),
    ("FDE-20261018-09", ("BOV_LEITE",), "FCo", _FERT),
    ("FDE-20261018-10", ("SUINOS",), "FCo", _FERT),
    ("FDE-20261018-11", ("AVES_CORTE", "AVES_POSTURA"), "FCo",
     _FERT + " É a maior distância de definição do registro: na leitura da fonte a cama cairia a 1/5."),
    ("FDE-20261017-12", ("AVES_CORTE",), "FCo",
     "sem valor numérico. Dá o preço da cama como adubo (R$ 145–236/t, SC, 2010) e o reuso por seis lotes: "
     "o uso concorrente da cama é econômico, não só agronômico."),
    ("FDE-20261017-17", ("VINHACA",), "FS", _SEASON),
    ("FDE-20261017-18", ("TORTA_FILTRO",), "FS", _SEASON),
    ("FDE-20261018-07", ("CASCA_CAFE",), "FS", _SEASON + " A casca é seca e estocável."),
    ("FDE-20261018-17", ("BAGACO_CITROS",), "FS", _SEASON),
    ("FDE-20261018-20", ("PODA_URBANA",), "FCo",
     "fração de municípios (metade manda poda para aterro ou lixão), não de massa."),
    ("FDE-20261017-09", ("SUINOS",), None, _KM),
    ("FDE-20261017-10", ("SUINOS",), None, _KM),
    ("FDE-20261017-11", ("SUINOS",), None, _KM),
    ("FDE-20261018-14", ("SUINOS",), None, _KM),
    ("FDE-20261018-15", ("BOV_LEITE", "BOV_CONFINADO"), None, _KM + " Estudo da Croácia."),
    ("FDE-20261017-14", ("PALHA",), None, _KM),
    ("FDE-20261017-16", ("PALHA",), None, _KM),
    ("FDE-20261018-18", ("BAGACO_CITROS",), None, _KM + " Estudo da Itália."),
)


def latest_registry() -> Path:
    files = sorted(REGISTRY_DIR.glob("REGISTRY_fde_factors_v*.csv"))
    if not files:
        raise FileNotFoundError(f"no REGISTRY_fde_factors_v*.csv in {REGISTRY_DIR}")
    return files[-1]


def bounds(r: dict) -> tuple[float | None, float | None, float | None]:
    """(low, central, high) of a record; a missing end falls back to the central value."""
    mid = num(r.get("value"))
    lo, hi = num(r.get("value_min")), num(r.get("value_max"))
    return (lo if lo is not None else mid), mid, (hi if hi is not None else mid)


def _source(r: dict) -> dict:
    return {"tier": r.get("tier", ""), "regiao": r.get("region", ""), "fonte": r.get("source_key", ""),
            "doi": r.get("doi", ""), "url": r.get("url", "")}


def with_fc_fco(params: dict) -> dict:
    """The CP2b ranges plus FC × FCo per substrate, as min×min, med×med, max×max."""
    out = dict(params)
    for code in {c for c, _ in params}:
        fc, fco = params.get((code, "FC")), params.get((code, "FCo"))
        if fc and fco:
            out[(code, FC_FCO)] = tuple(a * b for a, b in zip(fc, fco))
    return out


def compare(records: dict[str, dict], cp2b: dict) -> list[dict]:
    rows = []
    for rid, code, factor, what in MAP:
        r = records[rid]
        lo, mid, hi = bounds(r)
        rng = cp2b.get((code, factor))
        rows.append({
            "codigo": code, "fator": factor, "record_id": rid, "fator_no_registro": r.get("factor", ""),
            "literatura": mid, "literatura_min": lo, "literatura_max": hi,
            "cp2b_min": rng[0] if rng else None, "cp2b_med": rng[1] if rng else None,
            "cp2b_max": rng[2] if rng else None,
            "situacao": G.verdict(lo, hi, rng) if rng else "", "o_que_a_fonte_mede": what, **_source(r),
        })
    return rows


def context(records: dict[str, dict], cp2b: dict) -> list[dict]:
    rows = []
    for rid, codes, factor, why in CONTEXT:
        r = records[rid]
        lo, mid, hi = bounds(r)
        shown = [f"{c} {fmt(cp2b[(c, factor)][1], 2)}" for c in codes if factor and (c, factor) in cp2b]
        rows.append({
            "codigos": " · ".join(codes), "record_id": rid, "fator_no_registro": r.get("factor", ""),
            "literatura": mid, "literatura_min": lo, "literatura_max": hi, "unidade": r.get("unit", ""),
            "cp2b_fator": factor or "", "cp2b_med": "; ".join(shown), "por_que_nao_compara": why, **_source(r),
        })
    return rows


def _lit(lo, mid, hi) -> str:
    def v(x):
        s = fmt(x, 4)
        return s.rstrip("0").rstrip(",") if "," in s else s
    if lo is None and mid is None:
        return "—"
    if lo == hi:
        return v(mid if mid is not None else lo)
    return f"{v(mid)} ({v(lo)}–{v(hi)})" if mid is not None else f"{v(lo)}–{v(hi)}"


def _link(r: dict) -> str:
    return f"https://doi.org/{r['doi']}" if r["doi"] else r["url"]


def report(cmp_rows, ctx_rows, records: dict[str, dict], registry: Path, note: str) -> list[str]:
    L = [
        "# Evidência de FC, FCo, FS e FL: Literature Watch × CP2b",
        "",
        f"> Registro: `{registry.relative_to(ROOT).as_posix()}` ({len(records)} registros) · {note}",
        "> No CP2b: FC = eficiência de coleta da base A; FCo = fração que sobra após usos concorrentes (adubo é "
        "compatível com a digestão); FS = massa retida após perda documentada, nunca dias / 365 (DEC-013); "
        "FL = fração espacial por município.",
        "> O registro rotula pelo que o número parece; a leitura abaixo é pela definição da fonte. Valor fora da "
        "faixa é evidência a conferir, não erro da faixa. Nada aqui muda a plataforma.",
        "",
        "## Mesma definição do CP2b",
        "",
        "| Substrato | Fator | Literatura | CP2b mín–máx (med) | Situação | O que a fonte mede | Tier | Região "
        "| Fonte |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in cmp_rows:
        cp = (f"{fmt(r['cp2b_min'], 2)}–{fmt(r['cp2b_max'], 2)} ({fmt(r['cp2b_med'], 2)})"
              if r["cp2b_med"] is not None else "—")
        tag = r["fator"]
        if r["fator"] != r["fator_no_registro"]:
            tag += f" (registro: {r['fator_no_registro']})"
        L.append(f"| {r['codigo']} | {tag} | {_lit(r['literatura_min'], r['literatura'], r['literatura_max'])} "
                 f"| {cp} | {r['situacao'] or '—'} | {r['o_que_a_fonte_mede']} | {r['tier']} | {r['regiao']} "
                 f"| {_link(r)} |")

    L += ["", "## Mesmo substrato, outra definição", "",
          "Não entram na comparação. A coluna CP2b mostra o fator do CP2b que o registro toca, quando faz sentido.",
          "", "| Substrato | Registro | Rótulo | Valor | Unidade | CP2b (med) | Por que não compara | Tier | Fonte |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in ctx_rows:
        cp = f"{r['cp2b_fator']}: {r['cp2b_med']}" if r["cp2b_med"] else "—"
        L.append(f"| {r['codigos']} | {r['record_id']} | {r['fator_no_registro']} "
                 f"| {_lit(r['literatura_min'], r['literatura'], r['literatura_max'])} | {r['unidade']} | {cp} "
                 f"| {r['por_que_nao_compara']} | {r['tier']} | {_link(r)} |")

    read = {m[0] for m in MAP} | {c[0] for c in CONTEXT}
    outside = [r for r in records.values() if r["record_id"] not in read and STREAMS.get(r["feedstock_code"]) == ()]
    unread = [r for r in records.values() if r["record_id"] not in read and STREAMS.get(r["feedstock_code"]) != ()]
    L += ["", "## Fluxos que o CP2b não modela", ""]
    L += [f"- {r['record_id']} · {r['feedstock_code']} · {r['factor']} {r['value']} {r['unit']}: "
          f"{r['definition_in_source'][:160]}" for r in outside] or ["- nenhum"]
    if unread:
        L += ["", "## Registros ainda sem leitura", "",
              "Registros novos que ainda não estão em MAP nem em CONTEXT no script:", ""]
        L += [f"- {r['record_id']} · {r['feedstock_code']} · {r['factor']} {r['value']} {r['unit']}" for r in unread]
    L += ["", "## Como ler", "",
          "- Números, DOIs e notas são os do registro do Literature Watch, com a verificação que a rotina "
          "registrou. Antes de citar, abra a fonte.",
          "- FC×FCo: nas palhas o CP2b deixa a palha que fica no solo no FC, não no FCo. A fração removível da "
          "literatura é comparada com o produto, mín×mín a máx×máx.",
          "- \"—\" na coluna CP2b: o cp2b_parametros.csv do v5.1 não traz esse fator para o substrato, ou o "
          "snapshot não foi lido (veja o cabeçalho).",
          "- Um registro pode aparecer nas duas tabelas quando fala de mais de um substrato com sentidos "
          "diferentes (a eficiência de coleta de 90 % é FC para o confinado e só contexto para o leite)."]
    return L


def main() -> None:
    registry = latest_registry()
    records = {r["record_id"]: r for r in E.read_registry(registry)}
    params, note = E.cp2b_parameters(FACTORS)
    cp2b = with_fc_fco(params)
    cmp_rows, ctx_rows = compare(records, cp2b), context(records, cp2b)
    OUT.mkdir(parents=True, exist_ok=True)
    G.write_csv(OUT / "comparacao.csv", cmp_rows)
    G.write_csv(OUT / "contexto.csv", ctx_rows)
    (OUT / "RELATORIO.md").write_text("\n".join(report(cmp_rows, ctx_rows, records, registry, note)) + "\n",
                                      encoding="utf-8")
    print(f"{len(records)} registros: {len(cmp_rows)} comparados, {len(ctx_rows)} de contexto · {note}")
    print(f"Wrote {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
