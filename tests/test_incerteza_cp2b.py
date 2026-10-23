"""Guards for scripts/build_incerteza_cp2b.py.

The script samples each CP2b parameter inside its own range and recomputes the
cascade municipality by municipality. These tests fail if the recomputation
stops matching the sensitivity script's, if a parameter enters the wrong stage
or is not divided by its median, if a fixed seed stops giving the same draws,
if the variance shares stop adding up for a single parameter, or if the script
writes numbers without the snapshot.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("incerteza", ROOT / "scripts" / "build_incerteza_cp2b.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def _row(code, n1, fc, fco, u, fsfl, ibge, scen="med"):
    n2 = n1 * fc
    n3a = n2 * fco
    n3 = max(n3a - u, 0.0)
    return {"ibge": ibge, "codigo": code, "cenario": scen, "n1": n1, "n2": n2, "n3a": n3a, "u": u, "n3": n3,
            "n4": n3 * fsfl, "fsfl": fsfl}


ROWS = [_row("A", 100.0, 0.5, 0.8, 10.0, 0.5, "1"), _row("B", 50.0, 1.0, 1.0, 0.0, 0.9, "1"),
        _row("A", 300.0, 0.5, 0.8, 0.0, 0.5, "2"), _row("B", 10.0, 1.0, 1.0, 0.0, 0.9, "3")]
PARAMS = {("A", "BMP"): (200.0, 250.0, 300.0), ("A", "FC"): (0.4, 0.5, 0.6), ("A", "FS"): (0.9, 0.95, 1.0),
          ("B", "FCo"): (0.5, 1.0, 1.0)}


def test_no_multiplier_matches_the_sensitivity_recomputation():
    state, by_sub, by_mun = M.run(M.med_rows(ROWS), {})
    want = M.S.recompute(ROWS, {})
    for lvl in M.LEVEL_KEYS:
        assert state[lvl] == pytest.approx(want[lvl])
    assert sum(by_sub.values()) == pytest.approx(want["n4"]) == pytest.approx(sum(by_mun.values()))
    assert by_mun["2"] == pytest.approx(300 * 0.5 * 0.8 * 0.5)


def test_parameters_enter_their_stage_over_the_median():
    m = M.stage_mult(PARAMS, {("A", "BMP"): 300.0, ("A", "FC"): 0.6, ("A", "FS"): 0.9, ("B", "FCo"): 0.5})
    assert m["A"] == pytest.approx((1.2, 1.2, 1.0, 0.9 / 0.95))
    assert m["B"] == pytest.approx((1.0, 1.0, 0.5, 1.0))
    assert set(M.STAGE.values()) == {"n1", "n2", "n3a", "n4"}


def test_the_model_check_passes_when_min_and_max_are_the_products_of_the_parameter_ends():
    rows = list(ROWS)
    for i, scen in ((0, "min"), (2, "max")):
        k = {c: M.stage_mult(PARAMS, {key: v[i] for key, v in PARAMS.items() if key[0] == c})[c] for c in "AB"}
        for r in ROWS:
            m1, m2, m3, m4 = k[r["codigo"]]
            n1 = r["n1"] * m1
            rows.append(_row(r["codigo"], n1, r["n2"] / r["n1"] * m2, r["n3a"] / r["n2"] * m3, r["u"],
                             r["fsfl"] * m4, r["ibge"], scen))
    out = M.model_check(rows, M.med_rows(rows), PARAMS)
    assert out and all(r["razao"] == pytest.approx(1.0) for r in out if r["n4_snapshot"])
    steps = M.stage_check(rows, PARAMS)
    assert {r["etapa"] for r in steps} == {"N1", "FC", "FCo", "U", "FS × FL"}
    ratios = [(r["razao_snapshot"], r["razao_modelo"]) for r in steps if r["razao_snapshot"] is not None]
    assert ratios and all(a == pytest.approx(b) for a, b in ratios)


def test_a_fixed_seed_gives_the_same_draws_and_fixed_parameters_give_no_spread():
    med = M.med_rows(ROWS)
    a, b = M.simulate(med, PARAMS, 50), M.simulate(med, PARAMS, 50)
    assert a["levels"]["n4"] == b["levels"]["n4"]
    fixed = M.simulate(med, {k: (v[1],) * 3 for k, v in PARAMS.items()}, 20)
    base = M.run(med, {})[0]["n4"]
    assert all(x == pytest.approx(base) for x in fixed["levels"]["n4"])
    assert fixed["spearman"] == [pytest.approx(1.0)] * 20 and fixed["top"]["2"] == 20


def test_one_parameter_explains_all_of_the_variance():
    med = [("1", "A", 100.0, 50.0, 40.0, 0.0, 0.5)]
    params = {("A", "BMP"): (200.0, 250.0, 350.0)}
    sim = M.simulate(med, params, 4000)
    (row,) = M.tornado(med, params, sim)
    assert row["n4_no_min"] == pytest.approx(16.0) and row["n4_no_max"] == pytest.approx(28.0)
    assert row["parcela_variancia"] == pytest.approx(1.0, rel=0.08)


def test_ranks_and_quantiles():
    assert M.ranked({"a": 1.0, "b": 3.0, "c": 3.0}) == {"b": 1, "c": 2, "a": 3}
    assert M.spearman_rank({"a": 1, "b": 2, "c": 3}, {"a": 3, "b": 2, "c": 1}) == pytest.approx(-1.0)
    assert M.quantile([1, 2, 3, 4, 5], 0.5) == 3 and M.quantile([0, 10], 0.05) == pytest.approx(0.5)


def test_without_the_snapshot_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(M.B, "CP2B_SNAPSHOT", tmp_path / "none")
    monkeypatch.setattr(M, "OUT", tmp_path / "out")
    M.main()
    text = (tmp_path / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (tmp_path / "out" / "incerteza.csv").exists()


def test_municipality_names_fall_back_to_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "NAMES", tmp_path / "x.csv")
    monkeypatch.setattr(M, "REGIONS", tmp_path / "y.csv")
    assert M.municipalities()["3500105"] == ("", "")
