"""Capa de detección y corrección de errores Hamming(7,4).

Cada byte se parte en dos nibbles (el más significativo primero) y cada nibble
`d1 d2 d3 d4` se codifica en un bloque de 7 bits `p1 p2 d1 p3 d2 d3 d4` con
paridad par. Son 14 bits por byte. Al decodificar se calcula el síndrome, se
corrige un bit si el síndrome lo señala y se recuperan los datos originales.
"""

BITS_POR_BLOQUE = 7
BITS_POR_BYTE = 14


def _codificar_nibble(d1, d2, d3, d4):
    """Devuelve el bloque `p1 p2 d1 p3 d2 d3 d4` con paridad par."""
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p3 = d2 ^ d3 ^ d4
    return [p1, p2, d1, p3, d2, d3, d4]


def _decodificar_bloque(bloque):
    """Corrige un bit si hace falta y devuelve el nibble (d1, d2, d3, d4)."""
    r = list(bloque)
    # El síndrome apunta a la posición (1..7) del bit erróneo; 0 significa correcto.
    s1 = r[0] ^ r[2] ^ r[4] ^ r[6]
    s2 = r[1] ^ r[2] ^ r[5] ^ r[6]
    s3 = r[3] ^ r[4] ^ r[5] ^ r[6]
    posicion = s1 + (s2 << 1) + (s3 << 2)
    if posicion:
        r[posicion - 1] ^= 1
    return r[2], r[4], r[5], r[6]


def codificar(datos):
    """Convierte bytes en una cadena de bits ('0'/'1') codificada con Hamming."""
    bits = []
    for byte in datos:
        for nibble in ((byte >> 4) & 0xF, byte & 0xF):
            d1 = (nibble >> 3) & 1
            d2 = (nibble >> 2) & 1
            d3 = (nibble >> 1) & 1
            d4 = nibble & 1
            bits.extend(_codificar_nibble(d1, d2, d3, d4))
    return "".join(str(bit) for bit in bits)


def decodificar(cadena_bits):
    """Convierte una cadena de bits Hamming en los bytes originales corregidos."""
    if len(cadena_bits) % BITS_POR_BYTE:
        raise ValueError("La cadena de bits no es múltiplo de 14")
    bits = [1 if caracter == "1" else 0 for caracter in cadena_bits]
    salida = bytearray()
    for inicio in range(0, len(bits), BITS_POR_BYTE):
        alto = _decodificar_bloque(bits[inicio:inicio + BITS_POR_BLOQUE])
        bajo = _decodificar_bloque(bits[inicio + BITS_POR_BLOQUE:inicio + BITS_POR_BYTE])
        nibble_alto = (alto[0] << 3) | (alto[1] << 2) | (alto[2] << 1) | alto[3]
        nibble_bajo = (bajo[0] << 3) | (bajo[1] << 2) | (bajo[2] << 1) | bajo[3]
        salida.append((nibble_alto << 4) | nibble_bajo)
    return bytes(salida)
