#!/usr/bin/env python3
"""
CP2b v5.1 uncertainty when parameters move together.

build_incerteza_cp2b.py draws every parameter independently; the CP2b min-max
band moves all of them together. The true interval sits between the two, and
where depends on which parameters share a source. This script redraws the same
model with groups of parameters correlated through a Gaussian copula:

  z_k = √ρ · z_group + √(1 − ρ) · ε_k,   u_k = Φ(z_k),   x_k = F⁻¹_k(u_k)

F_k is the same triangular (min, med, max) as in build_incerteza_cp2b.py, so
each parameter keeps its own range and shape; only the joint movement
changes. Residuals (what the snapshot varies outside the parameter file) are
drawn the same way, as the position t in triangular(−1, 0, 1).

Structures:

  independente  each parameter alone (ρ = 0); the interval of build_incerteza
  substrato     every parameter of a substrate together (one source per substrate)
  elemento      one element across substrates together (all BMP, all FC, …:
                one lab method or one reading of the definition)
  cana          the four sugarcane residues together, the rest independent
  tudo          everything together; at ρ = 1 the extremes are the CP2b band

and, when the parameter file has a `fonte` column, three structures read from
the sources the CP2b cites (where `fonte` is feedstocks.yaml, the refs of that
element in the yaml, used only when the yaml range is the file's range):

  fonte         one element across substrates together when they cite a
                reference in common (bagaço, palha and torta BMP all cite
                Paulose 2021, Talha 2016 and Velásquez 2020); values set by the
                team ("cp2b") alone
  fonte_ampla   any parameters with a reference in common, across elements
  fonte_equipe  fonte, plus the team's own values of one element together

Every parameter raises N4, so ρ = 1 in a group means the group sits at the
same quantile of its ranges. Nothing here changes the platform or the numbers.

Run from the repo root (CP2B_MC_N draws per configuration, default 20000):
  python3 scripts/build_incerteza_correlacao.py

Outputs (outputs/incerteza_correlacao/):
  correlacao.csv · conferencia.csv · fontes.csv · RELATORIO.md
"""

from __future__ import annotations

import csv
import importlib.util
import math
import os
import re
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "incerteza_correlacao"
INC_CSV = ROOT / "outputs" / "incerteza_cp2b" / "incerteza.csv"
SEED = 20261024
CANE = ("PALHA", "BAGACO", "TORTA_FILTRO", "VINHACA")


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I = _load(ROOT / "scripts" / "build_incerteza_cp2b.py")  # noqa: E741
S, fmt, mi = I.S, I.fmt, I.mi

# (key, description, group of a (code, element) key, values of ρ)
STRUCTURES = (
    ("independente", "cada parâmetro sozinho", lambda c, e: (c, e), (0.0,)),
    ("substrato", "todos os parâmetros de um substrato juntos", lambda c, e: c, (0.5, 1.0)),
    ("elemento", "o mesmo elemento em todos os substratos (todos os BMP, todos os FC, …)", lambda c, e: e, (0.5, 1.0)),
    ("cana", "palha, bagaço, torta e vinhaça juntos; o resto independente",
     lambda c, e: "cana" if c in CANE else (c, e), (1.0,)),
    ("tudo", "todos juntos", lambda c, e: "tudo", (0.5, 1.0)),
)

