"""Transporte por sockets TCP: mensajes JSON delimitados por salto de línea."""

import json
import socket
import threading

FIN_DE_LINEA = b"\n"


class ServidorLineas:
    """Servidor TCP que entrega al callback cada mensaje JSON recibido."""

    def __init__(self, ip, puerto, callback, callback_crudo=None):
        self.ip = ip
        self.puerto = puerto
        self.callback = callback
        # El plano de datos entrega cadenas de bits (no JSON); si se registra un
        # callback_crudo, esas líneas se le pasan tal cual en vez de descartarse.
        self.callback_crudo = callback_crudo
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
                    self._entregar(linea)

    def _entregar(self, linea):
        """Distingue por contenido: el control es JSON ({...}); los datos, bits."""
        try:
            texto = linea.decode("utf-8").strip()
        except UnicodeDecodeError:
            return
        if not texto:
            return
        if texto.startswith("{"):
            try:
                self.callback(json.loads(texto))
            except json.JSONDecodeError:
                return
        elif self.callback_crudo is not None:
            self.callback_crudo(texto)


def enviar_linea(ip, puerto, texto, timeout=3):
    """Abre una conexión, envía `texto` como una línea y la cierra.

    Devuelve True si el envío se completó, False si el destino no respondió.
    """
    datos = texto.encode("utf-8") + FIN_DE_LINEA
    try:
        with socket.create_connection((ip, puerto), timeout=timeout) as conexion:
            conexion.sendall(datos)
        return True
    except OSError:
        return False


def enviar_json(ip, puerto, mensaje, timeout=3):
    """Envía el mensaje como una línea JSON. Devuelve True si se completó."""
    return enviar_linea(ip, puerto, json.dumps(mensaje), timeout)
