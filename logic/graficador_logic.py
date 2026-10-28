# -*- coding: utf-8 -*-
"""
graficador_logic.py
===================
Logica de calculo simbolico del Graficador (sympy + numpy).

Este modulo NO depende de PyQt5: solo matematica pura, para que la UI
(interfaces/graficador.py) y los tests puedan usarlo de forma aislada.
"""

import re

import numpy as np


# =========================================================
# FORMATO DE NUMEROS
# =========================================================

def fmt_numero(num, decimales=2):
    """Formatea un numero de forma compacta."""
    try:
        if abs(num - round(num)) < 1e-9:
            return str(int(round(num)))
        return f"{num:.{decimales}f}".rstrip("0").rstrip(".")
    except Exception:
        return str(num)


# Alias internos para compatibilidad con codigo existente
_fmt = fmt_numero


# =========================================================
# PARSING DE EXPRESIONES
# =========================================================

def parsear_expresion(texto, local_dict=None):
    """Parsea una expresion con sympy de forma segura.

    Soporta:
      - ^ como potencia          (convert_xor)
      - multiplicacion implicita (2x -> 2*x)
      - funciones estandar sin/cos/tan/log/sqrt/exp
    """
    from sympy.parsing.sympy_parser import (
        parse_expr,
        standard_transformations,
        implicit_multiplication_application,
        convert_xor,
    )

    transformations = (
        standard_transformations
        + (implicit_multiplication_application,)
        + (convert_xor,)
    )

    return parse_expr(
        texto,
        local_dict=local_dict or {},
        transformations=transformations,
    )


# Alias interno usado por la ventana
_parsear_expresion = parsear_expresion


# ---------------------------------------------------------
# Normalizacion de entrada de usuario
# ---------------------------------------------------------

_SUPERINDICES = {
    "\u2070": "^0", "\u00b9": "^1", "\u00b2": "^2", "\u00b3": "^3",
    "\u2074": "^4", "\u2075": "^5", "\u2076": "^6", "\u2077": "^7",
    "\u2078": "^8", "\u2079": "^9",
}


def preparar_texto(texto):
    """Adapta formatos comunes que un usuario puede escribir.

    - f(x)=expr / g(t)=expr / y=expr  ->  expr
    - superindices unicode            x²  -> x^2
    - raiz unicode                    √x  -> sqrt(x)
    - simbolos                        × ÷ π −
    - seno en espanol                 sen(x) -> sin(x)
    - decimal con coma                0,5    -> 0.5
    """
    t = texto.strip()

    # Prefijo de funcion: f(x)=... / g(t)=... -> solo la expresion
    m = re.match(r"^\s*[a-zA-Z_]\w*\s*\(\s*[a-zA-Z_]\w*\s*\)\s*=", t)
    if m:
        t = t[m.end():].strip()
    else:
        # Prefijo y=...
        t = re.sub(r"^\s*y\s*=", "", t).strip()

    # Superindices unicode: x² -> x^2
    for simbolo, reemplazo in _SUPERINDICES.items():
        t = t.replace(simbolo, reemplazo)

    # Simbolos matematicos comunes
    t = re.sub(r"\u221a\s*\(", "sqrt(", t)                   # raiz con parentesis
    t = re.sub(r"\u221a\s*([0-9a-zA-Z.]+)", r"sqrt(\1)", t)  # raiz de token
    t = t.replace("\u00d7", "*")      # multiplicacion
    t = t.replace("\u00f7", "/")      # division
    t = t.replace("\u03c0", "pi")     # pi
    t = t.replace("\u2212", "-")      # guion menos unicode

    # Seno en espanol: sen(x) -> sin(x)
    t = re.sub(r"\bsen\b", "sin", t)

    # Decimal con coma: 0,5 -> 0.5
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)

    return t


# Alias interno usado por la ventana
_preparar_texto = preparar_texto


# =========================================================
# TITULO MATEMATICO (matplotlib mathtext)
# =========================================================

def titulo_matematico(expr_sympy, var="x"):
    """Devuelve la funcion formateada para titulos de matplotlib.

    Ej: '$f(x) = - 5 x^{2} + 20 x + 2$' se renderiza como
        f(x) = -5x² + 20x + 2
    """
    try:
        import sympy as sp

        latex = sp.latex(expr_sympy)
        return rf"$f({var}) = {latex}$"
    except Exception:
        return f"f({var}) = {expr_sympy}"


# =========================================================
# ANALISIS SIMBOLICO COMPLETO
# =========================================================

