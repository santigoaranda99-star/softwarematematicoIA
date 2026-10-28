from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QDialog,
    QCheckBox,
    QApplication,
    QSizePolicy,
    QButtonGroup,
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

import sys

from utils.rutas import ruta_recurso
from utils.dialogo_acerca import mostrar_acerca
from logic.calculadora_logic import (
    evaluar,
    formatear,
    fmt_historial,
    CONSTANTES,
)


# =====================================================
# ESTILOS (claro / oscuro) — mismo lenguaje que Graficador
# =====================================================

LIGHT_QSS = """
    QWidget { font-family: "Segoe UI"; }
    QWidget#fondo { background: #F1F5F9; }

    QFrame#sidebar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0B1437, stop:1 #111D4A);
        border: none;
    }
    QLabel#sidebarLogoText { color: #FFFFFF; font-size: 13px; font-weight: bold; background: transparent; }
    QLabel#sidebarSection {
        color: rgba(255,255,255,0.35); font-size: 10px; font-weight: bold;
        background: transparent; letter-spacing: 1px;
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

    QPushButton#btnTema, QPushButton#btnCerrar {
        background: #FFFFFF; color: #334155; border: 1px solid #E2E8F0;
        border-radius: 8px; padding: 6px 14px; font-weight: bold;
    }
    QPushButton#btnTema:hover, QPushButton#btnCerrar:hover { background: #F1F5F9; }

    /* ===== PANTALLA ===== */
    QFrame#pantalla { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 14px; }
    QLabel#modoBadge {
        color: #2563EB; font-size: 11px; font-weight: bold;
        background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 9px;
    }
    QLabel#lblExpresion { color: #94A3B8; font-size: 11px; font-weight: bold; background: transparent; }
    QLineEdit#txtExpresion {
        background: transparent; border: none; color: #334155;
        font-size: 17px; padding: 0;
    }
    QLabel#lblResultado { color: #0F172A; font-size: 34px; font-weight: bold; background: transparent; }
    QLabel#lblErrorPantalla { color: #DC2626; font-size: 22px; font-weight: bold; background: transparent; }

    /* ===== SELECTOR DE MODO ===== */
    QPushButton#teclaModo {
        background: #FFFFFF; color: #334155; border: 1px solid #E2E8F0;
        border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: bold;
    }
    QPushButton#teclaModo:checked { background: #2563EB; color: #FFFFFF; border-color: #2563EB; }
    QPushButton#teclaModo:hover { border-color: #93C5FD; }

    /* ===== MEMORIA ===== */
    QLabel#lblMemoria { color: #64748B; font-size: 11px; font-weight: bold; background: transparent; }
    QPushButton#teclaMem {
        background: #FFFFFF; color: #475569; border: 1px solid #E2E8F0;
        border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: bold;
    }
    QPushButton#teclaMem:hover { background: #F1F5F9; border-color: #CBD5E1; }

    /* ===== TECLADO ===== */
    QPushButton#teclaNum {
        background: #FFFFFF; color: #0F172A; border: 1px solid #E2E8F0;
        border-radius: 10px; font-size: 15px; font-weight: bold;
    }
    QPushButton#teclaNum:hover { background: #F8FAFC; border-color: #CBD5E1; }
    QPushButton#teclaNum:pressed { background: #EFF6FF; }

    QPushButton#teclaFunc {
        background: #FFFFFF; color: #2563EB; border: 1px solid #E2E8F0;
        border-radius: 10px; font-size: 13px; font-weight: bold;
    }
    QPushButton#teclaFunc:hover { background: #F8FAFC; border-color: #93C5FD; }
    QPushButton#teclaFunc:pressed { background: #EFF6FF; }

    QPushButton#teclaOp {
        background: #EFF6FF; color: #2563EB; border: 1px solid #DBEAFE;
        border-radius: 10px; font-size: 16px; font-weight: bold;
    }
    QPushButton#teclaOp:hover { background: #DBEAFE; }
    QPushButton#teclaOp:pressed { background: #BFDBFE; }

    QPushButton#teclaPeligro {
        background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;
        border-radius: 10px; font-size: 13px; font-weight: bold;
    }
    QPushButton#teclaPeligro:hover { background: #FEE2E2; }
    QPushButton#teclaPeligro:pressed { background: #FECACA; }

    QPushButton#tecla2nd {
        background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE;
        border-radius: 10px; font-size: 13px; font-weight: bold;
    }
    QPushButton#tecla2nd:checked {
        background: #2563EB; color: #FFFFFF; border-color: #2563EB;
    }
    QPushButton#tecla2nd:hover { border-color: #60A5FA; }

    QPushButton#teclaIgual {
        background: #2563EB; color: #FFFFFF; border: none;
        border-radius: 10px; font-size: 18px; font-weight: bold;
    }
    QPushButton#teclaIgual:hover { background: #1D4ED8; }
    QPushButton#teclaIgual:pressed { background: #1E40AF; }

    /* ===== PANEL DERECHO ===== */
    QLabel#cardTitulo { color: #2563EB; font-size: 12px; font-weight: bold; background: transparent; }
    QPushButton#btnBasura {
        background: transparent; border: none; font-size: 14px; border-radius: 6px; padding: 2px 6px;
    }
    QPushButton#btnBasura:hover { background: #FEF2F2; }

    QListWidget#listaHistorial {
        background: transparent; border: none; font-size: 12px; color: #334155;
    }
    QListWidget#listaHistorial::item { padding: 6px 4px; border-bottom: 1px solid #F1F5F9; }
    QListWidget#listaHistorial::item:selected { background: #EFF6FF; color: #1D4ED8; }

    QPushButton#btnConstante {
        background: #F8FAFC; color: #334155; border: 1px solid #EEF2F7;
        border-radius: 8px; padding: 5px 8px; font-size: 12px; text-align: left;
    }
    QPushButton#btnConstante:hover { background: #EFF6FF; border-color: #BFDBFE; }

    QLabel#atajoTecla {
        color: #1E40AF; font-size: 10px; font-weight: bold;
        background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 6px;
    }
    QLabel#atajoDesc { color: #64748B; font-size: 11px; background: transparent; }

    QLabel#pie { color: #94A3B8; font-size: 11px; background: transparent; }

    QScrollArea { border: none; background: transparent; }
"""

