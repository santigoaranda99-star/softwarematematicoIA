# =====================================================
# LOGICA DE CALCULADORA CIENTIFICA (pura, sin Qt)
# Evaluacion segura basada en sympy (sin eval de Python)
# =====================================================

import re

from sympy import (
    E,
    Float,
    GoldenRatio,
    EulerGamma,
    pi,
    zoo,
    oo,
    nan,
    im,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

_TRANSFORMACIONES = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

# Constantes disponibles en expresiones (simbolo -> valor)
CONSTANTES = (
    ("\u03c0", "pi", 3.141592653589793),
    ("e", "e", 2.718281828459045),
    ("\u03c6", "\u03c6", 1.618033988749895),
    ("\u03b3", "\u03b3", 0.577215664901532),
)


def _factores_modo(modo):
    """Factor de conversion segun el modo angular."""
    if modo == "DEG":
        return pi / 180, 180 / pi
    if modo == "GRAD":
        return pi / 200, 200 / pi
    return 1, 1


def _construir_entorno(modo):
    """Diccionario de nombres seguros para parse_expr."""

    f_in, f_inv = _factores_modo(modo)

    def directa(fn):
        return lambda x: fn(x * f_in)

    def inversa(fn):
        return lambda x: fn(x) * f_inv

    return {
        "sin": directa(_sin_segura),
        "cos": directa(_cos_segura),
        "tan": directa(_tan_segura),
        "asin": inversa(_asin_segura),
        "acos": inversa(_acos_segura),
        "atan": inversa(_atan_segura),
        "sinh": _sinh_segura,
        "cosh": _cosh_segura,
        "tanh": _tanh_segura,
        "asinh": _asinh_segura,
        "acosh": _acosh_segura,
        "atanh": _atanh_segura,
        "ln": _ln_segura,
        "log": _log10_segura,
        "log10": _log10_segura,
        "sqrt": _sqrt_segura,
        "raiz": _sqrt_segura,
        "abs": _abs_segura,
        "Abs": _abs_segura,
        "exp": _exp_segura,
        "pi": pi,
        "e": E,
        "\u03c0": pi,
        "\u03c6": GoldenRatio,
        "\u03b3": EulerGamma,
        "GoldenRatio": GoldenRatio,
        "EulerGamma": EulerGamma,
    }


# Wrappers para traducir errores de dominio a excepciones controladas

from sympy import (
    sin as _sin_sympy,
    cos as _cos_sympy,
    tan as _tan_sympy,
    asin as _asin_sympy,
    acos as _acos_sympy,
    atan as _atan_sympy,
    sinh as _sinh_sympy,
    cosh as _cosh_sympy,
    tanh as _tanh_sympy,
    asinh as _asinh_sympy,
    acosh as _acosh_sympy,
    atanh as _atanh_sympy,
    log as _log_sympy,
    sqrt as _sqrt_sympy,
    Abs as _abs_sympy,
    exp as _exp_sympy,
)


class DominioInvalido(Exception):
    pass


def _verificar_real(fn, *args):
    try:
        r = fn(*args)
    except (ValueError, ZeroDivisionError):
        raise DominioInvalido()
    if r.is_extended_real is False or (hasattr(r, "is_real") and r.is_real is False):
        raise DominioInvalido()
    return r


def _sin_segura(x): return _verificar_real(_sin_sympy, x)
def _cos_segura(x): return _verificar_real(_cos_sympy, x)
def _tan_segura(x): return _verificar_real(_tan_sympy, x)
def _asin_segura(x): return _verificar_real(_asin_sympy, x)
def _acos_segura(x): return _verificar_real(_acos_sympy, x)
def _atan_segura(x): return _verificar_real(_atan_sympy, x)
def _sinh_segura(x): return _verificar_real(_sinh_sympy, x)
def _cosh_segura(x): return _verificar_real(_cosh_sympy, x)
def _tanh_segura(x): return _verificar_real(_tanh_sympy, x)
def _asinh_segura(x): return _verificar_real(_asinh_sympy, x)
def _acosh_segura(x): return _verificar_real(_acosh_sympy, x)
def _atanh_segura(x): return _verificar_real(_atanh_sympy, x)
def _ln_segura(x): return _verificar_real(_log_sympy, x)
def _log10_segura(x): return _verificar_real(_log_sympy, x, 10)
def _sqrt_segura(x): return _verificar_real(_sqrt_sympy, x)
def _abs_segura(x): return _abs_sympy(x)
def _exp_segura(x): return _exp_segura_impl(x)


def _exp_segura_impl(x):
    try:
        return _exp_sympy(x)
    except (ValueError, OverflowError):
        raise DominioInvalido()


def preparar_texto(texto, ans=0.0):
    """Normaliza simbolos visuales a sintaxis que sympy entiende."""

    t = texto.strip()

    # Ans -> ultimo resultado
    t = re.sub(r"\bAns\b", f"({float(ans)!r})", t)

    # Porcentaje postfix: 50% -> (50/100)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", t)

    # Raiz cuadrada con operando simple o parentesis
    t = re.sub(r"\u221a\s*\(", "sqrt(", t)
    t = re.sub(r"\u221a\s*([0-9.eE]+)", r"sqrt(\1)", t)

    # Operadores y constantes visuales
    t = t.replace("\u00d7", "*")
    t = t.replace("\u00f7", "/")
    t = t.replace("\u2212", "-")
    t = t.replace("log\u2081\u2080", "log10")
    t = t.replace("\u03c0", "pi")
    t = t.replace("\u03c6", "(1+sqrt(5))/2")
    t = t.replace("\u03b3", "EulerGamma")

    return t


def evaluar(texto, modo="DEG", ans=0.0):
    """
    Evalua una expresion numerica de forma segura.

    Devuelve (True, float) o (False, mensaje_amigable).
    """

    if not texto or not texto.strip():
        return False, "Expresi\u00f3n vac\u00eda"

    try:
        preparada = preparar_texto(texto, ans)
        entorno = _construir_entorno(modo)
        entorno["ans"] = float(ans)

        expr = parse_expr(
            preparada,
            local_dict=entorno,
            transformations=_TRANSFORMACIONES,
            evaluate=True,
        )

        if not expr.is_number:
            return False, "Expresi\u00f3n inv\u00e1lida"

        valor = expr.evalf()

        if valor is zoo or valor is -zoo or valor is nan or valor is oo or valor is -oo:
            return False, "Resultado indefinido"

        parte_im = float(im(valor))

        if abs(parte_im) > 1e-12:
            return False, "Dominio matem\u00e1tico inv\u00e1lido"

        numero = float(valor)

        if numero != numero:  # NaN
            return False, "Resultado indefinido"

        return True, numero

    except DominioInvalido:
        return False, "Dominio matem\u00e1tico inv\u00e1lido"
    except ZeroDivisionError:
        return False, "Divisi\u00f3n por cero"
    except (OverflowError):
        return False, "Resultado demasiado grande"
    except Exception:
        return False, "Expresi\u00f3n inv\u00e1lida"


def formatear(numero, decimales=8):
    """Formato de pantalla: 8 decimales fijos (estilo calculadora)."""
    return f"{numero:.{decimales}f}"


def fmt_historial(numero):
    """Formato compacto para el historial: recorta ceros finales."""
    texto = f"{numero:.6f}".rstrip("0").rstrip(".")
    return texto if texto else "0"
