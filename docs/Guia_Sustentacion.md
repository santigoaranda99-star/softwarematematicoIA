# Guía de sustentación — Software Matemático IA

**Ingreso biométrico por rostro, voz y postura con Teachable Machine, y empaquetado en .exe**

El software permite iniciar sesión sin contraseña de tres formas: **rostro**, **voz** o **postura**. Usa tres modelos entrenados en Teachable Machine, convertidos a formatos rápidos (ONNX y TFLite) y empaquetados en un `.exe` que no necesita Python instalado.

---

## 1. Arquitectura general

```
┌────────────────────────── INTERFAZ (PyQt5) ───────────────────────────┐
│ login.py  ──►  ingreso_tm.py (identifica la cuenta)                   │
│ registro.py ─►  escaneo_tm.py (abre cámara / micrófono, 3–4 s)        │
└───────────────┬───────────────────────────────┬───────────────────────┘
                │ cuadros de cámara / audio     │ datos del usuario
                ▼                               ▼
┌──────────── MODELOS (services/modelos_tm.py) ─┐   ┌──── BASE DE DATOS ────┐
│ Rostro : MobileNetV2 (.onnx) + onnxruntime    │   │ SQLite                │
│ Voz    : clasificador de audio (.tflite)      │   │ usuarios:             │
│          + LiteRT                             │   │  embedding_facial     │
│ Postura: PoseNet (.onnx) + capa densa (NumPy) │   │  plantilla_voz        │
│ Apoyo  : YuNet + SFace (identidad facial),    │   │  plantilla_postura    │
│          MiniFASNetV2 (anti-suplantación)     │   │  clase_tm_voz / ...   │
└───────────────┬───────────────────────────────┘   └───────────────────────┘
                ▼
      utils/decision_tm.py  →  combina los votos de todos los cuadros → aprueba o rechaza
```

**Idea clave:** no se decide con una sola foto o un solo audio. Se analizan **todos los cuadros** de un escaneo de 3–4 segundos y se decide por **votación** (mayoría + confianza mínima). Eso hace el ingreso más estable y más difícil de engañar.

---

## 2. Librerías y herramientas utilizadas

| Librería / herramienta | Versión | Para qué la usamos |
|---|---|---|
| Python | 3.14 | Lenguaje del proyecto |
| PyQt5 | 5.15.11 | Interfaz gráfica (ventanas, botones, video de la cámara) |
| OpenCV (`opencv-python`) | 5.0 | Cámara, procesamiento de imagen, detector YuNet y reconocedor SFace |
| NumPy | 2.x | Cálculos con matrices, capa densa de postura, red de voz antigua |
| onnxruntime | 1.31.1 | Ejecutar los modelos de rostro y PoseNet en formato ONNX (rápido) |
| ai-edge-litert (LiteRT) | 2.3.0 | Ejecutar el modelo de voz en formato TFLite |
| sounddevice | 0.5.6 | Grabar el micrófono |
| vosk | 0.3.45 | Reconocimiento de voz en español (desafío de números, modo anterior) |
| SQLite (`sqlite3`) | incluida | Base de datos de usuarios y biometría |
| PyInstaller | 6.22.0 | Convertir el proyecto en `.exe` |
| Teachable Machine | web | Entrenar los modelos de imagen, audio y postura |
| TensorFlow + tf2onnx | solo para convertir | Convertir los modelos a ONNX (no van dentro del .exe) |

---

## 3. Paso 1 — Preparar el entorno

1. Clonamos el repositorio:
   ```bash
   git clone https://github.com/santigoaranda99-star/softwarematematicoIA.git
   ```
2. Creamos el entorno virtual con Python 3.14 y lo activamos:
   ```bash
   py -3.14 -m venv venv
   venv\Scripts\activate
   ```
3. Instalamos las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
   Agregamos al `requirements.txt` las dos librerías nuevas de inferencia:
   ```
   onnxruntime==1.31.1
   ai-edge-litert==2.3.0
   ```
4. Copiamos `.env.example` como `.env` y pusimos la clave de la IA (`GROUP_API_KEY`, `GROUP_BASE_URL`, `GROUP_MODEL`).
5. Probamos que abre:
   ```bash
   python main.py
   ```

---

## 4. Paso 2 — Entrenar y exportar los modelos en Teachable Machine

### Configuración de entrenamiento (opciones avanzadas)

