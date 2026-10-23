"""Guards for scripts/build_mapas_incerteza.py.

The maps only redraw outputs/incerteza_cp2b/ranking.csv on the IBGE mesh. These
tests fail if a value lands in the wrong class, if a municipality without a
polygon (or a polygon without a municipality) goes unreported, if the maps are
drawn from a ranking of an older version, or if the script needs the network
when the mesh is given locally.
"""

import csv
import gzip
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mapas", ROOT / "scripts" / "build_mapas_incerteza.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def square(code, x, geom="Polygon"):
    ring = [[x, -22.0], [x + 1, -22.0], [x + 1, -21.0], [x, -21.0], [x, -22.0]]
    coords = [ring] if geom == "Polygon" else [[ring]]
    return {"type": "Feature", "properties": {"codarea": code}, "geometry": {"type": geom, "coordinates": coords}}


def ranking(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


ROWS = [
    {"ibge": "3500105", "municipio": "A", "rank_med": 1, "n4_med": 20e6, "n4_p5": 18e6, "n4_p95": 24e6,
     "prob_top50": 1.0, "n4_palha_fs": 16e6},
    {"ibge": "3500204", "municipio": "B", "rank_med": 2, "n4_med": 2e6, "n4_p5": 1e6, "n4_p95": 4e6,
     "prob_top50": 0.4, "n4_palha_fs": 2.05e6},
    {"ibge": "3500303", "municipio": "C", "rank_med": 3, "n4_med": 2.5e-12, "n4_p5": 0.0, "n4_p95": 1e5,
     "prob_top50": 0.0, "n4_palha_fs": 0.0},
]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    inc = tmp_path / "inc"
    inc.mkdir()
    mesh = {"type": "FeatureCollection", "features": [square("3500105", 0), square("3500204", 1, "MultiPolygon"),
                                                      square("3599999", 2)]}
    (tmp_path / "mesh.geojson").write_text(json.dumps(mesh), encoding="utf-8")
    monkeypatch.setenv("CP2B_MALHA", str(tmp_path / "mesh.geojson"))
    monkeypatch.setattr(M, "INC", inc)
    monkeypatch.setattr(M, "OUT", tmp_path / "out")
    monkeypatch.setattr(M, "CACHE", tmp_path / "no-download")
    return inc, tmp_path / "out"


def test_values_fall_in_their_class():
    breaks = M.delta_classes()[0]
    assert [M.classify(v, breaks) for v in (-30.0, -20.0, -0.5, 1.0, 50.0)] == [0, 1, 4, 5, 8]
    assert M.classify(None, breaks) is None and M.classify(math.nan, breaks) is None
    pb = M.prob_classes()[0]
    assert [M.classify(v, pb) for v in (0.0, 0.05, 0.1, 0.9, 1.0)] == [0, 1, 2, 4, 4]
    assert M.classify(-1.0, M.n4_classes()[0]) is None
    for make in (M.n4_classes, M.prob_classes, M.width_classes, M.delta_classes):
        b, labels, colors = make()
        assert len(b) - 1 == len(labels) == len(colors)


def test_maps_are_drawn_and_gaps_reported(setup):
    inc, out = setup
    ranking(inc / "ranking.csv", ROWS)
    M.main()
    for name in ("mapa_n4_med.png", "mapa_prob_top50.png", "mapa_amplitude.png", "mapa_cenarios.png"):
        assert (out / name).stat().st_size > 1000
    text = (out / "MAPAS.md").read_text(encoding="utf-8")
    assert "Sem polígono (ficam fora dos mapas): 3500303" in text
    assert "fora do ranking (cinza): 3599999" in text
    assert "| palha_fs |  | 1 | 0 |" in text
    assert "N4 med zero: 1 municípios (por região intermediária: sem região 1)" in text
    assert not (setup[1].parent / "no-download").exists()


def test_an_older_ranking_is_not_drawn(setup):
    inc, out = setup
    ranking(inc / "ranking.csv", [{k: v for k, v in r.items() if k != "n4_palha_fs"} for r in ROWS])
    M.main()
    text = (out / "MAPAS.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and "versão anterior" in text and not (out / "mapa_n4_med.png").exists()


def test_without_the_ranking_it_says_so(setup):
    M.main()
    assert "Não rodou" in (setup[1] / "MAPAS.md").read_text(encoding="utf-8")


def test_polygons_read_the_code_and_skip_the_rest():
    mesh = {"type": "FeatureCollection", "features": [
        square("3500105", 0), {"type": "Feature", "properties": {"CD_MUN": "3500204"},
                               "geometry": {"type": "Point", "coordinates": [0, 0]}},
        {"type": "Feature", "properties": {}, "geometry": square("x", 0)["geometry"]}]}
    rings = M.polygons(mesh)
    assert list(rings) == ["3500105"] and len(rings["3500105"][0]) == 5
    with pytest.raises(ValueError):
        M.polygons({"type": "Topology"})


def test_a_gzipped_mesh_is_read(tmp_path, monkeypatch):
    mesh = {"type": "FeatureCollection", "features": [square("3500105", 0)]}
    path = tmp_path / "mesh.geojson.gz"
    path.write_bytes(gzip.compress(json.dumps(mesh).encode("utf-8")))
    monkeypatch.setenv("CP2B_MALHA", str(path))
    got, _, _ = M.load_mesh()
    assert list(M.polygons(got)) == ["3500105"]
