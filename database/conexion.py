import sqlite3
import os

from utils.rutas import es_ejecutable, ruta_base

# Ruta de la base de datos.
# - Empaquetado (.exe): junto al ejecutable, para que sea persistente.
# - Desarrollo: en la carpeta database/.
# - La variable de entorno SOFTWARE_MATEMATICO_DB permite usar otra ruta.
if es_ejecutable():
    DB_NAME = os.path.join(ruta_base(), "software_matematico.db")
else:
    DB_NAME = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "software_matematico.db"
    )

DB_NAME = os.environ.get("SOFTWARE_MATEMATICO_DB") or DB_NAME


def obtener_conexion():
    """
    Retorna una conexión a la base de datos SQLite.
    """
    conexion = sqlite3.connect(DB_NAME)
    conexion.row_factory = sqlite3.Row
    return conexion
