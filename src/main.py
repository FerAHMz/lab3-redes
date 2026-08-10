"""Punto de entrada: levanta un nodo del plano de control."""

import argparse
import time

from configuracion import cargar_topologia
from router import Router


def main():
    parser = argparse.ArgumentParser(description="Nodo router Link State")
    parser.add_argument("nombre", help="Identificador del nodo en la topología, ej. A")
    parser.add_argument(
        "--topologia",
        default="config/topologia.json",
        help="Ruta al archivo JSON de topología",
    )
    args = parser.parse_args()

    topologia = cargar_topologia(args.topologia)
    router = Router(args.nombre, topologia)
    router.iniciar()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        router.servidor.detener()


if __name__ == "__main__":
    main()
