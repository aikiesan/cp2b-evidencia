"""Guards for scripts/build_fl_variantes.py.

The script swaps the spatial FL of the CP2b snapshot for each of its variants.
These tests fail if it stops finding the variant the snapshot used, if that
variant stops reproducing the snapshot N4, if another variant stops giving
N3 × FS × FL, if a supply threshold goes unseen, or if it writes numbers
without the snapshot.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fl_variantes", ROOT / "scripts" / "build_fl_variantes.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

FS = {"min": 0.8, "med": 0.9, "max": 1.0}
# municipality -> (N3 of A, FL B used, FL A coverage, supply m³/day)
MUN = {"1": (1000.0, 0.8, 0.9, 100.0), "2": (50.0, 0.0, 0.5, 10.0), "3": (400.0, 0.6, 0.7, 60.0)}


def data(fl_used=1):
    rows, fl = [], {}
    for s in F.SCEN:
        for m, (n3, b, a, sup) in MUN.items():
            used = (b, a)[1 - fl_used]
            rows.append({"ibge": m, "codigo": "A", "cenario": s, "n3": n3, "fsfl": FS[s] * used,
                         "n4": n3 * FS[s] * used})
            fl[(m, "A", s)] = {"fl_codig_alocado": b, "fl_codigestao": a, F.SUPPLY: sup}
    return rows, fl


def names():
    from collections import defaultdict
    return defaultdict(lambda: ("", ""))


def test_the_used_variant_is_found_and_reproduces_n4():
    rows, fl = data()
    res = F.build(rows, fl, ["fl_codig_alocado", "fl_codigestao"], names())
    assert res["ident"][("A", "med")][0] == "fl_codig_alocado"
    assert res["ident"][("A", "med")][1] == pytest.approx(0.9)
    assert all(c["resultado"] for c in res["conferencia"])
    v = {(r["cenario"], r["variante"]): r for r in res["variantes"]}
    expected = sum(n3 * 0.9 * a for n3, _, a, _ in MUN.values())
    assert v[("med", "fl_codigestao")]["n4"] == pytest.approx(expected)
    assert v[("med", "fl_codig_alocado")]["municipios_n4_zero"] == 1
    assert v[("med", "fl_codigestao")]["zero_que_abre"] == 1 and v[("med", "fl_codigestao")]["zero_novos"] == 0
    assert [r["ibge"] for r in res["municipios"]] == ["2"]
    assert res["municipios"][0]["n4_fl_codigestao"] == pytest.approx(50.0 * 0.9 * 0.5)


def test_a_supply_threshold_is_seen():
    rows, fl = data()
    lim = {r["cenario"]: r for r in F.build(rows, fl, ["fl_codig_alocado"], names())["limiar"]}
    assert lim["med"]["separa_por_linha"] and lim["med"]["oferta_linha_max_fl_zero"] == 10.0
    assert lim["med"]["oferta_linha_min_fl_positivo"] == 60.0
    fl[("3", "A", "med")][F.SUPPLY] = 5.0            # a small municipality with FL > 0: no threshold
    lim = {r["cenario"]: r for r in F.build(rows, fl, ["fl_codig_alocado"], names())["limiar"]}
    assert not lim["med"]["separa_por_linha"]


def test_a_variant_that_does_not_fit_is_not_taken():
    rows, fl = data()
    for r in rows:
        if r["ibge"] == "3":
            r["fsfl"] *= 1.1                          # FS × FL no longer one FS times the used FL
            r["n4"] *= 1.1
    res = F.build(rows, fl, ["fl_codig_alocado", "fl_codigestao"], names())
    assert res["ident"][("A", "med")][0] is None
    assert not all(c["resultado"] for c in res["conferencia"])
    rows, fl = data(fl_used=0)                        # the snapshot used coverage: it is found
    assert F.build(rows, fl, ["fl_codig_alocado", "fl_codigestao"], names())["ident"][("A", "med")][0] == \
        "fl_codigestao"


def test_the_report_is_written(tmp_path):
    rows, fl = data()
    text = "\n".join(F.report(F.build(rows, fl, ["fl_codig_alocado", "fl_codigestao"], names())))
    assert "## 4. O FL zero segue um limiar de oferta?" in text and "FALHOU" not in text


def test_without_the_snapshot_it_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(F.I.B, "CP2B_SNAPSHOT", tmp_path / "none")
    monkeypatch.setattr(F, "OUT", tmp_path / "out")
    F.main()
    text = (tmp_path / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (tmp_path / "out" / "variantes.csv").exists()


def test_a_substrate_outside_the_fl_file_keeps_its_n4():
    rows, fl = data()
    rows += [{"ibge": "1", "codigo": "PASTO", "cenario": "max", "n3": 10.0, "fsfl": 0.5, "n4": 5.0}]
    res = F.build(rows, fl, ["fl_codig_alocado", "fl_codigestao"], names())
    assert all(c["resultado"] for c in res["conferencia"])
    detail = res["conferencia"][-1]["detalhe"]
    assert "fora do FL espacial" in detail and "PASTO max" in detail
    v = {(r["cenario"], r["variante"]): r["n4"] for r in res["variantes"]}
    assert v[("max", "fl_codigestao")] - v[("max", "fl_codig_alocado")] == pytest.approx(
        sum(n3 * 1.0 * (a - b) for n3, b, a, _ in MUN.values()))
