"""
Convierte las exportaciones de Teachable Machine a ONNX para el ingreso rápido.

    Imagen: "TensorFlow → Keras"            → models/tm_rostro/keras_model.h5
    Audio:  "TensorFlow Lite (punto flotante)" → models/tm_voz/soundclassifier_with_metadata.tflite

Uso (en un entorno aparte, la app no necesita estas librerías):
    python -m venv C:\\tmc
    C:\\tmc\\Scripts\\pip install tensorflow tf2onnx onnxruntime h5py
    C:\\tmc\\Scripts\\python tools\\convertir_modelos_tm.py [rostro] [voz] [posenet]

La postura de Teachable Machine solo se exporta como TF.js (model.json + weights.bin en
models/my-pose-model): esa cabeza se lee directamente en Python y solo PoseNet se convierte.

Genera modelo.onnx junto a cada original y compara las salidas con el modelo de origen;
si alguna conversión no coincide, no se escribe ese .onnx (la app usará el original).
Hoy la voz no se puede convertir (tf2onnx no soporta la RFFT de su preprocesamiento) y la
app la ejecuta directamente como .tflite con LiteRT: ese fallo es esperado.
"""
import os
import sys

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import onnxruntime as ort
import tensorflow as tf
import tf2onnx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_ROSTRO = os.path.join(RAIZ, "models", "tm_rostro")
DIR_VOZ = os.path.join(RAIZ, "models", "tm_voz")
DIR_POSENET = os.path.join(RAIZ, "models", "posenet", "mobilenet_075_stride16")
TOLERANCIA = 1e-3


def _guardar_si_coincide(modelo_onnx, destino, entradas, referencia):
    sesion = ort.InferenceSession(modelo_onnx.SerializeToString(), providers=["CPUExecutionProvider"])
    nombre = sesion.get_inputs()[0].name
    salida = np.concatenate([sesion.run(None, {nombre: x[None]})[0] for x in entradas])
    diferencia = float(np.abs(salida - referencia).max())
    print(f"  diferencia máxima con el original: {diferencia:.2e}")
    if diferencia > TOLERANCIA:
        print("  ❌ No coincide: no se guarda el .onnx")
        return False
    with open(destino, "wb") as f:
        f.write(modelo_onnx.SerializeToString())
    print(f"  ✅ {destino}")
    return True


def reconstruir_rostro():
    """
    Keras 3 no abre el .h5 de Teachable Machine (Keras 2.4, modelos anidados), así que se
    reconstruye la misma red — MobileNetV2 alpha 0.35 + promedio global + Dense(100) +
    Dense(clases) — y se copian los pesos del .h5 capa por capa, verificando que no falte
    ni sobre ninguno.
    """
    import json
    import h5py
    import keras

    ruta = os.path.join(DIR_ROSTRO, "keras_model.h5")
    with h5py.File(ruta, "r") as f:
        pesos = {}
        f["model_weights"].visititems(
            lambda n, o: pesos.__setitem__(n, o[()]) if isinstance(o, h5py.Dataset) else None)
        config = json.loads(f.attrs["model_config"])
    cabeza = config["config"]["layers"][-1]["config"]["layers"]
    densas = [c["config"] for c in cabeza if c["class_name"] == "Dense"]

    base = keras.applications.MobileNetV2(input_shape=(224, 224, 3), alpha=0.35,
                                          include_top=False, weights=None)
    x = keras.layers.GlobalAveragePooling2D()(base.output)
    for d in densas:
        x = keras.layers.Dense(d["units"], activation=d["activation"], use_bias=d["use_bias"],
                               name=d["name"])(x)
    modelo = keras.Model(base.input, x)

    usados = set()
    for capa in modelo.layers:
        if not capa.weights:
            continue
        valores = []
        for w in capa.weights:
            grupo = "sequential_15" if capa.name.startswith("dense_") else "sequential_13"
            nombre = w.name.split("/")[-1]
            if isinstance(capa, keras.layers.DepthwiseConv2D) and nombre == "kernel":
                nombre = "depthwise_kernel"   # así se llama en Keras 2
            clave = f"{grupo}/{capa.name}/{nombre}:0"
            if clave not in pesos or pesos[clave].shape != tuple(w.shape):
                raise ValueError(f"Peso faltante o de otra forma: {clave}")
            valores.append(pesos[clave])
            usados.add(clave)
        capa.set_weights(valores)
    if len(usados) != len(pesos):
        raise ValueError(f"Quedaron pesos sin usar: {sorted(set(pesos) - usados)[:5]}")
    print(f"  {len(usados)} pesos copiados del .h5")
    return modelo


