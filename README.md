# Lab 3 — Protocolos de Enrutamiento

CC3067 Redes, Universidad del Valle de Guatemala

Implementación del protocolo **Link State**: descubrimiento de vecinos con
paquetes HELLO, difusión de LSAs mediante flooding, construcción del grafo de
la red y cálculo de rutas más cortas con Dijkstra. Cada nodo escribe su tabla
en `<nodo>_tabla_enrutamiento.csv`, que usa el plano de datos para reenviar
mensajes.

## Integrantes

- Fernando Hernández — 23645
- Fernando Rueda — 23748

## Requisitos

- Python 3.10 o superior (solo librería estándar, sin dependencias externas)

## Ejecución

Cada nodo es un proceso independiente. Desde la raíz del repositorio:

```sh
python3 src/main.py A
```

El identificador debe existir en `config/topologia.json`. Para levantar la
topología completa en local:

```sh
for n in A B C D E F G H I; do python3 src/main.py $n & done
```

Tras unos segundos los nodos convergen y cada uno genera su archivo
`<nodo>_tabla_enrutamiento.csv` con las columnas
`destino,siguiente_salto,costo,ip,puerto`.

## Configuración

`config/topologia.json` define por nodo su `ip`, `puerto` y `vecinos` con el
costo de cada enlace. Para las pruebas sobre Tailscale solo hay que sustituir
las IPs locales por las IPs de la red privada de cada integrante.

## Protocolo

Los formatos de los mensajes (HELLO, LSA y el sobre de datos) siguen la
propuesta de protocolo acordada entre las tres parejas de la topología:
JSON por línea para el plano de control, con control de duplicados por `seq`
y respaldo por `ttl` en el flooding.
