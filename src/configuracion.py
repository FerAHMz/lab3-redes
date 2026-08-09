"""Carga de la topología y de la configuración de cada nodo."""

import json


def cargar_topologia(ruta):
    """Lee el archivo JSON de topología y lo devuelve como diccionario."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def config_nodo(topologia, nombre):
    """Devuelve la configuración (ip, puerto, vecinos) del nodo indicado."""
    if nombre not in topologia:
        raise KeyError(f"El nodo {nombre} no existe en la topología")
    return topologia[nombre]


def direccion_nodo(topologia, nombre):
    """Devuelve la tupla (ip, puerto) del nodo indicado."""
    nodo = config_nodo(topologia, nombre)
    return nodo["ip"], nodo["puerto"]
