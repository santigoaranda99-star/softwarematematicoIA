# -*- coding: utf-8 -*-
"""Utilidades de posicionamiento de ventanas."""


def centrar_ventana(widget):
    """Centra la ventana en la pantalla disponible.

    Si la ventana es más grande que la pantalla, se ancla al borde
    superior-izquierdo de la zona útil.
    Funciona tanto antes como después de show().
    """
    from PyQt5.QtGui import QGuiApplication

    pantalla = QGuiApplication.primaryScreen()
    if pantalla is None:
        return

    geom = pantalla.availableGeometry()

    # Si el widget aún no fue mostrado, usamos sizeHint para obtener
    # dimensiones reales (resize() ya habrá sido llamado antes).
    w = widget.width() if widget.width() > 0 else widget.sizeHint().width()
    h = widget.height() if widget.height() > 0 else widget.sizeHint().height()

    x = geom.x() + max(0, (geom.width() - w) // 2)
    y = geom.y() + max(0, (geom.height() - h) // 2)
    widget.move(x, y)


def centrar_dialogo(dialogo, padre=None):
    """Centra un diálogo respecto a su ventana padre (o a la pantalla)."""
    if padre is not None and padre.isVisible():
        geo_p = padre.geometry()
        x = geo_p.x() + (geo_p.width() - dialogo.width()) // 2
        y = geo_p.y() + (geo_p.height() - dialogo.height()) // 2
        dialogo.move(x, y)
        return
    centrar_ventana(dialogo)
