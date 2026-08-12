"""Punto de entrada del nodo completo: plano de control + plano de datos.

Levanta el router Link State (routing) y la capa de red (forwarding) sobre el
mismo socket, corriendo en paralelo mediante hilos. El plano de control viaja
como JSON de texto y el plano de datos como cadenas de bits Hamming; el servidor
los distingue por su contenido.

Uso:
    python3 src/nodo.py A
    python3 src/nodo.py A --app-ip 127.0.0.1 --app-puerto 6101
"""

import argparse
import time

from configuracion import cargar_topologia
from plano_datos import CapaRed, TablaEnrutamiento, enviar_sobre
from router import Router
from transporte import ServidorLineas


def main():
    parser = argparse.ArgumentParser(description="Nodo router con plano de datos")
    parser.add_argument("nombre", help="Identificador del nodo en la topología, ej. A")
    parser.add_argument(
        "--topologia",
        default="config/topologia.json",
        help="Ruta al archivo JSON de topología",
    )
    parser.add_argument("--app-ip", help="IP de la aplicación (ATM o banco) adjunta a este nodo")
    parser.add_argument("--app-puerto", type=int, help="Puerto de la aplicación adjunta")
    args = parser.parse_args()

    topologia = cargar_topologia(args.topologia)
    router = Router(args.nombre, topologia)

    tabla = TablaEnrutamiento(f"{args.nombre}_tabla_enrutamiento.csv")
    entrega = None
    if args.app_ip and args.app_puerto:
        def entrega(sobre, ip=args.app_ip, puerto=args.app_puerto):
            enviar_sobre(ip, puerto, sobre)
    capa = CapaRed(args.nombre, tabla, entrega_local=entrega)

    # Un único socket atiende ambos planos: JSON para el control, bits para los
    # datos. El forwarding corre en su propio hilo, en paralelo al routing.
    router.servidor = ServidorLineas(
        router.ip, router.puerto, router.procesar, callback_crudo=capa.recibir
    )
    router.iniciar()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        router.servidor.detener()


if __name__ == "__main__":
    main()
