"""Guards for scripts/build_incerteza_cp2b.py.

The script samples each CP2b parameter inside its own range and recomputes the
cascade municipality by municipality, with the spatial FL following supply, U
following N3a, and what the snapshot varies outside the parameter file as a
residual. These tests build a snapshot the way the CP2b does and fail if the
model stops reproducing its min, med and max row by row, if a residual or a
med-zero substrate is missed, if a parameter enters the wrong stage, if a fixed
seed stops giving the same draws, if the variance share of a lone parameter
stops adding up, or if the script writes numbers without the snapshot.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("incerteza", ROOT / "scripts" / "build_incerteza_cp2b.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

PARAMS = {("A", "BMP"): (200.0, 250.0, 300.0), ("A", "FC"): (0.4, 0.5, 0.6), ("A", "FS"): (0.9, 0.95, 1.0),
          ("P", "g"): (1.0, 2.0, 3.0), ("P", "FC"): (0.0, 0.0, 0.2)}
BASE = {"A": 1.0, "P": 100.0}
BASE_FACTOR = (0.9, 1.0, 1.1)              # A's base varies outside the parameter file
SIZE = {"1": 4.0, "2": 1.0, "3": 0.2}       # municipality size
EXIST = {"1": 30.0, "2": 0.0, "3": 5.0}     # existing use of A


def spatial(n3):
    return min(1.0, n3 / 200.0)


def snapshot_rows():
    rows = []
    for ibge, size in SIZE.items():
        for s, scen in enumerate(M.SCEN):
            bmp, fc, fs = (PARAMS[("A", e)][s] for e in ("BMP", "FC", "FS"))
            n1 = size * BASE["A"] * bmp * BASE_FACTOR[s]
            n2 = n1 * fc
            n3a = n2 * 0.8
            u = min(EXIST[ibge], n3a)
            n3 = n3a - u
            fsfl = fs * spatial(n3)
            rows.append({"ibge": ibge, "codigo": "A", "cenario": scen, "n1": n1, "n2": n2, "n3a": n3a, "u": u,
                         "n3": n3, "n4": n3 * fsfl, "fsfl": fsfl})
            g, fcp = PARAMS[("P", "g")][s], PARAMS[("P", "FC")][s]
            n1 = size * BASE["P"] * g
            n3 = n1 * fcp
            rows.append({"ibge": ibge, "codigo": "P", "cenario": scen, "n1": n1, "n2": n3, "n3a": n3, "u": 0.0,
                         "n3": n3, "n4": n3 * 0.5, "fsfl": 0.5})
    return rows


ROWS = snapshot_rows()


def _snap(scen):
    return {(r["ibge"], r["codigo"]): r["n4"] for r in ROWS if r["cenario"] == scen}


def test_min_med_and_max_are_reproduced_row_by_row():
    model = M.Model(ROWS, PARAMS)
    keys = [(m, c) for m in model.munis for c in model.codes]
    order = {(model.munis[mu], model.codes[su]): j for j, (mu, su) in enumerate(zip(model.mun, model.sub))}
    for i, scen in enumerate(M.SCEN):
        got = model.at(i)["rows"][0]
        want = _snap(scen)
        for key in keys:
            assert got[order[key]] == pytest.approx(want[key], rel=1e-9, abs=1e-9), (scen, key)
    rows, checks = M.check_model(model)
    assert all(ok in (True, "vale") for _, ok, _ in checks)


def test_the_base_residual_and_the_med_zero_substrate_are_found():
    model = M.Model(ROWS, PARAMS)
    assert set(model.residuals) == {("A", M.RESIDUAL["n1"])}
    assert model.residual_range(("A", M.RESIDUAL["n1"])) == pytest.approx(BASE_FACTOR)
    assert model.ref[model.codes.index("P")] == 2 and model.ref[model.codes.index("A")] == 1
    assert model.at(1)["sub"][0][model.codes.index("P")] == 0.0
    assert not model.dropped


def test_parameters_and_extra_multipliers_enter_their_stage():
    model = M.Model(ROWS, PARAMS)
    med = model.evaluate()
    up = model.evaluate({("A", "BMP"): np.array([275.0])})
    a = model.codes.index("A")
    assert up["state"]["n1"][0] - med["state"]["n1"][0] == pytest.approx(0.1 * sum(SIZE.values()) * 250.0)
    fc2 = model.evaluate(extra={("A", "n2"): 2.0})
    assert fc2["state"]["n1"][0] == pytest.approx(med["state"]["n1"][0])
    assert fc2["state"]["n2"][0] == pytest.approx(med["state"]["n2"][0] + sum(SIZE.values()) * 125.0)
    fs = model.evaluate({("A", "FS"): np.array([0.9])})
    assert fs["sub"][0][a] == pytest.approx(med["sub"][0][a] * 0.9 / 0.95)
    assert set(M.STAGE.values()) == set(M.STAGES)


def test_spatial_and_existing_use_follow_supply_between_the_points():
    model = M.Model(ROWS, PARAMS)
    lo, mid, hi = (model.at(i)["state"]["n4"][0] for i in range(3))
    steps = model.evaluate({("A", "BMP"): np.linspace(200.0, 300.0, 11)})["state"]["n4"]
    assert np.all(np.diff(steps) > 0)
    xs, ys = np.array([[0.0], [1.0], [2.0]]), np.array([[0.0], [10.0], [30.0]])
    assert M._interp(np.array([-1.0, 0.5, 1.5, 9.0]), xs, ys).ravel() == pytest.approx([0.0, 5.0, 20.0, 30.0])
    assert lo < mid < hi


def test_a_fixed_seed_gives_the_same_draws():
    model = M.Model(ROWS, PARAMS)
    a, b = M.draw(model, 300), M.draw(model, 300)
    assert np.array_equal(a["levels"]["n4"], b["levels"]["n4"]) and a["ranks"].shape == (300, 3)
    assert np.all(a["levels"]["n4"] > 0) and a["spearman"].shape == (300,)


def test_one_parameter_explains_all_of_the_variance():
    rows = []
    for s, scen in enumerate(M.SCEN):
        bmp = (200.0, 250.0, 350.0)[s]
        rows.append({"ibge": "1", "codigo": "A", "cenario": scen, "n1": bmp, "n2": bmp / 2, "n3a": bmp / 2,
                     "u": 0.0, "n3": bmp / 2, "n4": bmp / 4, "fsfl": 0.5})
    model = M.Model(rows, {("A", "BMP"): (200.0, 250.0, 350.0)})
    sim = M.draw(model, 4000)
    (row,) = M.tornado(model, float(np.var(sim["levels"]["n4"])))
    assert row["n4_no_min"] == pytest.approx(50.0) and row["n4_no_max"] == pytest.approx(87.5)
    assert row["parcela_variancia"] == pytest.approx(1.0, rel=0.08)


def test_ranks_break_ties_by_column():
    assert M.rank_rows(np.array([1.0, 3.0, 3.0])).tolist() == [[3, 1, 2]]


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
