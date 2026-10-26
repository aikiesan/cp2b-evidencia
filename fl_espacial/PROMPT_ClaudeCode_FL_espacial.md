# Prompt para Claude Code — FL espacial do Método CP2b

> Como usar: abra o Claude Code na pasta `C:\Users\Lucas\Documents\Reposicionamento_Submissão_ESD\Metodo_CP2b` e cole tudo o que está abaixo da linha.
> O prompt é autossuficiente e não depende do histórico da conversa.
> Há dois pontos de parada obrigatórios (CHECKPOINT) em que o Claude Code mostra os resultados e espera sua confirmação.

---

## 1. Contexto

Você vai trabalhar no **Método CP2b**, uma avaliação do potencial de metano de resíduos agroindustriais e urbanos nos 645 municípios de São Paulo, inspirada no DBFZ Resource Monitoring (Brosowski et al., 2016; Brosowski, 2021).

A cascata é calculada por município × substrato, **sempre em Nm³ de CH4** (biogás e biometano são derivados):

| Nível | Fórmula |
|---|---|
| N1 teórico | P1 = A × g × ST × SV × BMP |
| N2 técnico | P2 = P1 × FC |
| N3 mobilizável | P3 = max(0, P2 × FCo − U) — FCo desconta só usos excludentes; U = plantas existentes |
| **N4 acessível** | **P4 = P3 × FS × FL** |

O código atual (v4) está em `cp2b_params.py` e `cp2b_cascade.py`, e os resultados em `outputs/`. Hoje o **FL** (fator logístico) é um valor fixo por substrato, tirado de `feedstocks.yaml` (0,55–0,90), **sem validação espacial**. Uma revisão anterior (`Evidencias_CP2B_FC_FCo_FL.md`, seção 3) mostrou que os testes de raio já feitos no CP2b **não servem como calibração**: R² negativo, erro de unidade (rendimento por tonelada aplicado por hectare por dia) e coordenadas ANP deslocadas em até 41 km.

**Sua tarefa:** calcular um **FL espacial** por município × substrato × cenário (min/med/max) e integrá-lo à cascata como opção, gerando a v5 do Nível 4.

### Definição que deve orientar todo o trabalho

**FL mede a logística da matéria-prima**, do ponto de geração do resíduo até um local de conversão viável. Não é o alcance do produto (gás ou eletricidade até gasoduto ou subestação), que é outra análise do paper e **não deve ser misturada aqui**.

- FL(s, m) = fração do resíduo mobilizável (N3) do substrato *s* no município *m* situada a uma **distância por estrada** que permita levá-lo a um **hub viável**.
- **Hub viável** = local candidato cuja bacia de captação (todos os resíduos a menos do raio de cada substrato) soma pelo menos **Q_min** Nm³ CH4/dia de N3.
- O peso por distância é uma função de decaimento linear:
  - w(d) = 1 se d ≤ r1;
  - w(d) = (r2 − d) / (r2 − r1) se r1 < d < r2;
  - w(d) = 0 se d ≥ r2.
- O FL de cada célula é o maior w entre os hubs viáveis que a alcançam.
- **FL é cobertura, não alocação.** O mesmo resíduo não é somado duas vezes, e bacias sobrepostas não inflam o FL.

---

## 2. Dados (caminhos absolutos no Windows)

