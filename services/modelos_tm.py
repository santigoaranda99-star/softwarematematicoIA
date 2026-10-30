"""
Modelos de Teachable Machine para el ingreso rápido: rostro (imagen) y voz (audio).

- Rostro: export "TensorFlow → Keras" (keras_model.h5) convertido a ONNX con
  tools/convertir_modelos_tm.py → models/tm_rostro/modelo.onnx
- Voz:    export "TensorFlow Lite" (soundclassifier_with_metadata.tflite), ejecutado con LiteRT.
  Trae el preprocesamiento dentro (FFT): recibe la onda cruda de 44032 muestras a 44,1 kHz
  (~1 s) y devuelve la probabilidad de cada clase. No se pasa a ONNX porque tf2onnx no
  soporta su RFFT; si algún día existe models/tm_voz/modelo.onnx, se usará ese.

Si hay modelo.onnx se usa onnxruntime; si no, el .tflite. Las sesiones se cargan una sola vez.
"""
import os
import threading

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from utils.rutas import ruta_recurso


def leer_etiquetas(ruta):
    """labels.txt de Teachable Machine ("0 clase" por línea) → lista de clases."""
    etiquetas = []
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                partes = linea.split(" ", 1)
                etiquetas.append(partes[1] if len(partes) == 2 and partes[0].isdigit() else linea)
    return etiquetas


class _Sesion:
    """Envoltura mínima sobre onnxruntime o el intérprete de TFLite: predecir(lote) → salida."""

    def __init__(self, directorio, nombre_tflite=None):
        ruta_onnx = os.path.join(directorio, "modelo.onnx")
        if os.path.exists(ruta_onnx):
            import onnxruntime as ort
            opciones = ort.SessionOptions()
            opciones.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._ort = ort.InferenceSession(ruta_onnx, opciones, providers=["CPUExecutionProvider"])
            self._entrada = self._ort.get_inputs()[0].name
            self.motor = "onnxruntime"
            return

        ruta_tflite = os.path.join(directorio, nombre_tflite or "modelo.tflite")
        if not os.path.exists(ruta_tflite):
            raise FileNotFoundError(f"No se encontró el modelo en {directorio}")
        try:
            from ai_edge_litert.interpreter import Interpreter
        except ImportError:
            from tensorflow.lite import Interpreter
        self._tfl = Interpreter(model_path=ruta_tflite)
        self._tfl.allocate_tensors()
        self._ent = self._tfl.get_input_details()[0]
        self._sal = self._tfl.get_output_details()[0]
        self._lock = threading.Lock()
        self.motor = "tflite"

    def predecir(self, lote):
        lote = np.asarray(lote, dtype=np.float32)
        if self.motor == "onnxruntime":
            return self._ort.run(None, {self._entrada: lote})[0]
        salidas = []
        with self._lock:  # el intérprete de TFLite no es seguro entre hilos
            for muestra in lote:
                self._tfl.set_tensor(self._ent["index"], muestra[None, ...])
                self._tfl.invoke()
                salidas.append(self._tfl.get_tensor(self._sal["index"])[0])
        return np.stack(salidas)


class _ModeloTM:
    DIRECTORIO = ""
    NOMBRE_TFLITE = None
    CLASES_SUPLANTACION = set()
    CLASES_SIN_PERSONA = set()

    _sesion = None
    _etiquetas = []
    _error_carga = None
    _lock_carga = threading.Lock()

    @classmethod
    def cargar(cls):
        """Carga el modelo una sola vez. Devuelve True si está listo."""
        if cls._sesion is not None:
            return True
        with cls._lock_carga:
            if cls._sesion is not None:
                return True
            try:
                directorio = ruta_recurso(cls.DIRECTORIO)
                cls._etiquetas = leer_etiquetas(os.path.join(directorio, "labels.txt"))
                cls._sesion = _Sesion(directorio, cls.NOMBRE_TFLITE)
                cls._error_carga = None
                print(f"[TM] {cls.__name__} cargado con {cls._sesion.motor}: {cls._etiquetas}")
            except Exception as error:
                cls._error_carga = str(error)
                print(f"[TM] ❌ No se pudo cargar {cls.__name__}: {error}")
                return False
        return True

    @classmethod
    def etiquetas(cls):
        return list(cls._etiquetas)

    @classmethod
    def clases_persona(cls):
        """Clases que representan a una persona (no fondo, ruido ni suplantación)."""
        excluidas = {c.lower() for c in cls.CLASES_SUPLANTACION | cls.CLASES_SIN_PERSONA}
        return [e for e in cls._etiquetas if e.lower() not in excluidas]

    @classmethod
    def error_carga(cls):
        return cls._error_carga