DARK_QSS = """
    QWidget { font-family: "Segoe UI"; }
    QWidget#fondo { background: #0F172A; }

    QFrame#sidebar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0B1437, stop:1 #111D4A);
        border: none;
    }
    QLabel#sidebarLogoText { color: #FFFFFF; font-size: 13px; font-weight: bold; background: transparent; }
    QLabel#sidebarSection {
        color: rgba(255,255,255,0.35); font-size: 10px; font-weight: bold;
        background: transparent; letter-spacing: 1px;
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

    QPushButton#btnTema, QPushButton#btnCerrar {
        background: #1E293B; color: #E2E8F0; border: 1px solid #334155;
        border-radius: 8px; padding: 6px 14px; font-weight: bold;
    }
    QPushButton#btnTema:hover, QPushButton#btnCerrar:hover { background: #334155; }

    /* ===== PANTALLA ===== */
    QFrame#pantalla { background: #0B1220; border: 1px solid #334155; border-radius: 14px; }
    QLabel#modoBadge {
        color: #93C5FD; font-size: 11px; font-weight: bold;
        background: rgba(147,197,253,0.12); border: 1px solid rgba(147,197,253,0.30); border-radius: 9px;
    }
    QLabel#lblExpresion { color: #64748B; font-size: 11px; font-weight: bold; background: transparent; }
    QLineEdit#txtExpresion {
        background: transparent; border: none; color: #E2E8F0;
        font-size: 17px; padding: 0;
    }
    QLabel#lblResultado { color: #F1F5F9; font-size: 34px; font-weight: bold; background: transparent; }
    QLabel#lblErrorPantalla { color: #F87171; font-size: 22px; font-weight: bold; background: transparent; }

    /* ===== SELECTOR DE MODO ===== */
    QPushButton#teclaModo {
        background: #1E293B; color: #CBD5E1; border: 1px solid #334155;
        border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: bold;
    }
    QPushButton#teclaModo:checked { background: #2563EB; color: #FFFFFF; border-color: #2563EB; }
    QPushButton#teclaModo:hover { border-color: #60A5FA; }

    /* ===== MEMORIA ===== */
    QLabel#lblMemoria { color: #94A3B8; font-size: 11px; font-weight: bold; background: transparent; }
    QPushButton#teclaMem {
        background: #1E293B; color: #CBD5E1; border: 1px solid #334155;
        border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: bold;
    }
    QPushButton#teclaMem:hover { background: #334155; }

    /* ===== TECLADO ===== */
    QPushButton#teclaNum {
        background: #1E293B; color: #F1F5F9; border: 1px solid #334155;
        border-radius: 10px; font-size: 15px; font-weight: bold;
    }
    QPushButton#teclaNum:hover { background: #26334D; border-color: #475569; }
    QPushButton#teclaNum:pressed { background: #1E3A5F; }

    QPushButton#teclaFunc {
        background: #1E293B; color: #60A5FA; border: 1px solid #334155;
        border-radius: 10px; font-size: 13px; font-weight: bold;
    }
    QPushButton#teclaFunc:hover { background: #26334D; border-color: #60A5FA; }
    QPushButton#teclaFunc:pressed { background: #1E3A5F; }

    QPushButton#teclaOp {
        background: rgba(37, 99, 235, 0.18); color: #93C5FD; border: 1px solid rgba(37, 99, 235, 0.35);
        border-radius: 10px; font-size: 16px; font-weight: bold;
    }
    QPushButton#teclaOp:hover { background: rgba(37, 99, 235, 0.30); }
    QPushButton#teclaOp:pressed { background: rgba(37, 99, 235, 0.42); }

    QPushButton#teclaPeligro {
        background: rgba(220, 38, 38, 0.12); color: #F87171; border: 1px solid rgba(220, 38, 38, 0.30);
        border-radius: 10px; font-size: 13px; font-weight: bold;
    }
    QPushButton#teclaPeligro:hover { background: rgba(220, 38, 38, 0.22); }
    QPushButton#teclaPeligro:pressed { background: rgba(220, 38, 38, 0.32); }

    QPushButton#tecla2nd {
        background: rgba(37, 99, 235, 0.18); color: #93C5FD; border: 1px solid rgba(37, 99, 235, 0.35);
        border-radius: 10px; font-size: 13px; font-weight: bold;
    }
    QPushButton#tecla2nd:checked {
        background: #2563EB; color: #FFFFFF; border-color: #2563EB;
    }
    QPushButton#tecla2nd:hover { border-color: #60A5FA; }

    QPushButton#teclaIgual {
        background: #2563EB; color: #FFFFFF; border: none;
        border-radius: 10px; font-size: 18px; font-weight: bold;
    }
    QPushButton#teclaIgual:hover { background: #3B82F6; }
    QPushButton#teclaIgual:pressed { background: #1D4ED8; }

    /* ===== PANEL DERECHO ===== */
    QLabel#cardTitulo { color: #93C5FD; font-size: 12px; font-weight: bold; background: transparent; }
    QPushButton#btnBasura {
        background: transparent; border: none; font-size: 14px; border-radius: 6px; padding: 2px 6px;
    }
    QPushButton#btnBasura:hover { background: rgba(220, 38, 38, 0.15); }

    QListWidget#listaHistorial {
        background: transparent; border: none; font-size: 12px; color: #CBD5E1;
    }
    QListWidget#listaHistorial::item { padding: 6px 4px; border-bottom: 1px solid #26334D; }
    QListWidget#listaHistorial::item:selected { background: rgba(37, 99, 235, 0.25); color: #FFFFFF; }

    QPushButton#btnConstante {
        background: #0B1220; color: #CBD5E1; border: 1px solid #26334D;
        border-radius: 8px; padding: 5px 8px; font-size: 12px; text-align: left;
    }
    QPushButton#btnConstante:hover { background: #1E293B; border-color: #60A5FA; }

    QLabel#atajoTecla {
        color: #93C5FD; font-size: 10px; font-weight: bold;
        background: rgba(37, 99, 235, 0.18); border: 1px solid rgba(37, 99, 235, 0.35); border-radius: 6px;
    }
    QLabel#atajoDesc { color: #94A3B8; font-size: 11px; background: transparent; }

    QLabel#pie { color: #64748B; font-size: 11px; background: transparent; }

    QScrollArea { border: none; background: transparent; }
"""


