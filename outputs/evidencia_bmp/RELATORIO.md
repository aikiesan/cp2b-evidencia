# Evidência de BMP: Literature Watch × CP2b × feedstocks.yaml

> Registro: `analysis/data/literature_watch/REGISTRY_bmp_v2026-10-17.csv` (40 registros) · CP2b v5.1, cp2b_parametros.csv (sha256 conferido).
> BMP em NmL CH₄/g SV, como o registro normalizou. Só substrato bruto é comparado às faixas.
> Valor fora da faixa é evidência a conferir, não erro da faixa. Nada aqui muda a plataforma.

## Substratos do CP2b com registro

| Código | Registros | Brutos comparáveis | Mediana bruto | Mín–máx bruto | Tier A | Faixa CP2b | Fora CP2b | Faixa feedstocks.yaml | Fora yaml |
|---|---:|---:|---:|---|---:|---|---:|---|---:|
| BAGACO | 3 | 3 | 273 | 125–326 | 0 | 115–220 (med 165) | 2 | 115–220 (med 165) | 2 |
| BAGACO_CITROS | 1 | 0 | — | — | 0 | 170–310 (med 230) | 0 | 170–310 (med 230) | 0 |
| CASCA_CAFE | 5 | 4 | 156 | 125–186 | 4 | 120–220 (med 165) | 0 | 120–220 (med 165) | 0 |
| PALHA | 2 | 1 | 199 | 199 | 0 | 140–250 (med 175) | 0 | 140–250 (med 175) | 0 |
| PALHA_SOJA | 2 | 1 | 113 | 113 | 0 | 150–280 (med 220) | 1 | 150–280 (med 220) | 1 |
| TORTA_FILTRO | 2 | 1 | 262 | 262 | 1 | 200–380 (med 280) | 0 | 200–380 (med 280) | 0 |
| VINHACA | 2 | 1 | 494 | 494 | 1 | — | — | 90–200 (med 160) | 1 |

O CP2b calcula a vinhaça direto por m³ de etanol (elemento "direto"), sem BMP por g SV. Para a vinhaça, a comparação por g SV é só com o feedstocks.yaml.

## Registros brutos fora de uma faixa

- **BAGACO · 326 NmL/g SV** (CP2b acima, yaml acima) · tier B · Brazil · Janke_2015_bagasse · https://doi.org/10.3390/ijms160920685
  - Nota da rotina: B-1 (326) is above PILAR's bagasse range (44-236). The second raw sample, B-2, gave 236 +/- 5, at the top of the PILAR range. The large spread between mills suggests residual sugars in fresh bagasse (55% TS, i.e. wet, fresh from the mill), plus an active co-digestion inoculum. ISR, replicates and positive control are not reported. Use the mean of B-1 and B-2 (~281) or B-2 as the conservative value.
- **BAGACO · 273 NmL/g SV** (CP2b acima, yaml acima) · tier C · Brazil · Marques_2023_bagasse · https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1158431/1/Producao-de-biogas-a-partir-de-bagaco.pdf
  - Nota da rotina: Embrapa conference abstract. It follows Holliger 2016 with a cellulose control, but the control result, duration and replicate count are not reported. The table has internal inconsistencies (per-kg-TS methane equals per-kg-VS at ISR 5:1). The value depends strongly on ISR (251 at 1:1, 273 at 3:1, 367 at 5:1), and 367 is likely inflated by inoculum effects. The ISR 3:1 value is reported here because the positive control was run at the same ratio. Slightly above PILAR's bagasse range (44-236).
- **CASCAS_CITROS · 131 NmL/g SV** (yaml abaixo) · tier B · Sweden · Wikandari_2015_orangepeel · https://doi.org/10.1155/2015/494182
  - Nota da rotina: Triplicate, method of Hansen et al. 2004 (not VDI/Holliger), thermophilic, ISR not stated, no positive control. Raw yield strongly depressed by limonene inhibition (chopped peel only 61 NmL/gVS) - illustrates downside risk; far below PILAR CASCAS_CITROS 398. Juice-industry peel, analogous to SP citrus industry stream.
- **CASCAS_CITROS · 360 NmL/g SV** (yaml acima) · tier B · Italy · Calabro_2017_ensiledOPW · https://doi.org/10.18280/ijht.35sp0118
  - Nota da rotina: BMP30 at 35 C, S/I ~0.3 gVS/gVS, NaHCO3 buffer, NaOH CO2 scrubbing; replicates not confirmed, no positive control; value read as 'about 360' (likely from figure). Close to PILAR CASCAS_CITROS 398 and above BAGACO_CITROS median 289. Mediterranean orange peel, comparable industrial stream. Ensiled 37 d: ~365.
