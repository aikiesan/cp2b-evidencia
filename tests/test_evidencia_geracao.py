"""Guards for scripts/build_evidencia_geracao.py.

The livestock registry's units are free text, so the script maps each record to a
CP2b element by hand. These tests fail if a mapped number is no longer in the
record it quotes, if a mapping points to a substrate the loader does not know, or
if the dry-matter range and the verdicts stop meaning what the report says.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evidencia_geracao", ROOT / "scripts" / "build_evidencia_geracao.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
RECORDS = {r["record_id"]: r for r in G.E.read_registry(G.latest_registry())}
SUBS = G.E.B.loader_constant("SUBSTRATES")


@pytest.mark.parametrize("entry", G.MAP, ids=lambda m: f"{m[0]}-{m[1]}-{m[2]}")
def test_every_mapped_number_is_quoted_from_its_record(entry):
    code, el, rid, quote, lo, hi, factor, _ = entry
    assert rid in RECORDS
    text = f"{RECORDS[rid]['value']} {RECORDS[rid]['unit']}"
    assert quote in text
    assert G.E.num(lo) is not None and lo <= hi and factor > 0
    assert code in SUBS and SUBS[code][1] == "livestock" and el in G.ELEMENTS


def test_not_comparable_records_exist_and_name_a_cp2b_substrate():
    for rid, (code, why) in G.NOT_COMPARABLE.items():
        assert rid in RECORDS and code in SUBS and why
        assert rid not in {m[2] for m in G.MAP}


def test_dry_matter_range_is_the_product_of_g_and_st():
    got = G.cp2b_ranges({("X", "g"): (2.0, 3.0, 4.0), ("X", "ST"): (0.1, 0.2, 0.3)})
    assert got[("X", "g×ST")] == pytest.approx((0.2, 0.6, 1.2))


def test_verdicts():
    rng = (1.0, 2.0, 3.0)
    assert G.verdict(0.2, 0.5, rng) == "abaixo"
    assert G.verdict(3.5, 4.0, rng) == "acima"
    assert G.verdict(1.5, 2.5, rng) == "dentro"
    assert G.verdict(0.5, 1.5, rng) == "sobrepõe"
    assert G.verdict(1.0, 2.0, None) == ""


def test_broiler_litter_per_flock_gives_flocks_per_year_not_a_verdict():
    cp2b = G.cp2b_ranges({("AVES_CORTE", "g"): (0.035, 0.045, 0.06), ("AVES_CORTE", "ST"): (0.2, 0.25, 0.3)})
    rows = [r for r in G.compare(RECORDS, cp2b) if r["elemento"] == "g×ST/lote"]
    assert rows and all(r["situacao"] == "" and r["lotes_por_ano_implicitos"] for r in rows)
