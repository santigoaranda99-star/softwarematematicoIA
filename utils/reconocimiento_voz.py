import os
import json
import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

try:
    import sounddevice as sd
except Exception:
    sd = None

from utils.rutas import ruta_recurso
from utils.modelos_tfjs import leer_modelo_tfjs, leer_metadata, resolver_etiqueta
from utils.umbrales_biometria import UMBRAL_CONFIANZA_VOZ, UMBRAL_SIMILITUD_VOZ_TM


class _RedAudioNumpy:
    """
    La red de speech-commands de Teachable Machine (4 x [Conv2D relu + MaxPool] → Flatten →
    Dense(2000, relu) → Dense(clases, softmax)) ejecutada con NumPy, sin TensorFlow/Keras, para
    que funcione igual en el .exe. predict(lote) → (vector de dense_1, probabilidades).
    """

    CAPAS = [("conv2d_1", (2, 2), (2, 2)), ("conv2d_2", (2, 2), (2, 2)),
             ("conv2d_3", (2, 2), (2, 2)), ("conv2d_4", (2, 2), (1, 2))]

    def __init__(self, pesos):
        self.pesos = {k: np.asarray(v, dtype=np.float32) for k, v in pesos.items()}

    @staticmethod
    def _conv_relu(x, kernel, bias):
        """Conv2D 'valid', paso 1, canales al final: x [n, h, w, c] · kernel [kh, kw, c, f]."""
        kh, kw = kernel.shape[:2]
        ventanas = np.lib.stride_tricks.sliding_window_view(x, (kh, kw), axis=(1, 2))  # n,h',w',c,kh,kw
        salida = np.einsum("nhwcij,ijcf->nhwf", ventanas, kernel, optimize=True) + bias
        return np.maximum(salida, 0.0)

    @staticmethod
    def _max_pool(x, tamano, paso):
        n, h, w, c = x.shape
        ph, pw = tamano
        sh, sw = paso
        h2, w2 = (h - ph) // sh + 1, (w - pw) // sw + 1
        ventanas = np.lib.stride_tricks.sliding_window_view(x, (ph, pw), axis=(1, 2))
        return ventanas[:, ::sh, ::sw][:, :h2, :w2].max(axis=(4, 5))

    def predict(self, lote, verbose=0):
        x = np.asarray(lote, dtype=np.float32)
        for nombre, tamano, paso in self.CAPAS:
            x = self._conv_relu(x, self.pesos[f"{nombre}/kernel"], self.pesos[f"{nombre}/bias"])
            x = self._max_pool(x, tamano, paso)
        x = x.reshape(len(x), -1)
        vector = np.maximum(x @ self.pesos["dense_1/kernel"] + self.pesos["dense_1/bias"], 0.0)
        logits = vector @ self.pesos["NewHeadDense/kernel"] + self.pesos["NewHeadDense/bias"]
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        return vector, probs / probs.sum(axis=1, keepdims=True)