| Modelo | Épocas | Batch size | Learning rate | Muestras por clase |
|---|---|---|---|---|
| Imagen (rostro) | 50 | 16 | 0.001 | 300–500, con luz, fondo y ángulo variados |
| Audio (voz) | 50 | 16 | 0.001 | Mínimo 50 clips de 1 s; "Ruido de fondo" 50 o más |
| Postura | 80 | 16 | 0.001 | 300 o más, a distintas distancias de la cámara |

**Reglas que seguimos:**
- La misma cantidad de muestras en todas las clases. Si hay desbalance, el modelo se sesga hacia la clase más grande.
- Siempre una clase de "fondo / nada". Sin ella, el modelo fuerza una predicción aunque no haya nadie.
- No subir el learning rate. Si la pérdida de validación sube mientras la de entrenamiento baja, hay sobreajuste: se bajan las épocas a 30.

### Clases de cada modelo

| Modelo | Clases de personas | Clases sin persona | Clase anti-suplantación |
|---|---|---|---|
| Rostro | mendi, alexa, santi | otros, oscuro, fondo | movil (foto en celular) |
| Voz | alexa, mendi, santi | Ruido de fondo, otros | audio-tel (audio desde teléfono) |
| Postura | Alexa, mendi | fondo, oscuro | — |

### Exportación

| Modelo | Exportar como | Archivo descargado |
|---|---|---|
| Rostro | TensorFlow → **Keras** | `converted_keras.zip` → `keras_model.h5` + `labels.txt` |
| Voz | TensorFlow **Lite** (punto flotante) | `converted_tflite.zip` → `soundclassifier_with_metadata.tflite` + `labels.txt` |
| Postura | **TensorFlow.js** (es la única opción para postura) | `my-pose-model.zip` → `model.json` + `weights.bin` + `metadata.json` |

Descomprimimos cada zip en su carpeta:
```
models/tm_rostro/      keras_model.h5, labels.txt
models/tm_voz/         soundclassifier_with_metadata.tflite, labels.txt
models/my-pose-model/  model.json, weights.bin, metadata.json
```

---

## 5. Paso 3 — Convertir los modelos a ONNX

**¿Por qué ONNX?** Porque onnxruntime es mucho más rápido y liviano que TensorFlow, y así el `.exe` no tiene que incluir TensorFlow (que pesa más de 1 GB y daba errores de DLL).

La conversión se hace **una sola vez**, en un entorno aparte (la app no necesita estas librerías):
```bash
python -m venv C:\tmc
C:\tmc\Scripts\pip install tensorflow tf2onnx onnxruntime h5py
C:\tmc\Scripts\python tools\convertir_modelos_tm.py rostro posenet
```

### 5.1 Rostro: `.h5` → `.onnx`
- El `.h5` de Teachable Machine está guardado con Keras 2.4 y **Keras 3 no lo abre** (error con los modelos anidados).
- Solución: **reconstruimos la misma red** en código: MobileNetV2 (alpha 0.35, 224×224) + GlobalAveragePooling + Dense(100, relu) + Dense(7, softmax).
- Copiamos los **263 pesos** del `.h5` capa por capa con `h5py`, verificando que no faltara ni sobrara ninguno.
- Convertimos con `tf2onnx` y **comparamos las salidas** del ONNX contra el original: diferencia máxima de 0.0000017. Resultado: `models/tm_rostro/modelo.onnx`.

### 5.2 Voz: se queda en `.tflite`
- Intentamos convertirlo a ONNX, pero el modelo trae su propio preprocesamiento con una **FFT** que tf2onnx no soporta.
- Por eso lo ejecutamos directamente como TFLite con **LiteRT** (la otra opción que da la guía). Ventaja: recibe el audio crudo (44 032 muestras a 44,1 kHz ≈ 1 s) y no hay que programar el espectrograma.

### 5.3 Postura: PoseNet → `.onnx` + capa densa en NumPy
- Teachable Machine de postura solo exporta TF.js. Ese modelo tiene dos partes:
  1. **PoseNet** MobileNetV1 0.75 (detecta el cuerpo) → lo convertimos a `models/posenet/posenet_075_stride16.onnx` (diferencia 0.0002).
  2. Una **cabeza densa** pequeña (Dense 100 → Dense 4) que está en `model.json` + `weights.bin` → la leemos y ejecutamos con NumPy.
- La entrada de la cabeza son **14 739 valores**: sigmoid(heatmaps 17×17×17) concatenado con offsets (17×17×34), igual que la librería `@teachablemachine/pose`.

