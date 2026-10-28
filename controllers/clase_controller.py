import json
import secrets
import sqlite3
from datetime import datetime

from database.conexion import obtener_conexion


# Alfabeto del código de acceso sin caracteres ambiguos (0/O, 1/I/L)
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGITUD_CODIGO = 6


class ClaseController:
    """Controlador de clases: creación, membresía y métodos de acceso biométrico."""

    # ==========================================
    # CÓDIGO DE ACCESO
    # ==========================================

    @staticmethod
    def _generar_codigo(cursor):
        """Genera un código de acceso que no exista todavía en la tabla clases."""
        while True:
            codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))
            cursor.execute("SELECT 1 FROM clases WHERE codigo_acceso=?", (codigo,))
            if cursor.fetchone() is None:
                return codigo

    @staticmethod
    def _ahora():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ==========================================
    # CREAR CLASE
    # ==========================================

    @staticmethod
    def crear_clase(creador_id, nombre, descripcion="", voz=False, postura=False):
        """
        Crea la clase, inscribe al creador como docente y guarda sus métodos de acceso.
        Devuelve (True, datos_clase) o (False, mensaje).
        """
        nombre = (nombre or "").strip()
        descripcion = (descripcion or "").strip()

        if not nombre:
            return False, "El nombre de la clase es obligatorio."

        conexion = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()

            # Nombre duplicado para el mismo creador. Se compara en Python porque
            # LOWER() de SQLite no convierte letras con tilde (Á/á).
            cursor.execute(
                "SELECT nombre FROM clases WHERE creador_id=? AND activa=1", (creador_id,)
            )
            if any(fila["nombre"].casefold() == nombre.casefold() for fila in cursor.fetchall()):
                return False, f"Ya tiene una clase llamada '{nombre}'. Elija otro nombre."

            codigo = ClaseController._generar_codigo(cursor)
            ahora = ClaseController._ahora()

            cursor.execute("""
                INSERT INTO clases
                (nombre, descripcion, codigo_acceso, creador_id, fecha_creacion,
                 activa, voz_habilitada, postura_habilitada)
                VALUES (?,?,?,?,?,1,?,?)
            """, (nombre, descripcion, codigo, creador_id, ahora, int(voz), int(postura)))

            clase_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO clase_usuarios (clase_id, usuario_id, rol, fecha_union) VALUES (?,?,?,?)",
                (clase_id, creador_id, "docente", ahora)
            )
            cursor.execute(
                "INSERT INTO clase_biometria (clase_id, usuario_id, voz_habilitada, postura_habilitada) "
                "VALUES (?,?,?,?)",
                (clase_id, creador_id, int(voz), int(postura))
            )

            conexion.commit()
            return True, {"id": clase_id, "nombre": nombre, "codigo_acceso": codigo}

        except sqlite3.Error as error:
            if conexion is not None:
                conexion.rollback()
            return False, f"No se pudo crear la clase: {error}"

        finally:
            if conexion is not None:
                conexion.close()

    # ==========================================
    # UNIRSE A UNA CLASE
    # ==========================================

    @staticmethod
    def unirse_por_codigo(usuario_id, codigo):
        """
        Inscribe al usuario como estudiante de la clase con ese código. Los métodos de
        acceso iniciales son los que el docente activó al crear la clase.
        Devuelve (True, datos_clase) o (False, mensaje).
        """
        codigo = (codigo or "").strip().upper()
        if not codigo:
            return False, "Escriba el código de acceso de la clase."

        conexion = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute(
                "SELECT * FROM clases WHERE codigo_acceso=? AND activa=1", (codigo,)
            )
            clase = cursor.fetchone()
            if clase is None:
                return False, f"No existe ninguna clase activa con el código '{codigo}'."

            cursor.execute(
                "SELECT 1 FROM clase_usuarios WHERE clase_id=? AND usuario_id=?",
                (clase["id"], usuario_id)
            )
            if cursor.fetchone():
                return False, f"Ya pertenece a la clase '{clase['nombre']}'."

            cursor.execute(
                "INSERT INTO clase_usuarios (clase_id, usuario_id, rol, fecha_union) VALUES (?,?,?,?)",
                (clase["id"], usuario_id, "estudiante", ClaseController._ahora())
            )
            cursor.execute(
                "INSERT OR IGNORE INTO clase_biometria "
                "(clase_id, usuario_id, voz_habilitada, postura_habilitada) VALUES (?,?,?,?)",
                (clase["id"], usuario_id, clase["voz_habilitada"], clase["postura_habilitada"])
            )

            conexion.commit()
            return True, dict(clase)

        except sqlite3.Error as error:
            if conexion is not None:
                conexion.rollback()
            return False, f"No se pudo unir a la clase: {error}"

        finally:
            if conexion is not None:
                conexion.close()

    # ==========================================
    # CONSULTAS
    # ==========================================

    @staticmethod
    def clases_de_usuario(usuario_id):
        """Clases activas del usuario con su rol y sus métodos de acceso en cada una."""
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT c.*,
                       cu.rol,
                       COALESCE(cb.voz_habilitada, 0) AS mi_voz,
                       COALESCE(cb.postura_habilitada, 0) AS mi_postura,
                       (SELECT COUNT(*) FROM clase_usuarios x WHERE x.clase_id = c.id) AS total_miembros
                FROM clases c
                JOIN clase_usuarios cu ON cu.clase_id = c.id AND cu.usuario_id = ?
                LEFT JOIN clase_biometria cb ON cb.clase_id = c.id AND cb.usuario_id = ?
                WHERE c.activa = 1
                ORDER BY c.fecha_creacion DESC
            """, (usuario_id, usuario_id))
            filas = cursor.fetchall()
            conexion.close()
            return filas
        except sqlite3.Error as error:
            print(f"[Clases] Error al listar clases: {error}")
            return []

    @staticmethod
    def obtener_clase(clase_id, usuario_id):
        """Datos de la clase vistos por un miembro (incluye su rol), o None si no pertenece."""
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT c.*, cu.rol
                FROM clases c
                JOIN clase_usuarios cu ON cu.clase_id = c.id AND cu.usuario_id = ?
                WHERE c.id = ?
            """, (usuario_id, clase_id))
            fila = cursor.fetchone()
            conexion.close()
            return fila
        except sqlite3.Error:
            return None

    @staticmethod
    def miembros(clase_id):
        """Lista de miembros (nombre, usuario, rol, fecha_union) de la clase."""
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT u.nombre, u.usuario, cu.rol, cu.fecha_union
                FROM clase_usuarios cu
                JOIN usuarios u ON u.id = cu.usuario_id
                WHERE cu.clase_id = ?
                ORDER BY cu.rol = 'estudiante', u.nombre
            """, (clase_id,))
            filas = cursor.fetchall()
            conexion.close()
            return filas
        except sqlite3.Error:
            return []

    # ==========================================
    # BIOMETRÍA POR CLASE
    # ==========================================

    @staticmethod
    def acceso_usuario(clase_id, usuario_id):
        """Fila de clase_biometria del usuario en la clase (la crea vacía si falta)."""
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO clase_biometria (clase_id, usuario_id) VALUES (?,?)",
                (clase_id, usuario_id)
            )
            conexion.commit()
            cursor.execute(
                "SELECT * FROM clase_biometria WHERE clase_id=? AND usuario_id=?",
                (clase_id, usuario_id)
            )
            fila = cursor.fetchone()
            conexion.close()
            return fila
        except sqlite3.Error:
            return None

    @staticmethod
    def actualizar_metodos(clase_id, usuario_id, voz, postura):
        """Activa o desactiva el acceso por voz / postura del usuario en la clase."""
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO clase_biometria (clase_id, usuario_id) VALUES (?,?)",
                (clase_id, usuario_id)
            )
            cursor.execute(
                "UPDATE clase_biometria SET voz_habilitada=?, postura_habilitada=? "
                "WHERE clase_id=? AND usuario_id=?",
                (int(voz), int(postura), clase_id, usuario_id)
            )
            conexion.commit()
            conexion.close()
            return True
        except sqlite3.Error:
            return False

    @staticmethod
    def guardar_biometria(clase_id, usuario_id, tipo, etiqueta, vector):
        """Guarda la voz ('voz') o la postura ('pose') registrada para esta clase."""
        if tipo not in ("voz", "pose"):
            return False
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO clase_biometria (clase_id, usuario_id) VALUES (?,?)",
                (clase_id, usuario_id)
            )
            cursor.execute(
                f"UPDATE clase_biometria SET etiqueta_{tipo}=?, embedding_{tipo}=? "
                f"WHERE clase_id=? AND usuario_id=?",
                (etiqueta, json.dumps(vector), clase_id, usuario_id)
            )
            conexion.commit()
            conexion.close()
            return True
        except sqlite3.Error:
            return False
