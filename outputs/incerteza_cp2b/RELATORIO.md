# Incerteza do N4 do CP2b v5.1 e estabilidade do ranking municipal

> Níveis: cp2b_municipio_substrato_niveis.csv (sha256 conferido) · Parâmetros: CP2b v5.1, cp2b_parametros.csv (sha256 conferido).
> 20000 sorteios, semente 20261023; volumes em milhões de Nm³ de CH₄ por ano. Cada parâmetro é sorteado numa triangular (mín, med, máx) do próprio CP2b, independente dos outros, e a cascata é refeita município a município. O FL espacial acompanha o N3 de cada município, o U acompanha o N3a, e o que o snapshot varia fora do arquivo de parâmetros entra como fator residual. Com tudo no mín, med ou máx, o modelo reproduz o snapshot linha a linha (seção 4). Nada aqui muda a plataforma.

## 1. Quanto o N4 do estado pode variar

| Nível | CP2b med | p5 | p50 | p95 |
|---|---:|---:|---:|---:|
| N1 | 23.642,6 | 20.790,6 | 23.666,5 | 26.878,5 |
| N2 | 15.207,6 | 12.943,2 | 15.090,7 | 17.466,8 |
| N3a | 7.230,4 | 6.437,9 | 7.335,8 | 8.446,1 |
| N3 | 7.001,9 | 6.229,4 | 7.122,4 | 8.229,1 |
| N4 | 5.971,7 | 5.130,2 | 5.941,3 | 6.894,9 |

Intervalo de 90 % do N4: 5.130,2–6.894,9 mi (-14,1 % a +15,5 % do med). Faixa mín–máx do CP2b, com todos os parâmetros juntos no mínimo ou no máximo: 1.882,6–15.576,9 mi. As duas são os dois limites: parâmetros independentes e parâmetros que andam todos juntos.

| Substrato | CP2b med | p5 | p95 | Amplitude p5–p95 / med |
|---|---:|---:|---:|---:|
| PALHA | 2.428,7 | 1.887,5 | 3.397,3 | 62 % |
| TORTA_FILTRO | 847,3 | 602,8 | 1.092,8 | 58 % |
| VINHACA | 809,7 | 685,6 | 891,0 | 25 % |
| BAGACO | 792,3 | 471,0 | 1.099,9 | 79 % |
| AVES_CORTE | 255,1 | 155,1 | 338,8 | 72 % |
| PALHA_MILHO | 187,0 | 62,3 | 219,0 | 84 % |
| PALHA_SOJA | 178,0 | 67,7 | 230,2 | 91 % |
| RSU_ORGANICO | 153,6 | 78,0 | 246,3 | 110 % |
| AVES_POSTURA | 104,9 | 53,7 | 131,2 | 74 % |
| BOV_CONFINADO | 55,6 | 23,4 | 67,3 | 79 % |
| LODO_ETE | 43,0 | 19,7 | 74,2 | 127 % |
| BAGACO_CITROS | 36,0 | 19,2 | 60,1 | 114 % |
| BOV_LEITE | 23,7 | 8,1 | 49,5 | 175 % |
| PODA_URBANA | 23,4 | 7,9 | 44,0 | 155 % |
| CASCA_CAFE | 17,8 | 9,3 | 24,9 | 88 % |
| SUINOS | 15,5 | 4,4 | 23,2 | 121 % |
| BOV_PASTO_MISTO | 0,0 | 2,1 | 76,1 | — |

Med zero no CP2b, escalados a partir do cenário máx: BOV_PASTO_MISTO. O p95 deles mostra quanto o máx do CP2b pesa quando o FC (ou outro fator) deixa de ser zero.

## 2. Quais parâmetros pesam (tornado)

