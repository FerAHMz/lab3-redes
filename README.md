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

`src/main.py` levanta únicamente el plano de control. Para correr el nodo
completo (routing + forwarding sobre el mismo socket) se usa `src/nodo.py`:

```sh
python3 src/nodo.py A
```

## Plano de datos (Hamming(7,4) + ATM/banco)

Una vez convergidas las tablas, los nodos reenvían **sobres de datos** entre un
ATM y un servidor bancario. Cada sobre viaja como una cadena de bits codificada
con Hamming(7,4): el nodo la decodifica, corrige un bit si hace falta,
reconstruye el JSON, lee el destino (`to`), consulta su tabla y reenvía al
siguiente salto decrementando `ttl` y anotándose en `hops` para cortar bucles.
El plano de control (HELLO/LSA) sigue viajando como texto plano; ambos comparten
el mismo puerto y se distinguen por su contenido (JSON `{...}` vs. bits).

El ATM y el banco no son routers: se conectan por socket a su nodo puerta de
enlace. La demostración usa el ATM en `A` y el banco en `E`. Para levantar todo
en local:

```sh
bash scripts/demo_local.sh
```

O manualmente, tras levantar los nodos (`A` y `E` con `--app-ip`/`--app-puerto`):

```sh
python3 src/banco.py --nombre E --escucha-puerto 6205 --gateway-ip 127.0.0.1 --gateway-puerto 6005
python3 src/atm.py --origen A --destino E --escucha-puerto 6101 --gateway-ip 127.0.0.1 --gateway-puerto 6001
```

El ATM ofrece un menú con las operaciones del laboratorio 2: `auth`, `withdraw`
y `logout`.

## Pruebas

```sh
python3 -m unittest discover -s tests
```

Cubren la ida y vuelta de Hamming con corrección de 1 bit y las reglas de
forwarding (reenvío al siguiente salto, entrega local, descarte por bucle y por
`ttl`).

## Configuración

`config/topologia.json` define por nodo su `ip`, `puerto` y `vecinos` con el
costo de cada enlace. Para las pruebas sobre Tailscale solo hay que sustituir
las IPs locales por las IPs de la red privada de cada integrante.

## Protocolo

Los formatos de los mensajes (HELLO, LSA y el sobre de datos) siguen la
propuesta de protocolo acordada entre las tres parejas de la topología:
JSON por línea para el plano de control, con control de duplicados por `seq`
y respaldo por `ttl` en el flooding.
