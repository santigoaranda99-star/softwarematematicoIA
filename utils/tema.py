# -*- coding: utf-8 -*-
"""Modo oscuro/claro reutilizable para todas las ventanas.

instalar_modo_oscuro(ventana, qss_claro) agrega un boton flotante en la
esquina superior derecha que alterna entre la hoja de estilos original
y una version oscura generada automaticamente por sustitucion de la
paleta. La ventana gana self._modo_oscuro y self._alternar_tema().
"""

# Paleta clara -> paleta oscura. Sustitucion en UN solo pase (sin
# colisiones en cadena): fondos oscuros, y TODO texto aclarado para que
# sea legible sobre fondo oscuro.
MAPA_OSCURO = {
    # Fondos / superficies
    "#F8FAFC": "#0B1220",
    "#F1F5F9": "#0C1526",
    "#EFF6FF": "#101B33",
    "#FFFFFF": "#151F38",
    "#F8F9FB": "#0E1830",
    "#F8FAFF": "#101B33",
    "#F0F6FF": "#101B33",
    "#EEF2F7": "#16213C",
    # Textos oscuros -> claros (legibilidad)
    "#0F172A": "#E2E8F0",
    "#111827": "#E2E8F0",
    "#1E293B": "#CBD5E1",
    "#334155": "#94A3B8",
    "#475569": "#94A3B8",
    "#64748B": "#8CA0BC",
    "#6B7280": "#9CA3AF",
    "#4B5563": "#9CA3AF",
    "#374151": "#D1D5DB",
    "#1E3A8A": "#BFDBFE",
    # Bordes
    "#D1D5DB": "#334155",
    "#E5E7EB": "#26334D",
    "#E2E8F0": "#223052",
    "#DBEAFE": "#1E293B",
    "#CBD5E1": "#3B4A63",
    # Acentos y estados: version clara para contrastar en oscuro
    "#2563EB": "#3B82F6",
    "#059669": "#34D399",
    "#047857": "#34D399",
    "#15803D": "#4ADE80",
    "#DC2626": "#F87171",
    "#B91C1C": "#FCA5A5",
    "#D97706": "#FBBF24",
    "#B45309": "#FBBF24",
    "#7C3AED": "#A78BFA",
    "#C2410C": "#FB923C",
}

ESTILO_BOTON_TEMA = """
    QPushButton#btnFlotanteTema {{
        background: {fondo};
        color: {texto};
        border: 1px solid {borde};
        border-radius: 14px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#btnFlotanteTema:hover {{
        background: {hover};
    }}
"""


import re


def transformar_a_oscuro(qss):
    """Devuelve una version oscura de la hoja de estilos dada.

    Un unico pase sobre cada codigo hexadecimal evita que un color ya
    sustituido vuelva a transformarse (colisiones en cadena).
    """

    def _sustituir(m):
        return MAPA_OSCURO.get(m.group(0).upper(), m.group(0))

    return re.sub(r"#[0-9A-Fa-f]{6}\b", _sustituir, qss)


def _estilo_boton(oscuro):
    if oscuro:
        return ESTILO_BOTON_TEMA.format(
            fondo="#1E293B", texto="#93C5FD",
            borde="#334155", hover="#26334D",
        )
    return ESTILO_BOTON_TEMA.format(
        fondo="#FFFFFF", texto="#2563EB",
        borde="#DBEAFE", hover="#DBEAFE",
    )