Cada linha põe um parâmetro no mínimo e no máximo do CP2b, com todos os outros na mediana. A última coluna é a parcela de primeira ordem da variância do N4 nos sorteios: a inclinação entre os dois extremos ao quadrado vezes a variância da triangular do parâmetro, sobre a variância do N4. Somadas, as parcelas dão 99 %; o resto vem da interação entre parâmetros e do FL espacial. Linhas "(snapshot)" são o que o CP2b varia fora do arquivo de parâmetros; a faixa delas é o fator médio do substrato no mín, med e máx.

| Substrato | Parâmetro | mín–med–máx | N4 no mín | N4 no máx | Amplitude | % da variância |
|---|---|---|---:|---:|---:|---:|
| PALHA | BMP | 140,000–175,000–250,000 | 5.422,7 | 7.030,0 | 26,9 % | 39,3 |
| PALHA | FC | 0,350–0,400–0,500 | 5.624,9 | 6.588,3 | 16,1 % | 14,0 |
| BAGACO | FCo | 0,050–0,100–0,150 | 5.585,1 | 6.344,9 | 12,7 % | 8,4 |
| PALHA | SV | 0,720–0,820–0,920 | 5.633,2 | 6.272,2 | 10,7 % | 6,0 |
| PALHA | g | 0,120–0,140–0,150 | 5.576,4 | 6.147,6 | 9,6 % | 4,9 |
| TORTA_FILTRO | BMP | 200,000–280,000–380,000 | 5.749,5 | 6.255,4 | 8,5 % | 3,7 |
| BAGACO | BMP | 115,000–165,000–220,000 | 5.740,2 | 6.222,7 | 8,1 % | 3,4 |
| PALHA | FCo | 0,800–0,900–0,950 | 5.662,8 | 6.108,5 | 7,5 % | 3,0 |
| TORTA_FILTRO | ST | 0,280–0,380–0,480 | 5.767,6 | 6.181,9 | 6,9 % | 2,5 |
| PALHA | FL | 0,780–0,850–0,920 | 5.771,7 | 6.171,7 | 6,7 % | 2,3 |
| PALHA | FS | 0,850–0,920–0,970 | 5.786,9 | 6.103,7 | 5,3 % | 1,5 |
| TORTA_FILTRO | g | 0,030–0,035–0,040 | 5.862,7 | 6.086,7 | 3,8 % | 0,7 |
| TORTA_FILTRO | SV | 0,680–0,800–0,900 | 5.857,2 | 6.072,4 | 3,6 % | 0,7 |
| BAGACO | ST | 0,500–0,589–0,660 | 5.857,3 | 6.063,5 | 3,5 % | 0,6 |
| VINHACA | direto | 57,000–65,550–74,100 | 5.870,9 | 6.072,7 | 3,4 % | 0,6 |
| RSU_ORGANICO | BMP | 170,000–270,000–360,000 | 5.885,4 | 6.071,4 | 3,1 % | 0,5 |
| VINHACA | base N1 (snapshot) | 0,917–1,000–1,147 | 5.907,4 | 6.085,3 | 3,0 % | 0,5 |
| BAGACO | SV | 0,765–0,900–0,970 | 5.858,1 | 6.031,0 | 2,9 % | 0,5 |
| AVES_CORTE | BMP | 200,000–280,000–360,000 | 5.867,8 | 6.038,9 | 2,9 % | 0,4 |
| PALHA_MILHO | BMP | 150,000–230,000–300,000 | 5.867,6 | 6.032,1 | 2,8 % | 0,4 |

Os outros 111 parâmetros estão em `tornado.csv`.

## 3. Estabilidade do ranking municipal

Nos sorteios, 44 dos 50 maiores municípios ficam no top 50 em pelo menos 90 % das vezes. Spearman do ranking inteiro contra o med: mediana 0,995, p5 0,989.

