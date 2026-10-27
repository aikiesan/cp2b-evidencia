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
refazer o FL não roda aqui: precisa da malha viária do OSM, dos shapefiles e
cadastros de entrada, que ficam fora do git. Uma mudança que só mexe no FS
(C01) não muda o FL, porque o FS vem depois do N3.

A C02 (BMP do bagaço) foi rodada no fl_v5 numa cópia, com a alocação (`04b`)
refeita sobre a oferta de bagaço escalada (`../outputs/fl_espacial/`, §4).
O FL estadual muda no máximo 0,0046 (suínos, med), e o número de hubs quase
não muda (med 455 → 456, com 25 entrando e 24 saindo; contagem da rodada
no notebook, fora de `data/`). Por isso o N4 da C02
no `build_v52.py`, que mantém o FL da v5.1, vale para o estado. No município
a história é outra: 835 linhas município × substrato mudam mais de 0,01, até
±0,95 no leite e nos suínos do máx, porque a seleção gulosa troca hubs de
lugar. As bacias de cobertura (filtro dos candidatos) ficaram as da v5.1,
então esse efeito é um piso.

A perturbação da oferta (`../outputs/fl_espacial/`, §6) diz o mesmo de forma
geral: com ruído de 10 % a 30 % na oferta de cada município, o FL estadual med
fica em 0,912–0,928 e o ranking municipal mantém Spearman ≥ 0,98, mas os hubs e
o FL municipal por substrato mudam. Uma candidata que mexe na oferta de poucos
municípios pode, então, mudar o FL de municípios longe dela; o `build_v52.py`
não mede isso.

## Candidatas de hoje

- C01: FS da palha de cana pela decomposição no solo (espera o tempo entre
  colheita e enfardamento).
- C02: BMP do bagaço pelos três registros medidos (tier B e C; pedir um tier A
  antes de aceitar).