def convertir_rostro():
    print("Rostro (Keras .h5 → ONNX)")
    modelo = reconstruir_rostro()
    firma = [tf.TensorSpec((None, 224, 224, 3), tf.float32, name="imagen")]
    funcion = tf.function(lambda imagen: modelo(imagen, training=False))
    modelo_onnx, _ = tf2onnx.convert.from_function(funcion, input_signature=firma, opset=17)

    entradas = np.random.default_rng(0).uniform(-1, 1, (4, 224, 224, 3)).astype(np.float32)
    referencia = modelo.predict(entradas, verbose=0)
    return _guardar_si_coincide(modelo_onnx, os.path.join(DIR_ROSTRO, "modelo.onnx"), entradas, referencia)


def convertir_voz():
    print("Voz (TFLite → ONNX)")
    ruta = os.path.join(DIR_VOZ, "soundclassifier_with_metadata.tflite")
    modelo_onnx, _ = tf2onnx.convert.from_tflite(ruta, opset=17)

    interprete = tf.lite.Interpreter(model_path=ruta)
    interprete.allocate_tensors()
    ent, sal = interprete.get_input_details()[0], interprete.get_output_details()[0]
    t = np.arange(44032) / 44100.0
    rng = np.random.default_rng(0)
    entradas = np.stack([
        0.3 * np.sin(2 * np.pi * 220 * t) + 0.05 * rng.standard_normal(44032),
        0.1 * rng.standard_normal(44032),
        0.5 * np.sin(2 * np.pi * 440 * t) * np.sin(2 * np.pi * 3 * t),
    ]).astype(np.float32)
    referencia = []
    for x in entradas:
        interprete.set_tensor(ent["index"], x[None])
        interprete.invoke()
        referencia.append(interprete.get_tensor(sal["index"])[0])
    return _guardar_si_coincide(modelo_onnx, os.path.join(DIR_VOZ, "modelo.onnx"), entradas, np.stack(referencia))


def convertir_posenet():
    """
    PoseNet MobileNetV1 0.75 (el mismo que usa Teachable Machine para postura) de SavedModel a
    ONNX, para clasificar posturas con onnxruntime sin TensorFlow. Salidas: heatmap y offsets.
    """
    print("PoseNet (SavedModel → ONNX)")
    posenet = tf.saved_model.load(DIR_POSENET)
    firma = [tf.TensorSpec((1, 257, 257, 3), tf.float32, name="imagen")]
    funcion = tf.function(lambda imagen: posenet.signatures["serving_default"](imagen=imagen))
    modelo_onnx, _ = tf2onnx.convert.from_function(funcion, input_signature=firma, opset=17,
                                                   output_path=None)

    sesion = ort.InferenceSession(modelo_onnx.SerializeToString(), providers=["CPUExecutionProvider"])
    nombres = [s.name for s in sesion.get_outputs()]
    diferencia = 0.0
    for x in np.random.default_rng(0).uniform(-1, 1, (3, 1, 257, 257, 3)).astype(np.float32):
        ref = posenet.signatures["serving_default"](imagen=tf.constant(x))
        salida = dict(zip(nombres, sesion.run(None, {sesion.get_inputs()[0].name: x})))
        for clave in ("heatmap", "offsets"):
            onnx_valor = next(v for n, v in salida.items() if clave in n)
            diferencia = max(diferencia, float(np.abs(onnx_valor - ref[clave].numpy()).max()))
    print(f"  salidas {nombres}, diferencia máxima con el original: {diferencia:.2e}")
    if diferencia > TOLERANCIA:
        print("  ❌ No coincide: no se guarda el .onnx")
        return False
    destino = os.path.join(os.path.dirname(DIR_POSENET), "posenet_075_stride16.onnx")
    with open(destino, "wb") as f:
        f.write(modelo_onnx.SerializeToString())
    print(f"  ✅ {destino}")
    return True


if __name__ == "__main__":
    todos = {"rostro": convertir_rostro, "voz": convertir_voz, "posenet": convertir_posenet}
    elegidos = sys.argv[1:] or list(todos)
    resultados = []
    for convertir in (todos[n] for n in elegidos):
        try:
            resultados.append(convertir())
        except Exception as error:
            print(f"  ❌ Error: {error}")
            resultados.append(False)
    sys.exit(0 if all(resultados) else 1)
