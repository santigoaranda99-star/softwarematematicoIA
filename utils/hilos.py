"""Ejecución de tareas pesadas (modelos de voz, postura) en un QThread sin bloquear la interfaz."""
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import QProgressDialog


class TareaEnHilo(QThread):
    """Ejecuta una función en otro hilo y emite (resultado, error) al terminar."""

    terminado = pyqtSignal(object, object)

    def __init__(self, funcion, args=(), parent=None):
        super().__init__(parent)
        self._funcion = funcion
        self._args = args

    def run(self):
        try:
            self.terminado.emit(self._funcion(*self._args), None)
        except Exception as error:  # el error se muestra en el hilo de la interfaz
            self.terminado.emit(None, error)


# Referencias vivas de los hilos para que el recolector no los destruya a mitad
_HILOS_ACTIVOS = set()


def ejecutar_en_hilo(parent, funcion, args, al_terminar, mensaje=None):
    """
    Lanza funcion(*args) en un QThread. Mientras trabaja muestra (si se indica) un aviso
    de espera sin bloquear la ventana; al terminar llama a al_terminar(resultado, error)
    en el hilo de la interfaz.
    """
    espera = None
    if mensaje:
        espera = QProgressDialog(mensaje, None, 0, 0, parent)
        espera.setWindowTitle("Un momento...")
        espera.setWindowModality(Qt.WindowModal)
        espera.setMinimumDuration(0)
        espera.setCancelButton(None)
        espera.show()

    hilo = TareaEnHilo(funcion, args)
    _HILOS_ACTIVOS.add(hilo)

    def fin(resultado, error):
        if espera is not None:
            espera.close()
        al_terminar(resultado, error)

    def liberar():
        _HILOS_ACTIVOS.discard(hilo)
        hilo.deleteLater()

    hilo.terminado.connect(fin)
    hilo.finished.connect(liberar)
    hilo.start()
    return hilo