# Structures read from the cited sources: (key, description, grouping mode, values of ρ).
SOURCE_STRUCTURES = (
    ("fonte", "o mesmo elemento com uma referência em comum (o BMP de bagaço, palha e torta, …); valores da "
     "equipe sozinhos", "elemento", (0.5, 1.0)),
    ("fonte_ampla", "qualquer parâmetro com uma referência em comum, mesmo de elementos diferentes", "ampla", (1.0,)),
    ("fonte_equipe", "fonte, e os valores da própria equipe (cp2b) de um mesmo elemento juntos", "equipe", (1.0,)),
)
YAML_KEY = {"BMP": ("bmp", 1.0), "ST": ("ts", 0.01), "SV": ("vs_of_ts", 0.01), "g": ("rpr", 1.0)}
YAML_FACTOR = {"FC": "fc", "FCo": "fco", "FS": "fs", "FL": "fl"}
TEAM = ("cp2b", "override cp2b", "decisão cp2b", "decisao cp2b")
SHOWN = "valores mostrados"     # "valores mostrados = feedstocks.yaml": where the shown range came from, not a source
NO_REFS = "o yaml não tem refs para esse elemento"
TAG = re.compile(r"^\s*(FC|FCo|FS|FL|eta)\s*=", re.IGNORECASE)


# ── Sources ─────────────────────────────────────────────────────────────────


def read_sources() -> tuple[dict, str]:
    """{(code, element): fonte} from the parameter file, or {} with the reason."""
    path, why = S._verified("parameters")
    if path is None:
        return {}, why
    with path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "fonte" not in rows[0]:
        return {}, f"{path.name} não tem a coluna fonte"
    return {(r["codigo"], r["elemento"]): (r.get("fonte") or "").strip() for r in rows}, ""


def read_yaml() -> tuple[dict, str]:
    """The feedstocks block of the platform's feedstocks.yaml, or {} with the reason."""
    path = I.P.FEEDSTOCKS
    if not path.exists():
        return {}, f"sem {path.name}"
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("feedstocks") or {}, ""


def _norm(part: str) -> str:
    """A cited source without pages and parentheses, lower case: 'Atlas SP 2020 p.65 (40/50%)' -> 'atlas sp 2020'."""
    t = re.sub(r"\([^)]*\)", " ", part.lower())
    t = re.sub(r"\bp\.\s*\d+(\s*[-–]\s*\d+)?", " ", t)
    return re.sub(r"\s+", " ", t).strip(" ,.:;")


def _same(a: tuple, b: tuple) -> bool:
    return all(abs(x - y) <= 1e-6 * max(1.0, abs(y)) for x, y in zip(a, b))


def yaml_refs(code: str, element: str, rng: tuple, yml: dict) -> tuple[list[str], str]:
    """The yaml refs of a parameter whose fonte is feedstocks.yaml, and a note when they cannot be used."""
    block = yml.get(code) or {}
    if element in YAML_KEY:
        key, scale = YAML_KEY[element]
        node = block.get(key)
        refs = node.get("refs") if isinstance(node, dict) else None
    elif element in YAML_FACTOR:
        fde = block.get("fde") or {}
        node, refs, scale = (fde.get("components") or {}).get(YAML_FACTOR[element]), fde.get("refs"), 1.0
        tagged = [r for r in refs or [] if isinstance(r, dict) and TAG.match(str(r.get("value", "")))]
        if tagged:
            refs = [r for r in tagged if TAG.match(str(r["value"])).group(1).lower() == element.lower()]
    else:
        node, refs, scale = None, None, 1.0
    if not isinstance(node, dict) or not refs:
        return [], f"{code} {element}: {NO_REFS}"
    got = tuple(scale * float(node[k]) for k in ("min", "medio", "max"))
    if not _same(got, tuple(rng)):
        return [], (f"{code} {element}: faixa do yaml {'–'.join(fmt(x, 3) for x in got)} diferente da do arquivo "
                    f"{'–'.join(fmt(x, 3) for x in rng)}")
    return sorted({str(r["id"] if isinstance(r, dict) else r) for r in refs}), ""


def source_info(fonte: str, code: str, element: str, rng: tuple, yml: dict) -> tuple[tuple, bool, str]:
    """(cited references, whether the team set the value, note) of one parameter."""
    refs, team, notes = set(), False, []
    for part in fonte.split(";"):
        t = _norm(part)
        if not t or t.startswith(SHOWN):
            continue
        if t == "feedstocks.yaml":
            got, note = yaml_refs(code, element, rng, yml)
            refs.update(got)
            notes += [note] if note else []
        elif t.startswith(TEAM):
            team = True
        else:
            refs.add("FL espacial do CP2b (fl_v5)" if "fl_espacial" in t else t)
    return tuple(sorted(refs)), team, "; ".join(notes)