---

## 6. Paso 4 — Cargar los modelos en el software

Creamos `services/modelos_tm.py` con tres clases. Cada modelo se carga **una sola vez** y se reutiliza.

| Clase | Preprocesamiento (igual que Teachable Machine) | Velocidad medida |
|---|---|---|
| `ModeloRostroTM` | Recorte cuadrado central → 224×224 → RGB → valores en [-1, 1] | ~3,5 ms por cuadro |
| `ModeloVozTM` | Audio remuestreado a 44,1 kHz, ventanas de 1 s cada 0,25 s, se descartan las de silencio | ~18 ms por 3 s de audio |
| `ModeloPosturaTM` | Recorte cuadrado → espejo → 257×257 con el bilineal de TF.js → [-1, 1]; además extrae los 17 puntos del cuerpo | ~28 ms por cuadro |

Las librerías se escogen así: si existe `modelo.onnx` se usa **onnxruntime**; si no, el `.tflite` con **LiteRT**.

**Decisión por votación** (`utils/decision_tm.py`):
1. Que haya suficientes muestras válidas (cuadros con cara, ventanas con voz, cuadros con cuerpo).
2. Que no gane la suplantación (`movil`, `audio-tel`).
3. Que gane una **persona**, no fondo ni ruido.
4. Que esa persona tenga mayoría de votos, probabilidad media alta y clara ventaja sobre la segunda.

Todos los umbrales están en `utils/umbrales_biometria.py` (por ejemplo, `UMBRAL_ROSTRO_ESCANEO = 0.80`, `SEGUNDOS_ESCANEO_ROSTRO = 3.5`). Cada escaneo queda anotado en `escaneo_tm.log` para calibrar.

---

## 7. Paso 5 — Iniciar sesión por rostro

**Flujo al pulsar 📷 Rostro:**
1. Se abre la ventana de escaneo (`DialogoEscaneoRostro`) con el video en vivo.
2. Cuando **YuNet** detecta una cara, empieza a contar **3,5 segundos**.
3. En cada cuadro con cara se ejecuta:
   - el modelo de Teachable Machine (¿hay una persona?),
   - **MiniFASNetV2** (¿es una persona real o una foto/pantalla?).
4. De los 5 cuadros más nítidos se extrae el **vector SFace** (128 números que describen la cara).
5. **Quién es** lo decide SFace: compara ese vector con el guardado de cada cuenta y elige la más parecida (umbral 0,35 y ventaja mínima sobre la segunda).
6. Si todo coincide, entra directo al menú principal sin escribir nada.

**Problema que resolvimos:** el modelo de Teachable Machine confundía a Alexa con la clase "movil" y con Mendi. Por eso:
- la detección de celular la hace **MiniFASNetV2** (modelo especializado), no la clase "movil";
- la identidad la decide **SFace**, que distingue muy bien a las personas (Alexa vs Mendi: 10% de parecido; cada una consigo misma: 99%).

---

## 8. Paso 6 — Iniciar sesión por voz

**Flujo al pulsar 🎤 Voz:**
1. Se graban **3 segundos** con un medidor de nivel del micrófono (`DialogoEscaneoVoz`).
2. El usuario dice su **palabra clave secreta**.
3. **Doble verificación:**
   - **Palabra clave:** se calculan los coeficientes **MFCC** del audio y se comparan con **DTW** (alineación dinámica) contra las grabaciones del registro. Eso identifica la cuenta.
   - **Voz:** el modelo de Teachable Machine debe reconocer la misma voz que se registró al vincular.
4. También se rechaza si el modelo detecta `audio-tel` (audio reproducido desde un teléfono).

**Problema que resolvimos:** antes, cualquiera que dijera "mendi" entraba a la cuenta de Mendi, porque el modelo solo tiene 3 opciones y mete cualquier voz en la más parecida. Con la palabra clave secreta, eso ya no pasa:

| Caso | Resultado |
|---|---|
| Mendi dice su palabra clave | ✅ Entra |
| Otra persona dice la palabra de Mendi | ❌ "La voz no corresponde al dueño" |
| Otra persona dice "mendi" | ❌ "La palabra clave no coincide" |

---

## 9. Paso 7 — Iniciar sesión por postura

