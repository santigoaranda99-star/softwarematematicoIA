from database.conexion import obtener_conexion


def _tabla_tiene_columna(cursor, tabla, columna):
    """Indica si una tabla ya tiene una columna determinada."""
    columnas = [
        fila[1]
        for fila in cursor.execute(f"PRAGMA table_info({tabla})").fetchall()
    ]

    return columna in columnas


def migrar_historial():
    """
    Agrega las columnas procedimiento y resultado a la tabla historial
    si no existen, y rellena las filas antiguas a partir de 'respuesta'.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    for columna in ("procedimiento", "resultado"):

        if not _tabla_tiene_columna(cursor, "historial", columna):

            cursor.execute(
                f"ALTER TABLE historial "
                f"ADD COLUMN {columna} TEXT NOT NULL DEFAULT ''"
            )

    # Rellenar filas antiguas con el parseo heurístico de la respuesta
    cursor.execute("""
        SELECT id, respuesta
        FROM historial
        WHERE procedimiento = '' AND resultado = ''
    """)

    filas = cursor.fetchall()

    from utils.parsing_respuesta import separar_procedimiento_resultado

    for fila in filas:

        procedimiento, resultado = separar_procedimiento_resultado(
            fila["respuesta"]
        )

        cursor.execute(
            "UPDATE historial SET procedimiento=?, resultado=? WHERE id=?",
            (procedimiento, resultado, fila["id"])
        )

    conexion.commit()
    conexion.close()


def migrar_usuarios_facial():
    """Agrega la columna etiqueta_facial a la tabla usuarios si no existe."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if not _tabla_tiene_columna(cursor, "usuarios", "etiqueta_facial"):
        cursor.execute(
            "ALTER TABLE usuarios "
            "ADD COLUMN etiqueta_facial TEXT NOT NULL DEFAULT ''"
        )
        conexion.commit()

    conexion.close()


def migrar_usuarios_embedding():
    """Agrega la columna embedding_facial (vector numérico SFace 128D) a usuarios si no existe."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if not _tabla_tiene_columna(cursor, "usuarios", "embedding_facial"):
        cursor.execute(
            "ALTER TABLE usuarios "
            "ADD COLUMN embedding_facial TEXT NOT NULL DEFAULT ''"
        )
        conexion.commit()

    conexion.close()


def migrar_usuarios_biometria():
    """
    Agrega las columnas de voz y postura si no existen: la clase de Teachable Machine
    (etiqueta_voz / etiqueta_pose) y el vector de referencia capturado (embedding_voz /
    embedding_pose, JSON), igual que etiqueta_facial / embedding_facial.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    for columna in ("etiqueta_voz", "etiqueta_pose", "embedding_voz", "embedding_pose"):

        if not _tabla_tiene_columna(cursor, "usuarios", columna):
            cursor.execute(
                f"ALTER TABLE usuarios "
                f"ADD COLUMN {columna} TEXT NOT NULL DEFAULT ''"
            )

    conexion.commit()
    conexion.close()


def migrar_usuarios_tm():
    """
    Agrega las columnas del ingreso rápido: la clase de los modelos de Teachable Machine
    (models/tm_rostro, models/tm_voz) vinculada a cada usuario. Vacías = sin vincular.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    for columna in ("clase_tm_rostro", "clase_tm_voz", "clase_tm_postura"):

        if not _tabla_tiene_columna(cursor, "usuarios", columna):
            cursor.execute(
                f"ALTER TABLE usuarios "
                f"ADD COLUMN {columna} TEXT NOT NULL DEFAULT ''"
            )

    conexion.commit()
    conexion.close()


def migrar_usuarios_ingreso():
    """
    Agrega las columnas de la palabra y la postura de ingreso propias de cada usuario:
    palabra_ingreso (hash con salt, nunca en texto plano), plantilla_voz y
    plantilla_postura (JSON). Vacías = el usuario aún no las registró.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    for columna in ("palabra_ingreso", "plantilla_voz", "plantilla_postura"):

        if not _tabla_tiene_columna(cursor, "usuarios", columna):
            cursor.execute(
                f"ALTER TABLE usuarios "
                f"ADD COLUMN {columna} TEXT NOT NULL DEFAULT ''"
            )

    conexion.commit()
    conexion.close()


def migrar_seguridad():
    """
    Tablas de seguridad del login biométrico (se crean solo si no existen):
    - intentos_fallidos: registro de cada intento fallido (fecha, método, motivo) y base
      del bloqueo temporal tras varios fallos seguidos.
    - audios_usados: hash de cada audio de login para rechazar grabaciones repetidas.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intentos_fallidos(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        fecha TEXT NOT NULL,

        usuario TEXT NOT NULL DEFAULT '',

        metodo TEXT NOT NULL,

        motivo TEXT NOT NULL DEFAULT ''

    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audios_usados(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        huella TEXT NOT NULL UNIQUE,

        fecha TEXT NOT NULL

    )
    """)

    # Columna 'exito' en el registro de intentos: un acceso correcto reinicia la racha
    if not _tabla_tiene_columna(cursor, "intentos_fallidos", "exito"):
        cursor.execute(
            "ALTER TABLE intentos_fallidos ADD COLUMN exito INTEGER NOT NULL DEFAULT 0"
        )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_intentos_fecha ON intentos_fallidos(fecha)"
    )

    conexion.commit()
    conexion.close()