def source_groups(info: dict, mode: str) -> dict:
    """{(code, element): group}: parameters joined by a reference in common (union-find).

    mode 'elemento' joins only parameters of the same element, 'ampla' any two, 'equipe' as 'elemento'
    plus the team's own values of one element.
    """
    parent: dict = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for key, (refs, team, _) in info.items():
        nodes = [r if mode == "ampla" else (key[1], r) for r in refs]
        if mode == "equipe" and team:
            nodes.append((key[1], "equipe CP2b"))
        for nd in nodes:
            parent[find(("ref", nd))] = find(("par", key))
    return {key: " ".join(find(("par", key))[1]) for key in info}


_erf = np.vectorize(math.erf, otypes=[float])


def phi(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + _erf(z / math.sqrt(2.0)))


def tri_ppf(u: np.ndarray, lo: float, mode: float, hi: float) -> np.ndarray:
    """Inverse CDF of the triangular (lo, mode, hi)."""
    u = np.asarray(u, float)
    if hi == lo:
        return np.full(u.shape, lo)
    f = (mode - lo) / (hi - lo)
    left = lo + np.sqrt(np.clip(u, 0, 1) * (hi - lo) * (mode - lo))
    right = hi - np.sqrt(np.clip(1 - u, 0, 1) * (hi - lo) * (hi - mode))
    return np.where(u < f, left, right)


def at_quantile(model, u: float) -> float:
    """State N4 with every parameter and residual at the same quantile u of its distribution."""
    vals = {k: tri_ppf(np.array([u]), *d) for k, d in model.dists().items()}
    return float(model.evaluate(vals)["state"]["n4"][0])


def run(model, group_of, rho: float, n: int, seed: int, r0: np.ndarray) -> dict:
    """n correlated draws: state N4, Spearman per draw and how often each municipality stays in the top 50."""
    rng = np.random.default_rng(seed)
    dists = model.dists()
    keys = sorted(dists)
    groups = sorted({repr(group_of(*k)) for k in keys})
    gi = np.array([groups.index(repr(group_of(*k))) for k in keys])
    n_mun = len(model.munis)
    n4 = np.empty(n)
    rho_s = np.empty(n)
    top = np.zeros(n_mun)
    for start in range(0, n, I.BATCH):
        d = min(I.BATCH, n - start)
        z = math.sqrt(rho) * rng.standard_normal((d, len(groups)))[:, gi] + \
            math.sqrt(1 - rho) * rng.standard_normal((d, len(keys)))
        u = phi(z)
        out = model.evaluate({k: tri_ppf(u[:, j], *dists[k]) for j, k in enumerate(keys)})
        n4[start:start + d] = out["state"]["n4"]
        ranks = I.rank_rows(out["mun"])
        rho_s[start:start + d] = (1 - 6 * ((ranks - r0) ** 2).sum(1) / (n_mun * (n_mun ** 2 - 1))
                                  if n_mun > 1 else 1.0)
        top += (ranks <= I.TOP).sum(0)
    return {"n4": n4, "spearman": rho_s, "p_top": top / n, "groups": len(groups)}


def q(a, p) -> float:
    return float(np.quantile(a, p))