**Flujo al pulsar 🧍 Postura:**
1. Se abre la cámara y se dibujan **los 17 puntos del cuerpo y el esqueleto** en vivo, como en Teachable Machine, con la clase reconocida arriba (ej.: "Alexa 93%").
2. **3 segundos** para ponerse en posición, luego **4 segundos** de escaneo.
3. Solo cuentan los cuadros donde se ven al menos 7 puntos del cuerpo.
4. Identificación:
   - Si el modelo de Teachable Machine reconoce la postura (Alexa o mendi) → esa cuenta.
   - Si no (un usuario nuevo que no está en el modelo) → se comparan los 17 puntos con la **plantilla** que grabó al registrarse (similitud ≥ 0,70).
5. Si la cuenta tiene rostro guardado, la cara que aparece también debe coincidir (SFace). Así, copiar la postura de otro no basta.

---

## 10. Paso 8 — Crear una cuenta nueva y vincular la biometría

En **Crear una cuenta** y en **🔗 Vincular mi Biometría** usamos los mismos métodos:

| Método | Cómo se registra | Qué se guarda |
|---|---|---|
| Rostro | Escaneo de 3,5 s | Vector SFace (`embedding_facial`) |
| Voz | Palabra clave grabada con **registro adaptativo** | Plantilla MFCC (`plantilla_voz`), hash de la palabra, clase de voz del modelo (`clase_tm_voz`) |
| Postura | Un escaneo de 4 s con puntos en pantalla | Plantilla de 17 puntos (`plantilla_postura`) y clase del modelo si la reconoce (`clase_tm_postura`) |

**Registro adaptativo de voz** (lo hicimos porque la mayoría fallaba al grabar 3 veces igual):
- Cada grabación se valida al momento; si no se oyó bien, se repite **solo esa**.
- Se graba hasta 5 veces y se usan las **3 más parecidas** entre sí (o 2 si no hay 3).
- La palabra no se guarda en texto: solo su **hash con salt** (SHA-256).

**Postura de un usuario nuevo:** el escaneo de 4 s se divide en tres partes, que sirven como las 3 capturas de la plantilla; no hace falta repetir la postura 3 veces.

---

## 11. Paso 9 — Cambios en la base de datos

En `database/crear_bd.py` agregamos una migración (`migrar_usuarios_tm`) que crea las columnas si no existen, sin borrar datos:

| Columna | Contenido |
|---|---|
| `clase_tm_rostro` | Clase del modelo de rostro (informativa) |
| `clase_tm_voz` | Clase con la que el modelo reconoce la voz del usuario |
| `clase_tm_postura` | Clase del modelo de postura, si lo reconoce |

Columnas que ya existían y reutilizamos: `embedding_facial` (SFace), `palabra_ingreso` (hash), `plantilla_voz` y `plantilla_postura` (JSON).

En `controllers/usuario_controller.py` agregamos `guardar_clase_tm()` y `usuarios_por_clase_tm()`.

---

## 12. Paso 10 — Pasar el proyecto a .exe desde cero

1. **Instalamos PyInstaller** (ya viene en `requirements.txt`).
2. **Precarga de `msvcp140.dll`:** copiamos `tools/sitecustomize.py` a `venv/Lib/site-packages/`.
   - **Por qué:** PyQt5 trae una versión vieja de la DLL de Visual C++ (14.26); si se carga primero, onnxruntime se cae. Este archivo hace que siempre se cargue primero la del sistema (14.44), igual que `main.py`.
3. **Configuramos `SoftwareMatematicoIA.spec`:**
   - Modo **carpeta (onedir)**: con un solo archivo, el programa se descomprimiría entero cada vez que se abre y tardaría mucho.
   - Incluimos `images/` y `models/` como datos.
   - Recogemos las DLL de `onnxruntime`, `ai_edge_litert`, `vosk` y `_sounddevice_data`.
   - **Excluimos TensorFlow y Keras**: ya no se usan, porque los modelos antiguos de la sección Clases también se pasaron a NumPy y ONNX.
   - **Quitamos las DLL viejas de Visual C++ de PyQt5**: el `.exe` se cerraba al abrir (error 0xC0000005).
   - UPX desactivado, porque comprime y daña las DLL.
4. **Compilamos:**
   ```bash
   venv\Scripts\python.exe -m PyInstaller SoftwareMatematicoIA.spec --noconfirm
   ```
