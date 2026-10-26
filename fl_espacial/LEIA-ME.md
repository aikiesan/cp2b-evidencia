# FL espacial do CP2b (fl_v5, v5.1)

Código e notas que geraram o FL espacial do CP2b v5.1, o que está no snapshot
e no artigo. Copiado de `Metodo_CP2b/fl_espacial/` em 26/10/2026, sem
alterações. Só código e texto: os dados de entrada, o cache (~3 GB) e as
saídas ficam fora do git.

## O que está aqui

| Arquivo | O que faz |
|---|---|
| `00_fabricas_suco.py` | Fábricas de suco (RAIS 1033-3/01, ≥ 100 vínculos) e base N3 com o bagaço de citros nelas (v5.1) |
| `01_grafo.py` | Grafo viário do OSM (SP + 50 km), com e sem track/service |
| `02_oferta.py` | N3 de cada substrato e cenário numa grade de 1 km, fechando com o total municipal |
| `03_hubs.py` | Hubs candidatos: usinas, ETEs não-lagoa, plantas de biogás, fábricas de suco e a grade |
| `03b_palha_usinas.py` | Raios da palha pela distância por estrada até a usina |
| `04_bacias_fl.py` | Bacias e FL por cobertura (variantes A e C) |
| `04b_alocacao.py` | FL com alocação (B, a principal, e D) e as checagens de robustez |
| `05_validacao_sensibilidade.py` | Taxa de acerto contra plantas operantes, sensibilidade a r2 e Q_min, curva MCLP |
| `06_integracao.py` | Tabelas `fl_v5_*_substrato.csv` que a cascata lê e arquivos para o banco (nada aplicado) |
| `07_reconciliacao_v5.py` | N4 v4 × v5 |
| `fl_comum.py`, `config_fl.yaml` | Funções comuns; todos os parâmetros (raios, Q_min, semente 20260923) |
| `rodar_pipeline.sh`, `ambiente.txt` | Ordem de execução e versões dos pacotes (Python 3.11) |
| `cascata_v51/` | `cp2b_cascade.py` e `cp2b_params.py` da v5.1 e o log da rodada (N4 1,883 / 5,972 / 15,577 bi Nm³ CH4/ano, igual ao snapshot); a seção de alocação do uso existente está somada por fluxo, sem os nomes dos titulares |
| `patch_v5/` | O diff v4 → v5.0 da cascata e o teste dele |
| `RELATORIO_FL_espacial.md` | O relatório da v5.1: decisões, FL por substrato, robustez, validação, limitações |
| `DECISOES_CHECKPOINT2.md`, `PROPOSTA_CHECKPOINT3_dados_CETESB.md`, `PROMPT_ClaudeCode_FL_espacial.md` | Decisões, proposta de dados e a tarefa original |

## A regra do FL

Para cada ponto de oferta (célula de 1 km, ou o local onde o resíduo nasce: usina, ETE, granja), FL = w(d) da distância por estrada até o
hub selecionado mais próximo: 1 até r1, cai em linha reta até 0 em r2. Os
hubs entram em ordem gulosa e só entram se acrescentam pelo menos Q_min de
resíduo (3.200 / 1.500 / 500 Nm³ CH4/dia no mín, med e máx), contando cada
resíduo uma vez. O FL municipal é a média dos pontos ponderada pela oferta.
Por isso o FL zera quando nenhum hub selecionado fica a menos de r2 da oferta
do município. Raios e Q_min em `config_fl.yaml`; a seleção em
`fl_comum.cobertura_gulosa`, chamada por `04b_alocacao.py`.

## Saídas de referência (fora do git)

Conferidas na máquina do Lucas em 26/10/2026 (12 primeiros caracteres do
sha256). A cópia em `Project_Twin/.../fl_espacial/outputs` é idêntica.

| Arquivo | sha256 |
|---|---|
| `outputs/fl_v5_municipio_substrato.csv` | `2a7b664b1f20` |
| `outputs/fl_v5_estado_substrato.csv` | `1bd83a1785ea` |

## Reprodução conferida (26/10/2026)

Numa cópia da pasta (`Metodo_CP2b/fl_espacial_v52/`), com o cache da v5.1 e o
`Metodo_CP2b/.venv` (pandas 2.2.3, numpy 2.2.6), `04b_alocacao.py` (1,8 min) e
`06_integracao.py` (0,1 min) geraram `fl_v5_municipio_substrato.csv`,
`fl_v5_estado_substrato.csv`, `fl_municipio_alocado.csv`, `fl_estado_alocado.csv`
e `alocacao_hubs_codigestao.csv` byte a byte iguais aos da v5.1. As etapas
00–04 (grafo, oferta, hubs, bacias) não foram refeitas: entram pelo cache.

Na mesma cópia, rodadas à parte (saídas agregadas em `../data/fl_v51/`,
relatório em `../outputs/fl_espacial/`):

- C02: `oferta_wide.pkl` com o bagaço escalado pelo BMP proposto e o `04b` de
  novo (2,9 min, outra cópia, `fl_espacial_v52_C02/`). Os pares em cache
  continuam válidos, porque a assinatura é dos nós, não da oferta.
- Municípios zerados: distância por estrada de cada ponto de oferta ao hub
  selecionado mais próximo (`fl_comum.Roteador`, limite de 150 km), contra o
  r2 da classe.

Cuidado ao rodar: `06_integracao.py` grava em `integracao.saida_v5`, que no
config aponta para a pasta da v5.1 (`Metodo_CP2b/outputs_v5`). Numa cópia,
troque esse caminho antes.

## Para rodar de novo

Não roda neste repositório como está. Os caminhos de `config_fl.yaml` e de
`cascata_v51/` são absolutos da máquina onde o método foi feito, e as entradas
não estão no git:

- N3 da cascata v4 (`cp2b_municipio_substrato.csv`, `cp2b_atividade_municipal.csv`, `cp2b_usinas_alocacao.csv`);
- malha viária OSM Geofabrik Sudeste (jan/2026) e municípios SP 2024;
- MapBiomas 10.1 (usinas de etanol, plantas de biogás, uso agropecuário 2024 e 2ª safra, áreas protegidas e terras indígenas);
- plantas de biogás do PILAR-2b e da ANP, ETEs 2019 e áreas urbanas;
- RAIS local (CNAEs prioritários), GEDAVE aves e bovinos, granjas de suínos;
- `feedstocks.yaml` do PILAR-2b.

Os cadastros GEDAVE e a RAIS trazem dados de pessoas e estabelecimentos e não
entram aqui em hipótese nenhuma; o código lê só as colunas listadas em
`config_fl.yaml` (`bovinos_colunas_lgpd`). A rodada completa leva ~1h40 do
zero (~45 min com o grafo em cache), segundo o relatório.
