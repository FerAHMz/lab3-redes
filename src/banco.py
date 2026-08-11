"""Servidor bancario del plano de datos.

No es un router: se conecta por sockets a su puerta de enlace. Recibe sobres de
datos (cadenas de bits Hamming), atiende la operación del payload (auth,
withdraw, error, logout, reutilizado del laboratorio 2) y responde por la misma
puerta de enlace hacia el nodo del ATM.

Uso:
    python3 src/banco.py --nombre E --escucha-puerto 6205 \
        --gateway-ip 127.0.0.1 --gateway-puerto 6005
"""

import argparse
import time

from plano_datos import TTL_POR_DEFECTO, decodificar_sobre, enviar_sobre
from transporte import ServidorLineas

# Cuentas de ejemplo para la demostración.
CUENTAS = {
    "juan": {"pin": "1234", "saldo": 1000},
    "ana": {"pin": "4321", "saldo": 500},
}


class Banco:
    """Servidor bancario adjunto a un nodo router (su puerta de enlace)."""

    def __init__(self, nombre, escucha, gateway):
        self.nombre = nombre        # nombre del nodo puerta de enlace, ej. "E"
        self.escucha = escucha      # (ip, puerto) local donde recibe entregas
        self.gateway = gateway      # (ip, puerto) del router puerta de enlace
        self.sesiones = {}          # nodo origen -> usuario autenticado

    def iniciar(self):
        servidor = ServidorLineas(
            self.escucha[0], self.escucha[1], lambda _m: None, callback_crudo=self.recibir
        )
        servidor.iniciar()
        print(f"[banco {self.nombre}] escuchando en {self.escucha[0]}:{self.escucha[1]}")
        return servidor

    def recibir(self, cadena_bits):
        try:
            sobre = decodificar_sobre(cadena_bits)
        except Exception:
            print(f"[banco {self.nombre}] sobre ilegible, descartado")
            return
        origen = sobre.get("from")
        payload = sobre.get("payload", {})
        print(f"[banco {self.nombre}] {origen} -> {payload}")
        respuesta = self.atender(origen, payload)
        self.responder(origen, respuesta)

    def atender(self, origen, payload):
        """Aplica la operación del laboratorio 2 y devuelve el payload de respuesta."""
        op = payload.get("op")
        if op == "auth":
            return self._auth(origen, payload)
        if op == "withdraw":
            return self._withdraw(origen, payload)
        if op == "logout":
            self.sesiones.pop(origen, None)
            return {"op": "logout", "status": "ok"}
        if op == "error":
            return {"op": "error", "code": payload.get("code", ""), "msg": payload.get("msg", "")}
        return {"op": "error", "code": "OP_INVALIDA", "msg": f"operación desconocida: {op}"}

    def _auth(self, origen, payload):
        usuario = payload.get("user")
        cuenta = CUENTAS.get(usuario)
        if cuenta is None or cuenta["pin"] != payload.get("pin"):
            return {"op": "auth", "status": "error", "msg": "credenciales inválidas"}
        self.sesiones[origen] = usuario
        return {"op": "auth", "status": "ok", "user": usuario, "saldo": cuenta["saldo"]}

    def _withdraw(self, origen, payload):
        usuario = self.sesiones.get(origen)
        if usuario is None:
            return {"op": "withdraw", "status": "error", "msg": "no autenticado"}
        monto = payload.get("amount", 0)
        cuenta = CUENTAS[usuario]
        if monto <= 0 or monto > cuenta["saldo"]:
            return {"op": "withdraw", "status": "error", "msg": "monto inválido o saldo insuficiente"}
        cuenta["saldo"] -= monto
        return {"op": "withdraw", "status": "ok", "amount": monto, "saldo": cuenta["saldo"]}

    def responder(self, destino, payload):
        """Envía la respuesta al nodo del ATM por la puerta de enlace."""
        sobre = {
            "type": "message",
            "from": self.nombre,
            "to": destino,
            "ttl": TTL_POR_DEFECTO,
            "hops": [],
            "payload": payload,
        }
        enviar_sobre(self.gateway[0], self.gateway[1], sobre)


def main():
    parser = argparse.ArgumentParser(description="Servidor bancario del plano de datos")
    parser.add_argument("--nombre", required=True, help="Nombre del nodo puerta de enlace, ej. E")
    parser.add_argument("--escucha-ip", default="127.0.0.1")
    parser.add_argument("--escucha-puerto", type=int, required=True)
    parser.add_argument("--gateway-ip", default="127.0.0.1")
    parser.add_argument("--gateway-puerto", type=int, required=True)
    args = parser.parse_args()

    banco = Banco(
        args.nombre,
        (args.escucha_ip, args.escucha_puerto),
        (args.gateway_ip, args.gateway_puerto),
    )
    banco.iniciar()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
