from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QApplication,
    QMessageBox,
    QLineEdit,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
    QListWidget,
    QCheckBox,
    QHeaderView,
    QSizePolicy,
)
from PyQt5.QtGui import QFont, QColor, QGuiApplication, QPixmap
from PyQt5.QtCore import Qt, QEvent
import sys
import re

import numpy as np

import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from utils.rutas import ruta_recurso
from utils.dialogo_acerca import mostrar_acerca


# =====================================================
# COLORES BASE
# =====================================================

_COLOR_FUN = "#2563EB"
_COLOR_GRID = "#CBD5E1"
_COLOR_TEXTO = "#0F172A"
_COLOR_SECUNDARIO = "#475569"
_COLOR_FONDO_CANVAS = "#FFFFFF"


def aplicar_sombra(widget, radio=20, desplazamiento_y=4, alfa=45):
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(radio)
    efecto.setOffset(0, desplazamiento_y)
    efecto.setColor(QColor(15, 23, 42, alfa))
    widget.setGraphicsEffect(efecto)
    return widget


# =====================================================
# TEMAS (claro / oscuro)
# =====================================================

LIGHT_QSS = """
    QWidget { background: #F1F5F9; font-family: "Segoe UI"; font-size: 13px; color: #0F172A; }

    QFrame#sidebar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0B1437, stop:1 #111D4A);
        border: none;
    }
    QLabel#sidebarLogoText {
        color: #FFFFFF; font-size: 14px; font-weight: bold; background: transparent;
    }
    QLabel#sidebarSection {
        color: rgba(255,255,255,0.35); font-size: 10px; font-weight: bold;
        letter-spacing: 1px; background: transparent;
    }
    QPushButton#navBtn {
        background: transparent; color: rgba(255,255,255,0.72); border: none;
        border-radius: 10px; padding: 0 14px; text-align: left; font-size: 13px;
    }
    QPushButton#navBtn:hover { background: rgba(255,255,255,0.08); color: #FFFFFF; }
    QPushButton#navBtn:checked { background: #2563EB; color: #FFFFFF; font-weight: bold; }

    QFrame#aiCard {
        background: rgba(37, 99, 235, 0.16);
        border: 1px solid rgba(37, 99, 235, 0.3);
        border-radius: 12px;
    }
    QLabel#aiTitle { color: #FFFFFF; font-size: 12px; font-weight: bold; background: transparent; }
    QLabel#aiDesc { color: rgba(255,255,255,0.55); font-size: 10px; background: transparent; }

    QFrame#card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }
    QLabel#tituloVentana { color: #0F172A; font-size: 18px; font-weight: bold; background: transparent; }
    QLabel#subtituloVentana { color: #64748B; font-size: 12px; background: transparent; }
    QLabel#lblCampo { color: #475569; font-weight: bold; font-size: 12px; background: transparent; }

    QLineEdit {
        padding: 8px; border: 1px solid #D1D5DB; border-radius: 8px;
        font-size: 13px; background: #FFFFFF; color: #0F172A;
    }
    QLineEdit:focus { border: 1px solid #2563EB; }
    QLineEdit#txtExpresion { padding: 10px; font-size: 14px; }

    QPushButton#btnGraficar {
        background: #2563EB; color: white; border: none; border-radius: 8px;
        padding: 8px 18px; font-weight: bold;
    }
    QPushButton#btnGraficar:hover { background: #1D4ED8; }
    QPushButton#btnGuardar {
        background: #059669; color: white; border: none; border-radius: 8px;
        padding: 8px 18px; font-weight: bold;
    }
    QPushButton#btnGuardar:hover { background: #047857; }
    QPushButton#btnTema, QPushButton#btnCerrar {
        background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1; border-radius: 8px;
        padding: 6px 14px; font-weight: bold;
    }
    QPushButton#btnTema:hover, QPushButton#btnCerrar:hover { background: #F1F5F9; color: #1E3A8A; }

    QPushButton#tabBtn {
        background: transparent; color: #64748B; border: none;
        border-bottom: 2px solid transparent; padding: 5px 16px;
        font-size: 13px; font-weight: bold;
    }
    QPushButton#tabBtn:hover { color: #2563EB; }
    QPushButton#tabBtn:checked { color: #2563EB; border-bottom: 3px solid #2563EB; }

    QLabel#cardTitulo { color: #1E3A8A; font-size: 13px; font-weight: bold; background: transparent; }
    QLabel#infoValor { color: #0F172A; font-size: 12px; background: transparent; }
    QLabel#infoSeccion { color: #2563EB; font-size: 11px; font-weight: bold; background: transparent; }
    QLabel#infoTexto { color: #334155; font-size: 12px; background: transparent; }
    QLabel#placeholder { color: #64748B; font-size: 13px; background: transparent; }
    QLabel#pie { color: #64748B; font-size: 11px; background: transparent; }
    QLabel#infoIcono { font-size: 15px; background: transparent; }

    QFrame#infoSep { background: #E2E8F0; border: none; max-height: 1px; }

    QPushButton#btnEjemplo {
        background: #EFF6FF; color: #2563EB; border: 1px solid #DBEAFE;
        border-radius: 12px; padding: 4px 14px; font-size: 11px; font-weight: bold;
    }
    QPushButton#btnEjemplo:hover { background: #DBEAFE; border-color: #93C5FD; }

    QPushButton#tbBtn {
        background: #EFF6FF; color: #2563EB; border: 1px solid #DBEAFE;
        border-radius: 6px; padding: 2px 10px; font-size: 11px; font-weight: bold;
    }
    QPushButton#tbBtn:hover { background: #DBEAFE; border-color: #93C5FD; }
    QPushButton#tbBtn:checked {
        background: #2563EB; color: #FFFFFF; border-color: #2563EB;
    }

    QTableWidget {
        background: #FFFFFF;
        alternate-background-color: #F1F5F9;
        color: #0F172A;
        border: none; gridline-color: #EEF2F7; font-size: 11px;
    }
    QTableWidget::item {
        color: #0F172A; background: transparent;
    }
    QTableWidget::item:selected {
        background: #2563EB; color: #FFFFFF;
    }
    QHeaderView::section {
        background: #F8FAFC; color: #475569; border: none;
        border-bottom: 1px solid #E2E8F0; padding: 4px; font-weight: bold;
    }

    QToolBar { background: transparent; border: none; spacing: 2px; padding: 0; }
    QToolBar QToolButton { background: transparent; border: none; border-radius: 4px; padding: 2px; }
    QToolBar QToolButton:hover { background: #EFF6FF; }

    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { border: none; background: transparent; width: 6px; }
    QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 3px; min-height: 30px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

DARK_QSS = """
    QWidget { background: #0F172A; font-family: "Segoe UI"; font-size: 13px; color: #E2E8F0; }

    QFrame#sidebar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0B1437, stop:1 #111D4A);
        border: none;
    }
    QLabel#sidebarLogoText {
        color: #FFFFFF; font-size: 14px; font-weight: bold; background: transparent;
    }
    QLabel#sidebarSection {
        color: rgba(255,255,255,0.35); font-size: 10px; font-weight: bold;
        letter-spacing: 1px; background: transparent;
    }
    QPushButton#navBtn {
        background: transparent; color: rgba(255,255,255,0.72); border: none;
        border-radius: 10px; padding: 0 14px; text-align: left; font-size: 13px;
    }
    QPushButton#navBtn:hover { background: rgba(255,255,255,0.08); color: #FFFFFF; }
    QPushButton#navBtn:checked { background: #2563EB; color: #FFFFFF; font-weight: bold; }

    QFrame#aiCard {
        background: rgba(37, 99, 235, 0.16);
        border: 1px solid rgba(37, 99, 235, 0.3);
        border-radius: 12px;
    }
    QLabel#aiTitle { color: #FFFFFF; font-size: 12px; font-weight: bold; background: transparent; }
    QLabel#aiDesc { color: rgba(255,255,255,0.55); font-size: 10px; background: transparent; }

    QFrame#card { background: #1E293B; border: 1px solid #334155; border-radius: 14px; }
    QLabel#tituloVentana { color: #F1F5F9; font-size: 18px; font-weight: bold; background: transparent; }
    QLabel#subtituloVentana { color: #94A3B8; font-size: 12px; background: transparent; }
    QLabel#lblCampo { color: #94A3B8; font-weight: bold; font-size: 12px; background: transparent; }

    QLineEdit {
        padding: 8px; border: 1px solid #334155; border-radius: 8px;
        font-size: 13px; background: #0F172A; color: #E2E8F0;
    }
    QLineEdit:focus { border: 1px solid #3B82F6; }
    QLineEdit#txtExpresion { padding: 10px; font-size: 14px; }

    QPushButton#btnGraficar {
        background: #2563EB; color: white; border: none; border-radius: 8px;
        padding: 8px 18px; font-weight: bold;
    }
    QPushButton#btnGraficar:hover { background: #3B82F6; }
    QPushButton#btnGuardar {
        background: #059669; color: white; border: none; border-radius: 8px;
        padding: 8px 18px; font-weight: bold;
    }
    QPushButton#btnGuardar:hover { background: #10B981; }
    QPushButton#btnTema, QPushButton#btnCerrar {
        background: #1E293B; color: #E2E8F0; border: 1px solid #334155; border-radius: 8px;
        padding: 6px 14px; font-weight: bold;
    }
    QPushButton#btnTema:hover, QPushButton#btnCerrar:hover { background: #334155; }

    QPushButton#tabBtn {
        background: transparent; color: #94A3B8; border: none;
        border-bottom: 2px solid transparent; padding: 5px 16px;
        font-size: 13px; font-weight: bold;
    }
    QPushButton#tabBtn:hover { color: #60A5FA; }
    QPushButton#tabBtn:checked { color: #60A5FA; border-bottom: 3px solid #60A5FA; }

    QLabel#cardTitulo { color: #93C5FD; font-size: 13px; font-weight: bold; background: transparent; }
    QLabel#infoValor { color: #F1F5F9; font-size: 12px; background: transparent; }
    QLabel#infoSeccion { color: #60A5FA; font-size: 11px; font-weight: bold; background: transparent; }
    QLabel#infoTexto { color: #CBD5E1; font-size: 12px; background: transparent; }
    QLabel#placeholder { color: #94A3B8; font-size: 13px; background: transparent; }
    QLabel#pie { color: #94A3B8; font-size: 11px; background: transparent; }
    QLabel#infoIcono { font-size: 15px; background: transparent; }

    QFrame#infoSep { background: #334155; border: none; max-height: 1px; }

    QPushButton#btnEjemplo {
        background: #1E293B; color: #93C5FD; border: 1px solid #334155;
        border-radius: 12px; padding: 4px 14px; font-size: 11px; font-weight: bold;
    }
    QPushButton#btnEjemplo:hover { background: #26334D; border-color: #475569; }

    QPushButton#tbBtn {
        background: #1E293B; color: #93C5FD; border: 1px solid #334155;
        border-radius: 6px; padding: 2px 10px; font-size: 11px; font-weight: bold;
    }
    QPushButton#tbBtn:hover { background: #26334D; border-color: #475569; }
    QPushButton#tbBtn:checked {
        background: #2563EB; color: #FFFFFF; border-color: #2563EB;
    }

    QTableWidget {
        background: #1E293B;
        alternate-background-color: #26334D;
        color: #E2E8F0;
        border: none; gridline-color: #334155; font-size: 11px;
    }
    QTableWidget::item {
        color: #E2E8F0; background: transparent;
    }
    QTableWidget::item:selected {
        background: #2563EB; color: #FFFFFF;
    }
    QHeaderView::section {
        background: #0F172A; color: #94A3B8; border: none;
        border-bottom: 1px solid #334155; padding: 4px; font-weight: bold;
    }

    QToolBar { background: transparent; border: none; spacing: 2px; padding: 0; }
    QToolButton {
        background: #E2E8F0; border: none; border-radius: 4px; padding: 2px;
    }
    QToolButton:hover { background: #FFFFFF; }
    QToolButton:pressed, QToolButton:checked { background: #CBD5E1; }

    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { border: none; background: transparent; width: 6px; }
    QScrollBar::handle:vertical { background: #334155; border-radius: 3px; min-height: 30px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


# =====================================================
# LOGICA DE CALCULO (modulo separado, sin dependencia Qt)
# =====================================================

from logic.graficador_logic import (
    fmt_numero as _fmt,
    preparar_texto as _preparar_texto,
    parsear_expresion as _parsear_expresion,
    analizar_funcion as _analizar_funcion,
    construir_analisis_texto as _construir_analisis_texto,
    titulo_matematico,
)


# =====================================================
# VENTANA GRAFICADOR
# =====================================================

class Graficador(QWidget):

    def __init__(self, expresion="", variable="x", usuario=None):
        super().__init__()

        self.expresion_str = expresion
        self.variable = variable
        self.usuario = usuario
        self._modo_oscuro = False
        self.favoritos = []

        self.setWindowTitle("Graficador Matemático IA - Software Matemático IA")

        # Garantizar barra de titulo con minimizar / restaurar / cerrar
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowCloseButtonHint
        )

        # Ajustar tamano a la pantalla disponible (evita cortar la barra)
        pantalla = QGuiApplication.primaryScreen()
        ancho_objetivo = 1360
        alto_objetivo = 920
        ancho_minimo = 980
        alto_minimo = 740

        # Altura minima del canvas adaptada a la pantalla (ideal: 560px).
        # Descuenta el espacio fijo de la ventana para NUNCA desbordar:
        # encabezado + panel entrada + tabs + pie + tarjetas inferiores ≈ 430px
        self._canvas_min_h = 560
        if pantalla:
            geom = pantalla.availableGeometry()
            disponible = geom.height() - 430
            self._canvas_min_h = max(170, min(560, int(disponible)))

        if pantalla:
            geom = pantalla.availableGeometry()
            ancho_objetivo = min(ancho_objetivo, geom.width() - 20)
            alto_objetivo = min(alto_objetivo, geom.height() - 20)
            ancho_minimo = min(ancho_minimo, geom.width() - 20)
            alto_minimo = min(alto_minimo, geom.height() - 20)

        self.setMinimumSize(ancho_minimo, alto_minimo)
        self.resize(ancho_objetivo, alto_objetivo)

        if pantalla:
            geom = pantalla.availableGeometry()
            x = geom.x() + max(0, (geom.width() - self.width()) // 2)
            y = geom.y() + max(0, (geom.height() - self.height()) // 2)
            self.move(x, y)

        self.setStyleSheet(LIGHT_QSS)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._construir_sidebar(root)
        self._construir_area_principal(root)

        # Conexiones de senales (botones del panel de entrada)
        self.btnGraficar.clicked.connect(self.graficar)
        self.btnGuardar.clicked.connect(self.guardar_imagen)
        self.txtExpresion.returnPressed.connect(self.graficar)

        # Tema inicial de matplotlib
        self._aplicar_estilo_grafico()

    # =====================================================
    # SIDEBAR
    # =====================================================

    def _construir_sidebar(self, root):

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(185)

        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(14, 18, 14, 14)
        sb.setSpacing(4)

        # Logo
        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        logo_lbl = QLabel()
        from utils.logos import crear_logo_circular

        pixmap = crear_logo_circular(ruta_recurso("images/logo.jpg"), 28)
        if not pixmap.isNull():
            logo_lbl.setPixmap(pixmap)
        logo_lbl.setFixedSize(30, 30)
        logo_lbl.setStyleSheet("background: transparent;")
        logo_txt = QLabel("Graficador IA")
        logo_txt.setObjectName("sidebarLogoText")
        logo_row.addWidget(logo_lbl)
        logo_row.addWidget(logo_txt)
        logo_row.addStretch()
        sb.addLayout(logo_row)
        sb.addSpacing(14)

        lbl_menu = QLabel("MENU")
        lbl_menu.setObjectName("sidebarSection")
        sb.addWidget(lbl_menu)
        sb.addSpacing(4)

        # Navegacion
        self.nav_botones = {}

        nav_items = [
            ("graficador", "\U0001F4C8", "Graficador"),
            ("funciones", "\U0001D4D1", "Funciones"),
            ("historial", "\U0001F553", "Historial"),
            ("favoritos", "\u2B50", "Favoritos"),
            ("ajustes", "\u2699", "Ajustes"),
            ("ayuda", "\u2753", "Ayuda"),
            ("acerca", "\u2139", "Acerca de"),
        ]

        for clave, icono, texto in nav_items:
            btn = QPushButton(f"  {icono}   {texto}")
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.clicked.connect(
                lambda checked, c=clave: self._navegar(c)
            )
            self.nav_botones[clave] = btn
            sb.addWidget(btn)

        self.nav_botones["graficador"].setChecked(True)

        sb.addStretch()

        # Tarjeta IA
        ai_card = QFrame()
        ai_card.setObjectName("aiCard")
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(12, 10, 12, 10)
        ai_layout.setSpacing(3)

        ai_title = QLabel("\U0001F916 Potenciado con IA")
        ai_title.setObjectName("aiTitle")
        ai_desc = QLabel("Analisis matematico automatico\ncon inteligencia artificial.")
        ai_desc.setObjectName("aiDesc")

        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(ai_desc)

        sb.addWidget(ai_card)

        root.addWidget(sidebar)

    def _navegar(self, clave):

        if clave == "graficador":
            return

        for c, b in self.nav_botones.items():
            b.setChecked(c == clave)

        dialogos = {
            "funciones": self._dialogo_funciones,
            "historial": self._dialogo_historial,
            "favoritos": self._dialogo_favoritos,
            "ajustes": self._dialogo_ajustes,
            "ayuda": self._dialogo_ayuda,
            "acerca": self._dialogo_acerca,
        }

        if clave in dialogos:
            dialogos[clave]()
            self.nav_botones[clave].setChecked(False)
            self.nav_botones["graficador"].setChecked(True)

    def _dialogo_funciones(self):
        QMessageBox.information(
            self,
            "Funciones soportadas",
            "Sintaxis soportada:\n\n"
            "\u2022 Operadores: + - * / ^ (potencia)\n"
            "\u2022 Trigonometricas: sin(x), cos(x), tan(x)\n"
            "\u2022 Inversas: asin(x), acos(x), atan(x)\n"
            "\u2022 Logaritmos: log(x), ln(x)\n"
            "\u2022 Exponencial: exp(x)\n"
            "\u2022 Raiz: sqrt(x)\n"
            "\u2022 Valor absoluto: Abs(x)\n\n"
            "Ejemplos:\n"
            "-5*x^2+20*x+2\n"
            "sin(x) + cos(2*x)\n"
            "sqrt(x^2 + 1)"
        )

    def _dialogo_historial(self):
        QMessageBox.information(
            self,
            "Historial",
            "Tu historial de consultas esta disponible\n"
            "en el Panel Principal, seccion Historial."
        )

    def _dialogo_favoritos(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Funciones favoritas")
        dlg.setFixedWidth(380)
        layout = QVBoxLayout(dlg)

        lista = QListWidget()
        for fav in self.favoritos:
            lista.addItem(fav)
        layout.addWidget(lista)

        btn_agregar = QPushButton("\u2605 Guardar expresion actual")
        btn_agregar.setObjectName("btnGraficar")

        def agregar():
            texto = self.txtExpresion.text().strip()
            if texto and texto not in self.favoritos:
                self.favoritos.append(texto)
                lista.addItem(texto)

        btn_agregar.clicked.connect(agregar)
        layout.addWidget(btn_agregar)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dlg.accept)
        layout.addWidget(btn_cerrar)

        dlg.exec_()

    def _dialogo_ajustes(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ajustes del graficador")
        dlg.setFixedWidth(320)
        layout = QVBoxLayout(dlg)

        chk = QCheckBox("Modo oscuro")
        chk.setChecked(self._modo_oscuro)
        chk.toggled.connect(lambda estado: self._alternar_tema(estado))
        layout.addWidget(chk)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dlg.accept)
        layout.addWidget(btn_cerrar)

        dlg.exec_()

    def _dialogo_ayuda(self):
        QMessageBox.information(
            self,
            "Ayuda del Graficador",
            "Como usar el graficador:\n\n"
            "1. Escribe una expresion matematica.\n"
            "2. Define la variable y el rango.\n"
            "3. Presiona Graficar.\n\n"
            "El sistema calculara automaticamente\n"
            "maximos, minimos, interceptos y mas."
        )

    def _dialogo_acerca(self):
        mostrar_acerca(
            self,
            "Graficador Matemático IA",
            "Python + PyQt5 + Matplotlib + SymPy",
        )

    # =====================================================
    # AREA PRINCIPAL
    # =====================================================

    def _construir_area_principal(self, root):

        area = QWidget()
        area_lay = QHBoxLayout(area)
        area_lay.setContentsMargins(12, 8, 12, 6)
        area_lay.setSpacing(14)

        # ---------- Columna central ----------
        central = QVBoxLayout()
        central.setSpacing(6)

        self._construir_header(central)
        self._construir_panel_entrada(central)
        self._construir_tabs(central)
        self._construir_charts(central)
        self._construir_tarjetas_inferiores(central)

        pie = QLabel("Software Matemático IA \u2022 Versión 1.1 \u2022 Graficador 2D/3D")
        pie.setObjectName("pie")
        pie.setAlignment(Qt.AlignCenter)
        central.addWidget(pie)

        area_lay.addLayout(central, 1)

        # ---------- Panel derecho ----------
        self._construir_panel_info(area_lay)

        root.addWidget(area, 1)

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    def _construir_header(self, central):

        header = QHBoxLayout()
        header.setSpacing(10)

        icono = QLabel("\U0001F4C8")
        icono.setStyleSheet("font-size: 24px; background: transparent;")

        titulos = QVBoxLayout()
        titulos.setSpacing(0)
        t = QLabel("Graficador Matemático IA")
        t.setObjectName("tituloVentana")
        s = QLabel("Visualiza funciones en 2D y 3D")
        s.setObjectName("subtituloVentana")
        titulos.addWidget(t)
        titulos.addWidget(s)

        header.addWidget(icono)
        header.addLayout(titulos)
        header.addStretch()

        btn_volver = QPushButton("\u2B05 Panel Principal")
        btn_volver.setObjectName("btnCerrar")
        btn_volver.setCursor(Qt.PointingHandCursor)
        btn_volver.setFixedHeight(32)
        btn_volver.clicked.connect(self.volver_panel)

        self.btnTema = QPushButton("\U0001F312 Modo oscuro")
        self.btnTema.setObjectName("btnTema")
        self.btnTema.setCursor(Qt.PointingHandCursor)
        self.btnTema.setFixedHeight(32)
        self.btnTema.clicked.connect(
            lambda: self._alternar_tema(not self._modo_oscuro)
        )

        btn_cerrar = QPushButton("\u2715 Cerrar")
        btn_cerrar.setObjectName("btnCerrar")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.setFixedHeight(32)
        btn_cerrar.clicked.connect(self.close)

        header.addWidget(btn_volver)
        header.addWidget(self.btnTema)
        header.addWidget(btn_cerrar)

        central.addLayout(header)

    def volver_panel(self):
        """Regresa al Panel Principal conservando la sesion del usuario."""

        from interfaces.menu import MenuPrincipal

        nombre = self.usuario or "Usuario"

        if self.usuario:
            try:
                from controllers.usuario_controller import UsuarioController

                datos = UsuarioController.buscar_usuario(self.usuario)

                if datos and datos.get("nombre"):
                    nombre = datos["nombre"]
            except Exception:
                pass

        self.menu = MenuPrincipal(nombre, self.usuario or "Usuario", "Estudiante")
        self.menu.show()
        self.close()

    # -----------------------------------------------------
    # PANEL DE ENTRADA
    # -----------------------------------------------------

    def _construir_panel_entrada(self, central):

        card = QFrame()
        card.setObjectName("card")
        aplicar_sombra(card, radio=16, desplazamiento_y=3, alfa=40)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(10)

        col_expr = QVBoxLayout()
        col_expr.setSpacing(3)
        l1 = QLabel("Expresión:")
        l1.setObjectName("lblCampo")
        self.txtExpresion = QLineEdit()
        self.txtExpresion.setObjectName("txtExpresion")
        self.txtExpresion.setPlaceholderText("Ej: -5*x^2+20*x+2, sin(x), 1/x ...")
        self.txtExpresion.setMinimumWidth(150)
        if self.expresion_str:
            self.txtExpresion.setText(self.expresion_str)
        col_expr.addWidget(l1)
        col_expr.addWidget(self.txtExpresion)

        col_var = QVBoxLayout()
        col_var.setSpacing(3)
        l2 = QLabel("Variable:")
        l2.setObjectName("lblCampo")
        self.txtVariable = QLineEdit(self.variable)
        self.txtVariable.setFixedWidth(56)
        col_var.addWidget(l2)
        col_var.addWidget(self.txtVariable)

        col_min = QVBoxLayout()
        col_min.setSpacing(3)
        l3 = QLabel("Rango de:")
        l3.setObjectName("lblCampo")
        self.txtRangoMin = QLineEdit("-10")
        self.txtRangoMin.setFixedWidth(64)
        col_min.addWidget(l3)
        col_min.addWidget(self.txtRangoMin)

        col_max = QVBoxLayout()
        col_max.setSpacing(3)
        l4 = QLabel("a:")
        l4.setObjectName("lblCampo")
        self.txtRangoMax = QLineEdit("10")
        self.txtRangoMax.setFixedWidth(64)
        col_max.addWidget(l4)
        col_max.addWidget(self.txtRangoMax)

        botones = QVBoxLayout()
        botones.setSpacing(6)
        self.btnGraficar = QPushButton("\U0001F4CA Graficar")
        self.btnGraficar.setObjectName("btnGraficar")
        self.btnGraficar.setCursor(Qt.PointingHandCursor)
        self.btnGraficar.setFixedHeight(30)

        self.btnGuardar = QPushButton("\U0001F4BE Guardar como imagen")
        self.btnGuardar.setObjectName("btnGuardar")
        self.btnGuardar.setCursor(Qt.PointingHandCursor)
        self.btnGuardar.setFixedHeight(30)

        botones.addWidget(self.btnGraficar)
        botones.addWidget(self.btnGuardar)

        lay.addLayout(col_expr, 1)
        lay.addLayout(col_var)
        lay.addLayout(col_min)
        lay.addLayout(col_max)
        lay.addSpacing(6)
        lay.addLayout(botones)

        central.addWidget(card)

        # Error inline
        self.lblError = QLabel("")
        self.lblError.setStyleSheet("color: #DC2626; font-size: 12px;")
        self.lblError.setVisible(False)
        central.addWidget(self.lblError)

    # -----------------------------------------------------
    # TABS
    # -----------------------------------------------------

    def _construir_tabs(self, central):

        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(4)

        self.tab2d = QPushButton("Gráfica 2D")
        self.tab2d.setObjectName("tabBtn")
        self.tab2d.setCheckable(True)
        self.tab2d.setChecked(True)
        self.tab2d.setCursor(Qt.PointingHandCursor)
        self.tab2d.clicked.connect(lambda: self._cambiar_tab(True))

        self.tab3d = QPushButton("Gráfica 3D")
        self.tab3d.setObjectName("tabBtn")
        self.tab3d.setCheckable(True)
        self.tab3d.setCursor(Qt.PointingHandCursor)
        self.tab3d.clicked.connect(lambda: self._cambiar_tab(False))

        tabs_row.addWidget(self.tab2d)
        tabs_row.addWidget(self.tab3d)
        tabs_row.addStretch()

        central.addLayout(tabs_row)

    def _cambiar_tab(self, mostrar_2d):
        """Muestra solo el contenido de la pestana activa, a ancho completo."""
        self.tab2d.setChecked(mostrar_2d)
        self.tab3d.setChecked(not mostrar_2d)

        if hasattr(self, "contenedor2d") and hasattr(self, "contenedor3d"):
            self.contenedor2d.setVisible(mostrar_2d)
            self.contenedor3d.setVisible(not mostrar_2d)
            if hasattr(self, "sep_charts"):
                self.sep_charts.setVisible(False)

    # -----------------------------------------------------
    # CHARTS 2D / 3D
    # -----------------------------------------------------

    def _construir_charts(self, central):

        charts_card = QFrame()
        charts_card.setObjectName("card")
        aplicar_sombra(charts_card, radio=16, desplazamiento_y=3, alfa=40)

        charts_lay = QHBoxLayout(charts_card)
        charts_lay.setContentsMargins(8, 6, 8, 8)
        charts_lay.setSpacing(10)
        self.charts_lay = charts_lay

        # ---------- 2D ----------
        self.contenedor2d = QWidget()
        self.contenedor2d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay2d = QVBoxLayout(self.contenedor2d)
        lay2d.setContentsMargins(0, 0, 0, 0)
        lay2d.setSpacing(2)

        self.figura = Figure(figsize=(7.0, 4.0), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figura)
        self.canvas.setParent(self)
        # Ignored: el tamaño lo manda el layout (no el figsize de la figura),
        # asi ninguna grafica aplasta a la otra
        self.canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.canvas.setMinimumHeight(self._canvas_min_h)
        self.canvas.setMinimumWidth(240)

        self.toolbar2d = NavigationToolbar2QT(self.canvas, self)
        self.toolbar2d.setStyleSheet("background: transparent; border: none;")
        # Motor oculto: la logica de zoom/pan sigue siendo la oficial.
        # Altura cero: aunque algo la re-muestre, no ocupa espacio ni pinta nada.
        self.toolbar2d.setVisible(False)
        self.toolbar2d.setFixedHeight(0)

        barra2d = self._barra_nav(self.toolbar2d)

        # ---------- Estado vacio: icono + mensaje + ejemplos ----------
        self.placeholderBox = QWidget()
        self.placeholderBox.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        pb = QVBoxLayout(self.placeholderBox)
        pb.setContentsMargins(0, 4, 0, 4)
        pb.setSpacing(6)
        pb.setAlignment(Qt.AlignCenter)

        lbl_icono_graf = QLabel("\U0001F4C8")
        lbl_icono_graf.setStyleSheet("font-size: 42px; background: transparent;")
        lbl_icono_graf.setAlignment(Qt.AlignCenter)

        self.lblPlaceholder = QLabel("Ingresa una expresión y presiona \U0001F4CA Graficar")
        self.lblPlaceholder.setObjectName("placeholder")
        self.lblPlaceholder.setAlignment(Qt.AlignCenter)
        # Que su texto no imponga un ancho minimo al panel de la grafica
        self.lblPlaceholder.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        fila_ejemplos = QHBoxLayout()
        fila_ejemplos.setSpacing(6)
        fila_ejemplos.addStretch()
        for ejemplo in ("sin(x)", "x^2", "1/x"):
            btn_ej = QPushButton(ejemplo)
            btn_ej.setObjectName("btnEjemplo")
            btn_ej.setCursor(Qt.PointingHandCursor)
            btn_ej.setToolTip(f"Graficar {ejemplo}")
            btn_ej.clicked.connect(
                lambda checked, ej=ejemplo: self._usar_ejemplo(ej)
            )
            fila_ejemplos.addWidget(btn_ej)
        fila_ejemplos.addStretch()

        pb.addWidget(lbl_icono_graf)
        pb.addWidget(self.lblPlaceholder)
        pb.addLayout(fila_ejemplos)

        lay2d.addWidget(barra2d)
        lay2d.addWidget(self.canvas, 1)
        lay2d.addWidget(self.placeholderBox)
        self.placeholderBox.setVisible(True)
        self.canvas.setVisible(False)

        charts_lay.addWidget(self.contenedor2d, 55)

        # Separador vertical (queda oculto: las pestanas son exclusivas)
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #E2E8F0;")
        charts_lay.addWidget(sep)
        self.sep_charts = sep

        # ---------- 3D ----------
        self.contenedor3d = QWidget()
        self.contenedor3d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay3d = QVBoxLayout(self.contenedor3d)
        lay3d.setContentsMargins(0, 0, 0, 0)
        lay3d.setSpacing(2)

        self.figura3d = Figure(figsize=(5.5, 4.0), dpi=100)
        self.canvas3d = FigureCanvasQTAgg(self.figura3d)
        self.canvas3d.setParent(self)
        self.canvas3d.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.canvas3d.setMinimumHeight(self._canvas_min_h)
        self.canvas3d.setMinimumWidth(170)

        def _bloquear_scroll_3d(event):
            pass
        self.canvas3d.wheelEvent = _bloquear_scroll_3d

        self.toolbar3d = NavigationToolbar2QT(self.canvas3d, self)
        self.toolbar3d.setStyleSheet("background: transparent; border: none;")
        # Motor oculto para la grafica 3D, con altura cero
        self.toolbar3d.setVisible(False)
        self.toolbar3d.setFixedHeight(0)

        barra3d = self._barra_nav(self.toolbar3d)

        self.ax3d = self.figura3d.add_subplot(111, projection="3d")
        self._preparar_ejes_3d()

        lay3d.addWidget(barra3d)
        lay3d.addWidget(self.canvas3d, 1)

        charts_lay.addWidget(self.contenedor3d, 55)

        # Pestana real: solo el contenido activo es visible (2D por defecto)
        self.contenedor2d.setVisible(True)
        self.contenedor3d.setVisible(False)
        self.sep_charts.setVisible(False)

        # Stretch alto: la grafica es el elemento dominante de la columna
        central.addWidget(charts_card, 8)

    def _barra_nav(self, toolbar):
        """Barra propia de navegacion que maneja la toolbar oficial oculta.

        Zoom y Pan alternan el modo del toolbar; Reset restaura la vista;
        Guardar abre el dialogo nativo de guardado. Toda la logica de
        zoom/pan sigue siendo NavigationToolbar2QT, asi no se rompe nada.
        """
        barra = QWidget()
        barra.setFixedHeight(32)
        h = QHBoxLayout(barra)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        h.addStretch()

        btn_zoom = QPushButton("\U0001F50D Zoom")
        btn_pan = QPushButton("\u270B Mover")
        btn_reset = QPushButton("\u27F2 Reset")
        btn_guardar = QPushButton("\U0001F4BE Guardar")
        for b in (btn_zoom, btn_pan, btn_reset, btn_guardar):
            b.setObjectName("tbBtn")
            b.setCursor(Qt.PointingHandCursor)
            h.addWidget(b)

        btn_zoom.setCheckable(True)
        btn_pan.setCheckable(True)

        def activar_zoom(marcado):
            if marcado and btn_pan.isChecked():
                btn_pan.setChecked(False)
                toolbar.pan()
            toolbar.zoom()

        def activar_pan(marcado):
            if marcado and btn_zoom.isChecked():
                btn_zoom.setChecked(False)
                toolbar.zoom()
            toolbar.pan()

        def resetear():
            btn_zoom.setChecked(False)
            btn_pan.setChecked(False)
            # Cancelar el modo activo antes de restaurar la vista
            if toolbar.mode == "zoom rect":
                toolbar.zoom()
            elif toolbar.mode == "pan/zoom":
                toolbar.pan()
            toolbar.home()

        btn_zoom.clicked.connect(activar_zoom)
        btn_pan.clicked.connect(activar_pan)
        btn_reset.clicked.connect(resetear)
        btn_guardar.clicked.connect(toolbar.save_figure)

        return barra

    def _tema_ejes_3d(self):
        """Paneles, grillas y encuadre del eje 3D segun el tema activo."""
        oscuro = self._modo_oscuro
        # Paneles (paredes) del cubo 3D: oscuros en modo oscuro, claros en claro
        pane = (0.06, 0.09, 0.16, 1.0) if oscuro else (0.97, 0.98, 1.0, 1.0)
        grid_c = "#475569" if oscuro else "#CBD5E1"
        for eje in (self.ax3d.xaxis, self.ax3d.yaxis, self.ax3d.zaxis):
            try:
                eje.set_pane_color(pane)
            except Exception:
                pass
            try:
                eje._axinfo["grid"]["color"] = grid_c
            except Exception:
                pass
        # La superficie llena el cubo en vez de quedar pequena al centro
        try:
            self.ax3d.set_box_aspect((1, 0.75, 0.85), zoom=1.0)
        except Exception:
            pass

    def _preparar_ejes_3d(self):
        """Estado inicial del eje 3D."""
        self.ax3d.clear()
        self.ax3d.set_facecolor(
            "#1E293B" if self._modo_oscuro else _COLOR_FONDO_CANVAS
        )
        self._tema_ejes_3d()
        self.ax3d.set_xlabel("x", fontsize=9)
        self.ax3d.set_ylabel("y", fontsize=9)
        self.ax3d.set_zlabel("z", fontsize=9)
        self.ax3d.set_title("Superficie z = f(x)", fontsize=10, pad=4)
        self.canvas3d.draw()

    # -----------------------------------------------------
    # TARJETAS INFERIORES
    # -----------------------------------------------------

    def _construir_tarjetas_inferiores(self, central):

        fila = QHBoxLayout()
        fila.setSpacing(10)

        # ---------- Puntos clave ----------
        card_puntos = QFrame()
        card_puntos.setObjectName("card")
        lp = QVBoxLayout(card_puntos)
        lp.setContentsMargins(12, 8, 12, 8)
        lp.setSpacing(4)
        tp = QLabel("Puntos clave")
        tp.setObjectName("cardTitulo")
        lp.addWidget(tp)

        fila_p = QHBoxLayout()
        fila_p.setContentsMargins(0, 0, 0, 0)
        fila_p.setSpacing(6)
        icono_p = QLabel("\u23F3")
        icono_p.setObjectName("infoIcono")
        self.lblPuntos = QLabel("Grafica una función para ver sus puntos clave.")
        self.lblPuntos.setObjectName("infoTexto")
        self.lblPuntos.setWordWrap(True)
        self.lblPuntos.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        fila_p.addWidget(icono_p, 0, Qt.AlignTop)
        fila_p.addWidget(self.lblPuntos, 1)
        lp.addLayout(fila_p, 1)

        # ---------- Caracteristicas ----------
        card_caract = QFrame()
        card_caract.setObjectName("card")
        lc = QVBoxLayout(card_caract)
        lc.setContentsMargins(12, 8, 12, 8)
        lc.setSpacing(4)
        tc = QLabel("Características")
        tc.setObjectName("cardTitulo")
        lc.addWidget(tc)

        fila_c = QHBoxLayout()
        fila_c.setContentsMargins(0, 0, 0, 0)
        fila_c.setSpacing(6)
        icono_c = QLabel("\u2139")
        icono_c.setObjectName("infoIcono")
        self.lblCaract = QLabel("Dominio, rango y monotonía\naparecerán aquí.")
        self.lblCaract.setObjectName("infoTexto")
        self.lblCaract.setWordWrap(True)
        self.lblCaract.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        fila_c.addWidget(icono_c, 0, Qt.AlignTop)
        fila_c.addWidget(self.lblCaract, 1)
        lc.addLayout(fila_c, 1)

        # ---------- Tabla de valores ----------
        card_tabla = QFrame()
        card_tabla.setObjectName("card")
        lt = QVBoxLayout(card_tabla)
        lt.setContentsMargins(12, 8, 12, 8)
        lt.setSpacing(4)
        tt = QLabel("Tabla de valores")
        tt.setObjectName("cardTitulo")
        lt.addWidget(tt)

        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["x", "f(x)"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        lt.addWidget(self.tabla, 1)

        fila.addWidget(card_puntos, 1)
        fila.addWidget(card_caract, 1)
        fila.addWidget(card_tabla, 1)

        central.addLayout(fila, 2)

    # -----------------------------------------------------
    # PANEL DERECHO: INFORMACION DE LA FUNCION
    # -----------------------------------------------------

    def _construir_panel_info(self, area_lay):

        panel = QFrame()
        panel.setObjectName("card")
        panel.setFixedWidth(240)
        aplicar_sombra(panel, radio=16, desplazamiento_y=3, alfa=40)

        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(8)

        titulo = QLabel("\u2139 Información de la función")
        titulo.setObjectName("cardTitulo")
        titulo.setWordWrap(True)
        pl.addWidget(titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(10)

        def separador_info():
            linea = QFrame()
            linea.setObjectName("infoSep")
            linea.setFixedHeight(1)
            return linea

        # Expresion
        l_expr = QLabel("EXPRESIÓN")
        l_expr.setObjectName("infoSeccion")
        self.infoExpresion = QLabel("Sin datos aún")
        self.infoExpresion.setObjectName("infoValor")
        self.infoExpresion.setWordWrap(True)
        self.infoExpresion.setStyleSheet("font-family: Consolas, monospace; font-size: 13px;")
        il.addWidget(l_expr)
        il.addWidget(self.infoExpresion)
        il.addWidget(separador_info())

        # Analisis
        l_analisis = QLabel("ANÁLISIS")
        l_analisis.setObjectName("infoSeccion")
        self.infoAnalisis = QLabel("Grafica una función para generar el análisis automático.")
        self.infoAnalisis.setObjectName("infoTexto")
        self.infoAnalisis.setWordWrap(True)
        il.addWidget(l_analisis)
        il.addWidget(self.infoAnalisis)
        il.addWidget(separador_info())

        # Tipo
        l_tipo = QLabel("TIPO DE FUNCIÓN")
        l_tipo.setObjectName("infoSeccion")
        self.infoTipo = QLabel("Sin datos aún")
        self.infoTipo.setObjectName("infoTexto")
        il.addWidget(l_tipo)
        il.addWidget(self.infoTipo)
        il.addWidget(separador_info())

        # Simetria
        l_sim = QLabel("SIMETRÍA")
        l_sim.setObjectName("infoSeccion")
        self.infoSimetria = QLabel("Sin datos aún")
        self.infoSimetria.setObjectName("infoTexto")
        self.infoSimetria.setWordWrap(True)
        il.addWidget(l_sim)
        il.addWidget(self.infoSimetria)
        il.addWidget(separador_info())

        # Comportamiento
        l_comp = QLabel("COMPORTAMIENTO")
        l_comp.setObjectName("infoSeccion")
        self.infoComportamiento = QLabel("Sin datos aún")
        self.infoComportamiento.setObjectName("infoTexto")
        self.infoComportamiento.setWordWrap(True)
        il.addWidget(l_comp)
        il.addWidget(self.infoComportamiento)

        il.addStretch()

        scroll.setWidget(inner)
        pl.addWidget(scroll, 1)

        area_lay.addWidget(panel)

    # =====================================================
    # TEMA
    # =====================================================

    def _alternar_tema(self, oscuro):
        self._modo_oscuro = oscuro
        self.setStyleSheet(DARK_QSS if oscuro else LIGHT_QSS)
        self.btnTema.setText(
            "\u2600 Modo claro" if oscuro else "\U0001F312 Modo oscuro"
        )
        self._aplicar_estilo_grafico()

        # Redibujar si ya hay grafico
        if not self.canvas.isHidden():
            expr = self.infoExpresion.text()
            var = self.txtVariable.text().strip() or "x"
            try:
                xs = np.linspace(
                    float(self.txtRangoMin.text() or -10),
                    float(self.txtRangoMax.text() or 10),
                    1000,
                )
                expr_s = _parsear_expresion(self.txtExpresion.text())
                func = None
                from sympy import lambdify, Symbol
                func = lambdify(Symbol(var), expr_s, modules=["numpy"])
                ys = np.asarray(func(xs), dtype=float)
                if ys.ndim == 0:
                    ys = np.full_like(xs, float(ys))
                ys = np.where(np.isnan(ys) | np.isinf(ys), np.nan, ys)
                analisis = _analizar_funcion(
                    expr_s, var,
                    float(self.txtRangoMin.text() or -10),
                    float(self.txtRangoMax.text() or 10),
                )
                self._dibujar_2d(xs, ys, self.txtExpresion.text(), var, analisis, expr_s)
                self._dibujar_3d(func, var, xs)
            except Exception:
                pass

    # =====================================================
    # ESTILO MATPLOTLIB
    # =====================================================

    def _aplicar_estilo_grafico(self):
        import matplotlib as mpl

        oscuro = self._modo_oscuro
        fondo = "#1E293B" if oscuro else _COLOR_FONDO_CANVAS
        texto = "#E2E8F0" if oscuro else _COLOR_TEXTO
        secundario = "#94A3B8" if oscuro else _COLOR_SECUNDARIO
        grid = "#334155" if oscuro else _COLOR_GRID

        mpl.rcParams.update({
            "font.size": 10,
            "font.family": "Segoe UI",
            "axes.labelcolor": secundario,
            "xtick.color": secundario,
            "ytick.color": secundario,
            "axes.facecolor": fondo,
            "figure.facecolor": fondo,
            "axes.edgecolor": grid,
            "text.color": texto,
        })

    # =====================================================
    # LIMPIAR ERROR
    # =====================================================

    def _limpiar_error(self, texto=None):
        self.lblError.setVisible(False)
        self.lblError.setText("")
        self.txtExpresion.setStyleSheet("")

    def _mostrar_error(self, mensaje, es_advertencia=False):
        color = "#F59E0B" if es_advertencia else "#DC2626"
        self.lblError.setText(mensaje.replace("\n", " "))
        self.lblError.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.lblError.setVisible(True)
        if not es_advertencia:
            self.txtExpresion.setStyleSheet("border: 2px solid #EF4444;")

    def _reset_vista(self):
        """Oculta la grafica anterior cuando un nuevo intento falla."""
        self.canvas.setVisible(False)
        self.placeholderBox.setVisible(True)

    def _usar_ejemplo(self, expresion):
        """Llena el campo con una funcion de ejemplo y la grafica."""
        self.txtExpresion.setText(expresion)
        self.graficar()

    # =====================================================
    # GRAFICAR
    # =====================================================

    def graficar(self):
        self._limpiar_error()

        expr = self.txtExpresion.text().strip()

        if not expr:
            QMessageBox.warning(
                self,
                "Campo vacío",
                "Por favor ingrese una expresión matemática.\n\n"
                "Ejemplos válidos: sin(x), x^2, 1/x, cos(x)*x"
            )
            self.txtExpresion.setFocus()
            return

        var = self.txtVariable.text().strip() or "x"

        if not var.isidentifier():
            self._mostrar_error("Variable inválida. Use un nombre como: x, t, u")
            return

        try:
            expr_limpio = _preparar_texto(expr)
            expr_sympy = _parsear_expresion(expr_limpio)
        except Exception as error:
            self._reset_vista()
            self._mostrar_error(
                f"No se pudo interpretar la expresión: {error}. "
                "Use +, -, *, /, ^ y funciones como sin, cos, log, sqrt, exp."
            )
            return

        # Resolver simbolos no reconocidos (e de Euler, mayusculas, etc.)
        from sympy import Symbol, E

        var_symbol = Symbol(var)

        extras = expr_sympy.free_symbols - {var_symbol}

        if extras:
            # e -> numero de Euler
            if extras == {Symbol("e")}:
                try:
                    expr_sympy = _parsear_expresion(
                        expr_limpio, local_dict={"e": E}
                    )
                    extras = expr_sympy.free_symbols - {var_symbol}
                except Exception:
                    pass

        if extras:
            # Variable en distinta case: X^2 con variable x
            for s in list(extras):
                if str(s).lower() == var.lower():
                    try:
                        corregido = re.sub(
                            rf"\b{re.escape(str(s))}\b", var, expr_limpio
                        )
                        expr_sympy = _parsear_expresion(corregido)
                        extras = expr_sympy.free_symbols - {var_symbol}
                        break
                    except Exception:
                        pass

        if extras:
            nombres = ", ".join(sorted(str(s) for s in extras))
            self._reset_vista()
            self._mostrar_error(
                f"Símbolos no reconocidos: {nombres}. "
                f"Use únicamente la variable '{var}'."
            )
            return

        try:
            x_min = float(self.txtRangoMin.text().strip() or "-10")
            x_max = float(self.txtRangoMax.text().strip() or "10")
            if x_min >= x_max:
                self._mostrar_error("El rango mínimo debe ser menor que el máximo.")
                return
        except ValueError:
            self._mostrar_error("Rango inválido. Use números.")
            return

        from sympy import lambdify, Symbol

        try:
            var_symbol = Symbol(var)
            func = lambdify(var_symbol, expr_sympy, modules=["numpy"])
        except Exception as error:
            self._reset_vista()
            self._mostrar_error(f"No se pudo preparar la expresión: {error}")
            return

        xs = np.linspace(x_min, x_max, 1000)

        try:
            ys_raw = func(xs)
            ys = np.asarray(ys_raw, dtype=float)
            if ys.ndim == 0:
                ys = np.full_like(xs, float(ys_raw))
            ys = np.where(np.isnan(ys) | np.isinf(ys), np.nan, ys)
        except Exception:
            ys = np.full_like(xs, np.nan)
            for i, x_val in enumerate(xs):
                try:
                    y_val = float(expr_sympy.subs(var_symbol, x_val))
                    ys[i] = y_val if np.isfinite(y_val) else np.nan
                except Exception:
                    ys[i] = np.nan

        if np.all(np.isnan(ys)):
            self._reset_vista()
            self._mostrar_error(
                "No se pudieron calcular valores numéricos en el rango "
                "especificado. Verifique la expresión y el dominio."
            )
            return

        self.placeholderBox.setVisible(False)
        self.canvas.setVisible(True)

        if np.any(np.isnan(ys)):
            self._mostrar_error(
                "La función tiene puntos discontinuos o fuera de dominio "
                "en el rango. Se muestran los valores válidos.",
                es_advertencia=True,
            )

        # Analisis matematico completo
        analisis = _analizar_funcion(expr_sympy, var, x_min, x_max)

        self._dibujar_2d(xs, ys, expr, var, analisis, expr_sympy)
        self._dibujar_3d(func, var, xs)
        self._actualizar_info(expr, var, analisis, x_min, x_max, expr_sympy)

    # =====================================================
    # DIBUJAR 2D
    # =====================================================

    def _dibujar_2d(self, xs, ys, expr, var, analisis, expr_sympy=None):

        self.figura.clear()
        self._aplicar_estilo_grafico()

        ax = self.figura.add_subplot(111)
        fondo = "#1E293B" if self._modo_oscuro else _COLOR_FONDO_CANVAS
        grid_color = "#334155" if self._modo_oscuro else _COLOR_GRID
        texto_color = "#E2E8F0" if self._modo_oscuro else _COLOR_TEXTO
        color_curva = "#60A5FA" if self._modo_oscuro else _COLOR_FUN

        ax.set_facecolor(fondo)

        ax.plot(xs, ys, color=color_curva, linewidth=2.4, zorder=3)

        ax.axhline(0, color=grid_color, linewidth=1.0, zorder=1)
        ax.axvline(0, color=grid_color, linewidth=1.0, zorder=1)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(grid_color)
        ax.spines["bottom"].set_color(grid_color)

        ax.grid(True, alpha=0.35, linestyle="--", color=grid_color)

        leyenda = [(f"f({var}) = {expr}", color_curva)]

        # Colores de puntos clave (spec): azul=Max/Min, verde=Inter Y, rojo=Inter X
        color_ext = "#60A5FA" if self._modo_oscuro else "#2563EB"
        color_iy = "#34D399" if self._modo_oscuro else "#059669"
        color_ix = "#F87171" if self._modo_oscuro else "#DC2626"

        def _guias(px, py):
            """Lineas guia punteadas del punto hacia ambos ejes."""
            ax.plot(
                [px, px], [py, 0], color="#94A3B8",
                linewidth=0.9, linestyle=":", alpha=0.85, zorder=2,
            )
            ax.plot(
                [0, px], [py, py], color="#94A3B8",
                linewidth=0.9, linestyle=":", alpha=0.85, zorder=2,
            )

        # Puntos clave resaltados
        for mx, my in analisis["maximos"]:
            _guias(mx, my)
            ax.scatter([mx], [my], color=color_ext, s=50, zorder=5,
                       edgecolors="white", linewidths=1)
            ax.annotate(
                f"Máximo ({_fmt(mx)}, {_fmt(my)})",
                (mx, my), textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=8, color=color_ext, fontweight="bold",
            )
        if analisis["maximos"]:
            leyenda.append(("Máximo", color_ext))

        for mn, my in analisis["minimos"]:
            _guias(mn, my)
            ax.scatter([mn], [my], color=color_ext, s=50, zorder=5,
                       edgecolors="white", linewidths=1)
            ax.annotate(
                f"Mínimo ({_fmt(mn)}, {_fmt(my)})",
                (mn, my), textcoords="offset points", xytext=(0, -14),
                ha="center", fontsize=8, color=color_ext, fontweight="bold",
            )
        if analisis["minimos"]:
            leyenda.append(("Mínimo", color_ext))

        if analisis["inter_y"] is not None and np.isfinite(analisis["inter_y"]):
            iyv = analisis["inter_y"]
            _guias(0, iyv)
            ax.scatter([0], [iyv], color=color_iy, s=45, zorder=5,
                       edgecolors="white", linewidths=1)
            ax.annotate(
                f"({_fmt(0)}, {_fmt(iyv)})",
                (0, iyv), textcoords="offset points", xytext=(10, 4),
                ha="left", fontsize=8, color=color_iy, fontweight="bold",
            )
            leyenda.append(("Intercepto Y", color_iy))

        for ix in analisis["inter_x"]:
            _guias(ix, 0)
            ax.scatter([ix], [0], color=color_ix, s=45, zorder=5,
                       edgecolors="white", linewidths=1)
            ax.annotate(
                f"({_fmt(ix)}, {_fmt(0)})",
                (ix, 0), textcoords="offset points", xytext=(4, -13),
                ha="center", fontsize=8, color=color_ix, fontweight="bold",
            )
        if analisis["inter_x"]:
            leyenda.append(("Intercepto X", color_ix))

        if analisis["eje_simetria"] is not None:
            ax.axvline(
                analisis["eje_simetria"], color="#7C3AED",
                linewidth=1.2, linestyle=":", alpha=0.8, zorder=2,
            )

        # Leyenda personalizada
        from matplotlib.lines import Line2D

        handles = [
            Line2D([0], [0], color=c, linewidth=2.4, label=l)
            for l, c in leyenda
        ]
        oscuro = self._modo_oscuro
        leg = ax.legend(handles=handles, loc="best", fontsize=8, framealpha=0.92)
        leg.get_frame().set_facecolor("#1E293B" if oscuro else "#FFFFFF")
        leg.get_frame().set_edgecolor("#475569" if oscuro else "#CBD5E1")
        for t in leg.get_texts():
            t.set_color("#E2E8F0" if oscuro else "#1E293B")

        ax.set_xlabel(var, fontsize=10, fontweight="bold")
        ax.set_ylabel(f"f({var})", fontsize=10, fontweight="bold")
        if expr_sympy is not None:
            titulo = titulo_matematico(expr_sympy, var)
        else:
            titulo = f"f({var}) = {expr}"
        ax.set_title(
            titulo,
            fontsize=12,
            fontweight="bold",
            color=texto_color,
            pad=8,
        )

        finite_y = ys[np.isfinite(ys)]
        if len(finite_y) > 0:
            y_min = float(np.min(finite_y))
            y_max = float(np.max(finite_y))
            margen = (y_max - y_min) * 0.12 if y_max != y_min else abs(y_max) * 0.1 + 1
            # Margen superior ampliado: las etiquetas de maximo/minimo no se cortan
            ax.set_ylim(y_min - margen, y_max + margen * 1.6)

        ax.set_xlim(xs[0], xs[-1])

        # Aprovechar el tamano real del canvas al redimensionar
        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.figura.tight_layout(pad=0.8)
        except Exception:
            pass
        self.canvas.draw()

    # =====================================================
    # DIBUJAR 3D
    # =====================================================

    def _dibujar_3d(self, func, var, xs):

        self.figura3d.clear()
        self.ax3d = self.figura3d.add_subplot(111, projection="3d")

        fondo = "#1E293B" if self._modo_oscuro else _COLOR_FONDO_CANVAS
        self.ax3d.set_facecolor(fondo)
        self.figura3d.patch.set_facecolor(fondo)

        # Superficie adaptada: z = f(x) extruida sobre y
        n = 120
        x_vals = np.linspace(xs[0], xs[-1], n)
        y_vals = np.linspace(-2, 2, n)
        X, Y = np.meshgrid(x_vals, y_vals)

        try:
            Z_raw = func(X)
            Z = np.asarray(Z_raw, dtype=float)
            if Z.ndim == 0:
                Z = np.full_like(X, float(Z_raw))
            elif Z.shape != X.shape:
                Z = np.broadcast_to(Z, X.shape).copy()
            Z = np.where(np.isnan(Z) | np.isinf(Z), np.nan, Z)
        except Exception:
            Z = np.full_like(X, np.nan)

        if not np.all(np.isnan(Z)):
            surf = self.ax3d.plot_surface(
                X, Y, Z,
                cmap="viridis",
                rstride=1,
                cstride=1,
                linewidth=0,
                antialiased=True,
                shade=True,
                alpha=0.95,
            )
            self.figura3d.colorbar(surf, ax=self.ax3d, shrink=0.7, pad=0.06)

        self.ax3d.set_xlabel("x", fontsize=8, labelpad=-4)
        self.ax3d.set_ylabel("y", fontsize=8, labelpad=-4)
        self.ax3d.set_zlabel("z", fontsize=8, labelpad=-4)
        self.ax3d.tick_params(labelsize=7, pad=-2)
        self._tema_ejes_3d()

        z_vals = Z[np.isfinite(Z)]
        if len(z_vals) > 0:
            z_min = float(np.min(z_vals))
            z_max = float(np.max(z_vals))
            z_margen = (z_max - z_min) * 0.15 if z_max != z_min else abs(z_max) * 0.1 + 0.5
            self.ax3d.set_zlim(z_min - z_margen, z_max + z_margen)

        self.ax3d.view_init(elev=25, azim=135)

        self.ax3d.set_title(
            f"z = {self.txtExpresion.text().strip()}",
            fontsize=9, pad=2,
        )

        # Aprovechar el tamano real del canvas al redimensionar
        # NOTA: tight_layout NO funciona con proyecciones 3D en matplotlib
        self.figura3d.subplots_adjust(left=0.02, right=0.92, top=0.93, bottom=0.05)
        self.canvas3d.draw()

    # =====================================================
    # ACTUALIZAR INFO / TARJETAS / TABLA
    # =====================================================

    def _actualizar_info(self, expr, var, analisis, x_min, x_max, expr_sympy):

        # ---------- Panel derecho ----------
        self.infoExpresion.setText(f"f({var}) = {expr}")
        self.infoAnalisis.setText(_construir_analisis_texto(analisis, var))
        self.infoTipo.setText(analisis["tipo"])

        if analisis["eje_simetria"] is not None:
            self.infoSimetria.setText(f"Eje de simetría: x = {_fmt(analisis['eje_simetria'])}")
        elif analisis["tipo"] == "Lineal":
            self.infoSimetria.setText("Una recta no tiene eje de simetría.")
        else:
            self.infoSimetria.setText("Sin simetría axial evidente en el rango.")

        self.infoComportamiento.setText(
            analisis["comportamiento"] or "No determinado"
        )

        # ---------- Puntos clave ----------
        lineas_puntos = []

        for mx, my in analisis["maximos"]:
            lineas_puntos.append(f"\u25CF Máximo: ({_fmt(mx)}, {_fmt(my)})")
        for mn, my in analisis["minimos"]:
            lineas_puntos.append(f"\u25CF Mínimo: ({_fmt(mn)}, {_fmt(my)})")
        if analisis["inter_y"] is not None:
            lineas_puntos.append(f"\u25CF Intercepto Y: (0, {_fmt(analisis['inter_y'])})")
        for ix in analisis["inter_x"]:
            lineas_puntos.append(f"\u25CF Intercepto X: ({_fmt(ix)}, 0)")

        if not lineas_puntos:
            lineas_puntos.append("Sin puntos destacables en el rango.")

        self.lblPuntos.setText("\n".join(lineas_puntos))

        # ---------- Caracteristicas ----------
        rango_txt = "No disponible"
        rg = analisis.get("rango_global")
        if rg:
            lo, hi = rg
            if lo == "todos":
                rango_txt = "Todos los reales"
            else:
                izq = "(-\u221e" if np.isneginf(lo) else f"[{_fmt(lo)}"
                der = "\u221e)" if np.isposinf(hi) else f"{_fmt(hi)}]"
                rango_txt = f"{izq}, {der}"
        elif analisis["rango"]:
            rango_txt = f"[{_fmt(analisis['rango'][0])}, {_fmt(analisis['rango'][1])}]"

        def _intervalos(lista):
            if not lista:
                return "No aplica"
            return ", ".join(
                f"({_fmt(a)}, {_fmt(b)})" for a, b in lista[:3]
            )

        caract = (
            f"Dominio: {analisis['dominio']}\n"
            f"Rango: {rango_txt}\n"
            f"Creciente: {_intervalos(analisis['creciente'])}\n"
            f"Decreciente: {_intervalos(analisis['decreciente'])}"
        )
        self.lblCaract.setText(caract)

        # ---------- Tabla de valores (puntos enteros del rango) ----------
        import math

        from sympy import Symbol

        v_sym = Symbol(var)

        x_ini = math.ceil(x_min)
        x_fin = math.floor(x_max)
        enteros = list(range(x_ini, x_fin + 1))

        if len(enteros) >= 2:
            # Limitar filas si el rango es muy amplio
            paso_ent = max(1, (len(enteros) - 1) // 29)
            xs_tabla = enteros[::paso_ent]
            if xs_tabla[-1] != enteros[-1]:
                xs_tabla.append(enteros[-1])
        else:
            # Rango muy corto: puntos equiespaciados como respaldo
            xs_tabla = [
                x_min + i * (x_max - x_min) / 9 for i in range(10)
            ]

        n_filas = len(xs_tabla)
        self.tabla.setRowCount(n_filas)

        for i, xv in enumerate(xs_tabla):
            xv = float(xv)
            try:
                yv = float(expr_sympy.subs(v_sym, xv))
                y_txt = _fmt(yv) if np.isfinite(yv) else "indef."
            except Exception:
                y_txt = "indef."

            item_x = QTableWidgetItem(_fmt(xv))
            item_y = QTableWidgetItem(y_txt)
            item_x.setTextAlignment(Qt.AlignCenter)
            item_y.setTextAlignment(Qt.AlignCenter)

            self.tabla.setItem(i, 0, item_x)
            self.tabla.setItem(i, 1, item_y)

    # =====================================================
    # GUARDAR IMAGEN
    # =====================================================

    def guardar_imagen(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar gráfico como imagen",
            "",
            "PNG Image (*.png);;Todos los archivos (*.*)"
        )

        if not ruta:
            return

        if not ruta.lower().endswith(".png"):
            ruta += ".png"

        try:
            fondo = "#1E293B" if self._modo_oscuro else _COLOR_FONDO_CANVAS
            self.figura.savefig(ruta, dpi=150, bbox_inches="tight", facecolor=fondo)
            QMessageBox.information(
                self,
                "Guardado",
                f"Gráfico guardado correctamente en:\n{ruta}"
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo guardar el gráfico:\n{error}"
            )


# ---------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Graficador("-5*x^2+20*x+2", "x")
    ventana.show()

    sys.exit(app.exec_())
