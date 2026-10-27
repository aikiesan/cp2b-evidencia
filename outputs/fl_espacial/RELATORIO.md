# O FL espacial do CP2b v5.1, lido das saídas do fl_v5

> Tabelas agregadas de `data/fl_v51/` (conferidas com o `MANIFESTO.csv`), escritas pelo código de `fl_espacial/`. FL entre 0 e 1; oferta em Nm³ de CH₄ por dia (N3). Nada aqui roda o fl_v5 de novo.

## 1. FL estadual por substrato (cenário med)

| Substrato | B · codigestão, alocado | A · codigestão, cobertura | C · mono, cobertura | D · mono, alocado | Oferta N3 (Nm³/dia) |
|---|---:|---:|---:|---:|---:|
| PALHA | 0,877 | 0,877 | 0,877 | 0,877 | 8.248.116 |
| TORTA_FILTRO | 1,000 | 1,000 | 1,000 | 0,995 | 2.579.251 |
| VINHACA | 0,996 | 1,000 | 1,000 | 0,995 | 2.422.173 |
| BAGACO | 1,000 | 1,000 | 1,000 | 0,995 | 2.238.076 |
| AVES_CORTE | 0,973 | 1,000 | 0,976 | 0,879 | 756.465 |
| PALHA_MILHO | 0,838 | 0,996 | 0,861 | 0,657 | 679.392 |
| PALHA_SOJA | 0,827 | 0,997 | 0,837 | 0,609 | 655.478 |
| RSU_ORGANICO | 0,951 | 0,986 | 0,907 | 0,777 | 442.516 |
| AVES_POSTURA | 0,974 | 0,998 | 0,927 | 0,832 | 310.400 |
| BOV_LEITE | 0,308 | 0,903 | 0,039 | 0,017 | 214.858 |
| BOV_CONFINADO | 0,980 | 0,999 | 0,895 | 0,834 | 163.572 |
| LODO_ETE | 0,835 | 0,986 | 0,750 | 0,687 | 140.906 |
| BAGACO_CITROS | 0,999 | 1,000 | 1,000 | 0,997 | 112.313 |
| SUINOS | 0,534 | 0,979 | 0,376 | 0,243 | 83.922 |
| PODA_URBANA | 0,950 | 0,988 | 0,593 | 0,477 | 68.774 |
| CASCA_CAFE | 0,767 | 1,000 | 0,756 | 0,495 | 66.988 |

## 2. Municípios com FL zero em todos os substratos

| Cenário | Variante | Municípios | Contra B |
|---|---|---:|---:|
| min | B · codigestão, alocado | 143 | 0 |
| min | A · codigestão, cobertura | 122 | -21 |
| min | C · mono, cobertura | 159 | +16 |
| min | D · mono, alocado | 169 | +26 |
| med | B · codigestão, alocado | 26 | 0 |
| med | A · codigestão, cobertura | 14 | -12 |
| med | C · mono, cobertura | 29 | +3 |
| med | D · mono, alocado | 46 | +20 |
| max | B · codigestão, alocado | 0 | 0 |
| max | A · codigestão, cobertura | 0 | 0 |
| max | C · mono, cobertura | 1 | +1 |
| max | D · mono, alocado | 1 | +1 |

Quase zero no B med (maior FL entre os substratos acima de 0 e até 0,01): Tapiraí (0,0000); Campos do Jordão (0,0003); Bertioga (0,0004); São Lourenço da Serra (0,0006); Natividade da Serra (0,0018); Ubatuba (0,0023); Joanópolis (0,0036).

Malha: API de malhas do IBGE (v3): https://servicodados.ibge.gov.br/api/v3/malhas/estados/35?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio (sha256 a9296e20334d…). No mapa, 14 municípios zeram nas quatro variantes, 12 na B e não em todas, e 21 só fora da B. Mapa: `mapa_zeros_variantes.png`.

## 3. Por que os municípios zeram, em km (B, med, palha nas usinas)

Distância por estrada do ponto de oferta ao hub selecionado mais próximo. r2 med: líquidos 15 km, sólidos úmidos 30 km, sólidos secos 25 km (palha: o r2 das usinas). Folga = menor (d mínima − r2) entre os substratos; acima de zero, nenhuma oferta do município alcança um hub. Q_min med = 1.500 Nm³/dia.

- 26 municípios; hub mais próximo a 26,7–140,5 km (mediana 51,6 km).
- Folga acima de zero em 26 de 26; a menor é 4,2 km.
- Oferta própria abaixo do Q_min em 25 de 26.

