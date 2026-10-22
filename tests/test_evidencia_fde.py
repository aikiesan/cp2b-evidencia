"""Guards for scripts/build_evidencia_fde.py.

The registry labels a number FC, FCo, FS or FL by what it resembles, so the script
reads each record by hand. These tests fail if a mapped record leaves the registry
copy, points to a substrate its stream cannot speak to, or if a record that is not
the CP2b definition (days of supply / 365, a distance in km) gets placed against a
CP2b range.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evidencia_fde", ROOT / "scripts" / "build_evidencia_fde.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
RECORDS = {r["record_id"]: r for r in F.E.read_registry(F.latest_registry())}
SUBS = F.E.B.loader_constant("SUBSTRATES")


def test_registry_has_the_columns_the_reading_uses():
    first = next(iter(RECORDS.values()))
    for col in ("record_id", "feedstock_code", "factor", "value", "value_min", "value_max", "unit",
                "definition_in_source", "tier", "doi", "url", "source_key", "region"):
        assert col in first, col


def test_every_reading_names_a_record_and_a_substrate_of_its_stream():
    for rid, code, factor, what in F.MAP:
        assert rid in RECORDS and factor in F.FACTORS + (F.FC_FCO,) and what
        assert code in SUBS and code in F.STREAMS[RECORDS[rid]["feedstock_code"]]
        lo, _, hi = F.bounds(RECORDS[rid])
        assert lo is not None and lo <= hi
    for rid, codes, factor, why in F.CONTEXT:
        assert rid in RECORDS and why and (factor is None or factor in F.FACTORS)
        assert all(c in SUBS and c in F.STREAMS[RECORDS[rid]["feedstock_code"]] for c in codes)
    for codes in F.STREAMS.values():
        assert all(c in SUBS for c in codes)


def test_no_reading_is_listed_twice_for_the_same_substrate():
    pairs = [(rid, code) for rid, code, _, _ in F.MAP]
    pairs += [(rid, code) for rid, codes, _, _ in F.CONTEXT for code in codes]
    assert len(pairs) == len(set(pairs))


def test_seasonal_and_distance_records_are_never_compared():
    for rid, _, factor, _ in F.MAP:
        unit = RECORDS[rid]["unit"]
        assert factor != "FL" and "km" not in unit
        assert "of year" not in unit, f"{rid}: days of supply / 365 is not the CP2b FS (DEC-013)"


def test_bounds_fall_back_to_the_central_value():
    assert F.bounds({"value": "0.9", "value_min": "", "value_max": ""}) == (0.9, 0.9, 0.9)
    assert F.bounds({"value": "", "value_min": "0.52", "value_max": "3.7"}) == (0.52, None, 3.7)


def test_verdict_only_with_a_cp2b_range():
    rows = F.compare(RECORDS, {})
    assert rows and all(r["situacao"] == "" for r in rows)
    rid, code, factor, _ = F.MAP[0]
    lo, _, hi = F.bounds(RECORDS[rid])
    rows = F.compare(RECORDS, {(code, factor): (hi + 1, hi + 2, hi + 3)})
    assert rows[0]["situacao"] == "abaixo"
    ctx = F.context(RECORDS, {(code, factor): (0.1, 0.2, 0.3)})
    assert all("situacao" not in r for r in ctx)


def test_crop_residue_removal_is_compared_with_fc_times_fco():
    got = F.with_fc_fco({("X", "FC"): (0.35, 0.4, 0.5), ("X", "FCo"): (0.8, 0.9, 0.95), ("Y", "FC"): (1, 1, 1)})
    assert got[("X", F.FC_FCO)] == pytest.approx((0.28, 0.36, 0.475))
    assert ("Y", F.FC_FCO) not in got
