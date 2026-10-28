from datetime import datetime
import sqlite3

from database.conexion import obtener_conexion
from utils.parsing_respuesta import separar_procedimiento_resultado


class HistorialController:
    """Controlador del historial de consultas matemáticas."""

    # ==========================================
    # GUARDAR CONSULTA
    # ==========================================

    @staticmethod
    def guardar_consulta(
        usuario,
        problema,
        respuesta,
        procedimiento="",
        resultado=""
    ):
        """
        Guarda una consulta separando procedimiento y resultado.

        Si no se reciben procedimiento/resultado, se calculan con la
        heurística de parsing de la respuesta completa.
        """
        if not procedimiento and not resultado:
            procedimiento, resultado = separar_procedimiento_resultado(
                respuesta
            )

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            ahora = datetime.now()

            fecha = ahora.strftime("%d/%m/%Y")
            hora = ahora.strftime("%H:%M:%S")

            cursor.execute("""

                INSERT INTO historial

                (usuario, problema, respuesta, procedimiento, resultado,
                 fecha, hora)

                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (
                usuario,
                problema,
                respuesta,
                procedimiento,
                resultado,
                fecha,
                hora
            ))

            conexion.commit()
            conexion.close()

            return True, "Consulta guardada correctamente."

        except sqlite3.Error as error:

            return False, str(error)

    # ==========================================
    # OBTENER HISTORIAL DE UN USUARIO
    # ==========================================

    @staticmethod
    def obtener_historial(usuario):
        """Devuelve las consultas de un usuario (más recientes primero)."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute("""

                SELECT

                    fecha,
                    hora,
                    problema,
                    procedimiento,
                    resultado

                FROM historial

                WHERE usuario=?

                ORDER BY id DESC

            """, (usuario,))

            historial = cursor.fetchall()

            conexion.close()

            return historial

        except sqlite3.Error:

            return []

    # ==========================================
    # BUSCAR CONSULTAS
    # ==========================================

    @staticmethod
    def buscar_consulta(usuario, texto):
        """Busca consultas de un usuario cuyo problema contenga el texto."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute("""

                SELECT

                    fecha,
                    hora,
                    problema,
                    procedimiento,
                    resultado

                FROM historial

                WHERE usuario=?

                AND problema LIKE ?

                ORDER BY id DESC

            """, (
                usuario,
                f"%{texto}%"
            ))

            datos = cursor.fetchall()

            conexion.close()

            return datos

        except sqlite3.Error:

            return []

    # ==========================================
    # ELIMINAR UNA CONSULTA
    # ==========================================

    @staticmethod
    def eliminar_consulta(id_consulta):
        """Elimina una consulta del historial por su id."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute(

                "DELETE FROM historial WHERE id=?",

                (id_consulta,)

            )

            conexion.commit()
            conexion.close()

            return True

        except sqlite3.Error:

            return False

    # ==========================================
    # ELIMINAR TODO EL HISTORIAL
    # ==========================================

    @staticmethod
    def eliminar_historial(usuario):
        """Elimina todas las consultas de un usuario."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute(

                "DELETE FROM historial WHERE usuario=?",

                (usuario,)

            )

            conexion.commit()
            conexion.close()

            return True

        except sqlite3.Error:

            return False

    # ==========================================
    # CONTAR CONSULTAS
    # ==========================================

    @staticmethod
    def total_consultas(usuario):
        """Devuelve la cantidad de consultas realizadas por un usuario."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute("""

                SELECT COUNT(*)

                FROM historial

                WHERE usuario=?

            """, (usuario,))

            total = cursor.fetchone()[0]

            conexion.close()

            return total

        except sqlite3.Error:

            return 0
