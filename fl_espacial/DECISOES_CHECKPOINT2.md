# FL espacial — decisões do CHECKPOINT 2 (para colar no Claude Code)

> 24/09/2026 · Resposta ao CHECKPOINT 2 de `fl_espacial/RELATORIO_FL_espacial.md`

Decisões:

1. **Variante principal da v5 = B, co-digestão com alocação.**
   - A (co-digestão por cobertura) entra como limite superior; D (monodigestão com alocação) como limite inferior. As quatro ficam em `outputs_v5`.
   - Registre no relatório que a definição original ("FL é cobertura") não discrimina quando os candidatos estão em toda parte e a oferta é densa. É por isso que a alocação vira a principal.
   - Checagem de robustez: depois da seleção gulosa, recalcule o FL como max w(d) só sobre o conjunto de hubs selecionados (sem refazer a viabilidade). Se o FL estadual por substrato mudar mais de 0,02, reporte as duas versões.

2. **Palha só vai para as usinas, com raio calibrado pela distância observada entre a cana e a moagem.**
   - Justificativa: a palha vem dos mesmos talhões que abastecem as usinas, e o uso realista (digestão ou queima) é na usina, junto de vinhaça e torta.
   - Calcular na rede viária a distribuição da distância das células com cana (peso = oferta de PALHA) até a usina mais próxima, incluindo as de divisa (MG/PR/MS).
   - Usar os percentis ponderados como raios:
     - min: r1/r2 = P50/P90;
     - med: P75/P95;
     - max: P90/P99.
   - Estimativa prévia (euclidiana × 1,30): P50 ≈ 17 km, P75 ≈ 24, P90 ≈ 31, P95 ≈ 37, P99 ≈ 50. Isso daria FL da palha ≈ 0,74 / 0,88 / 0,95; na rede deve sair um pouco menor.
   - Com isso, a palha deixa de contar para a viabilidade dos hubs da grade. Palhadas de milho e soja continuam com hubs gerais e os raios de sólidos secos.
   - Reportar lado a lado com a variante "palha em qualquer hub".

3. **Q_min confirmado:** 3.200 / 1.500 / 500 Nm³ CH4/dia (≈ 500 / 240 / 80 kWe). Referência de biometano (≥ 10.000) só informativa.

4. **Aplicar o patch da cascata (v5)**, com backup `*_v4.py.bak`, usando a variante B + a palha nas usinas.
   - Fixar as dependências em `Metodo_CP2b/requirements.txt` (pandas 2.2.x e as versões do `ambiente.txt`), porque a cascata quebra com pandas 3.
   - Rodar a v5 e gerar a reconciliação N4 v4 × v5 (estado, fluxo, top 20 municípios), com e sem lignocelulósicos.

5. **Banco de produção: não aplicar nada agora.**
   - Manter o SQL como rascunho, terminando em ROLLBACK.
   - A migração será única, depois de fechar o método (FS, parâmetros provisórios restantes e a nomenclatura CH4 das colunas `*_biogas_m3_year`).
   - Conferir os slugs (ORGANICO_RSU, PODA_URBANA) nesse momento.

6. **Resultados de planejamento para o relatório:**
   - curva MCLP (hubs × fração coberta: 50/80/95%) da variante B com a palha nas usinas;
   - taxa de acerto da monodigestão (é o teste que discrimina).
