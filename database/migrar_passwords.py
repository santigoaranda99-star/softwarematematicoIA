from database.conexion import obtener_conexion
from utils.seguridad import es_hash, generar_hash


def migrar_passwords():
    """
    Convierte las contraseñas en texto plano a hash SHA-256 con salt.

    Se ejecuta en el arranque de la aplicación (ver main.py). Los usuarios
    cuyo valor ya es un hash se dejan intactos.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT id, contraseña FROM usuarios")

    filas = cursor.fetchall()

    migradas = 0

    for fila in filas:

        contraseña = fila["contraseña"]

        if not contraseña or es_hash(contraseña):
            continue

        cursor.execute(
            "UPDATE usuarios SET contraseña=? WHERE id=?",
            (generar_hash(contraseña), fila["id"])
        )

        migradas += 1

    conexion.commit()
    conexion.close()

    return migradas


if __name__ == "__main__":

    total = migrar_passwords()

    print(f"Contraseñas migradas a hash: {total}")