| # | Município | Região intermediária | N4 med | N4 p5–p95 | Rank p5–p95 | P(top 50) |
|---:|---|---|---:|---|---|---:|
| 1 | Guaíra | Ribeirão Preto | 117,70 | 99,92–132,39 | 1–1 | 100 % |
| 2 | Morro Agudo | Ribeirão Preto | 100,47 | 86,11–117,42 | 2–2 | 100 % |
| 3 | Sertãozinho | Ribeirão Preto | 91,54 | 76,89–104,36 | 3–3 | 100 % |
| 4 | Pontal | Ribeirão Preto | 80,47 | 68,66–90,71 | 4–5 | 100 % |
| 5 | Pitangueiras | Ribeirão Preto | 75,10 | 64,92–84,62 | 5–6 | 100 % |
| 6 | Valparaíso | Araçatuba | 69,63 | 60,71–80,81 | 6–7 | 100 % |
| 7 | Novo Horizonte | São José do Rio Preto | 67,10 | 58,29–75,71 | 7–8 | 100 % |
| 8 | Ariranha | São José do Rio Preto | 62,25 | 51,00–71,73 | 8–12 | 100 % |
| 9 | Pirassununga | Araraquara | 61,51 | 50,93–70,15 | 9–11 | 100 % |
| 10 | Paraguaçu Paulista | Marília | 59,65 | 51,51–69,11 | 8–11 | 100 % |
| 11 | Junqueirópolis | Presidente Prudente | 57,84 | 48,90–66,13 | 10–14 | 100 % |
| 12 | Jaboticabal | Ribeirão Preto | 54,56 | 46,61–65,78 | 9–17 | 100 % |
| 13 | Araras | Campinas | 54,30 | 47,87–61,84 | 12–14 | 100 % |
| 14 | Tarumã | Marília | 53,10 | 45,10–59,48 | 13–18 | 100 % |
| 15 | Pradópolis | Ribeirão Preto | 51,62 | 44,27–57,43 | 14–22 | 100 % |
| 16 | São Paulo | São Paulo | 50,92 | 33,42–82,20 | 4–48 | 96 % |
| 17 | São Joaquim da Barra | Ribeirão Preto | 50,69 | 43,64–57,65 | 16–19 | 100 % |
| 18 | Catanduva | São José do Rio Preto | 50,37 | 42,70–57,80 | 14–23 | 100 % |
| 19 | Batatais | Ribeirão Preto | 50,14 | 42,45–59,13 | 14–20 | 100 % |
| 20 | São Manuel | Bauru | 49,66 | 43,44–57,34 | 15–20 | 100 % |

Na fronteira do top 50 (entre 10 % e 90 % de chance): Mococa (88 %); Palestina (83 %); Orindiúva (73 %); Buritizal (60 %); Paulicéia (60 %); Serrana (47 %); Macatuba (16 %); Meridiano (25 %); Lins (52 %); Brotas (12 %); Sebastianópolis do Sul (13 %); Colômbia (46 %); Rancharia (32 %).

Nos cenários de literatura da sensibilidade (valor central):

| Cenário | Top 10 mantidos | Top 50 mantidos | Spearman | Maiores mudanças no top 50 |
|---|---:|---:|---:|---|
| leite_g | 10 | 49 | 0,991 | Mirante do Paranapanema 40→34; Guaraci 37→39; Palestina 46→44 |
| leite_fc1 | 10 | 50 | 0,998 | Mirante do Paranapanema 40→38; Araçatuba 30→29; Cerqueira César 38→39 |
| confinado_ms | 10 | 50 | 1,000 | Barretos 27→33; Itápolis 36→38; Pereira Barreto 44→46 |
| confinado_fc | 10 | 50 | 1,000 | Barretos 27→25; Guaiçara 25→27; Itápolis 36→35 |
| pasto_g | 10 | 50 | 1,000 |  |
| citros_fco | 10 | 49 | 1,000 | Colina 42→54; Araraquara 32→38; Catanduva 18→20 |
| palha_fs | 9 | 47 | 0,998 | Barretos 27→44; Itápolis 36→52; Serrana 50→38 |
| bagaco_bmp | 10 | 48 | 1,000 | Barretos 27→35; Palestina 46→53; Orindiúva 47→42 |
| soja_bmp | 10 | 50 | 0,997 | Cerqueira César 38→41; Maracaí 28→31; Mococa 39→42 |
| literatura_g_total | 9 | 45 | 0,984 | Barretos 27→60; Itápolis 36→62; Araraquara 32→47 |
| literatura_g_coletavel | 9 | 45 | 0,993 | Barretos 27→60; Itápolis 36→62; Araraquara 32→47 |

