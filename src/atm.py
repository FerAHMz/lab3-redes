"""Nodo ATM (cliente) del plano de datos.

No es un router: se conecta por sockets a su puerta de enlace. Arma los sobres de
datos con las operaciones del laboratorio 2 (auth, withdraw, logout), los
codifica con Hamming y los envía a su puerta de enlace, que los enruta hasta el
servidor bancario. Escucha en paralelo las respuestas que le entrega su router.

Uso:
    python3 src/atm.py --origen A --destino E --escucha-puerto 6101 \
        --gateway-ip 127.0.0.1 --gateway-puerto 6001
"""

import argparse
import time

from plano_datos import TTL_POR_DEFECTO, decodificar_sobre, enviar_sobre
from transporte import ServidorLineas


class ATM:
    """Cliente ATM adjunto a un nodo router (su puerta de enlace)."""

    def __init__(self, origen, destino, escucha, gateway):
        self.origen = origen        # nombre del nodo puerta de enlace del ATM, ej. "A"
        self.destino = destino      # nombre del nodo puerta de enlace del banco, ej. "E"
        self.escucha = escucha      # (ip, puerto) local donde recibe respuestas
        self.gateway = gateway      # (ip, puerto) del router puerta de enlace

    def iniciar(self):
        servidor = ServidorLineas(
            self.escucha[0], self.escucha[1], lambda _m: None, callback_crudo=self.recibir
        )
        servidor.iniciar()
        print(f"[ATM {self.origen}] escuchando respuestas en {self.escucha[0]}:{self.escucha[1]}")
        return servidor

    def recibir(self, cadena_bits):
        try:
            sobre = decodificar_sobre(cadena_bits)
        except Exception:
            print(f"[ATM {self.origen}] respuesta ilegible")
            return
        print(f"[ATM {self.origen}] respuesta del banco: {sobre.get('payload')}")

    def enviar(self, payload):
        """Arma el sobre hacia el banco, lo codifica con Hamming y lo despacha."""
        sobre = {
            "type": "message",
            "from": self.origen,
            "to": self.destino,
            "ttl": TTL_POR_DEFECTO,
            "hops": [],
            "payload": payload,
        }
        enviar_sobre(self.gateway[0], self.gateway[1], sobre)


def menu(atm):
    opciones = {
        "1": ("Autenticarse", _pedir_auth),
        "2": ("Retirar", _pedir_withdraw),
        "3": ("Cerrar sesión", lambda: {"op": "logout"}),
    }
    while True:
        print("\n1) Autenticarse  2) Retirar  3) Cerrar sesión  4) Salir")
        eleccion = input("> ").strip()
        if eleccion == "4":
            break
        entrada = opciones.get(eleccion)
        if entrada is None:
            print("Opción inválida")
            continue
        atm.enviar(entrada[1]())
        # Pequeña espera para ver la respuesta antes de volver a pedir opción.
        time.sleep(1)


def _pedir_auth():
    return {"op": "auth", "user": input("Usuario: ").strip(), "pin": input("PIN: ").strip()}


def _pedir_withdraw():
    return {"op": "withdraw", "amount": int(input("Monto: ").strip() or 0)}


def main():
    parser = argparse.ArgumentParser(description="Nodo ATM (cliente) del plano de datos")
    parser.add_argument("--origen", required=True, help="Nodo puerta de enlace del ATM, ej. A")
    parser.add_argument("--destino", required=True, help="Nodo puerta de enlace del banco, ej. E")
    parser.add_argument("--escucha-ip", default="127.0.0.1")
    parser.add_argument("--escucha-puerto", type=int, required=True)
    parser.add_argument("--gateway-ip", default="127.0.0.1")
    parser.add_argument("--gateway-puerto", type=int, required=True)
    args = parser.parse_args()

    atm = ATM(
        args.origen,
        args.destino,
        (args.escucha_ip, args.escucha_puerto),
        (args.gateway_ip, args.gateway_puerto),
    )
    atm.iniciar()
    try:
        menu(atm)
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == "__main__":
    main()
