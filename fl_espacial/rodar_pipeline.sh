#!/usr/bin/env bash
# Pipeline completo do FL espacial + cascata v5 no ambiente fixado (Metodo_CP2b/.venv, pandas 2.2.3).
# Uso: bash rodar_pipeline.sh          (a passada pesada do 04 leva ~40 min por rede e é retomável)
set -euo pipefail
cd "$(dirname "$0")"
PY=../.venv/Scripts/python.exe
for passo in "00_fabricas_suco.py" "01_grafo.py" "02_oferta.py" "03_hubs.py" "03b_palha_usinas.py" "03b_palha_usinas.py sem_track" \
             "04_bacias_fl.py" "04_bacias_fl.py sem_track" "04b_alocacao.py" "05_validacao_sensibilidade.py" \
             "06_integracao.py" "../cp2b_cascade.py" "07_reconciliacao_v5.py"; do
  echo "=== $(date +%H:%M:%S) $passo"
  log="logs/stdout_$(basename "${passo// /_}")"
  $PY $passo > "${log%.py}.txt" 2>&1
done
echo "=== $(date +%H:%M:%S) fim"