Por região intermediária do IBGE:

| Região | % do N4 | N4 med | p5 | p95 | Amplitude p5–p95 / med |
|---|---:|---:|---:|---:|---:|
| Ribeirão Preto | 23,9 | 1.429,1 | 1.219,9 | 1.684,5 | 33 % |
| São José do Rio Preto | 16,8 | 1.005,6 | 864,1 | 1.181,1 | 32 % |
| Campinas | 9,6 | 571,3 | 492,4 | 642,2 | 26 % |
| Bauru | 9,2 | 546,5 | 473,0 | 639,1 | 30 % |
| Araçatuba | 8,9 | 528,7 | 451,0 | 636,1 | 35 % |
| Marília | 8,3 | 493,0 | 415,8 | 545,9 | 26 % |
| Presidente Prudente | 7,6 | 451,1 | 387,1 | 540,6 | 34 % |
| Araraquara | 7,3 | 438,7 | 373,4 | 519,2 | 33 % |
| Sorocaba | 6,8 | 406,8 | 311,7 | 429,9 | 29 % |
| São Paulo | 1,5 | 88,4 | 57,6 | 145,1 | 99 % |
| São José dos Campos | 0,2 | 12,5 | 10,0 | 20,7 | 86 % |

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
| modelo reproduz mín, med e máx do snapshot por substrato (±0,1 %) | ok | maior desvio 0,000 % |
| U = mín(uso existente, N3a) em cada linha e cenário (informativo: o modelo interpola o U) | vale | 0 linhas fora; 0,00 % do U |

Fatores residuais (o que o snapshot varia fora de `cp2b_parametros.csv`), fator médio do substrato no mín, med e máx: AVES_CORTE FC (snapshot) 0,944–1,000–1,056; AVES_POSTURA FC (snapshot) 0,944–1,000–1,056; BAGACO base N1 (snapshot) 0,935–1,000–1,002; TORTA_FILTRO base N1 (snapshot) 0,935–1,000–1,002; VINHACA base N1 (snapshot) 0,917–1,000–1,147.

Elementos do arquivo de parâmetros não sorteados: u (usos excludentes) / notas.

## Como ler

- O intervalo de 90 % supõe parâmetros independentes. Parâmetros com a mesma fonte (por exemplo o FC de vários rebanhos) andam juntos na vida real; por isso o intervalo verdadeiro fica entre este e a faixa mín–máx do CP2b, mais perto deste quanto mais independentes forem as fontes.
- A triangular dá peso à mediana do CP2b. Ela não diz que a mediana está certa: a sensibilidade (`outputs/sensibilidade_cp2b/`) é que testa a mediana contra a literatura.
- O FL espacial de cada município é interpolado no N3 dele entre os seus pontos mín, med e máx do snapshot. Entre esses pontos a interpolação é linear, e o FL de um município depende só da oferta dele, não da dos vizinhos; as duas coisas são aproximações.
- Nos cenários do ranking o FL espacial responde ao N3 do cenário; por isso o N4 de um cenário aqui pode diferir um pouco do da sensibilidade, que mantém o FS × FL de cada município.
- Rank 1 = maior N4 municipal (soma dos substratos). Cenários de definição ficam fora do ranking, porque não são leituras possíveis do CP2b.
