import os
import sys

# PyQt5 trae un msvcp140.dll antiguo; si se carga primero, TensorFlow (modelos de
# voz, postura y Teachable Machine) falla al iniciar su runtime nativo. Precargar el
# del sistema antes de importar PyQt5 evita el conflicto sin importar TensorFlow aquí.
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.WinDLL(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "msvcp140.dll"))
    except OSError:
        pass

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from interfaces.video_splash import VideoSplash
from database.crear_bd import crear_base_datos
from database.migrar_passwords import migrar_passwords
from utils.config import cargar_archivo_env
from utils.rutas import ruta_recurso
from utils.instancia_unica import InstanciaUnica


def main():
    """
    Punto de entrada del sistema.
    """

    app = QApplication(sys.argv)

    # Instancia única: si ya hay una ventana abierta, se trae al frente y esta ejecución termina
    instancia = InstanciaUnica()
    if not instancia.es_primera():
        InstanciaUnica.activar_primera()
        sys.exit(0)
    instancia.escuchar()
    app.aboutToQuit.connect(instancia.liberar)

    # Cargar las variables de configuración del archivo .env (si existe)
    cargar_archivo_env()

    # Crear las tablas de la base de datos si no existen
    crear_base_datos()

    # Migrar contraseñas en texto plano a hash SHA-256 + salt (si quedan)
    migrar_passwords()

    # Logo oficial como icono de la aplicación (barra de Windows)
    icono_app = QIcon(ruta_recurso("images/logo.jpg"))
    if not icono_app.isNull():
        app.setWindowIcon(icono_app)

    # Opcional: Nombre de la aplicación
    app.setApplicationName("Software Matemático IA")

    # Crear y mostrar el video de bienvenida
    ventana = VideoSplash()
    ventana.show()

    # Iniciar el ciclo de la aplicación
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()