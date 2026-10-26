# FL espacial: Método CP2b (v5.1 do Nível 4, versão final para o artigo)

> 24/09/2026 · `Metodo_CP2b/fl_espacial/` · base volumétrica: **Nm³ CH4** (N3 ÷ 365 = Nm³ CH4/dia)
> Status: **v5.1 aplicada e rodada do zero** (passada pesada nas duas redes). É a v5 do CHECKPOINT 2 (variante B + palha nas usinas) com o bagaço de citros nas fábricas de suco (decisão 7).
> Backups: a v5.0 está em `outputs_v5.0_bak/`, `fl_espacial/outputs_v5.0_bak/`, `*_v5.py.bak` e `patch_v5/*_v5.0.*.bak`; a v4 continua em `outputs/` e `*_v4.py.bak`.
> **Nada foi aplicado ao banco**, e o manuscrito e o repositório `Pilar2b` não foram alterados.
> Pacotes: artigo em `Submissão ESD + Data in Brief/Pacote_CP2b_v5.1/`; plataforma em `Metodo_CP2b/outputs_v5/plataforma/`.

## Decisões do CHECKPOINT 2 e onde estão implementadas

| # | Decisão | Implementação |
|---|---|---|
| 1 | Variante principal **B** (co-digestão com alocação); A = limite superior; D = limite inferior; as quatro em `outputs_v5` | `04b_alocacao.py`, `06_integracao.py`, `config_fl.yaml → integracao.variante_principal` |
| 1b | Robustez: recalcular o FL como max w(d) só sobre os hubs selecionados; reportar as duas versões se \|ΔFL\| > 0,02 | `04b` seção 4, `outputs/fl_alocado_robustez.csv` (ver §4) |
| 2 | Palha só nas usinas (SP + divisa MG/PR/MS); raios = percentis ponderados da distância por estrada (P50/P90, P75/P95, P90/P99); fora da viabilidade dos hubs; milho e soja seguem com hubs gerais; comparar com "palha em qualquer hub" | `03b_palha_usinas.py`; `04`/`04b` com dois modos de palha; arquivos `*_palha_qualquer_hub.csv` |
| 3 | Q_min 3.200 / 1.500 / 500 Nm³ CH4/dia | `config_fl.yaml` |
| 4 | Patch da cascata com backup `*_v4.py.bak`; `requirements.txt` com pandas 2.2; v5 + reconciliação com e sem lignocelulósicos | `cp2b_params.py` e `cp2b_cascade.py` (v5); `Metodo_CP2b/requirements.txt` e `.venv`; `07_reconciliacao_v5.py` |
| 5 | Banco: nada aplicado; SQL de rascunho terminando em ROLLBACK | `outputs/banco/` (a migração será única, depois de fechar o método) |
| 6 | Curva MCLP da B com a palha nas usinas; taxa de acerto da monodigestão | `05`, `outputs/mclp*.csv`, `outputs/validacao_taxa_acerto.csv` |
| 7 | **v5.1:** bagaço de citros nasce nas fábricas de suco concentrado (RAIS 1033-3/01, ≥ 100 vínculos, sem escritórios e portos: 20 estabelecimentos em 14 municípios). A laranja da PAM (total SP) é alocada ∝ vínculos; um ponto por município no centroide urbano, que é hub existente "na fonte". RSU e esgoto seguem como na v5.0: não forçar dados sem coordenada (proposta de 24/09 em `PROPOSTA_CHECKPOINT3_dados_CETESB.md`) | `00_fabricas_suco.py` (base N3 `outputs/n3_base_v51.csv`), `02`, `03`, `cp2b_cascade.py` v5.1 |

## 1. Por que a alocação virou a variante principal

A definição original ("FL é cobertura") **não discrimina** quando há hubs candidatos em toda parte e a oferta é densa. Em SP o N3 médio é de ~77 Nm³ CH4/dia por km², e na co-digestão por cobertura (A) quase todo hub é viável. O FL fica em ~1,0 no med e no max para quase todos os substratos e só cai no Vale do Ribeira, na Serra do Mar e no Litoral Norte.

