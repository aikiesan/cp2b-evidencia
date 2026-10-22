"""Guards for scripts/build_evidencia_bmp.py.

The library compares the Literature Watch BMP registry with the CP2b and
feedstocks.yaml ranges. These tests fail if the registry copy loses the columns
the comparison reads, if a pretreated record gets judged against a raw range, or
if the CP2b side is read from a snapshot without the loader's checksum.
"""

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evidencia_bmp", ROOT / "scripts" / "build_evidencia_bmp.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
B = E.B


def test_registry_has_the_columns_the_comparison_reads():
    rows = E.read_registry(E.latest_registry())
    assert rows
    for col in ("record_id", "feedstock_code", "bmp_nmlch4_gvs", "substrate_condition", "tier", "doi", "url",
                "source_key", "confidence_note"):
        assert col in rows[0], col
    assert len({r["record_id"] for r in rows}) == len(rows)


def test_only_raw_records_are_placed_against_a_range():
    rng = {"X": (100.0, 150.0, 200.0)}
    recs = [{"record_id": "1", "feedstock_code": "X", "bmp_nmlch4_gvs": "250", "substrate_condition": "raw"},
            {"record_id": "2", "feedstock_code": "X", "bmp_nmlch4_gvs": "250", "substrate_condition": "pretreated"},
            {"record_id": "3", "feedstock_code": "X", "bmp_nmlch4_gvs": "", "substrate_condition": "raw"},
            {"record_id": "4", "feedstock_code": "X", "bmp_nmlch4_gvs": "90", "substrate_condition": "raw"}]
    rows = E.evidence(recs, rng, rng)
    assert [r["situacao_cp2b"] for r in rows] == ["acima", "", "", "abaixo"]
    s = E.summary(rows, ["X"], rng, rng)[0]
    assert s["brutos_comparaveis"] == 2 and s["fora_cp2b"] == 2 and s["mediana_bruto"] == 170


def test_feedstocks_yaml_ranges_are_ordered():
    for code, (lo, med, hi) in E.yaml_bmp().items():
        assert lo <= med <= hi, code


def test_cp2b_side_needs_the_verified_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "CP2B_SNAPSHOT", tmp_path)
    assert E.cp2b_bmp()[0] == {}
    path = tmp_path / B.loader_constant("FILES")["parameters"]
    path.write_text("codigo,elemento,med,min,max\nTORTA_FILTRO,BMP,280,200,380\n", encoding="utf-8")
    got, note = E.cp2b_bmp()
    assert got == {} and "recusado" in note
    monkeypatch.setattr(B, "loader_constant", lambda name: {
        "FILES": {"parameters": path.name},
        "EXPECTED_SHA256": {"parameters": hashlib.sha256(path.read_bytes()).hexdigest()},
    }[name])
    got, _ = E.cp2b_bmp()
    assert got == {"TORTA_FILTRO": (200.0, 280.0, 380.0)}
