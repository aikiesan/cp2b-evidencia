"""Guards for scripts/build_incerteza_correlacao.py.

The script redraws the uncertainty model with groups of parameters moving
together. These tests fail if the inverse triangular stops matching its
range, if ρ = 0 stops giving the independent interval, if ρ = 1 with
everything together stops putting all parameters at the same quantile, if the
groups by source stop following the references cited, or if the script writes
numbers without the snapshot.
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


YML = {"A": {"bmp": {"min": 200.0, "medio": 250.0, "max": 300.0, "refs": [{"id": "paper2016", "value": "x"}]},
             "ts": {"min": 10.0, "medio": 20.0, "max": 30.0, "refs": ["paper2016"]},
             "fde": {"components": {"fc": {"min": 0.4, "medio": 0.5, "max": 0.6},
                                    "fco": {"min": 0.1, "medio": 0.2, "max": 0.3}},
                     "refs": [{"id": "bale2005", "value": "FC=0.5: baling"}, {"id": "soil2017", "value": "FCo=0.2"}]}},
       "B": {"bmp": {"min": 1.0, "medio": 2.0, "max": 3.0, "refs": ["paper2016", "other2020"]}}}


def test_sources_follow_the_citation():
    assert C._norm("Atlas SP 2020 p.65 (40/50%)") == "atlas sp 2020" == C._norm(" Atlas SP 2020 p.66")
    assert C.source_info("Atlas SP 2020 p.65 (40/50%); Tenelli et al. 2021 (35%)", "P", "FC", (0, 0, 0), {}) == \
        (("atlas sp 2020", "tenelli et al. 2021"), False, "")
    assert C.source_info("cp2b", "A", "g", (1, 2, 3), {}) == ((), True, "")
    assert C.source_info("override cp2b: ", "A", "ST", (1, 1, 1), {}) == ((), True, "")
    assert C.source_info("decisão CP2b 23/09; SIGA/ANEEL 215 UTEs (6 GW)", "A", "FCo", (0, 0, 0), {}) == \
        (("siga/aneel 215 utes",), True, "")
    assert C.source_info("feedstocks.yaml", "A", "BMP", (200.0, 250.0, 300.0), YML)[0] == ("paper2016",)
    assert C.source_info("feedstocks.yaml", "A", "ST", (0.1, 0.2, 0.3), YML)[0] == ("paper2016",)
    assert C.source_info("feedstocks.yaml", "A", "FC", (0.4, 0.5, 0.6), YML)[0] == ("bale2005",)
    refs, _, note = C.source_info("feedstocks.yaml", "A", "BMP", (100.0, 250.0, 300.0), YML)
    assert refs == () and "diferente" in note
    assert "não tem refs" in C.source_info("feedstocks.yaml", "B", "SV", (0, 0, 0), YML)[2]
    assert C.source_info("espacial (x), por município: fl_espacial/a.csv", "A", "FL", (0, 0, 0), {})[0] == \
        ("FL espacial do CP2b (fl_v5)",)
    assert C.source_info("espacial: fl_espacial/a.csv; valores mostrados = feedstocks.yaml", "A", "FL", (0, 0, 0),
                         YML) == (("FL espacial do CP2b (fl_v5)",), False, "")


def test_groups_join_what_cites_the_same_reference():
    info = {("A", "BMP"): (("paper2016",), False, ""), ("B", "BMP"): (("other2020", "paper2016"), False, ""),
            ("A", "ST"): (("paper2016",), False, ""), ("A", "g"): ((), True, ""), ("B", "g"): ((), True, ""),
            ("C", "BMP"): ((), False, "")}
    el = C.source_groups(info, "elemento")
    assert el[("A", "BMP")] == el[("B", "BMP")] != el[("A", "ST")]
    assert len({el[k] for k in info}) == 5
    ampla = C.source_groups(info, "ampla")
    assert ampla[("A", "BMP")] == ampla[("B", "BMP")] == ampla[("A", "ST")] != ampla[("A", "g")]
    eq = C.source_groups(info, "equipe")
    assert eq[("A", "g")] == eq[("B", "g")] and el[("A", "g")] != el[("B", "g")]
    assert eq[("C", "BMP")] != eq[("A", "BMP")]


def test_the_source_structures_run_and_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "INC_CSV", tmp_path / "none.csv")
    fontes = {("A", "BMP"): "Atlas SP 2020 p.3", ("P", "g"): "Atlas SP 2020 p.9 (tabela)", ("A", "FC"): "cp2b",
              ("P", "FC"): "cp2b", ("A", "FS"): "cp2b"}
    out, chk, src, lines = C.build(T.ROWS, T.PARAMS, 400, fontes, {})
    keys = [(r["estrutura"], r["rho"]) for r in out]
    assert ("fonte", 1.0) in keys and ("fonte_ampla", 1.0) in keys and ("fonte_equipe", 1.0) in keys
    by = {(r["estrutura"], r["rho"]): r for r in out}
    assert by[("fonte", 1.0)]["grupos"] > by[("fonte_ampla", 1.0)]["grupos"]
    assert by[("fonte_equipe", 1.0)]["grupos"] < by[("fonte", 1.0)]["grupos"]
    assert {(r["codigo"], r["elemento"]) for r in src} == set(C.I.Model(T.ROWS, T.PARAMS).params)
    text = "\n".join(lines)
    assert "## 3. Os grupos por fonte" in text and "Valores da própria equipe" in text
    _, _, src, lines = C.build(T.ROWS, T.PARAMS, 200, {}, {}, "x.csv não tem a coluna fonte")
    assert not src and "não rodaram: x.csv não tem a coluna fonte" in "\n".join(lines)