Na variante B:
- cada resíduo é contado uma vez;
- os hubs entram em ordem de resíduo acrescentado;
- um hub só entra se esse acréscimo for ≥ Q_min.

O FL resultante é o w(d) do hub selecionado mais próximo.

## 2. Palha de cana nas usinas (decisão 2)

A distância por estrada de cada célula com cana até a usina mais próxima foi medida para 160 usinas de SP e 26 de divisa, e ponderada pela oferta de palha no N3 med:

| | P25 | P50 | P75 | P90 | P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| Por estrada (km) | 12,9 | **19,5** | **27,2** | **35,2** | **41,7** | **53,8** |
| Euclidiana × 1,30 (km) | 10,6 | 16,6 | 23,8 | 31,0 | 37,2 | 49,5 |
| Sua estimativa prévia (km) | — | 17 | 24 | 31 | 37 | 50 |

Raios r1/r2: min 19,5/35,2; med 27,2/41,7; max 35,2/53,8 km. **FL da palha: 0,74 / 0,88 / 0,96.** As usinas de divisa são as mais próximas para só 0,5% da palha.

- **Propriedade de método.** Com r1 e r2 tirados da mesma distribuição, o FL cai necessariamente entre as frações dos dois percentis (0,50–0,90, 0,75–0,95 e 0,90–0,99). Ou seja, ele reflete a escolha dos percentis mais do que a acessibilidade. O que o espaço informa é a variação entre municípios.
- **Sensibilidade** (`sensibilidade_palha_usinas.csv`):

  | Raios | FL da palha (med) |
  |---|---:|
  | P25/P75 | 0,51 |
  | P50/P99 | 0,86 |
  | Sólidos secos gerais, med (10/25 km) | 0,42 |

- **Comparação lado a lado.** Com a palha em qualquer hub, o FL da palha em B é 0,49 / 0,95 / 1,00. Nesse modo, a palha também sustenta a viabilidade dos hubs da grade: no min, 44,5% dos hubs viáveis, contra 23,3% com a palha nas usinas.

## 3. FL estadual por substrato (min / med / max, ponderado pela oferta N3; v5.1)

| Substrato | % N3 | yaml v4 | **B (principal)** | A (sup.) | C | D (inf.) | B, palha em qualquer hub |
|---|---:|---|---|---|---|---|---|
| PALHA | 43,0 | 0,78/0,85/0,92 | **0,74/0,88/0,96** | 0,74/0,88/0,96 | 0,74/0,88/0,96 | 0,74/0,88/0,96 | 0,49/0,95/1,00 |
| TORTA_FILTRO | 13,4 | 0,78/0,85/0,92 | **1,00/1,00/1,00** | 1,00/1,00/1,00 | 0,97/1,00/1,00 | 0,91/0,99/1,00 | 1,00/1,00/1,00 |
| VINHACA | 12,6 | 0,88/0,90/0,92 | **0,99/1,00/1,00** | 1,00/1,00/1,00 | 0,99/1,00/1,00 | 0,98/1,00/1,00 | 0,99/1,00/1,00 |
| BAGACO | 11,7 | 0,85/0,90/0,98 | **0,99/1,00/1,00** | 1,00/1,00/1,00 | 0,62/1,00/1,00 | 0,55/0,99/1,00 | 1,00/1,00/1,00 |
| AVES_CORTE | 3,9 | 0,65/0,75/0,85 | **0,52/0,97/1,00** | 0,89/1,00/1,00 | 0,50/0,98/1,00 | 0,35/0,88/0,99 | 0,76/0,99/1,00 |
| PALHA_MILHO | 3,5 | 0,35/0,67/0,75 | **0,14/0,84/0,99** | 0,49/1,00/1,00 | 0,00/0,86/1,00 | 0,00/0,66/0,96 | 0,29/0,90/0,99 |
| PALHA_SOJA | 3,4 | 0,30/0,55/0,70 | **0,12/0,83/0,99** | 0,47/1,00/1,00 | 0,00/0,84/1,00 | 0,00/0,61/0,95 | 0,27/0,92/1,00 |
| RSU_ORGANICO | 2,3 | 0,70/0,82/0,90 | **0,52/0,95/1,00** | 0,82/0,99/1,00 | 0,35/0,91/1,00 | 0,27/0,78/0,98 | 0,66/0,96/1,00 |
| AVES_POSTURA | 1,6 | 0,62/0,70/0,78 | **0,52/0,97/1,00** | 0,83/1,00/1,00 | 0,41/0,93/1,00 | 0,32/0,83/0,98 | 0,73/0,99/1,00 |
| BOV_LEITE | 1,1 | 0,60/0,68/0,76 | **0,03/0,31/0,89** | 0,29/0,90/1,00 | 0,00/0,04/0,98 | 0,00/0,02/0,83 | 0,10/0,49/0,91 |
| BOV_CONFINADO | 0,9 | 0,52/0,65/0,85 | **0,35/0,98/1,00** | 0,68/1,00/1,00 | 0,10/0,90/0,99 | 0,10/0,83/0,97 | 0,79/0,99/1,00 |
| LODO_ETE | 0,7 | 0,82/0,90/0,95 | **0,42/0,84/0,99** | 0,67/0,99/1,00 | 0,28/0,75/0,98 | 0,28/0,69/0,97 | 0,44/0,85/0,99 |
| BAGACO_CITROS | 0,6 | 0,65/0,75/0,85 | **0,62/1,00/1,00** | 0,96/1,00/1,00 | 0,39/1,00/1,00 | 0,22/1,00/1,00 | 0,98/1,00/1,00 |
| SUINOS | 0,4 | 0,55/0,72/0,88 | **0,04/0,53/0,93** | 0,48/0,98/1,00 | 0,00/0,38/0,81 | 0,00/0,24/0,71 | 0,11/0,66/0,94 |
| PODA_URBANA | 0,4 | 0,60/0,75/0,90 | **0,46/0,95/1,00** | 0,68/0,99/1,00 | 0,00/0,59/1,00 | 0,00/0,48/0,93 | 0,55/0,96/1,00 |
| CASCA_CAFE | 0,3 | 0,55/0,65/0,75 | **0,06/0,77/0,99** | 0,33/1,00/1,00 | 0,00/0,76/0,98 | 0,00/0,50/0,90 | 0,18/0,83/0,99 |