def analizar_funcion(expr_sympy, var, x_min, x_max):
    """
    Analiza la funcion y devuelve un diccionario con:
    tipo, maximos, minimos, inter_y, inter_x, eje_simetria,
    dominio, rango, rango_global, creciente, decreciente,
    comportamiento.
    """
    import sympy as sp

    v = sp.Symbol(var)
    a = {
        "tipo": "Función general",
        "maximos": [],
        "minimos": [],
        "inter_y": None,
        "inter_x": [],
        "eje_simetria": None,
        "dominio": "Todos los reales",
        "rango": None,
        "rango_global": None,
        "creciente": [],
        "decreciente": [],
        "comportamiento": "",
        "abre": None,
    }

    # ---------- Tipo de funcion ----------
    try:
        p = sp.Poly(expr_sympy, v)
        grado = p.degree()
        tipos = {
            0: "Constante",
            1: "Lineal",
            2: "Cuadrática",
            3: "Cúbica",
        }
        a["tipo"] = tipos.get(grado, f"Polinómica (grado {grado})")
    except Exception:
        try:
            if expr_sympy.atoms(sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc):
                a["tipo"] = "Trigonométrica"
            elif expr_sympy.atoms(sp.log):
                a["tipo"] = "Logarítmica"
            elif expr_sympy.atoms(sp.exp):
                a["tipo"] = "Exponencial"
            else:
                num, den = sp.fraction(sp.together(expr_sympy))
                a["tipo"] = "Racional" if den.has(v) else "Función general"
        except Exception:
            a["tipo"] = "Función general"

    # ---------- Derivadas ----------
    try:
        d1 = sp.diff(expr_sympy, v)
        d2 = sp.diff(expr_sympy, v, 2)
    except Exception:
        d1 = d2 = None

    # ---------- Puntos criticos (maximos / minimos) ----------
    criticos = []
    if d1 is not None:
        try:
            for s in sp.solve(sp.Eq(d1, 0), v):
                try:
                    if s.is_real:
                        criticos.append(float(s))
                except Exception:
                    continue
        except Exception:
            criticos = []

        for c in criticos:
            if not (x_min <= c <= x_max):
                continue
            try:
                fy = float(expr_sympy.subs(v, c))
                s2 = float(d2.subs(v, c))
                if s2 < 0:
                    a["maximos"].append((c, fy))
                elif s2 > 0:
                    a["minimos"].append((c, fy))
            except Exception:
                continue

    # ---------- Intercepto Y ----------
    try:
        iy = expr_sympy.subs(v, 0)
        if iy.is_number and iy.is_finite:
            a["inter_y"] = float(iy)
    except Exception:
        pass

    # ---------- Interceptos X ----------
    try:
        for s in sp.solve(sp.Eq(expr_sympy, 0), v):
            try:
                sf = float(s)
                if x_min <= sf <= x_max:
                    a["inter_x"].append(sf)
            except (TypeError, ValueError):
                continue
    except Exception:
        pass

    # ---------- Eje de simetria (cuadratica) ----------
    if a["tipo"] == "Cuadrática":
        try:
            coefs = sp.Poly(expr_sympy, v).all_coeffs()
            aa, bb = coefs[0], coefs[1]
            a["eje_simetria"] = float(-bb / (2 * aa))
            a["abre"] = "abajo" if aa < 0 else "arriba"
        except Exception:
            pass

    # ---------- Dominio (singularidades) ----------
    try:
        sing = sp.singularities(expr_sympy, v)
        finitas = []
        for s in sing:
            try:
                sf = float(s)
                finitas.append(fmt_numero(sf))
            except Exception:
                continue
        if finitas:
            a["dominio"] = "Reales, excepto x = " + ", ".join(finitas)
    except Exception:
        pass

    # ---------- Muestreo numerico ----------
    xs_sample = np.linspace(x_min, x_max, 500)
    try:
        f_num = sp.lambdify(v, expr_sympy, modules=["numpy"])
        ys_sample = np.asarray(f_num(xs_sample), dtype=float)
        if ys_sample.ndim == 0:
            ys_sample = np.full_like(xs_sample, float(ys_sample))
        ys_valid = ys_sample[np.isfinite(ys_sample)]
        if len(ys_valid) > 0:
            a["rango"] = (float(np.min(ys_valid)), float(np.max(ys_valid)))
    except Exception:
        ys_sample = np.full_like(xs_sample, np.nan)

    # ---------- Rango global (simbolico cuando es posible) ----------
    try:
        if a["tipo"] == "Cuadrática" and a["abre"] and a["eje_simetria"] is not None:
            vy = float(expr_sympy.subs(v, sp.Float(a["eje_simetria"])))
            a["rango_global"] = (
                (vy, np.inf) if a["abre"] == "arriba" else (-np.inf, vy)
            )
        elif a["tipo"] == "Lineal":
            a["rango_global"] = ("todos", None)
        elif a["tipo"] == "Constante":
            cval = float(expr_sympy.subs(v, 0))
            a["rango_global"] = (cval, cval)
        elif d1 is not None:
            lim_izq = sp.limit(expr_sympy, v, -sp.oo)
            lim_der = sp.limit(expr_sympy, v, sp.oo)

            candidatos = []
            for c in criticos:
                try:
                    fy = float(expr_sympy.subs(v, c))
                    if np.isfinite(fy):
                        candidatos.append(fy)
                except Exception:
                    pass

            finitos = []
            sube = baja = False
            for L in (lim_izq, lim_der):
                try:
                    Lf = float(L)
                    if np.isfinite(Lf):
                        finitos.append(Lf)
                    elif np.isposinf(Lf):
                        sube = True
                    else:
                        baja = True
                except Exception:
                    pass

            todos_val = candidatos + finitos
            lo = -np.inf if baja else (min(todos_val) if todos_val else None)
            hi = np.inf if sube else (max(todos_val) if todos_val else None)
            if lo is not None and hi is not None:
                a["rango_global"] = (lo, hi)
    except Exception:
        a["rango_global"] = None

    # ---------- Crecimiento / decrecimiento ----------
    if d1 is not None:
        try:
            d1_num = sp.lambdify(v, d1, modules=["numpy"])
            ds = np.asarray(d1_num(xs_sample), dtype=float)
            if ds.ndim == 0:
                ds = np.full_like(xs_sample, float(ds))
            ds = np.nan_to_num(ds, nan=0.0)

            estado = ds[0] > 0
            inicio = 0
            for i in range(1, len(ds)):
                est = ds[i] > 0
                if est != estado:
                    tramo = (float(xs_sample[inicio]), float(xs_sample[i]))
                    if estado:
                        a["creciente"].append(tramo)
                    else:
                        a["decreciente"].append(tramo)
                    estado = est
                    inicio = i
            tramo_final = (float(xs_sample[inicio]), float(xs_sample[-1]))
            if estado:
                a["creciente"].append(tramo_final)
            else:
                a["decreciente"].append(tramo_final)
        except Exception:
            pass

    # ---------- Comportamiento en el infinito ----------
    try:
        lim_pos = sp.limit(expr_sympy, v, sp.oo)
        lim_neg = sp.limit(expr_sympy, v, -sp.oo)

        def _simbolo_lim(lim):
            s = str(lim)
            if s == "oo":
                return "+\u221e"
            if s == "-oo":
                return "-\u221e"
            try:
                return fmt_numero(float(lim))
            except Exception:
                return s

        a["comportamiento"] = (
            f"Al aumentar x \u2192 +\u221e, f({var}) \u2192 {_simbolo_lim(lim_pos)}\n"
            f"Al disminuir x \u2192 -\u221e, f({var}) \u2192 {_simbolo_lim(lim_neg)}"
        )
    except Exception:
        try:
            y_izq = ys_sample[0]
            y_der = ys_sample[-1]

            def _txt(yv):
                if not np.isfinite(yv):
                    return "\u00b1\u221e"
                return fmt_numero(float(yv))

            a["comportamiento"] = (
                f"En x = {fmt_numero(x_min)}: f({var}) \u2248 {_txt(y_izq)}\n"
                f"En x = {fmt_numero(x_max)}: f({var}) \u2248 {_txt(y_der)}"
            )
        except Exception:
            a["comportamiento"] = "No determinado"

    return a


