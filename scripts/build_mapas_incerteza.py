#!/usr/bin/env python3
"""
Maps of the CP2b v5.1 N4 uncertainty, municipality by municipality.

Reads outputs/incerteza_cp2b/ranking.csv (written by build_incerteza_cp2b.py)
and draws, on the IBGE municipal mesh of São Paulo:

  mapa_n4_med       N4 per municipality, CP2b med
  mapa_prob_top50   chance of staying in the top 50 across the draws
  mapa_amplitude    width of the 90 % interval of the municipal N4 over its med
  mapa_cenarios     change in municipal N4 in each literature scenario of the
                    sensitivity script (small multiples, one shared scale)

The mesh comes from the IBGE malhas API (v3) and is downloaded once to .cache/,
which is not in git; MAPAS.md records the URL and its sha256. CP2B_MALHA points
to a local GeoJSON instead (features with the 7-digit municipal code in
codarea, CD_MUN or ibge). Nothing here changes the platform or the numbers;
the maps only redraw ranking.csv.

Run from the repo root, after build_incerteza_cp2b.py:
  python3 scripts/build_mapas_incerteza.py

Outputs (outputs/mapas_incerteza/):
  mapa_n4_med.png · mapa_prob_top50.png · mapa_amplitude.png · mapa_cenarios.png · MAPAS.md
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INC = ROOT / "outputs" / "incerteza_cp2b"
OUT = ROOT / "outputs" / "mapas_incerteza"
CACHE = ROOT / ".cache" / "ibge_malha_sp_municipios.geojson"
MALHA_URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/35"
             "?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio")
CODE_KEYS = ("codarea", "CD_MUN", "ibge")
NEEDED = ("ibge", "n4_med", "n4_p5", "n4_p95", "prob_top50")
# Below this the med N4 is rounding noise of the model (it rebuilds a snapshot zero as ~1e-12): zero.
ZERO_NM3 = 1.0

INK, INK2, SURFACE, EDGE, EMPTY = "#0b0b0b", "#52514e", "#fcfcfb", "#ffffff", "#c3c2b7"
BLUE = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")
NEUTRAL = "#f0efec"
RED = ("#f6c4c0", "#ee8f8a", "#e34948", "#a92a2a")      # lighter → darker (bigger loss)
SOURCE = "Fonte: CP2b v5.1 (snapshot), sorteios de build_incerteza_cp2b.py; malha municipal do IBGE."


# ── Classes ─────────────────────────────────────────────────────────────────


def classify(v: float | None, breaks: list[float]) -> int | None:
    """Index of the class [breaks[i], breaks[i+1]) holding v; the last class is closed above."""
    if v is None or math.isnan(v) or v < breaks[0] or v > breaks[-1]:
        return None
    return next((i for i in range(len(breaks) - 1) if v < breaks[i + 1]), len(breaks) - 2)


def n4_classes():
    breaks = [0.0, 1e-9, 1.0, 2.5, 5.0, 10.0, 20.0, 40.0, math.inf]
    labels = ["zero", "< 1", "1–2,5", "2,5–5", "5–10", "10–20", "20–40", "≥ 40"]
    return breaks, labels, [NEUTRAL, *BLUE]


def prob_classes():
    breaks = [0.0, 1e-9, 0.10, 0.50, 0.90, math.inf]
    labels = ["0 %", "até 10 %", "10–50 %", "50–90 %", "≥ 90 %"]
    return breaks, labels, [NEUTRAL, BLUE[1], BLUE[3], BLUE[5], BLUE[6]]


def width_classes():
    breaks = [0.0, 0.25, 0.50, 0.75, 1.0, 1.5, math.inf]
    labels = ["< 25 %", "25–50 %", "50–75 %", "75–100 %", "100–150 %", "≥ 150 %"]
    return breaks, labels, list(BLUE[1:])


def delta_classes():
    breaks = [-math.inf, -20.0, -10.0, -5.0, -1.0, 1.0, 5.0, 10.0, 20.0, math.inf]
    labels = ["≤ −20 %", "−20 a −10 %", "−10 a −5 %", "−5 a −1 %", "±1 %", "+1 a +5 %", "+5 a +10 %",
              "+10 a +20 %", "≥ +20 %"]
    return breaks, labels, [RED[3], RED[2], RED[1], RED[0], NEUTRAL, BLUE[1], BLUE[3], BLUE[4], BLUE[6]]


# ── Inputs ──────────────────────────────────────────────────────────────────


def _num(x: str | None) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _med(r: dict) -> float:
    v = _num(r["n4_med"])
    return v if v is not None and v > ZERO_NM3 else 0.0


def read_ranking(path: Path) -> tuple[list[dict] | None, str]:
    if not path.exists():
        return None, f"falta {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}"
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = set(rows[0]) if rows else set()
    missing = [c for c in NEEDED if c not in cols]
    if missing or not any(c.startswith("n4_") and c not in NEEDED for c in cols):
        return None, ("ranking.csv é de uma versão anterior do build_incerteza_cp2b.py (faltam "
                      f"{', '.join(missing) or 'as colunas n4_<cenário>'}); rode o script de novo")
    return rows, ""


def scenario_labels(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["cenario"]: r.get("descricao", "") for r in csv.DictReader(f)}


def _gunzip(data: bytes) -> bytes:
    """The IBGE API answers gzip even unasked; a local file may be gzipped too."""
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def load_mesh() -> tuple[dict, str, str]:
    """GeoJSON, where it came from, and its sha256."""
    local = os.environ.get("CP2B_MALHA")
    if local:
        path, origin = Path(local), f"arquivo local `{Path(local).name}`"
    else:
        path, origin = CACHE, f"API de malhas do IBGE (v3): {MALHA_URL}"
        if not path.exists():
            req = urllib.request.Request(MALHA_URL, headers={"User-Agent": "cp2b-evidencia"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = _gunzip(r.read())
            json.loads(data)                     # fail here, not after caching, if it is not JSON
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    raw = _gunzip(path.read_bytes())
    return json.loads(raw), origin, hashlib.sha256(raw).hexdigest()


def polygons(mesh: dict) -> dict[str, list[list[tuple[float, float]]]]:
    """Municipal code → exterior rings (lon, lat). Holes are left out; enclaves are drawn on top."""
    if mesh.get("type") != "FeatureCollection":
        raise ValueError("a malha precisa ser um GeoJSON FeatureCollection")
    out: dict[str, list] = {}
    for feat in mesh["features"]:
        props = feat.get("properties") or {}
        code = next((str(props[k]) for k in CODE_KEYS if props.get(k) not in (None, "")), None)
        geom = feat.get("geometry") or {}
        if code is None or geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        parts = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        out.setdefault(code[:7], []).extend([tuple(p[:2]) for p in poly[0]] for poly in parts if poly)
    return out


# ── Drawing ─────────────────────────────────────────────────────────────────


def _area(ring) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def draw(ax, rings: dict, values: dict[str, float | None], classes) -> None:
    breaks, _, colors = classes
    polys, faces = [], []
    for code, parts in rings.items():
        k = classify(values.get(code), breaks)
        for ring in parts:
            polys.append(ring)
            faces.append(EMPTY if k is None else colors[k])
    order = sorted(range(len(polys)), key=lambda i: -_area(polys[i]))
    ax.add_collection(PolyCollection([polys[i] for i in order], facecolors=[faces[i] for i in order],
                                     edgecolors=EDGE, linewidths=0.15))
    xs = [x for r in polys for x, _ in r]
    ys = [y for r in polys for _, y in r]
    if xs:
        ax.set_xlim(min(xs), max(xs))
        ax.set_ylim(min(ys), max(ys))
        ax.set_aspect(1 / math.cos(math.radians((min(ys) + max(ys)) / 2)))
    ax.set_axis_off()


def legend(where, classes, title: str, empty: str | None, **kw) -> None:
    """Legend on an axes or a figure: one swatch per class, plus the no-data gray."""
    _, labels, colors = classes
    handles = [Patch(facecolor=c, edgecolor="none", label=lab) for c, lab in zip(colors, labels)]
    if empty:
        handles.append(Patch(facecolor=EMPTY, edgecolor="none", label=empty))
    leg = where.legend(handles=handles, title=title, frameon=False, fontsize=8, title_fontsize=8.5,
                       labelcolor=INK2, alignment="left", **kw)
    leg.get_title().set_color(INK)


def single_map(path: Path, rings, values, classes, title: str, subtitle: str, legend_title: str,
               empty: str | None) -> None:
    fig = plt.figure(figsize=(10, 6.4), facecolor=SURFACE)
    ax = fig.add_axes((0.02, 0.08, 0.78, 0.76))
    draw(ax, rings, values, classes)
    empty = empty if any(classify(values.get(c), classes[0]) is None for c in rings) else None
    legend(fig, classes, legend_title, empty, loc="center left", bbox_to_anchor=(0.81, 0.46))
    fig.text(0.04, 0.95, title, fontsize=13, color=INK, weight="bold", va="top")
    fig.text(0.04, 0.905, subtitle, fontsize=9, color=INK2, va="top")
    fig.text(0.04, 0.03, SOURCE, fontsize=7, color=INK2)
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def scenario_maps(path: Path, rings, deltas: dict[str, dict]) -> None:
    keys = list(deltas)
    cols = 4
    rows_n = math.ceil((len(keys) + 1) / cols)
    height = 3.1 * rows_n + 1.1                 # inches; the header takes the top 0.9
    fig, axes = plt.subplots(rows_n, cols, figsize=(4 * cols, height), facecolor=SURFACE)
    axes = list(getattr(axes, "flat", [axes]))
    classes = delta_classes()
    for ax, key in zip(axes, keys):
        draw(ax, rings, deltas[key], classes)
        ax.set_title(key, fontsize=9.5, color=INK, loc="left")
    for ax in axes[len(keys):]:
        ax.set_axis_off()
    gaps = any(classify(d.get(c), classes[0]) is None for d in deltas.values() for c in rings)
    legend(axes[len(keys)], classes, "N4 do cenário contra o med", "N4 med zero ou sem dado" if gaps else None,
           loc="center left")
    fig.text(0.02, 1 - 0.2 / height, "Quanto o N4 de cada município muda em cada cenário de literatura",
             fontsize=13, color=INK, weight="bold", va="top")
    fig.text(0.02, 1 - 0.5 / height, "Valor central de cada cenário; o FL espacial responde ao N3 do "
             "cenário. Descrições em MAPAS.md.", fontsize=9, color=INK2, va="top")
    fig.text(0.02, 0.008, SOURCE, fontsize=7, color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=1 - 0.95 / height, bottom=0.2 / height,
                        wspace=0.02, hspace=0.12)
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ── Main ────────────────────────────────────────────────────────────────────


def fmt(x: float, nd: int = 1) -> str:
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build(rows: list[dict], rings: dict, origin: str, sha: str, labels: dict[str, str]) -> list[str]:
    by = {r["ibge"]: r for r in rows}
    n4 = {k: _med(r) / 1e6 for k, r in by.items()}
    prob = {k: _num(r["prob_top50"]) for k, r in by.items()}
    width = {}
    for k, r in by.items():
        med, lo, hi = _med(r), _num(r["n4_p5"]), _num(r["n4_p95"])
        width[k] = (hi - lo) / med if med and lo is not None and hi is not None else None
    keys = [c[3:] for c in rows[0] if c.startswith("n4_") and c not in NEEDED]
    deltas = {}
    for key in keys:
        deltas[key] = {}
        for k, r in by.items():
            med, v = _med(r), _num(r[f"n4_{key}"])
            deltas[key][k] = 100 * (v / med - 1) if med and v is not None else None

    OUT.mkdir(parents=True, exist_ok=True)
    single_map(OUT / "mapa_n4_med.png", rings, n4, n4_classes(), "N4 por município, CP2b v5.1 (med)",
               "Biometano disponível no N4, em milhões de Nm³ de CH₄ por ano.", "mi Nm³/ano", "sem dado")
    single_map(OUT / "mapa_prob_top50.png", rings, prob, prob_classes(),
               "Chance de ficar entre os 50 maiores municípios",
               "Fração dos sorteios em que o município fica no top 50 do N4; parâmetros sorteados nas faixas "
               "do CP2b.", "P(top 50)", "sem dado")
    single_map(OUT / "mapa_amplitude.png", rings, width, width_classes(),
               "Largura do intervalo de 90 % do N4 municipal",
               "(p95 − p5) / med do N4 de cada município nos sorteios.", "(p95 − p5) / med", "N4 med zero")
    scenario_maps(OUT / "mapa_cenarios.png", rings, deltas)

    missing = sorted(k for k in by if k not in rings)
    extra = sorted(k for k in rings if k not in by)
    top = sorted(by.values(), key=lambda r: int(r["rank_med"]) if r.get("rank_med") else 10 ** 9)
    frontier = [r for r in top if 0.10 <= (prob[r["ibge"]] or 0) < 0.90]
    L = [
        "# Mapas da incerteza do N4 do CP2b v5.1",
        "",
        "> Redesenho de `outputs/incerteza_cp2b/ranking.csv`; nenhum número novo. "
        f"Malha: {origin} (sha256 `{sha[:16]}…`).",
        "",
        "| Mapa | O que mostra |",
        "|---|---|",
        "| `mapa_n4_med.png` | N4 municipal no med do CP2b, mi Nm³/ano |",
        "| `mapa_prob_top50.png` | fração dos sorteios em que o município fica no top 50 |",
        "| `mapa_amplitude.png` | (p95 − p5) / med do N4 municipal |",
        "| `mapa_cenarios.png` | N4 do cenário contra o med, município a município, um painel por cenário |",
        "",
        f"Municípios no ranking: {len(by)}; com polígono na malha: {len(by) - len(missing)}.",
    ]
    if missing:
        L.append(f"Sem polígono (ficam fora dos mapas): {', '.join(missing)}.")
    if extra:
        L.append(f"Na malha e fora do ranking (cinza): {', '.join(extra)}.")
    zero = [r for r in by.values() if not _med(r)]
    regions: dict[str, int] = {}
    for r in zero:
        regions[r.get("rgint") or "sem região"] = regions.get(r.get("rgint") or "sem região", 0) + 1
    if zero:
        L.append(f"N4 med zero: {len(zero)} municípios (por região intermediária: "
                 f"{'; '.join(f'{g} {n}' for g, n in sorted(regions.items(), key=lambda kv: -kv[1]))}).")
    L += ["", f"Na fronteira do top 50 (entre 10 % e 90 % de chance): {len(frontier)} municípios.", "",
          "## Cenários", "", "| Painel | Cenário | Municípios com queda > 5 % | Com alta > 5 % |",
          "|---|---|---:|---:|"]
    for key in keys:
        d = [v for v in deltas[key].values() if v is not None]
        L.append(f"| {key} | {labels.get(key, '')} | {sum(v < -5 for v in d)} | {sum(v > 5 for v in d)} |")
    L += ["", "## Como ler", "",
          "- As classes são fixas e iguais entre rodadas, para que dois mapas se comparem a olho.",
          "- Cinza claro é sem dado, ou N4 med zero quando a medida é relativa ao med.",
          "- O intervalo de 90 % supõe parâmetros independentes (ver `outputs/incerteza_cp2b/RELATORIO.md`).",
          f"- Escala dos cenários: {', '.join(delta_classes()[1])}; vermelho é queda, azul é alta.",
          ""]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, why = read_ranking(INC / "ranking.csv")
    if rows is None:
        (OUT / "MAPAS.md").write_text(f"# Mapas da incerteza do N4 do CP2b v5.1\n\nNão rodou: {why}.\n",
                                      encoding="utf-8")
        print(f"Sem mapas: {why}")
        return
    mesh, origin, sha = load_mesh()
    rings = polygons(mesh)
    lines = build(rows, rings, origin, sha, scenario_labels(INC / "cenarios_ranking.csv"))
    (OUT / "MAPAS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rings)} polígonos · {len(rows)} municípios no ranking")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
