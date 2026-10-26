"""Guards for scripts/build_fl_espacial.py.

The script reads the aggregated fl_v5 tables of data/fl_v51/. These tests fail
if it reads a table that does not match the manifest, if it counts a
municipality with some FL as zeroed, if the distance to the hub stops being
measured against r2 and Q_min, if the C02 effect is summed wrong, or if it
writes numbers without the tables.
"""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fl_espacial", ROOT / "scripts" / "build_fl_espacial.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

V = [v for v, _ in F.VARIANTS]
# municipality -> FL B, A, C, D in every substrate and scenario; "2" is zero in B, C and D, "3" nearly zero
MUN = {"3500105": (0.8, 0.9, 0.7, 0.6), "3500204": (0.0, 0.2, 0.0, 0.0), "3500303": (0.004, 0.1, 0.0, 0.0)}


def tables():
    mun, est = [], []
    for s in F.SCEN:
        for code in ("BOV_LEITE", "BAGACO"):
            for m, fl in MUN.items():
                mun.append({"ibge": m, "codigo": code, "cenario": s, "municipio": f"M{m[-1]}",
                            **dict(zip(V, fl)), "oferta_L3_m3dia": 100.0})
            est.append({"codigo": code, "cenario": s, **dict(zip(V, (0.7, 0.8, 0.6, 0.5))), "oferta_L3_m3dia": 300.0})
    return {
        "fl_v5_municipio_substrato.csv": mun,
        "fl_v5_estado_substrato.csv": est,
        "sensibilidade_r2.csv": [{"classe": "liquidos", "r1_km": 5, "r2_km": 15, "hubs_viaveis_co": 10,
                                  "FL_co": 0.5, "FL_mono": 0.4, "FL_co_todos_sem_palha": 0.5}],
        "sensibilidade_qmin.csv": [{"q_min": 1500, "hubs_viaveis_co": 10, "FL_co_sem_palha": 0.5,
                                    "FL_mono_sem_palha": 0.4}],
        "mclp_curva_B.csv": [{"hubs": h, "cobertura_sem_palha": c, "cobertura_N3_total": c}
                             for h, c in ((1, 0.3), (2, 0.6), (3, 0.85), (4, 0.96))],
        "robustez_rede.csv": [{"codigo": "BAGACO", "cenario": s, "dif_co": 0.001, "dif_mono": -0.002}
                              for s in F.SCEN],
        "fl_alocado_robustez.csv": [{"modo_palha": "usinas", "codigo": "BAGACO", "cenario": s,
                                     "dif_codig_maxw": 0.01, "dif_codig_exclusivo": -0.03} for s in F.SCEN],
        "c02_fl_delta.csv": [{"codigo": c, "cenario": s, "FL_codig_alocado_v51": 0.5, "FL_codig_alocado_c02": 0.5 + d,
                              "d_FL_codig_alocado": d, "d_FL_mono_alocado": 0.0}
                             for s in F.SCEN for c, d in (("SUINOS", 0.004 if s == "med" else 0.0), ("BAGACO", 0.0))],
        "c02_fl_municipio_delta.csv": [{"ibge": "3500105", "codigo": "SUINOS", "cenario": "max",
                                        "FL_codig_alocado_v51": 0.2, "FL_codig_alocado_c02": 0.9,
                                        "d_FL_codig_alocado": 0.7},
                                       {"ibge": "3500303", "codigo": "SUINOS", "cenario": "max",
                                        "FL_codig_alocado_v51": 0.6, "FL_codig_alocado_c02": 0.0,
                                        "d_FL_codig_alocado": -0.6}],
        "v52_zeros_distancia_hub.csv": [
            {"ibge": "3500204", "municipio": "M4", "codigo": "BOV_LEITE", "classe": "liquidos", "oferta_m3dia": 900.0,
             "d_min_km": 40.0, "d_mediana_km": 45.0, "r1_km": 5, "r2_km": 15},
            {"ibge": "3500204", "municipio": "M4", "codigo": "BAGACO", "classe": "solidos_secos",
             "oferta_m3dia": 700.0, "d_min_km": 30.0, "d_mediana_km": 31.0, "r1_km": 10, "r2_km": 25}],
    }


def write(folder: Path, data: dict, manifest=True):
    folder.mkdir(parents=True, exist_ok=True)
    man = []
    for name, rows in data.items():
        with (folder / name).open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        raw = (folder / name).read_bytes()
        man.append(f"{name},teste,{len(raw)},{hashlib.sha256(raw).hexdigest()}\n")
    if manifest:
        (folder / "MANIFESTO.csv").write_text("arquivo,origem,bytes,sha256\n" + "".join(man), encoding="utf-8")


