"""
Prueba de vida (liveness / anti-spoofing) del login biométrico.

Cada método se sigue verificando por sí solo, pero además exige algo que una foto, un video
o un audio grabado no pueden hacer a pedido:
- Rostro: acciones al azar (parpadear, girar, sonreír, abrir la boca) medidas con la malla
  facial, la misma identidad en todos los cuadros y el modelo anti-spoofing MiniFASNetV2.
- Voz: números al azar que solo se muestran al pulsar "Grabar", reconocidos con Vosk, más
  controles de reproducción y de audios repetidos.
- Postura: secuencia al azar (neutra -> postura registrada -> movimiento), con movimiento
  real entre cuadros, proporciones coherentes y el rostro del usuario visible.

Las clases DesafioRostro y DesafioPostura no dependen de la interfaz: reciben cuadros con
procesar(frame, t) y devuelven el estado, para poder ejecutarlas en un hilo y probarlas.
"""
import hashlib
import json
import random
import time

import numpy as np

from utils.umbrales_biometria import UMBRAL_ROSTRO_SFACE, UMBRAL_SIMILITUD_POSTURA

# =====================================================
# CONFIGURACIÓN (ajustable sin tocar la lógica)
# =====================================================

LIVENESS_ROSTRO = True
LIVENESS_VOZ = True
LIVENESS_POSTURA = True

# Segundo factor desactivado por defecto; si se activa, o si el usuario tiene uno de estos
# roles (p. ej. es docente de alguna clase), tras el método biométrico se pide la contraseña.
REQUERIR_SEGUNDO_FACTOR = False
ROLES_CON_SEGUNDO_FACTOR = ("docente",)

# Bloqueo temporal tras fallos seguidos (se duplica en cada racha, hasta el máximo).
# Con False nunca se bloquea ni se muestra el aviso; los intentos fallidos se siguen registrando.
BLOQUEO_BIOMETRICO_ACTIVO = False
INTENTOS_ANTES_DE_BLOQUEO = 3
BLOQUEO_BASE_SEGUNDOS = 60
BLOQUEO_MAXIMO_SEGUNDOS = 900

# ---- Rostro ----
ACCIONES_ROSTRO = ("parpadear", "girar_izquierda", "girar_derecha", "sonreir", "abrir_boca")
ACCIONES_POR_INTENTO = (1, 2)        # mínimo y máximo de acciones al azar
SEGUNDOS_REFERENCIA = 1.5            # mirar de frente para medir el rostro en reposo
SEGUNDOS_REFERENCIA_MAX = 6.0        # tiempo máximo para reconocer el rostro al empezar
LIVENESS_TIEMPO_LECTURA = 3          # segundos para leer cada instrucción (no se evalúa)
LIVENESS_TIEMPO_ACCION = 7           # segundos para realizar cada acción
LIVENESS_REINTENTOS_POR_ACCION = 2   # oportunidades por acción antes de contar el fallo
LIVENESS_TIEMPO_CONFIRMACION = 1.0   # segundos mostrando "✔ ... detectado"
FACTOR_PARPADEO = 0.70               # EAR por debajo de 70 % del normal = ojos cerrados
CAMBIO_GIRO = 0.12                   # desplazamiento de la nariz respecto al reposo
FACTOR_SONRISA = 1.10                # boca 10 % más ancha que en reposo
APERTURA_BOCA = 0.35                 # apertura vertical / ancho de la boca
UMBRAL_IDENTIDAD = UMBRAL_ROSTRO_SFACE
FRACCION_IDENTIDAD = 0.70            # cuadros de frente que deben ser del mismo usuario

# ---- Anti-pantalla / anti-foto (MiniFASNetV2 + heurísticas) ----
# El puntaje del modelo es la diferencia de logits real - falso de cada cuadro (> 0 = real).
ANTISPOOF_ACTIVO = True
ANTISPOOF_UMBRAL_PANTALLA = -1.5     # un cuadro cuenta como "falso" solo por debajo de esto (antes 0.0)
ANTISPOOF_UMBRAL_EVIDENTE = -3.5     # mediana por debajo = foto/pantalla muy evidente
ANTISPOOF_CUADROS_MINIMOS = 8        # cuadros válidos necesarios para decidir
ANTISPOOF_CUADROS_MAXIMOS = 15       # se toman repartidos a lo largo del desafío
ANTISPOOF_PORCENTAJE_RECHAZO = 0.60  # rechazar solo si más de este % de cuadros parecen falsos
ANTISPOOF_REPETIR_SI_DUDOSO = True   # señal dudosa: repetir una acción al azar en vez de rechazar
UMBRAL_MOIRE = 0.05                  # heurísticas: solo cuentan si son evidentes (antes 0.02)
UMBRAL_REFLEJO = 0.15                # (antes 0.08)
# Calidad mínima de un cuadro para evaluarlo (los borrosos o mal iluminados se descartan)
CALIDAD_NITIDEZ_MIN = 25.0           # varianza del laplaciano del rostro a 128x128
CALIDAD_BRILLO_MIN = 55.0            # luminosidad media del rostro (0-255)
CALIDAD_BRILLO_MAX = 225.0
CALIDAD_TAMANO_MIN = 0.12            # ancho del rostro / ancho de la imagen
CALIDAD_CONTRALUZ_MAX = 60.0         # fondo más brillante que el rostro (luz detrás)
# Registro temporal de diagnóstico con todas las métricas de cada intento
ANTISPOOF_LOG = True
ANTISPOOF_ARCHIVO_LOG = "liveness_rostro.log"

CONSEJO_ILUMINACION = ("Mejore la iluminación frontal, evite luz fuerte detrás de usted "
                       "y acérquese a la cámara.")

