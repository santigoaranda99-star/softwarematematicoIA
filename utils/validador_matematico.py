import re

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr,
        standard_transformations,
        implicit_multiplication_application,
        convert_xor,
    )
    _TRANSFORMACIONES = (
        standard_transformations + (implicit_multiplication_application,) + (convert_xor,)
    )
    _SYMPY_DISPONIBLE = True
except ImportError:
    sp = None
    _TRANSFORMACIONES = ()
    _SYMPY_DISPONIBLE = False


def _extraer_numero(respuesta):
    """Busca el último número de la respuesta de la IA (ej: 'x = 4')."""
    patrones = [
        r"RESULTADO\s*:?\s*([-+]?\d+(?:[.,]\d+)?)",
        r"Resultado\s*:?\s*([-+]?\d+(?:[.,]\d+)?)",
        r"=\s*([-+]?\d+(?:[.,]\d+)?)",
    ]

    for patron in patrones:

        coincidencias = list(re.finditer(patron, respuesta))

        if not coincidencias:
            continue

        valor = coincidencias[-1].group(1).replace(",", ".")

        try:
            return float(valor)
        except ValueError:
            continue

    return None


def _expresion_numerica(problema):
    """Convierte un problema simple en una expresión/ecuación de sympy o None."""
    texto = (problema or "").strip()

    if not texto:
        return None

    # Quitar preguntas y texto posterior a '¿' o '?'
    texto = re.split(r"[?¿]", texto)[0]

    # Ecuación: 'x + 3 = 7'
    if "=" in texto:

        izquierda, derecha = texto.split("=", 1)

        try:
            return sp.Eq(
                parse_expr(izquierda, transformations=_TRANSFORMACIONES),
                parse_expr(derecha, transformations=_TRANSFORMACIONES)
            )
        except Exception:
            return None

    # Expresión numérica directa
    try:
        expr = parse_expr(texto, transformations=_TRANSFORMACIONES)
        if not expr.free_symbols:
            return expr
    except Exception:
        pass

    # Quitar palabras y probar con lo que queda
    limpio = re.sub(r"[^0-9+\-*/().^xX ]", "", texto).strip()

    if not limpio:
        return None

    try:
        expr = parse_expr(limpio, transformations=_TRANSFORMACIONES)
        if not expr.free_symbols:
            return expr
    except Exception:
        return None

    return None


def _formatear(numero):
    """Formatea un número flotante para mostrarlo de forma compacta."""
    if float(numero).is_integer():
        return str(int(numero))

    return f"{numero:g}"


def validar_resultado(problema, respuesta):
    """
    Intenta verificar numéricamente el resultado de la IA usando sympy.

    Devuelve:
      - ('verificado', mensaje) si el resultado coincide con lo calculado.
      - ('no_verificable', None) si no se pudo validar (falla silenciosa).
    """
    if not _SYMPY_DISPONIBLE:
        return "no_verificable", None

    try:

        numero = _extraer_numero(respuesta)

        if numero is None:
            return "no_verificable", None

        expresion = _expresion_numerica(problema)

        if expresion is None:
            return "no_verificable", None

        # Ecuación: comparar con sus soluciones
        if isinstance(expresion, sp.Eq):

            soluciones = sp.solve(expresion)

            numericas = []

            for s in soluciones:

                try:
                    numericas.append(float(s.evalf()))
                except Exception:
                    continue

            if not numericas:
                return "no_verificable", None

            if any(abs(n - numero) < 1e-6 for n in numericas):
                return (
                    "verificado",
                    f"El resultado {_formatear(numero)} coincide con la "
                    "solución calculada por el software."
                )

            return "no_verificable", None

        # Expresión numérica: comparar con el valor calculado
        valor = float(expresion.evalf())

        if abs(valor - numero) < 1e-6:
            return (
                "verificado",
                f"El resultado {_formatear(numero)} coincide con el valor "
                f"calculado: {_formatear(valor)}."
            )

        return "no_verificable", None

    except Exception:
        return "no_verificable", None
