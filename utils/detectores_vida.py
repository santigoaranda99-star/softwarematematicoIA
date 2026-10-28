"""
Detectores para la prueba de vida (liveness) del rostro, ejecutados con cv2.dnn (sin
onnxruntime ni MediaPipe):

- Malla facial MediaPipe Face Mesh V2 (478 puntos) para medir parpadeo (EAR), giro de la
  cabeza (yaw), sonrisa y boca abierta.
- MiniFASNetV2 (Silent-Face-Anti-Spoofing) para distinguir un rostro real de una foto o
  una pantalla.
- Heurísticas de pantalla: moiré (picos de alta frecuencia) y reflejos especulares.

Las funciones son puras y seguras para ejecutarse en un hilo (las redes se usan con un lock).
"""
import os
import threading

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from utils.rutas import ruta_recurso

_DIRECTORIO = os.path.join("models", "liveness")

# Índices de la topología de MediaPipe Face Mesh
_OJO_DER = (33, 160, 158, 133, 153, 144)   # ojo derecho de la persona (p1..p6)
_OJO_IZQ = (362, 385, 387, 263, 373, 380)  # ojo izquierdo de la persona
_BOCA_ARRIBA, _BOCA_ABAJO = 13, 14
_COMISURA_DER, _COMISURA_IZQ = 61, 291
_NARIZ = 1
_MEJILLA_DER, _MEJILLA_IZQ = 234, 454

_malla = None
_antispoof = None
# Las redes de OpenCV no son reentrantes: un único lock para todas
_lock = threading.Lock()
_error_carga = None


def cargar_modelos():
    """Carga la malla facial y el anti-spoofing. Devuelve True si ambos están disponibles."""
    global _malla, _antispoof, _error_carga
    if _malla is not None and _antispoof is not None:
        return True
    if cv2 is None:
        _error_carga = "OpenCV no está instalado."
        return False
    try:
        if _malla is None:
            _malla = cv2.dnn.readNetFromONNX(ruta_recurso(os.path.join(_DIRECTORIO, "face_landmarks.onnx")))
        if _antispoof is None:
            _antispoof = cv2.dnn.readNetFromONNX(ruta_recurso(os.path.join(_DIRECTORIO, "antispoof_minifasv2.onnx")))
        _error_carga = None
        return True
    except Exception as error:
        _error_carga = f"No se pudieron cargar los modelos de liveness ({_DIRECTORIO}): {error}"
        print(f"[Liveness] {_error_carga}")
        return False


def error_carga():
    return _error_carga


# =====================================================
# DETECCIÓN DE ROSTROS (YuNet, ya incluido en el proyecto)
# =====================================================

def detectar_rostros(frame):
    """Devuelve el array de rostros de YuNet [n, 15] (bbox, 5 puntos, score) o un array vacío."""
    from services.clasificador_imagen import ClasificadorImagen

    if not ClasificadorImagen.cargar_detector_facial():
        return np.zeros((0, 15), dtype=np.float32)
    alto, ancho = frame.shape[:2]
    with _lock:
        ClasificadorImagen._detector_rostros.setInputSize((ancho, alto))
        _, rostros = ClasificadorImagen._detector_rostros.detect(frame)
    return rostros if rostros is not None else np.zeros((0, 15), dtype=np.float32)


def embedding_rostro(frame, rostro):
    """Vector SFace (128) del rostro detectado por YuNet."""
    from services.clasificador_imagen import ClasificadorImagen

    if not ClasificadorImagen.cargar_reconocedor_facial():
        return None
    with _lock:
        alineada = ClasificadorImagen._reconocedor_sface.alignCrop(frame, rostro)
        return ClasificadorImagen._reconocedor_sface.feature(alineada)[0].tolist()


# =====================================================
# MALLA FACIAL Y MÉTRICAS
# =====================================================

def puntos_malla(frame, rostro):
    """
    Ejecuta Face Mesh V2 sobre el recorte rotado del rostro (como MediaPipe: centro del bbox,
    lado 1.5 x el mayor lado, rotación según los ojos). Devuelve [478, 3] en píxeles del frame.
    """
    x, y, w, h = [float(v) for v in rostro[:4]]
    ojo_der = np.array(rostro[4:6], dtype=np.float64)   # YuNet: ojo derecho de la persona
    ojo_izq = np.array(rostro[6:8], dtype=np.float64)
    angulo = np.degrees(np.arctan2(ojo_izq[1] - ojo_der[1], ojo_izq[0] - ojo_der[0]))
    centro = (x + w / 2.0, y + h / 2.0)
    lado = max(w, h) * 1.5

    escala = 256.0 / lado
    matriz = cv2.getRotationMatrix2D(centro, angulo, escala)
    matriz[0, 2] += 128.0 - centro[0]
    matriz[1, 2] += 128.0 - centro[1]
    recorte = cv2.warpAffine(frame, matriz, (256, 256), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    entrada = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB).astype(np.float32)[np.newaxis] / 255.0

    with _lock:
        _malla.setInput(entrada)
        salida = _malla.forward(_malla.getUnconnectedOutLayersNames())[0]
    puntos = salida.reshape(-1, 3)[:478]

    inversa = cv2.invertAffineTransform(matriz)
    xy = puntos[:, :2] @ inversa[:, :2].T + inversa[:, 2]
    return np.column_stack([xy, puntos[:, 2] / escala]).astype(np.float32)


def _dist(a, b):
    return float(np.linalg.norm(a[:2] - b[:2]))


def _ear(p, indices):
    p1, p2, p3, p4, p5, p6 = (p[i] for i in indices)
    return (_dist(p2, p6) + _dist(p3, p5)) / (2.0 * _dist(p1, p4) + 1e-6)


