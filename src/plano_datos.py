"""Plano de datos: capa de red (forwarding) sobre Hamming(7,4).

Los sobres de datos viajan como una cadena de bits codificada con Hamming. Al
recibir uno, el nodo lo decodifica, reconstruye el JSON, lee únicamente el
destino y usa la tabla de enrutamiento para reenviarlo al siguiente salto,
decrementando el `ttl` y anotándose en `hops` para cortar bucles de ruteo.
"""

import csv
import json

import hamming
from transporte import enviar_linea

TTL_POR_DEFECTO = 16


class TablaEnrutamiento:
    """Lee y consulta el CSV `<nodo>_tabla_enrutamiento.csv` del plano de control."""

    def __init__(self, ruta):
        self.ruta = ruta
        self.rutas = {}

    def cargar(self):
        """Recarga la tabla desde el CSV. Devuelve True si pudo leerla."""
        rutas = {}
        try:
            with open(self.ruta, newline="", encoding="utf-8") as archivo:
                for fila in csv.DictReader(archivo):
                    rutas[fila["destino"]] = {
                        "siguiente_salto": fila["siguiente_salto"],
                        "costo": int(fila["costo"]),
                        "ip": fila["ip"],
                        "puerto": int(fila["puerto"]),
                    }
        except (FileNotFoundError, KeyError, ValueError):
            return False
        self.rutas = rutas
        return True

    def ruta_hacia(self, destino):
        """Devuelve la entrada de la tabla para el destino, o None si no hay ruta."""
        # Se relee en cada consulta porque el plano de control regenera el CSV
        # cada vez que el grafo cambia.
        self.cargar()
        return self.rutas.get(destino)


def codificar_sobre(sobre):
    """Serializa el sobre a JSON y lo codifica como cadena de bits Hamming."""
    datos = json.dumps(sobre, ensure_ascii=False).encode("utf-8")
    return hamming.codificar(datos)


def decodificar_sobre(cadena_bits):
    """Recupera el sobre (dict) desde una cadena de bits Hamming."""
    datos = hamming.decodificar(cadena_bits)
    return json.loads(datos.decode("utf-8"))


def enviar_sobre(ip, puerto, sobre):
    """Codifica el sobre con Hamming y lo envía como una línea de bits."""
    return enviar_linea(ip, puerto, codificar_sobre(sobre))


class CapaRed:
    """Reenvía sobres de datos según la tabla; entrega los dirigidos a este nodo."""

    def __init__(self, nombre, tabla, entrega_local=None):
        self.nombre = nombre
        self.tabla = tabla
        self.entrega_local = entrega_local

    def recibir(self, cadena_bits):
        """Punto de entrada del plano de datos: procesa una cadena de bits."""
        try:
            sobre = decodificar_sobre(cadena_bits)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            print(f"[{self.nombre}] sobre de datos ilegible, descartado")
            return
        if sobre.get("to") == self.nombre:
            self._entregar(sobre)
        else:
            self._reenviar(sobre)

    def _entregar(self, sobre):
        """El sobre llegó a su puerta de enlace: se pasa a la app adjunta."""
        print(f"[{self.nombre}] sobre entregado (origen {sobre.get('from')})")
        if self.entrega_local is not None:
            self.entrega_local(sobre)

    def _reenviar(self, sobre):
        destino = sobre.get("to")
        ttl = sobre.get("ttl", TTL_POR_DEFECTO) - 1
        if ttl <= 0:
            print(f"[{self.nombre}] sobre hacia {destino} descartado: ttl agotado")
            return
        hops = list(sobre.get("hops", []))
        if self.nombre in hops:
            print(f"[{self.nombre}] sobre hacia {destino} descartado: bucle detectado")
            return
        ruta = self.tabla.ruta_hacia(destino)
        if ruta is None:
            print(f"[{self.nombre}] sobre hacia {destino} descartado: sin ruta")
            return
        hops.append(self.nombre)
        sobre["ttl"] = ttl
        sobre["hops"] = hops
        enviar_sobre(ruta["ip"], ruta["puerto"], sobre)
        print(f"[{self.nombre}] sobre hacia {destino} reenviado por {ruta['siguiente_salto']}")
