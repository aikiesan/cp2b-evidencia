"""Guards for scripts/build_v52.py.

The script runs the CP2b model with the v5.1 parameters swapped for the ones
proposed in v52/mudancas.csv. These tests reuse the synthetic snapshot of the
uncertainty tests and fail if a malformed or stale change gets applied, if a
change stops entering the model at its v5.2 value, if v5.1 stops reproducing
the snapshot and its own draws, if a rejected change counts, or if the script
writes numbers without the snapshot.
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


V = _load("v52", ROOT / "scripts" / "build_v52.py")
T = _load("incerteza_fixture", ROOT / "tests" / "test_incerteza_cp2b.py")
I = V.I  # noqa: E741
HEADER = "id,status,codigo,elemento,v51_min,v51_med,v51_max,min,med,max,registros,tier,justificativa,decisao\n"
BMP = "C1,candidata,A,BMP,200,250,300,220,275,330,R1,B,mais alto,\n"


def write(tmp_path, *lines):
    path = tmp_path / "mudancas.csv"
    path.write_text(HEADER + "".join(lines), encoding="utf-8")
    return path


def names():
    return defaultdict(lambda: ("", ""))


def run(tmp_path, *lines, n=200):
    changes, problems = V.read_changes(write(tmp_path, *lines))
    return V.build(T.ROWS, T.PARAMS, changes, problems, n, names())


def mine(res):
    return {name: ok for name, ok, _ in res["checks"][-2:]}


def test_malformed_lines_are_reported_and_left_out(tmp_path):
    changes, problems = V.read_changes(write(
        tmp_path, BMP,
        "C2,talvez,A,FC,0.4,0.5,0.6,0.4,0.5,0.6,,,,\n",
        "C3,candidata,A,U,1,1,1,1,1,1,,,,\n",
        "C4,candidata,A,FS,0.9,0.95,1.0,0.9,1.1,1.0,,,,\n",
        "C5,candidata,A,FC,0.4,0.5,0.6,0.4,,0.6,,,,\n"))
    assert [c["id"] for c in changes] == ["C1"]
    assert len(problems) == 4 and any("C4" in p and "ordem" in p for p in problems)
    changes, problems = V.read_changes(write(tmp_path, BMP, BMP.replace("C1", "C9")))
    assert changes == [] and "duas mudanças" in problems[0]
    changes, problems = V.read_changes(write(tmp_path, BMP, BMP.replace("C1", "C9").replace("candidata", "rejeitada")))
    assert [c["id"] for c in changes] == ["C1", "C9"] and not problems


def test_a_change_enters_at_its_v52_value(tmp_path):
    res = run(tmp_path, BMP)
    model = I.Model(T.ROWS, T.PARAMS)
    imp = {r["conjunto"]: r for r in res["impact"]}
    want = model.evaluate({("A", "BMP"): np.array([275.0])})["state"]["n4"][0]
    assert imp["C1"]["n4"] == pytest.approx(want)
    lo = model.evaluate(V.values_at(model, [], 0) | {("A", "BMP"): np.array([220.0])})["state"]["n4"][0]
    assert imp["C1"]["n4_min"] == pytest.approx(lo)
    assert imp["C1"]["n4"] > imp["v5.1"]["n4"]
    assert all(mine(res).values())
    assert [s["codigo"] for s in res["subs"]] and res["munis"][0]["rank_v52"] == 1


def test_v51_reproduces_the_snapshot_and_its_draws(tmp_path):
    res = run(tmp_path, BMP)
    imp = {r["conjunto"]: r for r in res["impact"]}
    for i, key in enumerate(("n4_min", "n4", "n4_max")):
        assert imp["v5.1"][key] == pytest.approx(sum(r["n4"] for r in T.ROWS if r["cenario"] == I.SCEN[i]))
    lv = I.draw(I.Model(T.ROWS, T.PARAMS), 200)["levels"]["n4"]
    assert imp["v5.1"]["n4_p5"] == pytest.approx(I.q(lv, .05))
    assert imp["v5.1"]["spearman"] == pytest.approx(1.0) and imp["v5.1"]["top50_mantidos"] == 3


def test_a_stale_v51_range_is_not_applied(tmp_path):
    res = run(tmp_path, BMP.replace("200,250,300", "200,240,300"))
    assert res["applied"] == [] and not mine(res)[list(mine(res))[-1]]
    assert [r["conjunto"] for r in res["impact"]] == ["v5.1"]


def test_rejected_changes_do_not_count_and_sets_are_built(tmp_path):
    fs = "C2,aceita,A,FS,0.9,0.95,1.0,0.8,0.85,0.9,R2,A,menos,DEC-099\n"
    res = run(tmp_path, BMP, fs, "C3,rejeitada,A,FC,0.4,0.5,0.6,0.1,0.2,0.3,,,,\n")
    keys = [r["conjunto"] for r in res["impact"]]
    assert keys == ["v5.1", "C1", "C2", "aceitas", "aceitas+candidatas"]
    imp = {r["conjunto"]: r for r in res["impact"]}
    assert imp["aceitas"]["n4"] == pytest.approx(imp["C2"]["n4"])
    assert imp["aceitas+candidatas"]["n4_p5"] is not None and imp["C1"]["n4_p5"] is None
    lines = V.report(res, "níveis", "parâmetros")
    assert any("DEC-099" in ln for ln in lines) and any("| C3 | rejeitada |" in ln for ln in lines)


def test_without_the_snapshot_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(V.S.B, "CP2B_SNAPSHOT", tmp_path / "none")
    monkeypatch.setattr(V, "OUT", tmp_path / "out")
    V.main()
    text = (tmp_path / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (tmp_path / "out" / "impacto.csv").exists()
