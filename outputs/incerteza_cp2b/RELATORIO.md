# Incerteza do N4 do CP2b v5.1 e estabilidade do ranking municipal

> Níveis: cp2b_municipio_substrato_niveis.csv (sha256 conferido) · Parâmetros: CP2b v5.1, cp2b_parametros.csv (sha256 conferido).
> 5000 sorteios, semente 20261023; volumes em milhões de Nm³ de CH₄ por ano. Cada parâmetro é sorteado numa triangular (mín, med, máx) do próprio CP2b, independente dos outros, e a cascata é refeita município a município. Nada aqui muda a plataforma.

## 1. Quanto o N4 do estado pode variar

| Nível | CP2b med | p5 | p50 | p95 |
|---|---:|---:|---:|---:|
| N1 | 23.642,6 | 20.931,0 | 23.744,7 | 26.904,8 |
| N2 | 15.207,6 | 13.009,9 | 15.111,8 | 17.540,3 |
| N3a | 7.230,4 | 6.406,5 | 7.303,7 | 8.442,2 |
| N3 | 7.001,9 | 6.179,8 | 7.082,6 | 8.214,8 |
| N4 | 5.971,7 | 5.192,2 | 5.974,1 | 6.941,4 |

Intervalo de 90 % do N4: 5.192,2–6.941,4 mi (-13,1 % a +16,2 % do med). Faixa mín–máx do CP2b, com todos os parâmetros juntos no mínimo ou no máximo: 1.882,6–15.576,9 mi. As duas são os dois limites: parâmetros independentes e parâmetros que andam todos juntos.

| Substrato | CP2b med | p5 | p95 | Amplitude p5–p95 / med |
|---|---:|---:|---:|---:|
| PALHA | 2.428,7 | 1.942,9 | 3.378,3 | 59 % |
| TORTA_FILTRO | 847,3 | 587,2 | 1.117,3 | 63 % |
| VINHACA | 809,7 | 688,8 | 861,7 | 21 % |
| BAGACO | 792,3 | 463,6 | 1.119,1 | 83 % |
| AVES_CORTE | 255,1 | 184,3 | 342,9 | 62 % |
| PALHA_MILHO | 187,0 | 91,7 | 217,3 | 67 % |
| PALHA_SOJA | 178,0 | 99,8 | 232,9 | 75 % |
| RSU_ORGANICO | 153,6 | 69,1 | 251,2 | 119 % |
| AVES_POSTURA | 104,9 | 66,1 | 134,4 | 65 % |
| BOV_CONFINADO | 55,6 | 32,9 | 69,2 | 65 % |
| LODO_ETE | 43,0 | 24,4 | 71,5 | 110 % |
| BAGACO_CITROS | 36,0 | 22,0 | 61,4 | 109 % |
| BOV_LEITE | 23,7 | 14,0 | 37,7 | 100 % |
| PODA_URBANA | 23,4 | 10,4 | 45,5 | 150 % |
| CASCA_CAFE | 17,8 | 13,9 | 24,2 | 58 % |
| SUINOS | 15,5 | 8,3 | 21,7 | 86 % |
| BOV_PASTO_MISTO | 0,0 | 0,0 | 0,0 | — |

## 2. Quais parâmetros pesam (tornado)

Cada linha põe um parâmetro no mínimo e no máximo do CP2b, com todos os outros na mediana. A última coluna é a parcela de primeira ordem da variância do N4 nos sorteios: a inclinação entre os dois extremos ao quadrado vezes a variância da triangular do parâmetro, sobre a variância do N4. Somadas, as parcelas dão 95 %; o resto vem da interação entre parâmetros do mesmo substrato.