class ModeloRostroTM(_ModeloTM):
    """Clasificador de imagen (MobileNet 224x224) entrenado con las caras de cada usuario."""

    DIRECTORIO = os.path.join("models", "tm_rostro")
    TAMANO = 224
    CLASES_SUPLANTACION = {"movil"}
    CLASES_SIN_PERSONA = {"otros", "oscuro", "fondo", "fondo oscuro"}

    @classmethod
    def preprocesar(cls, frame_bgr):
        """Igual que Teachable Machine: recorte cuadrado central, 224x224, RGB, [-1, 1]."""
        alto, ancho = frame_bgr.shape[:2]
        lado = min(alto, ancho)
        y0, x0 = (alto - lado) // 2, (ancho - lado) // 2
        recorte = frame_bgr[y0:y0 + lado, x0:x0 + lado]
        recorte = cv2.resize(recorte, (cls.TAMANO, cls.TAMANO), interpolation=cv2.INTER_AREA)
        recorte = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB).astype(np.float32)
        return recorte / 127.5 - 1.0

    @classmethod
    def predecir(cls, frames_bgr):
        """Lista de cuadros BGR → matriz (n, clases) de probabilidades."""
        if not cls.cargar():
            raise RuntimeError(cls._error_carga)
        lote = np.stack([cls.preprocesar(f) for f in frames_bgr])
        return cls._sesion.predecir(lote)


def _redimensionar_tfjs(imagen, tamano):
    """
    Bilineal como resizeBilinear de TF.js 1.7 (align_corners=False, sin half-pixel centers),
    que es como Teachable Machine preparó la imagen al entrenar la postura.
    """
    alto, ancho = imagen.shape[:2]

    def ejes(n_entrada):
        origen = np.arange(tamano, dtype=np.float32) * (n_entrada / tamano)
        i0 = np.floor(origen).astype(int)
        return i0, np.minimum(i0 + 1, n_entrada - 1), (origen - i0)

    y0, y1, fy = ejes(alto)
    x0, x1, fx = ejes(ancho)
    fx = fx[None, :, None]
    arriba = imagen[y0][:, x0] * (1 - fx) + imagen[y0][:, x1] * fx
    abajo = imagen[y1][:, x0] * (1 - fx) + imagen[y1][:, x1] * fx
    return arriba * (1 - fy[:, None, None]) + abajo * fy[:, None, None]


