"""
Captura en modo registro de voz y postura (compartida por "Crear una cuenta" y
"Vincular mi Biometría"), mensajes comunes y estilo de los botones biométricos.
"""
import numpy as np

from utils.mensajes import Mensajes
from utils.umbrales_biometria import UMBRAL_CONFIANZA_POSTURA_TM

# Mismo aspecto en login, registro y vinculación: Rostro=verde, Voz=morado, Postura=azul
ESTILO_BOTONES_BIOMETRIA = """
    QPushButton#btnFacial, QPushButton#btnVoz, QPushButton#btnPose {
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#btnFacial { background: #0D9488; }
    QPushButton#btnFacial:hover { background: #0F766E; }
    QPushButton#btnFacial:pressed { background: #115E59; }
    QPushButton#btnVoz { background: #4F46E5; }
    QPushButton#btnVoz:hover { background: #4338CA; }
    QPushButton#btnVoz:pressed { background: #3730A3; }
    QPushButton#btnPose { background: #0284C7; }
    QPushButton#btnPose:hover { background: #0369A1; }
    QPushButton#btnPose:pressed { background: #075985; }
"""

MUESTRAS_REGISTRO_VOZ = 3
SEGUNDOS_GRABACION_VOZ = 2.0
# El umbral de voz está en ReconocedorVoz.UMBRAL_CONFIANZA (bajado temporalmente a 0.50)
UMBRAL_CONFIANZA_REGISTRO_POSE = UMBRAL_CONFIANZA_POSTURA_TM
UMBRAL_CONFIANZA_VERIFICACION_POSE = UMBRAL_CONFIANZA_POSTURA_TM

# metodo -> (con artículo, título del aviso, terminación de "vinculado")
_METODOS = {
    "rostro": ("un rostro", "Rostro No Vinculado", "o"),
    "voz": ("una voz", "Voz No Vinculada", "a"),
    "postura": ("una postura", "Postura No Vinculada", "a"),
}


def campo(datos, columna):
    """Lee una columna de un sqlite3.Row o dict, devolviendo '' si no existe (BD sin migrar)."""
    try:
        return datos[columna] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def biometria_vinculada(datos, metodo):
    """
    Devuelve (etiqueta, vector) guardados para 'voz' o 'postura', o (None, None) si no se
    vinculó (o la clase guardada ya no existe en el modelo). 'datos' puede ser una fila de
    usuarios o de clase_biometria: ambas usan etiqueta_voz/embedding_voz/etiqueta_pose/embedding_pose.
    """
    import json

    if metodo == "voz":
        from utils.reconocimiento_voz import ReconocedorVoz as Reconocedor
        sufijo = "voz"
    else:
        from utils.reconocimiento_pose import ReconocedorPose as Reconocedor
        sufijo = "pose"

    etiqueta = Reconocedor.clase_vinculada(campo(datos, f"etiqueta_{sufijo}"))
    try:
        vector = json.loads(campo(datos, f"embedding_{sufijo}") or "null")
    except ValueError:
        vector = None
    if etiqueta is None or not vector:
        return None, None
    return etiqueta, vector


def abrir_camara_pose(parent, titulo_ventana, titulo, al_capturar):
    """
    Abre la cámara en modo postura con los textos indicados y conecta la ráfaga capturada
    a al_capturar(frames). Devuelve la ventana (el llamador debe conservar la referencia).
    """
    from interfaces.camara import VentanaCamara

    ventana = VentanaCamara(parent)
    ventana.modo_pose = True
    ventana.setWindowTitle(titulo_ventana)
    ventana.titulo.setText(titulo)
    ventana.lblEstado.setText(
        f"Aléjese para que se vea su cuerpo y presione 'Capturar Postura'. "
        f"Tendrá {VentanaCamara.SEGUNDOS_CUENTA_POSE} segundos para colocarse."
    )
    ventana.btnCapturar.setText("🧍 Capturar Postura")
    ventana.rafaga_pose_capturada.connect(al_capturar)
    ventana.show()
    return ventana


def avisar_no_vinculado(parent, usuario, metodo):
    """Mismo aviso para los 3 métodos: solo cambia Rostro / Voz / Postura."""
    con_articulo, titulo, genero = _METODOS[metodo]
    Mensajes.advertencia(
        parent,
        titulo,
        f"El usuario '{usuario}' no tiene {con_articulo} vinculad{genero}.\n\n"
        f"Use '🔗 Vincular mi Biometría (cuenta existente)' para vincularl{genero} a su cuenta."
    )


def capturar_voz(parent, segundos=2.0, muestras=MUESTRAS_REGISTRO_VOZ):
    """
    Graba varias muestras de la palabra clave del usuario. Todas deben reconocerse como la
    misma persona entrenada con confianza suficiente.
    Devuelve (etiqueta, vector, confianza) o None si se canceló o falló (ya se avisó al usuario).
    """
    from utils.reconocimiento_voz import ReconocedorVoz
    from interfaces.dialogo_voz import DialogoVoz

    if not ReconocedorVoz.cargar_modelo():
        Mensajes.error(parent, "Modelo No Disponible",
                       f"No se pudo cargar el modelo de voz:\n{ReconocedorVoz._error_carga}")
        return None

    palabras = " · ".join(ReconocedorVoz.etiquetas_validas())
    clase, vectores, confianzas = None, [], []
    for i in range(1, muestras + 1):
        audio = DialogoVoz.obtener_audio(
            parent, palabras if clase is None else clase, segundos,
            f"🎤 Registro de Voz ({i}/{muestras})",
            "Pulse 'Grabar' y diga su palabra clave, cerca del micrófono. Palabras entrenadas:"
            if clase is None else f"Muestra {i} de {muestras}. Repita la misma palabra clave:"
        )
        if audio is None:
            return None

        ok, clase_muestra, confianza, vector, mensaje = ReconocedorVoz.evaluar_muestra_registro(
            audio, clase_previa=clase
        )
        if not ok:
            Mensajes.advertencia(parent, "Registro de Voz Fallido", f"Muestra {i} de {muestras}: {mensaje}")
            return None

        clase = clase_muestra
        vectores.append(vector)
        confianzas.append(confianza)

    return clase, ReconocedorVoz.promediar_vectores(vectores), float(np.mean(confianzas))


def capturar_pose(parent, al_terminar):
    """
    Abre la cámara en modo postura y, al completar la ráfaga, valida la captura.
    Llama a al_terminar((etiqueta, vector, confianza)) si es válida; si falla, avisa y no llama.
    Devuelve la ventana de cámara (el llamador debe conservar la referencia) o None.
    """
    from utils.reconocimiento_pose import ReconocedorPose

    if not ReconocedorPose.cargar_modelo():
        Mensajes.error(parent, "Modelo No Disponible",
                       f"No se pudo cargar el modelo de postura:\n{ReconocedorPose._error_carga}")
        return None

    def procesar(frames):
        ok, clase, confianza, vector, mensaje = ReconocedorPose.registrar_pose(frames, UMBRAL_CONFIANZA_REGISTRO_POSE)
        if not ok:
            Mensajes.advertencia(parent, "Registro de Postura Fallido", mensaje)
            return
        al_terminar((clase, vector, confianza))

    return abrir_camara_pose(
        parent, "🧍 Registro de Postura", "Haga la postura que usará para iniciar sesión", procesar
    )
