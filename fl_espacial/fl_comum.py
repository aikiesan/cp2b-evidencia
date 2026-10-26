"""Utilidades comuns do FL espacial (Método CP2b v5): configuração, caminhos, log, municípios, grades."""
from __future__ import annotations

import logging
import re
import sys
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
CFG = yaml.safe_load(open(HERE / "config_fl.yaml", encoding="utf-8"))
OUT = HERE / "outputs"
FIG = OUT / "figuras"
CACHE = HERE / "cache"
LOGS = HERE / "logs"
for _d in (OUT, FIG, CACHE, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

CRS = CFG["crs_metrico"]
SC = ["min", "med", "max"]
DAYS = 365
SEED = CFG["semente"]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def caminho(chave: str) -> Path:
    return Path(CFG["caminhos"][chave])


def logger(nome: str) -> logging.Logger:
    log = logging.getLogger(nome)
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S")
    for h in (logging.FileHandler(LOGS / f"{nome}.log", mode="w", encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)
    return log


@contextmanager
def etapa(log: logging.Logger, texto: str):
    t0 = time.perf_counter()
    log.info(f"▶ {texto}")
    yield
    log.info(f"  ✓ {texto} ({time.perf_counter() - t0:,.1f} s)")


def norm(s) -> str:
    """Mesma normalização de nomes de município usada em cp2b_cascade.py."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"\s*\((SP)\)\s*$|\s*-\s*SP$", "", s.strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def municipios():
    import geopandas as gpd

    mun = gpd.read_file(caminho("municipios"))
    mun["ibge"] = mun["CD_MUN"].astype(int)
    return mun[["ibge", "NM_MUN", "CD_RGINT", "geometry"]].rename(columns={"NM_MUN": "municipio"}).to_crs(CRS)


def classes_de(codigo: str) -> str:
    for cls, lst in CFG["classes_raio"].items():
        if codigo in lst:
            return cls
    raise KeyError(codigo)


def peso_w(d_m, r1_km: float, r2_km: float):
    """w(d) = 1 se d ≤ r1; (r2 − d)/(r2 − r1) se r1 < d < r2; 0 se d ≥ r2 (d em metros)."""
    if not r2_km > r1_km:
        raise ValueError(f"raios inválidos: r1 = {r1_km} km, r2 = {r2_km} km (exige r2 > r1)")
    r1, r2 = r1_km * 1000.0, r2_km * 1000.0
    return np.clip((r2 - np.asarray(d_m, dtype=float)) / (r2 - r1), 0.0, 1.0)


def assinatura_nos(HUBS, LOC) -> str:
    """Hash dos hubs e locais de oferta (ordem, nós, conexões): um cache de pares ou histogramas só vale se foi
    gerado com exatamente estes hubs e locais."""
    import hashlib

    h = hashlib.sha1()
    for a in (HUBS.node.to_numpy(np.int64), HUBS.conn_m.to_numpy(np.float64), LOC["loc"].to_numpy(np.int64),
              LOC.node.to_numpy(np.int64), LOC.conn_m.to_numpy(np.float64), LOC.hub_fonte.to_numpy(np.int64)):
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def cache_confere(salva, atual: dict, arquivo, dependencias) -> bool:
    """O cache vale se a assinatura salva é igual à atual. Um cache gravado antes da introdução do hash de nós
    (assinatura sem a chave "nos", demais campos iguais) só é aceito se for mais novo que todos os arquivos de que
    depende — isto é, se foi gerado a partir dos hubs e locais atuais."""
    if salva == atual:
        return True
    if isinstance(salva, dict) and "nos" not in salva and salva == {k: v for k, v in atual.items() if k != "nos"}:
        t = Path(arquivo).stat().st_mtime
        return all(t > Path(d).stat().st_mtime for d in dependencias)
    return False


class Grade:
    """Grade regular alinhada a múltiplos de `passo` no CRS métrico; id = iy * nx + ix."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float, passo: float):
        self.passo = float(passo)
        self.x0 = np.floor(x0 / passo) * passo
        self.y0 = np.floor(y0 / passo) * passo
        self.nx = int(np.ceil((x1 - self.x0) / passo))
        self.ny = int(np.ceil((y1 - self.y0) / passo))

    def ids(self, x, y):
        ix = np.floor((np.asarray(x) - self.x0) / self.passo).astype(np.int64)
        iy = np.floor((np.asarray(y) - self.y0) / self.passo).astype(np.int64)
        return iy * self.nx + ix

    def centro(self, cid):
        cid = np.asarray(cid, dtype=np.int64)
        return (self.x0 + (cid % self.nx + 0.5) * self.passo, self.y0 + (cid // self.nx + 0.5) * self.passo)

    def poligonos(self, cid):
        import shapely

        cx, cy = self.centro(cid)
        h = self.passo / 2
        return shapely.box(cx - h, cy - h, cx + h, cy + h)

    def to_dict(self):
        return dict(x0=self.x0, y0=self.y0, nx=self.nx, ny=self.ny, passo=self.passo)

    @classmethod
    def from_dict(cls, d):
        g = cls.__new__(cls)
        g.x0, g.y0, g.nx, g.ny, g.passo = d["x0"], d["y0"], int(d["nx"]), int(d["ny"]), float(d["passo"])
        return g


def grade_sp(passo: float, mun=None) -> Grade:
    """Grade que cobre SP (sem buffer), alinhada a múltiplos do passo."""
    if mun is None:
        mun = municipios()
    x0, y0, x1, y1 = mun.total_bounds
    return Grade(x0, y0, x1, y1, passo)


def carregar_grafo(variante: str = "completo"):
    d = np.load(CACHE / f"grafo_{variante}.npz", allow_pickle=True)
    return {k: d[k] for k in d.files}


def rede_pandana(G):
    import pandana
    import pandas as pd

    nodes = pd.Index(np.arange(len(G["x"])), name="id")
    net = pandana.Network(pd.Series(G["x"], index=nodes), pd.Series(G["y"], index=nodes),
                          pd.Series(G["u"]), pd.Series(G["v"]), pd.DataFrame({"m": G["comp"]}), twoway=True)
    return net


class Bacias:
    """Bacia ponderada exata a partir dos histogramas por km (F = Σ oferta, D = Σ oferta × d_km).

    Σ oferta·w(d) = Σ_{k<r1} F_k + [r2·Σ_{r1≤k<r2} F_k − Σ_{r1≤k<r2} D_k] / (r2 − r1), com r1 < r2 inteiros (km).
    """

    def __init__(self, F, D):
        z = np.zeros(F.shape[:2] + (1,))
        self.CF = np.concatenate([z, np.cumsum(F, axis=2, dtype=np.float64)], axis=2)
        self.CD = np.concatenate([z, np.cumsum(D, axis=2, dtype=np.float64)], axis=2)

    def col(self, j, r1, r2):
        r1, r2 = int(r1), int(r2)
        f_rg = self.CF[:, j, r2] - self.CF[:, j, r1]
        d_rg = self.CD[:, j, r2] - self.CD[:, j, r1]
        return self.CF[:, j, r1] + (r2 * f_rg - d_rg) / (r2 - r1)


def cobertura_gulosa(h, li, W, V, meta=1.0, ganho_min=0.0):
    """Cobertura máxima gulosa com avaliação preguiçosa (CELF), cada resíduo contado uma vez.

    h, li: pares hub–local ORDENADOS por h; W: (P, m) peso w de cada par por coluna; V: (NL, m) oferta.
    O ganho de um hub é o resíduo que ele cobre A MAIS (Σ oferta × aumento de w). Para ao atingir `meta`
    (fração da oferta) ou quando o melhor ganho marginal fica abaixo de `ganho_min` (Nm³ CH4/dia).
    Devolve (hubs selecionados, cobertura acumulada, cur = w obtido por local e coluna).
    """
    import heapq

    cur = np.zeros(V.shape, dtype=np.float64)
    total = float(V.sum())
    if total <= 0 or len(h) == 0:
        return [], np.array([]), cur
    hu, st, ct = np.unique(h, return_index=True, return_counts=True)
    g0 = np.add.reduceat((V[li] * W).sum(axis=1), st)
    heap = [(-g, k) for k, g in enumerate(g0)]
    heapq.heapify(heap)
    cob, sel, curva = 0.0, [], []
    while heap and cob / total < meta:
        _, k = heapq.heappop(heap)
        s = slice(st[k], st[k] + ct[k])
        g = float((V[li[s]] * np.maximum(0.0, W[s] - cur[li[s]])).sum())
        if heap and g < -heap[0][0] - 1e-9:
            heapq.heappush(heap, (-g, k))
            continue
        # hub entra se o ganho for ≥ ganho_min; se o melhor não passa, nenhum passa (os limites superiores só caem)
        if g < ganho_min or g <= 1e-7 * total:
            break
        cur[li[s]] = np.maximum(cur[li[s]], W[s])
        cob += g
        sel.append(int(hu[k]))
        curva.append(cob / total)
    return sel, np.array(curva), cur


class Roteador:
    """Distância (m) de cada local de oferta ao hub viável mais próximo: Dijkstra multi-fonte (SciPy) a partir de
    uma super-fonte ligada aos nós dos hubs viáveis com peso = conexão do hub. Resíduo gerado no próprio hub
    viável (na fonte) tem d = 0."""

    def __init__(self, G, HUBS, LOC):
        self.NN = len(G["x"])
        self.EU = np.r_[G["u"], G["v"]].astype(np.int64)
        self.EV = np.r_[G["v"], G["u"]].astype(np.int64)
        self.EW = np.r_[G["comp"], G["comp"]].astype(np.float64)
        self.hnode, self.hconn = HUBS.node.to_numpy(), HUBS.conn_m.to_numpy()
        self.lnode, self.lconn = LOC.node.to_numpy(), LOC.conn_m.to_numpy()
        self.fonte = LOC.hub_fonte.to_numpy()

    def dist(self, viavel, limite_km):
        import pandas as pd
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra

        idx = np.flatnonzero(viavel)
        d = np.full(len(self.lnode), np.inf)
        if len(idx) == 0:
            return d
        c = pd.Series(self.hconn[idx]).groupby(self.hnode[idx]).min()
        rows = np.r_[self.EU, np.full(len(c), self.NN)]
        cols = np.r_[self.EV, c.index.to_numpy()]
        data = np.r_[self.EW, c.to_numpy() + 1e-6]        # +1e-6: aresta de peso zero não existe no csgraph
        A = csr_matrix((data, (rows, cols)), shape=(self.NN + 1, self.NN + 1))
        dn = dijkstra(A, directed=True, indices=self.NN, limit=limite_km * 1000.0)[:self.NN]
        d = dn[self.lnode] + self.lconn
        d[(self.fonte >= 0) & viavel[np.maximum(self.fonte, 0)]] = 0.0
        return d
