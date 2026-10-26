# CP2b v5.1: uncertainty and sensitivity text for the paper (draft)

Date: 26/10/2026 · Internal draft for the method team. Do not circulate before
review.

## Notes for the authors

- Written in English on the assumption that the target is Energy for
  Sustainable Development (folder "Reposicionamento_Submissão_ESD"). A
  Portuguese version is easy to produce if that is wrong.
- Every number below comes from an output committed in this repository and is
  traced in the last section. Volumes are million Nm³ CH₄ per year, CP2b v5.1
  snapshot, med scenario unless stated otherwise.
- `[TEAM: …]` marks a sentence that needs an answer from the method team before
  submission. `[REF: …]` marks a citation to check: keys in parentheses exist
  in PILAR-2b `references.yaml`; the others are Literature Watch records whose
  source must be opened before citing. No DOI here was added by hand.
- Section numbers (2.x, 3.x) are placeholders for wherever this goes in the
  manuscript.

---

## Text for Methods

### 2.x Definitions the cascade depends on

Insert these sentences where FS, FCo and FL are first defined.

- **Seasonal factor (FS).** FS is the fraction of the generated mass that is
  retained after documented losses between generation and collection (for
  example, field decomposition of straw). It is not the fraction of the year
  in which the residue is available: seasonality governs plant sizing and
  storage, not the annual potential. `[TEAM: confirm wording against DEC-013
  and align DECISOES_METODOLOGICAS.md, which still describes FS as "seasonal
  availability relative to annual generation".]`
- **Competing-use factor (FCo).** FCo is the fraction not committed to uses
  that exclude anaerobic digestion. Use as fertiliser is compatible with
  digestion (the digestate returns to the field), so it is not deducted; for
  poultry FCo = 0.95.
- **Sugarcane straw.** The FS of 0.92 (0.85–0.97) assumes straw is baled
  `[TEAM: time between harvest and baling]` after harvest. The FCo of 0.90
  (boiler fuel and second-generation ethanol) has no quantitative source for
  São Paulo and is reported as a limitation.
- **Feedlot cattle.** The base is the confined stock (GEDAVE), not the animals
  that pass through the feedlot in the year; days on feed are therefore not
  applied as FS.
- **Pasture cattle.** Manure deposited on pasture is not collectable (FC = 0),
  so pasture cattle contribute to N1 but not to N2–N4 by premise.
- **Logistic factor (FL).** FL is municipality- and substrate-specific and
  comes from the CP2b spatial model (fl_v5), co-digestion with allocation
  variant. N3 is placed on a 1-km grid or at the point where it is generated
  (mill, wastewater plant, farm), and each point takes the weight w(d) of
  the road distance d (OpenStreetMap network) to the nearest selected hub:
  w = 1 up to r1, falling linearly to 0 at r2. The radii depend on the
  substrate class and scenario (med: liquids 5/15 km, wet solids 15/30 km,
  dry solids 10/25 km). Sugarcane straw goes only to the mills, with radii from
  the road-distance percentiles (med 27.2/41.7 km). Candidate hubs are existing
  plants (mills, wastewater plants, operating biogas plants, juice factories)
  and a 4-km grid. They enter greedily, and a hub enters only if the residue
  it adds, net of what earlier hubs already cover, is at least Q_min (3,200,
  1,500 and 500 Nm³ CH₄ d⁻¹ in min, med and max). Municipal FL is the
  supply-weighted mean of its points. FL is therefore zero when no selected hub
  lies within r2 by road of the municipality's supply: both the radius and the
  minimum hub size set it. `[TEAM: confirm; read from the fl_v5 code in
  fl_espacial/ (04b_alocacao.py, config_fl.yaml).]` Re-running the allocation
  and integration steps from the cached network reproduces the published FL
  tables byte for byte. Where FL is zero, the
  residue exists and is not consumed by existing uses, but no plant is counted
  in the municipality.

### 2.y Uncertainty and sensitivity analysis

**Parameter uncertainty.** Each CP2b parameter has a minimum, median and
maximum value for each substrate (`cp2b_parametros.csv`, v5.1). We sampled
each of the 126 parameters from a triangular distribution with those three
values as minimum, mode and maximum. We also sampled five residual factors,
which are snapshot variation not described in the parameter file: the
collection factor of broilers and layers, and the N1 base of bagasse, filter
cake and vinasse.

For each draw the cascade N1 → N2 → N3a → N3 → N4 was recomputed for every
municipality (645) and substrate:

- the existing use U was capped at N3a;
- FL was interpolated linearly in each municipality's N3 between its snapshot
  values in the min, med and max scenarios.