BOV_PASTO_MISTO não foi espacializado e mantém o FL do yaml (0,52/0,65/0,85). Todos os triplos são monotônicos.

**v5.1 × v5.0.** Com o bagaço nas fábricas, o FL do citros em B passa de 0,19/0,86/0,99 para 0,62/1,00/1,00. Os outros substratos variam no máximo 0,01, porque alguns hubs da grade perderam a oferta dos pomares de citros. A exceção é o BOV_CONFINADO no min (0,42 → 0,35). Arquivos: `outputs/fl_v5_*_substrato.csv` (o que a cascata lê) e `outputs/banco/fl_parametros_residuos.csv`.

## 4. Robustez

- **Checagem pedida (1b): max w(d) só sobre os hubs selecionados, por Dijkstra.** Deu \|ΔFL\| = 0,0000. Isso é por construção: o FL de B já é o max w sobre os selecionados, e a checagem só confirma a contabilidade gulosa. Não é evidência de robustez.
- **Checagem com poder de teste: atribuição exclusiva iterada.** Cada resíduo vai só ao hub selecionado de maior w, e os hubs com bacia exclusiva abaixo do Q_min saem.
  - B med: 455 → 447 hubs; min: nenhum sai; max: 752 → 751.
  - \|ΔFL\| estadual máximo: 0,0013 em co-digestão e 0,0001 em monodigestão, abaixo de 0,02.
  - Por isso uma única versão é reportada (`fl_alocado_robustez.csv`, `fl_alocado_robustez_poda.csv`).
