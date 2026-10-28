"""
Protección de instancia única: si la aplicación ya está abierta, una segunda ejecución avisa
a la primera (que se trae al frente) y se cierra sola.

- QLockFile en la carpeta temporal: solo una instancia obtiene el bloqueo. Si la app se
  cerró de golpe, Qt detecta el bloqueo huérfano (proceso inexistente) y lo libera.
- QLocalServer / QLocalSocket con un nombre fijo: canal para pedir "mostrarse".
"""
import os

from PyQt5.QtCore import QDir, QLockFile, Qt
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import QApplication

NOMBRE = "SoftwareMatematicoIA-instancia-unica"


class InstanciaUnica:

    def __init__(self):
        self._bloqueo = QLockFile(os.path.join(QDir.tempPath(), NOMBRE + ".lock"))
        self._servidor = None

    def es_primera(self):
        """True si esta es la única instancia (obtiene el bloqueo)."""
        return self._bloqueo.tryLock(100)

    @staticmethod
    def activar_primera():
        """Pide a la instancia que ya está abierta que se traiga al frente."""
        socket = QLocalSocket()
        socket.connectToServer(NOMBRE)
        if socket.waitForConnected(500):
            socket.write(b"mostrar")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()

    def escuchar(self):
        """En la primera instancia: atiende los avisos de ejecuciones posteriores."""
        QLocalServer.removeServer(NOMBRE)  # nombre que haya quedado de un cierre inesperado
        self._servidor = QLocalServer()
        self._servidor.newConnection.connect(self._traer_al_frente)
        self._servidor.listen(NOMBRE)

    def _traer_al_frente(self):
        conexion = self._servidor.nextPendingConnection()
        if conexion is not None:
            conexion.disconnected.connect(conexion.deleteLater)
        for ventana in QApplication.topLevelWidgets():
            if ventana.isVisible() and ventana.isWindow():
                ventana.setWindowState((ventana.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
                ventana.raise_()
                ventana.activateWindow()

    def liberar(self):
        if self._servidor is not None:
            self._servidor.close()
        self._bloqueo.unlock()
