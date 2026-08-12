"""Pruebas del plano de datos: codec del sobre y reglas de forwarding."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import plano_datos  # noqa: E402


class TablaFalsa:
    """Tabla de enrutamiento en memoria para las pruebas."""

    def __init__(self, rutas):
        self.rutas = rutas

    def ruta_hacia(self, destino):
        return self.rutas.get(destino)


class PruebasSobre(unittest.TestCase):
    def test_codec_ida_y_vuelta(self):
        sobre = {"type": "message", "from": "A", "to": "E", "ttl": 16,
                 "hops": [], "payload": {"op": "auth", "user": "juan", "pin": "1234"}}
        bits = plano_datos.codificar_sobre(sobre)
        self.assertEqual(set(bits) <= {"0", "1"}, True)
        self.assertEqual(plano_datos.decodificar_sobre(bits), sobre)


class PruebasForwarding(unittest.TestCase):
    def setUp(self):
        self.enviados = []
        self._enviar_real = plano_datos.enviar_linea
        # Se intercepta el envío por socket para inspeccionar el reenvío.
        plano_datos.enviar_linea = lambda ip, puerto, texto: self.enviados.append(
            (ip, puerto, plano_datos.decodificar_sobre(texto))
        )

    def tearDown(self):
        plano_datos.enviar_linea = self._enviar_real

    def _sobre(self, **cambios):
        base = {"type": "message", "from": "A", "to": "E", "ttl": 16,
                "hops": [], "payload": {"op": "logout"}}
        base.update(cambios)
        return plano_datos.codificar_sobre(base)

    def test_reenvia_al_siguiente_salto(self):
        tabla = TablaFalsa({"E": {"siguiente_salto": "D", "costo": 2,
                                  "ip": "127.0.0.1", "puerto": 6004}})
        capa = plano_datos.CapaRed("F", tabla)
        capa.recibir(self._sobre())
        self.assertEqual(len(self.enviados), 1)
        ip, puerto, sobre = self.enviados[0]
        self.assertEqual((ip, puerto), ("127.0.0.1", 6004))
        self.assertEqual(sobre["ttl"], 15)      # el ttl se decrementa
        self.assertEqual(sobre["hops"], ["F"])  # el nodo se anota en hops

    def test_entrega_local_en_destino(self):
        entregados = []
        capa = plano_datos.CapaRed("E", TablaFalsa({}), entrega_local=entregados.append)
        capa.recibir(self._sobre(to="E"))
        self.assertEqual(len(entregados), 1)
        self.assertEqual(self.enviados, [])  # no se reenvía, se entrega

    def test_descarta_por_bucle(self):
        tabla = TablaFalsa({"E": {"siguiente_salto": "D", "costo": 2,
                                  "ip": "127.0.0.1", "puerto": 6004}})
        capa = plano_datos.CapaRed("F", tabla)
        capa.recibir(self._sobre(hops=["F"]))
        self.assertEqual(self.enviados, [])

    def test_descarta_por_ttl(self):
        tabla = TablaFalsa({"E": {"siguiente_salto": "D", "costo": 2,
                                  "ip": "127.0.0.1", "puerto": 6004}})
        capa = plano_datos.CapaRed("F", tabla)
        capa.recibir(self._sobre(ttl=1))
        self.assertEqual(self.enviados, [])


if __name__ == "__main__":
    unittest.main()
