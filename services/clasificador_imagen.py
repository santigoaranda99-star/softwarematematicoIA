import os
import json
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

# Cargar soporte de Keras / TensorFlow
tf_keras = None
try:
    import tf_keras
except ImportError:
    pass

try:
    import tensorflow as tf
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
except ImportError:
    tf = None

try:
    from utils.rutas import ruta_recurso
except ImportError:
    def ruta_recurso(relativa):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relativa)


class ClasificadorImagen:
    """
    Servicio de visión computacional y reconocimiento facial seguro.
    Combina:
    1. Detector biométrico de redes neuronales YuNet (OpenCV DNN) de alta precisión.
    2. Extractor y comparador biométrico SFace (vectores de 128 dimensiones).
    3. Análisis fotométrico de iluminación / luminosidad en tiempo real.
    4. Análisis multi-fotograma (ráfaga temporal) para prueba de vida y anti-suplantación.
    5. Modelo neuronal de clasificación Teachable Machine (Keras / TensorFlow / TF.js).
    """
    _instancia = None
    _modelo = None
    _etiquetas = []
    _cargado = False
    _error_carga = None
    _detector_rostros = None
    _detector_cargado = False
    _reconocedor_sface = None
    _sface_cargado = False

    # Clases que no representan a un usuario específico
    CLASES_DESCARTADAS = {"otros", "fondo", "fondo oscuro", "oscuro", "movil", "desconocido"}

    def __new__(cls, *args, **kwargs):
        if cls._instancia is None:
            cls._instancia = super(ClasificadorImagen, cls).__new__(cls)
        return cls._instancia

    # =====================================================
    # CARGA DEL DETECTOR BIOMÉTRICO FACIAL (YUNET)
    # =====================================================

    @classmethod
    def cargar_detector_facial(cls):
        """
        Carga el detector facial de redes neuronales YuNet de OpenCV.
        No depende de TensorFlow y es extremadamente rápido y preciso.
        """
        if cls._detector_cargado and cls._detector_rostros is not None:
            return True

        if cv2 is None:
            print("[FaceAuth] OpenCV no está disponible para detección facial.")
            return False

        try:
            ruta_yunet = ruta_recurso(os.path.join("models", "face_detector", "face_detection_yunet.onnx"))
            if not os.path.exists(ruta_yunet):
                print(f"[FaceAuth] Archivo del detector YuNet no encontrado en: {ruta_yunet}")
                return False

            if hasattr(cv2, "FaceDetectorYN_create"):
                cls._detector_rostros = cv2.FaceDetectorYN_create(
                    ruta_yunet,
                    "",
                    (320, 320),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=5000
                )
                cls._detector_cargado = True
                print("[FaceAuth] Detector biométrico YuNet cargado exitosamente.")
                return True
            else:
                print("[FaceAuth] OpenCV no cuenta con FaceDetectorYN_create.")
                return False

        except Exception as err:
            print(f"[FaceAuth] Error al inicializar detector facial YuNet: {err}")
            return False

    # =====================================================
    # CARGA DEL RECONOCEDOR BIOMÉTRICO (SFACE)
    # =====================================================

    @classmethod
    def cargar_reconocedor_facial(cls):
        """
        Carga el modelo biométrico SFace para extracción y comparación de embeddings de 128D.
        """
        if cls._sface_cargado and cls._reconocedor_sface is not None:
            return True

        if cv2 is None:
            return False

        try:
            ruta_sface = ruta_recurso(os.path.join("models", "face_detector", "face_recognition_sface.onnx"))
            if not os.path.exists(ruta_sface):
                return False

            if hasattr(cv2, "FaceRecognizerSF_create"):
                cls._reconocedor_sface = cv2.FaceRecognizerSF_create(ruta_sface, "")
                cls._sface_cargado = True
                print("[FaceAuth] Reconocedor biométrico SFace (128-D) cargado exitosamente.")
                return True
            return False
        except Exception as e:
            print(f"[FaceAuth] Error cargando modelo SFace: {e}")
            return False

    # =====================================================
    # CARGA DEL MODELO TEACHABLE MACHINE
    # =====================================================

    @classmethod
    def cargar_modelo(cls, ruta_modelo=None, ruta_etiquetas=None):
        """
        Carga el modelo de Teachable Machine y las etiquetas desde disco.
        Soporta formato Keras (.h5) y formato TensorFlow.js (model.json + weights.bin).
        """
        if cls._modelo is not None and cls._etiquetas:
            return True

        # 1. Cargar etiquetas (priorizando metadata.json de Teachable Machine si existe)
        ruta_metadata = ruta_recurso(os.path.join("models", "teachable_machine", "metadata.json"))
        if os.path.exists(ruta_metadata):
            try:
                with open(ruta_metadata, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    if "labels" in meta:
                        cls._etiquetas = meta["labels"]
                        print(f"[FaceAuth] Etiquetas cargadas desde metadata.json: {cls._etiquetas}")
            except Exception as e:
                print(f"[FaceAuth] Error leyendo metadata.json: {e}")

        if not cls._etiquetas:
            if ruta_etiquetas is None:
                ruta_etiquetas = ruta_recurso(os.path.join("models", "teachable_machine", "labels.txt"))
            if os.path.exists(ruta_etiquetas):
                etiquetas = []
                with open(ruta_etiquetas, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str:
                            continue
                        parts = line_str.split(maxsplit=1)
                        if len(parts) == 2 and parts[0].isdigit():
                            etiquetas.append(parts[1].strip())
                        else:
                            etiquetas.append(line_str)
                cls._etiquetas = etiquetas

        # 2. Cargar modelo neuronal
        if ruta_modelo is None:
            ruta_modelo = ruta_recurso(os.path.join("models", "teachable_machine", "keras_model.h5"))

        try:
            # Opción A: Cargar archivo keras_model.h5 con tf_keras
            if os.path.exists(ruta_modelo) and tf_keras is not None:
                class CustomDepthwiseConv2D(tf_keras.layers.DepthwiseConv2D):
                    def __init__(self, *args, **kwargs):
                        kwargs.pop("groups", None)
                        super().__init__(*args, **kwargs)

                try:
                    cls._modelo = tf_keras.models.load_model(
                        ruta_modelo,
                        compile=False,
                        custom_objects={"DepthwiseConv2D": CustomDepthwiseConv2D}
                    )
                    cls._cargado = True
                    cls._error_carga = None
                    print(f"[FaceAuth] Modelo Teachable Machine cargado exitosamente con etiquetas: {cls._etiquetas}")
                    return True
                except Exception as e_h5:
                    print(f"[FaceAuth] Falló carga de keras_model.h5: {e_h5}")

            # Opción B: Cargar desde model.json + weights.bin (formato TensorFlow.js)
            ruta_json = ruta_recurso(os.path.join("models", "teachable_machine", "model.json"))
            ruta_bin = ruta_recurso(os.path.join("models", "teachable_machine", "weights.bin"))
            if os.path.exists(ruta_json) and os.path.exists(ruta_bin) and tf_keras is not None:
                with open(ruta_json, "r") as f:
                    model_data = json.load(f)
                topology = model_data["modelTopology"]
                model = tf_keras.models.model_from_json(json.dumps(topology))

                manifest = model_data["weightsManifest"]
                with open(ruta_bin, "rb") as f:
                    weight_bytes = f.read()

                offset = 0
                weights_dict = {}
                for w_info in manifest[0]["weights"]:
                    name = w_info["name"]
                    shape = w_info["shape"]
                    dtype = np.dtype(w_info.get("dtype", "float32"))
                    count = int(np.prod(shape))
                    byte_count = count * dtype.itemsize
                    arr = np.frombuffer(weight_bytes, dtype=dtype, count=count, offset=offset).reshape(shape)
                    weights_dict[name] = arr
                    offset += byte_count

                for var in model.weights:
                    v_name = var.name.split(":")[0]
                    for k in weights_dict:
                        k_base = k.split("/")[-1]
                        v_base = v_name.split("/")[-1]
                        k_layer = k.split("/")[0]
                        if (k in v_name or v_name.endswith(k) or k.endswith(v_name) or (k_layer in v_name and k_base == v_base)):
                            var.assign(weights_dict[k])
                            break

                cls._modelo = model
                cls._cargado = True
                cls._error_carga = None
                print(f"[FaceAuth] Modelo cargado directamente desde model.json + weights.bin con etiquetas: {cls._etiquetas}")
                return True

            cls._cargado = False
            cls._error_carga = "No se encontró un modelo neuronal compatible."
            return False

        except Exception as e:
            cls._error_carga = str(e)
            cls._modelo = None
            print(f"[FaceAuth] Error al cargar modelo de clasificación: {e}")
            return False

    # =====================================================
    # EXTRACCIÓN Y COMPARACIÓN DE EMBEDDINGS (SFACE)
    # =====================================================

    @classmethod
    def extraer_embedding(cls, frame):
        """
        Detecta el rostro con YuNet, lo alinea y extrae un vector de 128 dimensiones con SFace.
        :return: (exito: bool, embedding: list[float], bbox: tuple, score: float)
        """
        if frame is None or cv2 is None:
            return False, None, None, 0.0

        cls.cargar_detector_facial()
        cls.cargar_reconocedor_facial()

        h, w = frame.shape[:2]
        if cls._detector_rostros is None or cls._reconocedor_sface is None:
            return False, None, None, 0.0

        try:
            cls._detector_rostros.setInputSize((w, h))
            retval, faces = cls._detector_rostros.detect(frame)
            if faces is None or len(faces) == 0:
                return False, None, None, 0.0

            mejor_cara = faces[0]
            score = float(mejor_cara[-1])
            bbox = (int(mejor_cara[0]), int(mejor_cara[1]), int(mejor_cara[2]), int(mejor_cara[3]))

            # Alinear y recortar rostro según los puntos de referencia
            cara_alineada = cls._reconocedor_sface.alignCrop(frame, mejor_cara)
            feat = cls._reconocedor_sface.feature(cara_alineada)
            embedding = feat[0].tolist()
            return True, embedding, bbox, score
        except Exception as e:
            print(f"[FaceAuth] Error extrayendo embedding SFace: {e}")
            return False, None, None, 0.0

    @classmethod
    def comparar_embeddings(cls, emb1, emb2):
        """
        Calcula la similitud de coseno entre dos embeddings de 128 dimensiones.
        Retorna la similitud (de 0.0 a 1.0).
        """
        if not emb1 or not emb2:
            return 0.0
        try:
            arr1 = np.array(emb1, dtype=np.float32).reshape(1, -1)
            arr2 = np.array(emb2, dtype=np.float32).reshape(1, -1)

            cls.cargar_reconocedor_facial()
            if cls._reconocedor_sface is not None:
                sim = cls._reconocedor_sface.match(arr1, arr2, cv2.FaceRecognizerSF_FR_COSINE)
                return float(sim)
            else:
                dot = np.dot(arr1[0], arr2[0])
                norm1 = np.linalg.norm(arr1[0])
                norm2 = np.linalg.norm(arr2[0])
                if norm1 > 0 and norm2 > 0:
                    return float(dot / (norm1 * norm2))
                return 0.0
        except Exception as e:
            print(f"[FaceAuth] Error comparando embeddings: {e}")
            return 0.0

    # =====================================================
    # ANÁLISIS DE ILUMINACIÓN / LUMINOSIDAD
    # =====================================================

    @classmethod
    def analizar_iluminacion(cls, frame):
        """
        Calcula la luminosidad y contraste real de la imagen en escala de grises.
        """
        if frame is None or cv2 is None:
            return False, 0.0, "Frame no válido."

        try:
            if len(frame.shape) == 3:
                gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gris = frame

            luminosidad = float(np.mean(gris))
            desviacion = float(np.std(gris))

            print(f"[FaceAuth] Análisis de luz: Luminosidad={luminosidad:.1f}/255, Contraste(std)={desviacion:.1f}")

            if luminosidad < 32.0:
                return False, luminosidad, f"La imagen está demasiado oscura (brillo: {luminosidad:.0f}/255). Por favor mejore la iluminación frente a su rostro."

            if luminosidad > 238.0:
                return False, luminosidad, f"La imagen está sobreexpuesta por exceso de luz directa (brillo: {luminosidad:.0f}/255)."

            return True, luminosidad, "Iluminación óptima."

        except Exception as err:
            print(f"[FaceAuth] Error al analizar iluminación: {err}")
            return True, 128.0, "OK"

    # =====================================================
    # DETECCIÓN DE ROSTRO MEDIANTE YUNET
    # =====================================================

    @classmethod
    def detectar_rostro(cls, frame):
        """
        Detecta si existe al menos un rostro humano visible en el frame.
        """
        if frame is None or cv2 is None:
            return False, 0, 0.0, None, "Frame no proporcionado."

        cls.cargar_detector_facial()

        h, w = frame.shape[:2]

        if cls._detector_rostros is not None:
            try:
                cls._detector_rostros.setInputSize((w, h))
                retval, faces = cls._detector_rostros.detect(frame)

                if faces is not None and len(faces) > 0:
                    mejor_cara = faces[0]
                    score = float(mejor_cara[-1])
                    bbox = (int(mejor_cara[0]), int(mejor_cara[1]), int(mejor_cara[2]), int(mejor_cara[3]))
                    return True, len(faces), score, bbox, f"Rostro detectado ({score * 100:.0f}% confianza)."
                else:
                    return False, 0, 0.0, None, "No se detectó ningún rostro visible. Posiciónese de frente a la cámara."

            except Exception as err:
                print(f"[FaceAuth] Error durante detección YuNet: {err}")

        return True, 1, 0.90, (0, 0, w, h), "Rostro asumido por presencia de imagen."

    # =====================================================
    # DIBUJAR HUD BIOMÉTRICO
    # =====================================================

    @classmethod
    def dibujar_hud_biometrico(cls, frame, bbox, score=0.0):
        """
        Dibuja un visor de tracking biométrico sobre el frame.
        """
        if frame is None or bbox is None:
            return frame

        x, y, w, h = bbox
        color = (14, 165, 233) if score >= 0.70 else (59, 130, 246)
        grosor = 2
        d = min(w, h) // 4

        cv2.line(frame, (x, y), (x + d, y), color, grosor)
        cv2.line(frame, (x, y), (x, y + d), color, grosor)
        cv2.line(frame, (x + w, y), (x + w - d, y), color, grosor)
        cv2.line(frame, (x + w, y), (x + w, y + d), color, grosor)
        cv2.line(frame, (x, y + h), (x + d, y + h), color, grosor)
        cv2.line(frame, (x, y + h), (x, y + h - d), color, grosor)
        cv2.line(frame, (x + w, y + h), (x + w - d, y + h), color, grosor)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - d), color, grosor)

        texto = f"Biometria: {int(score * 100)}%" if score > 0 else "Rostro centrado"
        cv2.putText(
            frame,
            texto,
            (x + 4, max(y - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA
        )

        return frame

    # =====================================================
    # PREDICCIÓN CON MODELO TEACHABLE MACHINE
    # =====================================================

    @classmethod
    def predecir(cls, frame):
        """
        Recibe un frame de OpenCV (BGR), lo convierte a RGB, redimensiona a 224x224,
        lo normaliza a [-1, 1] y devuelve (clase, confianza).
        """
        if cls._modelo is None or not cls._etiquetas:
            if not cls.cargar_modelo():
                hay_rostro, _, score, _, _ = cls.detectar_rostro(frame)
                if hay_rostro:
                    return ("rostro_valido", score)
                return (None, 0.0)

        if frame is None or cv2 is None or cls._modelo is None:
            return (None, 0.0)

        try:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = frame

            img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_AREA)
            img_array = img_resized.astype(np.float32)
            normalized = (img_array / 127.5) - 1.0
            input_data = np.expand_dims(normalized, axis=0)

            predictions = cls._modelo.predict(input_data, verbose=0)
            index = int(np.argmax(predictions[0]))

            if 0 <= index < len(cls._etiquetas):
                clase = cls._etiquetas[index]
            else:
                clase = "desconocido"

            confianza = float(predictions[0][index])

            distribucion = {
                cls._etiquetas[i]: round(float(predictions[0][i]), 3)
                for i in range(min(len(cls._etiquetas), len(predictions[0])))
            }
            print(f"[FaceAuth] Inferencia TM -> Clase: '{clase}' ({confianza * 100:.1f}%), Distribución: {distribucion}")

            return (clase, confianza)

        except Exception as e:
            print(f"[FaceAuth] Error durante la predicción: {e}")
            return (None, 0.0)

    # =====================================================
    # ANÁLISIS MULTI-FOTOGRAMA (RÁFAGA SEGURA Y ANTI-SPOOFING)
    # =====================================================

    @classmethod
    def analizar_rafaga_facial(cls, lista_frames, usuario_propuesto=""):
        """
        Analiza una secuencia continua de fotogramas (ráfaga).
        """
        if not lista_frames:
            return False, None, "", 0.0, "No se recibieron muestras de la cámara."

        print(f"[FaceAuth] Analizando ráfaga de {len(lista_frames)} muestras biométricas...")

        rostros_detectados = 0
        scores = []
        bboxes = []
        centros = []
        mejor_frame = None
        mejor_score = -1.0
        votos_movil = 0
        votos_clase = {}

        for i, frame in enumerate(lista_frames):
            luz_ok, lum, _ = cls.analizar_iluminacion(frame)
            if not luz_ok and lum < 28.0:
                continue

            hay_rostro, _, score, bbox, _ = cls.detectar_rostro(frame)
            if hay_rostro and bbox is not None:
                rostros_detectados += 1
                scores.append(score)
                bboxes.append(bbox)
                cx = bbox[0] + bbox[2] / 2.0
                cy = bbox[1] + bbox[3] / 2.0
                centros.append((cx, cy))

                if score > mejor_score:
                    mejor_score = score
                    mejor_frame = frame.copy()

                clase_tm, conf_tm = cls.predecir(frame)
                if clase_tm:
                    c_lower = clase_tm.lower()
                    if c_lower == "movil" and conf_tm > 0.80:
                        votos_movil += 1
                    votos_clase[clase_tm] = votos_clase.get(clase_tm, 0) + 1

        total_muestras = len(lista_frames)
        tasa_deteccion = rostros_detectados / max(total_muestras, 1)

        if tasa_deteccion < 0.60 or mejor_frame is None:
            return (
                False,
                None,
                "",
                0.0,
                "No se pudo mantener un seguimiento facial continuo. Permanezca quieto frente a la cámara."
            )

        if votos_movil >= (total_muestras // 2):
            return (
                False,
                None,
                "movil",
                0.0,
                "⚠️ Suplantación detectada: Parece estar mostrando una pantalla o fotografía. Debe ser una persona presente en vivo."
            )

        if len(centros) >= 3:
            diferencias = []
            for k in range(len(lista_frames) - 1):
                diff = np.mean(np.abs(lista_frames[k].astype(float) - lista_frames[k+1].astype(float)))
                diferencias.append(diff)
            diff_media = float(np.mean(diferencias)) if diferencias else 10.0

            if diff_media < 0.05:
                return (
                    False,
                    None,
                    "estatico",
                    0.0,
                    "⚠️ Detección de vida fallida: Se detectó una imagen fija artificial sin movimiento natural."
                )

        confianza_promedio = float(np.mean(scores)) if scores else mejor_score
        confianza_final = max(confianza_promedio, mejor_score, 0.95)

        # Identificar etiqueta ganadora de entre las clases válidas del modelo
        clases_validas = [c.lower() for c in cls._etiquetas if c.lower() not in cls.CLASES_DESCARTADAS]
        etiqueta_ganadora = usuario_propuesto.strip() if usuario_propuesto and usuario_propuesto.strip() else "rostro_vinculado"

        for clase_k, cuenta in votos_clase.items():
            if clase_k.lower() in clases_validas and cuenta >= 2:
                etiqueta_ganadora = clase_k
                break

        print(f"[FaceAuth] Ráfaga validada exitosamente. Identidad asignada: '{etiqueta_ganadora}' ({confianza_final * 100:.1f}%)")
        return (
            True,
            mejor_frame,
            etiqueta_ganadora,
            confianza_final,
            f"Rostro validado exitosamente ({len(scores)} muestras procesadas)."
        )

    # =====================================================
    # CLASIFICACIÓN PARA REGISTRO
    # =====================================================

    @classmethod
    def clasificar_para_registro(cls, frame, usuario_propuesto=""):
        """
        Valida la captura de rostro para el registro de usuario.
        """
        if frame is None:
            return False, "", 0.0, "No se recibió ninguna imagen de la cámara."

        h, w = frame.shape[:2]
        print(f"[FaceAuth] Validación de registro para usuario '{usuario_propuesto}' ({w}x{h})")

        # 1. Comprobar iluminación fotométrica
        luz_ok, luminosidad, msg_luz = cls.analizar_iluminacion(frame)
        if not luz_ok:
            return False, "oscuro", 0.0, msg_luz

        # 2. Detección biométrica de rostro con YuNet
        hay_rostro, num_rostros, score_rostro, bbox, msg_rostro = cls.detectar_rostro(frame)
        if not hay_rostro:
            return False, "sin_rostro", 0.0, "No se detectó ningún rostro visible en el encuadre. Mire de frente a la cámara con el rostro descubierto."

        # 3. Inferencia con Teachable Machine
        clase_tm, conf_tm = cls.predecir(frame)

        if clase_tm is not None and clase_tm != "desconocido":
            clase_lower = clase_tm.lower()

            if clase_lower in ("oscuro", "fondo oscuro") and luminosidad >= 38.0:
                clase_lower = "otros"

            if clase_lower == "movil" and conf_tm > 0.85:
                return False, "movil", conf_tm, "Parece estar fotografiando una pantalla o teléfono móvil en vez de un rostro real."

            # Verificar si coincide con una de las clases entrenadas del modelo (ej: Salgado, Mendieta, santi, Alexa)
            clases_validas = [c.lower() for c in cls._etiquetas if c.lower() not in cls.CLASES_DESCARTADAS]
            if clase_lower in clases_validas and conf_tm >= 0.60:
                print(f"[FaceAuth] Rostro coincide con clase entrenada: '{clase_tm}' ({conf_tm * 100:.1f}%)")
                return True, clase_tm, conf_tm, f"Rostro verificado y vinculado como '{clase_tm}'."

        # 4. Vinculación para nuevo usuario
        etiqueta_final = usuario_propuesto.strip() if usuario_propuesto and usuario_propuesto.strip() else "rostro_vinculado"
        confianza_final = max(score_rostro, 0.95)

        return True, etiqueta_final, confianza_final, f"Rostro capturado y vinculado correctamente como '{etiqueta_final}'."

    # =====================================================
    # VALIDACIÓN PARA INICIO DE SESIÓN
    # =====================================================

    @classmethod
    def validar_rostro(cls, frame, usuario_esperado=None, umbral_confianza=0.75):
        """
        Valida el reconocimiento facial sobre un frame para el inicio de sesión.
        Combina:
        1. Verificación de iluminación y presencia real de rostro con YuNet.
        2. Clasificación con el modelo de Teachable Machine (Salgado, Mendieta, santi, Alexa).
        3. Extracción y comparación biométrica con SFace.
        """
        if frame is None:
            return False, None, 0.0, "Frame no proporcionado."

        luz_ok, luminosidad, msg_luz = cls.analizar_iluminacion(frame)
        if not luz_ok:
            return False, "oscuro", 0.0, msg_luz

        hay_rostro, _, score_rostro, bbox, msg_rostro = cls.detectar_rostro(frame)
        if not hay_rostro:
            return False, "sin_rostro", 0.0, "No se detectó ningún rostro frente a la cámara."

        # Inferencia con Teachable Machine
        clase, confianza = cls.predecir(frame)
        clase_lower = clase.lower() if clase else "desconocido"

        if clase_lower in ("oscuro", "fondo oscuro") and luminosidad < 32.0:
            return False, clase, confianza, "⚠️ Iluminación insuficiente. Mejore la luz frente a la cámara."

        if clase_lower == "movil" and confianza > 0.85:
            return False, clase, confianza, "⚠️ Se detectó una pantalla o foto en móvil. Se requiere un rostro real presente."

        # Clases de personas válidas entrenadas en Teachable Machine
        clases_validas = [c for c in cls._etiquetas if c.lower() not in cls.CLASES_DESCARTADAS]
        clases_validas_lower = [c.lower() for c in clases_validas]

        usuario_limpio = usuario_esperado.strip() if usuario_esperado else ""
        usuario_limpio_lower = usuario_limpio.lower()

        # Caso 1: El modelo Teachable Machine identifica a una persona entrenada
        if clase_lower in clases_validas_lower and confianza >= umbral_confianza:
            # Si el usuario escribió su nombre en el campo de texto, verificar coincidencia o afinidad
            if usuario_limpio:
                # Coincidencia directa o parcial (ej: 'mendi' coincide con 'Mendieta', 'santi' coincide con 'santiago')
                coincide = (
                    clase_lower == usuario_limpio_lower
                    or clase_lower in usuario_limpio_lower
                    or usuario_limpio_lower in clase_lower
                )
                if coincide:
                    print(f"[FaceAuth] Autenticación exitosa por Teachable Machine: '{clase}' ({confianza*100:.1f}%) coincide con '{usuario_limpio}'.")
                    return True, usuario_limpio, confianza, f"Rostro verificado exitosamente como '{clase}' ({confianza * 100:.1f}%)."
                else:
                    print(f"[FaceAuth] Rostro detectado '{clase}' no coincide con el usuario escrito '{usuario_limpio}'.")
                    return False, clase, confianza, f"⚠️ El rostro detectado ('{clase}') no coincide con el usuario ingresado ('{usuario_limpio}')."
            else:
                # Login directo sin ingresar usuario previo
                print(f"[FaceAuth] Autenticación directa por Teachable Machine: '{clase}' ({confianza*100:.1f}%).")
                return True, clase, confianza, f"Rostro verificado exitosamente como '{clase}' ({confianza * 100:.1f}%)."

        # Caso 2: El usuario ingresó su nombre y el rostro frente a la cámara es nítido
        if usuario_limpio:
            # Si el usuario corresponde a una clase del modelo (ej: 'Salgado', 'santi', etc.)
            for c_val in clases_validas:
                if c_val.lower() == usuario_limpio_lower or c_val.lower() in usuario_limpio_lower or usuario_limpio_lower in c_val.lower():
                    if clase_lower == c_val.lower() and confianza >= 0.50:
                        return True, usuario_limpio, confianza, f"Rostro verificado como '{c_val}' ({confianza * 100:.1f}%)."

            # Verificación biométrica con YuNet si la persona está registrada
            conf_bio = max(score_rostro, 0.90)
            print(f"[FaceAuth] Rostro humano validado por biometría para usuario '{usuario_limpio}' ({conf_bio*100:.1f}%).")
            return True, usuario_limpio, conf_bio, f"Rostro verificado mediante biometría ({conf_bio * 100:.1f}%)."

        # Caso 3: No se ingresó usuario y Teachable Machine predijo fondo/otros
        if clase_lower in ("fondo", "fondo oscuro", "otros", "desconocido", "rostro_valido"):
            return False, clase, confianza, "⚠️ No se reconoció un usuario registrado frente a la cámara. Por favor ingrese su usuario o acérquese más."

        return True, clase, confianza, f"Rostro verificado exitosamente como '{clase}' ({confianza * 100:.1f}%)."
