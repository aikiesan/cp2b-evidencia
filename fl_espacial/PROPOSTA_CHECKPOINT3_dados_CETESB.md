# Dados CETESB/DataGEO no FL espacial: inventário e proposta (CHECKPOINT 3)

> **Resolução de Lucas (24/09/2026): não forçar dados de RSU que não temos.**
> - Propostas 1–3 (RSU no aterro, uso existente pela bacia, ICTEM): **não implementadas**. Ficam registradas como limitação no artigo.
> - Proposta 4 (fábricas de suco): **implementada na v5.1** (decisão 7 do `RELATORIO_FL_espacial.md`).
> - Laticínios e sorvetes (arquivos de coordenadas que chegaram depois): só mapeados, no artigo e na plataforma.

> 24/09/2026 · leitura de `Reposicionamento_Submissão_ESD/DADOS_ESPACIAIS/`
> Nada foi alterado no pipeline, na cascata ou no banco, e **nenhuma passada pesada rodou**. Os números vêm das saídas da v5 já gravadas (`outputs/`, `outputs_v5/`, `fl_espacial/outputs/`).

## 1. O que há na pasta

| Arquivo | O que é | Cobertura | Serve para |
|---|---|---|---|
| `VWM_IQR_CETESB_2022–2024_POL` | IQR (0–10) do aterro usado pelo município + **`Dispoe_em`**: município de destino do RSU e tipo (A.P. = aterro particular, CDR, UF) | 645 polígonos municipais | **destino do RSU** (§2, §3) |
| `VWM_ICTEM_CETESB_2024_POL` | ICTEM (0–10), com código IBGE | 645, sem lacunas | FC do esgoto (§4) |
| `IGR2023–2025` | Índice de Gestão de Resíduos (IQG + disposição), com código IBGE | 567 / 591 / 597 com valor | contexto, fora do cálculo (§5) |
| `VWM_IQC_CETESB_2022–2024_POL` | IQC de usinas de compostagem | **2 municípios por ano** | evidência para o FCo do RSU (§5) |
| `dados_staging/rais_sp_cnaes_prioritarios.csv` | RAIS local, UF 35: 41.562 estabelecimentos com CNAE de 7 dígitos, CEP e vínculos. Sem ano, CNPJ ou coordenada | estabelecimento anônimo | fábricas de suco (§6) |
| `README.md`, `catalogo_dados.csv`, `problemas_qualidade.csv`, `fontes_prioritarias.csv`, `modelo_dados_pilar2b.md`, `auditoria/`, `scripts/` | Diagnóstico de 24/09 do pacote de dados do CP2B (bloqueia a camada industrial legada, entre outras coisas) | — | referência; nada a integrar no FL |
| `1790249213197.csv`, `document.kml` | Resultado de uma busca no catálogo DataGEO. Só metadados e retângulos envolventes: agências CETESB, áreas de restrição, emergências químicas | — | nada |
| `*_READ_ME.txt` | Metadados ISO das camadas | — | citação |

O que **não** está lá:
- **Não há `AreaUrbana.zip`.** O `AreaUrbana.shp` de `CP2B/Validacao_dados/03_DADOS_GEOESPACIAIS` é idêntico ao `Areas_Urbanas_SP.shp` que o pipeline já usa (36.916 polígonos, campos `CID`/`QAREA`). Não existe área urbana nova.
- **Nenhuma coordenada de aterro ou de transbordo.** Todas as camadas CETESB são polígonos municipais. O `estacao_transbordo_de_cargas` do MapBiomas lista 40 terminais de carga da ANTAQ no Brasil; não são transbordos de RSU.
- O IQT (transbordos) não vem separado; ele só entra dentro do IGR.

Armadilhas de leitura:
- **Código.** No IQR e no IQC, o campo `Codigo` é o código CETESB (100–794), não o IBGE. As geometrias são idênticas às do IGR e estão na mesma ordem (645/645), então a junção ao IBGE é feita pela geometria.
- **Codificação.** O `.cst` diz ISO-8859-1, e o pyogrio quebra nos nomes (`UnicodeDecodeError`). O DBF tem de ser lido em latin-1, à parte.
- **IQR = −1.** São os 8 municípios que dispõem fora de SP (MG, MS, RJ, SC).
- **`Dispoe_em` em branco (256 municípios)** = disposição no próprio município (aterro municipal). É a leitura coerente com os dados (Santo André, Osasco, São José dos Campos, Piracicaba, Franca), mas vale conferir no Inventário Estadual de Resíduos.
- **Mudanças de destino.** 46 municípios têm destino diferente entre 2022 e 2024. Usar 2024 e citar o ano.