| Substrato | Parâmetro | mín–med–máx | N4 no mín | N4 no máx | Amplitude | % da variância |
|---|---|---|---:|---:|---:|---:|
| PALHA | BMP | 140,000–175,000–250,000 | 5.483,8 | 7.018,9 | 25,7 % | 36,4 |
| PALHA | FC | 0,350–0,400–0,500 | 5.666,4 | 6.582,6 | 15,3 % | 12,9 |
| BAGACO | FCo | 0,050–0,100–0,150 | 5.572,9 | 6.373,9 | 13,4 % | 9,5 |
| PALHA | SV | 0,720–0,820–0,920 | 5.673,8 | 6.269,7 | 10,0 % | 5,3 |
| TORTA_FILTRO | BMP | 200,000–280,000–380,000 | 5.727,5 | 6.279,0 | 9,2 % | 4,5 |
| PALHA | g | 0,120–0,140–0,150 | 5.622,9 | 6.146,2 | 8,8 % | 4,2 |
| BAGACO | BMP | 115,000–165,000–220,000 | 5.729,6 | 6.239,9 | 8,5 % | 3,9 |
| TORTA_FILTRO | ST | 0,280–0,380–0,480 | 5.746,7 | 6.198,1 | 7,6 % | 3,0 |
| PALHA | FCo | 0,800–0,900–0,950 | 5.700,2 | 6.107,5 | 6,8 % | 2,5 |
| PALHA | FL | 0,780–0,850–0,920 | 5.771,7 | 6.171,7 | 6,7 % | 2,4 |
| PALHA | FS | 0,850–0,920–0,970 | 5.786,9 | 6.103,7 | 5,3 % | 1,5 |
| TORTA_FILTRO | g | 0,030–0,035–0,040 | 5.849,1 | 6.094,6 | 4,1 % | 0,9 |
| TORTA_FILTRO | SV | 0,680–0,800–0,900 | 5.843,0 | 6.079,2 | 4,0 % | 0,8 |
| BAGACO | ST | 0,500–0,589–0,660 | 5.850,5 | 6.068,7 | 3,7 % | 0,7 |
| VINHACA | direto | 57,000–65,550–74,100 | 5.864,6 | 6.079,0 | 3,6 % | 0,7 |
| RSU_ORGANICO | BMP | 170,000–270,000–360,000 | 5.880,6 | 6.074,2 | 3,2 % | 0,6 |
| BAGACO | SV | 0,765–0,900–0,970 | 5.851,3 | 6.034,3 | 3,1 % | 0,5 |
| AVES_CORTE | BMP | 200,000–280,000–360,000 | 5.898,5 | 6.045,1 | 2,5 % | 0,3 |
| BAGACO | g | 0,250–0,280–0,300 | 5.885,5 | 6.029,2 | 2,4 % | 0,3 |
| AVES_CORTE | g | 0,035–0,045–0,060 | 5.914,7 | 6.057,3 | 2,4 % | 0,3 |

Os outros 105 parâmetros estão em `tornado.csv`.

## 3. Estabilidade do ranking municipal

Nos sorteios, 44 dos 50 maiores municípios ficam no top 50 em pelo menos 90 % das vezes. Spearman do ranking inteiro contra o med: mediana 0,998, p5 0,994.

| # | Município | Região intermediária | N4 med | Rank p5–p95 | P(top 50) |
|---:|---|---|---:|---|---:|
| 1 | Guaíra | Ribeirão Preto | 117,70 | 1–1 | 100 % |
| 2 | Morro Agudo | Ribeirão Preto | 100,47 | 2–2 | 100 % |
| 3 | Sertãozinho | Ribeirão Preto | 91,54 | 3–3 | 100 % |
| 4 | Pontal | Ribeirão Preto | 80,47 | 4–5 | 100 % |
| 5 | Pitangueiras | Ribeirão Preto | 75,10 | 5–6 | 100 % |
| 6 | Valparaíso | Araçatuba | 69,63 | 6–7 | 100 % |
| 7 | Novo Horizonte | São José do Rio Preto | 67,10 | 7–8 | 100 % |
| 8 | Ariranha | São José do Rio Preto | 62,25 | 7–13 | 100 % |
| 9 | Pirassununga | Araraquara | 61,51 | 8–11 | 100 % |
| 10 | Paraguaçu Paulista | Marília | 59,65 | 8–11 | 100 % |
| 11 | Junqueirópolis | Presidente Prudente | 57,84 | 10–14 | 100 % |
| 12 | Jaboticabal | Ribeirão Preto | 54,56 | 9–17 | 100 % |
| 13 | Araras | Campinas | 54,30 | 11–14 | 100 % |
| 14 | Tarumã | Marília | 53,10 | 13–18 | 100 % |
| 15 | Pradópolis | Ribeirão Preto | 51,62 | 14–22 | 100 % |
| 16 | São Paulo | São Paulo | 50,92 | 4–76 | 86 % |
| 17 | São Joaquim da Barra | Ribeirão Preto | 50,69 | 16–19 | 100 % |
| 18 | Catanduva | São José do Rio Preto | 50,37 | 14–24 | 100 % |
| 19 | Batatais | Ribeirão Preto | 50,14 | 14–20 | 100 % |
| 20 | São Manuel | Bauru | 49,66 | 15–20 | 100 % |

Na fronteira do top 50 (entre 10 % e 90 % de chance): São Paulo (86 %); Palestina (82 %); Orindiúva (72 %); Buritizal (54 %); Paulicéia (58 %); Serrana (46 %); Macatuba (13 %); Meridiano (24 %); Lins (52 %); Brotas (30 %); Sebastianópolis do Sul (14 %); Colômbia (45 %); Rancharia (30 %).

Nos cenários de literatura da sensibilidade (valor central):