With all parameters at their minimum, median or maximum, the model reproduces
the snapshot row by row (largest deviation 0.000 %). We ran 20,000 draws (seed
20261023) and report the 5th–95th percentile range. The first-order share of
each parameter in the variance of state N4 is (ΔN4/Δθ)² × Var(θ) / Var(N4),
where ΔN4/Δθ is the slope between the parameter's minimum and maximum with
all other parameters at their medians.

Ranking stability was measured over the same draws by:

- the Spearman correlation of the municipal N4 ranking against the med
  ranking;
- the probability that each municipality stays in the top 50.

**Correlated parameters.** Independent draws give the narrowest interval, and
moving all parameters together gives the full min–max range. Where the true
interval lies depends on which parameters share an error. We repeated the
draws with a Gaussian copula: each parameter keeps its triangular marginal,
and parameters in the same group share a correlation ρ.

Groups were derived from the sources cited for each parameter (the source
column of the parameter file and the references in the CP2b feedstock
library, used only where the library range equals the parameter range).
Under the main structure, the same element in different substrates moves
together when it cites a common reference. Values set by the CP2b team without
an external reference are sampled independently. We also report:

- the team's values of the same element together;
- any parameters sharing a reference, across elements;
- the same element in all substrates;
- all parameters of a substrate;
- the four sugarcane residues together;
- all parameters together.

Each structure was run with 20,000 draws. None estimates the true ρ; each
interval holds if that correlation holds.

**Literature scenarios.** An automated literature search (Literature Watch,
October 2026) collected:

- 48 records of manure generation, 18 comparable with CP2b units;
- 40 records of biochemical methane potential (BMP);
- 41 records of collection, competing-use, seasonal and logistic factors, 14
  of them under the CP2b definitions.

`[REF: describe the search protocol in one sentence, or cite the
repository.]`

Each comparable record replaced the CP2b median at the stage where the
parameter enters. The cascade was then recomputed by municipality, with U and
FS × FL kept at their snapshot values. "Definition" scenarios read FS or FCo
under a definition different from CP2b's. They are not proposals: they size
the error of applying another definition.

**Logistic-factor variants.** The FL file holds five municipal variants:

- co-digestion with allocation (the one used);
- co-digestion by coverage;
- mono-digestion by coverage;
- mono-digestion with allocation;
- co-digestion with allocation and straw admitted at any hub.

We identified the variant used from the data (the one that yields a single FS
per substrate and scenario), recomputed N4 with each variant, and tested
whether FL = 0 follows a supply threshold, by row and by municipality.

---

## Text for Results

### 3.x Uncertainty of the state potential

State N4 is 5,971.7 million Nm³ CH₄ yr⁻¹ (N1 23,642.6; N2 15,207.6; N3
7,001.9). Sugarcane residues account for 81.8 %:

| Residue | Share of N4 |
|---|---:|
| straw | 40.7 % |
| filter cake | 14.2 % |
| vinasse | 13.6 % |
| bagasse | 13.3 % |

With independent parameters, the 90 % interval of N4 is 5,130–6,895
(−14.1 % to +15.5 % of the median). The full CP2b range, with all parameters
at their minimum or maximum, is 1,883–15,577.

Correlating parameters that cite a common source widens the interval to
4,892–7,173 (−18.1 % to +20.1 %). Correlating the same element across all
substrates, which is the conservative reading, widens it to 4,411–7,738
(−26.1 % to +29.6 %). The intermediate readings fall between these two:

| Structure | 90 % interval | Relative to median |
|---|---|---|
| team values together | 4,738–7,356 | −20.7 % to +23.2 % |
| shared references across elements | 4,537–7,761 | −24.0 % to +30.0 % |

Moving the four sugarcane residues together (−42.2 % to +70.4 %) has no
support in the cited sources. Of the straw parameters, only the BMP shares a
reference with the other cane residues; the straw FC comes from different
sources, and its g, FCo and FS are team values. The interval is skewed
upwards because the CP2b ranges have longer upper tails (straw BMP 140–175–250
NmL g⁻¹ VS).

Sugarcane straw drives the uncertainty, with 71 % of the first-order variance:

| Straw parameter | Share of variance |
|---|---:|
| BMP | 39.3 % |
| FC | 14.0 % |
| VS | 6.0 % |
| g | 4.9 % |
| FCo, FL and FS together | 6.8 % |

The bagasse FCo, 0.10 (0.05–0.15), is the third parameter (8.4 %): between its
minimum and maximum, state N4 goes from 5,585 to 6,345. `[TEAM: source of the
bagasse FCo range.]`

The median of the draws for corn and soybean straw lies 29 % and 19 % below
the CP2b med. Their ranges place the med near the maximum (corn FL
0.35–0.67–0.75, soybean FL 0.30–0.55–0.70), so the CP2b med is a high reading
within its own ranges for these two residues.

