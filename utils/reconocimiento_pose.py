import os
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

try:
    import cv2
except ImportError:
    cv2 = None

from utils.rutas import ruta_recurso
from utils.modelos_tfjs import aplicar_densas, capas_densas, leer_modelo_tfjs, leer_metadata, resolver_etiqueta
from utils.umbrales_biometria import UMBRAL_SIMILITUD_POSTURA


class ReconocedorPose:
    """
    Clasificación de poses con el modelo de Teachable Machine (@teachablemachine/pose).

    El clasificador de TM no recibe keypoints: recibe las salidas crudas de PoseNet
    MobileNetV1 (multiplier 0.75, outputStride 16, inputResolution 257), es decir
    sigmoid(heatmaps) [17x17x17] concatenado por canal con offsets [17x17x34] y
    aplanado -> vector de 14739 valores. Por eso se ejecuta el mismo PoseNet (en ONNX,
    models/posenet/posenet_075_stride16.onnx, compartido con services.modelos_tm) y no MediaPipe.
    """
    DIRECTORIO_MODELO = os.path.join("models", "my-pose-model")

    RESOLUCION = 257
    # La webcam de Teachable Machine muestra (y entrena) la imagen espejada
    VOLTEAR_HORIZONTAL = True

    CLASES_DESCARTADAS = {"otros", "fondo", "oscuro", "fondo oscuro"}

    PASO_SALIDA = 16  # outputStride de PoseNet: píxeles por celda de los heatmaps
    PUNTUACION_MINIMA_KEYPOINT = 0.3
    KEYPOINTS_MINIMOS = 5
    # Similitud mínima con la postura registrada. Valor inicial sin calibrar:
    # revisar los valores "[PoseAuth] Similitud" del log con capturas reales.
    UMBRAL_SIMILITUD = UMBRAL_SIMILITUD_POSTURA  # definido en utils/umbrales_biometria.py

    _posenet = None
    _pesos = None
    _etiquetas = []
    _error_carga = None

    # =====================================================
    # CARGA DE MODELOS
    # =====================================================

    @classmethod
    def cargar_modelo(cls):
        if cls._posenet is not None:
            return True

        if cv2 is None:
            cls._error_carga = "OpenCV no está instalado."
            return False

        try:
            from services.modelos_tm import ModeloPosturaTM

            directorio = ruta_recurso(cls.DIRECTORIO_MODELO)
            cls._etiquetas = [e.strip() for e in leer_metadata(directorio)["labels"]]
            topologia, pesos = leer_modelo_tfjs(directorio)
            # Cabeza de TM: Dense(100, relu) -> Dropout -> Dense(clases, softmax, sin bias)
            cls._pesos = capas_densas(topologia, pesos)

            if not ModeloPosturaTM.cargar():
                raise RuntimeError(ModeloPosturaTM.error_carga())
            cls._posenet = ModeloPosturaTM._sesion
            cls._error_carga = None
            print(f"[PoseAuth] PoseNet y clasificador de pose cargados con etiquetas: {cls._etiquetas}")
            return True

        except Exception as e:
            cls._posenet = None
            cls._error_carga = str(e)
            print(f"[PoseAuth] Error al cargar el modelo de pose: {e}")
            return False

    @classmethod
    def etiquetas_validas(cls):
        return [e for e in cls._etiquetas if e.lower() not in cls.CLASES_DESCARTADAS]

    # =====================================================
    # PREPROCESAMIENTO (equivalente a @teachablemachine/pose + PoseNet 2.x)
    # =====================================================

    @classmethod
    def preprocesar(cls, frame_bgr):
        """Recorte cuadrado centrado, espejo, RGB y escalado a 257x257 (bilineal de TF.js) en [-1, 1]."""
        from services.modelos_tm import ModeloPosturaTM
        return ModeloPosturaTM.preprocesar(frame_bgr)[np.newaxis].astype(np.float32)

    @classmethod
    def _salidas_posenet(cls, frame_bgr):
        """Devuelve (vector de 14739 valores para el clasificador de TM, keypoints [17, 3])."""
        nombres = [s.name for s in cls._posenet.get_outputs()]
        salida = dict(zip(nombres, cls._posenet.run(
            None, {cls._posenet.get_inputs()[0].name: cls.preprocesar(frame_bgr)})))
        heatmaps = next(v for n, v in salida.items() if "heatmap" in n)[0]
        heatmaps = 1.0 / (1.0 + np.exp(-heatmaps))
        offsets = next(v for n, v in salida.items() if "offsets" in n)[0]
        caracteristicas = np.concatenate([heatmaps, offsets], axis=2).reshape(-1)
        return caracteristicas, cls._keypoints(heatmaps, offsets)

    @classmethod
    def extraer_caracteristicas(cls, frame_bgr):
        """Devuelve el vector de 14739 valores que espera el clasificador de TM."""
        return cls._salidas_posenet(frame_bgr)[0]

    @classmethod
    def _keypoints(cls, heatmaps, offsets):
        """
        Decodifica los 17 puntos clave de PoseNet (igual que decodeSinglePose):
        celda de mayor puntuación de cada heatmap + offset, en píxeles de la imagen de 257x257.
        Devuelve un array [17, 3] con (y, x, puntuación).
        """
        alto, ancho, partes = heatmaps.shape
        celdas = heatmaps.reshape(-1, partes).argmax(axis=0)
        ys, xs = np.unravel_index(celdas, (alto, ancho))
        idx = np.arange(partes)
        puntuacion = heatmaps[ys, xs, idx]
        y = ys * cls.PASO_SALIDA + offsets[ys, xs, idx]
        x = xs * cls.PASO_SALIDA + offsets[ys, xs, idx + partes]
        return np.stack([y, x, puntuacion], axis=1).astype(np.float32)

    # =====================================================
    # INFERENCIA
    # =====================================================

    @classmethod
    def _analizar_frame(cls, frame_bgr):
        """Devuelve (probabilidades de TM, keypoints) de un frame."""
        caracteristicas, keypoints = cls._salidas_posenet(frame_bgr)
        return aplicar_densas(caracteristicas[np.newaxis], cls._pesos)[0], keypoints

    @classmethod
    def predecir(cls, frame_bgr):
        """Clasifica un frame BGR de OpenCV. Devuelve (clase, confianza, distribucion)."""
        if not cls.cargar_modelo() or frame_bgr is None:
            return None, 0.0, {}

        probs, _ = cls._analizar_frame(frame_bgr)
        indice = int(probs.argmax())
        clase = cls._etiquetas[indice]
        confianza = float(probs[indice])
        distribucion = {e: round(float(p), 3) for e, p in zip(cls._etiquetas, probs)}
        print(f"[PoseAuth] Inferencia -> Clase: '{clase}' ({confianza * 100:.1f}%), Distribución: {distribucion}")
        return clase, confianza, distribucion

    @classmethod
    def analizar_rafaga(cls, frames):
        """
        Clasifica varios frames por voto mayoritario. Devuelve (clase, confianza media de esa
        clase, votos, vector), donde vector son los keypoints promedio de los frames que
        votaron por la clase ganadora (lista de 51 valores y, x, puntuación).
        """
        if not cls.cargar_modelo():
            return None, 0.0, {}, None

        votos = {}
        for frame in frames:
            if frame is None:
                continue
            probs, keypoints = cls._analizar_frame(frame)
            indice = int(probs.argmax())
            votos.setdefault(cls._etiquetas[indice], []).append((float(probs[indice]), keypoints))

        if not votos:
            return None, 0.0, {}, None

        clase = max(votos, key=lambda c: (len(votos[c]), np.mean([conf for conf, _ in votos[c]])))
        confianza = float(np.mean([conf for conf, _ in votos[clase]]))
        promedio = np.mean([kp for _, kp in votos[clase]], axis=0)
        vector = [round(float(v), 4) for v in promedio.reshape(-1)]
        conteo = {c: len(v) for c, v in votos.items()}
        print(f"[PoseAuth] Ráfaga -> Clase: '{clase}' ({confianza * 100:.1f}%), Votos: {conteo}")
        return clase, confianza, conteo, vector

    @classmethod
    def predecir_rafaga(cls, frames):
        """Clasifica varios frames y devuelve (clase mayoritaria, confianza media de esa clase, votos)."""
        return cls.analizar_rafaga(frames)[:3]

    @classmethod
    def capturar_y_predecir(cls, indice_camara=0, num_frames=10):
        """Abre la cámara con OpenCV, captura una ráfaga de frames y la clasifica."""
        if cv2 is None:
            return None, 0.0, {}

        captura = cv2.VideoCapture(indice_camara)
        frames = []
        try:
            for _ in range(num_frames):
                ok, frame = captura.read()
                if ok:
                    frames.append(frame)
        finally:
            captura.release()

        return cls.predecir_rafaga(frames)

    @classmethod
    def similitud(cls, vector_a, vector_b):
        """
        Parecido entre dos posturas (0 a 1) a partir de sus keypoints. Solo usa los puntos
        visibles en ambas, elimina posición y escala (centrado + normalización RMS) y
        convierte la distancia media en similitud: 1 = misma postura.
        """
        a = np.asarray(vector_a, dtype=np.float32).reshape(-1, 3)
        b = np.asarray(vector_b, dtype=np.float32).reshape(-1, 3)
        if a.shape != b.shape:
            return 0.0

        peso = np.minimum(a[:, 2], b[:, 2])
        visibles = peso >= cls.PUNTUACION_MINIMA_KEYPOINT
        if visibles.sum() < cls.KEYPOINTS_MINIMOS:
            return 0.0

        def normalizar(puntos):
            centrados = puntos - puntos.mean(axis=0)
            escala = np.sqrt((centrados ** 2).sum(axis=1).mean())
            return centrados / escala if escala > 0 else centrados

        pa, pb = normalizar(a[visibles, :2]), normalizar(b[visibles, :2])
        distancia = float(np.average(np.linalg.norm(pa - pb, axis=1), weights=peso[visibles]))
        return float(np.clip(1.0 - distancia, 0.0, 1.0))

    @classmethod
    def clase_vinculada(cls, etiqueta_vinculada):
        """Devuelve la etiqueta de postura guardada si sigue existiendo en el modelo, o None."""
        if not etiqueta_vinculada or not cls.cargar_modelo():
            return None
        return resolver_etiqueta(cls.etiquetas_validas(), etiqueta_vinculada)

    # =====================================================
    # REGISTRO Y VERIFICACIÓN
    # =====================================================

    @classmethod
    def _mensaje_clase_descartada(cls, clase):
        if clase.lower() == "oscuro":
            return "⚠️ La imagen está muy oscura. Mejore la iluminación."
        return "⚠️ No se reconoció ninguna postura registrada. Colóquese de cuerpo completo frente a la cámara."

    @classmethod
    def registrar_pose(cls, frames, umbral_confianza=0.80):
        """
        Valida una ráfaga de registro: debe reconocerse a una persona entrenada con confianza
        suficiente y con suficientes puntos del cuerpo visibles.
        Devuelve (ok, clase, confianza, vector, mensaje).
        """
        clase, confianza, _, vector = cls.analizar_rafaga(frames)
        if clase is None:
            return False, None, 0.0, None, "No se pudieron analizar los fotogramas capturados."
        if clase.lower() in cls.CLASES_DESCARTADAS:
            return False, clase, confianza, None, (
                cls._mensaje_clase_descartada(clase) +
                f"\nPosturas reconocidas por el modelo: {', '.join(cls.etiquetas_validas())}."
            )
        if confianza < umbral_confianza:
            return False, clase, confianza, None, (
                f"⚠️ Confianza insuficiente ({confianza * 100:.1f}% < {umbral_confianza * 100:.0f}%). Intente de nuevo."
            )
        visibles = int((np.asarray(vector).reshape(-1, 3)[:, 2] >= cls.PUNTUACION_MINIMA_KEYPOINT).sum())
        if visibles < cls.KEYPOINTS_MINIMOS:
            return False, clase, confianza, None, (
                f"⚠️ Solo se ven {visibles} puntos del cuerpo. Aléjese de la cámara para que se vea su torso completo."
            )
        return True, clase, confianza, vector, f"Postura registrada como '{clase}' ({confianza * 100:.1f}%)."

    @classmethod
    def verificar_pose(cls, frames, clase_esperada, umbral_confianza=0.80,
                       vector_referencia=None, umbral_similitud=None):
        """
        Comprueba que la ráfaga muestra la postura esperada y, si hay vector de referencia,
        que se parece a la postura registrada. Devuelve (ok, clase, confianza, mensaje).
        """
        clase, confianza, _, vector = cls.analizar_rafaga(frames)
        if clase is None:
            return False, None, 0.0, "No se pudieron analizar los fotogramas capturados."

        if clase.lower() != clase_esperada.lower():
            if clase.lower() in cls.CLASES_DESCARTADAS:
                return False, clase, confianza, cls._mensaje_clase_descartada(clase)
            return False, clase, confianza, f"⚠️ La postura detectada ('{clase}') no coincide con el usuario."

        if confianza < umbral_confianza:
            return False, clase, confianza, (
                f"⚠️ Confianza insuficiente ({confianza * 100:.1f}% < {umbral_confianza * 100:.0f}%). Intente de nuevo."
            )

        if vector_referencia is not None:
            umbral_similitud = cls.UMBRAL_SIMILITUD if umbral_similitud is None else umbral_similitud
            sim = cls.similitud(vector, vector_referencia)
            print(f"[PoseAuth] Similitud con la postura registrada: {sim:.3f} (umbral={umbral_similitud})")
            if sim < umbral_similitud:
                return False, clase, confianza, (
                    f"⚠️ La postura no se parece a la registrada ({sim * 100:.1f}% < {umbral_similitud * 100:.0f}%). "
                    f"Repita la misma postura que usó al vincularla."
                )

        return True, clase, confianza, f"Postura verificada como '{clase}' ({confianza * 100:.1f}%)."


if __name__ == "__main__":
    print(ReconocedorPose.capturar_y_predecir())
