"""Método CP2b v5 — elementos de cálculo (formato BASISDATEN, DBFZ).

Cascata (tudo em Nm³ CH4):
  N1 teórico     P1 = A × g × ST × SV × BMP   (ou coeficiente direto de CH4 por unidade de A)
  N2 técnico     P2 = P1 × FC                 (restrições técnicas e ecológicas)
  N3 mobilizável P3 = max(0, P2 × FCo − U)    (FCo = 1 − u; u = só usos EXCLUDENTES; U = plantas existentes)
  N4 acessível   P4 = P3 × FS × FL            (FS = perda de armazenamento; FL = logística)

Cenários min/med/max acoplados. Status:
  'yaml' = feedstocks.yaml sem alteração; 'cp2b' = definido na consolidação, com fonte;
  'provisorio' = a confirmar.
Referências de validação consolidadas em Evidencias_CP2B_FC_FCo_FL.md.

v4 (23/09/2026): PAM/PPM 2024; UNICA 2020/21 (cana moída e etanol) alocados às usinas (EPE/MapBiomas);
bovinos por sistema com GEDAVE (confinado) e PPM Tab. 94 (vacas ordenhadas); aves corte × postura;
RSU = massa coletada SNIS 2022; lodo primário com fração de ETEs compatíveis com digestão.

v5: FL="espacial" — FL por município × substrato × cenário calculado em fl_espacial/ (fração do N3 a distância por
estrada de um hub viável; ver fl_espacial/RELATORIO_FL_espacial.md). FL_ref = chave do feedstocks.yaml mantida só
como referência (BASISDATEN, comparação com a v4). Saída em outputs_v5/; a v4 continua em outputs/.

v5.1 (24/09/2026): bagaço de citros nas fábricas de suco concentrado — laranja da PAM (total SP) alocada às fábricas
∝ vínculos RAIS (fl_espacial/00_fabricas_suco.py), como a cana moída nas usinas. Backup: cp2b_params_v5.py.bak.
"""


def T(a, b, c):
    return {"min": a, "med": b, "max": c}


ANO_PAM_PPM = 2024

GLOBAIS = {
    # UNICA/MAPA (hpm), SP. med = safra 2020/21 (última disponível); min/max = faixa 2017/18–2020/21
    "cana_moida_SP_t": {"min": 333_338_169, "med": 356_508_000, "max": 357_142_342,
                        "fonte": "UNICA/MAPA hpm, SP, safra 2020/21 (356.508 mil t); faixa 2017/18–2020/21",
                        "status": "cp2b"},
    "etanol_SP_m3": {"min": 13_222_807, "med": 14_426_000, "max": 16_544_705,
                     "fonte": "UNICA/MAPA hpm, SP, safra 2020/21 (14.426 mil m³); faixa 2017/18–2020/21",
                     "status": "cp2b"},
    "alocacao_usinas": {"min": None, "med": "EPE Webmap 2018 via MapBiomas 10.1 (structure_ethanol_plant)", "max": None,
                        "fonte": "cana moída ∝ ponto médio da classe de capacidade; etanol ∝ capacidade anidro+hidratado (m³/d)",
                        "status": "cp2b"},
    "alocacao_fabricas_suco": {"min": None, "med": "RAIS (staging local), CNAE 1033-3/01, estabelecimentos com ≥ 100 vínculos",
                               "max": None,
                               "fonte": "laranja PAM 2024 (total SP) ∝ vínculos por município; saem municípios sem laranja na PAM "
                                        "(escritórios e terminais portuários); fl_espacial/outputs/fabricas_suco_alocacao.csv",
                               "status": "cp2b"},
    "vacas_ordenhadas": {"min": None, "med": f"IBGE PPM Tab. 94, {ANO_PAM_PPM}", "max": None,
                         "fonte": "TABELA_94_VACAS_ORDENHADAS_PPM_2008_A2024.xlsx", "status": "cp2b"},
    "bovinos_confinados": {"min": None, "med": "GEDAVE/CDA-SP, cadastro de 03/11/2025 (estoque, SISTEMA_PRODUCAO = Confinado)",
                           "max": None, "fonte": "agregado por município em inputs/gedave_bovinos_agregado_municipio_sistema.csv "
                                                 "(sem dados pessoais); estoque na data — confinamento gira 2–3 ciclos/ano",
                           "status": "cp2b"},
    "rsu_kg_hab_dia_faixas": [(25_000, 0.7), (100_000, 0.8), (500_000, 0.9), (float("inf"), 1.1)],
    "ch4_frac_biogas": {"aterro": 0.50, "agro": 0.55, "esgoto": 0.60, "pecuaria": 0.60},
    "fator_capacidade_ute": 0.70,
    "eta_eletrica": 0.35,
    "pci_ch4_kwh_m3": 9.97,
    # Convenção de base volumétrica: base primária = Nm³ CH4
    "biometano_pureza_CH4": {"min": 0.90, "med": 0.96, "max": 0.98,
                             "fonte": "Especificação ANP Res. 1.006/2026 — confirmar teor mínimo; 0,96 típico PSA/membrana",
                             "status": "provisorio"},
    "perda_metano_upgrading": {"min": 0.005, "med": 0.01, "max": 0.02,
                               "fonte": "methane slip típico (IEA Bioenergy Task 37)", "status": "provisorio"},
    "vinhaca_ch4_no_biogas": {"min": 0.50, "med": 0.575, "max": 0.65, "fonte": "Atlas SP 2020 p.67", "status": "cp2b"},
    "eta_eletrica_motor": {"min": 0.35, "med": 0.38, "max": 0.42, "fonte": "motor a biogás", "status": "cp2b"},
}