| Dado | Caminho | Uso |
|---|---|---|
| N3 por município × substrato × cenário | `...\Metodo_CP2b\outputs\cp2b_municipio_substrato.csv` (colunas `ibge, codigo, fluxo, cenario, L3_CH4`, etc.) | Oferta a espacializar (Nm³ CH4/ano; dividir por 365 para /dia) |
| Parâmetros e alocação das usinas | `...\Metodo_CP2b\cp2b_params.py`, `outputs\cp2b_usinas_alocacao.csv`, `outputs\cp2b_atividade_municipal.csv` | Pesos de cana moída/etanol por usina; atividade municipal |
| Rede viária OSM (Geofabrik Sudeste, jan/2026) | `C:\Users\Lucas\Documents\CP2B\Validacao_dados\02_LITERATURA\PROTOCO_CODIGESTAO\sudeste-260112-free.shp\gis_osm_roads_free_1.shp` | Grafo para distância por estrada (há um recorte de exemplo em `C:\Users\Lucas\_ORGANIZACAO_USUARIO\01_NOTEBOOKS_RASCUNHO\Untitled5.ipynb`) |
| Municípios SP 2024 | `C:\Users\Lucas\Documents\Pilar2b\cp2b-workspace\NewLook\backend\data\shapefiles\SP_Municipios_2024.shp` | Recorte, chave `CD_MUN` |
| Usinas de etanol (EPE 2018) | `...\Reposicionamento_Submissão_ESD\00_Primary_Data_Sources_PILAR2b\SHAPEFILES_MAPBIOMAS_10.1\INFRAESTRUTURA\structure_ethanol_plant\*.shp` (filtrar `UF == 'SP'`) | Fonte pontual de vinhaça/torta/bagaço e hub natural da palha |
| Plantas de biogás | `...\INFRAESTRUTURA\structure_biogas_plant\*.shp`, `...\Pilar2b\...\backend\data\shapefiles\Plantas_Biogas_SP.shp`, `...\Resultados em Mapas-20260807T123054Z-1-001\analysis\data\05_biogas_plants_brazil.csv` | Hubs existentes e validação |
| ETEs (ANA/Atlas Esgotos 2019) | `...\Pilar2b\...\backend\data\shapefiles\ETEs_2019_SP.shp` (usar `ETE_DS_STA == 'Ativa'`; tipo em `ETE_DS_TI`) | Fonte pontual do lodo (não-lagoa) |
| Áreas urbanas | `...\Pilar2b\...\backend\data\shapefiles\Areas_Urbanas_SP.shp` | Oferta de RSU e poda |
| MapBiomas 2024 (raster SP) | `...\Pilar2b\cp2b-workspace\NewLook\backend\data\mapbiomas\mapbiomas_agropecuaria_sp_2024.tif` (+ `00_Primary_Data_Sources_PILAR2b\07_MapBiomas\`, incluindo `Segunda_Safra_TIF`) | Espacializar palha de cana (classe 20), soja (39), outras temporárias/milho (41 + 2ª safra), café (46), citros (47); conferir o código das classes na legenda da Coleção 10 |
| Aves (GEDAVE) | `...\00_Primary_Data_Sources_PILAR2b\Relatorio_0082803826_granjas_aves_UNICAMP.xlsx` | Capacidade por estabelecimento; corte = "Estab. de Aves Comerciais de Corte"; postura = classes de postura/recria/matrizeiro. Ignorar capacidade 9.999.999 (sentinela) |
| Suínos | `C:\Users\Lucas\Documents\CP2B\_DATA_FILES\farms_for_gee.csv` (`tipo_animal`, `plantel` estimado) e `...\Relatorio_0082804098_granjas_sui_UNICAMP.xlsx` | Pontos de granja; o plantel é estimado (usar só como peso) |
| Bovinos (GEDAVE, 03/11/2025) | `C:\Users\Lucas\Documents\CP2B\Validacao_dados\02_LITERATURA\PROTOCO_CODIGESTAO\Relatorio_de_bovinocultura_intensiva_em_SP_03_11_2025(Bovino).csv` (latin-1) | Pontos de confinado (`SISTEMA_PRODUCAO == 'Confinado'`) e de leite (`FINALIDADE_PRINCIPAL in ['Leite','Mista']`), peso = `SALDO_GERAL`. **LGPD: ver regras** |
| Exclusões para hubs | `...\SHAPEFILES_MAPBIOMAS_10.1\STATE_PROTECTED_AREAS_INTEGRAL_PROTECTION_v2`, `FEDERAL_PROTECTED_AREAS_INTEGRAL_PROTECTION_v2`, `INDIGENOUS_TERRITORIES_v3` | Hubs candidatos não podem cair nessas áreas |

---

## 3. Método (etapas)

### Etapa 0 — Ambiente e reconhecimento

1. Criar um ambiente Python isolado (venv ou conda) com `geopandas pyogrio shapely>=2 rasterio rasterstats numpy pandas scipy pyyaml matplotlib`. Tentar também `pandana`. Registrar as versões em `fl_espacial/ambiente.txt`.
2. Criar a pasta `Metodo_CP2b\fl_espacial\` com `config_fl.yaml`, os scripts numerados e `outputs\`.
3. Projeção única para distâncias: **EPSG:5880** (SIRGAS 2000 / Policônica do Brasil), já usada pela equipe. SP cruza as zonas UTM 22 e 23, então **não usar UTM** para distâncias entre zonas.
4. Ler rapidamente os notebooks `Validacao_CP2B.ipynb` e `Untitled5.ipynb` (em `_ORGANIZACAO_USUARIO\01_NOTEBOOKS_RASCUNHO`) para reaproveitar leitura de dados. **Não reaproveitar** os resultados de buffer desses arquivos.

### Etapa 1 — Grafo viário

1. Ler `gis_osm_roads_free_1.shp` recortado ao estado de SP com um buffer de 50 km (bacias de municípios de divisa).
2. Manter `fclass` em: motorway, trunk, primary, secondary, tertiary (e seus `_link`), unclassified, residential, living_street, service, **track**.
   - Faça também uma versão **sem track/service** para análise de sensibilidade: estradas de fazenda importam para a coleta rural, mas o mapeamento OSM é desigual.
3. Construir o grafo não direcionado (nós = extremidades dos segmentos, peso = comprimento em metros no EPSG:5880). Manter só o maior componente conexo e reportar quanto da extensão foi descartado.
4. **Fator de tortuosidade (validação):** sortear 5.000 pares origem-destino a 1–60 km e calcular a razão distância na rede / distância euclidiana. Reportar a mediana e o P10–P90 por faixa de distância. Esse valor será o fallback se o roteamento completo for inviável.

### Etapa 2 — Espacializar a oferta (N3 por substrato, preservando o total municipal)

Para cada substrato e cenário, distribua o `L3_CH4` municipal (em Nm³ CH4/dia) conforme abaixo:

| Substrato (`codigo`) | Onde a oferta "nasce" | Peso dentro do município |
|---|---|---|
| VINHACA, TORTA_FILTRO, BAGACO | **Na usina** (ponto) | Mesma alocação da v4 (`cp2b_usinas_alocacao.csv`: etanol para vinhaça; classe de capacidade para torta/bagaço) |
| PALHA | Pixels de cana (MapBiomas 2024) | Área de cana |
| PALHA_MILHO | Pixels de outras temporárias + 2ª safra (ou soja se não houver raster de 2ª safra) | Área |
| PALHA_SOJA | Pixels de soja | Área |
| CASCA_CAFE | Pixels de café | Área (limitação: o resíduo nasce no beneficiamento) |
| BAGACO_CITROS | Pixels de citros | Área (limitação: nasce na fábrica de suco. Se houver lista georreferenciada de fábricas, usar e avisar) |
| AVES_CORTE / AVES_POSTURA | Pontos GEDAVE por tipo | Capacidade de alojamento |
| SUINOS | Pontos `farms_for_gee.csv` (suínos) | Plantel estimado |
| BOV_LEITE | Pontos GEDAVE Leite + Mista | `SALDO_GERAL` |
| BOV_CONFINADO | Pontos GEDAVE Confinado | `SALDO_GERAL` |
| BOV_PASTO_MISTO | — | N3 ≈ 0; ignorar |
| RSU_ORGANICO, PODA_URBANA | Áreas urbanas | Área urbana |
| LODO_ETE | ETEs ativas não-lagoa | Partes iguais entre as ETEs do município (limitação: sem vazão por ETE) |

- Municípios sem ponto ou pixel do tipo necessário: usar o centroide da área agropecuária (ou o centroide municipal) e **contar e listar** esses casos.
- Agregar tudo numa **grade de 1 km** (EPSG:5880); fontes pontuais (usinas, ETEs) ficam como pontos.
- **Verificação obrigatória:** soma da grade = soma municipal por substrato e cenário (tolerância 0,01%).

> **CHECKPOINT 1:** pare e mostre ao Lucas:
> - a tabela de totais (municipal × grade) por substrato;
> - os casos de fallback;
> - 3 mapas rápidos (palha, aves, lodo).
>
> Aguarde confirmação antes de seguir.

### Etapa 3 — Hubs candidatos

1. **Existentes:** usinas (160), plantas de biogás operantes, ETEs não-lagoa. A lista de aterros não está nos dados; perguntar ao Lucas se há um inventário CETESB/SNIS com coordenadas.
2. **Novos:** centroides de uma grade de 2 km a ≤ 2 km de uma via do grafo, fora das exclusões (proteção integral, terras indígenas).
3. Associar cada hub e cada célula de oferta ao nó mais próximo do grafo. Reportar a distância de conexão, a mediana e o P95.

### Etapa 4 — Bacias de captação e viabilidade

1. Para cada hub, somar a oferta de N3 (Nm³ CH4/dia) de cada substrato a uma distância de rede ≤ r2(s), ponderada por w(d).
   - Implementação preferida: `pandana.Network.aggregate(distance=r2, type='sum')` com as ofertas atribuídas aos nós, uma chamada por classe de raio.
   - Fallback: `scipy.sparse.csgraph.dijkstra(..., limit=r2)` a partir dos hubs, em lotes.
   - Último recurso: distância euclidiana × fator de tortuosidade da Etapa 1, que deve ser declarado.
2. Duas variantes:
   - **(a) co-digestão (principal)**: a bacia soma todos os substratos, cada um dentro do próprio raio;
   - **(b) monodigestão (sensibilidade)**: cada substrato sozinho.
3. Hub viável se a bacia ≥ Q_min (tabela de parâmetros).
4. FL da célula/ponto = max w(d) entre os hubs viáveis alcançados. FL municipal por substrato = Σ(oferta × FL) / Σ oferta.
   - Casos especiais: vinhaça/torta/bagaço na usina têm d = 0, logo FL = 1 se a usina for viável. Lodo na ETE também tem d = 0.
5. Cenários acoplados:
   - **min** = raios curtos + Q_min alto;
   - **med** = centrais;
   - **max** = raios longos + Q_min baixo.
6. Extra informativo (não entra no FL): cobertura máxima gulosa (greedy MCLP) para estimar quantos hubs seriam necessários para cobrir 50/80/95% da oferta.

### Etapa 5 — Validação e sensibilidade

- **Taxa de acerto:** % das plantas de biogás/biometano operantes em SP (ANP/SIGA/MapBiomas) situadas a ≤ 2 km de um hub viável. Reportar por tipo (aterro, usina, ETE, pecuária).
- **Curvas de sensibilidade:** FL estadual ponderado × r2 (5–60 km) por classe de substrato, e FL × Q_min (250–10.000 Nm³ CH4/dia).
- **Checagens:** FL ∈ [0, 1]; FL_min ≤ FL_med ≤ FL_max em todos os pares; comparação com o FL fixo da v4 (tabela substrato × FL_yaml × FL_espacial).
- **Robustez da rede:** mostrar o efeito de incluir ou não `track/service` no grafo.

> **CHECKPOINT 2:** mostre:
> - FL por substrato (estado) nas variantes co-digestão e mono, nos três cenários;
> - a taxa de acerto;
> - as curvas de sensibilidade;
> - os mapas de FL e de hubs viáveis.
>
> Aguarde confirmação antes de integrar.

### Etapa 6 — Integração à cascata (v5)

1. Gravar `fl_espacial\outputs\fl_municipio_substrato.csv` com as colunas `ibge, codigo, cenario, FL_codigestao, FL_mono, oferta_L3_m3dia, oferta_coberta_m3dia`.
2. Em `cp2b_params.py`, permitir `FL="espacial"` por substrato. Em `cp2b_cascade.py`, ler o CSV quando `FL == "espacial"`, com uma opção de configuração para escolher co-digestão ou mono.
3. **Não sobrescrever os resultados da v4.** Rodar a v5 gravando em `outputs_v5\`, ou com o prefixo `v5_`.
4. Tabela de reconciliação N4 v4 × v5 (estado, por fluxo, top 20 municípios).

---

## 4. Parâmetros iniciais (`config_fl.yaml`)

Valores de partida tirados das faixas levantadas em `Evidencias_CP2B_FC_FCo_FL.md`. Todos editáveis.

| Classe | Substratos | r1 / r2 (km): min | med | max | Fontes das faixas |
|---|---|---|---|---|---|
| Líquidos | SUINOS, BOV_LEITE, LODO_ETE (fora da ETE) | 3/10 | 5/15 | 10/20 | Dejetos líquidos 10–20 km; lodo 15–25 km |
| Sólidos úmidos | BOV_CONFINADO, AVES_CORTE, AVES_POSTURA, TORTA (fora da usina), BAGACO_CITROS, RSU_ORGANICO, PODA_URBANA | 10/20 | 15/30 | 20/45 | Cama de aves 30–35; esterco sólido até ~45 (Coldebella 2006); RSU 20–35 |
| Sólidos secos volumosos | PALHA, PALHA_MILHO, PALHA_SOJA, CASCA_CAFE, BAGACO (fora da usina) | 5/15 | 10/25 | 15/40 | Palha "< 10 km da usina" (Leal 2013); raio típico de abastecimento de cana |
| Na fonte | VINHACA, TORTA, BAGACO na usina; LODO na ETE | d = 0 | d = 0 | d = 0 | Resíduo gerado no local de conversão |

- **Q_min** (N3, Nm³ CH4/dia) para o hub ser viável: min **3.200** (≈ 500 kWe) / med **1.500** (≈ 240 kWe) / max **500** (≈ 80 kWe, escala de propriedade).
- Referência de biometano (só informativa, não entra no FL): contar hubs ≥ 10.000 Nm³ CH4/dia.
- **Para a palha**, testar também uma variante em que os únicos hubs são as usinas, porque elas já recolhem cana num raio de 25–40 km. Reportar a diferença.

---

## 5. Regras

1. **LGPD:** o arquivo bovino tem CPF/CNPJ e nomes. Ler só as colunas `LATITUDE, LONGITUDE, NOME_MUN, FINALIDADE_PRINCIPAL, SISTEMA_PRODUCAO, SALDO_GERAL`. Nunca gravar pontos individuais: toda saída é agregada na grade de ≥ 1 km ou por município. Nada de CPF, nome ou endereço em arquivos, logs ou figuras.
2. **Não alterar** o manuscrito (`.md`/`.docx` do paper), nem arquivos em `C:\Users\Lucas\Documents\CP2B` ou no repositório `Pilar2b`. Só ler.
3. **Não sobrescrever** `outputs\` da v4. Tudo novo fica em `fl_espacial\` e `outputs_v5\`.
4. **Unidades:** oferta em Nm³ CH4/dia (N3); distâncias em metros na rede (EPSG:5880); relatório em km.
5. **Reprodutibilidade:** scripts numerados (`01_grafo.py` … `06_integracao.py`), parâmetros só no `config_fl.yaml`, sementes fixas, log de cada etapa com tempos e contagens.
6. **Honestidade metodológica:** o FL resultante é uma estimativa de acessibilidade logística, não uma medição. Declarar no relatório todos os fallbacks e limitações, entre elas:
   - lodo sem vazão por ETE;
   - citros e café sem as fábricas;
   - plantel suíno estimado;
   - GEDAVE bovino com 48% sem sistema informado;
   - estoque do confinado em 03/11 (os ciclos giram).
7. Trabalhar etapa por etapa, respeitando os dois CHECKPOINTs.

---

## 6. Entregáveis

- `fl_espacial\` com:
  - scripts;
  - `config_fl.yaml`;
  - `ambiente.txt`;
  - `outputs\grade_oferta_1km.gpkg` (agregada);
  - `outputs\hubs_viaveis.gpkg`;
  - `outputs\fl_municipio_substrato.csv`;
  - figuras (curvas de sensibilidade, mapa de FL, mapa de hubs);
  - `RELATORIO_FL_espacial.md` com método, parâmetros, validação, sensibilidade, limitações e a tabela FL_yaml × FL_espacial.
- `outputs_v5\` com a cascata recalculada e a tabela de reconciliação N4 v4 × v5.

## 7. Perguntas a fazer ao Lucas quando surgirem

- Há inventário georreferenciado de aterros e transbordos (CETESB/SNIS) e de fábricas de suco/beneficiamento de café?
- Co-digestão como variante principal está confirmada?
- Os valores de Q_min e os raios da tabela 4 estão aprovados para a rodada final?
