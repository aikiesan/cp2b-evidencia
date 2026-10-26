# cp2b-evidencia

Bibliotecas de evidência e análise de sensibilidade do CP2b (NIPE-UNICAMP).
Compara os registros da rotina Literature Watch com os parâmetros do CP2b v5.1
e refaz a cascata N1 → N4 com os valores da literatura.

Este repositório existe para não poluir o histórico do PILAR-2b. Ele só lê o
PILAR-2b (o loader do CP2b e o `feedstocks.yaml`); nada aqui escreve lá.

## Estrutura

- `data/literature_watch/`: registros CSV da rotina (BMP, geração de dejetos,
  fatores FC/FCo/FS/FL).
- `scripts/`: um script por biblioteca, mais `pilar2b.py`, que acha o checkout
  do PILAR-2b e confere a versão do método (CP2b v5.1).
- `outputs/`: relatórios gerados com o snapshot real. Entram no git
  normalmente.
- `outputs/incerteza_cp2b/`: intervalo do N4 com os parâmetros sorteados nas faixas do
  CP2b, tornado e estabilidade do ranking municipal (`CP2B_MC_N` sorteios, padrão
  20000, semente fixa).
- `outputs/mapas_incerteza/`: mapas municipais do N4 med, da chance de ficar no top 50, da
  largura do intervalo e da mudança em cada cenário de literatura. Redesenham o
  `ranking.csv` da incerteza na malha municipal do IBGE, baixada uma vez para `.cache/`
  (fora do git), ou lida de `CP2B_MALHA`.
- `outputs/incerteza_correlacao/`: o mesmo intervalo com grupos de parâmetros andando juntos, inclusive pelos grupos que as fontes citadas sustentam (`fontes.csv`: a referência de cada parâmetro, lida da coluna `fonte` e das refs do `feedstocks.yaml`)
  (por substrato, por elemento, a cana inteira, tudo), cópula gaussiana com ρ 0,5 e 1.
- `outputs/diagnostico_n4_zero/`: onde a cascata zera os municípios de N4 med zero.
- `outputs/fl_variantes/`: o N4 com cada variante do FL espacial do snapshot, os municípios de N4 zero em cada uma e se o FL zero segue um limiar de oferta.
- `outputs/v52/`: o que cada mudança proposta para a v5.2 (`v52/mudancas.csv`) faz no N4, no ranking e no intervalo de 90 %.
- `v52/`: a v5.2 em construção; como propor uma mudança está em `v52/README.md`.
- `fl_espacial/`: o código e as notas do FL espacial v5.1 (fl_v5) e a cascata v5.1 que gerou o snapshot; só código, sem dados de entrada, cache nem saídas (veja `fl_espacial/LEIA-ME.md`).
- `docs/NOTA_METODO_CP2B.md`: nota ao time do método.
- `docs/METODO_ARTIGO.md`: texto de método e resultados para o artigo (inglês), com os números finais e de onde cada um vem.
- `tests/`: testes com dados sintéticos; não precisam do snapshot.

## Como rodar

O PILAR-2b precisa estar clonado ao lado deste repositório (`../Pilar2b` ou
`../Pilar-2b`), ou em `PILAR2B_DIR`. O snapshot do CP2b fica onde o loader do
PILAR-2b espera; os scripts conferem o sha256 e não rodam com outro arquivo.

```
pip install -r requirements.txt
python scripts/build_evidencia_bmp.py
python scripts/build_evidencia_geracao.py
python scripts/build_evidencia_fde.py
python scripts/build_sensibilidade_cp2b.py
python scripts/build_incerteza_cp2b.py
python scripts/build_mapas_incerteza.py
python scripts/build_incerteza_correlacao.py
python scripts/build_diagnostico_n4_zero.py
python scripts/build_fl_variantes.py
python scripts/build_v52.py
python -m pytest -q
```

Sem o snapshot, os scripts escrevem um relatório dizendo que não rodaram. Não
faça commit desses relatórios.