CFG = {"q_min": {"min": 3200, "med": 1500, "max": 500},
       "raios_km": {"med": {"liquidos": [5, 15], "solidos_umidos": [15, 30], "solidos_secos": [10, 25]}}}


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "DATA", tmp_path / "fl_v51")
    monkeypatch.setattr(F, "OUT", tmp_path / "out")
    monkeypatch.setattr(F.M, "CACHE", tmp_path / "no-download")
    monkeypatch.setenv("CP2B_MALHA", str(tmp_path / "missing.geojson"))
    return tmp_path


def test_zeros_distances_and_c02(run):
    write(run / "fl_v51", tables())
    data, chk, why = F.load(run / "fl_v51")
    assert why == "" and chk[0]["resultado"]
    assert [c["resultado"] for c in chk[1:]] == [False, False]    # synthetic tables are not the published ones
    res = F.build(data, CFG)
    z = {(r["cenario"], r["variante"]): r["municipios_fl_zero"] for r in res["zeros"]}
    assert z[("med", "FL_codig_alocado")] == 1                 # "3" has FL 0,004: not zero
    assert z[("med", "FL_codigestao")] == 0 and z[("med", "FL_mono")] == 2
    assert [m for m, _, _ in res["near"]] == ["3500303"]
    (d,) = res["dist"]
    assert d["d_min_km"] == 30.0 and d["folga_r2_km"] == pytest.approx(5.0)   # 30 − 25 beats 40 − 15
    assert d["oferta_m3dia"] == 1600.0 and not d["abaixo_q_min"]
    c = {r["cenario"]: r for r in res["c02_estado"]}
    assert c["med"]["max_abs_d_B"] == pytest.approx(0.004) and c["med"]["substratos_acima"] == 1
    assert c["min"]["substratos_acima"] == 0
    (m,) = res["c02_mun"]
    assert (m["linhas"], m["municipios_sobem"], m["municipios_descem"]) == (2, 1, 1)
    assert {r["meta"]: r["hubs_N3_total"] for r in res["mclp"]} == {0.5: 2, 0.8: 3, 0.9: 4, 0.95: 4}
    assert all(c["resultado"] for c in res["conferencia"])


def test_a_table_that_does_not_match_the_manifest_is_refused(run):
    write(run / "fl_v51", tables())
    with (run / "fl_v51" / "c02_fl_delta.csv").open("a", encoding="utf-8") as fh:
        fh.write("BAGACO,med,0.5,0.6,0.1,0.0\n")
    data, _, why = F.load(run / "fl_v51")
    assert data is None and "não confere" in why


def test_a_zeroed_municipality_missing_from_the_distances_fails_the_check(run):
    t = tables()
    t["v52_zeros_distancia_hub.csv"][1]["ibge"] = "3500105"
    write(run / "fl_v51", t)
    data, _, _ = F.load(run / "fl_v51")
    chk = {c["checagem"]: c for c in F.build(data, CFG)["conferencia"]}
    assert not chk["os municípios da tabela de distâncias são os de FL B med zero"]["resultado"]


def test_the_report_and_the_map(run, monkeypatch):
    write(run / "fl_v51", tables())
    ring = [[0, -22.0], [1, -22.0], [1, -21.0], [0, -21.0], [0, -22.0]]
    mesh = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"codarea": m}, "geometry": {"type": "Polygon", "coordinates": [ring]}}
        for m in MUN]}
    (run / "mesh.geojson").write_text(json.dumps(mesh), encoding="utf-8")
    monkeypatch.setenv("CP2B_MALHA", str(run / "mesh.geojson"))
    F.main()
    text = (run / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "## 3. Por que os municípios zeram" in text
    assert "1 municípios; hub mais próximo a 30,0–30,0 km" in text and "M3 (0,0040)" in text
    assert (run / "out" / "mapa_zeros_variantes.png").exists() and "Mapa: `mapa_zeros_variantes.png`" in text
    rows = list(csv.DictReader((run / "out" / "conferencia.csv").open(encoding="utf-8")))
    assert [r["checagem"] for r in rows if r["resultado"] == "False"] == [
        f"{n} é o publicado com a v5.1 (sha256 {h}…)" for n, h in F.REFERENCE.items()]


def test_without_the_tables_it_says_so(run):
    write(run / "fl_v51", tables(), manifest=False)
    F.main()
    text = (run / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (run / "out" / "zeros_distancia.csv").exists()
