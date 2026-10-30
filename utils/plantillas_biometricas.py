"""
Plantillas biométricas propias de cada usuario: palabra de ingreso (voz) y postura de ingreso.

Voz: el modelo de Teachable Machine solo conoce palabras fijas, así que la palabra elegida
por el usuario se verifica por comparación con sus propias grabaciones: coeficientes MFCC
(huella del timbre y de los sonidos) alineados en el tiempo con DTW. Una palabra distinta o
una voz distinta dan una distancia mayor que la de las muestras de registro entre sí.

Postura: plantilla con los 17 puntos clave de PoseNet promediados en cada captura; se compara
con ReconocedorPose.similitud (independiente de posición y tamaño en la imagen).

Todas las funciones son puras (sin interfaz) para poder ejecutarlas en un hilo.
"""
import re

import numpy as np

from utils.umbrales_biometria import (
    MARGEN_IDENTIFICACION,
    UMBRAL_CONFIANZA_VOZ,
    UMBRAL_SIMILITUD_POSTURA,
)

MUESTRAS_REGISTRO = 3
SEGUNDOS_PALABRA = 2.5

# Palabra de ingreso: una sola palabra de 3 a 20 letras (se admiten tildes y ñ)
PATRON_PALABRA = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,20}$")

# ---- Parámetros MFCC ----
_VENTANA_S = 0.025
_SALTO_S = 0.010
_NUM_FILTROS = 26
_NUM_COEFICIENTES = 13
_FREC_MIN, _FREC_MAX = 80.0, 7600.0
_VOZ_MINIMA_S = 0.20      # duración mínima de voz detectada
_RANGO_DINAMICO_DB = 35.0  # tramos más de 35 dB bajo el pico se consideran silencio

# Límites de la distancia de referencia: evitan que unas muestras de registro casi
# idénticas vuelvan la verificación imposible, o que unas muy dispares la vuelvan laxa.
# Calibrados con voces sintéticas (misma palabra y voz: distancia <= 1.6; otra palabra u
# otra voz: >= 2.4, con referencias de 0.8-1.4). Revisar los logs "[VozIngreso]" con
# grabaciones reales y ajustar si hace falta.
_DISTANCIA_REF_MIN = 0.8
_DISTANCIA_REF_MAX = 2.5
# Distancia máxima entre dos muestras de registro antes de considerarlas palabras distintas
_DISTANCIA_REGISTRO_MAX = 3.5
# Cuántas veces la referencia puede crecer la distancia hasta llegar a confianza 0
# (con 1.3, el umbral de 50 % acepta hasta 1.65 veces la distancia de referencia)
_PENDIENTE_CONFIANZA = 1.3

# Puntos clave visibles mínimos para aceptar una postura
_PUNTOS_MINIMOS_POSTURA = 7


def validar_palabra(palabra):
    """Devuelve None si la palabra es válida o un mensaje explicando el problema."""
    palabra = (palabra or "").strip()
    if len(palabra) < 3:
        return "La palabra de ingreso debe tener al menos 3 letras."
    if not PATRON_PALABRA.match(palabra):
        return "Use una sola palabra, solo con letras (sin espacios, números ni símbolos)."
    return None


# =====================================================
# VOZ: MFCC + DTW
# =====================================================