### 3.y Stability of the municipal ranking

The ranking is robust to parameter uncertainty:

- With independent parameters, the Spearman correlation against the med
  ranking has a median of 0.995 (5th percentile 0.989).
- 44 of the 50 largest municipalities stay in the top 50 in at least 90 % of
  the draws. The exception is the city of São Paulo (rank 4–48, driven by
  municipal solid waste and sewage sludge).
- Under the source-based and conservative correlation structures, the 5th
  percentile of Spearman stays at or above 0.985, and 44–46 of the top 50
  remain.
- The ranking moves most when all parameters of each substrate move together
  but substrates are independent: 35 of the top 50 remain, and the 5th
  percentile of Spearman is 0.965. Municipalities with a different substrate
  mix then trade places.

Relative uncertainty is largest where N4 is small. The median municipal
(p95 − p5)/med is:

- 47–60 % in the nine inland intermediate regions;
- 125 % in the São Paulo region;
- 435 % in the São José dos Campos region, where dairy manure, solid waste and
  sludge dominate.

### 3.z Sensitivity to the literature

| Question | Scenario type | ΔN4 (literature range) |
|---|---|---|
| Sugarcane straw FS as mass remaining after field decomposition | literature | −11.1 % (−27.0 to −11.1) |
| Vinasse and filter cake FS read as fraction of the year in harvest | definition | −6.7 % |
| Bagasse BMP, measured (raw) | literature | +6.2 % (−3.2 to +13.1) |
| Poultry FCo read as "fraction not used as fertiliser" | definition | −4.8 % |
| Soybean straw BMP | literature | −1.4 % |
| Dairy manure g as total excretion | literature | +1.0 % (+0.6 to +1.5) |
| Orange bagasse FCo as residue left after pelletising | literature | −0.6 % |
| Feedlot faecal dry matter, measured | literature | −0.4 % |
| All literature together (dairy g as total excretion) | combined | −6.0 % (−31.8 to +1.5) |

All scenarios stay within the CP2b min–max range.

The straw FS scenario is the largest effect. Field decomposition leaves 0.67
of the mass after 36 days and 0.31 after one year, against the CP2b FS of
0.92 `[REF: Embrapa record, tier B, in evidencia_fde]`. The figure therefore
depends on the time between harvest and baling.

With all literature values together:

- 45 of the top 50 municipalities remain;
- the Spearman correlation against the med ranking is 0.984.

Manure questions move state N4 by 1 % or less:

- Dairy g changes N1 by a factor of 3.5 but N4 by only +1.0 %, because the
  dairy logistic factor is low.
- Pasture g changes only N1, since FC = 0.

### 3.w Municipalities without potential

In the med scenario, 26 municipalities have N4 = 0:

- 16 in the Ribeira Valley and southern coast (Sorocaba intermediate region);
- 8 in the historic Paraíba Valley and the Mantiqueira (São José dos Campos
  region);
- 2 in the São Paulo region.

In all of them the zero comes from the logistic factor. The residue exists and
is not consumed by existing uses: N3 is 0.04–0.60 per municipality, 5.9 in
total, mostly dairy manure and solid waste. All of them recover N4 in the max
scenario (0.09–2.93 each).

The zero holds across all five FL variants: no variant returns more than 0.11
(Silveiras, coverage variant). FL = 0 does not follow a municipal supply
threshold in any substrate, by row or by municipality. In the med scenario,
straw rows with FL = 0 reach 3,567 m³ CH₄ d⁻¹, while rows with FL > 0 start
at 12 m³ CH₄ d⁻¹.

The number of zero municipalities depends on the scenario: 146 in min, 27 in
med and 0 in max.¹ This follows from the FL rule (section 2.x): a hub needs
Q_min of residue from the supply around it, and Q_min falls from 3,200 to
500 Nm³ CH₄ d⁻¹ between min and max while the radii grow, so what counts is
the supply around the municipality, not its own. Measured by road, the
nearest selected hub is 27–141 km from these 26 municipalities (median
52 km; 137–141 km for Cananéia and Ilha Comprida). None of them has a supply point
within r2 of a selected hub; the smallest margin beyond r2 is 4.2 km
(Silveiras and São Bento do Sapucaí). In 25 of the 26, the municipality's own
supply is below Q_min (1,500 Nm³ CH₄ d⁻¹ in med), so it could not support a
hub alone. The exception is Bananal (1,648 Nm³ CH₄ d⁻¹). Without sugarcane
straw, which goes only to the mills, 1,571 remain for co-digestion, 85 % of it
dairy manure spread over 87 supply points, with the 5/15 km radii of liquids.
None of the 57 candidate hubs that reach this supply is viable: the best one
gathers 618 Nm³ CH₄ d⁻¹ weighted by w(d), almost all from Bananal itself,
against a Q_min of 1,500. The choice of variant moves state
N4 by −3.8 % (mono-digestion with allocation) to +4.5 % (straw at any hub) in
med, and by −12.1 % to +6.3 % in min. In med this is less than the parameter
uncertainty.

