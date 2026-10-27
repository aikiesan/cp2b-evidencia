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
    assert "## 6. Perturbação da oferta" in text and "Não rodou: faltam em `data/fl_v51/`" in text
    assert not (run / "out" / "mapa_perturbacao_fl.png").exists() and not (run / "out" / "perturbacao.csv").exists()
    rows = list(csv.DictReader((run / "out" / "conferencia.csv").open(encoding="utf-8")))
    assert [r["checagem"] for r in rows if r["resultado"] == "False"] == [
        f"{n} é o publicado com a v5.1 (sha256 {h}…)" for n, h in F.REFERENCE.items()]


def test_without_the_tables_it_says_so(run):
    write(run / "fl_v51", tables(), manifest=False)
    F.main()
    text = (run / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Não rodou" in text and not (run / "out" / "zeros_distancia.csv").exists()


def test_map_classes_put_b_first():
    sets = {(v, "med"): s for v, s in zip(V, ({"1", "2"}, {"1"}, {"1", "2", "3"}, {"1", "2", "3", "4"}))}
    value, n = F.map_classes(sets)
    assert value == {"1": 3.0, "2": 2.0, "3": 1.0, "4": 1.0} and n == [2, 1, 1]


# frac_zero of each municipality in every design and scenario; "2" is the one zero in B in the fl_v5 tables
MUN_ZERO = {"3500105": 0.0, "3500204": 1.0, "3500303": 0.5}
CFG_CLS = {**CFG, "classes_raio": {"liquidos": ["BOV_LEITE"], "solidos_secos": ["PALHA", "BAGACO"]}}


def pert_tables(hubs_v51=10):
    designs = (("mun30", 0.0, 0.3), ("sub20_mun20", 0.2, 0.2))
    ex, summ, est, tot = [], [], [], []
    for d, cs, cm in designs:
        for s in F.SCEN:
            for k, fl in ((1, 0.69), (2, 0.71)):
                ex.append({"desenho": d, "cv_substrato": cs, "cv_municipio": cm, "cenario": s, "rodada": k,
                           "hubs": 9 + k, "hubs_v51": hubs_v51 if (d, s, k) == ("mun30", "med", 1) else 10,
                           "jaccard": 0.8, "municipios_fl_zero": k, "municipios_fl_zero_v51": 1, "FL_estado": fl,
                           "FL_estado_v51": 0.7, "spearman_cob_mun": 0.99, "top50_em_comum": 3})
            summ.append({"desenho": d, "cenario": s, "rodadas": 2, "linhas_mun_substrato": 6,
                         "linhas_max_abs_d_acima_01": 2, "linhas_p95_p05_acima_01": 1, "hubs_v51": 10,
                         "municipios_zero_v51": 1, "municipios_zero_sempre": 1, "municipios_zero_alguma_vez": 2})
            est += [{"desenho": d, "cenario": s, "codigo": c, "FL_v51": 0.7, "p05": 0.7 - w, "p95": 0.7 + w}
                    for c, w in (("BOV_LEITE", 0.05), ("BAGACO", 0.01))]
            tot += [{"desenho": d, "cenario": s, "ibge": m, "FL_v51": 0.5, "p05": 0.4, "p95": 0.65 if z else 0.47,
                     "frac_zero": z, "zero_v51": m == "3500204"} for m, z in MUN_ZERO.items()]
    return {"pert_resumo.csv": summ, "pert_execucoes.csv": ex, "pert_fl_estado.csv": est,
            "pert_fl_municipio_total.csv": tot,
            "v52_bananal_candidatos.csv": [
                {"hub_id": 7, "tipo": "grade", "d_min_km": 0.4, "bacia_cobertura": 618.0, "viavel": False,
                 "de_bananal_w": 600.0, "ganho_sozinho": 618.0},
                {"hub_id": 9, "tipo": "ete", "d_min_km": 10.0, "bacia_cobertura": 500.0, "viavel": False,
                 "de_bananal_w": 80.0, "ganho_sozinho": 500.0}]}


def with_bananal():
    """tables() and pert_tables() plus Bananal: FL zero in every variant, zero in every perturbed run."""
    t = {**tables(), **pert_tables()}
    for s in F.SCEN:
        for code, v in (("BOV_LEITE", 1338.0), ("PALHA", 77.0), ("BAGACO", 196.0)):
            t["fl_v5_municipio_substrato.csv"].append({"ibge": F.BANANAL, "codigo": code, "cenario": s,
                                                       "municipio": "Bananal", **dict.fromkeys(V, 0.0),
                                                       "oferta_L3_m3dia": v})
    t["pert_fl_municipio_total.csv"] += [{**r, "ibge": F.BANANAL} for r in t["pert_fl_municipio_total.csv"]
                                         if r["ibge"] == "3500204"]
    return t


def test_perturbation_and_bananal(run):
    write(run / "fl_v51", with_bananal())
    data, chk, why = F.load(run / "fl_v51")
    assert why == "" and "15 arquivos" in chk[0]["detalhe"]
    res = F.build(data, CFG_CLS)
    p = res["pert"]
    assert [r["cenario"] for r in p["rows"]] == ["min", "med", "max"] * 2
    r = next(r for r in p["rows"] if (r["desenho"], r["cenario"]) == ("sub20_mun20", "med"))
    assert r["rotulo"] == "20 % por substrato × 20 % por município"
    assert r["FL_estado_p05"] == pytest.approx(0.691) and (r["hubs_min"], r["hubs_max"]) == (10, 11)
    assert [c for c, _, _ in p["wide"]] == ["BOV_LEITE", "BAGACO"]
    assert [z["ibge"] for z in p["zeros_med"]] == [F.BANANAL, "3500204", "3500303"]
    assert p["amp"]["3500105"] == pytest.approx(0.07) and p["amp"]["3500204"] == pytest.approx(0.25)
    b = res["bananal"]
    assert (b["oferta_total"], b["oferta_codig"], b["liquidos"]) == (1611.0, 1534.0, 1338.0)
    assert (b["candidatos"], b["viaveis"], b["melhor"]) == (2, 0, 618.0)
    mine = [c for c in res["conferencia"] if c["checagem"].startswith(("perturbação", "Bananal"))]
    assert len(mine) == 4 and all(c["resultado"] for c in mine), mine
    text = "\n".join(F.report(res, "", ""))
    assert "## 6. Perturbação da oferta" in text and "| 30 % por município | med | 10 → 10–11 |" in text
    assert "1.534,0 para a codigestão, 87 % dela em líquidos" in text and "41 % do Q_min" in text


def test_a_baseline_that_differs_between_designs_fails_the_check(run):
    write(run / "fl_v51", {**tables(), **pert_tables(hubs_v51=12)})
    data, _, _ = F.load(run / "fl_v51")
    chk = {c["checagem"]: c for c in F.build(data, CFG_CLS)["conferencia"]}
    assert not chk["perturbação: hubs, FL estadual e zerados da v5.1 iguais em todos os desenhos"]["resultado"]
    assert not chk["Bananal: FL B med zero, nenhum candidato viável e o melhor abaixo do Q_min"]["resultado"]


def test_a_perturbation_table_that_does_not_match_the_manifest_is_refused(run):
    write(run / "fl_v51", {**tables(), **pert_tables()})
    with (run / "fl_v51" / "pert_resumo.csv").open("a", encoding="utf-8") as fh:
        fh.write("x,med,2,6,2,1,10,1,1,2\n")
    data, _, why = F.load(run / "fl_v51")
    assert data is None and "pert_resumo.csv não confere" in why


def test_the_perturbation_map(run, monkeypatch):
    write(run / "fl_v51", with_bananal())
    ring = [[0, -22.0], [1, -22.0], [1, -21.0], [0, -21.0], [0, -22.0]]
    mesh = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"codarea": m}, "geometry": {"type": "Polygon", "coordinates": [ring]}}
        for m in (*MUN, F.BANANAL)]}
    (run / "mesh.geojson").write_text(json.dumps(mesh), encoding="utf-8")
    monkeypatch.setenv("CP2B_MALHA", str(run / "mesh.geojson"))
    F.main()
    text = (run / "out" / "RELATORIO.md").read_text(encoding="utf-8")
    assert (run / "out" / "mapa_perturbacao_fl.png").exists() and "Mapa: `mapa_perturbacao_fl.png`" in text
    assert "< 0,01: 0; 0,01–0,05: 0; 0,05–0,10: 1; 0,10–0,20: 0; ≥ 0,20: 3" in text
    assert (run / "out" / "perturbacao.csv").exists() and "## 7. Bananal" in text
