"""Guards for scripts/build_incerteza_rede.py.

The script gives each parameter draw of build_incerteza_cp2b.py one perturbed run of the fl_v5 allocation and
moves each row's spatial FL by what that run changed. These tests use the synthetic snapshot of
test_incerteza_cp2b.py and fail if the draws without the network stop being those of build_incerteza_cp2b.py, if
a run's FL change does not land on the right row with the right size, if the FL leaves [0, 1], if a snapshot that
does not use the fl_v5 FL passes the check, or if the script writes numbers without its inputs.
"""

import importlib.util
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load("incerteza_rede", ROOT / "scripts" / "build_incerteza_rede.py")
T = _load("test_incerteza_cp2b_rows", ROOT / "tests" / "test_incerteza_cp2b.py")
ROWS, PARAMS = T.ROWS, T.PARAMS
N3_MED = {r["ibge"]: r["n3"] for r in ROWS if r["cenario"] == "med" and r["codigo"] == "A"}
FL_A = {m: T.spatial(n3) for m, n3 in N3_MED.items()}          # FL B of A: what the snapshot's FS × FL holds
RUN_FL = (0.3, 0.7, 0.3, 0.7)                                  # municipality 2, substrate A (FL 0.5 in v5.1)


def fl_rows(fl_a=None):
    fl_a = fl_a or FL_A
    return [{"ibge": m, "codigo": c, "cenario": "med", "FL_codig_alocado": f}
            for m in T.SIZE for c, f in (("A", fl_a[m]), ("P", 1.0))]


def run_rows(designs=("mun10", "mun30", "sub20_mun20")):
    return [{"desenho": d, "ibge": "2", "codigo": "A", "FL_v51": FL_A["2"],
             **{f"r{k + 1:02d}": f for k, f in enumerate(RUN_FL)}} for d in designs]


def data(**kw):
    return {R.FLV5: fl_rows(kw.get("fl_a")), R.RUNS: run_rows(kw.get("designs", ("mun10", "mun30", "sub20_mun20")))}


NAMES = defaultdict(lambda: ("", ""), {"1": ("Um", "Norte"), "2": ("Dois", "Norte"), "3": ("Três", "Sul")})


def test_without_the_network_the_draws_are_those_of_the_uncertainty_script():
    model = R.RedeModel(ROWS, PARAMS)
    mine = R.draw(model, 600)
    theirs = R.I.draw(R.I.Model(ROWS, PARAMS), 600)
    assert np.array_equal(mine["munis"], theirs["munis"])
    assert np.array_equal(mine["state"], theirs["levels"]["n4"])


def test_a_run_moves_its_own_row_by_its_fl_change():
    model = R.RedeModel(ROWS, PARAMS)
    runs, n = R.runs_table(run_rows())
    lk = R.link(model, fl_rows(), runs, n)
    assert n == 4 and all(c["resultado"] for c in lk["conferencia"]), lk["conferencia"]
    assert lk["rho"]["A"] == pytest.approx(0.95) and "P" not in lk["rho"]      # P has no N3 in med
    model.shift, model.cap = lk["shifts"]["mun10"][[1]], lk["cap"]
    moved = model.at(1)["rows"][0]
    model.shift = model.cap = None
    base = model.at(1)["rows"][0]
    j = next(i for i, (m, s) in enumerate(zip(model.mun, model.sub))
             if (model.munis[m], model.codes[s]) == ("2", "A"))
    assert moved[j] == pytest.approx(N3_MED["2"] * 0.95 * 0.7)
    assert np.allclose(np.delete(moved, j), np.delete(base, j), rtol=0, atol=0)


def test_the_fl_stays_between_zero_and_one():
    model = R.RedeModel(ROWS, PARAMS)
    lk = R.link(model, fl_rows(), R.runs_table(run_rows())[0], 4)
    j = np.flatnonzero(np.abs(lk["shifts"]["mun10"]).sum(0) > 0)[0]
    n3 = np.array([[N3_MED["2"]] * len(model.sub)])
    model.cap = lk["cap"]
    model.shift = np.full((1, len(model.sub)), -5.0)
    assert (model.spatial(n3) >= 0).all() and model.spatial(n3)[0, j] == 0
    model.shift = np.full((1, len(model.sub)), 5.0)
    assert model.spatial(n3)[0, j] == pytest.approx(1.0)      # FL 1: ρ / (FS × FL of the file) = 0.95 / 0.95
    model.shift = model.cap = None


def test_a_snapshot_that_does_not_use_the_fl_v5_fl_fails_the_check():
    model = R.RedeModel(ROWS, PARAMS)
    lk = R.link(model, fl_rows({**FL_A, "1": FL_A["1"] / 2}), R.runs_table(run_rows())[0], 4)
    c = lk["conferencia"][0]
    assert not c["resultado"] and "não: A" in c["detalhe"]


def test_a_missing_design_fails_the_check():
    model = R.RedeModel(ROWS, PARAMS)
    lk = R.link(model, fl_rows(), R.runs_table(run_rows(("mun10",)))[0], 4)
    assert not next(c for c in lk["conferencia"] if c["checagem"].startswith("as rodadas"))["resultado"]


def test_the_network_widens_only_the_municipality_it_touches_and_is_reported():
    res = R.build(ROWS, PARAMS, data(), 400, NAMES)
    by = {r["ibge"]: r for r in res["ranking"]}
    assert by["2"]["razao_amplitude_mun30"] > 1.05
    for m in ("1", "3"):
        assert by[m]["razao_amplitude_mun30"] == pytest.approx(1.0)
    assert all(c["resultado"] for c in res["conferencia"] if c["checagem"].startswith(("o FS", "FL_v51", "toda")))
    s = res["resumo"][0]
    assert s["municipios_com_n4"] == 3 and s["rodadas"] == 4 and s["linhas_com_rede"] == 1
    assert {g["rgint"] for g in res["regioes"]} == {"Norte", "Sul"}
    text = "\n".join(R.report(res, ["teste"], ""))
    assert "## 2. Municípios" in text and "| 10 % por município |" in text and "| Dois | Norte |" in text


def test_without_its_inputs_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "OUT", tmp_path)
    monkeypatch.setattr(R.S, "read_levels", lambda: (None, "sem o snapshot CP2b v5.1"))
    R.main()
    assert "Não rodou: sem o snapshot CP2b v5.1" in (tmp_path / "RELATORIO.md").read_text(encoding="utf-8")
    monkeypatch.setattr(R.S, "read_levels", lambda: (ROWS, "teste"))
    monkeypatch.setattr(R.I, "parameters", lambda: (PARAMS, [], "teste"))
    monkeypatch.setattr(R.F, "load", lambda folder: ({R.FLV5: fl_rows()}, [], ""))
    R.main()
    text = (tmp_path / "RELATORIO.md").read_text(encoding="utf-8")
    assert f"Não rodou: falta {R.RUNS}" in text and not (tmp_path / "ranking_rede.csv").exists()