def migrar_clases():
    """
    Crea las tablas del módulo de Clases si no existen. Es segura: no borra datos y
    agrega las columnas que falten si las tablas vienen de una versión anterior.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Clases creadas por los usuarios. voz/postura_habilitada son los métodos de
    # acceso por defecto que se aplican a quien se une a la clase.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clases(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        nombre TEXT NOT NULL,

        descripcion TEXT NOT NULL DEFAULT '',

        codigo_acceso TEXT NOT NULL UNIQUE,

        creador_id INTEGER NOT NULL,

        fecha_creacion TEXT NOT NULL,

        activa INTEGER NOT NULL DEFAULT 1,

        voz_habilitada INTEGER NOT NULL DEFAULT 0,

        postura_habilitada INTEGER NOT NULL DEFAULT 0,

        FOREIGN KEY(creador_id) REFERENCES usuarios(id)

    )
    """)

    # Miembros de cada clase con su rol (docente / estudiante)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clase_usuarios(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        clase_id INTEGER NOT NULL,

        usuario_id INTEGER NOT NULL,

        rol TEXT NOT NULL DEFAULT 'estudiante'
            CHECK (rol IN ('docente', 'estudiante')),

        fecha_union TEXT NOT NULL,

        UNIQUE(clase_id, usuario_id),

        FOREIGN KEY(clase_id) REFERENCES clases(id) ON DELETE CASCADE,

        FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE

    )
    """)

    # Métodos de acceso de cada usuario en cada clase y, si los registró, su voz /
    # postura propias para esa clase (mismo formato que en la tabla usuarios).
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clase_biometria(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        clase_id INTEGER NOT NULL,

        usuario_id INTEGER NOT NULL,

        voz_habilitada INTEGER NOT NULL DEFAULT 0,

        postura_habilitada INTEGER NOT NULL DEFAULT 0,

        etiqueta_voz TEXT NOT NULL DEFAULT '',

        embedding_voz TEXT NOT NULL DEFAULT '',

        etiqueta_pose TEXT NOT NULL DEFAULT '',

        embedding_pose TEXT NOT NULL DEFAULT '',

        UNIQUE(clase_id, usuario_id),

        FOREIGN KEY(clase_id) REFERENCES clases(id) ON DELETE CASCADE,

        FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE

    )
    """)

    # Columnas que pueden faltar en tablas creadas por versiones previas
    columnas_extra = {
        "clases": {
            "descripcion": "TEXT NOT NULL DEFAULT ''",
            "activa": "INTEGER NOT NULL DEFAULT 1",
            "voz_habilitada": "INTEGER NOT NULL DEFAULT 0",
            "postura_habilitada": "INTEGER NOT NULL DEFAULT 0",
        },
        "clase_biometria": {
            "etiqueta_voz": "TEXT NOT NULL DEFAULT ''",
            "embedding_voz": "TEXT NOT NULL DEFAULT ''",
            "etiqueta_pose": "TEXT NOT NULL DEFAULT ''",
            "embedding_pose": "TEXT NOT NULL DEFAULT ''",
        },
    }

    for tabla, columnas in columnas_extra.items():
        for columna, definicion in columnas.items():
            if not _tabla_tiene_columna(cursor, tabla, columna):
                cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_clase_usuarios_usuario ON clase_usuarios(usuario_id)"
    )

    conexion.commit()
    conexion.close()


def crear_base_datos():
    """Crea las tablas si no existen y aplica las migraciones pendientes."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # ============================
    # TABLA USUARIOS
    # ============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        nombre TEXT NOT NULL,

        usuario TEXT NOT NULL UNIQUE,

        contraseña TEXT NOT NULL,

        etiqueta_facial TEXT NOT NULL DEFAULT '',

        embedding_facial TEXT NOT NULL DEFAULT '',

        etiqueta_voz TEXT NOT NULL DEFAULT '',

        etiqueta_pose TEXT NOT NULL DEFAULT '',

        embedding_voz TEXT NOT NULL DEFAULT '',

        embedding_pose TEXT NOT NULL DEFAULT '',

        palabra_ingreso TEXT NOT NULL DEFAULT '',

        plantilla_voz TEXT NOT NULL DEFAULT '',

        plantilla_postura TEXT NOT NULL DEFAULT ''

    )
    """)

    # ============================
    # TABLA HISTORIAL
    # ============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        usuario TEXT NOT NULL,

        problema TEXT NOT NULL,

        respuesta TEXT NOT NULL,

        procedimiento TEXT NOT NULL DEFAULT '',

        resultado TEXT NOT NULL DEFAULT '',

        fecha TEXT NOT NULL,

        hora TEXT NOT NULL,

        FOREIGN KEY(usuario) REFERENCES usuarios(usuario)

    )
    """)

    conexion.commit()
    conexion.close()

    # Migración de tablas existentes (bases de datos previas)
    migrar_historial()
    migrar_usuarios_facial()
    migrar_usuarios_embedding()
    migrar_usuarios_biometria()
    migrar_usuarios_ingreso()
    migrar_usuarios_tm()
    migrar_seguridad()
    migrar_clases()

    print("===================================")
    print("Base de datos creada correctamente.")
    print("===================================")


if __name__ == "__main__":
    crear_base_datos()
