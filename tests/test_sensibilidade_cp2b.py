"""Guards for scripts/build_sensibilidade_cp2b.py.

The script recomputes the CP2b cascade municipality by municipality with one
parameter swapped. These tests fail if the recomputation stops reproducing the
snapshot when nothing is swapped, if a swap enters the wrong stage, if existing
use U stops being subtracted as an absolute amount, if a scenario points to a
record the evidence libraries no longer have, or if the two dairy readings are
combined in one scenario.
"""

import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sensibilidade", ROOT / "scripts" / "build_sensibilidade_cp2b.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
SUBS = M.B.loader_constant("SUBSTRATES")


def _row(code, n1, fc, fco, u, fsfl, ibge="3500105", scen="med"):
    n2 = n1 * fc
    n3a = n2 * fco
    n3 = max(n3a - u, 0.0)
    return {"ibge": ibge, "codigo": code, "cenario": scen, "n1": n1, "n2": n2, "n3a": n3a, "u": u, "n3": n3,
            "n4": n3 * fsfl, "fsfl": fsfl}


ROWS = [_row("A", 100.0, 0.5, 0.8, 10.0, 0.5), _row("B", 50.0, 1.0, 1.0, 0.0, 0.9),
        _row("A", 999.0, 1.0, 1.0, 0.0, 1.0, scen="max")]


def test_nothing_swapped_reproduces_the_snapshot():
    got = M.recompute(ROWS, {})
    want = M.cascade(ROWS)
    for lvl in M.LEVELS:
        assert got[lvl] == pytest.approx(want["A"][lvl] + want["B"][lvl])


def test_each_element_enters_its_stage_and_u_stays_absolute():
    base = M.recompute(ROWS, {})
    fc = M.recompute(ROWS, {("A", "n2"): 2.0})
    assert fc["n1"] == base["n1"] and fc["n2"] == pytest.approx(base["n2"] + 50)
    assert fc["n3"] == pytest.approx(base["n3"] + 40)          # N3a 40 -> 80, U = 10 stays
    fs = M.recompute(ROWS, {("A", "n4"): 0.5})
    assert fs["n3"] == base["n3"] and fs["n4"] == pytest.approx(base["n4"] - 0.5 * 30 * 0.5)
    low = M.recompute(ROWS, {("A", "n1"): 0.1})                 # N3a 4 < U 10: N3 of A is zero
    assert low["n3"] == pytest.approx(50.0) and low["u"] == base["u"]
    assert set(M.STAGE.values()) == {"n1", "n2", "n3a", "n4"}


def test_checks_catch_a_broken_identity(monkeypatch):
    monkeypatch.setattr(M.B, "loader_constant", lambda name: {} if name == "EXPECTED_STATE_TOTALS" else None)
    assert all(ok for _, ok, _ in M.checks(ROWS))
    bad = [dict(ROWS[0], n4=ROWS[0]["n4"] + 1)] + ROWS[1:]
    assert not all(ok for _, ok, _ in M.checks(bad))


def test_multipliers_divide_by_the_cp2b_median_and_multiply_across_elements():
    lib = {"params": {("A", "FC"): (0.4, 0.5, 0.6), ("A", "SV"): (0.7, 0.8, 0.9)}, "ger": {}, "fde": {}, "bmp": {}}
    got = M.multipliers(lib, ("A",), (("valor", "FC", (0.5, 1.0, 1.0)), ("valor", "SV", (0.8, 0.8, 0.8))))
    assert got[("A", "n2")] == pytest.approx((1.0, 2.0, 2.0)) and got[("A", "n1")] == pytest.approx((1.0,) * 3)
    assert M.multipliers(lib, ("A",), (("valor", "FCo", (1, 1, 1)),)) is None


def test_every_scenario_term_resolves_from_the_evidence_libraries():
    lib = M.literature()
    for key, kind, label, codes, terms, note in M.SCENARIOS:
        assert kind in ("literatura", "hipótese", "definição") and label and note
        assert codes and all(c in SUBS for c in codes)
        for code in codes:
            for term in terms:
                assert term[1] in M.STAGE, key
                assert M.term_value(lib, code, term) is not None, (key, code, term)


def test_combined_scenarios_never_mix_the_two_dairy_readings():
    keys = {s[0]: s[1] for s in M.SCENARIOS}
    for _, _, parts in M.COMBINED:
        assert all(keys[p] in ("literatura", "hipótese") for p in parts)
        assert not {"leite_g", "leite_fc1"} <= set(parts)


def test_without_the_snapshot_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(M.B, "CP2B_SNAPSHOT", tmp_path / "none")
    monkeypatch.setattr(M, "OUT", tmp_path / "out")
    M.main()
    text = (tmp_path / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (tmp_path / "out" / "sensibilidade.csv").exists()


def test_levels_are_read_only_with_the_loader_checksum(tmp_path, monkeypatch):
    path = tmp_path / M.B.loader_constant("FILES")["levels"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ibge_code", "substrate", "scenario", *M.COLUMNS])
        w.writerow(["3500105.0", "A", "med", 1, 1, 1, 0, 1, 1])
    monkeypatch.setattr(M.B, "CP2B_SNAPSHOT", tmp_path)
    rows, why = M.read_levels()
    assert rows is None and "recusado" in why