class Calculadora(QWidget):

    def __init__(self, usuario=None):
        super().__init__()

        self.usuario = usuario
        self._modo_oscuro = False
        self._modo_angular = "DEG"
        self._memoria = 0.0
        self._ans = 0.0
        self._resultado_valor = 0.0
        self._segundo = False
        self._estado_teclas = {}

        self.setWindowTitle("Software Matemático IA — Calculadora Científica")

        # Ajuste a pantalla disponible
        pantalla = QApplication.primaryScreen()
        ancho_objetivo, alto_objetivo = 1180, 720
        ancho_minimo, alto_minimo = 1000, 640
        if pantalla:
            geom = pantalla.availableGeometry()
            ancho_objetivo = min(ancho_objetivo, geom.width() - 20)
            alto_objetivo = min(alto_objetivo, geom.height() - 20)
            ancho_minimo = min(ancho_minimo, geom.width() - 20)
            alto_minimo = min(alto_minimo, geom.height() - 20)
        self.setMinimumSize(ancho_minimo, alto_minimo)
        self.resize(ancho_objetivo, alto_objetivo)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)

        self.setStyleSheet(LIGHT_QSS)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._construir_sidebar(root)

        fondo = QWidget()
        fondo.setObjectName("fondo")
        root.addWidget(fondo, 1)

        exterior = QVBoxLayout(fondo)
        exterior.setContentsMargins(18, 14, 18, 10)
        exterior.setSpacing(10)

        self._construir_encabezado(exterior)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(14)
        exterior.addLayout(cuerpo, 1)

        self._construir_zona_calculadora(cuerpo)
        self._construir_panel_derecho(cuerpo)

        pie = QLabel("Software Matemático IA \u2022 Versión 1.1 \u2022 Calculadora Científica")
        pie.setObjectName("pie")
        pie.setAlignment(Qt.AlignCenter)
        exterior.addWidget(pie)

        self.setFocusPolicy(Qt.StrongFocus)

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

        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        logo_lbl = QLabel()
        from utils.logos import crear_logo_circular

        pixmap = crear_logo_circular(ruta_recurso("images/logo.jpg"), 28)
        if not pixmap.isNull():
            logo_lbl.setPixmap(pixmap)
        logo_lbl.setFixedSize(30, 30)
        logo_lbl.setStyleSheet("background: transparent;")
        logo_txt = QLabel("Calculadora IA")
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

        self.nav_botones = {}

        nav_items = [
            ("graficador", "\U0001F4C8", "Graficador"),
            ("calculadora", "\U0001F9EE", "Calculadora"),
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

        self.nav_botones["calculadora"].setChecked(True)

        sb.addStretch()

        ai_card = QFrame()
        ai_card.setObjectName("aiCard")
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(12, 10, 12, 10)
        ai_layout.setSpacing(3)

        ai_title = QLabel("\U0001F916 Potenciado con IA")
        ai_title.setObjectName("aiTitle")
        ai_desc = QLabel(
            "Obtén resultados precisos,\npaso a paso, y explicaciones\ninteligentes."
        )
        ai_desc.setObjectName("aiDesc")

        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(ai_desc)

        sb.addWidget(ai_card)

        root.addWidget(sidebar)

    def _navegar(self, clave):

        if clave == "calculadora":
            return

        for c, b in self.nav_botones.items():
            b.setChecked(c == clave)

        if clave == "graficador":
            from interfaces.graficador import Graficador

            self.graficador = Graficador(usuario=self.usuario)
            self.graficador.show()
            self.close()
            return

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
            self.nav_botones["calculadora"].setChecked(True)

    def _dialogo_funciones(self):
        QMessageBox.information(
            self,
            "Funciones soportadas",
            "Operadores: + \u2212 \u00d7 \u00f7 ^ %\n"
            "Trigonom\u00e9tricas: sin, cos, tan\n"
            "Inversas: asin, acos, atan\n"
            "Hiperb\u00f3licas: sinh, cosh, tanh (+ inversas)\n"
            "Logaritmos: ln, log, log10\n"
            "Ra\u00edz: \u221a   Valor absoluto: |x|\n"
            "Constantes: \u03c0, e, \u03c6, \u03b3, Ans\n\n"
            "Ejemplos:\n"
            "sin(30) + \u221a16 \u00d7 log(100)\n"
            "2^8 + 50%"
        )

    def _dialogo_historial(self):
        QMessageBox.information(
            self,
            "Historial",
            "El historial de esta sesi\u00f3n se muestra en el panel derecho.\n"
            "Tus consultas resueltas con IA est\u00e1n en el Panel Principal."
        )

    def _dialogo_favoritos(self):
        QMessageBox.information(
            self,
            "Favoritos",
            "Guarda tus funciones favoritas desde el Graficador.\n"
            "Aqu\u00ed puedes usar las constantes \u03c0, e, \u03c6 y \u03b3."
        )

    def _dialogo_ajustes(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ajustes de la calculadora")
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
            "Ayuda de la Calculadora",
            "1. Escribe o construye una expresi\u00f3n.\n"
            "2. Elige el modo angular DEG / RAD / GRAD.\n"
            "3. Presiona = para calcular.\n\n"
            "Ans inserta el \u00faltimo resultado.\n"
            "MC/MR/M+/M\u2212 controlan la memoria.\n"
            "2nd activa funciones inversas."
        )

    def _dialogo_acerca(self):
        mostrar_acerca(
            self,
            "Calculadora Científica IA",
            "Python + PyQt5 + SymPy",
        )

    # =====================================================
    # ENCABEZADO
    # =====================================================

    def _construir_encabezado(self, exterior):

        header = QHBoxLayout()
        header.setSpacing(10)

        chip = QLabel("\U0001F9EE")
        chip.setFixedSize(44, 44)
        chip.setAlignment(Qt.AlignCenter)
        chip.setStyleSheet("""
            font-size: 20px; background: #EFF6FF;
            border: 1px solid #DBEAFE; border-radius: 12px;
        """)

        titulos = QVBoxLayout()
        titulos.setSpacing(0)
        t = QLabel("Calculadora Científica IA")
        t.setObjectName("tituloVentana")
        s = QLabel("Realiza cálculos matemáticos avanzados")
        s.setObjectName("subtituloVentana")
        titulos.addWidget(t)
        titulos.addWidget(s)

        header.addWidget(chip)
        header.addLayout(titulos)
        header.addStretch()

        btn_volver = QPushButton("\u2B05 Panel Principal")
        btn_volver.setObjectName("btnCerrar")
        btn_volver.setCursor(Qt.PointingHandCursor)
        btn_volver.setFixedHeight(32)
        btn_volver.clicked.connect(self.volver_panel)

        self.btnTema = QPushButton("\U0001F312 Claro / Oscuro")
        self.btnTema.setObjectName("btnTema")
        self.btnTema.setCursor(Qt.PointingHandCursor)
        self.btnTema.clicked.connect(
            lambda: self._alternar_tema(not self._modo_oscuro)
        )

        btn_cerrar = QPushButton("\u2715 Cerrar")
        btn_cerrar.setObjectName("btnCerrar")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.close)

        header.addWidget(btn_volver)
        header.addWidget(self.btnTema)
        header.addWidget(btn_cerrar)

        exterior.addLayout(header)

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

    # =====================================================
    # ZONA CENTRAL: PANTALLA + TECLADO
    # =====================================================

    def _construir_zona_calculadora(self, cuerpo):

        col = QVBoxLayout()
        col.setSpacing(10)

        # ---------- Pantalla ----------
        pantalla = QFrame()
        pantalla.setObjectName("pantalla")

        pv = QVBoxLayout(pantalla)
        pv.setContentsMargins(20, 12, 20, 14)
        pv.setSpacing(2)

        fila_sup = QHBoxLayout()
        self.badgeModo = QLabel("DEG")
        self.badgeModo.setObjectName("modoBadge")
        self.badgeModo.setFixedSize(48, 20)
        self.badgeModo.setAlignment(Qt.AlignCenter)

        lbl_exp = QLabel("Expresión")
        lbl_exp.setObjectName("lblExpresion")

        fila_sup.addWidget(self.badgeModo)
        fila_sup.addStretch()
        fila_sup.addWidget(lbl_exp)
        pv.addLayout(fila_sup)

        self.txtExpresion = QLineEdit()
        self.txtExpresion.setObjectName("txtExpresion")
        self.txtExpresion.setAlignment(Qt.AlignRight)
        self.txtExpresion.setPlaceholderText("sin(30) + \u221a16 \u00d7 log(100)")
        self.txtExpresion.returnPressed.connect(self.calcular)
        pv.addWidget(self.txtExpresion)

        self.lblResultado = QLabel("0")
        self.lblResultado.setObjectName("lblResultado")
        self.lblResultado.setAlignment(Qt.AlignRight)
        pv.addWidget(self.lblResultado)

        col.addWidget(pantalla)

        # ---------- Modo angular + memoria ----------
        fila_modos = QHBoxLayout()
        fila_modos.setSpacing(6)

        self.grupo_modos = QButtonGroup(self)
        self.grupo_modos.setExclusive(True)

        for modo in ("DEG", "RAD", "GRAD"):
            btn = QPushButton(modo)
            btn.setObjectName("teclaModo")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setChecked(modo == self._modo_angular)
            btn.clicked.connect(lambda checked, m=modo: self.cambiar_modo(m))
            self.grupo_modos.addButton(btn)
            fila_modos.addWidget(btn)

        fila_modos.addStretch()

        lbl_mem = QLabel("Memoria")
        lbl_mem.setObjectName("lblMemoria")
        fila_modos.addWidget(lbl_mem)
        fila_modos.addSpacing(4)

        for texto, accion in (
            ("MC", self.mem_limpiar),
            ("MR", self.mem_recuperar),
            ("M+", self.mem_sumar),
            ("M\u2212", self.mem_restar),
        ):
            btn = QPushButton(texto)
            btn.setObjectName("teclaMem")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(46)
            btn.clicked.connect(accion)
            fila_modos.addWidget(btn)

        col.addLayout(fila_modos)

        # ---------- Teclado cientifico ----------
        tarjeta = QFrame()
        tarjeta.setObjectName("card")

        grid = QGridLayout(tarjeta)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(8)

        for c in range(8):
            grid.setColumnStretch(c, 1)

        self.teclas_2nd = {}

        filas = [
            # (texto, inserta, clase, span_cols)
            [("2nd", None, "tecla2nd", 1), ("(", "(", "teclaNum", 1),
             (")", ")", "teclaNum", 1), ("%", "%", "teclaNum", 1),
             ("AC", "AC", "teclaPeligro", 2), ("CE", "CE", "teclaPeligro", 2)],

            [("sin", "sin(", "teclaFunc", 1), ("cos", "cos(", "teclaFunc", 1),
             ("tan", "tan(", "teclaFunc", 1), ("\u03c0", "\u03c0", "teclaFunc", 1),
             ("7", "7", "teclaNum", 1), ("8", "8", "teclaNum", 1),
             ("9", "9", "teclaNum", 1), ("\u00f7", "\u00f7", "teclaOp", 1)],

            [("asin", "asin(", "teclaFunc", 1), ("acos", "acos(", "teclaFunc", 1),
             ("atan", "atan(", "teclaFunc", 1), ("e", "e", "teclaFunc", 1),
             ("4", "4", "teclaNum", 1), ("5", "5", "teclaNum", 1),
             ("6", "6", "teclaNum", 1), ("\u00d7", "\u00d7", "teclaOp", 1)],

            [("sinh", "sinh(", "teclaFunc", 1), ("cosh", "cosh(", "teclaFunc", 1),
             ("tanh", "tanh(", "teclaFunc", 1), ("ln", "ln(", "teclaFunc", 1),
             ("1", "1", "teclaNum", 1), ("2", "2", "teclaNum", 1),
             ("3", "3", "teclaNum", 1), ("\u2212", "\u2212", "teclaOp", 1)],

            [("log", "log(", "teclaFunc", 1), ("log\u2081\u2080", "log10(", "teclaFunc", 1),
             ("\u221a", "\u221a(", "teclaFunc", 1), ("x\u00b2", "^2", "teclaFunc", 1),
             ("0", "0", "teclaNum", 1), (".", ".", "teclaNum", 1),
             ("Ans", "Ans", "teclaFunc", 1), ("+", "+", "teclaOp", 1)],

            [("|x|", "abs(", "teclaFunc", 1), ("x\u02b8", "^", "teclaFunc", 1),
             ("x\u207b\u00b9", "^(-1)", "teclaFunc", 1),
             ("\u232b", "\u232b", "teclaPeligro", 1),
             ("=", "=", "teclaIgual", 3)],
        ]

        for f, fila in enumerate(filas):
            columna = 0
            for texto, inserta, clase, span in fila:
                btn = QPushButton(texto)
                btn.setObjectName(clase)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setMinimumHeight(44)

                if texto == "2nd":
                    btn.setCheckable(True)
                    btn.clicked.connect(self.alternar_2nd)
                elif texto == "=":
                    btn.clicked.connect(self.calcular)
                elif texto == "AC":
                    btn.clicked.connect(self.limpiar_todo)
                elif texto == "CE":
                    btn.clicked.connect(self.limpiar_entrada)
                elif texto == "\u232b":
                    btn.clicked.connect(self._retroceso)
                elif texto in self.CLAVES_2ND:
                    tn, ins_n, _, _ = self.CLAVES_2ND[texto]
                    self._estado_teclas[texto] = [tn, ins_n]
                    btn.clicked.connect(
                        lambda checked, k=texto: self.insertar(
                            self._estado_teclas[k][1]
                        )
                    )
                else:
                    btn.clicked.connect(
                        lambda checked, t=inserta: self.insertar(t)
                    )

                grid.addWidget(btn, f, columna, 1, span)
                self.teclas_2nd[texto] = (btn, inserta)
                columna += span

        col.addWidget(tarjeta, 1)

        contenedor = QWidget()
        contenedor.setLayout(col)
        cuerpo.addWidget(contenedor, 3)

    # =====================================================
    # PANEL DERECHO
    # =====================================================

    def _construir_panel_derecho(self, cuerpo):

        panel = QVBoxLayout()
        panel.setSpacing(10)

        ancho = 290

        # ---------- Historial ----------
        card_hist = QFrame()
        card_hist.setObjectName("card")
        card_hist.setFixedWidth(ancho)

        hv = QVBoxLayout(card_hist)
        hv.setContentsMargins(14, 12, 14, 12)
        hv.setSpacing(6)

        h_head = QHBoxLayout()
        titulo_h = QLabel("\U0001F553 Historial")
        titulo_h.setObjectName("cardTitulo")
        btn_basura = QPushButton("\U0001F5D1")
        btn_basura.setObjectName("btnBasura")
        btn_basura.setCursor(Qt.PointingHandCursor)
        btn_basura.setToolTip("Borrar historial")
        h_head.addWidget(titulo_h)
        h_head.addStretch()
        h_head.addWidget(btn_basura)
        hv.addLayout(h_head)

        self.listaHistorial = QListWidget()
        self.listaHistorial.setObjectName("listaHistorial")
        self.listaHistorial.itemClicked.connect(self.usar_del_historial)
        hv.addWidget(self.listaHistorial, 1)

        btn_basura.clicked.connect(self.listaHistorial.clear)

        panel.addWidget(card_hist, 3)

        # ---------- Constantes ----------
        card_const = QFrame()
        card_const.setObjectName("card")
        card_const.setFixedWidth(ancho)

        cv = QVBoxLayout(card_const)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(6)

        titulo_c = QLabel("\u03c0 Constantes")
        titulo_c.setObjectName("cardTitulo")
        cv.addWidget(titulo_c)

        grid_c = QGridLayout()
        grid_c.setVerticalSpacing(4)
        grid_c.setHorizontalSpacing(8)

        for i, (simbolo, _, valor) in enumerate(CONSTANTES):
            btn = QPushButton(f"{simbolo} = {valor}")
            btn.setObjectName("btnConstante")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, s=simbolo: self.insertar(s)
            )
            grid_c.addWidget(btn, i // 2, i % 2)

        cv.addLayout(grid_c)

        panel.addWidget(card_const)

        # ---------- Teclas rapidas ----------
        card_atajos = QFrame()
        card_atajos.setObjectName("card")
        card_atajos.setFixedWidth(ancho)

        av = QVBoxLayout(card_atajos)
        av.setContentsMargins(14, 12, 14, 12)
        av.setSpacing(6)

        titulo_a = QLabel("\u2328 Teclas rápidas")
        titulo_a.setObjectName("cardTitulo")
        av.addWidget(titulo_a)

        atajos = (
            ("AC", "Limpiar todo"),
            ("CE", "Limpiar entrada"),
            ("Ans", "\u00daltimo resultado"),
            ("2nd", "Funciones avanzadas"),
            ("DEG/RAD", "Cambiar modo angular"),
        )

        for tecla, desc in atajos:
            fila = QHBoxLayout()
            fila.setSpacing(8)
            k = QLabel(tecla)
            k.setObjectName("atajoTecla")
            k.setAlignment(Qt.AlignCenter)
            k.setFixedWidth(64)
            d = QLabel(desc)
            d.setObjectName("atajoDesc")
            fila.addWidget(k)
            fila.addWidget(d, 1)
            av.addLayout(fila)

        panel.addWidget(card_atajos)
        panel.addStretch()

        contenedor = QWidget()
        contenedor.setLayout(panel)
        cuerpo.addWidget(contenedor)

    # =====================================================
    # ACCIONES DE LA CALCULADORA
    # =====================================================

    def insertar(self, texto):
        cursor = self.txtExpresion.cursorPosition()
        actual = self.txtExpresion.text()
        nuevo = actual[:cursor] + texto + actual[cursor:]
        self.txtExpresion.setText(nuevo)
        self.txtExpresion.setCursorPosition(cursor + len(texto))
        self.txtExpresion.setFocus()

    def limpiar_todo(self):
        self.txtExpresion.clear()
        self.lblResultado.setText("0")
        self._restaurar_resultado()
        self.txtExpresion.setFocus()

    def limpiar_entrada(self):
        self.txtExpresion.clear()
        self.txtExpresion.setFocus()

    # Tokens que se borran completos con la tecla de retroceso
    TOKENS_BORRABLES = (
        "asinh(", "acosh(", "atanh(", "log10(", "asin(", "acos(",
        "atan(", "sinh(", "cosh(", "tanh(", "abs(", "sin(", "cos(",
        "tan(", "log(", "ln(", "^(-1)", "^(1/3)", "Ans", "^2", "^3",
    )

    def _retroceso(self):
        campo = self.txtExpresion
        cursor = campo.cursorPosition()

        if cursor == 0:
            campo.setFocus()
            return

        antes = campo.text()[:cursor]
        borrado = 1
        for token in self.TOKENS_BORRABLES:
            if antes.endswith(token):
                borrado = len(token)
                break

        texto = campo.text()
        campo.setText(texto[:cursor - borrado] + texto[cursor:])
        campo.setCursorPosition(cursor - borrado)
        campo.setFocus()

    def calcular(self):
        expresion = self.txtExpresion.text()

        ok, valor = evaluar(expresion, self._modo_angular, self._ans)

        if ok:
            self._ans = valor
            self._resultado_valor = valor
            self.lblResultado.setText(formatear(valor))
            self._restaurar_resultado()
            item = QListWidgetItem(f"{expresion.strip()} = {fmt_historial(valor)}")
            self.listaHistorial.insertItem(0, item)
        else:
            self.lblResultado.setText(valor)
            self._mostrar_error_pantalla()

        self.txtExpresion.setFocus()

    def _mostrar_error_pantalla(self):
        fuente = self.lblResultado.font()
        self.lblResultado.setObjectName("lblErrorPantalla")
        self.lblResultado.setStyleSheet("")
        self._repolish(self.lblResultado)

    def _restaurar_resultado(self):
        self.lblResultado.setObjectName("lblResultado")
        self._repolish(self.lblResultado)

    def _repolish(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def usar_del_historial(self, item):
        texto = item.text().split("=")[0].strip()
        self.txtExpresion.setText(texto)
        self.txtExpresion.setFocus()

    def cambiar_modo(self, modo):
        self._modo_angular = modo
        self.badgeModo.setText(modo)
        self.txtExpresion.setFocus()

    # ---------- Memoria ----------

    def mem_limpiar(self):
        self._memoria = 0.0
        self.txtExpresion.setFocus()

    def mem_recuperar(self):
        self.insertar(fmt_historial(self._memoria))

    def mem_sumar(self):
        self._memoria += self._resultado_valor
        self.txtExpresion.setFocus()

    def mem_restar(self):
        self._memoria -= self._resultado_valor
        self.txtExpresion.setFocus()

    # ---------- 2nd ----------

    # clave -> (texto_normal, inserta_normal, texto_2nd, inserta_2nd)
    CLAVES_2ND = {
        "sin": ("sin", "sin(", "sin\u207b\u00b9", "asin("),
        "cos": ("cos", "cos(", "cos\u207b\u00b9", "acos("),
        "tan": ("tan", "tan(", "tan\u207b\u00b9", "atan("),
        "sinh": ("sinh", "sinh(", "sinh\u207b\u00b9", "asinh("),
        "cosh": ("cosh", "cosh(", "cosh\u207b\u00b9", "acosh("),
        "tanh": ("tanh", "tanh(", "tanh\u207b\u00b9", "atanh("),
        "ln": ("ln", "ln(", "e\u02e3", "exp("),
        "log": ("log", "log(", "10\u02e3", "10^("),
        "\u221a": ("\u221a", "\u221a(", "\u221b", "^(1/3)"),
        "x\u00b2": ("x\u00b2", "^2", "x\u00b3", "^3"),
    }

    def alternar_2nd(self):
        self._segundo = not self._segundo

        for clave, estados in self.CLAVES_2ND.items():
            btn, _ = self.teclas_2nd[clave]
            if self._segundo:
                self._estado_teclas[clave] = [estados[2], estados[3]]
            else:
                self._estado_teclas[clave] = [estados[0], estados[1]]
            btn.setText(self._estado_teclas[clave][0])

        self.txtExpresion.setFocus()

    # =====================================================
    # TEMA
    # =====================================================

    def _alternar_tema(self, oscuro):
        self._modo_oscuro = oscuro
        self.setStyleSheet(DARK_QSS if oscuro else LIGHT_QSS)
        self.btnTema.setText(
            "\u2600\uFE0F Modo claro" if oscuro else "\U0001F312 Modo oscuro"
        )

    # =====================================================
    # TECLADO FISICO
    # =====================================================

    def keyPressEvent(self, event):
        texto = event.text()
        clave = event.key()

        if clave in (Qt.Key_Return, Qt.Key_Enter):
            self.calcular()
        elif clave == Qt.Key_Escape:
            self.limpiar_todo()
        elif clave == Qt.Key_Backspace:
            self._retroceso()
        elif texto and (texto.isdigit() or texto in "+-*/^().%"):
            self.insertar(texto)
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Calculadora()

    ventana.show()

    sys.exit(app.exec_())
