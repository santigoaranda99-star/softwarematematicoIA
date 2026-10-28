import re


def separar_procedimiento_resultado(respuesta):
    """
    Separa la respuesta de la IA en procedimiento y resultado.

    Heurística: busca un marcador tipo 'RESULTADO:' o, si no, la última
    línea del texto que contenga '='.
    """
    texto = (respuesta or "").strip()

    if not texto:
        return "", ""

    lineas = texto.splitlines()

    # 1) Marcador 'Resultado:' (última aparición)
    indice_marcador = None

    for i, linea in enumerate(lineas):
        if re.search(r"^\s*resultado\s*:", linea, re.IGNORECASE):
            indice_marcador = i

    if indice_marcador is not None:
        procedimiento = "\n".join(lineas[:indice_marcador]).strip()
        resultado = "\n".join(lineas[indice_marcador:]).strip()
        return procedimiento, resultado

    # 2) Última línea con '='
    for i in range(len(lineas) - 1, -1, -1):
        if "=" in lineas[i]:
            antes, despues = lineas[i].split("=", 1)

            procedimiento = "\n".join(lineas[:i]).strip()

            if procedimiento:
                procedimiento += "\n"

            procedimiento += f"{antes.strip()} ="

            resultado = despues.strip()

            resto = "\n".join(lineas[i + 1:]).strip()

            if resto:
                resultado = f"{resultado}\n{resto}"

            return procedimiento, resultado

    return texto, ""