class ModeloPosturaTM(_ModeloTM):
    """
    Postura de Teachable Machine (solo exporta TF.js): PoseNet MobileNetV1 0.75 en ONNX
    (models/posenet/posenet_075_stride16.onnx) + la cabeza Dense de models/my-pose-model
    ejecutada con NumPy. La entrada de la cabeza son 14739 valores: sigmoid(heatmaps)
    [17x17x17] concatenado con offsets [17x17x34], igual que @teachablemachine/pose.
    """

    DIRECTORIO = os.path.join("models", "my-pose-model")
    RUTA_POSENET = os.path.join("models", "posenet", "posenet_075_stride16.onnx")
    RESOLUCION = 257
    PASO = 16
    PUNTO_VISIBLE = 0.3
    CLASES_SIN_PERSONA = {"otros", "fondo", "oscuro", "fondo oscuro"}

    _densas = None

    @classmethod
    def cargar(cls):
        if cls._sesion is not None:
            return True
        with cls._lock_carga:
            if cls._sesion is not None:
                return True
            try:
                import onnxruntime as ort
                from utils.modelos_tfjs import capas_densas, leer_metadata, leer_modelo_tfjs

                directorio = ruta_recurso(cls.DIRECTORIO)
                etiquetas = [e.strip() for e in leer_metadata(directorio)["labels"]]
                cls._densas = capas_densas(*leer_modelo_tfjs(directorio))
                cls._etiquetas = etiquetas
                cls._sesion = ort.InferenceSession(ruta_recurso(cls.RUTA_POSENET),
                                                   providers=["CPUExecutionProvider"])
                cls._error_carga = None
                print(f"[TM] ModeloPosturaTM cargado con onnxruntime: {etiquetas}")
            except Exception as error:
                cls._sesion = None
                cls._error_carga = str(error)
                print(f"[TM] ❌ No se pudo cargar ModeloPosturaTM: {error}")
                return False
        return True

    @classmethod
    def preprocesar(cls, frame_bgr):
        """Recorte cuadrado central, espejo (la webcam de TM entrena espejada), RGB, 257x257, [-1, 1]."""
        alto, ancho = frame_bgr.shape[:2]
        lado = min(alto, ancho)
        y0, x0 = (alto - lado) // 2, (ancho - lado) // 2
        recorte = cv2.flip(frame_bgr[y0:y0 + lado, x0:x0 + lado], 1)
        rgb = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB).astype(np.float32)
        return _redimensionar_tfjs(rgb, cls.RESOLUCION) / 127.5 - 1.0

    # Conexiones del esqueleto de PoseNet (como el dibujo de Teachable Machine)
    ESQUELETO = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12),
                 (11, 13), (13, 15), (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4)]

    @classmethod
    def puntos_en_imagen(cls, puntos, ancho, alto):
        """
        Puntos [17, 3] (y, x, puntuación en el recorte espejado de 257x257) → coordenadas sobre
        la vista espejada de la cámara de ancho x alto, para dibujarlos.
        """
        lado = min(alto, ancho)
        y0, x0 = (alto - lado) // 2, (ancho - lado) // 2
        escala = lado / cls.RESOLUCION
        return [(int(x0 + x * escala), int(y0 + y * escala), float(p)) for y, x, p in puntos]

    @classmethod
    def predecir(cls, frame_bgr):
        """Un cuadro → (probabilidades por clase, puntos visibles, puntos [17, 3])."""
        from utils.modelos_tfjs import aplicar_densas

        if not cls.cargar():
            raise RuntimeError(cls._error_carga)
        entrada = cls.preprocesar(frame_bgr)[None].astype(np.float32)
        nombres = [s.name for s in cls._sesion.get_outputs()]
        salida = dict(zip(nombres, cls._sesion.run(None, {cls._sesion.get_inputs()[0].name: entrada})))
        heatmap = next(v for n, v in salida.items() if "heatmap" in n)[0]
        offsets = next(v for n, v in salida.items() if "offsets" in n)[0]
        heatmap = 1.0 / (1.0 + np.exp(-heatmap))
        caracteristicas = np.concatenate([heatmap, offsets], axis=2).reshape(1, -1)

        # Puntos clave igual que decodeSinglePose: celda de mayor puntuación + offset
        alto, ancho, partes = heatmap.shape
        celdas = heatmap.reshape(-1, partes).argmax(axis=0)
        ys, xs = np.unravel_index(celdas, (alto, ancho))
        idx = np.arange(partes)
        puntuacion = heatmap[ys, xs, idx]
        puntos = np.stack([ys * cls.PASO + offsets[ys, xs, idx],
                           xs * cls.PASO + offsets[ys, xs, idx + partes], puntuacion], axis=1)
        visibles = int((puntuacion >= cls.PUNTO_VISIBLE).sum())
        return aplicar_densas(caracteristicas, cls._densas)[0], visibles, puntos.astype(np.float32)


class ModeloVozTM(_ModeloTM):
    """Clasificador de audio de Teachable Machine (onda cruda de 1 s a 44,1 kHz)."""

    DIRECTORIO = os.path.join("models", "tm_voz")
    NOMBRE_TFLITE = "soundclassifier_with_metadata.tflite"
    FRECUENCIA = 44100
    MUESTRAS = 44032
    SALTO = 11025                     # una ventana cada 0,25 s
    RMS_SILENCIO = 0.004              # ventanas más bajas que esto no se evalúan
    CLASES_SUPLANTACION = {"audio-tel"}
    CLASES_SIN_PERSONA = {"ruido de fondo", "otros"}

    @classmethod
    def ventanas(cls, audio, frecuencia):
        """Audio mono → ventanas de 1 s (remuestreado a 44,1 kHz) que no son silencio."""
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if frecuencia != cls.FRECUENCIA and len(audio):
            n = int(round(len(audio) * cls.FRECUENCIA / frecuencia))
            audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)
        if len(audio) < cls.MUESTRAS:
            audio = np.pad(audio, (0, cls.MUESTRAS - len(audio)))
        ventanas = [audio[i:i + cls.MUESTRAS]
                    for i in range(0, len(audio) - cls.MUESTRAS + 1, cls.SALTO)]
        return [v for v in ventanas if float(np.sqrt(np.mean(v ** 2))) >= cls.RMS_SILENCIO]

    @classmethod
    def predecir(cls, audio, frecuencia):
        """Audio → matriz (n_ventanas, clases). Vacía si todo fue silencio."""
        if not cls.cargar():
            raise RuntimeError(cls._error_carga)
        ventanas = cls.ventanas(audio, frecuencia)
        if not ventanas:
            return np.zeros((0, len(cls._etiquetas)), np.float32)
        return cls._sesion.predecir(np.stack(ventanas))
