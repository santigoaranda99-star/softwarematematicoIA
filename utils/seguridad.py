import hashlib
import secrets

SEPARADOR = "$"


def generar_hash(contraseña):
    """Genera un hash SHA-256 con salt aleatorio (formato: salt$hash)."""
    salt = secrets.token_hex(16)
    hash_hex = hashlib.sha256((salt + contraseña).encode("utf-8")).hexdigest()
    return f"{salt}{SEPARADOR}{hash_hex}"


def es_hash(almacenado):
    """Indica si el valor almacenado tiene formato de hash con salt."""
    if not almacenado or SEPARADOR not in almacenado:
        return False

    partes = almacenado.split(SEPARADOR)

    if len(partes) != 2:
        return False

    salt, hash_hex = partes

    if len(salt) != 32 or len(hash_hex) != 64:
        return False

    try:
        int(salt, 16)
        int(hash_hex, 16)
    except ValueError:
        return False

    return True


def verificar_contraseña(contraseña, almacenado):
    """Verifica una contraseña contra el valor almacenado (hash o texto plano)."""
    if not almacenado:
        return False

    if es_hash(almacenado):
        salt, hash_hex = almacenado.split(SEPARADOR)
        prueba = hashlib.sha256(
            (salt + contraseña).encode("utf-8")
        ).hexdigest()
        return secrets.compare_digest(prueba, hash_hex)

    # Valor antiguo en texto plano (antes de la migración)
    return secrets.compare_digest(almacenado, contraseña or "")
