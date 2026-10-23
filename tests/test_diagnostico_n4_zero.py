"""Guards for scripts/build_diagnostico_n4_zero.py.

The script finds the municipalities whose med N4 is zero and the first stage
of the cascade that zeroes them. These tests fail if a municipality with N4
above zero is listed, if the stage is read in the wrong order, or if the
script writes numbers without the snapshot.
"""

import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("diag", ROOT / "scripts" / "build_diagnostico_n4_zero.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def row(ibge, code, scen, n1, n2, n3a, u, fsfl):
    n3 = max(n3a - u, 0.0)
    return {"ibge": ibge, "codigo": code, "cenario": scen, "n1": n1, "n2": n2, "n3a": n3a, "u": u, "n3": n3,
            "n4": n3 * fsfl, "fsfl": fsfl}


ROWS = []
for scen, k in (("min", 0.5), ("med", 1.0), ("max", 2.0)):
    ROWS += [row("1", "A", scen, 10 * k, 5 * k, 4 * k, 0.0, 0.6),          # has N4
             row("2", "A", scen, 10 * k, 5 * k, 4 * k, 0.0, 0.0 if scen != "max" else 0.2),   # FL zero
             row("2", "B", scen, 3 * k, 0.0, 0.0, 0.0, 0.5),                # FC zero
             row("3", "A", scen, 10 * k, 5 * k, 4 * k, 4 * k, 0.6),         # existing use takes all
             row("4", "B", scen, 0.0, 0.0, 0.0, 0.0, 0.5)]                  # no generation


def test_zero_municipalities_and_where_they_zero():
    names = defaultdict(lambda: ("", ""))
    mun, sub, lines = M.build(ROWS, names)
    got = {r["ibge"]: r["onde_zera"] for r in mun}
    assert set(got) == {"2", "3", "4"}
    assert got["2"].startswith("N4 = 0") and got["3"].startswith("N3 = 0") and got["4"].startswith("N1 = 0")
    assert {(r["ibge"], r["codigo"]): r["onde_zera"][:6] for r in sub} == {
        ("2", "A"): "N4 = 0", ("2", "B"): "N2 = 0", ("3", "A"): "N3 = 0"}
    two = next(r for r in mun if r["ibge"] == "2")
    assert two["n4_max"] > 0 and two["n4_min"] == 0
    assert any("3 municípios com N4 med zero" in ln for ln in lines)


def test_nothing_zero_is_reported_as_such():
    mun, sub, lines = M.build([r for r in ROWS if r["ibge"] == "1"], defaultdict(lambda: ("", "")))
    assert mun == [] and sub == [] and "Nenhum município tem N4 med zero." in lines


def test_without_the_snapshot_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(M.I.B, "CP2B_SNAPSHOT", tmp_path / "none")
    monkeypatch.setattr(M, "OUT", tmp_path / "out")
    M.main()
    text = (tmp_path / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (tmp_path / "out" / "municipios.csv").exists()
