# CP2b v5.2 em construção: o que cada mudança faz no N4

> Níveis: cp2b_municipio_substrato_niveis.csv (sha256 conferido) · Parâmetros: CP2b v5.1, cp2b_parametros.csv (sha256 conferido).
> Volumes em milhões de Nm³ de CH₄ por ano. O modelo de `build_incerteza_cp2b.py` (que reproduz o snapshot v5.1 linha a linha) com os parâmetros de `v52/mudancas.csv` no lugar dos da v5.1. O FL espacial acompanha o N3 de cada município; o modelo do FL não é refeito. Nada aqui muda a plataforma.

## 1. Mudanças

| Id | Status | Substrato | Elemento | v5.1 mín–med–máx | v5.2 mín–med–máx | Registros (tier) | Decisão |
|---|---|---|---|---|---|---|---|
| C01 | candidata | PALHA | FS | 0,85–0,92–0,97 | 0,31–0,67–0,97 | FDE-20261017-19 (B) | — |
| C02 | candidata | BAGACO | BMP | 115–165–220 | 125–241,3–326 | BMP-20261017-01; BMP-20261017-02; BMP-20261017-03 (B; B; C) | — |

Justificativas:

- **C01**: Massa da palha que resta após a decomposição no solo (Embrapa): 0,67 com cerca de um mês no campo antes do enfardamento (med) e 0,31 após um ano (mín). O registro diz que enfardar logo evita a perda; o máx fica o da v5.1. Depende da resposta do time sobre o tempo entre colheita e enfardamento.
- **C02**: BMP bruto medido do bagaço: 326 (tier B, doi 10.3390/ijms160920685), 125 (tier B, doi 10.3390/su17030892, base STP não confirmada) e 273 (tier C, Embrapa Alice doc/1158431). Med = média dos três; mín e máx = os extremos. Registros tier B e C: pedir um tier A antes de aceitar.

## 2. N4 do estado

v5.1: 5.971,7 mi no med; faixa do snapshot 1.882,6–15.576,9.

| Conjunto | N3 med | N4 med | ΔN4 med | N4 mín | N4 máx | N4 p5–p95 | Top 10 | Top 50 | Spearman |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| v5.1, sem mudanças | 7.001,9 | 5.971,7 | 0,0 % | 1.882,6 | 15.576,9 | 5.130,2–6.894,9 | 10 | 50 | 1,000 |
| C01 sozinha (candidata) | 7.001,9 | 5.311,7 | -11,1 % | 1.323,8 | 15.576,9 | — | 9 | 47 | 0,998 |
| C02 sozinha (candidata) | 7.385,4 | 6.317,5 | +5,8 % | 1.895,7 | 16.635,0 | — | 10 | 48 | 1,000 |
| v5.2 com aceitas e candidatas | 7.385,4 | 5.657,5 | -5,3 % | 1.337,0 | 16.635,0 | 4.544,0–6.547,8 | 9 | 46 | 0,997 |

## 3. Por substrato (v5.2 com aceitas e candidatas, med)

| Substrato | N4 v5.1 | N4 v5.2 | Δ |
|---|---:|---:|---:|
| PALHA | 2.428,7 | 1.768,7 | -27,2 % |
| BAGACO | 792,3 | 1.138,1 | +43,6 % |
| TORTA_FILTRO | 847,3 | 847,3 | 0,0 % |
| VINHACA | 809,7 | 809,7 | 0,0 % |
| AVES_CORTE | 255,1 | 255,1 | 0,0 % |
| PALHA_MILHO | 187,0 | 187,0 | 0,0 % |
| PALHA_SOJA | 178,0 | 178,0 | 0,0 % |
| RSU_ORGANICO | 153,6 | 153,6 | 0,0 % |
| AVES_POSTURA | 104,9 | 104,9 | 0,0 % |
| BOV_CONFINADO | 55,6 | 55,6 | 0,0 % |
| LODO_ETE | 43,0 | 43,0 | 0,0 % |
| BAGACO_CITROS | 36,0 | 36,0 | 0,0 % |
| BOV_LEITE | 23,7 | 23,7 | 0,0 % |
| PODA_URBANA | 23,4 | 23,4 | 0,0 % |
| CASCA_CAFE | 17,8 | 17,8 | 0,0 % |
| SUINOS | 15,5 | 15,5 | 0,0 % |

## 4. Ranking municipal (v5.2 com aceitas e candidatas)

Entram no top 50: Meridiano 52→40; Sebastianópolis do Sul 55→41; Américo Brasiliense 57→45; Macatuba 51→50.
Saem do top 50: Barretos 27→54; Jaú 45→55; Palestina 46→58; Itápolis 36→60.

