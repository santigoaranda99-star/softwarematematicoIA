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

```bash
pyinstaller SoftwareMatematicoIA.spec --noconfirm
```

El ejecutable se genera en `dist/SoftwareMatematicoIA.exe`.

**Importante al distribuir el .exe:**

- Copie el `.exe` junto con un archivo `.env` (con `GROUP_API_KEY`, `GROUP_BASE_URL` y `GROUP_MODEL`) en la misma carpeta.
- La base de datos `software_matematico.db` se crea automáticamente junto al ejecutable la primera vez que se abre.
- La carpeta `images/` se incluye dentro del ejecutable (no hace falta copiarla).

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
