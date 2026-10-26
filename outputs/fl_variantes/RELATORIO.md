# O FL espacial do CP2b v5.1: quanto do N4 depende da variante

> Snapshot v5.1; volumes em milhões de Nm³ de CH₄ por ano. N4 = N3 × FS × FL, com o FL de cada variante do arquivo `cp2b_fl_municipio_substrato.csv` no lugar do FL usado. O FS é o do snapshot: FS × FL dividido pelo FL usado. Nada aqui muda a plataforma.

## 1. Qual variante o snapshot usa (cenário med)

- fl_codig_alocado: AVES_CORTE, AVES_POSTURA, BAGACO, BAGACO_CITROS, BOV_CONFINADO, BOV_LEITE, CASCA_CAFE, LODO_ETE, PALHA, PALHA_MILHO, PALHA_SOJA, PODA_URBANA, RSU_ORGANICO, SUINOS, TORTA_FILTRO, VINHACA

## 2. N4 do estado com cada variante

| Cenário | Variante | N4 | Contra a usada | Municípios com N4 zero | Zeros que abrem | Zeros novos |
|---|---|---:|---|---:|---:|---:|
| min | B · codigestão, alocado (`fl_codig_alocado`) | 1.882,6 | 0,0 % | 146 | 0 | 0 |
| min | A · codigestão, cobertura (`fl_codigestao`) | 2.001,8 | +6,3 % | 122 | 24 | 0 |
| min | C · mono, cobertura (`fl_mono`) | 1.782,7 | -5,3 % | 160 | 7 | 21 |
| min | D · mono, alocado (`fl_mono_alocado`) | 1.735,6 | -7,8 % | 169 | 0 | 23 |
| min | B · palha em qualquer hub (`fl_codig_alocado_palhaqh`) | 1.654,4 | -12,1 % | 160 | 8 | 22 |
| med | B · codigestão, alocado (`fl_codig_alocado`) | 5.971,7 | 0,0 % | 27 | 0 | 0 |
| med | A · codigestão, cobertura (`fl_codigestao`) | 6.136,6 | +2,8 % | 15 | 12 | 0 |
| med | C · mono, cobertura (`fl_mono`) | 5.927,6 | -0,7 % | 30 | 6 | 9 |
| med | D · mono, alocado (`fl_mono_alocado`) | 5.742,6 | -3,8 % | 47 | 1 | 21 |
| med | B · palha em qualquer hub (`fl_codig_alocado_palhaqh`) | 6.238,0 | +4,5 % | 24 | 3 | 0 |
| max | B · codigestão, alocado (`fl_codig_alocado`) | 15.576,9 | 0,0 % | 0 | 0 | 0 |
| max | A · codigestão, cobertura (`fl_codigestao`) | 15.632,8 | +0,4 % | 0 | 0 | 0 |
| max | C · mono, cobertura (`fl_mono`) | 15.602,9 | +0,2 % | 0 | 0 | 0 |
| max | D · mono, alocado (`fl_mono_alocado`) | 15.461,6 | -0,7 % | 0 | 0 | 0 |
| max | B · palha em qualquer hub (`fl_codig_alocado_palhaqh`) | 15.853,9 | +1,8 % | 0 | 0 | 0 |

## 3. Os municípios com N4 med zero

