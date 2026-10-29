"""
Decisión del ingreso rápido: combina las predicciones de varios cuadros (rostro) o ventanas
(voz) de Teachable Machine en un solo veredicto. Es lógica pura (sin Qt ni modelos) para
poder probarla aparte.

Reglas, en orden:
1. Suficientes muestras válidas.
2. Suplantación: si "movil" / "audio-tel" es mayoría o supera a la persona, se rechaza.
3. Debe haber una persona: la clase ganadora no puede ser fondo, ruido ni "otros".
4. La persona ganadora necesita mayoría de votos, una probabilidad media alta y clara
   ventaja sobre la segunda persona más votada.
"""
import json
import os
import time
from dataclasses import dataclass, field

import numpy as np

ARCHIVO_LOG = "escaneo_tm.log"   # una línea JSON por escaneo, para calibrar umbrales


def evaluar_antispoof(reales, pantallas):
    """
    Celular o foto con MiniFASNetV2 y las heurísticas de pantalla, con los mismos umbrales
    calibrados de la prueba de vida (utils/liveness.py). Solo rechaza cuando la mayoría de
    cuadros parecen falsos Y la señal es evidente, para no rechazar a personas reales.
    """
    from utils import liveness as L

    if not reales:
        return {}
    puntajes = np.asarray(reales, dtype=np.float32)
    falsos = float(np.mean(puntajes < L.ANTISPOOF_UMBRAL_PANTALLA))
    mediana = float(np.median(puntajes))
    moire = float(np.median([p["moire"] for p in pantallas]))
    reflejo = float(np.median([p["reflejo"] for p in pantallas]))
    evidente = mediana < L.ANTISPOOF_UMBRAL_EVIDENTE or moire > L.UMBRAL_MOIRE or reflejo > L.UMBRAL_REFLEJO
    return {"rechazar": bool(falsos > L.ANTISPOOF_PORCENTAJE_RECHAZO and evidente),
            "falsos": round(falsos, 2), "mediana": round(mediana, 2),
            "moire": round(moire, 3), "reflejo": round(reflejo, 3)}


def registrar_escaneo(que, veredicto, **extra):
    """Anota el resultado y los votos por clase de un escaneo (junto a la base de datos)."""
    from utils.rutas import es_ejecutable, ruta_base

    carpeta = ruta_base() if es_ejecutable() else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    linea = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "tipo": que, "aprobado": veredicto.aprobado,
             "clase": veredicto.clase, "confianza": round(veredicto.confianza, 3),
             "votos": round(veredicto.votos, 3), "conteo": veredicto.conteo, "motivo": veredicto.motivo, **extra}
    try:
        with open(os.path.join(carpeta, ARCHIVO_LOG), "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    except OSError:
        pass


@dataclass
class Veredicto:
    aprobado: bool
    clase: str = ""
    confianza: float = 0.0      # probabilidad media de la clase en los cuadros que la votaron
    votos: float = 0.0          # fracción de muestras que votaron por la clase
    motivo: str = ""
    conteo: dict = field(default_factory=dict)


def decidir(probabilidades, etiquetas, clases_persona, clases_suplantacion,
            umbral, votos_minimos, muestras_minimas, fraccion_suplantacion, que="rostro",
            contar_sin_persona=True):
    probabilidades = np.asarray(probabilidades, dtype=np.float32)
    n = len(probabilidades)
    if n < muestras_minimas:
        detalle = ("No se vio su rostro el tiempo suficiente. Mire de frente a la cámara, "
                   "con buena luz, durante todo el escaneo." if que == "rostro" else
                   "No se escuchó su voz el tiempo suficiente. Hable cerca del micrófono "
                   "durante la grabación.")
        return Veredicto(False, motivo=detalle)

    ganadores = probabilidades.argmax(axis=1)
    conteo = {}
    for i in ganadores:
        conteo[etiquetas[i]] = conteo.get(etiquetas[i], 0) + 1

    suplantacion = {c.lower() for c in clases_suplantacion}
    personas = {c.lower() for c in clases_persona}
    votos_falsos = sum(v for c, v in conteo.items() if c.lower() in suplantacion)
    votos_persona = {c: v for c, v in conteo.items() if c.lower() in personas}
    mejor_persona = max(votos_persona.values(), default=0)

    # Voz: las ventanas de silencio/ruido entre palabras no cuentan en contra (solo se mide
    # entre las que sí sonaron a persona o a teléfono). Rostro: todo cuadro con cara cuenta.
    base = n if contar_sin_persona else max(1, sum(votos_persona.values()) + votos_falsos)

    # Suplantación solo si es mayoritaria o supera a la persona: unos pocos cuadros
    # confundidos con "movil" no bastan para rechazar a alguien real.
    if votos_falsos and (votos_falsos / base >= fraccion_suplantacion or votos_falsos > mejor_persona):
        detalle = ("⚠️ Se detectó la pantalla de un celular o una foto. Debe estar usted en persona "
                   "frente a la cámara." if que == "rostro" else
                   "⚠️ Se detectó un audio reproducido desde un teléfono o parlante. Hable usted "
                   "directamente al micrófono.")
        return Veredicto(False, motivo=detalle, conteo=conteo)

    if not votos_persona:
        if que == "rostro" and max(conteo, key=conteo.get).lower() in ("oscuro", "fondo oscuro"):
            return Veredicto(False, motivo="La imagen está muy oscura. Encienda una luz frente a su "
                                           "rostro e intente de nuevo.", conteo=conteo)
        detalle = ("No se reconoció a ningún usuario frente a la cámara." if que == "rostro" else
                   "No se reconoció la voz de ningún usuario registrado.")
        return Veredicto(False, motivo=detalle, conteo=conteo)

    clase = max(votos_persona, key=votos_persona.get)
    indice = etiquetas.index(clase)
    filas = probabilidades[ganadores == indice]
    confianza = float(filas[:, indice].mean())
    votos = votos_persona[clase] / base
    segundo = sorted(votos_persona.values(), reverse=True)[1] if len(votos_persona) > 1 else 0

    if votos < votos_minimos or confianza < umbral or segundo > 0.5 * votos_persona[clase]:
        return Veredicto(False, clase, confianza, votos, (
            f"El reconocimiento no fue concluyente ({votos * 100:.0f}% de coincidencia, "
            f"confianza {confianza * 100:.0f}%). "
            + ("Quédese quieto, de frente y con buena luz, e intente de nuevo." if que == "rostro"
               else "Hable claro y sin ruido alrededor, e intente de nuevo.")
        ), conteo)

    return Veredicto(True, clase, confianza, votos, "", conteo)
