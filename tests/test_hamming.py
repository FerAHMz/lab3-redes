"""Pruebas de la capa Hamming(7,4): ida y vuelta y corrección de 1 bit."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import hamming  # noqa: E402


class PruebasHamming(unittest.TestCase):
    def test_ida_y_vuelta(self):
        for mensaje in (b"", b"A", b"Hola", b'{"op":"auth"}', bytes(range(256))):
            bits = hamming.codificar(mensaje)
            self.assertEqual(len(bits), len(mensaje) * hamming.BITS_POR_BYTE)
            self.assertEqual(hamming.decodificar(bits), mensaje)

    def test_corrige_un_bit_por_bloque(self):
        mensaje = b"Redes"
        bits = list(hamming.codificar(mensaje))
        # Se corrompe un bit en cada bloque de 7; Hamming(7,4) debe corregirlos.
        for inicio in range(0, len(bits), hamming.BITS_POR_BLOQUE):
            bits[inicio] = "1" if bits[inicio] == "0" else "0"
        corrompido = "".join(bits)
        self.assertEqual(hamming.decodificar(corrompido), mensaje)

    def test_longitud_invalida(self):
        with self.assertRaises(ValueError):
            hamming.decodificar("0101")


if __name__ == "__main__":
    unittest.main()