| # v5.2 | Município | Região | N4 v5.1 | N4 v5.2 | Δ | # v5.1 |
|---:|---|---|---:|---:|---:|---:|
| 1 | Guaíra | Ribeirão Preto | 117,70 | 120,70 | +2,6 % | 1 |
| 2 | Sertãozinho | Ribeirão Preto | 91,54 | 98,57 | +7,7 % | 3 |
| 3 | Morro Agudo | Ribeirão Preto | 100,47 | 95,31 | -5,1 % | 2 |
| 4 | Pontal | Ribeirão Preto | 80,47 | 85,02 | +5,7 % | 4 |
| 5 | Pitangueiras | Ribeirão Preto | 75,10 | 77,09 | +2,6 % | 5 |
| 6 | Ariranha | São José do Rio Preto | 62,25 | 69,82 | +12,2 % | 8 |
| 7 | Valparaíso | Araçatuba | 69,63 | 67,32 | -3,3 % | 6 |
| 8 | Novo Horizonte | São José do Rio Preto | 67,10 | 67,18 | +0,1 % | 7 |
| 9 | Pirassununga | Araraquara | 61,51 | 65,99 | +7,3 % | 9 |
| 10 | Junqueirópolis | Presidente Prudente | 57,84 | 61,93 | +7,1 % | 11 |
| 11 | Paraguaçu Paulista | Marília | 59,65 | 58,91 | -1,2 % | 10 |
| 12 | Tarumã | Marília | 53,10 | 55,28 | +4,1 % | 14 |
| 13 | Pradópolis | Ribeirão Preto | 51,62 | 54,90 | +6,3 % | 15 |
| 14 | Catanduva | São José do Rio Preto | 50,37 | 54,49 | +8,2 % | 18 |
| 15 | Araras | Campinas | 54,30 | 53,23 | -2,0 % | 13 |
| 16 | São Joaquim da Barra | Ribeirão Preto | 50,69 | 52,00 | +2,6 % | 17 |
| 17 | São Paulo | São Paulo | 50,92 | 50,92 | 0,0 % | 16 |
| 18 | Jaboticabal | Ribeirão Preto | 54,56 | 49,23 | -9,8 % | 12 |
| 19 | São Manuel | Bauru | 49,66 | 46,96 | -5,4 % | 20 |
| 20 | Batatais | Ribeirão Preto | 50,14 | 46,88 | -6,5 % | 19 |

## 5. Conferência

| Checagem | Resultado | Detalhe |
|---|---|---|
| total do estado N3 min | ok | 2.821,9 mi (loader 2.821,9) |
| total do estado N1 med | ok | 23.642,6 mi (loader 23.642,6) |
| total do estado N2 med | ok | 15.207,6 mi (loader 15.207,6) |
| total do estado N3 med | ok | 7.001,9 mi (loader 7.001,9) |
| total do estado N4 med | ok | 5.971,7 mi (loader 5.971,7) |
| total do estado N3 max | ok | 16.410,6 mi (loader 16.410,6) |
| N3 = máx(N3a − U, 0) em cada linha | ok | 0 linhas fora de 32895 |
| N4 = N3 × FS × FL em cada linha | ok | 0 linhas fora de 32895 |
| modelo reproduz mín, med e máx do snapshot por substrato (±0,1 %) | ok | maior desvio 0,000 % |
| U = mín(uso existente, N3a) em cada linha e cenário (informativo: o modelo interpola o U) | vale | 0 linhas fora; 0,00 % do U |
| v5.1 sem mudanças reproduz o N4 do snapshot no mín, med e máx (±0,01 %) | ok | 1.882,6 · 5.971,7 · 15.576,9 mi |
| toda linha de mudancas.csv é lida, confere com a v5.1 e entra no modelo | ok | 2 mudanças |

## Como ler

- Uma mudança candidata não é a v5.2: o relatório mostra o tamanho dela para o time decidir. Só as aceitas, com a decisão escrita, vão para o PILAR-2b depois da submissão.
- O p5–p95 usa os mesmos sorteios (mesma semente) da incerteza da v5.1; a linha v5.1 reproduz `outputs/incerteza_cp2b/`. A diferença entre as linhas é a mudança, não o sorteio.
- 20000 sorteios por conjunto com p5–p95; mudanças sozinhas só no med, mín e máx.
- Top 10, top 50 e Spearman comparam o ranking do med de cada conjunto com o da v5.1.
- O FL espacial de cada município é interpolado no N3 dele, como na incerteza. Uma mudança que mexe muito no N3 de um município pequeno pode abrir ou fechar um hub que o fl_v5 trataria de outro jeito.