def build(rows, params, n: int, fontes: dict | None = None, yml: dict | None = None,
          fonte_note: str = "") -> tuple[list[dict], list[dict], list[dict], list[str]]:
    model = I.Model(rows, params)
    med = float(model.at(1)["state"]["n4"][0])
    band = {s: float(model.snapshot["n4"][I.SCEN.index(s)].sum()) for s in ("min", "max")}
    r0 = I.rank_rows(model.at(1)["mun"])[0]
    top0 = r0 <= I.TOP
    out, sims = [], {}
    structures = list(STRUCTURES)
    info, src_rows = {}, []
    if fontes:
        info = {k: source_info(fontes.get(k, ""), *k, model.params[k], yml or {}) for k in sorted(model.params)}
        by_mode = {mode: source_groups(info, mode) for _, _, mode, _ in SOURCE_STRUCTURES}
        for key, desc, mode, rhos in SOURCE_STRUCTURES:
            structures.append((key, desc, lambda c, e, g=by_mode[mode]: g.get((c, e), (c, e)), rhos))
        for k, (refs, team, note) in info.items():
            src_rows.append({"codigo": k[0], "elemento": k[1], "min": model.params[k][0], "med": model.params[k][1],
                             "max": model.params[k][2], "fonte": fontes.get(k, ""), "referencias": " | ".join(refs),
                             "valor_da_equipe": team, "nota": note,
                             **{f"grupo_{key}": by_mode[mode][k] for key, _, mode, _ in SOURCE_STRUCTURES}})
    for k, (key, desc, group_of, rhos) in enumerate(structures):
        for j, rho in enumerate(rhos):
            t0 = time.time()
            sim = run(model, group_of, rho, n, SEED + 10 * k + j, r0)
            sims[(key, rho)] = sim
            v = sim["n4"]
            out.append({"estrutura": key, "descricao": desc, "rho": rho, "grupos": sim["groups"],
                        "n4_p5": q(v, .05), "n4_p50": q(v, .5), "n4_p95": q(v, .95), "n4_media": float(v.mean()),
                        "p5_rel": q(v, .05) / med - 1, "p95_rel": q(v, .95) / med - 1,
                        "spearman_p50": q(sim["spearman"], .5), "spearman_p5": q(sim["spearman"], .05),
                        "top50_90pct": int((sim["p_top"][top0] >= 0.9).sum()), "top50_n": int(top0.sum())})
            print(f"  {key} ρ={rho}: {time.time() - t0:.0f} s")

    chk = []
    ind = sims[("independente", 0.0)]["n4"]
    ref = None
    if INC_CSV.exists():
        with INC_CSV.open(encoding="utf-8") as fh:
            ref = next((r for r in csv.DictReader(fh) if r["nivel"] == S.LABELS["n4"]), None)
    if ref:
        dev = max(abs(q(ind, .05) / float(ref["p5"]) - 1), abs(q(ind, .95) / float(ref["p95"]) - 1))
        chk.append({"checagem": "independente reproduz o p5 e o p95 de build_incerteza_cp2b (±1 %)",
                    "resultado": dev <= 0.01, "detalhe": f"maior desvio {fmt(100 * dev, 2)} %"})
    else:
        chk.append({"checagem": "independente reproduz o p5 e o p95 de build_incerteza_cp2b (±1 %)",
                    "resultado": "sem incerteza.csv", "detalhe": "rode build_incerteza_cp2b.py antes"})
    allv = sims[("tudo", 1.0)]["n4"]
    exp5, exp95 = at_quantile(model, 0.05), at_quantile(model, 0.95)
    dev = max(abs(q(allv, .05) / exp5 - 1), abs(q(allv, .95) / exp95 - 1))
    chk.append({"checagem": "tudo, ρ = 1: p5 e p95 = N4 com tudo no quantil 5 % e 95 % (±1 %)",
                "resultado": dev <= 0.01, "detalhe": f"{mi(exp5)}–{mi(exp95)} mi; maior desvio {fmt(100 * dev, 2)} %"})
    lo, hi = at_quantile(model, 0.0), at_quantile(model, 1.0)
    dev = max(abs(lo / band["min"] - 1), abs(hi / band["max"] - 1))
    chk.append({"checagem": "quantil 0 e 1 de tudo = faixa mín–máx do snapshot (±0,1 %)",
                "resultado": dev <= 0.001,
                "detalhe": f"{mi(lo)}–{mi(hi)} mi contra {mi(band['min'])}–{mi(band['max'])}"})
    return out, chk, src_rows, report(out, chk, med, band, n, src_rows, fonte_note)


