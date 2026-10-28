from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QMessageBox,
    QFileDialog,
    QApplication,
    QScrollArea,
    QSizePolicy,
    QDialog,
    QCheckBox,
)

from PyQt5.QtGui import QPixmap, QGuiApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import sys
import os

from utils.rutas import ruta_recurso
from interfaces.menu import aplicar_sombra
from utils.parsing_respuesta import separar_procedimiento_resultado
from utils.validador_matematico import validar_resultado
import re


# =============================================================
# HILO DE RESOLUCIÓN EN SEGUNDO PLANO (NO CONGELA LA UI)
# =============================================================

class ResolverWorker(QThread):
    """Hilo asíncrono para ejecutar la consulta de IA sin congelar la ventana."""
    resultado_listo = pyqtSignal(bool, str)

    def __init__(self, problema, imagenes):
        """
        imagenes: lista de tuplas (bytes, mime_type).
                  Si está vacía se usa solo texto.
        """
        super().__init__()
        self.problema = problema
        self.imagenes = imagenes  # [(bytes, mime), ...]
        # Compatibilidad con código legado que accede a imagen_bytes/mime
        self.imagen_bytes = imagenes[0][0] if imagenes else None
        self.imagen_mime  = imagenes[0][1] if imagenes else None

    def run(self):
        try:
            from services.ia_service import IAService
            ia = IAService()
            if self.imagenes:
                ok, respuesta = ia.resolver_problema_con_imagenes(
                    self.problema,
                    self.imagenes
                )
            else:
                ok, respuesta = ia.resolver_problema(self.problema)
            self.resultado_listo.emit(ok, respuesta)
        except Exception as e:
            self.resultado_listo.emit(False, f"Error inesperado al conectar con la IA:\n{e}")



# =============================================================
# HOJA DE ESTILOS — TEMA CLARO (paleta azul profesional)
# =============================================================

QSS_CLARO = """
    Resolver {
        background: #F4F7FB;
        font-family: "Segoe UI";
        font-size: 13px;
    }

    /* ================= SIDEBAR ================= */
    QFrame#sidebar {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #0F2F66,
            stop:1 #0B2450
        );
        border: none;
    }

    QLabel#sidebarNombreApp {
        color: #FFFFFF;
        font-size: 13px;
        font-weight: bold;
        background: transparent;
    }
    QLabel#sidebarSubApp {
        color: rgba(255,255,255,0.55);
        font-size: 10px;
        background: transparent;
    }
    QFrame#logoCircle {
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: 23px;
    }
    QFrame#lineaSidebar {
        background: rgba(255,255,255,0.10);
        max-height: 1px;
        border: none;
    }

    QPushButton#navItem {
        background: transparent;
        color: #C7D6F2;
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        text-align: left;
        font-size: 13px;
    }
    QPushButton#navItem:hover {
        background: rgba(255,255,255,0.08);
        color: #FFFFFF;
    }
    QPushButton#navItem:checked {
        background: #2563EB;
        color: #FFFFFF;
        font-weight: bold;
    }

    QLabel#lblCaptionTema {
        color: rgba(255,255,255,0.65);
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 1px;
        background: transparent;
    }
    QFrame#switchTema {
        background: rgba(255,255,255,0.18);
        border: none;
        border-radius: 13px;
    }
    QFrame#switchTema[encendido="true"] {
        background: #2563EB;
    }
    QLabel#knobTema {
        background: #FFFFFF;
        border-radius: 9px;
    }

    /* ================= ZONA CENTRAL ================= */
    QWidget#zonaCentral {
        background: #F4F7FB;
    }
    QScrollArea#zonaScroll {
        background: transparent;
        border: none;
    }
    QWidget#scrollContenido {
        background: transparent;
    }
    QScrollBar:vertical {
        background: transparent;
        width: 9px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #C4D2E6;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: #A9BCD8; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    /* ================= HEADER ================= */
    QFrame#header {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 #1E40AF,
            stop:0.55 #2563EB,
            stop:1 #3B82F6
        );
        border: 1px solid #3B82F6;
        border-radius: 18px;
    }
    QLabel#appTitulo {
        color: #FFFFFF;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 0.3px;
        background: transparent;
    }
    QLabel#appSub {
        color: rgba(255,255,255,0.88);
        font-size: 12px;
        background: transparent;
    }
    QLabel#headerDeco {
        color: rgba(255,255,255,0.16);
        font-size: 15px;
        font-weight: bold;
        background: transparent;
    }
    QLabel#usuarioNombre {
        color: #FFFFFF;
        font-size: 15px;
        font-weight: bold;
        background: transparent;
    }
    QFrame#pillRol {
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.38);
        border-radius: 13px;
    }
    QLabel#usuarioRol {
        color: #FFFFFF;
        font-size: 12px;
        font-weight: bold;
        background: transparent;
    }

    /* ================= TARJETAS ================= */
    QFrame#card {
        background: #FFFFFF;
        border: 1px solid #E4EBF5;
        border-radius: 14px;
    }
    QLabel#seccion {
        color: #173B76;
        font-size: 14px;
        font-weight: bold;
        background: transparent;
    }
    QLabel#decoResultado {
        color: rgba(23,59,118,0.20);
        font-size: 13px;
        font-weight: bold;
        background: transparent;
    }
    QLabel#pie {
        color: #8A97AC;
        font-size: 11px;
        background: transparent;
    }

    /* ================= CAMPOS ================= */
    QTextEdit {
        background: #FBFCFE;
        border: 1.5px solid #D9E4F5;
        border-radius: 10px;
        padding: 10px;
        font-size: 13px;
        color: #1F2A44;
        selection-background-color: #BFDBFE;
    }
    QTextEdit:focus {
        border: 2px solid #2563EB;
        background: #FFFFFF;
    }

    /* ================= BOTONES ================= */
    QPushButton {
        background: #2563EB;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 18px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton:hover { background: #1D4ED8; }
    QPushButton:pressed { background: #1E40AF; }

    QPushButton#btnFoto { background: #7C3AED; }
    QPushButton#btnFoto:hover { background: #6D28D9; }
    QPushButton#btnFoto:pressed { background: #5B21B6; }

    QPushButton#btnQR { background: #0284C7; }
    QPushButton#btnQR:hover { background: #0369A1; }
    QPushButton#btnQR:pressed { background: #075985; }

    QPushButton#btnCargar { background: #10B981; }
    QPushButton#btnCargar:hover { background: #059669; }
    QPushButton#btnCargar:pressed { background: #047857; }

    QPushButton#btnQuitar { background: #64748B; }
    QPushButton#btnQuitar:hover { background: #475569; }
    QPushButton#btnQuitar:pressed { background: #334155; }

    QPushButton#btnGraficar { background: #10B981; }
    QPushButton#btnGraficar:hover { background: #059669; }

    QPushButton#btnResolver {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #2563EB,
            stop:1 #1D4ED8
        );
        border: none;
        border-radius: 12px;
        font-size: 15px;
        font-weight: 800;
        color: #FFFFFF;
    }
    QPushButton#btnResolver:hover {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #1D4ED8,
            stop:1 #1E40AF
        );
    }
    QPushButton#btnResolver:pressed { background: #1E40AF; }

    QPushButton#btnVolver {
        background: #FFFFFF;
        color: #173B76;
        border: 1.5px solid #C9D6EC;
        border-radius: 10px;
        font-weight: bold;
    }
    QPushButton#btnVolver:hover {
        background: #F1F5F9;
        border-color: #2563EB;
    }
"""

