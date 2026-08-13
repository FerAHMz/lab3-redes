"""Plano de control del router: protocolo Link State."""

import csv
import os
import threading
import time

from configuracion import config_nodo, direccion_nodo
from dijkstra import caminos_mas_cortos, siguiente_salto
from transporte import ServidorLineas, enviar_json

INTERVALO_HELLO = 5
TIEMPO_CAIDA = 15
INTERVALO_VIGILANCIA = 1
TTL_LSA = 8
# Refresco periódico del LSA propio (estilo LSRefresh de OSPF). Sin esto, un LSA
# perdido en el flooding inicial nunca se re-anuncia y los nodos lejanos quedan
# sin aprender nuestros enlaces cuando la topología cambia con la red ya viva.
INTERVALO_REEMISION = 30
# Directorio donde se persiste el número de secuencia del LSA propio, para que un
# nodo que se reinicia no vuelva a numerar desde cero.
DIRECTORIO_ESTADO = "state"


class Router:
    """Nodo de la red que descubre vecinos, difunde LSAs y mantiene la LSDB."""

    def __init__(self, nombre, topologia):
        self.nombre = nombre
        self.topologia = topologia
        config = config_nodo(topologia, nombre)
        self.ip = config["ip"]
        self.puerto = config["puerto"]
        self.costos_vecinos = dict(config["vecinos"])
        self.vecinos_activos = set(self.costos_vecinos)
        self.ultimo_hello = {}
        # El seq no vuelve a cero al reiniciar: se retoma el último valor
        # persistido para que la red no descarte nuestros LSA nuevos por "viejos".
        self.seq = self._cargar_seq()
        self.lsdb = {}
        self.mayor_seq = {}
        self.candado = threading.Lock()
        self.servidor = ServidorLineas(self.ip, self.puerto, self.procesar)

    # ------------------------------------------------------------------
    # Persistencia del número de secuencia
    # ------------------------------------------------------------------

    def _ruta_seq(self):
        return os.path.join(DIRECTORIO_ESTADO, f"{self.nombre}_seq.txt")

    def _cargar_seq(self):
        """Lee el último seq persistido; 0 si no existe o está corrupto."""
        try:
            with open(self._ruta_seq(), encoding="utf-8") as archivo:
                return int(archivo.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def _guardar_seq(self):
        """Persiste el seq propio de forma atómica (escribe y renombra)."""
        os.makedirs(DIRECTORIO_ESTADO, exist_ok=True)
        ruta = self._ruta_seq()
        temporal = f"{ruta}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            archivo.write(str(self.seq))
        os.replace(temporal, ruta)

    def iniciar(self):
        # Al arrancar se da un margen de TIEMPO_CAIDA a cada vecino
        # antes de declararlo caído por no haber enviado HELLO.
        ahora = time.time()
        for vecino in self.costos_vecinos:
            self.ultimo_hello[vecino] = ahora
        self.servidor.iniciar()
        threading.Thread(target=self._ciclo_hello, daemon=True).start()
        threading.Thread(target=self._vigilar_vecinos, daemon=True).start()
        threading.Thread(target=self._ciclo_reemision, daemon=True).start()
        with self.candado:
            self._emitir_lsa()
        print(f"[{self.nombre}] escuchando en {self.ip}:{self.puerto}")

    def _ciclo_reemision(self):
        """Re-anuncia el LSA propio cada INTERVALO_REEMISION segundos.

        Es el respaldo contra floods perdidos: aunque no cambien los vecinos, el
        seq sube y el anuncio vuelve a inundarse, de modo que un nodo que se sumó
        tarde (p. ej. al cerrar un bucle) termina aprendiendo nuestros enlaces.
        """
        while True:
            time.sleep(INTERVALO_REEMISION)
            with self.candado:
                self._emitir_lsa()

    def procesar(self, mensaje):
        """Despacha cada mensaje recibido según su tipo."""
        tipo = mensaje.get("type")
        if tipo == "HELLO":
            self._procesar_hello(mensaje)
        elif tipo == "LSA":
            self._procesar_lsa(mensaje)

    # ------------------------------------------------------------------
    # HELLO
    # ------------------------------------------------------------------

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
        """Ante un cambio de vecinos se anuncia un LSA nuevo. Requiere el candado."""
        self._emitir_lsa()

    # ------------------------------------------------------------------
    # LSA y flooding
    # ------------------------------------------------------------------

    def _emitir_lsa(self):
        """Genera el LSA propio con seq nuevo y lo difunde. Requiere el candado."""
        self.seq += 1
        enlaces = {
            vecino: costo
            for vecino, costo in self.costos_vecinos.items()
            if vecino in self.vecinos_activos
        }
        lsa = {
            "proto": "LinkState",
            "type": "LSA",
            "origin": self.nombre,
            "seq": self.seq,
            "links": enlaces,
            "from": self.nombre,
            "ttl": TTL_LSA,
        }
        self.lsdb[self.nombre] = enlaces
        self.mayor_seq[self.nombre] = self.seq
        self._guardar_seq()
        self._recalcular()
        print(f"[{self.nombre}] emito LSA propio (seq={self.seq}, enlaces={enlaces}) e inundo a mis vecinos")
        self._inundar(lsa, excepto=None)

    def _procesar_lsa(self, mensaje):
        origen = mensaje.get("origin")
        seq = mensaje.get("seq")
        enlaces = mensaje.get("links")
        emisor = mensaje.get("from")
        if origen is None or seq is None or not isinstance(enlaces, dict):
            return
        with self.candado:
            # Eco de un LSA propio: si la red recuerda un seq mayor que el nuestro
            # (típico tras un reinicio), lo superamos y re-anunciamos para que dejen
            # de vernos "viejos". En un nodo hoja este eco no llega por split horizon,
            # por eso la persistencia del seq es la que realmente lo cubre.
            if origen == self.nombre:
                if seq > self.seq:
                    self.seq = seq
                    self._emitir_lsa()
                return
            # El seq corta los ciclos: solo se acepta una versión más nueva.
            if seq <= self.mayor_seq.get(origen, -1):
                print(f"[{self.nombre}] LSA de {origen} (seq={seq}) descartado: duplicado o viejo")
                return
            self.mayor_seq[origen] = seq
            self.lsdb[origen] = dict(enlaces)
            print(f"[{self.nombre}] LSA de {origen} (seq={seq}) aceptado; recibido de {emisor}")
            self._recalcular()
            # El ttl es el respaldo contra LSAs que sobreviven al control de seq.
            ttl = mensaje.get("ttl", TTL_LSA) - 1
            if ttl <= 0:
                print(f"[{self.nombre}] LSA de {origen} (seq={seq}) no reenviado: ttl agotado")
                return
            reenvio = dict(mensaje)
            reenvio["ttl"] = ttl
            reenvio["from"] = self.nombre
            print(f"[{self.nombre}] reenvío (flooding) LSA de {origen} (seq={seq}) a mis vecinos")
            self._inundar(reenvio, excepto=emisor)

    def _inundar(self, lsa, excepto):
        """Envía el LSA a todos los vecinos activos menos al que lo mandó."""
        for vecino in self.vecinos_activos:
            if vecino == excepto:
                continue
            ip, puerto = direccion_nodo(self.topologia, vecino)
            enviar_json(ip, puerto, lsa)

    # ------------------------------------------------------------------
    # Rutas y tabla de enrutamiento
    # ------------------------------------------------------------------

    def _recalcular(self):
        """Corre Dijkstra sobre la LSDB y reescribe la tabla. Requiere el candado."""
        distancias, previos = caminos_mas_cortos(self.lsdb, self.nombre)
        ruta_csv = f"{self.nombre}_tabla_enrutamiento.csv"
        with open(ruta_csv, "w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["destino", "siguiente_salto", "costo", "ip", "puerto"])
            for destino in sorted(distancias):
                if destino == self.nombre:
                    continue
                salto = siguiente_salto(previos, self.nombre, destino)
                if salto is None or destino not in self.topologia:
                    continue
                ip, puerto = direccion_nodo(self.topologia, salto)
                escritor.writerow([destino, salto, distancias[destino], ip, puerto])