def _matriz_mel(frecuencia, n_fft):
    """Banco de filtros triangulares en escala mel [filtros, n_fft // 2 + 1]."""
    def a_mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def a_hz(m):
        return 700.0 * (10 ** (m / 2595.0) - 1.0)

    puntos = a_hz(np.linspace(a_mel(_FREC_MIN), a_mel(min(_FREC_MAX, frecuencia / 2)), _NUM_FILTROS + 2))
    bins = np.floor((n_fft + 1) * puntos / frecuencia).astype(int)
    filtros = np.zeros((_NUM_FILTROS, n_fft // 2 + 1), dtype=np.float32)
    for i in range(1, _NUM_FILTROS + 1):
        izq, centro, der = bins[i - 1], bins[i], bins[i + 1]
        if centro > izq:
            filtros[i - 1, izq:centro] = (np.arange(izq, centro) - izq) / (centro - izq)
        if der > centro:
            filtros[i - 1, centro:der] = (der - np.arange(centro, der)) / (der - centro)
    return filtros


def _matriz_dct(n_entrada, n_salida):
    """DCT-II ortonormal como matriz [n_salida, n_entrada]."""
    k = np.arange(n_salida)[:, None]
    n = np.arange(n_entrada)[None, :]
    dct = np.cos(np.pi * k * (2 * n + 1) / (2 * n_entrada)) * np.sqrt(2.0 / n_entrada)
    dct[0] /= np.sqrt(2.0)
    return dct.astype(np.float32)


def caracteristicas_voz(audio, frecuencia):
    """
    Convierte un audio mono en una secuencia MFCC [frames, 12] solo del tramo con voz
    (se recortan los silencios del inicio y del final). Lanza ValueError si no hay voz.
    """
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    if audio.size == 0 or float(np.abs(audio).max()) < 0.01:
        raise ValueError("No se detectó voz: el micrófono parece silenciado o muy lejos.")

    ventana = int(round(_VENTANA_S * frecuencia))
    salto = int(round(_SALTO_S * frecuencia))
    n_fft = 1 << (ventana - 1).bit_length()
    if audio.size < ventana:
        raise ValueError("La grabación es demasiado corta.")

    inicios = np.arange(0, audio.size - ventana + 1, salto)
    frames = np.stack([audio[i:i + ventana] for i in inicios]) * np.hamming(ventana).astype(np.float32)
    potencia = (np.abs(np.fft.rfft(frames, n_fft, axis=1)) ** 2) / n_fft
    frecuencias = np.fft.rfftfreq(n_fft, 1.0 / frecuencia)

    # Detección de voz por energía en la banda de la voz (100-4000 Hz), sobre la señal sin
    # pre-énfasis para que el ruido agudo no tape la palabra. Se conserva desde el primer
    # hasta el último frame con voz.
    banda = (frecuencias >= 100) & (frecuencias <= 4000)
    energia_db = 10.0 * np.log10(potencia[:, banda].sum(axis=1) + 1e-10)
    piso = np.percentile(energia_db, 10)
    umbral = max(energia_db.max() - _RANGO_DINAMICO_DB, piso + 6.0)
    con_voz = np.where(energia_db > umbral)[0]
    if con_voz.size == 0 or (con_voz[-1] - con_voz[0] + 1) * _SALTO_S < _VOZ_MINIMA_S:
        raise ValueError("No se detectó la palabra. Hable más fuerte y cerca del micrófono.")
    margen = 3
    potencia = potencia[max(0, con_voz[0] - margen):con_voz[-1] + margen + 1]

    # Pre-énfasis (filtro 1 - 0.97 z^-1) aplicado en frecuencia: realza los agudos de la voz
    w = 2.0 * np.pi * frecuencias / frecuencia
    potencia = potencia * (1.0 + 0.97 ** 2 - 2.0 * 0.97 * np.cos(w))

    log_mel = np.log(potencia @ _matriz_mel(frecuencia, n_fft).T + 1e-10)
    mfcc = log_mel @ _matriz_dct(_NUM_FILTROS, _NUM_COEFICIENTES).T
    mfcc = mfcc[:, 1:]                   # c0 (volumen) no aporta a la identidad
    mfcc -= mfcc.mean(axis=0)            # normalización por micrófono/canal (CMN)
    return mfcc.astype(np.float32)


def distancia_dtw(a, b):
    """Distancia DTW entre dos secuencias MFCC, normalizada por la longitud del camino."""
    a, b = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    n, m = len(a), len(b)
    # Palabras de duración muy distinta no pueden ser la misma
    if max(n, m) > 2.5 * min(n, m):
        return float("inf")

    costo = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2))
    acumulado = np.full((n + 1, m + 1), np.inf, dtype=np.float64)
    acumulado[0, 0] = 0.0
    for i in range(1, n + 1):
        fila_prev = acumulado[i - 1]
        fila = acumulado[i]
        c = costo[i - 1]
        for j in range(1, m + 1):
            fila[j] = c[j - 1] + min(fila_prev[j], fila[j - 1], fila_prev[j - 1])
    return float(acumulado[n, m] / (n + m))