class ReconocedorVoz:
    """
    Reconocimiento de palabras clave con el modelo de audio de Teachable Machine
    (@tensorflow-models/speech-commands, formato TMv2 / BROWSER_FFT).

    El modelo espera un espectrograma de [43 frames x 232 bins] igual al que produce
    speech-commands 0.4.0 (browser_fft_extractor.js) con el AnalyserNode de WebAudio:
      - fftSize = 1024, pero el AnalyserNode se configura con fftSize * 2 = 2048
        (línea "this.analyser.fftSize = this.fftSize * 2"): cada frame es la FFT de las
        últimas 2048 muestras con ventana Blackman -> 1024 bins de ~21.5-23.4 Hz.
      - Un frame cada 1024 muestras (setInterval de fftSize / sampleRate): 50 % de solapamiento.
      - Magnitud |X| / 2048 en dB, solo los primeros 232 bins (0 - ~5 kHz).
      - 43 frames (~1 s), normalización z-score sobre todo el espectrograma.
      - Sin remuestreo: se usa la frecuencia del AudioContext del navegador.
    """
    DIRECTORIO_MODELO = os.path.join("models", "tm-my-audio-model")

    # speech-commands no remuestrea: usa la frecuencia del AudioContext de Chrome, que en
    # Windows suele ser 48 kHz. El modelo se entrenó en otra PC, así que no se conoce la
    # exacta; 48000 es lo más común. Para comparar: python -m utils.reconocimiento_voz 44100
    FRECUENCIA_MUESTREO = 48000
    TAMANO_FFT = 1024            # fftSize de speech-commands = salto entre frames
    TAMANO_VENTANA_FFT = 2048    # analyser.fftSize = fftSize * 2
    NUM_FRAMES = 43
    NUM_BINS = 232
    SALTO_VENTANA = 2  # frames entre ventanas deslizantes (~46 ms)

    CLASES_DESCARTADAS = {"otras voces", "ruido de fondo", "voces"}

    # Confianza mínima de la clase para registrar e iniciar sesión por voz.
    # TEMPORAL: se bajó de 0.80 a 0.70 y luego a 0.50 porque las grabaciones reales daban ~60-80 %.
    # Lo ideal es que el preprocesamiento replique exactamente al de speech-commands (ver
    # docstring) y volver a 0.80, no compensar con un umbral más bajo: un umbral bajo acepta
    # más palabras/voces equivocadas. Revisar con los logs "[VozAuth] Inferencia".
    UMBRAL_CONFIANZA = UMBRAL_CONFIANZA_VOZ  # definido en utils/umbrales_biometria.py

    # Correlación mínima con el vector de voz registrado. Valor inicial sin calibrar:
    # revisar los valores "[VozAuth] Similitud" del log con grabaciones reales.
    UMBRAL_SIMILITUD = UMBRAL_SIMILITUD_VOZ_TM

    _modelo = None
    _modelo_vector = None
    _etiquetas = []
    _error_carga = None
    _ventana = None
    _forma_entrada_modelo = None
    _frecuencia_grabacion = None

    # =====================================================
    # CARGA DEL MODELO
    # =====================================================

    @classmethod
    def cargar_modelo(cls):
        """Carga el modelo de model.json + weights.bin y lo ejecuta con NumPy (_RedAudioNumpy)."""
        if cls._modelo is not None:
            return True

        try:
            directorio = ruta_recurso(cls.DIRECTORIO_MODELO)
            cls._etiquetas = [e.strip() for e in leer_metadata(directorio)["wordLabels"]]
            topologia, pesos = leer_modelo_tfjs(directorio)

            # La forma de entrada de model.json debe coincidir con el espectrograma que generamos
            forma = topologia["config"]["layers"][0]["config"]["batch_input_shape"]
            cls._forma_entrada_modelo = forma
            if list(forma[1:]) != [cls.NUM_FRAMES, cls.NUM_BINS, 1]:
                raise ValueError(f"model.json espera {forma}, pero el espectrograma es "
                                 f"[None, {cls.NUM_FRAMES}, {cls.NUM_BINS}, 1].")

            # Una sola red con dos salidas: vector de dense_1 (referencia de voz) y probabilidades
            cls._modelo = cls._modelo_vector = _RedAudioNumpy(pesos)
            cls._error_carga = None
            print(f"[VozAuth] Modelo de audio cargado con etiquetas: {cls._etiquetas}")
            return True

        except Exception as e:
            cls._modelo = None
            cls._error_carga = str(e)
            print(f"[VozAuth] Error al cargar el modelo de audio: {e}")
            return False

    @classmethod
    def etiquetas_validas(cls):
        """Etiquetas que representan a una persona (excluye ruido y voces genéricas)."""
        return [e for e in cls._etiquetas if e.lower() not in cls.CLASES_DESCARTADAS]

    # =====================================================
    # PREPROCESAMIENTO (equivalente a speech-commands)
    # =====================================================

    @classmethod
    def _ventana_blackman(cls):
        # WebAudio usa N (no N-1) en el denominador, a diferencia de np.blackman
        if cls._ventana is None:
            n = np.arange(cls.TAMANO_VENTANA_FFT)
            x = 2 * np.pi * n / cls.TAMANO_VENTANA_FFT
            cls._ventana = (0.42 - 0.5 * np.cos(x) + 0.08 * np.cos(2 * x)).astype(np.float32)
        return cls._ventana

    @classmethod
    def espectrograma(cls, audio):
        """
        Convierte audio mono float32 [-1, 1] en un espectrograma [frames, 232] en dB, como
        getFloatFrequencyData() del AnalyserNode: FFT de 2048 muestras cada 1024 muestras.
        """
        n = cls.TAMANO_VENTANA_FFT
        if len(audio) < n:
            return np.zeros((0, cls.NUM_BINS), dtype=np.float32)
        inicios = range(0, len(audio) - n + 1, cls.TAMANO_FFT)
        frames = np.stack([audio[i:i + n] for i in inicios])
        magnitud = np.abs(np.fft.rfft(frames * cls._ventana_blackman(), axis=1)) / n
        return 20.0 * np.log10(np.maximum(magnitud[:, :cls.NUM_BINS], 1e-12))

    @staticmethod
    def _normalizar(x):
        return (x - x.mean()) / (x.std() + 1e-8)

    # =====================================================
    # CAPTURA DE AUDIO
    # =====================================================

    @classmethod
    def iniciar_grabacion(cls, segundos=2.0):
        """
        Inicia una grabación no bloqueante del micrófono y devuelve el buffer.
        Llamar a terminar_grabacion() cuando haya transcurrido el tiempo.
        """
        if sd is None:
            raise RuntimeError("El paquete 'sounddevice' no está instalado.")
        frecuencia = cls.FRECUENCIA_MUESTREO
        try:
            sd.check_input_settings(samplerate=frecuencia, channels=1, dtype="float32")
        except Exception as err:
            print(f"[VozAuth] ⚠️ El micrófono no admite {frecuencia} Hz ({err}). Se graba a 44100 Hz.")
            frecuencia = 44100
        cls._frecuencia_grabacion = frecuencia
        return sd.rec(int(segundos * frecuencia), samplerate=frecuencia, channels=1, dtype="float32")

    @staticmethod
    def terminar_grabacion(buffer):
        sd.wait()
        return buffer[:, 0]

    @classmethod
    def grabar(cls, segundos=2.0):
        """Graba del micrófono de forma bloqueante."""
        return cls.terminar_grabacion(cls.iniciar_grabacion(segundos))

    # =====================================================
    # INFERENCIA
    # =====================================================

    @classmethod
    def analizar_audio(cls, audio):
        """
        Clasifica un audio de al menos ~1 s usando ventanas deslizantes de 43 frames.
        Usa la ventana más representativa (la de mayor confianza entre las que predicen
        una persona, o si ninguna lo hace, la de mayor confianza global) y devuelve
        (clase, confianza, distribucion, vector), donde vector es la salida de la capa
        dense_1 (2000 valores) de esa ventana, usada como referencia de la voz.
        """
        if not cls.cargar_modelo():
            return None, 0.0, {}, None

        audio = np.asarray(audio, dtype=np.float32)
        espec = cls.espectrograma(audio)
        if len(espec) < cls.NUM_FRAMES:
            print("[VozAuth] Audio demasiado corto para clasificar.")
            return None, 0.0, {}, None

        inicios = range(0, len(espec) - cls.NUM_FRAMES + 1, cls.SALTO_VENTANA)
        lote = np.stack([cls._normalizar(espec[i:i + cls.NUM_FRAMES]) for i in inicios])[..., np.newaxis]

        # LOG TEMPORAL: verificar que el espectrograma coincide con el input_shape de model.json
        frecuencia = cls._frecuencia_grabacion or cls.FRECUENCIA_MUESTREO
        hz_por_bin = frecuencia / cls.TAMANO_VENTANA_FFT
        pico = float(np.abs(audio).max()) if len(audio) else 0.0
        if pico < 0.01:
            print(f"[VozAuth] ⚠️ Nivel de audio muy bajo (pico {pico:.4f}): ¿micrófono silenciado o muy lejos?")
        print(f"[VozAuth] Audio: {len(audio)} muestras a {frecuencia} Hz ({len(audio) / frecuencia:.2f} s), "
              f"pico {pico:.3f} | "
              f"espectrograma {espec.shape} (FFT {cls.TAMANO_VENTANA_FFT}, salto {cls.TAMANO_FFT}, "
              f"0-{hz_por_bin * cls.NUM_BINS:.0f} Hz) | lote {lote.shape} vs model.json {cls._forma_entrada_modelo}")

        vectores, probs = cls._modelo_vector.predict(lote, verbose=0)

        indices = probs.argmax(axis=1)
        confianzas = probs.max(axis=1)
        es_persona = np.array([cls._etiquetas[i].lower() not in cls.CLASES_DESCARTADAS for i in indices])
        candidatas = np.where(es_persona)[0] if es_persona.any() else np.arange(len(probs))
        mejor = candidatas[confianzas[candidatas].argmax()]

        clase = cls._etiquetas[indices[mejor]]
        confianza = float(confianzas[mejor])
        distribucion = {e: round(float(p), 3) for e, p in zip(cls._etiquetas, probs[mejor])}
        print(f"[VozAuth] Inferencia -> Clase: '{clase}' ({confianza * 100:.1f}%), Distribución: {distribucion}")
        return clase, confianza, distribucion, vectores[mejor]

    @classmethod
    def predecir_audio(cls, audio):
        """Devuelve (clase, confianza, distribucion) del audio."""
        return cls.analizar_audio(audio)[:3]

    @classmethod
    def escuchar(cls, segundos=2.0):
        """Graba del micrófono y devuelve (clase, confianza, distribucion)."""
        return cls.predecir_audio(cls.grabar(segundos))

    @staticmethod
    def similitud(vector_a, vector_b):
        """
        Correlación entre dos vectores de voz, recortada a [0, 1]. Se centran antes de
        comparar: dense_1 usa ReLU (valores >= 0) y el coseno sin centrar da ~0.64 incluso
        entre vectores sin relación.
        """
        a = np.asarray(vector_a, dtype=np.float32)
        b = np.asarray(vector_b, dtype=np.float32)
        if a.shape != b.shape:
            return 0.0
        a = a - a.mean()
        b = b - b.mean()
        norma = float(np.linalg.norm(a) * np.linalg.norm(b))
        return max(0.0, float(np.dot(a, b) / norma)) if norma > 0 else 0.0

    @classmethod
    def clase_vinculada(cls, etiqueta_vinculada):
        """Devuelve la etiqueta de voz guardada si sigue existiendo en el modelo, o None."""
        if not etiqueta_vinculada or not cls.cargar_modelo():
            return None
        return resolver_etiqueta(cls.etiquetas_validas(), etiqueta_vinculada)

    # =====================================================
    # REGISTRO Y VERIFICACIÓN
    # =====================================================

    @classmethod
    def evaluar_muestra_registro(cls, audio, umbral_confianza=None, clase_previa=None):
        """
        Valida una grabación de registro: debe reconocerse a una persona entrenada con
        confianza suficiente y, si ya hay muestras previas, la misma persona.
        Devuelve (ok, clase, confianza, vector, mensaje).
        """
        umbral_confianza = cls.UMBRAL_CONFIANZA if umbral_confianza is None else umbral_confianza
        clase, confianza, _, vector = cls.analizar_audio(audio)
        if clase is None:
            return False, None, 0.0, None, "No se pudo analizar el audio capturado."
        if clase.lower() in cls.CLASES_DESCARTADAS:
            return False, clase, confianza, None, (
                "⚠️ No se reconoció ninguna palabra clave entrenada. Diga su palabra clave más cerca del micrófono.\n"
                f"Palabras reconocidas por el modelo: {', '.join(cls.etiquetas_validas())}."
            )
        if confianza < umbral_confianza:
            return False, clase, confianza, None, (
                f"⚠️ Confianza insuficiente ({confianza * 100:.1f}% < {umbral_confianza * 100:.0f}%). Intente de nuevo."
            )
        if clase_previa and clase.lower() != clase_previa.lower():
            return False, clase, confianza, None, (
                f"⚠️ Esta grabación se reconoció como '{clase}', pero las anteriores como '{clase_previa}'. "
                f"Repita siempre la misma palabra clave."
            )
        return True, clase, confianza, vector, f"Muestra reconocida como '{clase}' ({confianza * 100:.1f}%)."

    @staticmethod
    def promediar_vectores(vectores):
        """Vector de referencia: promedio de las muestras normalizadas, como lista para JSON."""
        normalizados = [np.asarray(v, dtype=np.float32) / (np.linalg.norm(v) + 1e-8) for v in vectores]
        return [round(float(x), 5) for x in np.mean(normalizados, axis=0)]

    @classmethod
    def verificar_palabra(cls, audio, clase_esperada, umbral_confianza=None,
                          vector_referencia=None, umbral_similitud=None):
        """
        Comprueba que el audio contiene la palabra esperada y, si hay vector de referencia,
        que se parece a la voz registrada. Devuelve (ok, clase, confianza, mensaje).
        """
        umbral_confianza = cls.UMBRAL_CONFIANZA if umbral_confianza is None else umbral_confianza
        clase, confianza, _, vector = cls.analizar_audio(audio)
        if clase is None:
            return False, None, 0.0, "No se pudo analizar el audio capturado."

        if clase.lower() != clase_esperada.lower():
            if clase.lower() in cls.CLASES_DESCARTADAS:
                return False, clase, confianza, "⚠️ No se detectó la palabra clave. Hable más cerca del micrófono."
            return False, clase, confianza, f"⚠️ La palabra detectada ('{clase}') no coincide con el usuario."

        if confianza < umbral_confianza:
            return False, clase, confianza, (
                f"⚠️ Confianza insuficiente ({confianza * 100:.1f}% < {umbral_confianza * 100:.0f}%). Intente de nuevo."
            )

        if vector_referencia is not None:
            umbral_similitud = cls.UMBRAL_SIMILITUD if umbral_similitud is None else umbral_similitud
            sim = cls.similitud(vector, vector_referencia)
            print(f"[VozAuth] Similitud con la voz registrada: {sim:.3f} (umbral={umbral_similitud})")
            if sim < umbral_similitud:
                return False, clase, confianza, (
                    f"⚠️ La voz no se parece a la registrada ({sim * 100:.1f}% < {umbral_similitud * 100:.0f}%). "
                    f"Intente de nuevo o vuelva a vincular su voz."
                )

        return True, clase, confianza, f"Voz verificada como '{clase}' ({confianza * 100:.1f}%)."


if __name__ == "__main__":
    # Diagnóstico: python -m utils.reconocimiento_voz [frecuencia_hz]
    import sys
    if len(sys.argv) > 1:
        ReconocedorVoz.FRECUENCIA_MUESTREO = int(sys.argv[1])
    ReconocedorVoz.cargar_modelo()
    print(f"Frecuencia: {ReconocedorVoz.FRECUENCIA_MUESTREO} Hz | umbral: {ReconocedorVoz.UMBRAL_CONFIANZA:.0%}")
    while input("\nEnter para grabar 2 s (q + Enter para salir): ").strip().lower() != "q":
        print("Hable ahora...")
        clase, confianza, distribucion = ReconocedorVoz.escuchar()
        print(f"-> {clase} ({confianza:.1%}) {'OK' if confianza >= ReconocedorVoz.UMBRAL_CONFIANZA else 'BAJO UMBRAL'}")