- **Rede sem track/service.** A palha usa os raios do grafo completo, e só as distâncias mudam. Na cobertura, \|ΔFL\| estadual máximo foi 0,021 em co-digestão (LODO_ETE min) e 0,009 em mono (`robustez_rede.csv`), iguais aos da v5.0. A tortuosidade mediana foi 1,30 com o grafo completo e 1,31 sem track/service.
- **Reprodutibilidade.** O pipeline inteiro foi refeito do zero no ambiente fixado (pandas 2.2.3). Histogramas (1,3 GB), bacias, distâncias e todas as tabelas de FL saíram idênticos aos da execução com pandas 3.
- **Revisão independente.** Três revisores (decisões, numérico, encadeamento/pandas) leram o código. Todos os achados foram corrigidos:
  - robustez de rede da palha anulada por raios recalibrados;
  - rótulos `FL_fonte` truncados;
  - cache de pares sem assinatura;
  - soma com arredondamento diferente (FL = 1,0000000000000002);
  - parada da alocação estrita no Q_min;
  - arredondamento de r1 na sensibilidade;
  - diff do patch desatualizado;
  - SQL afirmando monotonicidade sem conferir;
  - chaves de configuração sem uso.

## 5. Efeito no Nível 4 (cascata v5.1 × v4; `outputs_v5/reconciliacao_v4_v5_*.csv`)

A "v4" é a mesma base N3, com o FL do yaml. Desde a v5.1 essa base já traz o bagaço de citros nas fábricas: os totais estaduais da v4 não mudam, só a distribuição municipal do citros.

| Base | Cenário | N3 | N4 v4 | **N4 v5.1 (B)** | Δ | A | C | D |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Com lignocel. | min | 7,73 | 5,12 | **5,16** | +0,7% | 5,48 | 4,88 | 4,76 |
| Com lignocel. | **med** | 19,18 | 14,82 | **16,36** | **+10,4%** | 16,81 | 16,24 | 15,73 |
| Com lignocel. | max | 44,96 | 39,55 | **42,68** | +7,9% | 42,83 | 42,75 | 42,36 |
| Sem lignocel. | min | 3,04 | 2,11 | **2,29** | +8,9% | 2,50 | 2,22 | 2,12 |
| Sem lignocel. | med | 7,36 | 5,68 | **6,54** | +15,0% | 6,79 | 6,40 | 6,16 |
| Sem lignocel. | max | 17,36 | 15,01 | **16,62** | +10,7% | 16,75 | 16,67 | 16,40 |

Valores em M Nm³ CH4/dia.

**FL efetivo por fluxo (med), v4 → B:**

| Fluxo | v4 | B |
|---|---:|---:|
| Cana | 0,87 | 0,93 |
| Aves | 0,74 | 0,97 |
| Soja | 0,55 | 0,83 |
| Milho | 0,67 | 0,84 |
| RSU | 0,82 | 0,95 |
| Poda | 0,75 | 0,95 |
| Citros | 0,75 | 1,00 |
| Café | 0,65 | 0,77 |
| Esgoto | 0,90 | 0,84 |
| Bovinos | 0,67 | 0,59 |
| Suínos | 0,72 | 0,53 |

N4 v5.1 × v4 por fluxo: bovinos −11%, esgoto −7%, suínos −26%; soja +50%, citros +33%, aves +32%.

**v5.1 × v5.0:** o N4 estadual med fica em 16,361 contra 16,360 M Nm³ CH4/dia. O N4 do citros sobe 16,6% (de 0,085 para 0,099). No município, Matão ganha 21 mil Nm³/dia, Araraquara 12 mil, Itajobi 10 mil e Colina e Bebedouro 10 mil cada. Os municípios que só têm pomares perdem até 4,5 mil (Casa Branca).

**Top 5 municípios:** a ordem não muda (Guaíra, Morro Agudo, Sertãozinho, Pontal, Pitangueiras), e o N4 sobe 12–15% em cada um.

## 6. Validação: taxa de acerto (plantas operantes a ≤ 2 km de um hub viável)

A base tem 46 plantas com tipo conhecido: ANP, com a reclassificação da v4, e MapBiomas 10.1, sem duplicatas. Mais 84 plantas sem tipo vêm do PILAR.

| Tipo | n | **Monodigestão med** | Mono min | Mono max | Co-digestão min | Co-digestão med |
|---|---:|---:|---:|---:|---:|---:|
| Usina | 5 | **100%** | 60% | 100% | 100% | 100% |
| Aterro | 10 | **80%** | 0% | 100% | 20% | 100% |
| Pecuária | 19 | **68%** | 0% | 100% | 53% | 100% |
| ETE | 2 | **50%** | 0% | 100% | 0% | 100% |
| **Todas com tipo** | 46 | **75%** | 8% | 100% | 50% | 100% |