5. **Copiamos junto al `.exe`** la base de datos (`software_matematico.db`) y el `.env`.
6. **Probamos** con la autoprueba integrada:
   ```bash
   dist\SoftwareMatematicoIA\SoftwareMatematicoIA.exe --autoprueba
   ```
   Genera `autoprueba.txt` con 10 comprobaciones: los modelos de rostro, voz y postura, YuNet + SFace, la anti-suplantación, los modelos de Clases, el micrófono, la cámara, Vosk y la base de datos.

**Resultado:** carpeta `dist/SoftwareMatematicoIA/` de **576 MB** con `SoftwareMatematicoIA.exe`. Para llevarlo a otra PC se copia la carpeta completa.

---

## 13. Archivos nuevos y modificados

| Archivo | Qué hace |
|---|---|
| `services/modelos_tm.py` | Carga y ejecuta los 3 modelos (rostro ONNX, voz TFLite, postura ONNX + NumPy) |
| `interfaces/escaneo_tm.py` | Ventanas de escaneo: cámara con video, puntos del cuerpo, micrófono con medidor |
| `interfaces/ingreso_tm.py` | Identifica la cuenta en el login; registro y vinculación de rostro, voz y postura |
| `utils/decision_tm.py` | Votación, anti-suplantación y registro `escaneo_tm.log` |
| `utils/umbrales_biometria.py` | Todos los umbrales y tiempos |
| `utils/plantillas_biometricas.py` | Plantillas de voz (MFCC + DTW) y de postura; registro adaptativo |
| `utils/modelos_tfjs.py` | Lee modelos TF.js y ejecuta la cabeza densa con NumPy |
| `utils/reconocimiento_voz.py`, `reconocimiento_pose.py` | Modelos de la sección Clases, ahora sin TensorFlow |
| `interfaces/login.py`, `registro.py` | Botones conectados al ingreso rápido |
| `database/crear_bd.py`, `controllers/usuario_controller.py` | Columnas y consultas nuevas |
| `tools/convertir_modelos_tm.py` | Conversión de modelos a ONNX con verificación |
| `tools/sitecustomize.py` | Precarga de la DLL para compilar |
| `SoftwareMatematicoIA.spec` | Configuración del `.exe` |
| `main.py` | Precarga de DLL y opción `--autoprueba` |

---

## 14. Preguntas probables del jurado

**¿Por qué no usaron directamente el modelo de Teachable Machine para todo?**
Porque con pocas clases confunde a personas parecidas (le pasó con Alexa y Mendi). Lo usamos para detectar que hay una persona real y para la postura. La identidad facial la confirma SFace, que es un reconocedor facial especializado.

**¿Por qué ONNX y no TensorFlow?**
Es más rápido (3,5 ms por cuadro en rostro), más liviano y no trae los conflictos de DLL de TensorFlow. Además, permitió que el `.exe` pesara 576 MB en vez de más de 1,5 GB.

**¿Cómo evitan que alguien entre con una foto o un audio grabado?**
- Rostro: MiniFASNetV2 detecta fotos y pantallas.
- Voz: la clase `audio-tel` detecta audio reproducido desde un teléfono.
- Además, se analizan muchos cuadros durante varios segundos, no una sola imagen.

**¿Qué pasa si alguien dice el nombre de otro usuario?**
No entra. Hace falta la palabra clave secreta, y además el modelo tiene que reconocer la voz del dueño.

**¿Cómo funciona la postura con un usuario que no está en el modelo?**
Se guardan los 17 puntos de su cuerpo al registrarse y se comparan al entrar (similitud ≥ 70%). Si tiene rostro guardado, también se verifica la cara.

**¿Dónde se guardan los datos biométricos? ¿Son seguros?**
En SQLite, como vectores numéricos y plantillas (no como fotos ni audios). La palabra clave se guarda como hash con salt, nunca en texto.

**¿Por qué el .exe es una carpeta y no un solo archivo?**
Con un solo archivo, cada vez que se abre tendría que descomprimir cientos de MB en una carpeta temporal y tardaría mucho más en arrancar.

**¿Cómo comprueban que el .exe funciona en otra computadora?**
Con `SoftwareMatematicoIA.exe --autoprueba`, que revisa los modelos, la cámara, el micrófono y la base de datos, y deja el resultado en `autoprueba.txt`.

**¿Cómo se ajusta si reconoce mal?**
Los umbrales están centralizados en `utils/umbrales_biometria.py`, y cada intento queda en `escaneo_tm.log` con los votos de cada clase. Si el problema es del modelo, se reentrena en Teachable Machine con más muestras balanceadas y se vuelve a convertir con `tools/convertir_modelos_tm.py`.
