import os
import sys


def es_ejecutable():
    """Indica si la aplicación corre empaquetada (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def ruta_base():
    """Devuelve el directorio base: junto al .exe si está empaquetado, si no la raíz del proyecto."""
    if es_ejecutable():
        return os.path.dirname(os.path.abspath(sys.executable))

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta_recurso(relativa):
    """Resuelve la ruta de un recurso empaquetado (carpeta interna) o de desarrollo."""
    if es_ejecutable():

        base = getattr(sys, "_MEIPASS", None)

        if base:

            ruta = os.path.join(base, relativa)

            if os.path.exists(ruta):
                return ruta

    return os.path.join(ruta_base(), relativa)
