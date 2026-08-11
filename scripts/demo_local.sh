#!/usr/bin/env bash
# Demo local del laboratorio: levanta la topología completa (A-I), espera a que
# las tablas converjan y conecta el servidor bancario (en E) y el ATM (en A).
#
# Uso:  bash scripts/demo_local.sh
# El ATM queda interactivo; Ctrl-C cierra todo (los nodos corren en segundo plano).
set -euo pipefail
cd "$(dirname "$0")/.."

PIDS=()
cerrar() { kill "${PIDS[@]}" 2>/dev/null || true; }
trap cerrar EXIT

echo ">> Levantando nodos A-I (routing + forwarding)..."
python3 src/nodo.py A --app-ip 127.0.0.1 --app-puerto 6101 & PIDS+=($!)
for n in B C D F G H I; do
  python3 src/nodo.py "$n" & PIDS+=($!)
done
python3 src/nodo.py E --app-ip 127.0.0.1 --app-puerto 6205 & PIDS+=($!)

echo ">> Esperando convergencia de las tablas (15 s)..."
sleep 15

echo ">> Conectando el servidor bancario en E..."
python3 src/banco.py --nombre E --escucha-puerto 6205 \
  --gateway-ip 127.0.0.1 --gateway-puerto 6005 & PIDS+=($!)
sleep 1

echo ">> Conectando el ATM en A (destino: banco en E)"
python3 src/atm.py --origen A --destino E --escucha-puerto 6101 \
  --gateway-ip 127.0.0.1 --gateway-puerto 6001