A monodigestão med é o teste que discrimina. A co-digestão med dá 100%, porque quase tudo é viável.

Os erros:
- **ETE:** o piloto de Franca, onde o lodo sozinho dá ~560 Nm³ CH4/dia, abaixo do Q_min.
- **Pecuária:** plantas de pequeno porte (Itararé, Coronel Macedo, Ibiúna, Colina).

O teste mede coerência, não calibra o FL.

## 7. Planejamento: curva MCLP da variante B, palha nas usinas (med)

A palha coberta pelas usinas soma 37,7% do N3 total. Os hubs necessários, em ordem gulosa, com candidatos entre os existentes e a grade de 4 km:

| Meta | N3 total (palha nas usinas) | N3 sem palha |
|---|---:|---:|
| 50% | **16 hubs** | 55 |
| 80% | **114 hubs** | 143 |
| 95% | não atingível (máx. 94,5%, porque a palha nas usinas fica em 88%) | 438 |

A variante B para em **455 hubs** (v5.0: 465), quando o resíduo acrescentado cai abaixo do Q_min. Nesse ponto ela cobre 95,3% do N3 sem palha e 92,0% do N3 total. Dos 455 hubs, 423 são da grade e 32 existentes: 14 plantas de biogás, 12 usinas, 4 ETEs e 2 fábricas de suco. Arquivos: `mclp.csv`, `mclp_curva_B.csv`; figura `figuras/mclp_curva_B.png`.

## 8. Sensibilidade (med, sem a palha; `sensibilidade_r2.csv`, `sensibilidade_qmin.csv`)

- **Raio:** em co-digestão, o FL por classe fica ≥ 0,94 mesmo com r2 = 5 km. Em mono, com r2 = 5 km, os sólidos secos caem para 0,62, os úmidos para 0,77 e os líquidos para 0,88.
- **Q_min** de 250 a 10.000:
  - co-digestão: 1,00 → 0,98;
  - monodigestão: 0,99 → 0,77 (líquidos 0,97 → 0,81; secos 1,00 → 0,70).

## 9. Arquivos para o banco (nada aplicado)

`outputs/banco/`: `fl_parametros_residuos.csv` (triplos por resíduo nas variantes e mapeamento CP2b → yaml → `residuos.codigo`), `fl_municipio_substrato_banco.csv`, `v5_n4_municipio_fluxo.csv`, `rascunho_update_residuos_fl.sql` (variante B; termina em ROLLBACK) e `LEIA-ME.md`.

A migração será única, depois de fechar FS, os parâmetros provisórios e a nomenclatura CH4 das colunas `*_biogas_m3_year`. Nesse momento, conferir os slugs ORGANICO_RSU e PODA_URBANA.

## 10. Limitações

1. **Lodo:** o N3 é dividido em partes iguais entre as ETEs, porque não há vazão por ETE. 26 municípios sem ETE compatível usam o centroide urbano.
2. **Citros e café.** Desde a v5.1, o bagaço de citros está nas fábricas de suco.
   - As fábricas vêm da RAIS local (sem ano, anônima), com peso pelos vínculos e o ponto no centroide urbano do município.
   - A casca de café segue nos pixels de cultivo: o beneficiamento é na fazenda, e a RAIS tem só 9 estabelecimentos de beneficiamento (1081-3/01), com 14 vínculos.
3. **Suínos:** o plantel é estimado e só serve de peso. **Bovinos:** 48% do cadastro GEDAVE não tem sistema informado, e o estoque do confinado é de uma única data.
4. **Aterros e RSU.** Só os aterros com biogás operante entram como hubs existentes, e o RSU nasce nas áreas urbanas.
   - O IQR da CETESB informa o aterro de destino de 381 municípios, mas só 7 desses aterros têm coordenada.
   - Decisão de 24/09: não mover o RSU sem coordenada (ver `PROPOSTA_CHECKPOINT3_dados_CETESB.md`).
   - Por isso dois aterros (Jambeiro, Guatapará) falham na taxa de acerto em mono.
