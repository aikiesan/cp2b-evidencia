# CP2b v5.2 em construção

O PILAR-2b e a plataforma ficam congelados com a v5.1 até a submissão. A v5.2
nasce aqui: cada mudança de parâmetro é uma linha de `mudancas.csv`, e
`scripts/build_v52.py` mostra o que ela faz no N4, no ranking e no intervalo de
90 %, com o mesmo modelo que reproduz o snapshot v5.1.

Tudo o que o artigo cita fica como está; a referência é a tag `v5.1-artigo`.

## Como propor uma mudança

Uma linha em `mudancas.csv`:

| Coluna | O que vai |
|---|---|
| `id` | C01, C02, … (não reusar) |
| `status` | `candidata` (espera o time), `aceita` (decidida) ou `rejeitada` (fica registrada, não entra) |
| `codigo`, `elemento` | como em `cp2b_parametros.csv` (PALHA, FS; BAGACO, BMP; …) |
| `v51_min`, `v51_med`, `v51_max` | a faixa da v5.1; o script confere com o snapshot e recusa a linha se não bater |
| `min`, `med`, `max` | a faixa proposta, na unidade do CP2b |
| `registros`, `tier` | ids do Literature Watch (separados por `;`) e o tier de cada um |
| `justificativa` | de onde vêm os três números, em uma ou duas frases |
| `decisao` | a nota de decisão (DEC-…) quando a mudança for aceita |

Os números saem dos registros; nada de valor sem fonte. Uma mudança só passa a
`aceita` com a decisão do time escrita.

## Como rodar

```
python scripts/build_v52.py
```

Precisa do snapshot v5.1 (como os outros scripts). Sai em `outputs/v52/`:
cada mudança sozinha, as aceitas juntas e aceitas mais candidatas, com o N4
med, mín e máx, o p5–p95 e o ranking contra a v5.1.

## Quando a v5.2 fechar

As mudanças aceitas viram um patch para o PILAR-2b, aplicado e commitado pelos
mantenedores, não pelo Claude.

## O que ainda não dá para fazer aqui

O FL espacial entra como na incerteza: interpolado no N3 de cada município.
O código do fl_v5 (v5.1) está em `../fl_espacial/` (veja o LEIA-ME de lá), mas
refazer o FL ainda não roda aqui. O pipeline precisa da malha viária do OSM,
dos shapefiles e cadastros de entrada, que ficam fora do git, e de cerca de
1h40 de máquina. Enquanto isso, uma mudança que mexe no N3 (C02, BMP do
bagaço) entra com o FL da v5.1; uma que só mexe no FS (C01) não muda o FL,
porque o FS vem depois do N3.

## Candidatas de hoje

- C01: FS da palha de cana pela decomposição no solo (espera o tempo entre
  colheita e enfardamento).
- C02: BMP do bagaço pelos três registros medidos (tier B e C; pedir um tier A
  antes de aceitar).