| Município | Oferta N3 (Nm³/dia) | Hub mais próximo (km) | Folga além do r2 (km) | Abaixo do Q_min |
|---|---:|---:|---:|---|
| Ribeira | 322,8 | 26,7 | 11,7 | sim |
| Silveiras | 1.117,3 | 28,1 | 4,2 | sim |
| Itaoca | 435,6 | 31,2 | 7,4 | sim |
| Lavrinhas | 501,1 | 31,6 | 4,5 | sim |
| São Bento do Sapucaí | 519,7 | 34,2 | 4,2 | sim |
| Juquitiba | 162,1 | 35,9 | 5,9 | sim |
| Iporanga | 169,3 | 38,6 | 8,6 | sim |
| Eldorado | 387,8 | 39,1 | 14,1 | sim |
| Queluz | 692,2 | 39,3 | 14,3 | sim |
| Pedro de Toledo | 110,4 | 44,7 | 14,7 | sim |
| Iguape | 1.206,1 | 45,2 | 15,2 | sim |
| Itapirapuã Paulista | 289,2 | 46,8 | 25,9 | sim |
| Areias | 677,4 | 48,2 | 24,9 | sim |
| Miracatu | 461,4 | 55,0 | 25,0 | sim |
| Juquiá | 358,5 | 55,2 | 25,2 | sim |
| Sete Barras | 443,5 | 58,0 | 30,1 | sim |
| São José do Barreiro | 1.170,0 | 71,8 | 48,1 | sim |
| Barra do Turvo | 167,3 | 83,2 | 53,2 | sim |
| Registro | 1.065,7 | 90,8 | 65,8 | sim |
| Arapeí | 489,2 | 100,1 | 70,1 | sim |
| Bananal | 1.648,3 | 110,1 | 86,0 | não |
| Pariquera-Açu | 545,2 | 110,4 | 85,0 | sim |
| Jacupiranga | 1.070,1 | 114,0 | 85,3 | sim |
| Cajati | 974,0 | 116,8 | 91,8 | sim |
| Cananéia | 798,7 | 137,1 | 112,1 | sim |
| Ilha Comprida | 254,0 | 140,5 | 110,5 | sim |

## 4. A C02 (BMP do bagaço) no FL

`04b` rodado de novo com a oferta de bagaço escalada pelo BMP proposto; as bacias de cobertura (filtro dos candidatos) ficaram as da v5.1, então o efeito é um piso.

| Cenário | Máx \|ΔFL\| B | Máx \|ΔFL\| D | Substratos com \|Δ\| ≥ 0,0005 |
|---|---:|---:|---:|
| min | 0,0000 | 0,0070 | 1 |
| med | 0,0046 | 0,0024 | 7 |
| max | 0,0030 | 0,0001 | 2 |

| Substrato | Cenário | FL B v5.1 | FL B C02 | ΔFL B | ΔFL D |
|---|---|---:|---:|---:|---:|
| BAGACO | min | 0,9881 | 0,9881 | 0,0000 | +0,0070 |
| AVES_CORTE | med | 0,9726 | 0,9731 | +0,0006 | 0,0000 |
| BAGACO | med | 0,9999 | 0,9999 | 0,0000 | +0,0024 |
| BOV_LEITE | med | 0,3084 | 0,3079 | -0,0005 | 0,0000 |
| CASCA_CAFE | med | 0,7673 | 0,7683 | +0,0011 | 0,0000 |
| LODO_ETE | med | 0,8355 | 0,8334 | -0,0021 | 0,0000 |
| PALHA_MILHO | med | 0,8381 | 0,8369 | -0,0012 | 0,0000 |
| SUINOS | med | 0,5341 | 0,5387 | +0,0046 | 0,0000 |
| BOV_LEITE | max | 0,8854 | 0,8884 | +0,0030 | 0,0000 |
| SUINOS | max | 0,9255 | 0,9225 | -0,0029 | 0,0000 |

No município, 835 linhas município × substrato mudam mais de 0,01 no FL B:

| Substrato | Cenário | Linhas | Sobem | Descem | ΔFL mín | ΔFL máx |
|---|---|---:|---:|---:|---:|---:|
| BOV_LEITE | med | 31 | 15 | 16 | -0,363 | +0,457 |
| SUINOS | med | 30 | 14 | 16 | -0,135 | +0,340 |
| PALHA_MILHO | med | 29 | 11 | 18 | -0,096 | +0,284 |
| PALHA_SOJA | med | 29 | 11 | 18 | -0,082 | +0,313 |
| AVES_CORTE | med | 11 | 7 | 4 | -0,210 | +0,112 |
| AVES_POSTURA | med | 10 | 6 | 4 | -0,278 | +0,111 |
| CASCA_CAFE | med | 10 | 6 | 4 | -0,147 | +0,263 |
| LODO_ETE | med | 6 | 3 | 3 | -0,363 | +0,708 |
| PODA_URBANA | med | 5 | 2 | 3 | -0,252 | +0,206 |
| RSU_ORGANICO | med | 5 | 2 | 3 | -0,252 | +0,206 |
| VINHACA | med | 1 | 0 | 1 | -0,323 | -0,323 |
| BOV_CONFINADO | med | 1 | 0 | 1 | -0,129 | -0,129 |
| BOV_LEITE | max | 220 | 118 | 102 | -0,638 | +0,899 |
| SUINOS | max | 190 | 95 | 95 | -0,769 | +0,952 |
| PALHA_MILHO | max | 89 | 51 | 38 | -0,206 | +0,221 |
| PALHA_SOJA | max | 76 | 42 | 34 | -0,178 | +0,121 |
| CASCA_CAFE | max | 28 | 15 | 13 | -0,162 | +0,283 |
| LODO_ETE | max | 27 | 16 | 11 | -0,550 | +1,000 |
| PODA_URBANA | max | 12 | 8 | 4 | -0,045 | +0,055 |
| RSU_ORGANICO | max | 12 | 8 | 4 | -0,045 | +0,055 |
| AVES_POSTURA | max | 6 | 3 | 3 | -0,040 | +0,084 |
| AVES_CORTE | max | 3 | 2 | 1 | -0,026 | +0,042 |
| VINHACA | max | 2 | 1 | 1 | -0,298 | +0,326 |
| BOV_CONFINADO | max | 2 | 1 | 1 | -0,098 | +0,024 |

## 5. Sensibilidades que o fl_v5 já rodou

Cobertura da rede B (curva MCLP): hubs para cobrir cada fração do N3.

| Meta | Hubs (N3 total) | Hubs (sem palha) |
|---:|---:|---:|
| 50 % | 16 | 55 |
| 80 % | 114 | 143 |
| 90 % | 295 | 253 |
| 95 % | não chega | 438 |

Com os 5.075 candidatos da curva, a cobertura chega a 94,5 % do N3 total e 99,6 % do N3 sem palha (a palha só vai às usinas).

Robustez (maior \|ΔFL\| estadual entre os substratos): rede sem trilhas e regra de atribuição.

| Cenário | Rede, codigestão | Rede, mono | Atribuição pelo maior w | Atribuição exclusiva |
|---|---:|---:|---:|---:|
| min | 0,0205 | 0,0087 | 0,0000 | 0,0000 |
| med | 0,0064 | 0,0069 | 0,0000 | 0,0013 |
| max | 0,0023 | 0,0023 | 0,0000 | 0,0003 |

FL estadual com outro r2 (por classe) e outro Q_min:

| Classe | r1 | r2 | Hubs viáveis | FL codigestão | FL mono |
|---|---:|---:|---:|---:|---:|
| liquidos | 2 | 5 | 48201 | 0,982 | 0,878 |
| liquidos | 3 | 10 | 48335 | 0,988 | 0,883 |
| liquidos | 5 | 15 | 48627 | 0,991 | 0,897 |
| liquidos | 7 | 20 | 49144 | 0,994 | 0,910 |
| liquidos | 8 | 25 | 49781 | 0,996 | 0,924 |
| liquidos | 10 | 30 | 50605 | 0,998 | 0,943 |
| liquidos | 12 | 35 | 51699 | 0,999 | 0,958 |
| liquidos | 13 | 40 | 52551 | 0,999 | 0,969 |
| liquidos | 15 | 45 | 53318 | 1,000 | 0,977 |
| liquidos | 17 | 50 | 53941 | 1,000 | 0,983 |
| liquidos | 20 | 60 | 54781 | 1,000 | 0,989 |
| solidos_umidos | 3 | 5 | 36815 | 0,973 | 0,794 |
| solidos_umidos | 5 | 10 | 38704 | 0,991 | 0,886 |
| solidos_umidos | 8 | 15 | 41365 | 0,996 | 0,928 |
| solidos_umidos | 10 | 20 | 43746 | 0,997 | 0,948 |
| solidos_umidos | 13 | 25 | 46166 | 0,998 | 0,962 |
| solidos_umidos | 15 | 30 | 48627 | 0,998 | 0,971 |
| solidos_umidos | 18 | 35 | 50492 | 0,999 | 0,981 |
| solidos_umidos | 20 | 40 | 51707 | 0,999 | 0,986 |
| solidos_umidos | 23 | 45 | 52685 | 1,000 | 0,990 |
| solidos_umidos | 25 | 50 | 53473 | 1,000 | 0,992 |
| solidos_umidos | 30 | 60 | 54810 | 1,000 | 0,995 |
| solidos_secos | 2 | 5 | 44085 | 0,926 | 0,617 |
| solidos_secos | 4 | 10 | 45499 | 0,987 | 0,724 |
| solidos_secos | 6 | 15 | 46725 | 0,996 | 0,860 |
| solidos_secos | 8 | 20 | 47687 | 0,998 | 0,913 |
| solidos_secos | 10 | 25 | 48627 | 0,999 | 0,940 |
| solidos_secos | 12 | 30 | 49578 | 0,999 | 0,964 |
| solidos_secos | 14 | 35 | 50669 | 1,000 | 0,979 |
| solidos_secos | 16 | 40 | 51456 | 1,000 | 0,988 |
| solidos_secos | 18 | 45 | 52032 | 1,000 | 0,994 |
| solidos_secos | 20 | 50 | 52517 | 1,000 | 0,996 |
| solidos_secos | 24 | 60 | 53209 | 1,000 | 0,999 |

| Q_min (Nm³/dia) | Hubs viáveis | FL codigestão sem palha | FL mono sem palha |
|---:|---:|---:|---:|
| 250 | 55117 | 1,000 | 0,989 |
| 500 | 53376 | 0,999 | 0,977 |
| 1000 | 50677 | 0,998 | 0,957 |
| 1500 | 48627 | 0,997 | 0,941 |
| 2000 | 47143 | 0,996 | 0,930 |
| 3200 | 44399 | 0,994 | 0,909 |
| 5000 | 40751 | 0,991 | 0,878 |
| 7500 | 36887 | 0,984 | 0,827 |
| 10000 | 33609 | 0,979 | 0,781 |

## 6. Perturbação da oferta (B, palha nas usinas)

A oferta N3 de cada substrato multiplicada por um fator lognormal de média 1, o mesmo nos três cenários, e a alocação gulosa refeita (o filtro de candidatos acompanha o ruído). A rodada sem ruído repete os hubs e o FL municipal da v5.1. Com o fator igual dentro do município, o FL municipal de um substrato só muda se a rede de hubs mudar.

| Ruído | Cenário | Hubs (v5.1 → faixa) | Jaccard mediano | FL estadual v5.1 (p05–p95) | Zerados v5.1 (faixa) | Zeram sempre | Zeram alguma vez | Linhas mun. × subst. com p95 − p05 > 0,1 | Spearman mín. | Top-50 mín. |
|---|---|---|---:|---|---|---:|---:|---|---:|---:|
| 10 % por município | min | 175 → 171–180 | 0,95 | 0,776 (0,774–0,777) | 143 (140–159) | 139 | 162 | 370 de 5.953 | 0,991 | 46 |
| 10 % por município | med | 455 → 450–467 | 0,73 | 0,920 (0,919–0,921) | 26 (23–30) | 23 | 33 | 1.348 de 6.127 | 0,998 | 46 |
| 10 % por município | max | 752 → 742–765 | 0,61 | 0,979 (0,978–0,979) | 0 (0–0) | 0 | 0 | 685 de 6.136 | 0,998 | 45 |
| 30 % por município | min | 175 → 167–179 | 0,80 | 0,776 (0,772–0,779) | 143 (139–162) | 125 | 169 | 898 de 5.953 | 0,982 | 41 |
| 30 % por município | med | 455 → 439–464 | 0,52 | 0,920 (0,918–0,922) | 26 (18–32) | 14 | 44 | 2.434 de 6.127 | 0,989 | 41 |
| 30 % por município | max | 752 → 732–764 | 0,40 | 0,979 (0,978–0,980) | 0 (0–1) | 0 | 1 | 1.101 de 6.136 | 0,988 | 40 |
| 20 % por substrato × 20 % por município | min | 175 → 160–195 | 0,82 | 0,776 (0,755–0,791) | 143 (137–172) | 126 | 188 | 996 de 5.953 | 0,982 | 42 |
| 20 % por substrato × 20 % por município | med | 455 → 414–496 | 0,55 | 0,920 (0,912–0,928) | 26 (14–38) | 12 | 44 | 2.312 de 6.127 | 0,990 | 41 |
| 20 % por substrato × 20 % por município | max | 752 → 702–827 | 0,43 | 0,979 (0,975–0,981) | 0 (0–1) | 0 | 1 | 1.035 de 6.136 | 0,989 | 42 |