5. A **viabilidade da alocação** é heurística (gulosa), com candidatos na grade de 4 km mais os existentes.
6. A **conexão ao grafo** vai ao nó mais próximo (mediana de 513 m), o que é conservador.
7. **PAM × MapBiomas:** o total segue a PAM, e a densidade fica baixa onde há muito pixel de cana para pouca cana declarada.
8. **Hubs novos só em SP.** A palha pode ir a usinas de divisa.
9. **Raster de 2ª safra:** o valor 1 não foi identificado na legenda e ficou de fora; só a classe 41 entra.
10. O FL da palha é limitado pela escolha dos percentis (§2).
11. O FL é uma estimativa de acessibilidade logística, não uma medição.

## 11. Estado final e próximos passos

**Dados da CETESB e da RAIS (24/09).** O inventário e as decisões estão em `PROPOSTA_CHECKPOINT3_dados_CETESB.md`.

| Dado | Uso no método | Motivo |
|---|---|---|
| IQR, IGR, ICTEM e IQC | Fora do cálculo | Não forçar dados de RSU sem coordenada de aterro. O IQC entra só como evidência para o FCo do RSU = 1 |
| RAIS 1033-3/01 (fábricas de suco) | **Na v5.1** | Bagaço de citros nas fábricas (decisão 7) |
| Laticínios e sorvetes (coordenadas por CEP, pendentes de validação) | Só mapeados | Não há substrato de indústria láctea no `feedstocks.yaml` |
| Citros e café municipais; categorias de produtores RAIS | Sem uso no método | A mesma RAIS em centroide municipal. Servem de evidência descritiva e de backlog da plataforma |

`AreaUrbana` não é camada nova: é idêntica à que o pipeline já usa.

**Entregas geradas a partir da v5.1**
- **Artigo:** `Submissão ESD + Data in Brief/Pacote_CP2b_v5.1/`, com texto em inglês, 13 tabelas e 6 figuras. Gerado por `cp2b_indicadores_artigo.py`.
- **Plataforma:** `Metodo_CP2b/outputs_v5/plataforma/`, com uma tabela longa N1–N4 por município × substrato × cenário, os parâmetros, o FL municipal, a camada de unidades industriais e o rascunho de migração 032, que termina em ROLLBACK. Gerado por `cp2b_pacote_plataforma.py`.
- **Banco:** os arquivos de `outputs/banco/` foram regenerados pela v5.1 (`06_integracao.py`).

**Pendências (não bloqueiam o artigo; ficam declaradas nas limitações)**
- **Parâmetros provisórios:** 11 dos 17 substratos, com 57,6% do N3. A palha de cana (43,0%) é o principal.
- **Plataforma:** fazer um PR no `Pilar2b` com a migração 032, o carregador e a API/front para os níveis CP2b. Conferir os slugs `ORGANICO_RSU`/`PODA_URBANA` e a nomenclatura CH4 das colunas `*_biogas_m3_year`.
- **Coordenadas oficiais:** das ~20 fábricas de suco (CNPJ + licença CETESB) e dos aterros de destino do RSU.
- **Substratos futuros:** laticínios (soro e efluente), abatedouros (MapBiomas `structure_slaughterhouse`) e silvicultura.

## 12. Reprodutibilidade

```bash
cd "C:/Users/Lucas/Documents/Reposicionamento_Submissão_ESD/Metodo_CP2b"
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # uma vez (pandas 2.2.3)
bash fl_espacial/rodar_pipeline.sh              # 00 → 07, inclui a cascata v5.1 (~45 min com o grafo em cache; ~1h40 do zero)
.venv/Scripts/python.exe cp2b_indicadores_artigo.py    # pacote do artigo (outputs_v5/artigo/)
.venv/Scripts/python.exe cp2b_pacote_plataforma.py     # pacote da plataforma (outputs_v5/plataforma/)
```

Parâmetros só em `fl_espacial/config_fl.yaml`; semente 20260923; logs por etapa em `fl_espacial/logs/` (os da rodada v5.1 terminam em `_v51.txt`). O patch da v5 e o diff contra a v4 estão em `fl_espacial/patch_v5/` (ver `LEIA-ME.md`), com os backups da v5.0 (`*_v5.0.*.bak`).
