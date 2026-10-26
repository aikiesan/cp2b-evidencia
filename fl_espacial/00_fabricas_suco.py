#!/usr/bin/env python3
"""Etapa 0 (v5.1) — fábricas de suco concentrado e base N3 com o bagaço de citros nas fábricas.

O bagaço de laranja é resíduo da extração do suco: nasce na fábrica, não no pomar. Até a v5.0 ele era espacializado
nos pixels de citros (limitação 2 do relatório); a partir da v5.1 nasce nas fábricas, como vinhaça, torta e bagaço
de cana nas usinas.

1. Fábricas: RAIS local (staging de DADOS_ESPACIAIS), CNAE 1033-3/01 (fabricação de sucos concentrados de frutas,
   hortaliças e legumes), estabelecimentos com ≥ vinculos_min vínculos ativos. Saem os estabelecimentos em municípios
   sem laranja na PAM 2024 (escritórios em São Paulo, terminais portuários em Santos e Guarujá). Peso do município =
   vínculos ÷ total. A RAIS local não tem ano nem CNPJ: entra só como peso agregado por município.
2. Base N3: linhas da cascata v4 (n3_municipal_v4) com BAGACO_CITROS redistribuído — total estadual de cada nível ×
   peso do município. É exato: g, ST, SV, BMP, FC, FCo e FS do citros são estaduais e não há uso existente (U = 0),
   então equivale a rodar a cascata com A = laranja da PAM (total SP) × peso (o que cp2b_cascade.py v5.1 faz).

Saídas: outputs/fabricas_suco_alocacao.csv (lida por 02_oferta.py e por cp2b_cascade.py),
        outputs/fabricas_suco_estabelecimentos.csv (seleção, com o motivo de cada exclusão),
        outputs/n3_base_v51.csv (= n3_municipal; formato da v4)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import fl_comum as C

log = C.logger("00_fabricas_suco")
CF = C.CFG
FS_ = CF["fabricas_suco"]
COD = "BAGACO_CITROS"

# ---------------------------------------------------------------------------
# 1. Fábricas
# ---------------------------------------------------------------------------
with C.etapa(log, f"Fábricas de suco: RAIS {FS_['cnae_subclasse']}, ≥ {FS_['vinculos_min']} vínculos"):
    R = pd.read_csv(C.caminho("rais_staging"), dtype=str)
    R = R[R.cnae_subclasse_7 == FS_["cnae_subclasse"]].copy()
    R["vinculos"] = pd.to_numeric(R.qtd_vinculos_ativos, errors="coerce").fillna(0)
    mun = C.municipios()[["ibge", "municipio"]]
    i6 = dict(zip(mun.ibge // 10, mun.ibge))
    R["ibge"] = R.municipio_ibge_6.astype(int).map(i6)
    atv = pd.read_csv(C.caminho("atividade_v4"), usecols=["ibge", "laranja_t"]).set_index("ibge").laranja_t
    R["laranja_pam_t"] = R.ibge.map(atv).fillna(0)
    R["motivo_exclusao"] = np.select(
        [R.ibge.isna(), R.vinculos < FS_["vinculos_min"], R.laranja_pam_t <= 0],
        ["município fora de SP", f"< {FS_['vinculos_min']} vínculos",
         "município sem laranja na PAM 2024 (escritório ou terminal portuário)"], default="")
    R["municipio"] = R.ibge.map(dict(zip(mun.ibge, mun.municipio)))
    R[["pilar_id_staging", "cnae_formatado", "ibge", "municipio", "cep_8", "vinculos", "tamanho_estabelecimento",
       "laranja_pam_t", "motivo_exclusao"]].sort_values("vinculos", ascending=False).to_csv(
        C.OUT / "fabricas_suco_estabelecimentos.csv", index=False, encoding="utf-8-sig")
    S = R[R.motivo_exclusao == ""]
    F = (S.groupby(["ibge", "municipio"], as_index=False)
         .agg(n_estabelecimentos=("vinculos", "size"), vinculos=("vinculos", "sum"), laranja_pam_t=("laranja_pam_t", "first")))
    F["w"] = F.vinculos / F.vinculos.sum()
    F = F.sort_values("w", ascending=False)
    F.to_csv(C.OUT / "fabricas_suco_alocacao.csv", index=False, encoding="utf-8-sig")
    log.info(f"  {len(R)} estabelecimentos na subclasse ({R.vinculos.sum():,.0f} vínculos); selecionados {len(S)} "
             f"({S.vinculos.sum() / R.vinculos.sum():.1%} dos vínculos) em {len(F)} municípios")
    log.info("  exclusões: " + "; ".join(f"{k}: {v}" for k, v in R.loc[R.motivo_exclusao != "", "motivo_exclusao"]
                                          .value_counts().items()))
    log.info("  excluídos com ≥ mínimo de vínculos: " + ", ".join(
        f"{m} ({v:.0f})" for m, v in R.loc[(R.vinculos >= FS_["vinculos_min"]) & (R.motivo_exclusao != ""),
                                          ["municipio", "vinculos"]].itertuples(index=False)))
    log.info("  peso por município:\n" + F[["municipio", "n_estabelecimentos", "vinculos", "w"]].round(4).to_string(index=False))

# ---------------------------------------------------------------------------
# 2. Base N3 (formato da v4) com o bagaço de citros nas fábricas
# ---------------------------------------------------------------------------
with C.etapa(log, "Base N3: BAGACO_CITROS redistribuído às fábricas"):
    L = pd.read_csv(C.caminho("n3_municipal_v4"))
    aditivas = [c for c in L.columns if c.endswith(("_CH4", "_biogas_eq", "_biometano_eq"))]
    constantes = ["FSxFL", "y_CH4_biogas"]
    m = (L.codigo == COD).to_numpy()
    cit = L[m]
    for c in constantes:     # a realocação só é exata se estes fatores não variam entre municípios
        assert cit.groupby("cenario")[c].nunique().max() == 1, f"{COD}: {c} varia entre municípios"
    assert float(cit[["U_CH4", "U_efetivo_CH4"]].abs().max().max()) == 0.0, f"{COD}: há uso existente alocado"
    wmap = F.set_index("ibge").w
    tot = cit.groupby("cenario")[aditivas].sum()
    w = cit.ibge.map(wmap).fillna(0.0).to_numpy()
    L.loc[m, aditivas] = tot.loc[cit.cenario].to_numpy() * w[:, None]
    novo = L[m].groupby("cenario")[aditivas].sum()
    dif = float(((novo - tot).abs() / tot.where(tot > 0)).max().max())
    log.info(f"  total estadual preservado: desvio relativo máx {dif:.1e}; municípios com N3 de citros: "
             f"{int((cit.groupby('ibge').L3_CH4.sum() > 0).sum())} (pomares) → {int((w > 0).sum() / 3)} (fábricas)")
    assert dif < 1e-12
    L.to_csv(C.caminho("n3_municipal"), index=False, encoding="utf-8-sig")
    log.info(f"  gravado: {C.caminho('n3_municipal')}")
log.info("Etapa 0 concluída.")
