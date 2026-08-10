"""Plano de control del router: protocolo Link State."""

import threading
import time

from configuracion import config_nodo, direccion_nodo
from transporte import ServidorLineas, enviar_json

INTERVALO_HELLO = 5
TIEMPO_CAIDA = 15
INTERVALO_VIGILANCIA = 1


class Router:
    """Nodo de la red que descubre vecinos mediante paquetes HELLO."""

    def __init__(self, nombre, topologia):
        self.nombre = nombre
        self.topologia = topologia
        config = config_nodo(topologia, nombre)
        self.ip = config["ip"]
        self.puerto = config["puerto"]
        self.costos_vecinos = dict(config["vecinos"])
        self.vecinos_activos = set(self.costos_vecinos)
        self.ultimo_hello = {}
        self.candado = threading.Lock()
        self.servidor = ServidorLineas(self.ip, self.puerto, self.procesar)

    def iniciar(self):
        # Al arrancar se da un margen de TIEMPO_CAIDA a cada vecino
        # antes de declararlo caído por no haber enviado HELLO.
        ahora = time.time()
        for vecino in self.costos_vecinos:
            self.ultimo_hello[vecino] = ahora
        self.servidor.iniciar()
        threading.Thread(target=self._ciclo_hello, daemon=True).start()
        threading.Thread(target=self._vigilar_vecinos, daemon=True).start()
        print(f"[{self.nombre}] escuchando en {self.ip}:{self.puerto}")

    def procesar(self, mensaje):
        """Despacha cada mensaje recibido según su tipo."""
        tipo = mensaje.get("type")
        if tipo == "HELLO":
            self._procesar_hello(mensaje)

    def _ciclo_hello(self):
        while True:
            hello = {
                "proto": "LinkState",
                "type": "HELLO",
                "from": self.nombre,
                "ttl": 1,
            }
            for vecino in self.costos_vecinos:
                ip, puerto = direccion_nodo(self.topologia, vecino)
                enviar_json(ip, puerto, hello)
            time.sleep(INTERVALO_HELLO)

    def _procesar_hello(self, mensaje):
        vecino = mensaje.get("from")
        if vecino not in self.costos_vecinos:
            return
        with self.candado:
            self.ultimo_hello[vecino] = time.time()
            if vecino not in self.vecinos_activos:
                self.vecinos_activos.add(vecino)
                print(f"[{self.nombre}] vecino {vecino} recuperado")
                self._al_cambiar_vecinos()

    def _vigilar_vecinos(self):
        while True:
            time.sleep(INTERVALO_VIGILANCIA)
            ahora = time.time()
            with self.candado:
                caidos = [
                    vecino
                    for vecino in self.vecinos_activos
                    if ahora - self.ultimo_hello.get(vecino, 0) > TIEMPO_CAIDA
                ]
                for vecino in caidos:
                    self.vecinos_activos.discard(vecino)
                    print(f"[{self.nombre}] vecino {vecino} dado por caído")
                if caidos:
                    self._al_cambiar_vecinos()

    def _al_cambiar_vecinos(self):
        """Reacciona a un cambio en el conjunto de vecinos activos."""
        pass