# ---- Voz ----
SEGUNDOS_DESAFIO_VOZ = 4.0           # una sola toma: palabra de ingreso + números (2 a 4 s)
DIGITOS_DESAFIO = 3
FRACCION_RECORTE_MAX = 0.01          # muestras saturadas permitidas
SILENCIO_DIGITAL_MAX = 400           # muestras exactamente en 0 seguidas (audio inyectado)
UMBRAL_AGUDOS = 0.002                # energía 6-10 kHz / 300-3400 Hz mínima de una voz en vivo
CORRELACION_REPETIDO = 0.95          # envolvente casi idéntica a un audio anterior = repetido

# ---- Postura ----
MOVIMIENTOS_POSTURA = ("levantar_derecho", "levantar_izquierdo")
SEGUNDOS_POR_PASO_POSTURA = 7.0
CUADROS_ESTABLES_POSTURA = 3         # cuadros seguidos cumpliendo cada paso
UMBRAL_POSTURA = UMBRAL_SIMILITUD_POSTURA
MOVIMIENTO_MINIMO = 0.35             # desplazamiento de muñecas / ancho de hombros
VARIACION_PROPORCION_MAX = 0.25      # hombros/ojos debe mantenerse estable entre cuadros
EXIGIR_ROSTRO_EN_POSTURA = True      # el rostro debe verse (y coincidir si está vinculado)
UMBRAL_ROSTRO_POSTURA = 0.30         # SFace con el rostro más lejos (menor resolución)
FRACCION_ROSTRO_POSTURA = 0.60

# Textos en pantalla de cada acción
INSTRUCCIONES = {
    "referencia": "🙂 Mire de frente a la cámara",
    "parpadear": "👁️ Parpadee",
    "girar_izquierda": "↩️ Gire la cabeza a su izquierda",
    "girar_derecha": "↪️ Gire la cabeza a su derecha",
    "sonreir": "😁 Sonría",
    "abrir_boca": "😮 Abra la boca",
    "neutra": "Póngase de pie con los brazos abajo",
    "postura": "Haga su postura de ingreso",
    "levantar_derecho": "Levante el brazo derecho por encima de la cabeza",
    "levantar_izquierdo": "Levante el brazo izquierdo por encima de la cabeza",
}


# Indicador mostrado al completar cada acción del rostro
CONFIRMACIONES = {
    "parpadear": "✔ Parpadeo detectado",
    "girar_izquierda": "✔ Giro a la izquierda detectado",
    "girar_derecha": "✔ Giro a la derecha detectado",
    "sonreir": "✔ Sonrisa detectada",
    "abrir_boca": "✔ Boca abierta detectada",
}


class ResultadoPaso:
    """Estado devuelto por un desafío después de procesar un cuadro."""

    def __init__(self, estado, instruccion="", detalle="", progreso=0.0, datos=None,
                 fase=None, aviso="", restante=None, segundos=None):
        self.estado = estado          # "continuar", "aprobado" o "fallido"
        self.instruccion = instruccion
        self.detalle = detalle
        self.progreso = progreso      # 0-1 del paso actual (para la barra de tiempo)
        self.datos = datos or {}
        # Solo rostro: fase ("referencia", "lectura", "accion", "confirmacion"), texto grande
        # de la fase ("Prepárese... 3", "¡Ahora!", "✔ ..."), fracción y segundos restantes
        self.fase = fase
        self.aviso = aviso
        self.restante = restante
        self.segundos = segundos


# =====================================================
# ROSTRO
# =====================================================

def _calidad_valida(c):
    """Cuadro apto para el anti-spoofing: nítido, bien iluminado, cerca y sin contraluz fuerte."""
    return (c["nitidez"] >= CALIDAD_NITIDEZ_MIN and CALIDAD_BRILLO_MIN <= c["brillo"] <= CALIDAD_BRILLO_MAX
            and c["tamano"] >= CALIDAD_TAMANO_MIN and c["contraluz"] <= CALIDAD_CONTRALUZ_MAX)


def _aviso_calidad(c):
    """
    (mensaje, bloquea) si la luz o la distancia no son adecuadas, o (None, False).
    Poca luz y rostro lejano impiden empezar; el resto solo se avisa (esos cuadros se descartan).
    """
    if c["brillo"] < CALIDAD_BRILLO_MIN:
        return "💡 Hay poca luz en su rostro. Encienda una luz frente a usted.", True
    if c["tamano"] < CALIDAD_TAMANO_MIN:
        return "🔍 Acérquese un poco más a la cámara.", True
    if c["contraluz"] > CALIDAD_CONTRALUZ_MAX:
        return "💡 Hay luz fuerte detrás de usted. Póngase de frente a la luz.", False
    if c["brillo"] > CALIDAD_BRILLO_MAX:
        return "💡 Demasiada luz directa sobre el rostro.", False
    if c["nitidez"] < CALIDAD_NITIDEZ_MIN:
        return "📷 La imagen está borrosa. Quédese quieto o limpie la cámara.", False
    return None, False