Jaccard: hubs em comum com a v5.1 sobre a união. Spearman e top-50: ordem dos municípios pela oferta coberta (N3 × FL), contra a v5.1; inclui o ruído da própria oferta.

Substratos com o FL estadual mais largo no med (p05–p95):

| Substrato | FL v5.1 | 10 % por município | 30 % por município | 20 % por substrato × 20 % por município |
|---|---:|---|---|---|
| LODO_ETE | 0,835 | 0,812–0,855 | 0,777–0,862 | 0,796–0,854 |
| BOV_LEITE | 0,308 | 0,302–0,315 | 0,302–0,327 | 0,279–0,348 |
| SUINOS | 0,534 | 0,517–0,552 | 0,502–0,562 | 0,506–0,566 |
| PALHA_MILHO | 0,838 | 0,837–0,846 | 0,836–0,851 | 0,823–0,863 |
| CASCA_CAFE | 0,767 | 0,761–0,777 | 0,755–0,791 | 0,755–0,794 |
| PALHA_SOJA | 0,827 | 0,824–0,834 | 0,826–0,838 | 0,810–0,845 |
| RSU_ORGANICO | 0,951 | 0,950–0,954 | 0,947–0,960 | 0,939–0,961 |
| PODA_URBANA | 0,950 | 0,946–0,952 | 0,942–0,955 | 0,938–0,957 |

Municípios com FL B med zero na v5.1 ou em alguma rodada (47): fração das rodadas em que zeram.

| Município | Zero na v5.1 | 10 % por município | 30 % por município | 20 % por substrato × 20 % por município |
|---|---|---:|---:|---:|
| Arapeí | sim | 1,00 | 1,00 | 1,00 |
| Areias | sim | 1,00 | 1,00 | 1,00 |
| Bananal | sim | 1,00 | 1,00 | 1,00 |
| Barra do Turvo | sim | 1,00 | 1,00 | 1,00 |
| Iporanga | sim | 1,00 | 1,00 | 1,00 |
| Itaoca | sim | 1,00 | 1,00 | 1,00 |
| Itapirapuã Paulista | sim | 1,00 | 1,00 | 1,00 |
| Miracatu | sim | 1,00 | 1,00 | 1,00 |
| Pedro de Toledo | sim | 1,00 | 1,00 | 1,00 |
| Ribeira | sim | 1,00 | 1,00 | 1,00 |
| São Bento do Sapucaí | sim | 1,00 | 1,00 | 1,00 |
| São José do Barreiro | sim | 1,00 | 1,00 | 1,00 |
| Juquiá | sim | 1,00 | 1,00 | 0,97 |
| Ilha Comprida | sim | 1,00 | 1,00 | 0,90 |
| Juquitiba | sim | 1,00 | 0,87 | 0,90 |
| Cananéia | sim | 1,00 | 0,83 | 0,83 |
| Eldorado | sim | 1,00 | 0,73 | 0,77 |
| Sete Barras | sim | 1,00 | 0,70 | 0,80 |
| Iguape | sim | 1,00 | 0,70 | 0,73 |
| Cajati | sim | 1,00 | 0,63 | 0,73 |
| Jacupiranga | sim | 1,00 | 0,63 | 0,73 |
| Pariquera-Açu | sim | 1,00 | 0,63 | 0,73 |
| Registro | sim | 1,00 | 0,63 | 0,73 |
| Queluz | sim | 0,60 | 0,47 | 0,57 |
| Silveiras | sim | 0,60 | 0,47 | 0,57 |
| Lavrinhas | sim | 0,60 | 0,43 | 0,53 |
| Ubatuba | não | 0,20 | 0,57 | 0,33 |
| Caiuá | não | 0,40 | 0,30 | 0,37 |
| Igaratá | não | 0,27 | 0,37 | 0,43 |
| São Luiz do Paraitinga | não | 0,13 | 0,37 | 0,47 |
| Natividade da Serra | não | 0,17 | 0,43 | 0,27 |
| Lagoinha | não | 0,10 | 0,23 | 0,40 |
| Joanópolis | não | 0,07 | 0,27 | 0,10 |
| Campos do Jordão | não | 0,00 | 0,33 | 0,10 |
| Santo Antônio do Pinhal | não | 0,00 | 0,33 | 0,10 |
| Santa Clara d'Oeste | não | 0,00 | 0,17 | 0,23 |
| Cruzeiro | não | 0,00 | 0,17 | 0,13 |
| Caraguatatuba | não | 0,00 | 0,07 | 0,10 |
| Ilhabela | não | 0,00 | 0,07 | 0,10 |
| São Sebastião | não | 0,00 | 0,07 | 0,10 |
| São Lourenço da Serra | não | 0,00 | 0,07 | 0,03 |
| Bom Sucesso de Itararé | não | 0,00 | 0,03 | 0,00 |
| Itanhaém | não | 0,00 | 0,00 | 0,03 |
| Itariri | não | 0,00 | 0,00 | 0,03 |
| Paraibuna | não | 0,00 | 0,03 | 0,00 |
| Peruíbe | não | 0,00 | 0,00 | 0,03 |
| Salesópolis | não | 0,00 | 0,03 | 0,00 |