def source_section(src_rows: list[dict], fonte_note: str) -> list[str]:
    L = ["", "## 3. Os grupos por fonte", ""]
    if not src_rows:
        return L + [f"As estruturas por fonte não rodaram: {fonte_note or 'sem a coluna fonte'}.", ""]
    L += ["Grupos da estrutura `fonte` com mais de um parâmetro (o mesmo elemento citando uma referência em "
          "comum). Os grupos de `fonte_ampla` e `fonte_equipe` estão em `fontes.csv`.", "",
          "| Parâmetros | Referências em comum |", "|---|---|"]
    groups: dict = {}
    for r in src_rows:
        groups.setdefault(r["grupo_fonte"], []).append(r)
    for members in sorted((g for g in groups.values() if len(g) > 1), key=lambda g: (g[0]["elemento"], -len(g))):
        common = set.intersection(*(set(r["referencias"].split(" | ")) for r in members))
        shown = sorted(common) or sorted({x for r in members for x in r["referencias"].split(" | ")})
        L.append(f"| {', '.join(r['codigo'] + ' ' + r['elemento'] for r in members)} | "
                 f"{'; '.join(shown)}{'' if common else ' (em cadeia)'} |")
    team = [f"{r['codigo']} {r['elemento']}" for r in src_rows if r["valor_da_equipe"] and not r["referencias"]]
    alone = [f"{r['codigo']} {r['elemento']}" for r in src_rows
             if not (r["referencias"] or r["valor_da_equipe"] or r["nota"])]
    no_refs: dict = {}
    for r in src_rows:
        if r["nota"].endswith(NO_REFS):
            no_refs.setdefault(r["codigo"], []).append(r["elemento"])
    other = [r["nota"] for r in src_rows if r["nota"] and not r["nota"].endswith(NO_REFS)]
    L += ["", f"- Valores da própria equipe, sem referência externa ({len(team)}): {', '.join(team) or 'nenhum'}."]
    if alone:
        L.append(f"- Sem fonte identificável, ficam sozinhos ({len(alone)}): {', '.join(alone)}.")
    if no_refs:
        L.append("- Fonte feedstocks.yaml, mas o yaml não tem refs para o código e o elemento: "
                 + "; ".join(f"{c} {', '.join(els)}" for c, els in sorted(no_refs.items())) + ".")
    if other:
        L.append(f"- Fonte feedstocks.yaml com faixa diferente da do arquivo (refs não usadas): {'; '.join(other)}.")
    if fonte_note:
        L.append(f"- {fonte_note}.")
    return L + [""]