| Cenário | Top 10 mantidos | Top 50 mantidos | Spearman | Maiores mudanças no top 50 |
|---|---:|---:|---:|---|
| leite_g | 10 | 50 | 0,999 | Mirante do Paranapanema 40→35; Guaiçara 25→26; Jaboticabal 12→13 |
| leite_fc1 | 10 | 50 | 1,000 | Guaiçara 25→26; Mococa 39→40; Piracicaba 26→25 |
| confinado_ms | 10 | 50 | 1,000 | Barretos 27→32; Pereira Barreto 44→46; Sandovalina 31→29 |
| confinado_fc | 10 | 50 | 1,000 | Guaiçara 25→27; Barretos 27→25; Itápolis 36→34 |
| pasto_g | 10 | 50 | 1,000 | Orindiúva 47→47; Olímpia 21→21; Sertãozinho 3→3 |
| citros_fco | 10 | 49 | 1,000 | Colina 42→54; Araraquara 32→38; Catanduva 18→20 |
| palha_fs | 9 | 47 | 0,998 | Barretos 27→44; Itápolis 36→52; Serrana 50→38 |
| bagaco_bmp | 10 | 48 | 1,000 | Barretos 27→35; Palestina 46→54; Paulicéia 49→43 |
| soja_bmp | 10 | 50 | 0,999 | Mococa 39→42; Paulicéia 49→47; Cerqueira César 38→40 |
| literatura_g_total | 9 | 45 | 0,996 | Barretos 27→59; Itápolis 36→62; Araraquara 32→48 |
| literatura_g_coletavel | 9 | 45 | 0,997 | Barretos 27→59; Itápolis 36→62; Araraquara 32→48 |

Por região intermediária do IBGE:

| Região | % do N4 | N4 med | p5 | p95 | Amplitude p5–p95 / med |
|---|---:|---:|---:|---:|---:|
| Ribeirão Preto | 23,9 | 1.429,1 | 1.235,1 | 1.702,5 | 33 % |
| São José do Rio Preto | 16,8 | 1.005,6 | 874,7 | 1.187,6 | 31 % |
| Campinas | 9,6 | 571,3 | 501,3 | 650,1 | 26 % |
| Bauru | 9,2 | 546,5 | 475,0 | 641,1 | 30 % |
| Araçatuba | 8,9 | 528,7 | 456,7 | 631,7 | 33 % |
| Marília | 8,3 | 493,0 | 420,7 | 551,5 | 27 % |
| Presidente Prudente | 7,6 | 451,1 | 389,2 | 533,5 | 32 % |
| Araraquara | 7,3 | 438,7 | 379,8 | 529,7 | 34 % |
| Sorocaba | 6,8 | 406,8 | 338,3 | 438,6 | 25 % |
| São Paulo | 1,5 | 88,4 | 42,7 | 148,3 | 120 % |
| São José dos Campos | 0,2 | 12,5 | 8,6 | 16,9 | 67 % |

## 4. Conferência

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
| modelo reproduz o mín e o máx do snapshot por substrato (±1 %) | não | AVES_CORTE min ×1,704; AVES_POSTURA min ×1,744; BAGACO min ×1,022; BAGACO_CITROS min ×1,405; BOV_CONFINADO min ×2,247; BOV_LEITE min ×8,369; CASCA_CAFE min ×11,488; LODO_ETE min ×1,768; PALHA min ×1,093; PALHA_MILHO min ×3,166; PALHA_SOJA min ×3,839; PODA_URBANA min ×1,639; RSU_ORGANICO min ×1,572; SUINOS min ×10,081; TORTA_FILTRO min ×0,986; VINHACA min ×1,071; AVES_CORTE max ×1,044; AVES_POSTURA max ×1,029; BAGACO max ×1,087; BAGACO_CITROS max ×1,132; BOV_CONFINADO max ×1,282; BOV_LEITE max ×0,390; BOV_PASTO_MISTO max ×0,000; CASCA_CAFE max ×0,895; LODO_ETE max ×0,895; PALHA_MILHO max ×0,948; PALHA_SOJA max ×1,064; PODA_URBANA max ×1,142; RSU_ORGANICO max ×1,042; SUINOS max ×0,705; TORTA_FILTRO max ×1,080; VINHACA max ×0,886 |

Onde o modelo não reproduz o snapshot, o CP2b varia algo que não está em `cp2b_parametros.csv` como multiplicador (a base, ou o FL espacial de cada município). Nesses substratos o intervalo acima é o dos parâmetros, não o do CP2b inteiro. Detalhe em `conferencia_modelo.csv`.

Elementos do arquivo de parâmetros não sorteados: u (usos excludentes) / notas.

## Como ler

- O intervalo de 90 % supõe parâmetros independentes. Parâmetros com a mesma fonte (por exemplo o FC de vários rebanhos) andam juntos na vida real; por isso o intervalo verdadeiro fica entre este e a faixa mín–máx do CP2b, mais perto deste quanto mais independentes forem as fontes.
- A triangular dá peso à mediana do CP2b. Ela não diz que a mediana está certa: a sensibilidade (`outputs/sensibilidade_cp2b/`) é que testa a mediana contra a literatura.
- U e o FL espacial de cada município ficam como estão no med; só o multiplicador do FL do arquivo de parâmetros, quando existe, é sorteado.
- Rank 1 = maior N4 municipal (soma dos substratos). Cenários de definição ficam fora do ranking, porque não são leituras possíveis do CP2b.