# =============================================================
# OVERRIDES MODO OSCURO (mismo criterio que el Panel Principal)
# =============================================================

OVERRIDES_OSCURO = """
    Resolver { background: #0B1220; }
    QWidget#zonaCentral { background: #0B1220; }

    QFrame#header {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 #16307A,
            stop:0.55 #1D4ED8,
            stop:1 #2563EB
        );
        border-color: #2A4A8C;
    }

    QFrame#card { background: #151F38; border-color: #26334D; }
    QLabel#seccion { color: #93C5FD; }
    QLabel#decoResultado { color: rgba(147,197,253,0.30); }
    QLabel#pie { color: #7C8BA6; }

    QTextEdit {
        background: #101B33;
        border-color: #2B3A57;
        color: #E8EEF9;
        selection-background-color: #1E3A8A;
    }
    QTextEdit:focus { border-color: #3B82F6; }

    QPushButton#btnVolver {
        background: #16213C;
        color: #C9D6EC;
        border-color: #334155;
    }
    QPushButton#btnVolver:hover {
        background: #1D2B4A;
        border-color: #3B82F6;
    }

    QScrollBar::handle:vertical { background: #33415E; }
    QScrollBar::handle:vertical:hover { background: #43548A; }
"""


class Resolver(QWidget):

    def __init__(self, usuario="Usuario"):
        super().__init__()

        self.usuario = usuario

        # Lista de imágenes: cada elemento es (bytes, mime, ruta)
        self._imagenes = []          # lista de (bytes, mime, ruta)
        self.imagen_bytes = None     # compat: primera imagen (o None)
        self.imagen_mime = None
        self.imagen_ruta = None
        self._pixmap_original = None
        self._MAX_IMAGENES = 10      # límite configurable

        self._modo_oscuro = False

        self.setWindowTitle("Software Matemático IA — Resolver Problema")

        # Ventana adaptable como el Panel Principal (redimensionable)
        self.setMinimumSize(1080, 700)
        self.resize(1280, 720)
        self.centrar()

        # =====================================================
        # RAIZ: SIDEBAR IZQUIERDO + ZONA CENTRAL
        # =====================================================

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # -----------------------------------------------------
        # SIDEBAR
        # -----------------------------------------------------

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)

        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(16, 20, 16, 18)
        sb.setSpacing(6)

        logo_circle = QFrame()
        logo_circle.setObjectName("logoCircle")
        logo_circle.setFixedSize(46, 46)

        lc_layout = QVBoxLayout(logo_circle)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setAlignment(Qt.AlignCenter)

        logo_lbl = QLabel()
        pixmap_logo = QPixmap(ruta_recurso("images/logo.jpg"))
        if not pixmap_logo.isNull():
            from utils.logos import crear_logo_circular

            logo_lbl.setPixmap(
                crear_logo_circular(
                    ruta_recurso("images/logo.jpg"), 40
                )
            )
        logo_lbl.setFixedSize(42, 42)
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent;")
        lc_layout.addWidget(logo_lbl)

        fila_marca = QHBoxLayout()
        fila_marca.setSpacing(10)

        col_marca = QVBoxLayout()
        col_marca.setSpacing(1)
        nombre_app = QLabel("Software Matemático IA")
        nombre_app.setObjectName("sidebarNombreApp")
        nombre_app.setWordWrap(True)
        sub_app = QLabel("Panel de resolución")
        sub_app.setObjectName("sidebarSubApp")
        col_marca.addWidget(nombre_app)
        col_marca.addWidget(sub_app)

        fila_marca.addWidget(logo_circle)
        fila_marca.addLayout(col_marca, 1)
        sb.addLayout(fila_marca)

        linea_sb = QFrame()
        linea_sb.setObjectName("lineaSidebar")
        linea_sb.setFixedHeight(1)
        sb.addSpacing(12)
        sb.addWidget(linea_sb)
        sb.addSpacing(10)

        opciones_nav = [
            ("\U0001F3E0  Inicio", True, self.volver_menu),
            ("\u21A9  Historial", False, self._nav_historial),
            ("\U0001F9EE  Calculadora", False, self._nav_calculadora),
            ("\U0001F4D6  Guía", False, self._nav_guia),
            ("\u2699  Ajustes", False, self._nav_ajustes),
            ("\u2139  Acerca de", False, self._nav_acerca),
        ]

        self._nav_items = []
        for texto, activo, handler in opciones_nav:
            btn = QPushButton(texto)
            btn.setObjectName("navItem")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(activo)
            btn.setChecked(activo)
            btn.setFixedHeight(40)
            btn.clicked.connect(handler)
            sb.addWidget(btn)
            self._nav_items.append(btn)

        sb.addStretch()

        caption_tema = QLabel("APARIENCIA")
        caption_tema.setObjectName("lblCaptionTema")
        sb.addWidget(caption_tema)

        # Interruptor moderno de modo oscuro (píldora con perilla)
        fila_switch = QHBoxLayout()
        fila_switch.setSpacing(10)

        lbl_switch = QLabel("\U0001F312 Modo oscuro")
        lbl_switch.setStyleSheet(
            "color: #C7D6F2; font-size: 12px; background: transparent;"
        )

        self.switch_oscuro = QFrame()
        self.switch_oscuro.setObjectName("switchTema")
        self.switch_oscuro.setFixedSize(46, 26)
        self.switch_oscuro.setProperty("encendido", False)

        self.knob_oscuro = QLabel(self.switch_oscuro)
        self.knob_oscuro.setObjectName("knobTema")
        self.knob_oscuro.setGeometry(3, 3, 20, 20)

        fila_switch.addWidget(lbl_switch)
        fila_switch.addStretch()
        fila_switch.addWidget(self.switch_oscuro)
        sb.addLayout(fila_switch)

        raiz.addWidget(sidebar)

        # -----------------------------------------------------
        # ZONA CENTRAL
        # -----------------------------------------------------

        central = QWidget()
        central.setObjectName("zonaCentral")
        central.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        contenido = QVBoxLayout(central)
        contenido.setContentsMargins(24, 18, 24, 12)
        contenido.setSpacing(12)

        # =====================================================
        # HEADER CON DEGRADADO Y DECORACIÓN MATEMÁTICA
        # =====================================================

        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(92)
        aplicar_sombra(header, radio=28, desplazamiento_y=7, alfa=60)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(26, 14, 26, 14)
        header_layout.setSpacing(16)

        logo = QLabel()
        if not pixmap_logo.isNull():
            from utils.logos import crear_logo_circular

            logo.setPixmap(
                crear_logo_circular(
                    ruta_recurso("images/logo.jpg"), 52
                )
            )
        logo.setFixedSize(54, 54)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background: transparent;")

        info_app = QVBoxLayout()
        info_app.setSpacing(2)

        app_titulo = QLabel("Software Matemático IA")
        app_titulo.setObjectName("appTitulo")
        app_sub = QLabel("Resolver de problemas • Inteligencia Artificial")
        app_sub.setObjectName("appSub")

        info_app.addWidget(app_titulo)
        info_app.addWidget(app_sub)

        header_deco = QLabel(
            "\u222B dx&nbsp;&nbsp;\u03C0&nbsp;&nbsp;\u221Ax\u00B2"
            "&nbsp;&nbsp;\u0192\u2032(x)&nbsp;&nbsp;\u2211&nbsp;&nbsp;\u0394"
        )
        header_deco.setObjectName("headerDeco")

        header_layout.addWidget(logo)
        header_layout.addLayout(info_app)
        header_layout.addStretch()
        header_layout.addWidget(header_deco)
        header_layout.addStretch()

        # Nombre visible del usuario (con respaldo al nombre de usuario)
        try:

            from controllers.usuario_controller import UsuarioController

            datos = UsuarioController.buscar_usuario(self.usuario)

            nombre = datos["nombre"] if datos else self.usuario

        except Exception:

            nombre = self.usuario

        info_usuario = QVBoxLayout()
        info_usuario.setSpacing(5)

        usuario_nombre = QLabel(f"\U0001F464 {nombre}")
        usuario_nombre.setObjectName("usuarioNombre")
        usuario_nombre.setAlignment(Qt.AlignRight)

        pill = QFrame()
        pill.setObjectName("pillRol")

        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(15, 6, 15, 6)
        pill_layout.setSpacing(6)

        rol_label = QLabel("\U0001F393 Estudiante")
        rol_label.setObjectName("usuarioRol")

        pill_layout.addWidget(rol_label)

        info_usuario.addWidget(usuario_nombre)
        info_usuario.addWidget(pill, 0, Qt.AlignRight)

        header_layout.addLayout(info_usuario)

        contenido.addWidget(header)

        # =====================================================
        # SCROLL DE CONTENIDO
        # =====================================================

        scroll = QScrollArea()
        scroll.setObjectName("zonaScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cuerpo = QWidget()
        cuerpo.setObjectName("scrollContenido")

        layout = QVBoxLayout(cuerpo)
        layout.setContentsMargins(4, 14, 8, 6)
        layout.setSpacing(14)

        # =====================================================
        # TARJETA 1: PROBLEMA POR TEXTO
        # =====================================================

        card_problema = QFrame()
        card_problema.setObjectName("card")
        aplicar_sombra(card_problema, radio=22, desplazamiento_y=5, alfa=35)

        card_problema_layout = QVBoxLayout(card_problema)
        card_problema_layout.setContentsMargins(18, 14, 18, 16)
        card_problema_layout.setSpacing(10)

        lblProblema = QLabel(
            "\u270F\uFE0F  1. Escriba el problema"
        )
        lblProblema.setObjectName("seccion")

        self.txtProblema = QTextEdit()
        self.txtProblema.setPlaceholderText(
            "Ejemplo: Calcular la derivada de f(x) = x\u00B2 + 3x + 2"
        )
        self.txtProblema.setMinimumHeight(72)
        self.txtProblema.setMaximumHeight(130)

        card_problema_layout.addWidget(lblProblema)
        card_problema_layout.addWidget(self.txtProblema)

        layout.addWidget(card_problema)

        # =====================================================
        # TARJETA 2: FOTO / IMAGEN (multi-imagen)
        # =====================================================

        card_imagen = QFrame()
        card_imagen.setObjectName("card")
        aplicar_sombra(card_imagen, radio=22, desplazamiento_y=5, alfa=35)

        card_imagen_layout = QVBoxLayout(card_imagen)
        card_imagen_layout.setContentsMargins(18, 14, 18, 16)
        card_imagen_layout.setSpacing(10)

        lblImagen = QLabel(
            "\U0001F4F7  2. O adjunte fotos del problema"
        )
        lblImagen.setObjectName("seccion")

        self.btnTomarFoto = QPushButton("\U0001F4F7 Tomar Foto")
        self.btnTomarFoto.setObjectName("btnFoto")
        self.btnTomarFoto.setFixedHeight(38)

        self.btnQR = QPushButton("📱 Celular (QR)")
        self.btnQR.setObjectName("btnQR")
        self.btnQR.setFixedHeight(38)
        self.btnQR.setCursor(Qt.PointingHandCursor)

        self.btnCargarImagen = QPushButton("\U0001F5BC Cargar Imágenes")
        self.btnCargarImagen.setObjectName("btnCargar")
        self.btnCargarImagen.setFixedHeight(38)

        self.btnQuitarImagen = QPushButton("\u2716 Quitar Todas")
        self.btnQuitarImagen.setObjectName("btnQuitar")
        self.btnQuitarImagen.setFixedHeight(38)
        self.btnQuitarImagen.setVisible(False)

        self.chkAutoResolver = QCheckBox("⚡ Resolver automáticamente al recibir foto")
        self.chkAutoResolver.setChecked(True)
        self.chkAutoResolver.setCursor(Qt.PointingHandCursor)
        self.chkAutoResolver.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #1D4ED8; margin-top: 2px;"
        )

        # Contador de imágenes
        self.lblContadorImagenes = QLabel("0 / 10 imágenes")
        self.lblContadorImagenes.setStyleSheet(
            "color: #64748B; font-size: 11px; font-weight: bold; background: transparent;"
        )

        botones_imagen = QHBoxLayout()
        botones_imagen.setSpacing(10)
        botones_imagen.addWidget(self.btnTomarFoto)
        botones_imagen.addWidget(self.btnQR)
        botones_imagen.addWidget(self.btnCargarImagen)
        botones_imagen.addWidget(self.btnQuitarImagen)
        botones_imagen.addWidget(self.lblContadorImagenes)
        botones_imagen.addStretch()
        botones_imagen.addWidget(self.chkAutoResolver)

        # ---- Tira horizontal de miniaturas ----
        self.scrollMiniaturas = QScrollArea()
        self.scrollMiniaturas.setFixedHeight(150)
        self.scrollMiniaturas.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollMiniaturas.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollMiniaturas.setWidgetResizable(True)
        self.scrollMiniaturas.setStyleSheet(
            "QScrollArea { border: 1.5px dashed #C4D2E6; border-radius: 10px;"
            " background: #F8FAFC; }"
        )

        self._contenedor_miniaturas = QWidget()
        self._contenedor_miniaturas.setStyleSheet("background: transparent;")
        self._layout_miniaturas = QHBoxLayout(self._contenedor_miniaturas)
        self._layout_miniaturas.setContentsMargins(8, 8, 8, 8)
        self._layout_miniaturas.setSpacing(10)
        self._layout_miniaturas.setAlignment(Qt.AlignLeft)

        # Placeholder cuando no hay imágenes
        self.lblImagen = QLabel()
        self.lblImagen.setObjectName("preview")
        self.lblImagen.setAlignment(Qt.AlignCenter)
        self.lblImagen.setText(self.texto_zona_vacia())
        self.lblImagen.setStyleSheet("background: transparent;")
        self._layout_miniaturas.addWidget(self.lblImagen)

        self.scrollMiniaturas.setWidget(self._contenedor_miniaturas)

        card_imagen_layout.addWidget(lblImagen)
        card_imagen_layout.addLayout(botones_imagen)
        card_imagen_layout.addWidget(self.scrollMiniaturas)

        layout.addWidget(card_imagen)

        # =====================================================
        # BOTÓN RESOLVER (acción principal)
        # =====================================================

        self.btnResolver = QPushButton("\u2728 Resolver")
        self.btnResolver.setObjectName("btnResolver")
        self.btnResolver.setFixedHeight(50)
        aplicar_sombra(self.btnResolver, radio=24,
                       desplazamiento_y=5, alfa=90)

        layout.addWidget(self.btnResolver)

        # =====================================================
        # TARJETA 3: PROCEDIMIENTO Y RESULTADO
        # =====================================================

        card_resultado = QFrame()
        card_resultado.setObjectName("card")
        aplicar_sombra(card_resultado, radio=22, desplazamiento_y=5, alfa=35)

        card_resultado_layout = QVBoxLayout(card_resultado)
        card_resultado_layout.setContentsMargins(18, 14, 18, 16)
        card_resultado_layout.setSpacing(10)

        fila_resultado = QHBoxLayout()
        fila_resultado.setSpacing(10)

        lblRespuesta = QLabel(
            "\U0001F4C4  Procedimiento y Resultado"
        )
        lblRespuesta.setObjectName("seccion")

        deco_resultado = QLabel("\u221Ax \u00B7 \u0192\u2032(x) \u00B7 \u2211")
        deco_resultado.setObjectName("decoResultado")

        self.lblValidacion = QLabel("")
        self.lblValidacion.setVisible(False)
        self.lblValidacion.setAlignment(Qt.AlignCenter)

        fila_resultado.addWidget(lblRespuesta)
        fila_resultado.addStretch()
        fila_resultado.addWidget(deco_resultado)
        fila_resultado.addWidget(self.lblValidacion)

        self.txtRespuesta = QTextEdit()
        self.txtRespuesta.setReadOnly(True)
        self.txtRespuesta.setPlaceholderText(
            "Aquí se mostrará el resultado de la IA."
        )
        self.txtRespuesta.setMinimumHeight(120)
        self.txtRespuesta.setMaximumHeight(230)

        card_resultado_layout.addLayout(fila_resultado)
        card_resultado_layout.addWidget(self.txtRespuesta)

        layout.addWidget(card_resultado)

        # =====================================================
        # VOLVER AL MENÚ (inferior derecha)
        # =====================================================

        self.btnVolver = QPushButton("\u2B05 Volver al Menú")
        self.btnVolver.setObjectName("btnVolver")
        self.btnVolver.setFixedHeight(42)

        self.btnGraficar = QPushButton("\U0001F4CA Graficar")
        self.btnGraficar.setObjectName("btnGraficar")
        self.btnGraficar.setFixedHeight(42)

        botones_row = QHBoxLayout()
        botones_row.setSpacing(12)
        botones_row.addWidget(self.btnGraficar)
        botones_row.addStretch()
        botones_row.addWidget(self.btnVolver)

        layout.addLayout(botones_row)

        # =====================================================
        # PIE DE PÁGINA
        # =====================================================

        pie = QLabel(
            "Software Matemático IA  •  Versión 1.1  •  "
            "Desarrollado con Python y PyQt5"
        )
        pie.setObjectName("pie")
        pie.setAlignment(Qt.AlignCenter)

        layout.addWidget(pie)

        scroll.setWidget(cuerpo)
        contenido.addWidget(scroll, 1)

        raiz.addWidget(central, 1)

        self.setLayout(raiz)

        # =====================================================
        # TEMA OSCURO (interruptor del sidebar)
        # =====================================================

        def alternar_tema(oscuro):
            self._modo_oscuro = bool(oscuro)
            hoja = QSS_CLARO + (OVERRIDES_OSCURO if oscuro else "")
            self.setStyleSheet(hoja)

            from PyQt5.QtGui import QColor, QPalette

            paleta = self.palette()
            paleta.setColor(
                QPalette.PlaceholderText,
                QColor("#8598B4" if oscuro else "#94A3B8"),
            )
            self.setPalette(paleta)

            self.switch_oscuro.setProperty("encendido", oscuro)
            self.switch_oscuro.style().unpolish(self.switch_oscuro)
            self.switch_oscuro.style().polish(self.switch_oscuro)
            self.knob_oscuro.setGeometry(
                23 if oscuro else 3, 3, 20, 20
            )

        self._alternar_tema = alternar_tema

        def toggle_switch():
            alternar_tema(not self._modo_oscuro)

        self.switch_oscuro.mousePressEvent = lambda evento: toggle_switch()

        # =====================================================
        # CONEXIONES (sin cambios funcionales)
        # =====================================================

        self.btnResolver.clicked.connect(self.resolver)
        self.btnTomarFoto.clicked.connect(self.tomar_foto)
        self.btnQR.clicked.connect(self.conectar_celular_qr)
        self.btnCargarImagen.clicked.connect(self.cargar_imagen)
        self.btnQuitarImagen.clicked.connect(self.quitar_imagen)
        self.btnVolver.clicked.connect(self.volver_menu)

        self.btnGraficar.clicked.connect(self.abrir_graficador)

        alternar_tema(False)

        # Botón de graficar inicialmente oculto
        self.btnGraficar.setVisible(False)
        self._ultima_respuesta = ""

    # -----------------------------------------------------
    # TEXTO DE LA ZONA SIN IMAGEN
    # -----------------------------------------------------

    def texto_zona_vacia(self):
        """Mensaje decorativo mostrado cuando no hay imagen cargada."""
        return (
            "<div align='center'>"
            "<p style='font-size:28px; margin:2px;'>\u2601\uFE0F</p>"
            "<p style='margin:2px;'><b>Arrastra una imagen aqu\u00ED</b></p>"
            "<p style='color:#64748B; font-size:11px; margin:1px;'>"
            "o selecciona una opci\u00F3n para cargar</p>"
            "<p style='color:#94A3B8; font-size:10px; margin:1px;'>"
            "Formatos: JPG \u00B7 PNG \u00B7 JPEG (M\u00E1x. 10MB)</p>"
            "</div>"
        )

    # =====================================================
    # CENTRAR LA VENTANA EN LA PANTALLA
    # =====================================================

    def centrar(self):

        pantalla = QGuiApplication.primaryScreen()

        if pantalla is None:
            return

        from utils.ventanas import centrar_ventana

        centrar_ventana(self)

    # =====================================================
    # AJUSTAR LA VISTA PREVIA AL REDIMENSIONAR
    # =====================================================

    def resizeEvent(self, event):

        super().resizeEvent(event)

        if self._pixmap_original is not None:

            self.lblImagen.setPixmap(
                self._pixmap_original.scaled(
                    self.lblImagen.width(),
                    self.lblImagen.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

    # =====================================================
    # ASIGNAR IMAGEN (desde el menú "Tomar Foto")
    # =====================================================

    def set_imagen(self, datos, mime):
        """Agrega una foto capturada externamente a la lista de imágenes."""
        self.imagen_bytes = datos
        self.imagen_mime = mime
        self.imagen_ruta = f"Foto capturada {len(self._imagenes) + 1}"
        self.mostrar_vista_previa()
        if hasattr(self, "chkAutoResolver") and self.chkAutoResolver.isChecked():
            QTimer.singleShot(250, self.resolver)

    # =====================================================
    # TOMAR FOTO (PC)
    # =====================================================

    def tomar_foto(self):

        from interfaces.camara import VentanaCamara

        self.camara = VentanaCamara(self)
        self.camara.foto_capturada.connect(self.mostrar_imagen_capturada)
        self.camara.show()

    def mostrar_imagen_capturada(self, datos, mime):
        self.imagen_bytes = datos
        self.imagen_mime = mime
        self.imagen_ruta = f"Foto de la cámara {len(self._imagenes) + 1}"
        self.mostrar_vista_previa()
        if hasattr(self, "chkAutoResolver") and self.chkAutoResolver.isChecked():
            QTimer.singleShot(250, self.resolver)

    # =====================================================
    # CONECTAR CÁMARA DEL CELULAR CON CÓDIGO QR
    # =====================================================

    def conectar_celular_qr(self):
        """Abre el diálogo modal con el código QR para conectar la cámara del smartphone."""
        from interfaces.dialogo_qr import DialogoQR

        auto_activo = self.chkAutoResolver.isChecked() if hasattr(self, "chkAutoResolver") else True
        self.dialogo_qr = DialogoQR(self, auto_resolver_por_defecto=auto_activo)
        self.dialogo_qr.foto_recibida_senal.connect(self._on_foto_qr_recibida)
        self.dialogo_qr.exec_()

    def _on_foto_qr_recibida(self, imagen_bytes, mime, nota, auto_resolver):
        """Maneja la foto enviada desde el smartphone vía Wi-Fi."""
        self.imagen_bytes = imagen_bytes
        self.imagen_mime = mime
        self.imagen_ruta = f"Foto desde celular (QR) {len(self._imagenes) + 1}"

        if nota and nota.strip():
            self.txtProblema.setPlainText(nota.strip())

        self.mostrar_vista_previa()

        if auto_resolver or (hasattr(self, "chkAutoResolver") and self.chkAutoResolver.isChecked()):
            QTimer.singleShot(300, self.resolver)

    # =====================================================
    # CARGAR IMÁGENES (múltiples, acumulativas)
    # =====================================================

    def cargar_imagen(self):
        """Abre el explorador para seleccionar una o varias imágenes."""
        faltantes = self._MAX_IMAGENES - len(self._imagenes)
        if faltantes <= 0:
            QMessageBox.information(
                self,
                "Límite alcanzado",
                f"Ya tiene {self._MAX_IMAGENES} imágenes cargadas.\n"
                "Quite alguna antes de agregar más."
            )
            return

        rutas, _ = QFileDialog.getOpenFileNames(
            self,
            f"Seleccionar imágenes del problema (máx. {faltantes} más)",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)"
        )

        if not rutas:
            return

        agregadas = 0
        for ruta in rutas:
            if len(self._imagenes) >= self._MAX_IMAGENES:
                QMessageBox.information(
                    self,
                    "Límite alcanzado",
                    f"Solo se pudieron agregar {agregadas} imagen(es).\n"
                    f"El límite es {self._MAX_IMAGENES} imágenes."
                )
                break
            try:
                with open(ruta, "rb") as archivo:
                    datos = archivo.read()
                mime = self.obtener_mime(ruta)
                self._imagenes.append((datos, mime, ruta))
                agregadas += 1
            except Exception as error:
                QMessageBox.critical(
                    self, "Error",
                    f"No se pudo leer la imagen:\n{ruta}\n{error}"
                )

        if agregadas:
            self._sincronizar_compat()
            self._refrescar_miniaturas()
            if hasattr(self, "chkAutoResolver") and self.chkAutoResolver.isChecked():
                QTimer.singleShot(250, self.resolver)

    def obtener_mime(self, ruta):
        extension = os.path.splitext(ruta)[1].lower()
        mimes = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        return mimes.get(extension, "image/jpeg")

    # =====================================================
    # SINCRONIZACIÓN CON ATRIBUTOS DE COMPATIBILIDAD
    # =====================================================

    def _sincronizar_compat(self):
        """Mantiene imagen_bytes/mime/ruta apuntando a la primera imagen."""
        if self._imagenes:
            self.imagen_bytes, self.imagen_mime, self.imagen_ruta = self._imagenes[0]
        else:
            self.imagen_bytes = None
            self.imagen_mime = None
            self.imagen_ruta = None

    # =====================================================
    # REFRESCAR TIRA DE MINIATURAS
    # =====================================================

    def _refrescar_miniaturas(self):
        """Limpia y regenera las miniaturas en el scroll horizontal."""
        # Quitar todos los widgets existentes
        while self._layout_miniaturas.count():
            item = self._layout_miniaturas.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._imagenes:
            # Mostrar placeholder
            self.lblImagen = QLabel()
            self.lblImagen.setObjectName("preview")
            self.lblImagen.setAlignment(Qt.AlignCenter)
            self.lblImagen.setText(self.texto_zona_vacia())
            self.lblImagen.setStyleSheet("background: transparent;")
            self._layout_miniaturas.addWidget(self.lblImagen)
            self.btnQuitarImagen.setVisible(False)
            self.lblContadorImagenes.setText("0 / 10 imágenes")
            return

        self.btnQuitarImagen.setVisible(True)
        self.lblContadorImagenes.setText(
            f"{len(self._imagenes)} / {self._MAX_IMAGENES} imagen(es)"
        )

        for idx, (datos, mime, ruta) in enumerate(self._imagenes):
            marco = QFrame()
            marco.setFixedSize(120, 120)
            marco.setStyleSheet(
                "QFrame { background: #E8EEF8; border: 1px solid #C4D2E6;"
                " border-radius: 8px; }"
            )

            marco_layout = QVBoxLayout(marco)
            marco_layout.setContentsMargins(4, 4, 4, 4)
            marco_layout.setSpacing(2)

            # Miniatura
            miniatura = QLabel()
            miniatura.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap()
            pixmap.loadFromData(datos)
            if not pixmap.isNull():
                miniatura.setPixmap(
                    pixmap.scaled(100, 82, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            miniatura.setFixedHeight(84)
            miniatura.setToolTip(os.path.basename(ruta))

            # Botón ✕ con captura de índice
            btn_quitar = QPushButton("✕")
            btn_quitar.setFixedHeight(22)
            btn_quitar.setStyleSheet(
                "QPushButton { background: #EF4444; color: white; border: none;"
                " border-radius: 4px; font-size: 11px; font-weight: bold; padding: 0; }"
                "QPushButton:hover { background: #DC2626; }"
            )
            btn_quitar.setCursor(Qt.PointingHandCursor)
            # Captura de idx por valor
            btn_quitar.clicked.connect(lambda _, i=idx: self._quitar_imagen_individual(i))

            marco_layout.addWidget(miniatura)
            marco_layout.addWidget(btn_quitar)

            self._layout_miniaturas.addWidget(marco)

        # Actualiza referencia lblImagen al último pixmap para resizeEvent
        if self._imagenes:
            pm = QPixmap()
            pm.loadFromData(self._imagenes[0][0])
            self._pixmap_original = pm if not pm.isNull() else None

    def _quitar_imagen_individual(self, indice):
        """Elimina la imagen en la posición indicada."""
        if 0 <= indice < len(self._imagenes):
            self._imagenes.pop(indice)
        self._sincronizar_compat()
        self._refrescar_miniaturas()

    def mostrar_vista_previa(self):
        """Agrega la imagen actual (imagen_bytes/mime/ruta) a la lista y refresca."""
        if self.imagen_bytes is None:
            return
        # Evitar duplicados de la misma ruta
        ruta = self.imagen_ruta or "Foto capturada"
        if not any(r == ruta for _, _, r in self._imagenes):
            if len(self._imagenes) < self._MAX_IMAGENES:
                self._imagenes.append((self.imagen_bytes, self.imagen_mime, ruta))
        self._sincronizar_compat()
        self._refrescar_miniaturas()

    def quitar_imagen(self):
        """Quita TODAS las imágenes cargadas."""
        self._imagenes.clear()
        self._sincronizar_compat()
        self._pixmap_original = None
        self._refrescar_miniaturas()

    # =====================================================
    # RESOLVER (ASÍNCRONO CON QThread — ULTRA RÁPIDO)
    # =====================================================

    def resolver(self):

        problema = self.txtProblema.toPlainText().strip()

        if problema == "" and not self._imagenes:

            QMessageBox.warning(
                self,
                "Sin datos",
                "Debe escribir un problema o adjuntar una foto."
            )

            return

        # Deshabilitar botón temporalmente e indicar progreso
        self.btnResolver.setEnabled(False)
        self.btnResolver.setText("⚡ Resolviendo con IA ultra-rápida...")
        self.txtRespuesta.setPlainText("⚡ Procesando con IA en tiempo real... por favor espere un momento.")
        self.lblValidacion.setVisible(False)

        # Construir la lista de (bytes, mime) para el worker
        imagenes_para_worker = [(b, m) for b, m, _ in self._imagenes]

        # Ejecutar en hilo secundario para mantener la interfaz 100% fluida
        self._worker = ResolverWorker(problema, imagenes_para_worker)
        self._worker.resultado_listo.connect(
            lambda ok, resp: self._on_resolucion_terminada(ok, resp, problema)
        )
        self._worker.start()

    def _on_resolucion_terminada(self, ok, respuesta, problema):
        """Procesa la respuesta de la IA cuando el hilo finaliza."""

        self.btnResolver.setEnabled(True)
        self.btnResolver.setText("\u2728 Resolver")

        if ok:

            # Mostrar solo el resultado final (sin el procedimiento largo)
            _, resultado_mostrar = separar_procedimiento_resultado(respuesta)

            texto_mostrar = resultado_mostrar.strip()

            if texto_mostrar:
                self.txtRespuesta.setPlainText(texto_mostrar)
            else:
                self.txtRespuesta.setPlainText(respuesta)

            self._ultima_respuesta = texto_mostrar if texto_mostrar else respuesta

            # Detectar si hay una expresión matemática para graficar
            self._actualizar_boton_graficar()

            # Validación matemática por software (sympy), sin bloquear
            estado, detalle = validar_resultado(problema, respuesta)

            self.mostrar_validacion(estado, detalle)

            # Guardar la consulta en el historial separando
            # procedimiento y resultado
            problema_guardar = problema if problema != "" else "[Problema capturado en imagen]"

            procedimiento, resultado = separar_procedimiento_resultado(
                respuesta
            )

            try:
                from controllers.historial_controller import HistorialController
                HistorialController.guardar_consulta(
                    self.usuario,
                    problema_guardar,
                    respuesta,
                    procedimiento,
                    resultado
                )
            except Exception as error_bd:
                print("Aviso: No se pudo guardar en historial:", error_bd)

        else:

            self.txtRespuesta.clear()
            self.lblValidacion.setVisible(False)

            QMessageBox.critical(
                self,
                "Error al resolver",
                respuesta
            )

    # =====================================================
    # MOSTRAR INDICADOR DE VALIDACIÓN
    # =====================================================

    def mostrar_validacion(self, estado, detalle):

        if estado == "verificado":

            self.lblValidacion.setText(
                "✅ Resultado verificado por software"
            )

            self.lblValidacion.setToolTip(detalle or "")

            self.lblValidacion.setStyleSheet(
                "color:#047857;"
                "background:#ECFDF5;"
                "border:1px solid #A7F3D0;"
                "border-radius:8px;"
                "font-weight:bold;"
                "padding:4px;"
            )

        else:

            self.lblValidacion.setText(
                "⚠️ No se pudo verificar automáticamente"
            )

            self.lblValidacion.setToolTip(
                "El software no pudo verificar el resultado numérico "
                "de forma automática."
            )

            self.lblValidacion.setStyleSheet(
                "color:#B45309;"
                "background:#FFFBEB;"
                "border:1px solid #FDE68A;"
                "border-radius:8px;"
                "font-weight:bold;"
                "padding:4px;"
            )

        self.lblValidacion.setVisible(True)

    # =====================================================
    # GRAFICAR
    # =====================================================

    def _actualizar_boton_graficar(self):
        """Muestra el botón de graficar si la respuesta contiene una función matemática."""
        texto = self._ultima_respuesta.lower()

        expresion = None

        # Detectar f(x) = ... o funciones como x^2, sin(x), etc.
        if re.search(r"f\s*\(\s*x\s*\)\s*=", texto):
            match = re.search(r"f\s*\(\s*x\s*\)\s*=\s*(.+)", texto)
            if match:
                expresion = match.group(1).strip()
        elif re.search(r"y\s*=\s*[0-9x]", texto):
            match = re.search(r"y\s*=\s*(.+)", texto)
            if match:
                expresion = match.group(1).strip()
        elif "x^" in texto or "x**" in texto or "x2" in texto:
            expresion = "x^2"

        if expresion:
            self.btnGraficar.setVisible(True)
            self._expresion_graficar = expresion
        else:
            self.btnGraficar.setVisible(False)
            self._expresion_graficar = None

    def abrir_graficador(self):
        """Abre la ventana de graficado con la expresión detectada."""
        expresion = getattr(self, "_expresion_graficar", None)

        try:
            from interfaces.graficador import Graficador

            # Pasar la expresión detectada (puede ser None/"" → el usuario escribe)
            self.graficador = Graficador(expresion if expresion else "", "x", self.usuario)
            self.graficador.show()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir el graficador:\n{error}"
            )

    # =====================================================
    # VOLVER AL MENÚ
    # =====================================================

    def volver_menu(self):

        from interfaces.menu import MenuPrincipal
        from controllers.usuario_controller import UsuarioController

        nombre = self.usuario

        datos = UsuarioController.buscar_usuario(self.usuario)

        if datos:
            nombre = datos["nombre"]

        self.menu = MenuPrincipal(nombre, self.usuario)
        self.menu.show()
        self.close()

    def _nav_historial(self):
        from interfaces.historial import Historial
        w = Historial(self.usuario)
        w.show()
        self.close()

    def _nav_calculadora(self):
        from interfaces.calculadora import Calculadora
        w = Calculadora(self.usuario)
        w.show()
        self.close()

    def _nav_guia(self):
        from interfaces.informacion import Informacion
        w = Informacion(self.usuario)
        w.show()
        self.close()

    def _nav_ajustes(self):
        from utils.dialogo_ajustes_ia import mostrar_dialogo_ajustes_ia
        mostrar_dialogo_ajustes_ia(self)


    def _nav_acerca(self):
        from utils.dialogo_acerca import mostrar_acerca
        mostrar_acerca(self, "Resolver Problema Matematico", "Python + PyQt5 + SymPy + IA")


# ---------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Resolver("Santiago Peña")

    ventana.show()

    sys.exit(app.exec_())
