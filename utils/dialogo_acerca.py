# -*- coding: utf-8 -*-
"""Diálogo 'Acerca de' con perfil del desarrollador.

Muestra la foto personal desde images/foto_perfil.png (recortada en
círculo con borde azul). Si la imagen no existe, muestra un avatar de
respaldo con la inicial. Compartido por todos los módulos.
"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.rutas import ruta_recurso

DESARROLLADOR = "Santiago Peña Aranda"
ROL = "Desarrollador"
APP_NOMBRE = "Software Matemático IA"
APP_VERSION = "v1.1"


def _ruta_foto():
    """Busca la foto personal aceptando varios formatos.

    Prioridad: images/foto_perfil.(png|jpg|jpeg); si no existe,
    usa images/presentacion.png como foto de perfil.
    """
    for ext in ("foto_perfil.png", "foto_perfil.jpg", "foto_perfil.jpeg"):
        ruta = ruta_recurso(f"images/{ext}")
        if os.path.exists(ruta):
            return ruta
    ruta_presentacion = ruta_recurso("images/presentacion.png")
    if os.path.exists(ruta_presentacion):
        return ruta_presentacion
    return ruta_recurso("images/foto_perfil.png")


def _pixmap_circular(ruta_imagen, tamano):
    """Devuelve la foto recortada en circulo con borde azul."""
    base = QPixmap(tamano, tamano)
    base.fill(Qt.transparent)

    fuente = QPixmap(ruta_imagen)
    if not fuente.isNull():
        fuente = fuente.scaled(
            tamano - 8,
            tamano - 8,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
    else:
        # Avatar de respaldo: inicial sobre degradado azul
        fuente = QPixmap(tamano - 8, tamano - 8)
        fuente.fill(Qt.transparent)
        p = QPainter(fuente)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#1D4ED8"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, tamano - 8, tamano - 8)
        p.setPen(Qt.white)
        f = p.font()
        f.setPixelSize(int((tamano - 8) * 0.42))
        f.setBold(True)
        p.setFont(f)
        p.drawText(fuente.rect(), Qt.AlignCenter, DESARROLLADOR[0])
        p.end()

    p = QPainter(base)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(4, 4, tamano - 8, tamano - 8)
    p.setClipPath(path)
    p.drawPixmap(4, 4, fuente)
    p.setClipping(False)
    lapiz = QPen(QColor("#3B82F6"))
    lapiz.setWidth(3)
    p.setPen(lapiz)
    p.drawEllipse(4, 4, tamano - 8, tamano - 8)
    p.end()
    return base


def mostrar_acerca(parent, titulo_modulo, stack):
    """Abre el dialogo 'Acerca de' con el perfil del desarrollador."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Acerca de")
    dlg.setFixedSize(340, 430)
    dlg.setStyleSheet(
        """
        QDialog { background-color: #131F49; }
        QLabel#nombre {
            color: #FFFFFF; font-size: 18px; font-weight: bold;
            background: transparent;
        }
        QLabel#rol {
            color: #FFFFFF; font-size: 11px; font-weight: bold;
            background-color: #2563EB; border-radius: 10px;
            padding: 3px 14px;
        }
        QLabel#appTitulo {
            color: #EDF1FA; font-size: 15px; font-weight: bold;
            background: transparent;
        }
        QLabel#detalle {
            color: #B9C6DE; font-size: 12px; background: transparent;
        }
        QLabel#stack {
            color: #8CA0BC; font-size: 11px; background: transparent;
        }
        QFrame#linea {
            background: rgba(255, 255, 255, 0.16); max-height: 1px;
            border: none;
        }
        QPushButton#btnCerrar {
            background-color: #2563EB; color: #FFFFFF;
            border: none; border-radius: 8px;
            padding: 9px 26px; font-weight: bold; font-size: 13px;
        }
        QPushButton#btnCerrar:hover { background-color: #1D4ED8; }
        """
    )

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(24, 22, 24, 20)
    lay.setSpacing(6)
    lay.setAlignment(Qt.AlignHCenter)

    foto = QLabel()
    foto.setAlignment(Qt.AlignCenter)
    foto.setPixmap(_pixmap_circular(_ruta_foto(), 116))
    lay.addWidget(foto)
    lay.addSpacing(8)

    nombre = QLabel(DESARROLLADOR)
    nombre.setObjectName("nombre")
    nombre.setAlignment(Qt.AlignCenter)
    lay.addWidget(nombre)

    fila_rol = QHBoxLayout()
    fila_rol.addStretch()
    rol = QLabel(ROL)
    rol.setObjectName("rol")
    fila_rol.addWidget(rol)
    fila_rol.addStretch()
    lay.addLayout(fila_rol)

    lay.addSpacing(8)
    linea = QFrame()
    linea.setObjectName("linea")
    linea.setFrameShape(QFrame.NoFrame)
    linea.setFixedHeight(1)
    lay.addWidget(linea)
    lay.addSpacing(8)

    app_titulo = QLabel(f"{titulo_modulo}")
    app_titulo.setObjectName("appTitulo")
    app_titulo.setAlignment(Qt.AlignCenter)
    lay.addWidget(app_titulo)

    version = QLabel(f"{APP_NOMBRE} \u2014 {APP_VERSION}")
    version.setObjectName("detalle")
    version.setAlignment(Qt.AlignCenter)
    lay.addWidget(version)

    stack_lbl = QLabel(stack)
    stack_lbl.setObjectName("stack")
    stack_lbl.setAlignment(Qt.AlignCenter)
    stack_lbl.setWordWrap(True)
    lay.addWidget(stack_lbl)

    lay.addStretch()

    fila_btn = QHBoxLayout()
    fila_btn.addStretch()
    btn = QPushButton("Cerrar")
    btn.setObjectName("btnCerrar")
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(dlg.accept)
    fila_btn.addWidget(btn)
    fila_btn.addStretch()
    lay.addLayout(fila_btn)

    dlg.exec_()
