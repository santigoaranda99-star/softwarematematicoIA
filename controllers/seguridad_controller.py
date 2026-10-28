import sqlite3
from datetime import datetime, timedelta

from database.conexion import obtener_conexion

_FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


class SeguridadController:
    """Registro de intentos de login, bloqueo temporal y huellas de audios ya usados."""

    # ==========================================
    # INTENTOS Y BLOQUEO TEMPORAL
    # ==========================================

    @staticmethod
    def registrar_intento(metodo, exito, motivo="", usuario=""):
        """Guarda un intento de login. Un acceso correcto (exito=True) reinicia la racha de fallos."""
        try:
            conexion = obtener_conexion()
            conexion.execute(
                "INSERT INTO intentos_fallidos (fecha, usuario, metodo, motivo, exito) VALUES (?,?,?,?,?)",
                (datetime.now().strftime(_FORMATO_FECHA), usuario or "", metodo, motivo[:300], int(bool(exito)))
            )
            conexion.commit()
            conexion.close()
        except sqlite3.Error as error:
            print(f"[Seguridad] No se pudo registrar el intento: {error}")

    @staticmethod
    def fallos_seguidos():
        """Fallos consecutivos desde el último acceso correcto y fecha del último fallo."""
        try:
            conexion = obtener_conexion()
            filas = conexion.execute(
                "SELECT fecha, exito FROM intentos_fallidos ORDER BY id DESC LIMIT 200"
            ).fetchall()
            conexion.close()
        except sqlite3.Error:
            return 0, None

        fallos, ultimo = 0, None
        for fila in filas:
            if fila["exito"]:
                break
            fallos += 1
            ultimo = ultimo or datetime.strptime(fila["fecha"], _FORMATO_FECHA)
        return fallos, ultimo

    @staticmethod
    def segundos_bloqueo(intentos_max, base_segundos, maximo_segundos):
        """
        Segundos de bloqueo restantes (0 = libre). Cada racha de 'intentos_max' fallos seguidos
        bloquea 'base_segundos', duplicándose en cada racha nueva hasta 'maximo_segundos'.
        """
        fallos, ultimo = SeguridadController.fallos_seguidos()
        if fallos < intentos_max or ultimo is None:
            return 0
        rachas = fallos // intentos_max
        # Solo bloquea justo al completar una racha (3, 6, 9... fallos)
        if fallos % intentos_max != 0:
            return 0
        duracion = min(base_segundos * (2 ** (rachas - 1)), maximo_segundos)
        restante = (ultimo + timedelta(seconds=duracion) - datetime.now()).total_seconds()
        return max(0, int(restante + 0.999))

    # ==========================================
    # AUDIOS YA USADOS (anti-repetición)
    # ==========================================

    @staticmethod
    def huellas_recientes(limite=300):
        try:
            conexion = obtener_conexion()
            filas = conexion.execute(
                "SELECT huella FROM audios_usados ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
            conexion.close()
            return [f["huella"] for f in filas]
        except sqlite3.Error:
            return []

    @staticmethod
    def guardar_huellas(huellas):
        try:
            conexion = obtener_conexion()
            fecha = datetime.now().strftime(_FORMATO_FECHA)
            conexion.executemany(
                "INSERT OR IGNORE INTO audios_usados (huella, fecha) VALUES (?,?)",
                [(h, fecha) for h in huellas]
            )
            conexion.commit()
            conexion.close()
        except sqlite3.Error as error:
            print(f"[Seguridad] No se pudo guardar la huella del audio: {error}")
