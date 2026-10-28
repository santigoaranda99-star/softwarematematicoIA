import os
import json
import numpy as np


def leer_modelo_tfjs(directorio):
    """
    Lee un layers_model exportado por TensorFlow.js (model.json + weights.bin).
    Devuelve (topologia, pesos) donde pesos es un dict nombre -> np.ndarray.
    """
    with open(os.path.join(directorio, "model.json"), "r", encoding="utf-8") as f:
        datos = json.load(f)

    pesos = {}
    for grupo in datos["weightsManifest"]:
        buffer = b""
        for ruta in grupo["paths"]:
            with open(os.path.join(directorio, ruta), "rb") as f:
                buffer += f.read()

        offset = 0
        for w in grupo["weights"]:
            dtype = np.dtype(w.get("dtype", "float32"))
            cantidad = int(np.prod(w["shape"])) if w["shape"] else 1
            pesos[w["name"]] = np.frombuffer(buffer, dtype, cantidad, offset).reshape(w["shape"])
            offset += cantidad * dtype.itemsize

    return datos["modelTopology"], pesos


def leer_metadata(directorio):
    """Lee metadata.json de Teachable Machine."""
    with open(os.path.join(directorio, "metadata.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def resolver_etiqueta(etiquetas_validas, etiqueta_vinculada="", *identificadores):
    """
    Devuelve la etiqueta del modelo que corresponde a un usuario, o None.

    Prioriza la etiqueta vinculada en la BD; si no hay (o ya no existe en el modelo),
    busca coincidencia exacta con el usuario o con la primera palabra del nombre.
    La comparación ignora mayúsculas porque cada modelo escribe las clases distinto.
    """
    por_minusculas = {e.strip().lower(): e for e in etiquetas_validas}

    vinculada = (etiqueta_vinculada or "").strip().lower()
    if vinculada in por_minusculas:
        return por_minusculas[vinculada]

    for ident in identificadores:
        ident = (ident or "").strip().lower()
        if not ident:
            continue
        for candidato in (ident, ident.split()[0]):
            if candidato in por_minusculas:
                return por_minusculas[candidato]
    return None
