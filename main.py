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


def autoprueba():
    """
    SoftwareMatematicoIA.exe --autoprueba: carga todos los modelos biométricos, la cámara y el
    micrófono sin abrir ventanas y escribe el resultado en autoprueba.txt junto al ejecutable.
    Sirve para comprobar que el .exe quedó completo en otra computadora.
    """
    import faulthandler
    import traceback
    from utils.rutas import ruta_base

    # Si una librería nativa se cae, deja el punto exacto en autoprueba_fallo.txt
    registro_fallo = open(os.path.join(ruta_base(), "autoprueba_fallo.txt"), "w", encoding="utf-8")
    faulthandler.enable(registro_fallo)
    import numpy as np

    resultados = []

    def probar(nombre, funcion):
        try:
            detalle = funcion()
            resultados.append(f"OK    {nombre}: {detalle}")
        except Exception as error:
            resultados.append(f"FALLO {nombre}: {error!r}\n{traceback.format_exc()}")

    def rostro():
        from services.modelos_tm import ModeloRostroTM
        p = ModeloRostroTM.predecir([np.zeros((480, 640, 3), np.uint8)])
        return f"{ModeloRostroTM._sesion.motor}, salida {p.shape}"

    def voz():
        from services.modelos_tm import ModeloVozTM
        p = ModeloVozTM.predecir(0.05 * np.random.default_rng(0).standard_normal(44100 * 2), 44100)
        return f"{ModeloVozTM._sesion.motor}, {len(p)} ventanas"

    def postura():
        from services.modelos_tm import ModeloPosturaTM
        p, visibles, puntos = ModeloPosturaTM.predecir(np.zeros((480, 640, 3), np.uint8))
        return f"clases {ModeloPosturaTM.etiquetas()}, puntos {puntos.shape}"

    def rostro_sface():
        from services.clasificador_imagen import ClasificadorImagen
        return f"YuNet {ClasificadorImagen.cargar_detector_facial()}, SFace {ClasificadorImagen.cargar_reconocedor_facial()}"

    def antispoof():
        from utils import detectores_vida
        assert detectores_vida.cargar_modelos(), detectores_vida.error_carga()
        return "MiniFASNetV2 y malla facial"

    def anteriores():
        from utils.reconocimiento_pose import ReconocedorPose
        from utils.reconocimiento_voz import ReconocedorVoz
        assert ReconocedorPose.cargar_modelo(), ReconocedorPose._error_carga
        assert ReconocedorVoz.cargar_modelo(), ReconocedorVoz._error_carga
        return "postura y voz de la sección Clases"

    def microfono():
        import sounddevice as sd
        return f"entrada predeterminada: {sd.query_devices(kind='input')['name']}"

    def camara():
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        ok = cap.isOpened() and cap.read()[0]
        cap.release()
        return "abre y entrega imagen" if ok else "no disponible (¿otra app la usa?)"

    def vosk():
        import vosk as v
        return f"vosk {getattr(v, '__version__', '')}".strip()

    def base_datos():
        from database.conexion import DB_NAME
        from database.crear_bd import crear_base_datos
        crear_base_datos()
        from controllers.usuario_controller import UsuarioController
        return f"{DB_NAME} ({len(UsuarioController.usuarios_con_rostro())} cuentas con rostro)"

    for nombre, funcion in (("Rostro (ONNX)", rostro), ("Voz (LiteRT)", voz), ("Postura (ONNX)", postura),
                            ("YuNet + SFace", rostro_sface), ("Anti-suplantación", antispoof),
                            ("Modelos de Clases", anteriores), ("Micrófono", microfono),
                            ("Cámara", camara), ("Vosk", vosk), ("Base de datos", base_datos)):
        probar(nombre, funcion)

    with open(os.path.join(ruta_base(), "autoprueba.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(resultados) + "\n")
    sys.exit(0 if all(r.startswith("OK") for r in resultados) else 1)


def main():
    """
    Punto de entrada del sistema.
    """

    if "--autoprueba" in sys.argv:
        autoprueba()

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