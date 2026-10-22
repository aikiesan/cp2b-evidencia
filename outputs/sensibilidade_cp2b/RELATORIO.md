# Sensibilidade do CP2b v5.1 à literatura (N1 → N4)

> Níveis: cp2b_municipio_substrato_niveis.csv (sha256 conferido) · Parâmetros: CP2b v5.1, cp2b_parametros.csv (sha256 conferido).
> Cenário med do CP2b; volumes em milhões de Nm³ de CH₄ por ano. Cada cenário troca um parâmetro pelo valor da literatura na etapa onde ele entra e refaz a cascata município a município, com U e FS × FL de cada município mantidos. Nada aqui muda a plataforma.

## 1. Cascata do CP2b v5.1 (med)

| Substrato | N1 | N2 | N3a | U | N3 (Ideal) | N4 (Real) | % do N4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| PALHA | 8.409,1 | 3.363,6 | 3.027,3 | 16,7 | 3.010,6 | 2.428,7 | 40,7 |
| TORTA_FILTRO | 1.062,1 | 955,9 | 955,9 | 14,5 | 941,4 | 847,3 | 14,2 |
| VINHACA | 945,6 | 898,3 | 898,3 | 14,2 | 884,1 | 809,7 | 13,6 |
| BAGACO | 8.731,1 | 8.294,5 | 829,5 | 12,6 | 816,9 | 792,3 | 13,3 |
| AVES_CORTE | 325,9 | 292,6 | 277,9 | 1,8 | 276,1 | 255,1 | 4,3 |
| PALHA_MILHO | 652,6 | 261,0 | 248,0 | 0,0 | 248,0 | 187,0 | 3,1 |
| PALHA_SOJA | 797,5 | 239,2 | 239,2 | 0,0 | 239,2 | 178,0 | 3,0 |
| RSU_ORGANICO | 499,5 | 324,6 | 324,6 | 163,1 | 161,5 | 153,6 | 2,6 |
| AVES_POSTURA | 133,1 | 119,4 | 113,4 | 0,1 | 113,3 | 104,9 | 1,8 |
| BOV_CONFINADO | 92,0 | 59,8 | 59,8 | 0,1 | 59,7 | 55,6 | 0,9 |
| LODO_ETE | 102,5 | 55,4 | 55,4 | 4,0 | 51,4 | 43,0 | 0,7 |
| BAGACO_CITROS | 218,6 | 164,0 | 41,0 | 0,0 | 41,0 | 36,0 | 0,6 |
| BOV_LEITE | 157,8 | 78,9 | 78,9 | 0,5 | 78,4 | 23,7 | 0,4 |
| PODA_URBANA | 55,8 | 27,9 | 25,1 | 0,0 | 25,1 | 23,4 | 0,4 |
| CASCA_CAFE | 45,3 | 40,8 | 24,5 | 0,0 | 24,5 | 17,8 | 0,3 |
| SUINOS | 37,1 | 31,6 | 31,6 | 0,9 | 30,6 | 15,5 | 0,3 |
| BOV_PASTO_MISTO | 1.376,9 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| **Estado** | **23.642,6** | **15.207,6** | **7.230,4** | **228,5** | **7.001,9** | **5.971,7** | 100 |

## 2. Conferência do snapshot

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

## 3. Sensibilidade

N4 do estado hoje: 5.971,7 mi Nm³/ano. A coluna "Na faixa" diz se o N4 depois da troca fica entre o N4 mínimo e o máximo do próprio CP2b.