def report(out, chk, med, band, n, src_rows=(), fonte_note="") -> list[str]:
    def pct(x):
        return f"{'+' if x > 0 else ''}{fmt(100 * x, 1)} %"

    L = [
        "# Incerteza do N4 do CP2b v5.1 com parâmetros correlacionados",
        "",
        f"> {n} sorteios por configuração; volumes em milhões de Nm³ de CH₄ por ano. O mesmo modelo de "
        "`build_incerteza_cp2b.py` (que reproduz o mín, o med e o máx do snapshot), com grupos de parâmetros "
        "sorteados juntos por uma cópula gaussiana de correlação ρ. Cada parâmetro mantém a sua triangular "
        "(mín, med, máx) do CP2b; muda só o quanto eles andam juntos. Nada aqui muda a plataforma.",
        "",
        f"N4 med do CP2b: {mi(med)}. Faixa mín–máx do snapshot: {mi(band['min'])}–{mi(band['max'])}.",
        "",
        "## 1. Intervalo de 90 % do N4 do estado",
        "",
        "| Estrutura | O que anda junto | ρ | p5 | p50 | p95 | p5–p95 contra o med | Spearman p5 | "
        "Top 50 com ≥ 90 % |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for r in out:
        L.append(f"| {r['estrutura']} | {r['descricao']} | {fmt(r['rho'], 1)} | {mi(r['n4_p5'])} | "
                 f"{mi(r['n4_p50'])} | {mi(r['n4_p95'])} | {pct(r['p5_rel'])} a {pct(r['p95_rel'])} | "
                 f"{fmt(r['spearman_p5'], 3)} | {r['top50_90pct']} de {r['top50_n']} |")
    L += ["", "## 2. Conferência", "", "| Checagem | Resultado | Detalhe |", "|---|---|---|"]
    for c in chk:
        ok = c["resultado"]
        L.append(f"| {c['checagem']} | {ok if isinstance(ok, str) else 'ok' if ok else 'FALHOU'} | {c['detalhe']} |")
    L += source_section(list(src_rows), fonte_note)
    L += ["", "## Como ler", "",
          "- ρ = 0 é a leitura de `build_incerteza_cp2b.py`. Com ρ = 1 num grupo, o grupo inteiro fica no mesmo "
          "quantil das suas faixas em cada sorteio; tudo com ρ = 1 vai de ponta a ponta da faixa mín–máx do "
          "CP2b.",
          "- `elemento` é a correlação mais defensável para o BMP (o mesmo método de laboratório) e para FC, FS e "
          "FL (a mesma leitura da definição); `substrato` é a correlação de quem tira todos os fatores de um "
          "substrato da mesma fonte; `cana` mede só o peso de a cana andar junta.",
          "- O Spearman p5 e o top 50 dizem se o ranking municipal aguenta a correlação: quando tudo sobe ou desce "
          "junto, o ranking tende a ficar mais estável que o total, porque os municípios andam juntos.",
          "- `fonte` é a correlação que as fontes citadas sustentam: o mesmo elemento anda junto quando cita a mesma "
          "referência. Onde `fonte` é feedstocks.yaml, as referências são as refs do yaml para aquele elemento, "
          "usadas só quando a faixa do yaml é a do arquivo. Um valor da equipe (`cp2b`) não cita fonte, e `fonte` o "
          "deixa sozinho; `fonte_equipe` põe os valores da equipe de um mesmo elemento juntos. `fonte_ampla` junta "
          "também elementos diferentes da mesma referência (o ST e o BMP do mesmo artigo), o que supõe que eles "
          "erram para o mesmo lado.",
          "- O intervalo de cada estrutura é o que se tem se aquela correlação for verdadeira; não há aqui uma "
          "estimativa de qual ρ é o real.",
          ""]
    return L


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, levels_note = S.read_levels()
    params, _, param_note = I.parameters()
    if rows is None or not params:
        why = levels_note if rows is None else param_note
        (OUT / "RELATORIO.md").write_text("# Incerteza do N4 do CP2b v5.1 com parâmetros correlacionados\n\n"
                                          f"Não rodou: {why}.\n", encoding="utf-8")
        print(f"Sem correlação: {why}")
        return
    n = int(os.environ.get("CP2B_MC_N", "20000"))
    fontes, fonte_note = read_sources()
    yml, yaml_note = read_yaml() if fontes else ({}, "")
    out, chk, src_rows, lines = build(rows, params, n, fontes, yml, fonte_note or yaml_note)
    I.write_csv(OUT / "correlacao.csv", out)
    I.write_csv(OUT / "conferencia.csv", chk)
    I.write_csv(OUT / "fontes.csv", src_rows)
    (OUT / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [c["checagem"] for c in chk if c["resultado"] is False]
    print(f"{n} sorteios por configuração · conferência: {'ok' if not failed else 'FALHOU em ' + '; '.join(failed)}")
    print(f"Wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}/")


if __name__ == "__main__":
    main()
