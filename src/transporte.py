"""Transporte por sockets TCP: mensajes JSON delimitados por salto de línea."""

import json
import socket
import threading

FIN_DE_LINEA = b"\n"


class ServidorLineas:
    """Servidor TCP que entrega al callback cada mensaje JSON recibido."""

    def __init__(self, ip, puerto, callback):
        self.ip = ip
        self.puerto = puerto
        self.callback = callback
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._activo = False

    def iniciar(self):
        self._socket.bind((self.ip, self.puerto))
        self._socket.listen()
        self._activo = True
        threading.Thread(target=self._aceptar, daemon=True).start()

    def detener(self):
        self._activo = False
        self._socket.close()

    def _aceptar(self):
        while self._activo:
            try:
                conexion, _ = self._socket.accept()
            except OSError:
                break
            threading.Thread(target=self._atender, args=(conexion,), daemon=True).start()

    def _atender(self, conexion):
        buffer = b""
        with conexion:
            while True:
                try:
                    datos = conexion.recv(4096)
                except OSError:
                    break
                if not datos:
                    break
                buffer += datos
                while FIN_DE_LINEA in buffer:
                    linea, buffer = buffer.split(FIN_DE_LINEA, 1)
                    if not linea.strip():
                        continue
                    try:
                        mensaje = json.loads(linea.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    self.callback(mensaje)


def enviar_json(ip, puerto, mensaje, timeout=3):
    """Abre una conexión, envía el mensaje como línea JSON y la cierra.

    Devuelve True si el envío se completó, False si el destino no respondió.
    """
    datos = json.dumps(mensaje).encode("utf-8") + FIN_DE_LINEA
    try:
        with socket.create_connection((ip, puerto), timeout=timeout) as conexion:
            conexion.sendall(datos)
        return True
    except OSError:
        return False