No mapa da perturbação (mun30, med), municípios por classe de p95 − p05: < 0,01: 109; 0,01–0,05: 241; 0,05–0,10: 124; 0,10–0,20: 91; ≥ 0,20: 80. Mapa: `mapa_perturbacao_fl.png`.

## 7. Bananal: oferta acima do Q_min e nenhum hub

- Oferta N3 med: 1.648,3 Nm³/dia; sem a palha de cana (77,3), que vai só às usinas, 1.571,0 para a codigestão, 85 % dela em líquidos (raios de 5/15 km). Fonte: `fl_v5_municipio_substrato.csv`.
- 57 candidatos a hub alcançam essa oferta; 0 viáveis pela bacia de cobertura (Q_min 1.500 Nm³/dia).
- O melhor (grade, a 0,4 km da oferta) junta 617,9 Nm³/dia pesados por w(d), 41 % do Q_min; 617,9 vêm do próprio Bananal. Fonte: `v52_bananal_candidatos.csv`.

## 8. Conferência

| Checagem | Resultado | Detalhe |
|---|---|---|
| as tabelas de data/fl_v51 conferem com o MANIFESTO.csv | ok | 15 arquivos, sha256 e tamanho |
| fl_v5_municipio_substrato.csv é o publicado com a v5.1 (sha256 2a7b664b1f20…) | ok | sha256 2a7b664b1f20… |
| fl_v5_estado_substrato.csv é o publicado com a v5.1 (sha256 1bd83a1785ea…) | ok | sha256 1bd83a1785ea… |
| os municípios da tabela de distâncias são os de FL B med zero | ok | 26 na tabela, 26 com FL B med zero |
| c02_fl_delta: d_FL = FL C02 − FL v5.1 | ok | 48 linhas |
| c02_fl_municipio_delta só tem |ΔFL| > 0,01 | ok | 835 linhas |
| perturbação: rodadas por desenho e cenário iguais às do resumo | ok | 270 rodadas em 9 grupos |
| perturbação: hubs, FL estadual e zerados da v5.1 iguais em todos os desenhos | ok | min: 175 hubs; med: 455 hubs; max: 752 hubs |
| perturbação: os zerados da v5.1 são os de FL B zero na tabela fl_v5 | ok | min, med e max |
| Bananal: FL B med zero, nenhum candidato viável e o melhor abaixo do Q_min | ok | 57 candidatos; melhor 617,9 Nm³/dia |

## Como ler

- Um município zera quando nenhuma oferta dele fica a menos de r2 de um hub selecionado; um hub só entra com Q_min de resíduo à sua volta. A seção 3 mede as duas coisas.
- O N4 zero do snapshot (`outputs/fl_variantes/`) conta municípios com N4 abaixo de 1 Nm³/ano; aqui conta-se FL exatamente zero, e um município com FL quase zero entra lá e não aqui.
- O efeito da C02 no FL estadual vem da tabela 4; o efeito no N4 é o do `build_v52.py`, que mantém o FL da v5.1. No município, a C02 troca hubs de lugar e o FL de líquidos muda onde a pecuária é dispersa.

