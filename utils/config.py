import os

try:
    from dotenv import load_dotenv
    DOTENV_DISPONIBLE = True
except ImportError:
    DOTENV_DISPONIBLE = False

from utils.rutas import ruta_base

# Ruta raíz del proyecto (o del ejecutable si está empaquetado)
BASE_DIR = ruta_base()

# Ruta del archivo .env en la raíz (o junto al ejecutable)
RUTA_ENV = os.path.join(BASE_DIR, ".env")


def cargar_archivo_env():
    """
    Carga las variables definidas en el archivo .env de la raíz
    del proyecto (sin sobrescribir variables del sistema).
    Usa python-dotenv si está instalado; si no, usa un lector mínimo.
    """
    if DOTENV_DISPONIBLE:
        load_dotenv(RUTA_ENV, override=False)
        return

    if not os.path.exists(RUTA_ENV):
        return

    with open(RUTA_ENV, "r", encoding="utf-8") as archivo:

        for linea in archivo:

            linea = linea.strip()

            if not linea or linea.startswith("#") or "=" not in linea:
                continue

            clave, _, valor = linea.partition("=")

            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")

            if clave and clave not in os.environ:
                os.environ[clave] = valor


def obtener_variable(nombre, valor_por_defecto=""):
    """
    Devuelve una variable de entorno o el valor por defecto.

    Una variable vacía o de solo espacios NO se considera un valor
    válido y devuelve el valor por defecto.
    """
    valor = os.getenv(nombre)

    if valor is None:
        return valor_por_defecto

    valor = valor.strip()

    return valor or valor_por_defecto


# Cargar el .env al importar este módulo
cargar_archivo_env()


# =====================================================
# CONFIGURACIÓN DE LA IA (Group API Key)
# =====================================================

# Clave de acceso a la API (nunca se escribe en el código)
GROUP_API_KEY = obtener_variable("GROUP_API_KEY")

# URL base del proveedor (compatible con el estándar OpenAI)
GROUP_BASE_URL = obtener_variable(
    "GROUP_BASE_URL",
    ""
)

# Modelo a utilizar (configurable según el proveedor)
GROUP_MODEL = obtener_variable(
    "GROUP_MODEL",
    "gpt-4o-mini"
)


def guardar_configuracion_env(api_key=None, base_url=None, modelo=None):
    """
    Guarda las variables de configuración en el archivo .env y actualiza
    el entorno en memoria y las variables globales del módulo.
    """
    global GROUP_API_KEY, GROUP_BASE_URL, GROUP_MODEL

    rutas = [RUTA_ENV]
    # Si existe una carpeta dist con .env, mantenerla sincronizada
    ruta_dist_env = os.path.join(BASE_DIR, "dist", ".env")
    if os.path.exists(os.path.join(BASE_DIR, "dist")):
        rutas.append(ruta_dist_env)

    nuevos_valores = {}
    if api_key is not None:
        nuevos_valores["GROUP_API_KEY"] = api_key.strip()
    if base_url is not None:
        nuevos_valores["GROUP_BASE_URL"] = base_url.strip()
    if modelo is not None:
        nuevos_valores["GROUP_MODEL"] = modelo.strip()

    for ruta in set(rutas):
        lineas = []
        claves_encontradas = set()

        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                for linea in f:
                    linea_strip = linea.strip()
                    if (
                        linea_strip
                        and not linea_strip.startswith("#")
                        and "=" in linea_strip
                    ):
                        clave, _, _ = linea_strip.partition("=")
                        clave = clave.strip()
                        if clave in nuevos_valores:
                            lineas.append(f"{clave}={nuevos_valores[clave]}\n")
                            claves_encontradas.add(clave)
                            continue
                    lineas.append(linea)
        else:
            lineas.append("# =====================================================\n")
            lineas.append("# Configuración de la Inteligencia Artificial\n")
            lineas.append("# =====================================================\n\n")

        for clave, valor in nuevos_valores.items():
            if clave not in claves_encontradas:
                lineas.append(f"{clave}={valor}\n")

        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.writelines(lineas)
        except Exception:
            pass

    # Actualizar os.environ y globales
    for clave, valor in nuevos_valores.items():
        os.environ[clave] = valor

    if api_key is not None:
        GROUP_API_KEY = nuevos_valores["GROUP_API_KEY"]
    if base_url is not None:
        GROUP_BASE_URL = nuevos_valores["GROUP_BASE_URL"]
    if modelo is not None:
        GROUP_MODEL = nuevos_valores["GROUP_MODEL"]