## 2. Proposta 1: o RSU nasce no aterro de destino (análoga à palha nas usinas)

Hoje o RSU_ORGANICO nasce na área urbana e procura um hub pelo raio de sólidos úmidos. Mas o RSU coletado já vai todo dia para um aterro conhecido, e é lá que acontece a triagem do orgânico em que se baseia o FC (0,50/0,65/0,80). O `Dispoe_em` do IQR 2024 diz qual é esse aterro:

| Destino do RSU coletado (IQR 2024) | Municípios | RSU (Mt/ano) | % |
|---|---:|---:|---:|
| Aterro particular em outro município | 335 | 10,24 | 69,4 |
| Aterro particular no próprio município | 35 | 1,20 | 8,2 |
| CDR (São Paulo) | 7 | 0,65 | 4,4 |
| Próprio município (em branco), mais 4 destinos sem sufixo | 260 | 2,61 | 17,7 |
| Fora de SP | 8 | 0,04 | 0,3 |

A base é o `rsu_coletado_t` da cascata (14,75 Mt/ano). **82% do RSU vai para 40 municípios de destino.** Os maiores, com o número de municípios de origem:
- Caieiras (17), Paulínia (24), Iperó (12), Santana de Parnaíba (7), Onda Verde (22);
- Piratininga (25), São Paulo/CDR (7), Mauá (9), Guatapará (14), Catanduva (30).

**Implementação**
- `02_oferta.py`: o RSU dos 381 municípios com destino nomeado no `Dispoe_em` nasce no ponto do aterro. O `ref` é o mesmo do hub existente, então conta como "na fonte" (d = 0), pela mesma regra de vinhaça, torta e lodo.
- `03_hubs.py`: os 40 destinos entram como hubs existentes do tipo `aterro`.
- Continuam na área urbana, como hoje:
  - quem dispõe no próprio município;
  - os 8 municípios que mandam o RSU para fora de SP;
  - a poda (o IQR não informa o destino dela).

**Coordenadas.** 7 dos 40 destinos já têm ponto no pipeline: Caieiras, Paulínia, Guatapará, Tremembé, Mauá, Santana de Parnaíba (grafada "Santana do Parnaiba" no MapBiomas) e Jambeiro (via ZEG). Os dois pontos de São Paulo são provavelmente os aterros encerrados São João e Bandeirantes, não o CDR Pedreira. Faltam **33** coordenadas. Opções:
- a. **(recomendado)** Digitalizar do "Mapa de destinação de resíduos urbanos" da CETESB (link no `IQR_READ_ME.txt`). São ~33 pontos, e é a opção mais precisa.
- b. OSM `landuse=landfill` via Overpass. Não vem no shapefile Geofabrik que o pipeline usa, e é preciso conferir nome e município.
- c. Fallback: hub no município de destino, no nó do grafo mais próximo do centroide urbano, com `coord_tipo = centroide_municipio`.

Para o próprio RSU, a coordenada quase não importa (d = 0 por construção). Ela importa para a co-digestão, porque o aterro atrai poda, lodo e aves, e para a curva MCLP.

**Viabilidade** só com o RSU que chega a cada destino (N3, Nm³ CH4/dia):
- min: 3 destinos passam de 3.200 e recebem 44% desse RSU;
- med: 30 dos 40 passam do Q_min de 1.500 e recebem 97,8%;
- max: 39 passam de 500.

**Prévia do efeito.** É um limite inferior: FL = 1 só para quem manda o RSU a um destino viável apenas com RSU. Os demais municípios mantêm o FL da v5.

| Cenário | FL do RSU (v5 → proposta) | N4 do RSU (M Nm³ CH4/dia) |
|---|---|---|
| min | 0,52 → 0,62 | 0,047 → 0,052 |
| med | 0,95 → 0,98 | 0,422 → 0,432 |
| max | 1,00 → 1,00 | 1,582 → 1,584 |

