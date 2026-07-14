#!/usr/bin/env bash
#
# Comando unico do Otimizador de Composicao de Corte de Aco.
# Instala as dependencias (se preciso) e abre a interface visual no navegador.
#
# Uso:
#   ./otimizar.sh          -> abre a interface visual (Streamlit)
#   ./otimizar.sh cli      -> roda o relatorio no terminal (sem interface)
#
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

echo "==> Verificando dependencias..."
if ! "$PY" -c "import streamlit, pulp, pandas" >/dev/null 2>&1; then
  echo "==> Instalando dependencias (primeira vez)..."
  "$PY" -m pip install --quiet -r requirements.txt
fi

if [ "${1:-}" = "cli" ]; then
  echo "==> Relatorio no terminal:"
  exec "$PY" -m otimizador_corte.cli
fi

echo "==> Abrindo a interface no navegador (Ctrl+C para encerrar)..."
exec "$PY" -m streamlit run app.py