| Município | Região | N3 | Oferta (m³ CH₄/dia) | `fl_codig_alocado` | `fl_codigestao` | `fl_mono` | `fl_mono_alocado` | `fl_codig_alocado_palhaqh` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Bananal | São José dos Campos | 0,60 | 1.648 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Iguape | Sorocaba | 0,44 | 1.206 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| São José do Barreiro | São José dos Campos | 0,43 | 1.170 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Silveiras | São José dos Campos | 0,41 | 1.117 | 0,00 | 0,11 | 0,00 | 0,00 | 0,01 |
| Jacupiranga | Sorocaba | 0,39 | 1.070 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Registro | Sorocaba | 0,39 | 1.066 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Cajati | Sorocaba | 0,36 | 974 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Cananéia | Sorocaba | 0,29 | 799 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Queluz | São José dos Campos | 0,25 | 692 | 0,00 | 0,01 | 0,00 | 0,00 | 0,00 |
| Areias | São José dos Campos | 0,25 | 677 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Pariquera-Açu | Sorocaba | 0,20 | 545 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| São Bento do Sapucaí | São José dos Campos | 0,19 | 520 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Lavrinhas | São José dos Campos | 0,18 | 501 | 0,00 | 0,02 | 0,00 | 0,00 | 0,01 |
| Arapeí | São José dos Campos | 0,18 | 489 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Miracatu | Sorocaba | 0,17 | 461 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Sete Barras | Sorocaba | 0,16 | 444 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Itaoca | Sorocaba | 0,16 | 436 | 0,00 | 0,02 | 0,00 | 0,00 | 0,00 |
| Eldorado | Sorocaba | 0,14 | 388 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Juquiá | Sorocaba | 0,13 | 359 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Ribeira | Sorocaba | 0,12 | 323 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Itapirapuã Paulista | Sorocaba | 0,11 | 289 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Ilha Comprida | Sorocaba | 0,09 | 254 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Iporanga | Sorocaba | 0,06 | 169 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Barra do Turvo | Sorocaba | 0,06 | 167 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Juquitiba | São Paulo | 0,06 | 162 | 0,00 | 0,03 | 0,02 | 0,00 | 0,00 |
| Pedro de Toledo | São Paulo | 0,04 | 110 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| Tapiraí | Sorocaba | 0,03 | 70 | 0,00 | 0,02 | 0,00 | 0,00 | 0,00 |

## 4. O FL zero segue um limiar de oferta?

Oferta por linha; a do município é a soma das linhas. "Separa" quer dizer que toda linha com FL zero tem menos oferta que toda linha com FL acima de zero.