| Cenário | Tipo | O que muda | Multiplicador (med, faixa) | N1 | N2 | N3 | N4 | ΔN4 | N4 na faixa da literatura | Na faixa |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| leite_g | literatura | g do bovino de leite = excreção medida | BOV_LEITE N1 ×3,48 (2,54–4,71) | 24.033,2 | 15.402,9 | 7.197,2 | 6.030,8 | +1,0 % | 6.008,5–6.060,3 | sim |
| leite_fc1 | hipótese | g do leite já é a fração coletável: FC = 1 | BOV_LEITE N2 ×2,00 | 23.642,6 | 15.286,5 | 7.080,8 | 5.995,6 | +0,4 % | — | sim |
| confinado_ms | literatura | matéria orgânica fecal do confinado = medida | BOV_CONFINADO N1 ×0,61 (0,60–0,63) | 23.607,1 | 15.184,5 | 6.978,8 | 5.950,3 | -0,4 % | 5.949,2–5.951,3 | sim |
| confinado_fc | literatura | FC do confinado = 0,9 (coleta no alojamento) | BOV_CONFINADO N2 ×1,38 | 23.642,6 | 15.230,6 | 7.024,9 | 5.993,1 | +0,4 % | — | sim |
| pasto_g | literatura | g do bovino de pasto = inventário nacional | BOV_PASTO_MISTO N1 ×2,40 | 25.570,3 | 15.207,6 | 7.001,9 | 5.971,7 | 0,0 % | — | sim |
| citros_fco | literatura | FCo do bagaço de laranja = sobra após a peletização | BAGACO_CITROS N3a ×0,08 (0,00–0,20) | 23.642,6 | 15.207,6 | 6.964,2 | 5.938,5 | -0,6 % | 5.935,7–5.942,9 | sim |
| palha_fs | literatura | FS da palha de cana = massa após decomposição no solo | PALHA N4 ×0,73 (0,34–0,73) | 23.642,6 | 15.207,6 | 7.001,9 | 5.311,7 | -11,1 % | 4.361,4–5.311,7 | sim |
| bagaco_bmp | literatura | BMP do bagaço de cana = medido (bruto) | BAGACO N1 ×1,46 (0,76–1,98) | 27.681,8 | 19.044,8 | 7.385,6 | 6.343,9 | +6,2 % | 5.777,8–6.756,7 | sim |
| soja_bmp | literatura | BMP da palha de soja = medido (bruto) | PALHA_SOJA N1 ×0,51 | 23.254,7 | 15.091,2 | 6.885,5 | 5.885,1 | -1,4 % | — | sim |
| aves_fco_adubo | definição | FCo das aves lido como 'fração não usada como adubo' | AVES_CORTE N3a ×0,21; AVES_POSTURA N3a ×0,21 | 23.642,6 | 15.207,6 | 6.693,4 | 5.686,6 | -4,8 % | — | sim |
| leite_suinos_fco_adubo | definição | FCo de leite e suínos lido como 'fração não usada como adubo' | BOV_LEITE N3a ×0,80 (0,80–1,00); SUINOS N3a ×0,80 (0,80–1,00) | 23.642,6 | 15.207,6 | 6.979,9 | 5.963,8 | -0,1 % | 5.963,8–5.971,7 | sim |
| confinado_fs_dof | definição | FS do confinado lido como dias de cocho / 365 | BOV_CONFINADO N4 ×0,31 (0,20–0,34) | 23.642,6 | 15.207,6 | 7.001,9 | 5.933,1 | -0,6 % | 5.927,2–5.934,8 | sim |
| cana_fs_safra | definição | FS de vinhaça e torta lido como fração do ano em safra | TORTA_FILTRO N4 ×0,77 (0,74–0,79); VINHACA N4 ×0,75 (0,73–0,77) | 23.642,6 | 15.207,6 | 7.001,9 | 5.571,6 | -6,7 % | 5.535,1–5.608,0 | sim |
| literatura_g_total | combinado | Toda a literatura, g do leite = excreção total | BAGACO N1 ×1,46 (0,76–1,98); BAGACO_CITROS N3a ×0,08 (0,00–0,20); BOV_CONFINADO N1 ×0,61 (0,60–0,63); BOV_CONFINADO N2 ×1,38; BOV_LEITE N1 ×3,48 (2,54–4,71); BOV_PASTO_MISTO N1 ×2,40; PALHA N4 ×0,73 (0,34–0,73); PALHA_SOJA N1 ×0,51 | 29.576,8 | 19.114,9 | 7.417,9 | 5.614,9 | -6,0 % | 4.071,9–6.063,1 | sim |
| literatura_g_coletavel | combinado | Toda a literatura, g do leite = fração coletável (FC = 1) | BAGACO N1 ×1,46 (0,76–1,98); BAGACO_CITROS N3a ×0,08 (0,00–0,20); BOV_CONFINADO N1 ×0,61 (0,60–0,63); BOV_CONFINADO N2 ×1,38; BOV_LEITE N2 ×2,00; BOV_PASTO_MISTO N1 ×2,40; PALHA N4 ×0,73 (0,34–0,73); PALHA_SOJA N1 ×0,51 | 29.186,2 | 18.998,5 | 7.301,5 | 5.579,7 | -6,6 % | 4.059,0–5.998,3 | sim |

Notas dos cenários:

- **leite_g**: Vale se o g do CP2b for excreção total. Alternativa a leite_fc1.
- **leite_fc1**: Vale se o g do CP2b já descontar a coleta. Alternativa a leite_g.
- **confinado_ms**: Matéria seca fecal × SV medidos, contra g × ST × SV do CP2b.
- **confinado_fc**: Tier C; o mesmo 0,9 vale para todos os rebanhos na fonte.
- **pasto_g**: FC do pasto é 0: muda o N1, não o N4.
- **citros_fco**: Fonte de 2004, tier B.
- **palha_fs**: Depende do tempo entre a colheita e o enfardamento.
- **bagaco_bmp**: Tiers B e C.
- **soja_bmp**: Um registro, tier C.
- **aves_fco_adubo**: Não é a definição do CP2b (adubo é compatível com a digestão).
- **leite_suinos_fco_adubo**: Não é a definição do CP2b (adubo é compatível com a digestão).
- **confinado_fs_dof**: A DEC-013 proíbe; a base já é o estoque confinado.
- **cana_fs_safra**: A DEC-013 proíbe; a safra pesa no dimensionamento da planta.
- **literatura_g_total**: leite_g + confinado_ms + confinado_fc + pasto_g + citros_fco + palha_fs + bagaco_bmp + soja_bmp
- **literatura_g_coletavel**: leite_fc1 + confinado_ms + confinado_fc + pasto_g + citros_fco + palha_fs + bagaco_bmp + soja_bmp

## 4. Revisão por substrato

O que as três bibliotecas de evidência dizem de cada substrato, do maior N4 para o menor. "Confere" = todo registro comparável cai dentro da faixa do CP2b ou se sobrepõe a ela; "diverge" = algum fica inteiro acima ou abaixo.

| Substrato | % do N4 | Geração (g, ST, SV) | BMP | FC | FCo | FS | Cenários |
|---|---:|---|---|---|---|---|---|
| PALHA | 40,7 | — | confere (1) | — | confere (2) | diverge: 1 de 1 (abaixo) | palha_fs |
| TORTA_FILTRO | 14,2 | — | confere (1) | — | — | — | cana_fs_safra |
| VINHACA | 13,6 | — | — | — | confere (1) | — | cana_fs_safra |
| BAGACO | 13,3 | — | diverge: 2 de 3 (acima) | — | — | — | bagaco_bmp |
| AVES_CORTE | 4,3 | diverge: 1 de 1 (acima); lotes/ano implícitos 6,0, 7,6 | — | — | — | — | aves_fco_adubo |
| PALHA_MILHO | 3,1 | — | — | — | confere (3) | — | — |
| PALHA_SOJA | 3,0 | — | diverge: 1 de 1 (abaixo) | — | confere (1) | — | soja_bmp |
| RSU_ORGANICO | 2,6 | — | — | — | — | — | — |
| AVES_POSTURA | 1,8 | confere (5) | — | — | — | — | aves_fco_adubo |
| BOV_CONFINADO | 0,9 | diverge: 3 de 4 (abaixo, acima) | — | diverge: 1 de 1 (acima) | — | — | confinado_ms, confinado_fc, confinado_fs_dof |
| LODO_ETE | 0,7 | — | — | — | — | — | — |
| BAGACO_CITROS | 0,6 | — | — | — | diverge: 1 de 1 (abaixo) | confere (1) | citros_fco |
| BOV_LEITE | 0,4 | diverge: 2 de 5 (acima) | — | — | — | — | leite_g, leite_fc1, leite_suinos_fco_adubo |
| PODA_URBANA | 0,4 | — | — | — | — | — | — |
| CASCA_CAFE | 0,3 | — | confere (4) | — | confere (1) | — | — |
| SUINOS | 0,3 | — | — | confere (1) | confere (1) | — | leite_suinos_fco_adubo |
| BOV_PASTO_MISTO | 0,0 | diverge: 1 de 1 (acima) | — | — | — | — | pasto_g |

Sem nenhum registro comparável: RSU_ORGANICO, LODO_ETE, PODA_URBANA.

## Como ler

- O multiplicador é o valor da literatura (na unidade do CP2b) sobre a mediana do CP2b, tirado das bibliotecas de evidência. Registros do mesmo elemento entram juntos (faixa = menor e maior; centro = média dos centros); elementos diferentes se multiplicam.
- U fica como está porque é uso energético já instalado; se o N3a cai abaixo de U, o N3 do município fica em zero, como no CP2b.
- Cenários do tipo definição não são propostas: mostram o tamanho do erro de quem ler FS ou FCo com outra definição. Servem para a frase dos Métodos.
- leite_g e leite_fc1 são alternativas; por isso há dois combinados.
- O FL (espacial, por município) e o U não têm registro comparável no Literature Watch; ficam como estão em todos os cenários.
- Números, DOIs e notas vêm dos registros do Literature Watch. Antes de citar, abra a fonte.