¹ The FL variant count treats N4 below 1 Nm³ yr⁻¹ as zero and adds Tapiraí.

---

## Limitations (paragraph)

- The 90 % intervals hold under the stated correlation structures; the data do
  not identify the true correlation.
- The model takes FL as a function of each municipality's own N3. It ignores
  the supply of neighbouring municipalities, which the FL results suggest
  matters.
- Municipal FL depends on which hubs the greedy selection picks, and so on
  supply far from the municipality. Re-running the allocation with the bagasse
  BMP proposed for v5.2 moves state FL by at most 0.005, but municipal FL by
  more than 0.01 in 835 municipality × substrate rows, by up to ±0.95 for
  dairy and pig manure in max. Municipal rankings of dispersed livestock
  should be read with that in mind.
- The sugarcane straw FCo, the largest parameter without a quantitative source
  for São Paulo, is a team estimate.
- Municipal solid waste, sewage sludge and urban pruning have no comparable
  literature record, so their N4 was not tested against the literature.
- The literature records are tier A to C. The two largest literature effects
  (straw FS, bagasse BMP) rest on tier B and C records.

---

## Open items for the method team

| # | Question | Where it goes | Weight on N4 |
|---|---|---|---|
| 1 | Time between harvest and baling assumed by the straw FS of 0.92 | 2.x, 3.z | −11.1 % if FS = 0.67 |
| 2 | Source of the straw FCo of 0.90, or state it as a gap | 2.x, Limitations | 3.0 % of variance |
| 3 | Source of the bagasse FCo range 0.05–0.15 | 3.x | 8.4 % of variance |
| 4 | fl_v5 rule that sets FL = 0: drafted from the code (radius and Q_min), distances measured, Bananal explained (dispersed supply, best candidate 618 < Q_min); confirm | 2.x, 3.w | 26 municipalities |
| 5 | FS definition: align DECISOES_METODOLOGICAS.md with DEC-013 | 2.x | −6.7 % under the other reading |
| 6 | Dairy g: total excretion or collectable fraction? | 3.z | +1.0 % / +0.4 % |
| 7 | Feedlot g × ST representative of SP, or anchor on faecal dry matter? | 3.z | −0.4 % |
| 8 | Broiler batches per year implied by the litter mass | Methods (feedstock table) | — |
| 9 | Source of the orange-bagasse FCo of 0.25 | 3.z | −0.6 % |
| 10 | Citation for the straw FC: "Atlas SP 2020 p.65" is not in `references.yaml` | References | — |

---

## Where each number comes from

| Number | File (this repository) | Output commit |
|---|---|---|
| Cascade N1–N4, shares of N4 | `outputs/sensibilidade_cp2b/RELATORIO.md` §1 | 75ea805 |
| Literature scenarios, ranges, notes | `outputs/sensibilidade_cp2b/RELATORIO.md` §3 | 75ea805 |
| Literature record counts | `outputs/evidencia_geracao`, `evidencia_bmp`, `evidencia_fde` | 75ea805 |
| Independent 90 % interval, variance shares, ranking, regions | `outputs/incerteza_cp2b/RELATORIO.md` §1–3, `incerteza.csv`, `ranking.csv` | 4fc6651 |
| Municipal (p95 − p5)/med by region | computed from `outputs/incerteza_cp2b/ranking.csv` (municipalities with N4 med > 0) | 4fc6651 |
| Correlated intervals, source groups | `outputs/incerteza_correlacao/RELATORIO.md`, `fontes.csv` | 610f947 |
| N4-zero municipalities | `outputs/diagnostico_n4_zero/RELATORIO.md` | 1cd3c07 |
| FL variants, threshold test | `outputs/fl_variantes/RELATORIO.md` | 7ab5ca8 |
| Distance to the nearest hub, Q_min, C02 effect on FL | `outputs/fl_espacial/RELATORIO.md` §3–4 (from `data/fl_v51/`) | f6a1815 |
| Bananal: supply, candidates, best basin | `fl_espacial/analises_v52/v52_bananal.py`, run on the v5.1 cache; output outside the repo | — (notebook run, 26/10/2026) |

The correlation run (base seed 20261024) gives an independent interval of
5,130–6,887. It matches the uncertainty run within 0.12 %; the text uses the
latter.
