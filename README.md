# Software Matemático IA

Aplicación de escritorio en **Python + PyQt5** que resuelve problemas matemáticos con **Inteligencia Artificial** (API compatible con OpenAI, por defecto Groq). Permite escribir el problema, cargarlo como imagen o capturarlo con la cámara, muestra el procedimiento paso a paso, verifica resultados con **SymPy** y guarda el historial por usuario en **SQLite**.

## Funcionalidades

- Pantalla de bienvenida (Splash) con transición automática al login.
- Registro e inicio de sesión con contraseñas protegidas (hash SHA-256 con salt).
- Panel principal con estadísticas y tarjetas de navegación.
- Resolución de problemas por texto, por imagen cargada y por fotografía (cámara).
- Validación matemática automática con SymPy (expresiones y ecuaciones simples).
- Historial por usuario con **procedimiento** y **resultado** separados.
- Manejo diferenciado de errores de la API (clave inválida, modelo inexistente, sin conexión, timeout, límites).
- Ingreso rápido por rostro (escaneo de 3,5 s), voz (3 s) y postura (4 s) con modelos de Teachable Machine.

## Ingreso rápido por rostro, voz y postura

- **Rostro:** `models/tm_rostro/` (export Keras convertido a ONNX, se ejecuta con onnxruntime).
  Teachable Machine confirma que hay una persona; quién es lo decide SFace, y el celular/foto
  se detecta con MiniFASNetV2.
- **Voz:** `models/tm_voz/` (export TensorFlow Lite, se ejecuta con LiteRT). Doble verificación:
  la palabra clave secreta del usuario (grabada 3 veces) y que el modelo reconozca su voz.
- **Postura:** `models/my-pose-model/` (export TF.js) sobre PoseNet convertido a ONNX
  (`models/posenet/posenet_075_stride16.onnx`). Si la cuenta tiene rostro, la cara también se
  confirma con SFace.
- Cada cuenta se vincula una vez en **🔗 Vincular mi Biometría**; luego basta con pulsar
  📷 Rostro o 🎤 Voz en el inicio de sesión.
- Umbrales y tiempos: `utils/umbrales_biometria.py`. Cada escaneo se anota en `escaneo_tm.log`.
- Al reentrenar el modelo de imagen, reemplace `models/tm_rostro/keras_model.h5` y `labels.txt`
  y ejecute `tools/convertir_modelos_tm.py` (instrucciones dentro del archivo).

## Requisitos

- Python 3.12 o superior (3.14 recomendado).
- Conexión a Internet (para la IA).
- Cámara web opcional.

## Instalación

```bash
# Crear el entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración del archivo `.env`

Copie `.env.example` como `.env` y complete los valores:

```dotenv
GROUP_API_KEY=su_clave_real
GROUP_BASE_URL=https://api.groq.com/openai/v1
GROUP_MODEL=qwen/qwen3.6-27b
```

| Variable           | Descripción                                            | Ejemplo                          |
| ------------------ | ------------------------------------------------------ | -------------------------------- |
| `GROUP_API_KEY`    | Clave de acceso a la API de su proveedor              | `gsk_...`                        |
| `GROUP_BASE_URL`   | URL base compatible con OpenAI                         | `https://api.groq.com/openai/v1` |
| `GROUP_MODEL`      | Modelo a utilizar (texto e imagen)                     | `qwen/qwen3.6-27b`               |

> La clave **nunca** se sube al repositorio: `.env` está en `.gitignore`.

## Ejecución

```bash
python main.py
```

O bien, si el usuario no tiene Python instalado, usar el ejecutable (ver abajo).

## Generar el ejecutable (.exe)

Antes de la primera compilación, copie `tools/sitecustomize.py` a `venv/Lib/site-packages/`
(evita que el análisis de PyInstaller se caiga por el conflicto de `msvcp140.dll` con PyQt5).

```bash
venv\Scripts\python.exe -m PyInstaller SoftwareMatematicoIA.spec --noconfirm
```

Se genera la carpeta `dist/SoftwareMatematicoIA/` con `SoftwareMatematicoIA.exe` y la carpeta
`_internal` (librerías, imágenes y modelos). No necesita Python ni TensorFlow.

**Importante al distribuir:**

- Copie la carpeta completa `dist/SoftwareMatematicoIA/`, no solo el `.exe`.
- Ponga en esa carpeta el `.env` (con `GROUP_API_KEY`, `GROUP_BASE_URL` y `GROUP_MODEL`).
- La base de datos `software_matematico.db` se lee/crea junto al ejecutable. Para conservar
  las cuentas ya registradas, copie ahí la de `database/`.
- Para comprobar el ejecutable en otra computadora: `SoftwareMatematicoIA.exe --autoprueba`
  escribe `autoprueba.txt` con el estado de los modelos, la cámara, el micrófono y la base de datos.

## Estructura del proyecto

```
controllers/   Lógica de negocio (usuarios, historial)
database/      Conexión, creación de tablas y migraciones SQLite
interfaces/    Pantallas PyQt5 (splash, login, registro, menú, resolver, cámara, historial, información)
models/        Modelos de datos (Usuario, Historial)
services/      IAService (cliente de la API de IA)
utils/         Configuración, validaciones, seguridad, rutas, parsing y validación matemática
docs/          Documentación (técnica y manual de usuario)
main.py        Punto de entrada
SoftwareMatematicoIA.spec  Especificación de PyInstaller (versionada para reproducir el build)
```

## Documentación

- `docs/Documento_Tecnico.docx` — documento técnico completo.
- `docs/Manual_Usuario.docx` — manual paso a paso para el usuario final.
