# Mapas da incerteza do N4 do CP2b v5.1

> Redesenho de `outputs/incerteza_cp2b/ranking.csv`; nenhum número novo. Malha: API de malhas do IBGE (v3): https://servicodados.ibge.gov.br/api/v3/malhas/estados/35?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio (sha256 `a9296e20334db2f4…`).

| Mapa | O que mostra |
|---|---|
| `mapa_n4_med.png` | N4 municipal no med do CP2b, mi Nm³/ano |
| `mapa_prob_top50.png` | fração dos sorteios em que o município fica no top 50 |
| `mapa_amplitude.png` | (p95 − p5) / med do N4 municipal |
| `mapa_cenarios.png` | N4 do cenário contra o med, município a município, um painel por cenário |

Municípios no ranking: 645; com polígono na malha: 645.
N4 med zero: 27 municípios (por região intermediária: Sorocaba 17; São José dos Campos 8; São Paulo 2).

Na fronteira do top 50 (entre 10 % e 90 % de chance): 13 municípios.

## Cenários

| Painel | Cenário | Municípios com queda > 5 % | Com alta > 5 % |
|---|---|---:|---:|
| leite_g | g do bovino de leite = excreção medida | 0 | 235 |
| leite_fc1 | g do leite já é a fração coletável: FC = 1 | 0 | 118 |
| confinado_ms | matéria orgânica fecal do confinado = medida | 23 | 0 |
| confinado_fc | FC do confinado = 0,9 (coleta no alojamento) | 0 | 15 |
| pasto_g | g do bovino de pasto = inventário nacional | 0 | 0 |
| citros_fco | FCo do bagaço de laranja = sobra após a peletização | 11 | 0 |
| palha_fs | FS da palha de cana = massa após decomposição no solo | 371 | 0 |
| bagaco_bmp | BMP do bagaço de cana = medido (bruto) | 0 | 110 |
| soja_bmp | BMP da palha de soja = medido (bruto) | 112 | 0 |
| literatura_g_total | Toda a literatura, g do leite = excreção total | 308 | 142 |
| literatura_g_coletavel | Toda a literatura, g do leite = fração coletável (FC = 1) | 357 | 96 |

## Como ler

- As classes são fixas e iguais entre rodadas, para que dois mapas se comparem a olho.
- Cinza claro é sem dado, ou N4 med zero quando a medida é relativa ao med.
- O intervalo de 90 % supõe parâmetros independentes (ver `outputs/incerteza_cp2b/RELATORIO.md`).
- Escala dos cenários: ≤ −20 %, −20 a −10 %, −10 a −5 %, −5 a −1 %, ±1 %, +1 a +5 %, +5 a +10 %, +10 a +20 %, ≥ +20 %; vermelho é queda, azul é alta.