def _registrar_diagnostico(metricas, decision, motivo, acciones, coincidencia, repetido):
    """
    (Temporal) Imprime y guarda en liveness_rostro.log cada métrica del anti-spoofing con su
    umbral y la decisión, para calibrar con los valores reales de la webcam del usuario.
    """
    if not ANTISPOOF_LOG:
        return

    def fmt(v, d=2):
        return "—" if v is None else f"{v:.{d}f}"

    lineas = [
        f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} | decisión: {decision.upper()}"
        f"{' (' + motivo + ')' if motivo else ''} | acciones: {acciones}{' | 2ª ronda' if repetido else ''}",
        f"  identidad coincidente: {coincidencia * 100:.0f}% (mínimo {FRACCION_IDENTIDAD * 100:.0f}%)",
        f"  cuadros: válidos {metricas['cuadros_validos']}, descartados por calidad {metricas['cuadros_descartados']}, "
        f"evaluados {metricas['cuadros_evaluados']} (mínimo {ANTISPOOF_CUADROS_MINIMOS})",
        f"  modelo (real-falso): mediana {fmt(metricas['mediana_modelo'])} "
        f"(evidente < {ANTISPOOF_UMBRAL_EVIDENTE}) | cuadros < {ANTISPOOF_UMBRAL_PANTALLA}: "
        f"{fmt(None if metricas['porcentaje_falsos'] is None else metricas['porcentaje_falsos'] * 100, 0)}% "
        f"(rechazo > {ANTISPOOF_PORCENTAJE_RECHAZO * 100:.0f}%)",
        f"  puntajes: {metricas['puntajes_modelo']}",
        f"  moiré {fmt(metricas['moire'], 4)} (máx {UMBRAL_MOIRE}) | reflejo {fmt(metricas['reflejo'], 4)} "
        f"(máx {UMBRAL_REFLEJO})",
        f"  brillo {fmt(metricas['brillo'], 0)} ({CALIDAD_BRILLO_MIN:.0f}-{CALIDAD_BRILLO_MAX:.0f}) | nitidez "
        f"{fmt(metricas['nitidez'], 0)} (mín {CALIDAD_NITIDEZ_MIN:.0f}) | tamaño {fmt(metricas['tamano'])} "
        f"(mín {CALIDAD_TAMANO_MIN}) | contraluz {fmt(metricas['contraluz'], 0)} (máx {CALIDAD_CONTRALUZ_MAX:.0f})",
    ]
    texto = "\n".join(lineas)
    print("[Liveness]\n" + texto)
    try:
        import os
        from utils.rutas import ruta_base
        with open(os.path.join(ruta_base(), ANTISPOOF_ARCHIVO_LOG), "a", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
    except OSError as error:
        print(f"[Liveness] No se pudo escribir el registro: {error}")


class DesafioRostro:
    """
    Secuencia: referencia (de frente) -> 1 o 2 acciones al azar. En la referencia se
    identifica al usuario (1:1 con 'embedding_esperado' o 1:N con 'candidatos'); luego todos
    los cuadros deben mostrar una sola cara, la misma persona y parecer reales.
    """

    def __init__(self, embedding_esperado=None, candidatos=None, acciones=None, semilla=None):
        rng = random.Random(semilla)
        self.acciones = acciones or rng.sample(ACCIONES_ROSTRO, rng.randint(*ACCIONES_POR_INTENTO))
        # Nunca pedir girar a ambos lados en el mismo intento (confunde al usuario)
        if "girar_izquierda" in self.acciones and "girar_derecha" in self.acciones:
            self.acciones.remove("girar_derecha")
        self.embedding_esperado = embedding_esperado
        self.candidatos = candidatos or []     # [(datos_usuario, embedding)]
        self.usuario = None
        self.paso = "referencia"
        self.fase = "referencia"
        self.intento = 1                       # oportunidad actual de la acción
        self.reintentando = False
        self.indice = 0
        self.inicio_paso = None
        self.reposo = []                       # métricas en reposo
        self.base = None
        self.cerrados = False                  # parpadeo: ojos cerrados vistos
        self.identidad = []                    # similitudes en cuadros de frente
        self.reales = []                       # puntuaciones anti-spoofing (cuadros válidos)
        self.pantalla = []
        self.descartados = 0                   # cuadros de frente descartados por calidad
        self.calidades = []
        self.repetido = False                  # ya se repitió una acción por señal dudosa
        self.ultimo_centro = None

    def instruccion_actual(self):
        return INSTRUCCIONES[self.paso]

    def preparar(self):
        """Carga los modelos (antes de empezar a contar el tiempo)."""
        from services.clasificador_imagen import ClasificadorImagen
        from utils import detectores_vida as dv

        if not dv.cargar_modelos():
            raise RuntimeError(dv.error_carga())
        if not (ClasificadorImagen.cargar_detector_facial() and ClasificadorImagen.cargar_reconocedor_facial()):
            raise RuntimeError("No se pudieron cargar los modelos de rostro (YuNet / SFace).")

    def procesar(self, frame, t=None):
        from utils import detectores_vida as dv

        t = time.monotonic() if t is None else t
        if self.inicio_paso is None:
            self.inicio_paso = t
        transcurrido = t - self.inicio_paso

        # Cambios de fase por tiempo: lectura -> acción -> (reintento o fallo) / confirmación -> siguiente
        if self.fase == "referencia" and transcurrido > SEGUNDOS_REFERENCIA_MAX:
            if self.usuario is None:
                return self._fallo("No se reconoció su rostro como el de una cuenta con rostro vinculado.\n\n"
                                   + CONSEJO_ILUMINACION)
            return self._fallo("No se pudo medir su rostro de frente. " + CONSEJO_ILUMINACION)
        if self.fase == "lectura" and transcurrido >= LIVENESS_TIEMPO_LECTURA:
            self.fase, self.inicio_paso, transcurrido = "accion", t, 0.0
            self.cerrados = False
            self.reintentando = False
        elif self.fase == "accion" and transcurrido > LIVENESS_TIEMPO_ACCION:
            if self.intento < LIVENESS_REINTENTOS_POR_ACCION:
                # Se agotó el tiempo: se repite la misma instrucción (con su pausa de lectura)
                self.intento += 1
                self.fase, self.inicio_paso, transcurrido = "lectura", t, 0.0
                self.reintentando = True
            else:
                return self._fallo(
                    f"No se detectó la acción «{self.instruccion_actual()}» en "
                    f"{LIVENESS_REINTENTOS_POR_ACCION} intentos."
                )
        elif self.fase == "confirmacion" and transcurrido >= LIVENESS_TIEMPO_CONFIRMACION:
            return self._siguiente_paso(t)
        elif self.fase == "verificacion" and transcurrido >= LIVENESS_TIEMPO_CONFIRMACION:
            return self._siguiente_paso(t)

        rostros = dv.detectar_rostros(frame)
        if len(rostros) == 0:
            return self._seguir(transcurrido, "No se ve su rostro. Acérquese y mire a la cámara.")
        if len(rostros) > 1:
            return self._fallo("Se detectó más de un rostro. Debe haber una sola persona frente a la cámara.")
        rostro = rostros[0]

        # El rostro no puede "saltar" de lugar entre cuadros (cambio de foto o de persona)
        centro = np.array([rostro[0] + rostro[2] / 2, rostro[1] + rostro[3] / 2])
        if self.ultimo_centro is not None and np.linalg.norm(centro - self.ultimo_centro) > rostro[2] * 0.8:
            return self._fallo("El rostro cambió bruscamente de posición. Intente de nuevo sin moverse de lugar.")
        self.ultimo_centro = centro

        metricas = dv.metricas_rostro(dv.puntos_malla(frame, rostro))
        de_frente = self.base is None or abs(metricas["giro"] - self.base["giro"]) < CAMBIO_GIRO / 2

        # Identidad, anti-spoofing y pantalla solo en cuadros de frente (más fiables)
        if de_frente:
            error = self._revisar_identidad(dv.embedding_rostro(frame, rostro))
            if error:
                return self._fallo(error)
            calidad = dv.calidad_rostro(frame, rostro)
            if _calidad_valida(calidad):
                self.reales.append(dv.puntuacion_real(frame, rostro))
                self.pantalla.append(dv.indicios_pantalla(frame, rostro))
                self.calidades.append(calidad)
            else:
                self.descartados += 1

            # Antes del desafío: comprobar luz y distancia, y avisar en lugar de empezar
            if self.paso == "referencia":
                aviso, bloquea = _aviso_calidad(calidad)
                if bloquea:
                    return self._seguir(transcurrido, aviso)
                self._aviso_luz = aviso

        if self.paso == "referencia":
            if de_frente:
                self.reposo.append(metricas)
            if transcurrido >= SEGUNDOS_REFERENCIA and len(self.reposo) >= 3 and self.usuario is not None:
                self.base = {k: float(np.median([m[k] for m in self.reposo])) for k in metricas}
                return self._siguiente_paso(t)
            return self._seguir(transcurrido, getattr(self, "_aviso_luz", None) or "")

        # Durante la lectura y la confirmación no se evalúa la acción (las comprobaciones de
        # identidad, rostro único y anti-spoofing de arriba sí siguen activas)
        if self.fase == "accion" and self._accion_cumplida(metricas):
            self.fase, self.inicio_paso = "confirmacion", t
            return self._seguir(0.0)
        return self._seguir(transcurrido)

    def _revisar_identidad(self, embedding):
        from services.clasificador_imagen import ClasificadorImagen

        if embedding is None:
            return None
        if self.usuario is None:
            # Primer cuadro de frente: identificar al usuario
            if self.embedding_esperado is not None:
                sim = ClasificadorImagen.comparar_embeddings(embedding, self.embedding_esperado)
                self.identidad.append(sim)
                if sim >= UMBRAL_IDENTIDAD:
                    self.usuario = "esperado"
                return None
            mejores = sorted(((ClasificadorImagen.comparar_embeddings(embedding, emb), d)
                              for d, emb in self.candidatos), key=lambda par: par[0], reverse=True)
            if mejores and mejores[0][0] >= UMBRAL_IDENTIDAD:
                self.usuario = mejores[0][1]
                self.embedding_esperado = next(emb for d, emb in self.candidatos if d is self.usuario)
                self.identidad.append(mejores[0][0])
            return None

        self.identidad.append(ClasificadorImagen.comparar_embeddings(embedding, self.embedding_esperado))
        coincidencias = np.mean(np.array(self.identidad) >= UMBRAL_IDENTIDAD)
        if len(self.identidad) >= 5 and coincidencias < FRACCION_IDENTIDAD:
            return "El rostro no coincide con el de la cuenta durante la prueba."
        return None

    def _accion_cumplida(self, m):
        b = self.base
        if self.paso == "parpadear":
            if m["ear"] < b["ear"] * FACTOR_PARPADEO:
                self.cerrados = True
            # Parpadeo completo: ojos cerrados y luego abiertos de nuevo
            return self.cerrados and m["ear"] > b["ear"] * 0.9
        if self.paso == "girar_izquierda":   # nariz hacia la derecha de la imagen sin espejar
            return m["giro"] - b["giro"] > CAMBIO_GIRO
        if self.paso == "girar_derecha":
            return b["giro"] - m["giro"] > CAMBIO_GIRO
        if self.paso == "sonreir":
            return m["sonrisa"] > b["sonrisa"] * FACTOR_SONRISA and m["boca"] < APERTURA_BOCA
        if self.paso == "abrir_boca":
            return m["boca"] > max(APERTURA_BOCA, b["boca"] + 0.2)
        return False

    def _siguiente_paso(self, t):
        if self.indice >= len(self.acciones):
            return self._veredicto(t)
        self.paso = self.acciones[self.indice]
        self.indice += 1
        # Cada acción empieza con su pausa de lectura y el tiempo completo
        self.fase = "lectura"
        self.intento = 1
        self.reintentando = False
        self.inicio_paso = t
        self.cerrados = False
        return self._seguir(0.0)

    def _veredicto(self, t):
        """
        Tras completar las acciones. Jerarquía: el desafío aleatorio ya se superó; si además la
        identidad coincidió todo el tiempo, el anti-pantalla solo rechaza si es muy evidente.
        Con una señal dudosa se repite una acción al azar (una vez) en lugar de rechazar.
        """
        if self.usuario is None:
            return self._fallo("No se reconoció su rostro. ¿Vinculó su rostro a la cuenta?")
        coincidencia = float(np.mean(np.array(self.identidad) >= UMBRAL_IDENTIDAD)) if self.identidad else 0.0
        if coincidencia < FRACCION_IDENTIDAD:
            return self._fallo("El rostro no coincidió con el de la cuenta durante toda la prueba.")

        decision, motivo, metricas = self._evaluar_antispoof()
        _registrar_diagnostico(metricas, decision, motivo, self.acciones, coincidencia, self.repetido)

        if decision == "rechazar":
            return self._fallo(f"{motivo}\n\n{CONSEJO_ILUMINACION}")
        if decision == "dudoso" and ANTISPOOF_REPETIR_SI_DUDOSO and not self.repetido:
            return self._repetir_con_otra_accion(t)
        return ResultadoPaso("aprobado", "¡Listo!", "", 1.0, {
            "usuario": self.usuario, "similitud": float(np.mean(self.identidad)), "acciones": self.acciones,
        })

    def _evaluar_antispoof(self):
        """
        Decide con 8-15 cuadros válidos repartidos en todo el desafío.
        Devuelve ("aceptar" | "dudoso" | "rechazar", motivo, métricas para el registro).
        """
        indices = np.arange(len(self.reales))
        if len(indices) > ANTISPOOF_CUADROS_MAXIMOS:
            indices = np.linspace(0, len(indices) - 1, ANTISPOOF_CUADROS_MAXIMOS).round().astype(int)
        puntajes = np.array(self.reales)[indices] if len(indices) else np.array([])
        pantalla = [self.pantalla[i] for i in indices]
        calidades = [self.calidades[i] for i in indices]

        metricas = {
            "cuadros_validos": len(self.reales),
            "cuadros_descartados": self.descartados,
            "cuadros_evaluados": len(puntajes),
            "puntajes_modelo": [round(float(v), 2) for v in puntajes],
            "mediana_modelo": float(np.median(puntajes)) if len(puntajes) else None,
            "porcentaje_falsos": float(np.mean(puntajes < ANTISPOOF_UMBRAL_PANTALLA)) if len(puntajes) else None,
            "moire": float(np.median([p["moire"] for p in pantalla])) if pantalla else None,
            "reflejo": float(np.median([p["reflejo"] for p in pantalla])) if pantalla else None,
            "brillo": float(np.median([c["brillo"] for c in calidades])) if calidades else None,
            "nitidez": float(np.median([c["nitidez"] for c in calidades])) if calidades else None,
            "tamano": float(np.median([c["tamano"] for c in calidades])) if calidades else None,
            "contraluz": float(np.median([c["contraluz"] for c in calidades])) if calidades else None,
        }
        if not ANTISPOOF_ACTIVO:
            return "aceptar", "anti-spoofing desactivado", metricas
        if len(puntajes) < ANTISPOOF_CUADROS_MINIMOS:
            return "dudoso", "pocos cuadros con buena calidad para decidir", metricas

        falsos, mediana = metricas["porcentaje_falsos"], metricas["mediana_modelo"]
        mayoria_falsos = falsos > ANTISPOOF_PORCENTAJE_RECHAZO
        pantalla_evidente = metricas["moire"] > UMBRAL_MOIRE or metricas["reflejo"] > UMBRAL_REFLEJO
        if mayoria_falsos and (mediana < ANTISPOOF_UMBRAL_EVIDENTE or pantalla_evidente):
            return "rechazar", "La imagen parece una foto o una pantalla, no un rostro real.", metricas
        if mayoria_falsos or pantalla_evidente:
            return "dudoso", "señal anti-pantalla débil", metricas
        return "aceptar", "", metricas

    def _repetir_con_otra_accion(self, t):
        """Añade una acción al azar distinta de las ya hechas y vuelve a la fase de lectura."""
        disponibles = [a for a in ACCIONES_ROSTRO if a not in self.acciones
                       and not ({a, *self.acciones} >= {"girar_izquierda", "girar_derecha"})]
        self.acciones.append(random.SystemRandom().choice(disponibles or list(ACCIONES_ROSTRO)))
        self.repetido = True
        self.fase, self.inicio_paso = "verificacion", t
        print(f"[Liveness] Señal anti-pantalla dudosa: se pide una acción más ({self.acciones[-1]}).")
        return ResultadoPaso("continuar", "Verificación adicional", "Mire de frente a la cámara con buena luz.",
                             0.0, fase="verificacion", aviso="Una acción más, por favor")

    def _seguir(self, transcurrido, detalle=""):
        """Estado 'continuar' con los textos y el tiempo de la fase actual."""
        restante, segundos = None, None
        if self.fase == "referencia":
            aviso = "Reconociendo su rostro..."
            progreso = transcurrido / SEGUNDOS_REFERENCIA
        elif self.fase == "lectura":
            cuenta = max(1, int(np.ceil(LIVENESS_TIEMPO_LECTURA - transcurrido)))
            aviso = f"Prepárese... {cuenta}"
            progreso, restante = transcurrido / LIVENESS_TIEMPO_LECTURA, 1.0
            if self.reintentando and not detalle:
                detalle = "No se detectó la acción. Intentémoslo una vez más."
        elif self.fase == "accion":
            aviso = "¡Ahora!"
            progreso = transcurrido / LIVENESS_TIEMPO_ACCION
            restante = max(0.0, 1.0 - progreso)
            segundos = max(0, int(np.ceil(LIVENESS_TIEMPO_ACCION - transcurrido)))
        elif self.fase == "verificacion":
            aviso = "Una acción más, por favor"
            progreso = 1.0
        else:
            aviso = CONFIRMACIONES.get(self.paso, "✔ Acción detectada")
            progreso = 1.0
        return ResultadoPaso("continuar", self.instruccion_actual(), detalle, min(1.0, progreso),
                             fase=self.fase, aviso=aviso, restante=restante, segundos=segundos)

    def _fallo(self, motivo):
        return ResultadoPaso("fallido", self.instruccion_actual(), motivo)


# =====================================================
# POSTURA
# =====================================================

# Índices de PoseNet (sobre la imagen espejada que usa ReconocedorPose)
_NARIZ, _OJO_I, _OJO_D = 0, 1, 2
_HOMBRO_I, _HOMBRO_D, _MUNECA_I, _MUNECA_D = 5, 6, 9, 10


def _visible(p, i):
    from utils.reconocimiento_pose import ReconocedorPose
    return p[i, 2] >= ReconocedorPose.PUNTUACION_MINIMA_KEYPOINT


def _brazo_levantado(p, lado_derecho):
    """
    Solo el brazo pedido levantado: una muñeca por encima de la nariz en ese lado y la otra
    por debajo de los hombros. En la imagen espejada el lado derecho del usuario queda a la
    derecha de la nariz.
    """
    if not all(_visible(p, i) for i in (_NARIZ, _HOMBRO_I, _HOMBRO_D)):
        return False
    hombro_y = (p[_HOMBRO_I, 0] + p[_HOMBRO_D, 0]) / 2
    arriba = [i for i in (_MUNECA_I, _MUNECA_D) if _visible(p, i) and p[i, 0] < p[_NARIZ, 0]
              and (p[i, 1] > p[_NARIZ, 1]) == lado_derecho]
    otra_abajo = [i for i in (_MUNECA_I, _MUNECA_D) if i not in arriba and _visible(p, i) and p[i, 0] > hombro_y]
    return bool(arriba) and bool(otra_abajo)


class DesafioPostura:
    """
    Secuencia: postura neutra -> postura registrada -> movimiento al azar, con tiempo límite
    por paso. Exige movimiento real entre pasos, proporciones estables y el rostro del usuario
    visible y coincidente durante la captura.
    """

    def __init__(self, plantilla=None, embedding_rostro=None, exigir_rostro=True, movimiento=None,
                 semilla=None, candidatos=None):
        rng = random.Random(semilla)
        self.plantilla = plantilla
        self.embedding_rostro = embedding_rostro
        self.exigir_rostro = exigir_rostro
        # Sin usuario escrito: [(datos, plantilla, embedding_rostro)]; se elige por el rostro
        self.candidatos = candidatos or []
        self.usuario = None
        self._rng = rng
        self.pasos = ["neutra", "postura", movimiento]
        if movimiento is None and plantilla is not None:
            self._elegir_movimiento()
        self.indice = 0
        self.inicio_paso = None
        self.estables = 0
        self.muñecas = {}        # posición normalizada de las muñecas al cumplir cada paso
        self.proporciones = []
        self.rostro = []         # similitudes del rostro durante la captura
        self.rostro_visible = 0
        self.cuadros = 0
        self.similitud_postura = 0.0

    @property
    def paso(self):
        return self.pasos[min(self.indice, len(self.pasos) - 1)]

    def _elegir_movimiento(self):
        """Movimiento al azar que la postura registrada no cumpla ya por sí misma."""
        muestra = np.asarray(self.plantilla["muestras"][0], dtype=np.float32).reshape(-1, 3)
        opciones = [m for m in MOVIMIENTOS_POSTURA if not _brazo_levantado(muestra, m == "levantar_derecho")]
        self.pasos[2] = self._rng.choice(opciones or list(MOVIMIENTOS_POSTURA))

    def instruccion_actual(self):
        return INSTRUCCIONES[self.paso]

    def preparar(self):
        """Carga PoseNet y los modelos de rostro (antes de empezar a contar el tiempo)."""
        from services.clasificador_imagen import ClasificadorImagen
        from utils.reconocimiento_pose import ReconocedorPose

        if not ReconocedorPose.cargar_modelo():
            raise RuntimeError(f"No se pudo cargar el modelo de postura: {ReconocedorPose._error_carga}")
        ClasificadorImagen.cargar_detector_facial()
        ClasificadorImagen.cargar_reconocedor_facial()

    def _identificar(self, embedding):
        """Elige entre los candidatos al usuario cuyo rostro coincide mejor."""
        from services.clasificador_imagen import ClasificadorImagen

        mejores = sorted(((ClasificadorImagen.comparar_embeddings(embedding, emb), d, pl, emb)
                          for d, pl, emb in self.candidatos), key=lambda x: x[0], reverse=True)
        if mejores and mejores[0][0] >= UMBRAL_ROSTRO_POSTURA:
            _, self.usuario, self.plantilla, self.embedding_rostro = mejores[0]
            if self.pasos[2] is None:
                self._elegir_movimiento()

    def procesar(self, frame, t=None):
        from utils.reconocimiento_pose import ReconocedorPose
        from utils import detectores_vida as dv
        from utils.plantillas_biometricas import comparar_postura

        t = time.monotonic() if t is None else t
        if self.inicio_paso is None:
            self.inicio_paso = t
        transcurrido = t - self.inicio_paso
        if transcurrido > SEGUNDOS_POR_PASO_POSTURA:
            if self.plantilla is None:
                return self._fallo("No se reconoció su rostro como el de una cuenta con postura registrada.")
            return self._fallo(f"Se acabó el tiempo para: «{self.instruccion_actual()}».")

        self.cuadros += 1
        p = ReconocedorPose._salidas_posenet(frame)[1]   # [17, 3] (y, x, puntuación)

        # Rostro visible y del usuario (cada 2 cuadros para no frenar la captura)
        if self.cuadros % 2 == 1:
            rostros = dv.detectar_rostros(frame)
            if len(rostros) > 1:
                return self._fallo("Se detectó más de una persona. Debe estar solo frente a la cámara.")
            if len(rostros) == 1:
                self.rostro_visible += 1
                emb = dv.embedding_rostro(frame, rostros[0])
                if emb is not None and self.plantilla is None and self.candidatos:
                    self._identificar(emb)
                if emb is not None and self.embedding_rostro is not None:
                    from services.clasificador_imagen import ClasificadorImagen
                    self.rostro.append(ClasificadorImagen.comparar_embeddings(emb, self.embedding_rostro))

        hombros_ok = _visible(p, _HOMBRO_I) and _visible(p, _HOMBRO_D)
        if not hombros_ok or not _visible(p, _NARIZ):
            self.estables = 0
            return self._seguir(transcurrido, "Aléjese: deben verse su cabeza, hombros y brazos.")

        ancho_hombros = abs(p[_HOMBRO_I, 1] - p[_HOMBRO_D, 1]) + 1e-6
        if _visible(p, _OJO_I) and _visible(p, _OJO_D):
            self.proporciones.append(ancho_hombros / (abs(p[_OJO_I, 1] - p[_OJO_D, 1]) + 1e-6))

        if self._paso_cumplido(p, ancho_hombros, comparar_postura):
            self.estables += 1
        else:
            self.estables = 0

        if self.estables >= CUADROS_ESTABLES_POSTURA:
            self.muñecas[self.paso] = self._muñecas(p, ancho_hombros)
            self.indice += 1
            self.estables = 0
            self.inicio_paso = t
            if self.indice >= len(self.pasos):
                return self._veredicto()
            return ResultadoPaso("continuar", self.instruccion_actual(), "", 0.0)
        return self._seguir(transcurrido)

    def _paso_cumplido(self, p, ancho_hombros, comparar_postura):
        hombro_y = (p[_HOMBRO_I, 0] + p[_HOMBRO_D, 0]) / 2
        if self.paso == "neutra":
            # Ambas muñecas visibles por debajo de los hombros
            return all(_visible(p, i) and p[i, 0] > hombro_y + 0.3 * ancho_hombros for i in (_MUNECA_I, _MUNECA_D))
        if self.paso == "postura":
            if self.plantilla is None:
                return False   # aún no se identificó al usuario por su rostro
            self.similitud_postura = comparar_postura([round(float(v), 4) for v in p.reshape(-1)], self.plantilla)
            return self.similitud_postura >= UMBRAL_POSTURA
        return _brazo_levantado(p, self.paso == "levantar_derecho")

    @staticmethod
    def _muñecas(p, ancho):
        centro = (p[_HOMBRO_I, :2] + p[_HOMBRO_D, :2]) / 2
        return (p[[_MUNECA_I, _MUNECA_D], :2] - centro) / ancho

    def _veredicto(self):
        # Movimiento real: las muñecas deben cambiar de lugar entre la postura neutra y las demás
        movimiento = max(float(np.max(np.linalg.norm(self.muñecas[k] - self.muñecas["neutra"], axis=1)))
                         for k in self.pasos[1:])
        proporciones = np.array(self.proporciones)
        variacion = float(proporciones.std() / proporciones.mean()) if len(proporciones) > 2 else 0.0
        rostro_ok = float(np.mean(np.array(self.rostro) >= UMBRAL_ROSTRO_POSTURA)) if self.rostro else 0.0
        print(f"[Liveness] Postura: movimiento {movimiento:.2f}, variación de proporciones {variacion:.2f}, "
              f"rostro visible {self.rostro_visible}, rostro coincide {rostro_ok * 100:.0f}%, "
              f"similitud postura {self.similitud_postura:.2f}")

        if movimiento < MOVIMIENTO_MINIMO:
            return self._fallo("No se detectó movimiento real entre los pasos.")
        if variacion > VARIACION_PROPORCION_MAX:
            return self._fallo("Las proporciones del cuerpo no son coherentes (¿imagen o pantalla?).")
        if self.exigir_rostro:
            if self.rostro_visible == 0:
                return self._fallo("Su rostro debe verse durante la captura de la postura.")
            if self.embedding_rostro is not None and rostro_ok < FRACCION_ROSTRO_POSTURA:
                return self._fallo("El rostro visible no coincide con el de la cuenta.")
        return ResultadoPaso("aprobado", "¡Listo!", "", 1.0, {
            "similitud": self.similitud_postura, "movimiento": self.pasos[2], "usuario": self.usuario,
        })

    def _seguir(self, transcurrido, detalle=""):
        return ResultadoPaso("continuar", self.instruccion_actual(), detalle,
                             min(1.0, transcurrido / SEGUNDOS_POR_PASO_POSTURA))

    def _fallo(self, motivo):
        return ResultadoPaso("fallido", self.instruccion_actual(), motivo)


# =====================================================
# VOZ: DESAFÍO, RECONOCIMIENTO Y CONTROLES DE REPRODUCCIÓN
# =====================================================

NUMEROS = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve")
_modelo_vosk = None


def nuevo_desafio_voz():
    """Números al azar sin repetir el mismo dos veces seguidas (ej. [4, 7, 2])."""
    digitos = []
    while len(digitos) < DIGITOS_DESAFIO:
        d = random.SystemRandom().randrange(10)
        if not digitos or d != digitos[-1]:
            digitos.append(d)
    return digitos


def texto_desafio(digitos):
    return "  -  ".join(str(d) for d in digitos)


def _remuestrear_16k(audio, frecuencia):
    """Baja el audio a 16 kHz (lo que espera Vosk) con un filtro paso bajo previo."""
    audio = np.asarray(audio, dtype=np.float64)
    if frecuencia == 16000:
        return audio
    corte = 7600.0 / frecuencia
    n = np.arange(-64, 65)
    filtro = 2 * corte * np.sinc(2 * corte * n) * np.hamming(len(n))
    filtrado = np.convolve(audio, filtro / filtro.sum(), mode="same")
    tiempos = np.arange(0, len(audio) / frecuencia, 1 / 16000.0)
    return np.interp(tiempos, np.arange(len(audio)) / frecuencia, filtrado)


def reconocer_numeros(audio, frecuencia):
    """
    (Hilo) Reconoce con Vosk los números dichos, con una gramática restringida a los dígitos
    en español (lo demás, como la palabra de ingreso, sale como [unk]).
    Devuelve (dígitos, segundo en que empieza el primer número o None).
    """
    global _modelo_vosk
    import os
    from vosk import KaldiRecognizer, Model, SetLogLevel
    from utils.rutas import ruta_recurso

    if _modelo_vosk is None:
        SetLogLevel(-1)
        ruta = ruta_recurso(os.path.join("models", "vosk", "vosk-model-small-es-0.42"))
        if not os.path.isdir(ruta):
            raise RuntimeError(f"No se encontró el modelo de voz de Vosk en {ruta}.")
        _modelo_vosk = Model(ruta)

    gramatica = json.dumps(list(NUMEROS) + ["un", "[unk]"])
    reconocedor = KaldiRecognizer(_modelo_vosk, 16000, gramatica)
    reconocedor.SetWords(True)
    pcm = (np.clip(_remuestrear_16k(audio, frecuencia), -1, 1) * 32767).astype(np.int16).tobytes()
    reconocedor.AcceptWaveform(pcm)
    resultado = json.loads(reconocedor.FinalResult())
    palabras = [("uno" if w["word"] == "un" else w["word"], w["start"]) for w in resultado.get("result", [])]
    digitos = [(NUMEROS.index(w), inicio) for w, inicio in palabras if w in NUMEROS]
    print(f"[Liveness] Vosk reconoció: '{resultado.get('text', '')}'")
    return [d for d, _ in digitos], (digitos[0][1] if digitos else None)


def indicios_reproduccion(audio, frecuencia):
    """
    Señales de audio reproducido o inyectado. Devuelve un mensaje si hay indicios, o None.
    - Silencio digital exacto: un micrófono real siempre tiene ruido de fondo.
    - Recorte: muchas muestras saturadas (altavoz cerca del micrófono a todo volumen).
    - Espectro recortado: casi sin energía por encima de 6 kHz (altavoz de celular).
    """
    audio = np.asarray(audio, dtype=np.float32)
    ceros = (audio == 0.0).astype(np.int8)
    if ceros.any():
        cambios = np.diff(np.concatenate([[0], ceros, [0]]))
        if (np.where(cambios == -1)[0] - np.where(cambios == 1)[0]).max() >= SILENCIO_DIGITAL_MAX:
            return "El audio contiene silencio digital perfecto (no proviene del micrófono en vivo)."

    pico = float(np.abs(audio).max()) if audio.size else 0.0
    if pico > 0.95 and float(np.mean(np.abs(audio) >= 0.99 * pico)) > FRACCION_RECORTE_MAX:
        return "El audio está saturado. Hable a una distancia normal del micrófono."

    if frecuencia >= 22050:
        espectro = np.abs(np.fft.rfft(audio * np.hanning(audio.size))) ** 2
        frecuencias = np.fft.rfftfreq(audio.size, 1.0 / frecuencia)
        voz = espectro[(frecuencias > 300) & (frecuencias < 3400)].sum() + 1e-12
        agudos = espectro[(frecuencias > 6000) & (frecuencias < 10000)].sum()
        print(f"[Liveness] Agudos/voz: {agudos / voz:.2e} (mínimo {UMBRAL_AGUDOS:.0e})")
        if agudos / voz < UMBRAL_AGUDOS:
            return "El audio no tiene las frecuencias de una voz en vivo (posible reproducción por altavoz)."
    return None


def huellas_audio(audio, frecuencia):
    """
    Huellas para detectar audios repetidos: SHA-256 exacto de las muestras y la envolvente
    de energía del tramo con voz (64 valores), que resiste cambios de volumen y algo de ruido.
    """
    audio = np.asarray(audio, dtype=np.float32)
    exacta = "sha:" + hashlib.sha256(audio.tobytes()).hexdigest()
    return exacta, "env:" + ",".join(f"{v:.2f}" for v in _envolvente(audio, frecuencia))


def _envolvente(audio, frecuencia, puntos=64):
    salto = max(1, int(frecuencia * 0.01))
    energia = np.log10(np.array([np.mean(audio[i:i + salto] ** 2) for i in range(0, audio.size - salto, salto)]) + 1e-10)
    activos = np.where(energia > energia.max() - 3.0)[0]       # tramo con voz (30 dB bajo el pico)
    if activos.size < 2:
        return np.zeros(puntos)
    tramo = energia[activos[0]:activos[-1] + 1]
    tramo = np.interp(np.linspace(0, tramo.size - 1, puntos), np.arange(tramo.size), tramo)
    return (tramo - tramo.mean()) / (tramo.std() + 1e-9)


def audio_repetido(huellas, recientes):
    """True si el audio coincide exactamente o en su envolvente con uno usado antes."""
    exacta, envolvente = huellas
    if exacta in recientes:
        return True
    actual = np.array([float(v) for v in envolvente[4:].split(",")])
    for h in recientes:
        if h.startswith("env:"):
            anterior = np.array([float(v) for v in h[4:].split(",")])
            if anterior.size == actual.size and float(np.mean(actual * anterior)) > CORRELACION_REPETIDO:
                return True
    return False