def instalar_modo_oscuro(ventana, qss_claro, margen=12):
    """Agrega boton de tema flotante y alterna claro/oscuro en la ventana.

    El boton se coloca automaticamente en la primera esquina libre: se
    prefiere abajo-derecha y solo si todas estan ocupadas se usa la
    superior derecha. Asi nunca tapa botones como "Volver".
    """
    from PyQt5.QtWidgets import QPushButton, QWidget
    from PyQt5.QtCore import Qt, QRect

    ventana._modo_oscuro = False
    ventana._qss_tema_base = qss_claro

    btn = QPushButton("\U0001F312 Modo oscuro", ventana)
    btn.setObjectName("btnFlotanteTema")
    btn.setCursor(Qt.PointingHandCursor)
    ventana.btnTemaFlotante = btn

    def aplicar(oscuro):
        base = ventana._qss_tema_base
        hoja = transformar_a_oscuro(base) if oscuro else base
        ventana.setStyleSheet(hoja + _estilo_boton(oscuro))
        btn.setText(
            "\u2600 Modo claro" if oscuro else "\U0001F312 Modo oscuro"
        )

    ventana._alternar_tema = aplicar

    def alternar():
        aplicar(not ventana._modo_oscuro)
        ventana._modo_oscuro = not ventana._modo_oscuro

    btn.clicked.connect(alternar)

    def rectangulo_en(nombre_esquina, ancho_b, alto_b):
        w, h = ventana.width(), ventana.height()
        x = (w - ancho_b - margen) if "derecha" in nombre_esquina else margen
        y = margen if nombre_esquina.startswith("arriba") \
            else h - alto_b - margen
        return QRect(x, y, ancho_b, alto_b)

    def _interactivos():
        """Rects de widgets interactivos que no se deben tapar jamas."""
        from PyQt5.QtWidgets import (
            QAbstractButton, QLineEdit, QTextEdit, QPlainTextEdit,
            QComboBox, QListView, QTableView, QTreeView, QSlider,
        )
        clases = (QAbstractButton, QLineEdit, QTextEdit, QPlainTextEdit,
                  QComboBox, QListView, QTableView, QTreeView, QSlider)
        rects = []
        for hijo in ventana.findChildren(
                QWidget, options=Qt.FindDirectChildrenOnly):
            if hijo is btn or not hijo.isVisible():
                continue
            g = hijo.geometry()
            # Paneles de fondo que cubren casi todo: no son un elemento
            # concreto que el boton pueda estorbar.
            if g.width() >= ventana.width() - 4 \
                    and g.height() >= ventana.height() * 0.85:
                continue
            if isinstance(hijo, clases):
                rects.append(g)
            else:
                for nieto in hijo.findChildren(clases):
                    rects.append(
                        QRect(hijo.mapTo(ventana, nieto.geometry().topLeft()),
                              nieto.size()))
        return rects

    def _decorativos():
        rects = []
        for hijo in ventana.findChildren(
                QWidget, options=Qt.FindDirectChildrenOnly):
            if hijo is btn or not hijo.isVisible():
                continue
            g = hijo.geometry()
            if g.width() >= ventana.width() - 4 \
                    and g.height() >= ventana.height() * 0.85:
                continue
            rects.append(g)
        return rects

    def elegir_esquina():
        decor = _decorativos()
        inter = _interactivos()
        mejor = None
        for orden, esquina in enumerate(
                ("abajo-derecha", "abajo-izquierda",
                 "arriba-izquierda", "arriba-derecha")):
            r = rectangulo_en(esquina, btn.width(), btn.height())
            if any(r.intersects(g) for g in inter):
                nivel = 2
            elif any(r.intersects(g) for g in decor):
                nivel = 1
            else:
                nivel = 0
            candidato = (nivel, orden)
            if mejor is None or candidato < mejor[0]:
                mejor = (candidato, esquina)
            if nivel == 0:
                break
        return mejor[1]

    def reposicionar():
        btn.adjustSize()
        ventana._tema_esquina = elegir_esquina()
        r = rectangulo_en(ventana._tema_esquina, btn.width(), btn.height())
        btn.move(r.x(), r.y())
        btn.raise_()

    resize_original = ventana.resizeEvent

    def resize_event(evento):
        if resize_original is not None:
            resize_original(evento)
        else:
            QWidget.resizeEvent(ventana, evento)
        reposicionar()

    ventana.resizeEvent = resize_event

    aplicar(False)
    reposicionar()
    btn.show()
    from PyQt5.QtCore import QTimer

    def reasentar():
        try:
            reposicionar()
        except RuntimeError:
            pass

    QTimer.singleShot(0, reasentar)
    QTimer.singleShot(120, reasentar)


def instalar_modo_oscuro_al_mostrar(ventana):
    """Difiere instalar_modo_oscuro hasta el primer show() de la ventana.

    Util cuando la hoja de estilos definitiva se construye durante todo
    el __init__: en el primer show() el styleSheet() ya esta completo.
    """
    from PyQt5.QtWidgets import QWidget

    show_original = ventana.showEvent

    def show_event(evento):
        if show_original is not None:
            show_original(evento)
        else:
            QWidget.showEvent(ventana, evento)
        if not getattr(ventana, "_tema_instalado", False):
            ventana._tema_instalado = True
            instalar_modo_oscuro(ventana, ventana.styleSheet())

    ventana.showEvent = show_event
