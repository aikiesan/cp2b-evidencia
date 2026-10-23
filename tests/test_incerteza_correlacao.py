"""Guards for scripts/build_incerteza_correlacao.py.

The script redraws the uncertainty model with groups of parameters moving
together. These tests fail if the inverse triangular stops matching its
range, if ρ = 0 stops giving the independent interval, if ρ = 1 with
everything together stops putting all parameters at the same quantile, or if
the script writes numbers without the snapshot.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _load("correlacao", ROOT / "scripts" / "build_incerteza_correlacao.py")
T = _load("t_incerteza", ROOT / "tests" / "test_incerteza_cp2b.py")


def model():
    return C.I.Model(T.ROWS, T.PARAMS)


def test_the_inverse_triangular_keeps_the_range_and_the_mean():
    u = np.linspace(0, 1, 200001)
    x = C.tri_ppf(u, 1.0, 2.0, 5.0)
    assert x[0] == pytest.approx(1.0) and x[-1] == pytest.approx(5.0)
    assert C.tri_ppf(np.array([0.25]), 1.0, 2.0, 5.0)[0] == pytest.approx(2.0)
    assert np.all(np.diff(x) >= 0) and x.mean() == pytest.approx(8.0 / 3, rel=1e-3)
    assert C.tri_ppf(np.array([0.3]), 2.0, 2.0, 2.0)[0] == 2.0
    assert C.phi(np.array([0.0]))[0] == pytest.approx(0.5)


def test_independent_draws_match_the_uncertainty_script():
    m = model()
    r0 = C.I.rank_rows(m.at(1)["mun"])[0]
    ind = C.run(m, lambda c, e: (c, e), 0.0, 4000, 1, r0)["n4"]
    ref = C.I.draw(m, 4000)["levels"]["n4"]
    for p in (0.05, 0.5, 0.95):
        assert np.quantile(ind, p) == pytest.approx(np.quantile(ref, p), rel=0.02)


def test_everything_together_sits_at_one_quantile():
    m = model()
    r0 = C.I.rank_rows(m.at(1)["mun"])[0]
    sim = C.run(m, lambda c, e: "tudo", 1.0, 4000, 2, r0)
    assert sim["groups"] == 1
    assert np.quantile(sim["n4"], 0.05) == pytest.approx(C.at_quantile(m, 0.05), rel=0.01)
    assert C.at_quantile(m, 0.0) == pytest.approx(float(m.snapshot["n4"][0].sum()), rel=1e-9)
    assert C.at_quantile(m, 1.0) == pytest.approx(float(m.snapshot["n4"][2].sum()), rel=1e-9)
    ind = C.run(m, lambda c, e: (c, e), 0.0, 4000, 2, r0)["n4"]
    assert np.quantile(sim["n4"], 0.95) - np.quantile(sim["n4"], 0.05) > np.quantile(ind, 0.95) - np.quantile(ind, 0.05)


def test_without_the_snapshot_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(C.I.B, "CP2B_SNAPSHOT", tmp_path / "none")
    monkeypatch.setattr(C, "OUT", tmp_path / "out")
    C.main()
    text = (tmp_path / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (tmp_path / "out" / "correlacao.csv").exists()