# Alias interno usado por la ventana
_analizar_funcion = analizar_funcion


def construir_analisis_texto(a, var):
    """Genera la explicacion matematica en lenguaje sencillo."""

    lineas = []

    if a["tipo"] == "Cuadrática" and a["abre"]:
        lineas.append(f"Es una parábola que abre hacia {a['abre']}.")
    elif a["tipo"] == "Lineal":
        lineas.append("Es una recta con pendiente constante.")
    elif a["tipo"] == "Constante":
        lineas.append("Es una función constante.")
    else:
        lineas.append(f"Es una función {a['tipo'].lower()}.")

    if a["maximos"]:
        pts = ", ".join(f"({fmt_numero(x)}, {fmt_numero(y)})" for x, y in a["maximos"])
        lineas.append(f"Tiene punto máximo en {pts}.")
    if a["minimos"]:
        pts = ", ".join(f"({fmt_numero(x)}, {fmt_numero(y)})" for x, y in a["minimos"])
        lineas.append(f"Tiene punto mínimo en {pts}.")

    if a["inter_y"] is not None:
        lineas.append(f"Corta al eje Y en (0, {fmt_numero(a['inter_y'])}).")

    if a["inter_x"]:
        pts = ", ".join(f"({fmt_numero(x)}, 0)" for x in a["inter_x"])
        lineas.append(f"Corta al eje X en {pts}.")
    else:
        lineas.append("No corta al eje X en el rango visible.")

    return "\n".join(lineas)


# Alias interno usado por la ventana
_construir_analisis_texto = construir_analisis_texto