No N4 estadual o efeito é pequeno (+0,06% no med). O ganho está no realismo da localização dos hubs e na §3.

**Custos e cuidados**
- **Exige a passada pesada.** O conjunto de hubs muda, o que invalida a assinatura do cache (~40 min por rede, duas redes). Convém agrupar com a Proposta 4 numa passada só.
- **Um destino por município.** Quando há mais de um aterro, o IQR dá a média ponderada. A capital aparece só como Caieiras, embora parte do RSU vá para a CTL, dentro da própria capital.
- **A taxa de acerto dos aterros deixa de ser um teste independente** (relatório §6: 80% em mono med), porque os aterros passam a ser hubs por construção. Reportar a taxa de acerto sem aterros, ou com e sem os destinos do IQR.

## 3. Proposta 2: uso existente do RSU pela bacia real do aterro (só a cascata)

Hoje o uso energético existente do RSU (163 M Nm³ CH4/ano) é abatido do N3 por região intermediária. Com o `Dispoe_em`, dá para abatê-lo na bacia de cada aterro. O cruzamento dos dois no cenário med:

| Município-sede | Uso existente (M Nm³ CH4/ano) | N3a do RSU da bacia IQR | Razão |
|---|---:|---:|---:|
| Caieiras | 63,4 | 99,9 | 0,63 |
| São Paulo | 56,2 | 14,4 | **3,90** |
| Guatapará | 10,0 | 7,8 | **1,28** |
| Tremembé | 7,5 | 4,6 | **1,64** |
| Santana de Parnaíba | 7,5 | 17,5 | 0,43 |
| Jambeiro | 5,1 | 9,7 | 0,52 |
| Catanduva | 2,5 | 4,8 | 0,53 |
| Paulínia | 0,0 | 17,5 | 0,00 |

Dois achados:
- **Gás de aterro encerrado.** Em São Paulo, 46 M Nm³ CH4/ano vêm de São João (37,9) e Bandeirantes (8,1), dois aterros já fechados. Esse gás sai do resíduo antigo e não compete com o orgânico gerado hoje, que é o que o N3 mede. Quando o abatimento é feito por região, o problema fica diluído. Pela bacia, ele aparece.
- **Duas usinas SIGA "Biogás - RU" em municípios sem aterro de destino:** PCT Barueri Biogás (Carapicuíba, 4,6) e Ambient (Ribeirão Preto, 2,6). Pelo nome e pelo local, parecem ser biogás de ETE (Sabesp em Barueri; concessionária de esgoto de Ribeirão Preto), não de aterro. Se isso se confirmar, as duas passam para o fluxo do esgoto.

**Implementação** em `cp2b_cascade.py`: o U do fluxo rsu passa a ser alocado pela bacia IQR do município-sede. Onde não houver bacia, fica a região intermediária, como hoje. Roda em minutos, sem passada pesada.

## 4. Proposta 3: ICTEM no FC do esgoto, como faixa (só a cascata)

Hoje o FC do lodo é o atendimento (IN056) × o tratamento (IN016) × a fração de ETEs compatíveis, e é o mesmo nos três cenários.

O ICTEM é um índice composto de 0 a 10 que reúne:
- coleta e tratamento;
- eficiência de remoção (≥ 80%);
- corpo receptor e destino do lodo.

Como não é uma fração da população atendida, ele não substitui o IN056 × IN016. Mas é uma segunda fonte, independente: a CETESB, em vez do prestador que responde ao SNIS.

| | IN056 × IN016 (SNIS 2022) | ICTEM/10 (2024) |
|---|---:|---:|
| Média ponderada pela população | 0,773 | 0,709 |
| São Paulo | 0,945 | 0,683 |
| Guarulhos | 0,176 | 0,319 |
| São José dos Campos | 0,955 | 0,713 |
| Santos (emissário; o FC já é 0 pela fração de ETEs) | 0,959 | 0,584 |

As duas fontes concordam pouco:
- a correlação de Spearman é de só 0,46;
- 90 municípios (3,35 M hab.) diferem em mais de 0,3;
- nos 30 municípios em que o índice SNIS é 0 (0,56 M hab.), o ICTEM/10 médio é 0,36.

