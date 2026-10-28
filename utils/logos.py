# -*- coding: utf-8 -*-
"""Logo oficial con recorte circular reutilizable."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath


def crear_logo_circular(ruta, tamano):
    """Devuelve el logo de `ruta` recortado en un circulo perfecto.

    La imagen se escala con KeepAspectRatioByExpanding (llena el cuadrado
    sin deformarse), se centra recortando el sobrante y se aplica una
    mascara circular via QPainterPath con antialiasing. El archivo
    original nunca se modifica.
    """
    tamano = int(tamano)

    origen = QPixmap(ruta)
    if origen.isNull():
        return QPixmap()

    base = origen.scaled(
        tamano, tamano,
        Qt.KeepAspectRatioByExpanding,
        Qt.SmoothTransformation,
    )

    x = max(0, (base.width() - tamano) // 2)
    y = max(0, (base.height() - tamano) // 2)
    cuadrado = base.copy(x, y, tamano, tamano)

    resultado = QPixmap(tamano, tamano)
    resultado.fill(Qt.transparent)

    pintor = QPainter(resultado)
    pintor.setRenderHint(QPainter.Antialiasing, True)

    mascara = QPainterPath()
    mascara.addEllipse(0, 0, tamano, tamano)
    pintor.setClipPath(mascara)
    pintor.drawPixmap(0, 0, cuadrado)
    pintor.end()

    return resultado