| Substrato | Cenário | Linhas FL 0 / > 0 | Linha: máx com FL 0 | Linha: mín com FL > 0 | Separa | Município: máx com FL 0 | Município: mín com FL > 0 | Separa |
|---|---|---|---:|---:|---|---:|---:|---|
| AVES_CORTE | max | 1 / 545 | 4,6 | 0,2 | não | 479,4 | 460,4 | não |
| AVES_CORTE | med | 33 / 512 | 122,8 | 0,1 | não | 22.829,2 | 163,8 | não |
| AVES_CORTE | min | 254 / 290 | 2.848,2 | 0,0 | não | 65.682,0 | 11,5 | não |
| AVES_POSTURA | max | 1 / 521 | 23,4 | 0,3 | não | 479,4 | 460,4 | não |
| AVES_POSTURA | med | 34 / 487 | 264,2 | 0,1 | não | 57.656,1 | 163,8 | não |
| AVES_POSTURA | min | 261 / 258 | 1.264,1 | 0,1 | não | 149.997,1 | 11,5 | não |
| BAGACO | min | 1 / 119 | 1.002,1 | 1.002,1 | não | 9.748,6 | 5.068,1 | não |
| BAGACO_CITROS | min | 7 / 7 | 2.370,1 | 349,4 | não | 33.354,1 | 7.603,8 | não |
| BOV_CONFINADO | med | 8 / 217 | 74,1 | 0,6 | não | 27.055,2 | 274,7 | não |
| BOV_CONFINADO | min | 122 / 102 | 1.391,9 | 0,3 | não | 149.997,1 | 701,3 | não |
| BOV_LEITE | max | 2 / 600 | 113,9 | 2,2 | não | 196.101,9 | 460,4 | não |
| BOV_LEITE | med | 92 / 507 | 2.220,9 | 0,5 | não | 137.595,6 | 201,3 | não |
| BOV_LEITE | min | 365 / 228 | 528,8 | 0,4 | não | 63.988,0 | 366,7 | não |
| CASCA_CAFE | max | 2 / 274 | 1,3 | 0,4 | não | 479,4 | 827,7 | sim |
| CASCA_CAFE | med | 19 / 257 | 30,2 | 0,2 | não | 24.123,1 | 319,4 | não |
| CASCA_CAFE | min | 167 / 109 | 1.992,8 | 0,1 | não | 68.070,8 | 1.658,1 | não |
| LODO_ETE | max | 6 / 172 | 173,2 | 0,9 | não | 11.449,1 | 486,5 | não |
| LODO_ETE | med | 48 / 130 | 711,5 | 0,3 | não | 143.915,1 | 201,2 | não |
| LODO_ETE | min | 126 / 52 | 1.107,0 | 0,2 | não | 149.997,1 | 26,6 | não |
| PALHA | max | 46 / 462 | 8.081,5 | 17,7 | não | 672.850,7 | 921,0 | não |
| PALHA | med | 55 / 453 | 3.566,7 | 11,9 | não | 141.651,8 | 353,6 | não |
| PALHA | min | 69 / 438 | 10.417,8 | 15,8 | não | 22.673,5 | 112,7 | não |
| PALHA_MILHO | med | 32 / 511 | 196,9 | 0,6 | não | 17.680,4 | 274,7 | não |
| PALHA_MILHO | min | 223 / 320 | 3.503,7 | 0,7 | não | 25.914,8 | 160,5 | não |
| PALHA_SOJA | med | 8 / 475 | 288,5 | 2,5 | não | 17.680,4 | 357,5 | não |
| PALHA_SOJA | min | 163 / 320 | 8.340,6 | 1,2 | não | 38.834,8 | 366,7 | não |
| PODA_URBANA | max | 1 / 644 | 64,4 | 8,5 | não | 479,4 | 210,9 | não |
| PODA_URBANA | med | 30 / 615 | 92,8 | 1,4 | não | 17.680,4 | 70,5 | não |
| PODA_URBANA | min | 299 / 346 | 60,2 | 0,1 | não | 51.566,0 | 4,7 | não |
| RSU_ORGANICO | max | 1 / 644 | 148,8 | 10,7 | não | 479,4 | 210,9 | não |
| RSU_ORGANICO | med | 30 / 615 | 949,4 | 7,0 | não | 17.680,4 | 70,5 | não |
| RSU_ORGANICO | min | 222 / 270 | 2.026,9 | 1,3 | não | 51.566,0 | 117,2 | não |
| SUINOS | max | 7 / 575 | 65,3 | 1,0 | não | 4.645,0 | 210,9 | não |
| SUINOS | med | 118 / 462 | 467,4 | 0,5 | não | 57.656,1 | 319,4 | não |
| SUINOS | min | 399 / 176 | 644,9 | 0,1 | não | 126.770,7 | 366,7 | não |

## 5. Conferência

| Checagem | Resultado | Detalhe |
|---|---|---|
| a variante identificada reproduz o N4 do snapshot, min (±0,01 %) | ok | 1.882,6 contra 1.882,6 mi |
| a variante identificada reproduz o N4 do snapshot, med (±0,01 %) | ok | 5.971,7 contra 5.971,7 mi |
| a variante identificada reproduz o N4 do snapshot, max (±0,01 %) | ok | 15.576,9 contra 15.576,9 mi |
| toda combinação de substrato e cenário com linhas no arquivo do FL tem a variante identificada | ok | 48 combinações; fora do FL espacial, com o N4 do snapshot em todas as variantes: BOV_PASTO_MISTO max |

## Como ler

- A variante usada é lida dos números, não do texto: é a que dá um só FS por substrato e cenário. Se a conferência falhar, os números das outras variantes não valem.
- "Zeros que abrem" são municípios com N4 zero na variante usada que passam a ter N4 na outra; "zeros novos", o contrário.
- Se o FL zero separa pela oferta, há um limiar de oferta mínima entre os dois valores da tabela 4; se não separa, o FL zero vem de outra regra (distância ao hub, alocação), e a tabela 3 diz o quanto cada variante devolve.
- O N3 e o FS não mudam; só o FL. Variantes de mono-digestão e de cobertura respondem a outra pergunta (planta própria, ou raio sem alocar), e não são correções da usada.

