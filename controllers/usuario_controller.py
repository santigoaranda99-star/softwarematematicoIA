import sqlite3

from database.conexion import obtener_conexion
from utils.seguridad import es_hash, generar_hash, verificar_contraseña


class UsuarioController:
    """Controlador de usuarios: registro, inicio de sesión y consultas."""

    # ==========================================
    # REGISTRAR USUARIO
    # ==========================================

    @staticmethod
    def registrar_usuario(nombre, usuario, contraseña, etiqueta_facial=""):
        """Registra un usuario guardando la contraseña con hash SHA-256 + salt y parámetro de reconocimiento facial."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            # Verificar si el usuario ya existe

            cursor.execute(
                "SELECT id FROM usuarios WHERE usuario=?",
                (usuario,)
            )

            if cursor.fetchone():

                conexion.close()

                return False, "El usuario ya existe."

            # Insertar usuario (contraseña hasheada con salt + etiqueta facial)
            etiqueta = etiqueta_facial.strip() if etiqueta_facial else usuario

            cursor.execute("""

                INSERT INTO usuarios

                (nombre, usuario, contraseña, etiqueta_facial)

                VALUES (?,?,?,?)

            """, (nombre, usuario, generar_hash(contraseña), etiqueta))

            conexion.commit()
            conexion.close()

            return True, "Usuario registrado correctamente."

        except sqlite3.Error as error:

            return False, str(error)

    # ==========================================
    # INICIAR SESIÓN
    # ==========================================

    @staticmethod
    def iniciar_sesion(usuario, contraseña):
        """Valida las credenciales comparando el hash almacenado con el mismo salt."""

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute("""

                SELECT *

                FROM usuarios

                WHERE usuario=?

            """, (usuario,))

            datos = cursor.fetchone()

            if datos is None:

                conexion.close()

                return False, "Usuario o contraseña incorrectos."

            almacenada = datos["contraseña"]

            if not verificar_contraseña(contraseña, almacenada):

                conexion.close()

                return False, "Usuario o contraseña incorrectos."

            # Migración automática si el valor aún está en texto plano
            if not es_hash(almacenada):

                cursor.execute(
                    "UPDATE usuarios SET contraseña=? WHERE id=?",
                    (generar_hash(almacenada), datos["id"])
                )

                conexion.commit()

            conexion.close()

            return True, datos

        except sqlite3.Error as error:

            return False, str(error)

    # ==========================================
    # INICIAR SESIÓN POR RECONOCIMIENTO FACIAL
    # ==========================================

    @staticmethod
    def iniciar_sesion_por_rostro(identificador_rostro):
        """Valida el inicio de sesión buscando coincidencia de usuario o nombre."""

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()

            cursor.execute("""
                SELECT *
                FROM usuarios
                WHERE LOWER(usuario)=LOWER(?)
                   OR LOWER(nombre)=LOWER(?)
                   OR LOWER(etiqueta_facial)=LOWER(?)
            """, (identificador_rostro, identificador_rostro, identificador_rostro))

            datos = cursor.fetchone()

            # Búsqueda difusa / por prefijo si no hubo coincidencia exacta
            if datos is None and identificador_rostro:
                patron = f"%{identificador_rostro.lower()}%"
                cursor.execute("""
                    SELECT *
                    FROM usuarios
                    WHERE LOWER(usuario) LIKE ?
                       OR LOWER(nombre) LIKE ?
                       OR LOWER(etiqueta_facial) LIKE ?
                """, (patron, patron, patron))
                datos = cursor.fetchone()

            # Búsqueda inversa: si el nombre o usuario en BD está contenido en el identificador (ej: 'santi' en 'santiago' o 'mendi' en 'mendieta')
            if datos is None and identificador_rostro:
                cursor.execute("SELECT * FROM usuarios")
                todos = cursor.fetchall()
                id_lower = identificador_rostro.lower()
                for u in todos:
                    u_nom = (u["nombre"] or "").lower()
                    u_usr = (u["usuario"] or "").lower()
                    u_etq = (u["etiqueta_facial"] or "").lower()
                    if (u_nom and (u_nom in id_lower or id_lower in u_nom)) or \
                       (u_usr and (u_usr in id_lower or id_lower in u_usr)) or \
                       (u_etq and (u_etq in id_lower or id_lower in u_etq)):
                        datos = u
                        break

            conexion.close()

            if datos is None:
                return False, f"El usuario reconocido '{identificador_rostro}' no está registrado en la base de datos."

            return True, datos

        except sqlite3.Error as error:
            return False, str(error)

    # ==========================================
    # GUARDAR EMBEDDING FACIAL (SFACE 128D)
    # ==========================================

    @staticmethod
    def guardar_embedding_facial(usuario, embedding_lista):
        """
        Guarda el vector biométrico SFace (128 flotantes) en la columna
        embedding_facial de la tabla usuarios, serializado como JSON.
        """
        import json
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE usuarios SET embedding_facial=? WHERE LOWER(usuario)=LOWER(?)",
                (json.dumps(embedding_lista), usuario)
            )
            conexion.commit()
            conexion.close()
            return True
        except sqlite3.Error as error:
            return False

    # ==========================================
    # GUARDAR BIOMETRÍA DE VOZ / POSTURA
    # ==========================================

    @staticmethod
    def guardar_biometria_voz(usuario, etiqueta, vector):
        """Guarda la clase de voz detectada y su vector de referencia (JSON)."""
        return UsuarioController._guardar_biometria("voz", usuario, etiqueta, vector)

    @staticmethod
    def guardar_biometria_pose(usuario, etiqueta, vector):
        """Guarda la clase de postura detectada y su vector de referencia (JSON)."""
        return UsuarioController._guardar_biometria("pose", usuario, etiqueta, vector)

    @staticmethod
    def _guardar_biometria(tipo, usuario, etiqueta, vector):
        import json
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                f"UPDATE usuarios SET etiqueta_{tipo}=?, embedding_{tipo}=? WHERE usuario=?",
                (etiqueta, json.dumps(vector), usuario)
            )
            conexion.commit()
            conexion.close()
            return True
        except sqlite3.Error:
            return False

    # ==========================================
    # PALABRA Y POSTURA DE INGRESO PROPIAS
    # ==========================================

    @staticmethod
    def guardar_palabra_ingreso(usuario, palabra, plantilla):
        """Guarda la palabra de ingreso (solo su hash con salt) y la plantilla de voz (JSON)."""
        import json
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE usuarios SET palabra_ingreso=?, plantilla_voz=? WHERE usuario=?",
                (generar_hash(palabra.strip().lower()), json.dumps(plantilla), usuario)
            )
            conexion.commit()
            guardado = cursor.rowcount > 0
            conexion.close()
            return guardado
        except sqlite3.Error:
            return False

    @staticmethod
    def guardar_plantilla_postura(usuario, plantilla):
        """Guarda la plantilla de postura de ingreso (JSON con los puntos clave)."""
        import json
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE usuarios SET plantilla_postura=? WHERE usuario=?",
                (json.dumps(plantilla), usuario)
            )
            conexion.commit()
            guardado = cursor.rowcount > 0
            conexion.close()
            return guardado
        except sqlite3.Error:
            return False

    @staticmethod
    def es_palabra_actual(usuario, palabra):
        """Indica si 'palabra' es la palabra de ingreso guardada (se compara contra el hash)."""
        datos = UsuarioController.buscar_usuario(usuario)
        if datos is None or not datos["palabra_ingreso"]:
            return False
        return verificar_contraseña(palabra.strip().lower(), datos["palabra_ingreso"])

    @staticmethod
    def usuarios_con_plantilla(tipo):
        """Usuarios con plantilla de 'voz' o 'postura' registrada (para identificar 1:N)."""
        columna = {"voz": "plantilla_voz", "postura": "plantilla_postura"}[tipo]
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute(f"SELECT * FROM usuarios WHERE {columna} != ''")
            filas = cursor.fetchall()
            conexion.close()
            return filas
        except sqlite3.Error:
            return []

    # ==========================================
    # INGRESO RÁPIDO (TEACHABLE MACHINE)
    # ==========================================

    @staticmethod
    def guardar_clase_tm(usuario, tipo, clase):
        """Vincula la clase del modelo de 'rostro', 'voz' o 'postura' de Teachable Machine al usuario."""
        columna = {"rostro": "clase_tm_rostro", "voz": "clase_tm_voz", "postura": "clase_tm_postura"}[tipo]
        try:
            conexion = obtener_conexion()
            conexion.execute(f"UPDATE usuarios SET {columna}=? WHERE LOWER(usuario)=LOWER(?)",
                             (clase, usuario))
            conexion.commit()
            conexion.close()
            return True
        except sqlite3.Error:
            return False

    @staticmethod
    def usuarios_por_clase_tm(tipo, clase):
        """
        Usuarios vinculados a una clase del modelo. Si nadie la vinculó todavía, se acepta el
        usuario cuyo nombre de usuario (o primer nombre) es igual a la clase y que no tenga
        otra clase vinculada.
        """
        columna = {"rostro": "clase_tm_rostro", "voz": "clase_tm_voz", "postura": "clase_tm_postura"}[tipo]
        try:
            conexion = obtener_conexion()
            filas = conexion.execute(f"SELECT * FROM usuarios WHERE LOWER({columna})=LOWER(?)",
                                     (clase,)).fetchall()
            if not filas:
                filas = [f for f in conexion.execute(f"SELECT * FROM usuarios WHERE {columna}=''")
                         if clase.lower() in (f["usuario"].strip().lower(),
                                              (f["nombre"].split() or [""])[0].lower())]
            conexion.close()
            return filas
        except sqlite3.Error:
            return []

    @staticmethod
    def usuarios_con_rostro():
        """Usuarios con vector facial SFace guardado (para identificar 1:N en la prueba de vida)."""
        try:
            conexion = obtener_conexion()
            filas = conexion.execute("SELECT * FROM usuarios WHERE embedding_facial != ''").fetchall()
            conexion.close()
            return filas
        except sqlite3.Error:
            return []

    @staticmethod
    def es_docente(usuario):
        """True si el usuario es docente de alguna clase (rol que puede exigir segundo factor)."""
        try:
            conexion = obtener_conexion()
            fila = conexion.execute("""
                SELECT 1 FROM clase_usuarios cu JOIN usuarios u ON u.id = cu.usuario_id
                WHERE u.usuario = ? AND cu.rol = 'docente' LIMIT 1
            """, (usuario,)).fetchone()
            conexion.close()
            return fila is not None
        except sqlite3.Error:
            return False

    # ==========================================
    # AUTENTICAR POR EMBEDDING 1:N
    # ==========================================

    @staticmethod
    def buscar_por_embedding(embedding_nuevo, umbral=0.35):
        """
        Compara el embedding facial capturado contra TODOS los usuarios
        registrados que tienen embedding guardado (1:N matching).

        Retorna (True, datos_usuario) si hay coincidencia por encima del
        umbral, o (False, mensaje_error) si no se encuentra.

        Nota: SFace con FaceRecognizerSF_FR_COSINE devuelve valores en
        [0, 1]. El umbral por defecto 0.35 es recomendado por OpenCV
        (score >= 0.363 → misma persona según los benchmarks del modelo).
        """
        import json
        try:
            import cv2
            import numpy as np
        except ImportError:
            return False, "OpenCV no disponible para comparación biométrica."

        if embedding_nuevo is None:
            return False, "No se recibió embedding facial."

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        try:
            cursor.execute(
                "SELECT * FROM usuarios WHERE embedding_facial != '' AND embedding_facial IS NOT NULL"
            )
            usuarios = cursor.fetchall()
        except sqlite3.Error as e:
            conexion.close()
            return False, str(e)

        conexion.close()

        if not usuarios:
            return False, "No hay usuarios con rostro registrado en la base de datos."

        mejor_usuario = None
        mejor_similitud = -1.0

        arr_nuevo = np.array(embedding_nuevo, dtype=np.float32).reshape(1, -1)

        for u in usuarios:
            try:
                emb_guardado = json.loads(u["embedding_facial"])
            except (json.JSONDecodeError, TypeError, KeyError):
                continue

            if not emb_guardado:
                continue

            try:
                arr_guardado = np.array(emb_guardado, dtype=np.float32).reshape(1, -1)

                # Similitud coseno con el modelo SFace de OpenCV
                from services.clasificador_imagen import ClasificadorImagen
                ClasificadorImagen.cargar_reconocedor_facial()
                if ClasificadorImagen._reconocedor_sface is not None:
                    sim = float(ClasificadorImagen._reconocedor_sface.match(
                        arr_nuevo, arr_guardado, cv2.FaceRecognizerSF_FR_COSINE
                    ))
                else:
                    dot = float(np.dot(arr_nuevo[0], arr_guardado[0]))
                    n1 = float(np.linalg.norm(arr_nuevo[0]))
                    n2 = float(np.linalg.norm(arr_guardado[0]))
                    sim = dot / (n1 * n2) if n1 > 0 and n2 > 0 else 0.0

                print(f"[FaceAuth 1:N] Usuario '{u['usuario']}': similitud={sim:.4f} (umbral={umbral})")

                if sim > mejor_similitud:
                    mejor_similitud = sim
                    mejor_usuario = dict(u)

            except Exception as e:
                print(f"[FaceAuth 1:N] Error comparando con '{u['usuario']}': {e}")
                continue

        if mejor_usuario is not None and mejor_similitud >= umbral:
            print(f"[FaceAuth 1:N] ✅ Coincidencia encontrada: '{mejor_usuario['usuario']}' ({mejor_similitud:.4f})")
            mejor_usuario["_similitud_facial"] = mejor_similitud
            return True, mejor_usuario

        print(f"[FaceAuth 1:N] ❌ Sin coincidencia. Mejor similitud: {mejor_similitud:.4f} (umbral={umbral})")
        return False, (
            f"No se encontró ningún usuario que coincida con el rostro capturado "
            f"(similitud máxima: {mejor_similitud * 100:.1f}%). "
            f"Asegúrese de haber registrado su rostro al crear la cuenta."
        )

    # ==========================================
    # BUSCAR USUARIO
    # ==========================================

    @staticmethod
    def buscar_usuario(usuario):
        """Devuelve los datos de un usuario por su nombre de usuario."""

        try:

            conexion = obtener_conexion()

            cursor = conexion.cursor()

            cursor.execute(

                "SELECT * FROM usuarios WHERE usuario=?",

                (usuario,)

            )

            datos = cursor.fetchone()

            conexion.close()

            return datos

        except sqlite3.Error:

            return None

    # ==========================================
    # OBTENER TODOS LOS USUARIOS
    # ==========================================

    @staticmethod
    def obtener_usuarios():
        """Devuelve la lista de usuarios (id, nombre, usuario) ordenada por nombre."""

        try:

            conexion = obtener_conexion()

            cursor = conexion.cursor()

            cursor.execute("""

                SELECT id,
                       nombre,
                       usuario

                FROM usuarios

                ORDER BY nombre

            """)

            usuarios = cursor.fetchall()

            conexion.close()

            return usuarios

        except sqlite3.Error:

            return []

    # ==========================================
    # ELIMINAR USUARIO
    # ==========================================

    @staticmethod
    def eliminar_usuario(id_usuario):
        """Elimina un usuario de la base de datos por su id."""

        try:

            conexion = obtener_conexion()

            cursor = conexion.cursor()

            cursor.execute(

                "DELETE FROM usuarios WHERE id=?",

                (id_usuario,)

            )

            conexion.commit()

            conexion.close()

            return True

        except sqlite3.Error:

            return False