def metricas_rostro(puntos):
    """
    Medidas geométricas de la malla:
    - ear: apertura media de los ojos (baja al parpadear).
    - giro: posición horizontal de la nariz entre las mejillas (0.5 = de frente; sube cuando la
      persona gira hacia SU izquierda en la imagen sin espejar).
    - sonrisa: ancho de la boca / ancho de la cara.
    - boca: apertura vertical / ancho de la boca (MAR).
    """
    izquierda, derecha = puntos[_MEJILLA_DER, 0], puntos[_MEJILLA_IZQ, 0]
    ancho_cara = abs(derecha - izquierda) + 1e-6
    ancho_boca = _dist(puntos[_COMISURA_DER], puntos[_COMISURA_IZQ]) + 1e-6
    return {
        "ear": (_ear(puntos, _OJO_DER) + _ear(puntos, _OJO_IZQ)) / 2.0,
        "giro": float((puntos[_NARIZ, 0] - min(izquierda, derecha)) / ancho_cara),
        "sonrisa": ancho_boca / ancho_cara,
        "boca": _dist(puntos[_BOCA_ARRIBA], puntos[_BOCA_ABAJO]) / ancho_boca,
    }


# =====================================================
# ANTI-SPOOFING (MiniFASNetV2) Y HEURÍSTICAS DE PANTALLA
# =====================================================

def _recorte_cuadrado(frame, rostro, factor):
    """Recorte cuadrado centrado en el rostro, ampliado 'factor' veces, con bordes reflejados."""
    x, y, w, h = [float(v) for v in rostro[:4]]
    lado = int(max(w, h) * factor)
    x0, y0 = int(x + w / 2 - lado / 2), int(y + h / 2 - lado / 2)
    alto, ancho = frame.shape[:2]
    recorte = frame[max(0, y0):min(alto, y0 + lado), max(0, x0):min(ancho, x0 + lado)]
    if recorte.size == 0:
        return None
    return cv2.copyMakeBorder(
        recorte, max(0, -y0), max(0, y0 + lado - alto), max(0, -x0), max(0, x0 + lado - ancho),
        cv2.BORDER_REFLECT_101
    )


def puntuacion_real(frame, rostro):
    """
    Diferencia de logits real - falso de MiniFASNetV2 (> 0 = parece real). Mismo
    preprocesamiento que el proyecto original: RGB, recorte x1.5, 128x128, [0, 1].
    """
    recorte = _recorte_cuadrado(frame, rostro, 1.5)
    if recorte is None:
        return -10.0
    rgb = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB)
    interpolacion = cv2.INTER_LANCZOS4 if rgb.shape[0] < 128 else cv2.INTER_AREA
    entrada = cv2.resize(rgb, (128, 128), interpolation=interpolacion)
    entrada = entrada.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
    with _lock:
        _antispoof.setInput(entrada)
        logits = _antispoof.forward()[0]
    return float(logits[0] - logits[1])


def calidad_rostro(frame, rostro):
    """
    Calidad del cuadro para evaluar el anti-spoofing y avisar al usuario:
    - brillo: luminosidad media del rostro (0-255).
    - nitidez: varianza del laplaciano del rostro a 128x128 (baja = borroso o movido).
    - tamano: ancho del rostro / ancho de la imagen (bajo = demasiado lejos).
    - contraluz: brillo del fondo menos el del rostro (alto = luz fuerte detrás).
    """
    recorte = _recorte_cuadrado(frame, rostro, 1.0)
    if recorte is None:
        return {"brillo": 0.0, "nitidez": 0.0, "tamano": 0.0, "contraluz": 0.0}
    gris_rostro = cv2.cvtColor(cv2.resize(recorte, (128, 128)), cv2.COLOR_BGR2GRAY)
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    x, y, w, h = [int(v) for v in rostro[:4]]
    mascara = np.ones(gris.shape, dtype=bool)
    mascara[max(0, y):y + h, max(0, x):x + w] = False
    brillo = float(gris_rostro.mean())
    return {
        "brillo": brillo,
        "nitidez": float(cv2.Laplacian(gris_rostro, cv2.CV_64F).var()),
        "tamano": float(w) / frame.shape[1],
        "contraluz": float(gris[mascara].mean()) - brillo if mascara.any() else 0.0,
    }


def indicios_pantalla(frame, rostro):
    """
    Heurísticas de foto mostrada en una pantalla, sobre el recorte del rostro:
    - moire: energía de picos aislados en altas frecuencias del espectro (rejilla de píxeles).
    - reflejo: fracción de píxeles casi blancos y sin saturación de color (brillo del vidrio).
    Devuelve un dict con ambos valores (0 = sin indicios).
    """
    recorte = _recorte_cuadrado(frame, rostro, 1.0)
    if recorte is None or min(recorte.shape[:2]) < 48:
        return {"moire": 0.0, "reflejo": 0.0}

    gris = cv2.cvtColor(cv2.resize(recorte, (128, 128)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    espectro = np.abs(np.fft.fftshift(np.fft.fft2(gris - gris.mean())))
    espectro = np.log1p(espectro)
    yy, xx = np.mgrid[-64:64, -64:64]
    radio = np.sqrt(xx ** 2 + yy ** 2)
    alta = espectro[(radio > 28) & (radio < 62)]
    # Picos muy por encima del nivel típico de esa banda indican una rejilla periódica
    moire = float(np.mean(alta > alta.mean() + 4.0 * alta.std()))

    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
    reflejo = float(np.mean((hsv[..., 2] > 245) & (hsv[..., 1] < 30)))
    return {"moire": moire, "reflejo": reflejo}
