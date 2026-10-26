# Patch v5 da cascata: FL espacial

Aplicação autorizada no CHECKPOINT 2 (decisão 4, 24/09/2026): variante **B** (co-digestão com alocação) e a palha só nas usinas. Os originais da v4 ficam em `cp2b_params_v4.py.bak` e `cp2b_cascade_v4.py.bak`. A pasta `outputs/` da v4 não é tocada; a v5 grava em `outputs_v5/`.

## O que muda

| Arquivo | Mudança |
|---|---|
| `cp2b_params.py` | 16 substratos passam a `FL="espacial"`. Quem usava uma chave própria do yaml a mantém em `FL_ref`, só como referência. BOV_PASTO_MISTO continua com o FL do yaml. Novos blocos: `FL_ESPACIAL` (arquivos `fl_espacial/outputs/fl_v5_*_substrato.csv` e variante `codig_alocado`) e `PASTA_SAIDA = "outputs_v5"`. |
| `cp2b_cascade.py` | `resolve()` reconhece `FL="espacial"`. A cascata lê o FL por município × cenário do arquivo consolidado; município sem oferta N3 do substrato recebe o FL estadual, o que não altera nada porque o N3 é zero. BASISDATEN registra a fonte. A saída vai para `P.PASTA_SAIDA`. |

Diferenças linha a linha contra a v4: `patch_cascata_v5.diff`.

**Variantes** (`FL_ESPACIAL["variante"]`):

| Valor | Variante | Papel |
|---|---|---|
| `codig_alocado` | B, co-digestão com alocação | principal |
| `codigestao` | A, co-digestão por cobertura | limite superior |
| `mono_alocado` | D, monodigestão com alocação | limite inferior |
| `mono` | C, monodigestão por cobertura | sensibilidade |

Para rodar outra variante, troque também `PASTA_SAIDA`, por exemplo para `outputs_v5_D`, e o `integracao.variante_principal` do `config_fl.yaml`, porque o `06` confere se os dois batem.

## Ordem de execução

Use sempre o ambiente fixado. A cascata quebra com pandas 3 e com pandas < 2.2.

```bash
cd "C:/Users/Lucas/Documents/Reposicionamento_Submissão_ESD/Metodo_CP2b"
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # uma vez
bash fl_espacial/rodar_pipeline.sh                                               # 01 → 06 (FL e arquivos fl_v5_*)
.venv/Scripts/python cp2b_cascade.py                                             # cascata v5 → outputs_v5/cp2b_*.csv
.venv/Scripts/python fl_espacial/07_reconciliacao_v5.py                          # reconciliação v4 × v5 e conferências
```

`testar_patch.py` roda uma cópia temporária da cascata do patch sem tocar nos arquivos da raiz. Foi o teste feito antes da aplicação e confere N1–N3 iguais aos da v4 e N4 igual ao da variante B no `06`.

## Como voltar à v4

```bash
cp cp2b_params_v4.py.bak cp2b_params.py && cp cp2b_cascade_v4.py.bak cp2b_cascade.py
.venv/Scripts/python cp2b_cascade.py        # grava de novo em outputs/
```
