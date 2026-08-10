"""Cálculo de rutas más cortas sobre el grafo construido con la LSDB."""

import heapq

INFINITO = float("inf")


def caminos_mas_cortos(grafo, origen):
    """Dijkstra sobre un grafo {nodo: {vecino: costo}}.

    Devuelve (distancias, previos), donde previos permite reconstruir
    la ruta de cada destino hacia el origen.
    """
    distancias = {origen: 0}
    previos = {}
    visitados = set()
    cola = [(0, origen)]
    while cola:
        distancia, nodo = heapq.heappop(cola)
        if nodo in visitados:
            continue
        visitados.add(nodo)
        for vecino, costo in grafo.get(nodo, {}).items():
            nueva = distancia + costo
            if nueva < distancias.get(vecino, INFINITO):
                distancias[vecino] = nueva
                previos[vecino] = nodo
                heapq.heappush(cola, (nueva, vecino))
    return distancias, previos


def siguiente_salto(previos, origen, destino):
    """Retrocede por los previos hasta encontrar el primer salto desde el origen."""
    actual = destino
    while previos.get(actual) is not None:
        if previos[actual] == origen:
            return actual
        actual = previos[actual]
    return None