- **PALHA_SOJA · 113 NmL/g SV** (CP2b abaixo, yaml abaixo) · tier C · China · Zhu_2017_soybeanstraw · https://bioresources.cnr.ncsu.edu/resources/integrated-methane-and-ethanol-production-from-livestock-manure-and-soybean-straw/
  - Nota da rotina: Weak protocol: ISR 1 (TS basis), no replicate count, no positive control, water displacement plus GC. The text says there was 'almost no methane from SS after 30 days', which conflicts with the table. The about 113 NmL/g VS figure is plausible for lignified straw (cf. Xiong 2020, untreated about 127). The 30-day value is 45.2 g/kg TS (about 64 mL/g VS).
- **VINHACA · 494 NmL/g SV** (yaml acima) · tier A · Brazil · Freitas_2023_vinasse · https://doi.org/10.3390/methane2040029
  - Nota da rotina: Good protocol (VDI 4630, cellulose positive control, inoculum blank, triplicate, STP-corrected, GC-TCD). Thermophilic (55 C) test, which tends to give higher yields than mesophilic. SP origin match (UNICAMP/LNBR group, Moraes). Value 494 is well above PILAR median 180 but inside PILAR range 49-968; high per-VS yields are typical of vinasse because VS underestimates volatile organics (ethanol, acids lost on drying). The authors report COD/TVS of 1.5-1.9.

## Substratos fora do CP2b (candidatos, sem faixa no artigo)

| Código | Registros | Brutos comparáveis | Mediana bruto | Faixa feedstocks.yaml |
|---|---:|---:|---:|---|
| BAGACO_MANDIOCA | 4 | 2 | 344 | — |
| BAGACO_UVA | 4 | 2 | 202 | — |
| CASCAS_CITROS | 3 | 2 | 246 | 160–290 (med 210) |
| CASCA_AMENDOIM | 1 | 0 | — | — |
| CASCA_BANANA | 1 | 1 | 322 | — |
| MANIPUEIRA | 2 | 0 | — | — |
| MUCILAGEM_CAFE | 2 | 1 | 294 | 260–390 (med 320) |
| POLPA_CAFE | 2 | 2 | 252 | 190–290 (med 245) |
| PSEUDOCAULE_BANANA | 3 | 1 | 347 | — |
| VINHACA_MILHO | 1 | 0 | — | — |

## Sem valor normalizado no registro (por DQO, biogás ou base de CNTP não confirmada)

- BAGACO_CITROS · 0.79 L biogas/g VS (accumulated, methanogenic reactor; ~60% CH4) · JimenezCastro_2020_orangepeel
- BAGACO_MANDIOCA · 306 mL CH4/g VS added · Panichnumsin_2010_cassavapulp
- BAGACO_MANDIOCA · 290 mL CH4/g VS (m3/kg VS as reported; normalisation basis not stated in abstract) · Awiszus_2017_cassavapulp
- BAGACO_UVA · 35.74 L CH4/kg TVS · Castro_2024_grapeSWH
- BAGACO_UVA · 256.88 L CH4/kg TVS · Castro_2024_grapeSWH
- CASCA_AMENDOIM · 48 mL CH4/g VS · Oliva_2023_peanutshell
- MANIPUEIRA · 249 mL CH4/g COD applied · Amorim_2019_manipueira
- MANIPUEIRA · 620 mL CH4/g VS · Achi_2020_cassavaww
- MUCILAGEM_CAFE · 0.153 L CH4 (STP)/g COD removed · VillaMontoya_2017_cpw
- PALHA_SOJA · 206 mL CH4/g VS · Xiong_2020_soybeanstraw
- TORTA_FILTRO · 185 mL CH4/g VS · Janke_2019_filtercake
- VINHACA_MILHO · 630 mL CH4/g VS fed · Lee_2011_thinstillage

## Como ler

- Os valores, DOIs e notas são os do registro do Literature Watch, com a verificação que a rotina registrou. Antes de citar um valor, abra a fonte.
- Tier A/B/C é a nota de qualidade da rotina (protocolo, réplicas, controle positivo).
- `ja_no_pilar` diz se a fonte já está no corpus de referências da plataforma.
