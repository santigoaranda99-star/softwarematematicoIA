import base64
import re
from urllib.parse import urlparse

import requests

from utils.config import (
    GROUP_API_KEY,
    GROUP_BASE_URL,
    GROUP_MODEL
)


class IAService:
    """Servicio de IA que consulta un proveedor compatible con OpenAI (Groq)."""

    def __init__(self, api_key=None, base_url=None, modelo=None):
        """Carga la configuración de la IA desde parámetros o variables de entorno."""
        import os
        import utils.config as cfg

        self.api_key = (
            api_key
            if api_key is not None
            else (os.getenv("GROUP_API_KEY") or cfg.GROUP_API_KEY or "")
        ).strip()

        self.base_url = (
            base_url
            if base_url is not None
            else (os.getenv("GROUP_BASE_URL") or cfg.GROUP_BASE_URL or "")
        ).strip()

        self.modelo = (
            modelo
            if modelo is not None
            else (os.getenv("GROUP_MODEL") or cfg.GROUP_MODEL or "")
        ).strip()


    # =========================================
    # VERIFICAR CONFIGURACIÓN
    # =========================================

    def verificar_configuracion(self):
        """Verifica que estén configuradas la clave, la URL y el modelo."""

        # Normalizar: una clave vacía o de solo espacios NO es válida
        self.api_key = (self.api_key or "").strip()
        self.base_url = (self.base_url or "").strip()
        self.modelo = (self.modelo or "").strip()

        faltan = []

        if not self.api_key:
            faltan.append("GROUP_API_KEY (clave de acceso a la IA)")

        if not self.base_url:
            faltan.append("GROUP_BASE_URL (URL base del proveedor)")

        if not self.modelo:
            faltan.append("GROUP_MODEL (modelo a utilizar)")

        if not faltan:
            return True, ""

        mensaje = (
            "Falta(n) por configurar la IA:\n\n"
            + "\n".join(f"   - {variable}" for variable in faltan)
            + "\n\nComplete el archivo .env de la raíz del proyecto "
            "y reinicie la aplicación:\n\n"
            "GROUP_API_KEY=su_clave_real\n"
            "GROUP_BASE_URL=https://api.groq.com/openai/v1\n"
            "GROUP_MODEL=qwen/qwen3.6-27b\n\n"
            "(Las variables de entorno del sistema tienen prioridad "
            "sobre el archivo .env)"
        )

        return False, mensaje

    def endpoint(self):
        """Devuelve la URL completa del endpoint de chat completions."""

        base = self.base_url.rstrip("/")

        if base.endswith("/chat/completions"):
            return base

        return f"{base}/chat/completions"

    def _url_valida(self, url):
        """Indica si una URL tiene formato válido (http/https)."""

        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _verificar_placeholders(self):
        """Detecta valores de ejemplo en el .env y devuelve el aviso o None."""

        clave = self.api_key.lower().strip()

        claves_ejemplo = {
            "tu_clave_real",
            "tu_clave_aqui",
            "tu_clave",
            "your_api_key",
            "your-api-key",
            "your_key_here",
            "api_key_here",
            "sk-your-api-key-here",
            "sk-xxxx",
            "change-me",
            "change_me",
        }

        if clave in claves_ejemplo or clave.startswith("tu_") or "xxxx" in clave:

            return (
                "La GROUP_API_KEY del archivo .env sigue siendo un valor "
                "de ejemplo.\n\n"
                "Coloque la clave real que le entregó su proveedor de IA "
                "y reinicie la aplicación."
            )

        url = self.base_url.lower().strip().split("?")[0].rstrip("/")

        if ("tu-proveedor" in url or "tuproveedor" in url
                or "example.com" in url or "your-provider" in url
                or url in ("https://tu-proveedor/v1", "http://tu-proveedor/v1")):

            return (
                "La GROUP_BASE_URL del archivo .env sigue siendo un valor "
                "de ejemplo.\n\n"
                "Coloque la URL real de su proveedor, por ejemplo:\n"
                "  https://api.groq.com/openai/v1  (si usa Groq)\n"
                "  https://api.openai.com/v1        (si usa OpenAI)\n"
                "y reinicie la aplicación."
            )

        if not self._url_valida(self.base_url):

            return (
                f"La GROUP_BASE_URL no tiene un formato de URL válido: "
                f"{self.base_url}\n\n"
                "Debe ser una dirección como: https://api.proveedor.com/v1"
            )

        return None

    # =========================================
    # CONSULTAR A LA API
    # =========================================

    def consultar(self, mensajes):
        """Envía los mensajes a la API y clasifica la respuesta o el error."""

        ok, error = self.verificar_configuracion()

        if not ok:
            return False, error

        error_placeholder = self._verificar_placeholders()

        if error_placeholder:
            return False, error_placeholder

        cabeceras = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        datos = {
            "model": self.modelo,
            "messages": mensajes,
            "temperature": 0.2,
            "max_tokens": 600,
        }

        try:

            respuesta = requests.post(
                self.endpoint(),
                headers=cabeceras,
                json=datos,
                timeout=35
            )

        except requests.exceptions.Timeout:

            return False, (
                "El proveedor de IA tardó demasiado en responder (timeout de 35s).\n"
                "Espere unos segundos e intente nuevamente."
            )

        except requests.exceptions.ConnectionError:

            return False, (
                "No se pudo conectar con el proveedor de IA.\n\n"
                "Posibles causas:\n"
                "  - No hay conexión a Internet.\n"
                "  - La GROUP_BASE_URL no existe o quedó el valor de ejemplo "
                "(https://TU-PROVEEDOR/v1).\n"
                "  - El servidor del proveedor está caído.\n\n"
                f"URL probada: {self.endpoint()}"
            )

        except requests.exceptions.SSLError:

            return False, (
                "Error de seguridad SSL al conectar con el proveedor.\n"
                "Verifique que GROUP_BASE_URL sea correcta (https://...)."
            )

        except Exception as error:

            return False, f"Error de conexión:\n{error}"

        # =============================================
        # CLASIFICACIÓN DE ERRORES HTTP
        # =============================================

        codigo = respuesta.status_code
        cuerpo = (respuesta.text or "")[:300]
        cuerpo_min = cuerpo.lower()

        if codigo == 200:

            try:

                contenido = respuesta.json()

                texto = contenido["choices"][0]["message"]["content"]

                texto_limpio = self._limpiar_respuesta(texto)

                return True, texto_limpio

            except Exception:

                return False, (
                    "La respuesta de la API no tiene el formato esperado.\n"
                    f"Detalle: {cuerpo}"
                )

        if codigo in (401, 403):

            return False, (
                f"El proveedor rechazó la API Key (código {codigo}).\n\n"
                "Verifique que GROUP_API_KEY sea la clave correcta de su "
                "proveedor.\n\n"
                f"Detalle del proveedor: {cuerpo}"
            )

        if codigo == 404:

            if self.modelo and (
                self.modelo.lower() in cuerpo_min or "model" in cuerpo_min
            ):

                return False, (
                    f"El modelo '{self.modelo}' no existe o no está "
                    f"disponible para este proveedor (código 404).\n\n"
                    "Verifique GROUP_MODEL en el archivo .env.\n\n"
                    f"Detalle: {cuerpo}"
                )

            return False, (
                "La URL del proveedor no se encontró (código 404).\n\n"
                "Verifique GROUP_BASE_URL; debe apuntar a la raíz de una API "
                "compatible con OpenAI (por ejemplo "
                "https://api.groq.com/openai/v1).\n\n"
                f"URL probada: {self.endpoint()}\n\n"
                f"Detalle: {cuerpo}"
            )

        if codigo == 400:

            return False, (
                "Solicitud inválida (código 400).\n\n"
                "Puede deberse a un modelo incorrecto (GROUP_MODEL) o a un "
                "mensaje mal formado.\n\n"
                f"Detalle: {cuerpo}"
            )

        if codigo == 429:

            return False, (
                "Límite de solicitudes alcanzado (código 429).\n"
                "Espere un momento e intente nuevamente."
            )

        if codigo >= 500:

            return False, (
                f"El proveedor tuvo un error interno (código {codigo}).\n"
                "Espere unos momentos e intente nuevamente.\n\n"
                f"Detalle: {cuerpo}"
            )

        return False, (
            f"Error de la API (código {codigo}):\n"
            f"{cuerpo}"
        )

    # =========================================
    # LIMPIEZA DE RESPUESTAS (Remover <think>)
    # =========================================

    def _limpiar_respuesta(self, texto):
        """Elimina bloques de razonamiento <think>...</think> y limpia espacios."""
        if not texto:
            return ""

        # Eliminar etiquetas <think>...</think> completas
        texto_limpio = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)

        # En caso de que el tag de apertura quedó sin cerrar al final
        if "<think>" in texto_limpio:
            texto_limpio = re.sub(r"<think>.*$", "", texto_limpio, flags=re.DOTALL)

        return texto_limpio.strip()

    # =========================================
    # PRUEBA RÁPIDA DE CONEXIÓN
    # =========================================

    def probar_conexion(self):
        """Realiza una consulta mínima de prueba al proveedor de IA."""

        return self.consultar([
            {
                "role": "user",
                "content": "Responde solo con la palabra OK.",
            }
        ])

    # =========================================
    # RESOLVER PROBLEMA MATEMÁTICO (TEXTO)
    # =========================================

    def resolver_problema(self, problema):
        """Resuelve un problema matemático escrito por el usuario de forma rápida y clara."""

        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente matematico. Resuelve el problema de forma "
                    "breve y directa.\n\n"
                    "Responde con este formato exacto:\n"
                    "1. Procedimiento en 2-4 lineas maximas.\n"
                    "2. Resultado: <expresion_o_valor>\n"
                    "3. Explicacion clara y concisa de 1 sola linea que diga "
                    "que significa el resultado (por ejemplo: "
                    "'La funcion tiene un corte en y=5' o 'El valor de x es 3').\n\n"
                    "No saludes, no pongas titulo."
                ),
            },
            {
                "role": "user",
                "content": f"{problema}",
            },
        ]

        return self.consultar(mensajes)

    # =========================================
    # RESOLVER PROBLEMA MATEMÁTICO CON IMAGEN
    # =========================================

    def resolver_problema_con_imagen(self, problema, imagen_bytes, mime_type):
        """Resuelve un problema matemático a partir de UNA imagen (foto) de forma rápida y precisa.
        Mantenido por compatibilidad. Internamente delega a resolver_problema_con_imagenes."""
        return self.resolver_problema_con_imagenes(
            problema, [(imagen_bytes, mime_type)]
        )

    # =========================================
    # RESOLVER PROBLEMA CON MÚLTIPLES IMÁGENES
    # =========================================

    def resolver_problema_con_imagenes(self, problema, imagenes):
        """Resuelve un problema matemático a partir de varias imágenes.

        Args:
            problema (str): Texto descriptivo del problema (puede estar vacío).
            imagenes (list[tuple]): Lista de (imagen_bytes: bytes, mime_type: str).
        """
        ok, error = self.verificar_configuracion()

        if not ok:
            return False, error

        instruccion = (
            f"Nota del estudiante: {problema}\n\n"
            "Analiza las imágenes y resuelve el problema."
            if (problema and problema.strip())
            else "Analiza las imágenes y resuelve el problema."
        )

        # Construir el contenido del mensaje con texto + todas las imágenes
        contenido_usuario = [
            {
                "type": "text",
                "text": instruccion,
            }
        ]

        for imagen_bytes, mime_type in imagenes:
            imagen_base64 = base64.b64encode(imagen_bytes).decode("utf-8")
            contenido_usuario.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{imagen_base64}"
                },
            })

        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente matematico con vision. Analiza las imagenes "
                    "y resuelve el problema.\n\n"
                    "Responde con este formato exacto:\n"
                    "1. Procedimiento en 2-4 lineas maximas.\n"
                    "2. Resultado: <expresion_o_valor>\n"
                    "3. Explicacion clara y concisa de 1 sola linea que diga "
                    "que significa el resultado (por ejemplo: "
                    "'La funcion tiene un corte en y=5' o 'El valor de x es 3').\n\n"
                    "No saludes, no pongas titulo."
                ),
            },
            {
                "role": "user",
                "content": contenido_usuario,
            },
        ]

        return self.consultar(mensajes)