def crear_plantilla_voz(audios, frecuencia):
    """
    Crea la plantilla a partir de las grabaciones de registro. Exige que las muestras se
    parezcan entre sí (misma palabra). Devuelve (ok, plantilla | None, mensaje).
    """
    try:
        muestras = [caracteristicas_voz(a, frecuencia) for a in audios]
    except ValueError as error:
        return False, None, str(error)

    distancias = [distancia_dtw(muestras[i], muestras[j])
                  for i in range(len(muestras)) for j in range(i + 1, len(muestras))]
    print(f"[VozIngreso] Distancias entre muestras de registro: {[round(d, 2) for d in distancias]}")

    # Una muestra muy distinta de las demás indica otra palabra o mucho ruido
    if max(distancias) > _DISTANCIA_REGISTRO_MAX:
        return False, None, (
            "Las grabaciones no se parecen entre sí. Repita siempre la misma palabra, "
            "con el mismo tono y en un lugar sin ruido."
        )

    plantilla = {
        "version": 1,
        "muestras": [np.round(m, 3).tolist() for m in muestras],
        "distancia_ref": round(float(np.mean(distancias)), 4),
    }
    return True, plantilla, "Palabra de ingreso registrada."


def mejor_grupo_voz(muestras):
    """
    Registro adaptativo: de todas las grabaciones válidas (secuencias MFCC) elige las 3 más
    parecidas entre sí (o 2 si no hay 3 compatibles). Así una grabación con otro tono o con
    ruido no obliga a repetirlo todo. Devuelve (plantilla | None, distancia máxima del grupo).
    """
    from itertools import combinations

    mejor = (None, float("inf"))
    for tamano in (3, 2):
        for grupo in combinations(range(len(muestras)), tamano):
            distancias = [distancia_dtw(muestras[i], muestras[j]) for i, j in combinations(grupo, 2)]
            peor = max(distancias)
            if peor <= _DISTANCIA_REGISTRO_MAX and peor < mejor[1]:
                plantilla = {
                    "version": 1,
                    "muestras": [np.round(muestras[i], 3).tolist() for i in grupo],
                    "distancia_ref": round(float(np.mean(distancias)), 4),
                }
                mejor = (plantilla, peor)
        if mejor[0] is not None:
            print(f"[VozIngreso] Grupo elegido de {len(mejor[0]['muestras'])} de {len(muestras)} "
                  f"grabaciones (distancia máx. {mejor[1]:.2f})")
            return mejor
    return mejor


def comparar_voz(audio, frecuencia, plantilla):
    """
    Compara una grabación con la plantilla del usuario. Devuelve (confianza 0-1, mensaje).
    La confianza vale 1 si la distancia es igual (o menor) a la habitual entre las muestras
    de registro y baja linealmente a 0 cuando llega a (1 + _PENDIENTE_CONFIANZA) veces.
    """
    try:
        actual = caracteristicas_voz(audio, frecuencia)
    except ValueError as error:
        return 0.0, str(error)

    distancias = [distancia_dtw(actual, np.asarray(m, dtype=np.float32)) for m in plantilla["muestras"]]
    distancia = float(np.mean(distancias))
    referencia = float(np.clip(plantilla.get("distancia_ref", _DISTANCIA_REF_MIN),
                               _DISTANCIA_REF_MIN, _DISTANCIA_REF_MAX))
    confianza = float(np.clip(1.0 - (distancia / referencia - 1.0) / _PENDIENTE_CONFIANZA, 0.0, 1.0))
    print(f"[VozIngreso] Distancia {distancia:.2f} (referencia {referencia:.2f}) -> confianza {confianza * 100:.1f}%")
    return confianza, ""


def verificar_voz(audio, frecuencia, plantilla, umbral=UMBRAL_CONFIANZA_VOZ):
    """Verificación 1:1. Devuelve (ok, confianza, mensaje)."""
    confianza, error = comparar_voz(audio, frecuencia, plantilla)
    if error:
        return False, 0.0, error
    if confianza < umbral:
        return False, confianza, (
            f"La palabra o la voz no coinciden con las registradas "
            f"({confianza * 100:.1f}% < {umbral * 100:.0f}%). Intente de nuevo."
        )
    return True, confianza, f"Voz verificada ({confianza * 100:.1f}%)."


# =====================================================
# POSTURA: PLANTILLA DE PUNTOS CLAVE
# =====================================================