**Proposta**
- med = SNIS. É uma fração definida, e é o que gera o volume de lodo.
- min = min(SNIS, ICTEM/10); max = max(SNIS, ICTEM/10).
- ICTEM/10 como fallback onde o SNIS falta (2 municípios, hoje preenchidos com a mediana) ou é 0 (30 municípios).

**Referência de efeito.** Trocar tudo pelo ICTEM levaria o N4 do lodo (med) de 117,3 para 102,7 mil Nm³ CH4/dia (−12%), ou −0,09% do N4 estadual.

## 5. O que não entra no cálculo

- **IQR (a nota) e IGR.** Medem a qualidade da instalação e da gestão, sem ligação calibrada com logística ou coletabilidade. Usá-los no FC ou no FL seria arbitrário.
  - Os 30 municípios com IQR ≤ 7 dispõem todos no próprio município, e nenhum destino regional é inadequado. Um filtro por IQR não mudaria os hubs.
  - Os dois índices ficam como camadas de contexto no PILAR-2b.
- **IQC.** A CETESB avaliou só 2 usinas de compostagem de RSU por ano: São José do Rio Preto, e Ribeirão Grande (2022–23) ou Salto (2024). Isso é evidência documental para FCo do RSU = 1,0, porque quase não há compostagem concorrente. Citar em `Evidencias_CP2B_FC_FCo_FL.md`.
- **Área urbana.** Não há camada nova.
  - O `URBAN_CENSUS_TRACTS_v1` do MapBiomas tem 5.570 feições no Brasil, um setor por município. Não serve para densidade intraurbana.
  - Com a Proposta 1, a espacialização urbana só vale para os ~18% de RSU com disposição própria e para a poda (0,4% do N3). Não compensa agora.

## 6. Proposta 4: fábricas de suco pela RAIS (pendência do relatório; muda o N3)

A subclasse 1033-3/01 (sucos concentrados) do staging RAIS reproduz as fábricas conhecidas. Em vínculos:
- Matão: 7 estabelecimentos, 1.648 vínculos;
- Araraquara 887, Bebedouro 848, Colina 780, Itajobi 775;
- também Araras, Catanduva, Taquaritinga, Conchal, Engenheiro Coelho e Uchoa.

São 23 estabelecimentos com ≥ 100 vínculos, em 18 municípios. Os de São Paulo, Santos e Guarujá são escritórios e terminais portuários de suco e saem da conta. O CEP permite geocodificar pelo centroide do CEP.

**Proposta.** Realocar o N3 do BAGACO_CITROS para as fábricas, com peso pelos vínculos, como a v4 fez com as usinas. O bagaço passa a nascer na fonte. Isso muda o N3, então é decisão sua, e convém rodar junto da Proposta 1.

**Limitações.** A RAIS local não tem ano nem CNPJ, e os vínculos medem emprego, não capacidade de processamento. Por isso o staging não deve ir para o banco.

**Café.** A subclasse 1081-3/01 (beneficiamento) tem só 9 estabelecimentos. A casca continua nos pixels, porque o beneficiamento acontece sobretudo na fazenda.

## 7. Ordem sugerida

1. **Só a cascata (minutos):** Propostas 2 e 3, mais a reclassificação de Barueri e Ribeirão Preto.
2. **Uma passada pesada (~1h20, as duas redes):** Proposta 1, com as 33 coordenadas, e a Proposta 4, se aprovada.
3. **Reconciliação v5 × v5.1** (estado, fluxo, top 20 municípios), com e sem lignocelulósicos.

## 8. Decisões para o CHECKPOINT 3

1. **RSU no aterro.** O RSU passa a nascer no aterro de destino do IQR 2024? Se sim, de onde vêm as 33 coordenadas: (a) mapa CETESB, (b) OSM ou (c) centroide?
2. **Gás de aterro encerrado.** O gás de São João e Bandeirantes continua sendo abatido do N3? E o U do RSU passa a ser alocado pela bacia IQR?
3. **Reclassificação.** PCT Barueri Biogás e Ambient (Ribeirão Preto) passam do fluxo rsu para o do esgoto?
4. **ICTEM.** Entra como faixa min/max do FC do esgoto e como fallback do SNIS?
5. **Fábricas de suco.** A RAIS 1033-3/01 entra nesta rodada, junto da passada pesada?