# v5 — FL espacial. Município sem oferta N3 do substrato (N3 = 0) recebe o FL estadual, só para completar.
# Variantes (CHECKPOINT 2, 24/09/2026): "codig_alocado" = B, principal (co-digestão com alocação);
# "codigestao" = A (limite superior); "mono_alocado" = D (limite inferior); "mono" = C. Palha só nas usinas em todas.
FL_ESPACIAL = {"arquivo": "fl_espacial/outputs/fl_v5_municipio_substrato.csv",
               "arquivo_estado": "fl_espacial/outputs/fl_v5_estado_substrato.csv",
               "variante": "codig_alocado",
               "fabricas_suco": "fl_espacial/outputs/fabricas_suco_alocacao.csv"}   # v5.1
PASTA_SAIDA = "outputs_v5"

KG_DIA = 365 / 1000  # kg/dia -> t/ano

SUBSTRATOS = [
    # ---------------- CANA (resíduos de usina alocados às usinas) ----------------
    dict(codigo="BAGACO", fluxo="sugarcane", setor="agricultural", atividade="cana_moida_t", lignocel=True,
         g=T(0.25, 0.28, 0.30), g_unid="t úmida / t cana moída", yaml="BAGACO",
         FC=T(0.90, 0.95, 0.98), FCo=T(0.05, 0.10, 0.15), FS=T(0.95, 0.97, 0.99), FL="espacial",
         u="Cogeração (excludente). Sempre há excedente: 5–15% (decisão da equipe; o yaml cita 15–38% em usinas modernas, Paulose 2021).",
         fonte_FC="feedstocks.yaml", fonte_FCo="decisão CP2b 23/09; SIGA/ANEEL 215 UTEs a bagaço (6,27 GW)", status="cp2b"),
    dict(codigo="TORTA_FILTRO", fluxo="sugarcane", setor="agricultural", atividade="cana_moida_t", lignocel=False,
         g=T(0.030, 0.035, 0.040), g_unid="t úmida / t cana moída", yaml="TORTA_FILTRO",
         FC=T(0.85, 0.90, 0.95), FCo=T(0.90, 1.00, 1.00), FS=T(0.85, 0.90, 0.95), FL="espacial",
         u="Adubo é compatível com digestão (DBFZ).", fonte_g="Atlas SP 2020 p.66; real_rpr", status="cp2b"),
    dict(codigo="VINHACA", fluxo="sugarcane", setor="agricultural", atividade="etanol_m3", lignocel=False,
         direto=T(57.0, 65.55, 74.1), g_unid="Nm³ CH4 / m³ etanol", yaml=None,
         FC=T(0.90, 0.95, 0.98), FCo=T(0.90, 1.00, 1.00), FS=T(0.85, 0.92, 0.98), FL="espacial", FL_ref="VINHACA",
         u="Fertirrigação é compatível.", fonte_g="Atlas SP 2020 p.67 (114 m³ biogás/m³ etanol × 50–65% CH4)", status="cp2b"),
    dict(codigo="PALHA", fluxo="sugarcane", setor="agricultural", atividade="cana_t", lignocel=True,
         g=T(0.12, 0.14, 0.15), g_unid="t MS / t cana colhida (PAM)", yaml="PALHA", ts_override=T(1.0, 1.0, 1.0),
         FC=T(0.35, 0.40, 0.50), FCo=T(0.80, 0.90, 0.95), FS=T(0.85, 0.92, 0.97), FL="espacial",
         u="Queima em caldeira/2G (excludente) — FCo sem fonte quantitativa para SP (lacuna). "
           "BMP sem pré-tratamento: parâmetro inicial; digestão de lignocelulósicos em pesquisa no CP2b.",
         fonte_FC="Atlas SP 2020 p.65 (40/50%); Tenelli et al. 2021 (35%)", status="provisorio"),
    # ---------------- GRÃOS / CULTURAS ----------------
    dict(codigo="PALHA_MILHO", fluxo="corn", setor="agricultural", atividade="milho_t", lignocel=True,
         g=T(1.0, 1.1, 1.2), g_unid="t / t grão", yaml="PALHA_MILHO",
         FC=T(0.25, 0.40, 0.50), FCo=T(0.85, 0.95, 1.00), FS=T(0.85, 0.90, 0.95), FL="espacial",
         u="Ração/cama (menor). Cobertura de solo no FC.", status="provisorio"),
    dict(codigo="PALHA_SOJA", fluxo="soybean", setor="agricultural", atividade="soja_t", lignocel=True,
         g=T(1.35, 1.40, 1.50), g_unid="t / t grão", yaml="PALHA_SOJA",
         FC=T(0.20, 0.30, 0.40), FCo=T(0.90, 1.00, 1.00), FS=T(0.85, 0.90, 0.95), FL="espacial",
         u="Sem uso excludente relevante.", status="provisorio"),
    dict(codigo="CASCA_CAFE", fluxo="coffee", setor="agricultural", atividade="cafe_t", lignocel=False,
         g=T(1.0, 1.0, 1.18), g_unid="t / t café beneficiado", yaml="CASCA_CAFE",
         FC=T(0.80, 0.90, 0.95), FCo=T(0.50, 0.60, 0.70), FS=T(0.90, 0.95, 0.98), FL="espacial",
         u="Combustível em secadores (excludente).", status="provisorio"),
    dict(codigo="BAGACO_CITROS", fluxo="citrus", setor="agricultural", atividade="laranja_fabrica_t", lignocel=False,
         g=T(0.48, 0.50, 0.52), g_unid="t úmida / t fruta", yaml="BAGACO_CITROS",
         FC=T(0.65, 0.75, 0.85), FCo=T(0.15, 0.25, 0.40), FS=T(0.80, 0.88, 0.95), FL="espacial",
         u="Polpa peletizada para ração, pectina, d-limoneno (excludentes). A = laranja PAM (total SP) alocada às "
           "fábricas de suco (v5.1).", status="provisorio"),
    # ---------------- BOVINOS (três sistemas) ----------------
    dict(codigo="BOV_LEITE", fluxo="cattle", setor="livestock", atividade="bov_leite_cab", lignocel=False,
         g=T(10 * KG_DIA, 14 * KG_DIA, 18 * KG_DIA), g_unid="t / vaca / ano (10–18 kg/dia)", yaml="ESTERCO_BOVINO",
         FC=T(0.40, 0.50, 0.75), FCo=T(0.90, 1.00, 1.00), FS=T(0.95, 0.98, 1.00), FL="espacial", FL_ref="DEJETOS_BOVINO",
         u="Adubo compatível. A = vacas ordenhadas (PPM 94). FC: IEA Task 37 (~40% coletável, Liebetrau 2021); yaml 0,75.",
         fonte_g="Embrapa Pecuária Sudeste via feedstocks.yaml (leite 10–18 kg/cab/dia)", status="provisorio"),
    dict(codigo="BOV_CONFINADO", fluxo="cattle", setor="livestock", atividade="bov_conf_cab", lignocel=False,
         g=T(13.3 * KG_DIA, 20 * KG_DIA, 25 * KG_DIA), g_unid="t / cab / ano (13,3–25 kg/dia)", yaml="ESTERCO_BOVINO",
         quim_override=dict(ST=T(0.18, 0.205, 0.23), SV=T(0.78, 0.81, 0.84), BMP=T(210, 260, 307)),
         FC=T(0.40, 0.65, 0.75), FCo=T(0.90, 1.00, 1.00), FS=T(0.90, 0.95, 1.00), FL="espacial", FL_ref="ESTERCO_BOVINO",
         u="Adubo compatível. A = estoque confinado GEDAVE. Nota: a consistência das fezes em confinamento varia com a dieta "
           "(teor de fibra fisicamente efetiva; Contadini 2020) — afeta ST e, portanto, a faixa de ST adotada.",
         fonte_g="Montoro 2017 (13,33 kg/dia, ST 20,49%, SV 81%, Presidente Prudente); Cenario_Bovinocultura2 (20 kg/dia)",
         fonte_FC="IEA Task 37 (40%); Cenario_Bovinocultura/2 (0,60–0,75; Herrero 2018, Mendes 2023)",
         nota_quim="BMP 210–307 (Embrapa 0,21–0,23; Velásquez 2018 0,28; Montoro 2019 0,307)", status="provisorio"),
    dict(codigo="BOV_PASTO_MISTO", fluxo="cattle", setor="livestock", atividade="bov_pasto_cab", lignocel=False,
         g="ESTERCO_BOVINO", g_unid="t / cab / ano", yaml="ESTERCO_BOVINO",
         FC=T(0.0, 0.0, 0.10), FCo=T(0.90, 1.00, 1.00), FS=T(0.95, 0.98, 1.00), FL="ESTERCO_BOVINO",
         u="Pasto e sistema misto: esterco de pastejo não recolhível (DBFZ/IEA). Máx. 10% para curral em sistema misto "
           "(Guerini Filho 2019: 20% em extensivo).", status="cp2b"),
    # ---------------- SUÍNOS / AVES ----------------
    dict(codigo="SUINOS", fluxo="swine", setor="livestock", atividade="suinos_cab", lignocel=False,
         g="DEJETOS_SUINO", g_unid="t / cab / ano", yaml="DEJETOS_SUINO", ts_override=T(0.08, 0.10, 0.12),
         FC=T(0.70, 0.85, 0.95), FCo=T(0.90, 1.00, 1.00), FS=T(0.90, 0.95, 1.00), FL="espacial", FL_ref="DEJETOS_SUINO",
         u="Adubo compatível. FC reduzido: mediana paulista 33 cab/granja; 0,90–0,95 só para coleta ≤ 7 d (Kunz 2009).",
         nota_quim="ST 8–12% (excreta fresca; yaml 3% é chorume diluído)", status="provisorio"),
    dict(codigo="AVES_CORTE", fluxo="poultry", setor="livestock", atividade="aves_corte_cab", lignocel=False,
         g="CAMA_AVIARIO", g_unid="t cama / ave alojada / ano", yaml="CAMA_AVIARIO",
         FC="municipal:aves_fc", FCo=T(0.85, 0.95, 1.00), FS=T(0.90, 0.95, 0.98), FL="espacial",
         u="Adubo compatível. A = galináceos − galinhas (PPM).", fonte_FC="GEDAVE: fração comercial da capacidade × 0,90",
         status="cp2b"),
    dict(codigo="AVES_POSTURA", fluxo="poultry", setor="livestock", atividade="aves_postura_cab", lignocel=False,
         g=T(0.040, 0.050, 0.055), g_unid="t dejeto fresco / galinha / ano (~0,15 kg/dia)", yaml="DEJETOS_AVES",
         ts_override=T(0.20, 0.25, 0.30),
         FC="municipal:aves_fc", FCo=T(0.85, 0.95, 1.00), FS=T(0.90, 0.95, 0.98), FL="espacial", FL_ref="DEJETOS_AVES",
         u="Adubo compatível. A = galinhas (PPM).", fonte_g="Planilha Resíduo_Disponível (0,15 kg/ave/dia postura)",
         nota_quim="ST 20–30% (dejeto fresco)", status="provisorio"),
    # ---------------- URBANO ----------------
    dict(codigo="RSU_ORGANICO", fluxo="rsu", setor="urban", atividade="rsu_coletado_t", lignocel=False,
         g=T(0.46, 0.50, 0.55), g_unid="fração orgânica do RSU coletado", yaml="ORGANICO_RSU",
         FC=T(0.50, 0.65, 0.80), FCo=T(1.0, 1.0, 1.0), FS=T(0.98, 1.00, 1.00), FL="espacial",
         u="A = massa coletada SNIS 2022 (RDO+RPU). FC = separabilidade do orgânico em resíduo misturado (triagem mecânica; "
           "sem fonte primária — provisório). Aterro com captura = uso existente (subtraído no N3).",
         fonte_g="Atlas SP 2020 Eq. V.5 (0,4646); feedstocks.yaml (0,50–0,55)", status="provisorio"),
    dict(codigo="PODA_URBANA", fluxo="rpo", setor="urban", atividade="pop", lignocel=False,
         g="PODA_URBANA", g_unid="t / hab / ano", yaml="PODA_URBANA",
         FC=T(0.30, 0.50, 0.70), FCo=T(0.80, 0.90, 1.00), FS=T(0.95, 0.98, 1.00), FL="espacial",
         u="Compostagem compatível; caldeira excludente. FCo sem fonte primária.", status="provisorio"),
    dict(codigo="LODO_ETE", fluxo="sewage", setor="urban", atividade="pop", lignocel=False,
         g="LODO_PRIMARIO", g_unid="t úmida / hab / ano (ST 15%)", yaml="LODO_PRIMARIO", ts_override=T(0.15, 0.15, 0.15),
         FC="municipal:esgoto_fc", FCo=T(1.0, 1.0, 1.0), FS=T(0.98, 1.00, 1.00), FL="espacial",
         u="FC = atendimento (IN056) × tratamento (IN016) × fração de ETEs compatíveis com digestão (não-lagoa; ANA/Atlas "
           "Esgotos 2019). Metagás subtraída no N3.", status="cp2b"),
]

AVES_COLETA = T(0.85, 0.90, 0.95)

EXCLUIDOS = {
    "forestry": "Lenhosos: não fermentáveis sem pré-tratamento (filtro de fermentabilidade DBFZ Report 41).",
    "aquaculture": "Potencial desprezível.",
    "industriais": "Frigoríficos, laticínios, cervejarias, CRI Geo (Elias Fausto): limitação declarada; fora dos fluxos.",
}