def puntos_postura(frames):
    """
    Promedia los 17 puntos clave de PoseNet de una ráfaga de frames.
    Devuelve una lista de 51 valores (y, x, puntuación). Lanza ValueError si no se ve el cuerpo.
    """
    from utils.reconocimiento_pose import ReconocedorPose

    if not ReconocedorPose.cargar_modelo():
        raise ValueError(f"No se pudo cargar el modelo de postura: {ReconocedorPose._error_carga}")

    puntos = [ReconocedorPose._salidas_posenet(f)[1] for f in frames if f is not None]
    if not puntos:
        raise ValueError("No se pudieron analizar los fotogramas capturados.")

    promedio = np.mean(puntos, axis=0)
    visibles = int((promedio[:, 2] >= ReconocedorPose.PUNTUACION_MINIMA_KEYPOINT).sum())
    if visibles < _PUNTOS_MINIMOS_POSTURA:
        raise ValueError(
            f"Solo se ven {visibles} puntos del cuerpo. Aléjese de la cámara para que se vean "
            f"su cabeza, hombros, brazos y torso, con buena iluminación."
        )
    return [round(float(v), 4) for v in promedio.reshape(-1)]


def similitud_postura(vector_a, vector_b):
    from utils.reconocimiento_pose import ReconocedorPose
    return ReconocedorPose.similitud(vector_a, vector_b)


def crear_plantilla_postura(capturas, umbral=UMBRAL_SIMILITUD_POSTURA):
    """
    Crea la plantilla con las capturas de registro (listas de 51 valores). Exige que se
    parezcan entre sí (misma postura). Devuelve (ok, plantilla | None, mensaje).
    """
    similitudes = [similitud_postura(capturas[i], capturas[j])
                   for i in range(len(capturas)) for j in range(i + 1, len(capturas))]
    print(f"[PosturaIngreso] Similitud entre capturas de registro: {[round(s, 3) for s in similitudes]}")
    if min(similitudes) < umbral:
        return False, None, (
            f"Las capturas no coinciden entre sí ({min(similitudes) * 100:.1f}% < {umbral * 100:.0f}%). "
            f"Repita exactamente la misma postura en las tres capturas."
        )
    return True, {"version": 1, "muestras": capturas}, "Postura de ingreso registrada."


def comparar_postura(vector, plantilla):
    """Similitud media (0-1) entre la postura actual y las capturas de la plantilla."""
    similitud = float(np.mean([similitud_postura(vector, m) for m in plantilla["muestras"]]))
    print(f"[PosturaIngreso] Similitud con la plantilla: {similitud * 100:.1f}%")
    return similitud


def verificar_postura(vector, plantilla, umbral=UMBRAL_SIMILITUD_POSTURA):
    """Verificación 1:1. Devuelve (ok, similitud, mensaje)."""
    similitud = comparar_postura(vector, plantilla)
    if similitud < umbral:
        return False, similitud, (
            f"La postura no coincide con la registrada ({similitud * 100:.1f}% < {umbral * 100:.0f}%). "
            f"Repita la misma postura que usó al registrarla."
        )
    return True, similitud, f"Postura verificada ({similitud * 100:.1f}%)."


# =====================================================
# IDENTIFICACIÓN 1:N (sin usuario escrito)
# =====================================================

def identificar(puntuaciones, umbral):
    """
    Elige al usuario con mayor puntuación de una lista [(usuario, puntuación)]. Exige superar
    el umbral y una ventaja clara sobre el segundo. Devuelve (usuario | None, puntuación, mensaje).
    """
    if not puntuaciones:
        return None, 0.0, "No hay usuarios con este método registrado."

    ordenadas = sorted(puntuaciones, key=lambda par: par[1], reverse=True)
    mejor, puntuacion = ordenadas[0]
    if puntuacion < umbral:
        return None, puntuacion, (
            f"No se encontró ningún usuario que coincida ({puntuacion * 100:.1f}% < {umbral * 100:.0f}%)."
        )
    if len(ordenadas) > 1 and puntuacion - ordenadas[1][1] < MARGEN_IDENTIFICACION:
        return None, puntuacion, (
            "Hay más de un usuario con un resultado parecido. Escriba su nombre de usuario e intente de nuevo."
        )
    return mejor, puntuacion, ""
