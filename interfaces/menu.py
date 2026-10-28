from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QMessageBox,
    QApplication,
    QSizePolicy,
    QGraphicsDropShadowEffect,
    QScrollArea,
    QSpacerItem,
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QIcon
from PyQt5.QtCore import Qt, QDate, pyqtSignal
import sys

from utils.rutas import ruta_recurso


# =====================================================
# FUNCIONES AUXILIARES (reutilizadas por otros módulos)
# =====================================================

def aplicar_sombra(widget, radio=28, desplazamiento_y=6, alfa=90):
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(radio)
    efecto.setOffset(0, desplazamiento_y)
    efecto.setColor(QColor(15, 23, 42, alfa))
    widget.setGraphicsEffect(efecto)
    return widget


# =====================================================
# COMPONENTE: Tarjeta de Acción Rápida (nuevo diseño)
# =====================================================

class ActionCard(QFrame):
    """Tarjeta horizontal para acciones rápidas con icono, título, descripción y botón."""

    clicked = pyqtSignal()

    def __init__(self, icono, titulo, descripcion, color_acento, color_fondo_icono):
        super().__init__()
        self.setObjectName("actionCard")
        self.setMinimumHeight(72)
        self.setCursor(Qt.PointingHandCursor)

        self.color_acento = color_acento

        self.setStyleSheet(f"""
            QFrame#actionCard {{
                background: #FFFFFF;
                border: 1px solid #E4E9F4;
                border-radius: 14px;
            }}
            QFrame#actionCard:hover {{
                border: 1px solid {color_acento};
                background: #F7FAFF;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        chip = QFrame()
        chip.setFixedSize(42, 42)
        chip.setStyleSheet(
            f"background: {color_fondo_icono}; border: none; border-radius: 12px;"
        )
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setAlignment(Qt.AlignCenter)
        self.lbl_icon = QLabel(icono)
        self.lbl_icon.setStyleSheet("font-size: 20px; background: transparent;")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        chip_layout.addWidget(self.lbl_icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setStyleSheet(
            "color: #101A33; font-size: 14px; font-weight: bold; background: transparent;"
        )
        self.lbl_desc = QLabel(descripcion)
        self.lbl_desc.setStyleSheet(
            "color: #68788F; font-size: 12px; background: transparent;"
        )
        info.addWidget(self.lbl_titulo)
        info.addWidget(self.lbl_desc)

        btn = QLabel("\u2192")
        btn.setFixedSize(32, 32)
        btn.setAlignment(Qt.AlignCenter)
        btn.setStyleSheet(f"""
            color: {color_acento};
            font-size: 18px;
            font-weight: bold;
            background: {color_fondo_icono};
            border-radius: 16px;
        """)

        layout.addWidget(chip)
        layout.addLayout(info, 1)
        layout.addWidget(btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def aplicar_tema(self, oscuro):
        """Adapta la tarjeta al tema claro u oscuro."""
        fondo = "#141E36" if oscuro else "#FFFFFF"
        borde = "#223052" if oscuro else "#E4E9F4"
        fondo_hover = "#182543" if oscuro else "#F7FAFF"
        texto_titulo = "#EDF1FA" if oscuro else "#101A33"
        texto_desc = "#8CA0BC" if oscuro else "#68788F"

        self.setStyleSheet(f"""
            QFrame#actionCard {{
                background: {fondo};
                border: 1px solid {borde};
                border-radius: 14px;
            }}
            QFrame#actionCard:hover {{
                border: 1px solid {self.color_acento};
                background: {fondo_hover};
            }}
        """)
        self.lbl_titulo.setStyleSheet(
            f"color: {texto_titulo}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        self.lbl_desc.setStyleSheet(
            f"color: {texto_desc}; font-size: 12px; background: transparent;"
        )


# =====================================================
# COMPONENTE: Tarjeta de Clase (mismo diseño que ActionCard)
# =====================================================

# (acento, fondo del ícono) que se alternan entre las tarjetas de clase
COLORES_CLASE = [
    ("#2563EB", "#DBEAFE"),
    ("#7C3AED", "#EDE9FE"),
    ("#0D9488", "#CCFBF1"),
    ("#EA580C", "#FFF7ED"),
    ("#D97706", "#FEF3C7"),
    ("#0891B2", "#CFFAFE"),
]


class ClaseCard(ActionCard):
    """ActionCard con una línea extra de detalles: rol, miembros y métodos de acceso."""

    def __init__(self, clase):
        acento, fondo = COLORES_CLASE[clase["id"] % len(COLORES_CLASE)]
        descripcion = (clase["descripcion"] or "Sin descripción").replace("\n", " ")
        if len(descripcion) > 70:
            descripcion = descripcion[:67] + "..."

        super().__init__("\U0001F3EB", clase["nombre"], descripcion, acento, fondo)
        self.clase = clase
        self.setToolTip(clase["descripcion"] or clase["nombre"])

        rol = "Docente" if clase["rol"] == "docente" else "Estudiante"
        miembros = clase["total_miembros"]
        metodos = [nombre for nombre, activo in (("\U0001F3A4 Voz", clase["mi_voz"]),
                                                  ("\U0001F9CD Postura", clase["mi_postura"])) if activo]
        acceso = " + ".join(metodos) if metodos else "Acceso directo"
        self.lbl_meta = QLabel(
            f"{rol} · {miembros} miembro{'s' if miembros != 1 else ''} · {acceso}"
        )
        self.lbl_meta.setStyleSheet(
            f"color: {acento}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        # El layout de textos es el segundo elemento del layout de la tarjeta
        self.layout().itemAt(1).layout().addWidget(self.lbl_meta)


# =====================================================
# COMPONENTE: Botón del sidebar
# =====================================================

class SidebarButton(QPushButton):
    """Botón de navegación del sidebar."""

    def __init__(self, icono, texto, object_name="sidebarBtn"):
        super().__init__(f"  {icono}   {texto}")
        self.setObjectName(object_name)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.7);
                border: none;
                border-radius: 10px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.08);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.12);
                color: #FFFFFF;
            }
        """)

    def set_active(self, active):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background: #2563EB;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    padding: 0 16px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: rgba(255,255,255,0.7);
                    border: none;
                    border-radius: 10px;
                    padding: 0 16px;
                    font-size: 13px;
                    font-weight: 500;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.08);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background: rgba(255,255,255,0.12);
                    color: #FFFFFF;
                }
            """)


# =====================================================
# COMPONENTE: Stat card
# =====================================================

class StatCard(QFrame):
    """Tarjeta de estadística con chip de color, etiqueta y valor."""

    def __init__(self, emoji, etiqueta, valor, color_acento, color_bg):
        super().__init__()
        self.setObjectName("stat")
        self.setFixedHeight(90)
        aplicar_sombra(self, radio=16, desplazamiento_y=3, alfa=40)

        self.setStyleSheet("""
            QFrame#stat {
                background: #FFFFFF;
                border: 1px solid #E4E9F4;
                border-radius: 14px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(12)

        chip = QFrame()
        chip.setFixedSize(40, 40)
        chip.setStyleSheet(
            f"background: {color_bg}; border: none; border-radius: 12px;"
        )
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setAlignment(Qt.AlignCenter)
        lbl_e = QLabel(emoji)
        lbl_e.setStyleSheet("font-size: 20px; background: transparent;")
        lbl_e.setAlignment(Qt.AlignCenter)
        chip_layout.addWidget(lbl_e)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_label = QLabel(etiqueta)
        self.lbl_label.setStyleSheet(
            "color: #68788F; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; background: transparent;"
        )
        self.lbl_val = QLabel(valor)
        self.lbl_val.setStyleSheet(
            "color: #101A33; font-size: 22px; font-weight: bold; background: transparent;"
        )
        info.addWidget(self.lbl_label)
        info.addWidget(self.lbl_val)

        layout.addWidget(chip)
        layout.addLayout(info, 1)
        layout.addStretch()

    def aplicar_tema(self, oscuro):
        """Adapta la tarjeta de estadistica al tema claro u oscuro."""
        fondo = "#141E36" if oscuro else "#FFFFFF"
        borde = "#223052" if oscuro else "#E4E9F4"
        texto_label = "#8CA0BC" if oscuro else "#68788F"
        texto_valor = "#EDF1FA" if oscuro else "#101A33"

        self.setStyleSheet(f"""
            QFrame#stat {{
                background: {fondo};
                border: 1px solid {borde};
                border-radius: 14px;
            }}
        """)
        self.lbl_label.setStyleSheet(
            f"color: {texto_label}; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; background: transparent;"
        )
        self.lbl_val.setStyleSheet(
            f"color: {texto_valor}; font-size: 22px; font-weight: bold; background: transparent;"
        )


# =====================================================
# PANEL PRINCIPAL
# =====================================================

class MenuPrincipal(QWidget):

    def __init__(self, nombre_usuario="Usuario", usuario="Usuario", rol="Estudiante"):
        super().__init__()

        self.nombre_usuario = nombre_usuario
        self.usuario = usuario
        self.rol = rol

        self.setWindowTitle("Software Matematico IA - Panel Principal")
        self.setWindowIcon(QIcon(ruta_recurso("images/logo.jpg")))
        self.setMinimumSize(1100, 680)
        self.resize(1340, 780)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)

        self._modo_oscuro = False

        qss_claro = """
            QWidget {
                background: #0E1A38;
                font-family: "Segoe UI";
            }

            /* ===== TOP BAR ===== */
            QFrame#topBar {
                background: #05070F;
                border: none;
            }

            QLabel#topBarTitle {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#topBarSub {
                color: rgba(255,255,255,0.5);
                font-size: 11px;
                background: transparent;
            }

            QPushButton#btnTemaMenu {
                background: rgba(255,255,255,0.08);
                color: #E6EBF7;
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 13px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#btnTemaMenu:hover {
                background: rgba(255,255,255,0.18);
                border: 1px solid rgba(255,255,255,0.30);
            }

            QPushButton#btnCerrarSesionTop {
                background: rgba(239,68,68,0.12);
                color: #FCA5A5;
                border: 1px solid rgba(239,68,68,0.35);
                border-radius: 13px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#btnCerrarSesionTop:hover {
                background: rgba(239,68,68,0.25);
                border: 1px solid rgba(239,68,68,0.55);
                color: #FECACA;
            }

            /* ===== SIDEBAR ===== */
            QFrame#sidebar {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0B1437,
                    stop:1 #111D4A
                );
                border: none;
            }

            QLabel#sidebarLogo {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#sidebarVersion {
                color: rgba(255,255,255,0.35);
                font-size: 10px;
                background: transparent;
            }

            QFrame#sidebarSeparator {
                background: rgba(255,255,255,0.08);
                border: none;
                max-height: 1px;
            }

            QLabel#sidebarSection {
                color: rgba(255,255,255,0.35);
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                background: transparent;
            }

            /* Sidebar manual card */
            QFrame#manualCard {
                background: rgba(37, 99, 235, 0.15);
                border: 1px solid rgba(37, 99, 235, 0.25);
                border-radius: 12px;
            }

            QLabel#manualTitle {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#manualDesc {
                color: rgba(255,255,255,0.5);
                font-size: 10px;
                background: transparent;
            }

            QPushButton#manualBtn {
                background: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#manualBtn:hover {
                background: #3B82F6;
            }

            /* ===== HEADER ===== */
            QFrame#header {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563EB,
                    stop:0.55 #2160E8,
                    stop:1 #1D4ED8
                );
                border: 1px solid #3B82F6;
                border-radius: 18px;
            }

            QLabel#appTitulo {
                color: #FFFFFF;
                font-size: 22px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#appSub {
                color: #FFFFFF;
                font-size: 12px;
                background: transparent;
            }

            QLabel#appTag {
                color: #FFFFFF;
                font-size: 10px;
                font-weight: bold;
                background: rgba(255,255,255,0.25);
                border-radius: 6px;
                padding: 2px 8px;
            }

            QLabel#appVersion {
                color: rgba(255,255,255,0.6);
                font-size: 10px;
                background: transparent;
            }

            QLabel#usuarioNombre {
                color: #0F1B3D;
                font-size: 15px;
                font-weight: bold;
                background: transparent;
            }

            QFrame#pillRol {
                background: #2563EB;
                border: 1px solid #60A5FA;
                border-radius: 11px;
            }

            QLabel#usuarioRol {
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }

            QFrame#userCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,0.16),
                    stop:1 rgba(255,255,255,0.07)
                );
                border: 1px solid rgba(255,255,255,0.30);
                border-radius: 14px;
            }

            QLabel#aiEngine {
                color: rgba(255,255,255,0.6);
                font-size: 10px;
                background: transparent;
            }

            QLabel#aiKey {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#aiStatus {
                color: #34D399;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }

            /* ===== SECTIONS ===== */
            QLabel#sectionTitle {
                color: #EDF1FA;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#sectionSub {
                color: #8CA0BC;
                font-size: 12px;
                background: transparent;
            }

            /* ===== WELCOME CARD ===== */
            QFrame#welcomeCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #131F49,
                    stop:1 #1D2E6E
                );
                border: 1px solid #27356E;
                border-radius: 16px;
            }

            QLabel#welcomeTitle {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#welcomeDesc {
                color: rgba(255,255,255,0.75);
                font-size: 12px;
                background: transparent;
            }

            QLabel#welcomeFormula {
                color: #93C5FD;
                font-size: 22px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#welcomeQuote {
                color: rgba(255,255,255,0.55);
                font-size: 11px;
                font-style: italic;
                background: transparent;
            }

            /* ===== LOGOUT CARD ===== */
            QPushButton#logoutCard {
                background: #FFFFFF;
                border: 1px solid #F1D8DC;
                border-radius: 14px;
                text-align: left;
                padding: 14px 18px;
            }
            QPushButton#logoutCard:hover {
                background: #FDF6F7;
                border: 1px solid #EBC3C9;
            }

            QLabel#logoutTitle {
                color: #DC2626;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#logoutDesc {
                color: #94A3B8;
                font-size: 11px;
                background: transparent;
            }

            /* ===== MIS CLASES ===== */
            QPushButton#btnNuevaClase {
                background: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnNuevaClase:hover {
                background: #3B82F6;
            }

            QPushButton#btnUnirseClase {
                background: rgba(255,255,255,0.08);
                color: #E6EBF7;
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnUnirseClase:hover {
                background: rgba(255,255,255,0.18);
            }

            QFrame#claseVacia {
                background: #FFFFFF;
                border: 1px dashed #BFD0F0;
                border-radius: 14px;
            }
            QFrame#claseVacia QLabel {
                background: transparent;
            }
            QLabel#claseVaciaIcono {
                font-size: 34px;
            }
            QLabel#claseVaciaTitulo {
                color: #101A33;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#claseVaciaDesc {
                color: #68788F;
                font-size: 12px;
            }
            QFrame#claseVacia QPushButton#btnUnirseClase {
                background: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
            }
            QFrame#claseVacia QPushButton#btnUnirseClase:hover {
                background: #DBEAFE;
            }

            /* ===== FOOTER ===== */
            QLabel#footer {
                color: #7C8BA6;
                font-size: 11px;
                background: transparent;
            }

            /* ===== SCROLLBAR ===== */
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #33415E;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 6px;
            }
        """

        self._qss_claro = qss_claro
        self.setStyleSheet(qss_claro)

        # El tema oscuro reutiliza el claro y sobreescribe solo la zona de
        # contenido (sidebar, top bar y encabezado ya son oscuros).
        self._qss_oscuro = qss_claro + """
            /* ===== OVERRIDES MODO OSCURO ===== */
            QWidget {
                background: #0C1322;
            }

            QLabel#sectionTitle {
                color: #EDF1FA;
                background: transparent;
            }

            QLabel#sectionSub {
                color: #8CA0BC;
                background: transparent;
            }

            QFrame#welcomeCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #172450,
                    stop:0.6 #1C2C64,
                    stop:1 #25377A
                );
                border: 1px solid #303F7D;
                border-radius: 16px;
            }

            QLabel#welcomeTitle {
                color: #DBEAFE;
                background: transparent;
            }

            QLabel#welcomeDesc {
                color: #9FB2D1;
                background: transparent;
            }

            QLabel#welcomeFormula {
                color: #A5B8FC;
                background: transparent;
            }

            QLabel#welcomeQuote {
                color: #8296B8;
                background: transparent;
            }

            QPushButton#logoutCard {
                background: #161F37;
                border: 1px solid #4A2530;
            }
            QPushButton#logoutCard:hover {
                background: #1E2846;
                border: 1px solid #632B38;
            }

            QLabel#logoutTitle {
                color: #F87171;
                background: transparent;
            }

            QLabel#logoutDesc {
                color: #7C8BA6;
                background: transparent;
            }

            QLabel#footer {
                color: #7C8BA6;
                background: transparent;
            }

            QFrame#claseVacia {
                background: #141E36;
                border: 1px dashed #2E3F66;
            }
            QLabel#claseVaciaTitulo {
                color: #EDF1FA;
            }
            QLabel#claseVaciaDesc {
                color: #8CA0BC;
            }
            QFrame#claseVacia QPushButton#btnUnirseClase {
                background: #182543;
                color: #93C5FD;
                border: 1px solid #223052;
            }
            QFrame#claseVacia QPushButton#btnUnirseClase:hover {
                background: #1E2D52;
            }

            QScrollBar::handle:vertical {
                background: #33415E;
            }
        """

        # =====================================================
        # LAYOUT PRINCIPAL
        # =====================================================
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # =====================================================
        # TOP BAR
        # =====================================================
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(44)

        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(20, 0, 20, 0)
        tb_layout.setSpacing(10)

        logo_icon = QLabel()
        pixmap = QPixmap(ruta_recurso("images/logo.jpg"))
        if not pixmap.isNull():
            from utils.logos import crear_logo_circular

            logo_icon.setPixmap(crear_logo_circular(
                ruta_recurso("images/logo.jpg"), 22
            ))
        logo_icon.setFixedSize(24, 24)
        logo_icon.setStyleSheet("background: transparent;")

        tb_title = QLabel("Software Matematico IA")
        tb_title.setObjectName("topBarTitle")

        tb_layout.addWidget(logo_icon)
        tb_layout.addWidget(tb_title)
        tb_layout.addStretch()

        self.btnTema = QPushButton("\U0001F312 Modo oscuro")
        self.btnTema.setObjectName("btnTemaMenu")
        self.btnTema.setCursor(Qt.PointingHandCursor)
        self.btnTema.clicked.connect(
            lambda: self._alternar_tema(not self._modo_oscuro)
        )
        tb_layout.addWidget(self.btnTema)

        tb_sub = QLabel("Panel Principal")
        tb_sub.setObjectName("topBarSub")
        tb_layout.addWidget(tb_sub)

        self.btnCerrarSesion = QPushButton("\U0001F6AA Cerrar Sesion")
        self.btnCerrarSesion.setObjectName("btnCerrarSesionTop")
        self.btnCerrarSesion.setCursor(Qt.PointingHandCursor)
        self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        tb_layout.addWidget(self.btnCerrarSesion)

        root.addWidget(top_bar)

        # =====================================================
        # BODY: SIDEBAR + CONTENT + ACTIVITY
        # =====================================================
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # =====================================================
        # SIDEBAR
        # =====================================================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)

        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 18, 16, 14)
        sb_layout.setSpacing(4)

        # Logo + nombre
        sb_logo_row = QHBoxLayout()
        sb_logo_row.setSpacing(10)
        sb_logo_icon = QLabel()
        if not pixmap.isNull():
            from utils.logos import crear_logo_circular

            sb_logo_icon.setPixmap(
                crear_logo_circular(
                    ruta_recurso("images/logo.jpg"), 56
                )
            )
        sb_logo_icon.setFixedSize(58, 58)
        sb_logo_icon.setStyleSheet("background: transparent;")
        sb_logo_text = QLabel("Software\nMatematico IA")
        sb_logo_text.setObjectName("sidebarLogo")
        sb_logo_text.setStyleSheet(
            "color: #FFFFFF; font-size: 14px; font-weight: bold; background: transparent; line-height: 1.2;"
        )
        sb_logo_row.addWidget(sb_logo_icon)
        sb_logo_row.addWidget(sb_logo_text)
        sb_logo_row.addStretch()
        sb_layout.addLayout(sb_logo_row)
        sb_layout.addSpacing(6)

        sep1 = QFrame()
        sep1.setObjectName("sidebarSeparator")
        sep1.setFixedHeight(1)
        sb_layout.addWidget(sep1)
        sb_layout.addSpacing(8)

        # Seccion menu
        lbl_menu = QLabel("MENU")
        lbl_menu.setObjectName("sidebarSection")
        sb_layout.addWidget(lbl_menu)
        sb_layout.addSpacing(4)

        # Botones de navegacion
        self.btnDashboard = SidebarButton("\U0001F3E0", "Dashboard")
        self.btnClases = SidebarButton("\U0001F3EB", "Clases")
        self.btnResolver = SidebarButton("\U0001F9EE", "Resolver Problema")
        self.btnFoto = SidebarButton("\U0001F4F7", "Tomar Foto")
        self.btnHistorial = SidebarButton("\U0001F553", "Historial")
        self.btnGraficas = SidebarButton("\U0001F4C8", "Graficas")
        self.btnCalculadora = SidebarButton("\U0001F522", "Calculadora")
        self.btnInfo = SidebarButton("\U0001F4D6", "Informacion")
        self.btnAjustes = SidebarButton("\u2699\uFE0F", "Ajustes")
        self.btnDesarrollador = SidebarButton("\U0001F4BB", "Desarrollador")

        self.sidebar_buttons = [
            self.btnDashboard,
            self.btnClases,
            self.btnResolver,
            self.btnFoto,
            self.btnHistorial,
            self.btnGraficas,
            self.btnCalculadora,
            self.btnInfo,
            self.btnAjustes,
            self.btnDesarrollador,
        ]

        self.btnDashboard.set_active(True)

        sb_layout.addWidget(self.btnDashboard)
        sb_layout.addWidget(self.btnClases)
        sb_layout.addWidget(self.btnResolver)
        sb_layout.addWidget(self.btnFoto)
        sb_layout.addWidget(self.btnHistorial)
        sb_layout.addWidget(self.btnGraficas)
        sb_layout.addWidget(self.btnCalculadora)
        sb_layout.addWidget(self.btnInfo)
        sb_layout.addWidget(self.btnAjustes)
        sb_layout.addWidget(self.btnDesarrollador)

        sb_layout.addSpacing(8)
        sep2 = QFrame()
        sep2.setObjectName("sidebarSeparator")
        sep2.setFixedHeight(1)
        sb_layout.addWidget(sep2)
        sb_layout.addSpacing(6)

        # Manual de uso card
        manual_frame = QFrame()
        manual_frame.setObjectName("manualCard")
        manual_frame.setFixedHeight(110)
        mf_layout = QVBoxLayout(manual_frame)
        mf_layout.setContentsMargins(14, 10, 14, 10)
        mf_layout.setSpacing(4)
        mf_title = QLabel("Manual de Uso")
        mf_title.setObjectName("manualTitle")
        mf_desc = QLabel("Aprende a usar todas las\nfunciones de la aplicacion\npaso a paso.")
        mf_desc.setObjectName("manualDesc")
        self.btnVerManual = QPushButton("Ver Manual")
        self.btnVerManual.setObjectName("manualBtn")
        self.btnVerManual.setFixedWidth(90)
        mf_layout.addWidget(mf_title)
        mf_layout.addWidget(mf_desc)
        mf_layout.addWidget(self.btnVerManual)
        mf_layout.addStretch()

        # El estiro ancla la tarjeta del manual al fondo del sidebar
        sb_layout.addStretch()
        sb_layout.addWidget(manual_frame)

        body.addWidget(sidebar)

        # =====================================================
        # CONTENT SCROLLABLE
        # =====================================================
        content_scroll = QScrollArea()
        self.content_scroll = content_scroll
        content_scroll.setWidgetResizable(True)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 18, 20, 18)
        content_layout.setSpacing(18)

        # =====================================================
        # HEADER (gradient card)
        # =====================================================
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(120)
        aplicar_sombra(header, radio=20, desplazamiento_y=4, alfa=50)

        header.setStyleSheet("""
            QFrame#header {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563EB,
                    stop:0.55 #2160E8,
                    stop:1 #1D4ED8
                );
                border: 1px solid #3B82F6;
                border-radius: 18px;
            }
            QLabel#appTitulo {
                color: #FFFFFF;
                font-size: 22px;
                font-weight: bold;
                background: transparent;
            }
            QLabel#appSub {
                color: #FFFFFF;
                font-size: 12px;
                background: transparent;
            }
            QLabel#appTag {
                color: #FFFFFF;
                font-size: 10px;
                font-weight: bold;
                background: rgba(255,255,255,0.25);
                border-radius: 6px;
                padding: 2px 8px;
            }
            QLabel#appVersion {
                color: rgba(255,255,255,0.75);
                font-size: 10px;
                background: transparent;
            }
        """)

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 18, 28, 18)
        h_layout.setSpacing(16)

        # Logo circular
        logo_circle = QFrame()
        logo_circle.setFixedSize(60, 60)
        logo_circle.setStyleSheet(
            "background: rgba(255,255,255,0.15); border-radius: 30px;"
        )
        lc_layout = QHBoxLayout(logo_circle)
        lc_layout.setContentsMargins(0, 0, 0, 0)
        lc_layout.setAlignment(Qt.AlignCenter)
        logo_lbl = QLabel()
        if not pixmap.isNull():
            from utils.logos import crear_logo_circular

            logo_lbl.setPixmap(
                crear_logo_circular(
                    ruta_recurso("images/logo.jpg"), 48
                )
            )
        logo_lbl.setFixedSize(50, 50)
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent;")
        lc_layout.addWidget(logo_lbl)

        app_info = QVBoxLayout()
        app_info.setSpacing(3)
        app_title = QLabel("Software Matematico IA")
        app_title.setObjectName("appTitulo")
        app_sub = QLabel("Inteligencia Artificial aplicada a las matematicas")
        app_sub.setObjectName("appSub")

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        lbl_panel = QLabel("Panel Principal")
        lbl_panel.setObjectName("appTag")
        lbl_ver = QLabel("v1.1")
        lbl_ver.setObjectName("appVersion")
        tag_row.addWidget(lbl_panel)
        tag_row.addWidget(lbl_ver)
        tag_row.addStretch()

        app_info.addWidget(app_title)
        app_info.addWidget(app_sub)
        app_info.addLayout(tag_row)

        h_layout.addWidget(logo_circle)
        h_layout.addLayout(app_info, 1)
        h_layout.addStretch()

        # User info
        user_card = QFrame()
        user_card.setObjectName("userCard")
        uc_lay = QHBoxLayout(user_card)
        uc_lay.setContentsMargins(14, 8, 16, 8)
        uc_lay.setSpacing(12)

        user_avatar = QFrame()
        user_avatar.setFixedSize(42, 42)
        user_avatar.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 #3B82F6, stop:1 #1D4ED8);"
            " border: 1px solid rgba(255,255,255,0.45); border-radius: 21px;"
        )
        ua_layout = QHBoxLayout(user_avatar)
        ua_layout.setContentsMargins(0, 0, 0, 0)
        ua_layout.setAlignment(Qt.AlignCenter)
        initials = QLabel(self.nombre_usuario[0].upper() if self.nombre_usuario else "U")
        initials.setStyleSheet(
            "color: #FFFFFF; font-size: 16px; font-weight: bold; background: transparent;"
        )
        initials.setAlignment(Qt.AlignCenter)
        ua_layout.addWidget(initials)

        user_col = QVBoxLayout()
        user_col.setSpacing(3)

        lbl_name = QLabel(self.nombre_usuario)
        lbl_name.setObjectName("usuarioNombre")
        lbl_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        pill = QFrame()
        pill.setObjectName("pillRol")
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(10, 3, 10, 3)
        pill_layout.setAlignment(Qt.AlignLeft)
        rol_lbl = QLabel(f"\U0001F393 {self.rol}")
        rol_lbl.setObjectName("usuarioRol")
        pill_layout.addWidget(rol_lbl)

        user_col.addWidget(lbl_name)
        user_col.addWidget(pill)

        uc_lay.addWidget(user_avatar)
        uc_lay.addLayout(user_col)

        h_layout.addWidget(user_card)

        content_layout.addWidget(header)

        # =====================================================
        # STATS ROW (4 cards)
        # =====================================================
        total = self.obtener_total_consultas()
        hoy = QDate.currentDate()
        dias_es = {
            0: "Lunes", 1: "Martes", 2: "Miercoles",
            3: "Jueves", 4: "Viernes", 5: "Sabado", 6: "Domingo",
        }
        dia_semana = dias_es.get(hoy.dayOfWeek(), "")
        fecha_str = hoy.toString("dd / MM / yyyy")

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)

        stat_consultas = StatCard(
            "\U0001F4DA",
            "CONSULTAS REALIZADAS",
            str(total),
            "#2563EB",
            "#DBEAFE",
        )

        stat_fecha = StatCard(
            "\U0001F4C5",
            "FECHA ACTUAL",
            fecha_str,
            "#0D9488",
            "#CCFBF1",
        )

        stat_motor = StatCard(
            "\U0001F916",
            "MOTOR DE IA",
            "Group API Key",
            "#7C3AED",
            "#EDE9FE",
        )

        stat_estado = StatCard(
            "\u2705",
            "ESTADO DEL SISTEMA",
            "Optimo",
            "#059669",
            "#D1FAE5",
        )

        stats_row.addWidget(stat_consultas)
        stats_row.addWidget(stat_fecha)
        stats_row.addWidget(stat_motor)
        stats_row.addWidget(stat_estado)

        self._tarjetas_stat = [stat_consultas, stat_fecha, stat_motor, stat_estado]

        content_layout.addLayout(stats_row)

        # =====================================================
        # ACCIONES RAPIDAS SECTION
        # =====================================================
        sec_header = QVBoxLayout()
        sec_header.setSpacing(2)
        lbl_acciones = QLabel("Acciones rapidas")
        lbl_acciones.setObjectName("sectionTitle")
        lbl_acciones_sub = QLabel("Accede a las funciones principales de la aplicacion")
        lbl_acciones_sub.setObjectName("sectionSub")
        sec_header.addWidget(lbl_acciones)
        sec_header.addWidget(lbl_acciones_sub)
        content_layout.addLayout(sec_header)

        # Grid de tarjetas de accion: 2 columnas
        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)
        cards_grid.setColumnStretch(0, 1)
        cards_grid.setColumnStretch(1, 1)

        self.card_resolver = ActionCard(
            "\U0001F4D0", "Resolver Problema",
            "Ingresa una expresion matematica y obtiene resultados paso a paso.",
            "#2563EB", "#DBEAFE",
        )
        self.card_resolver.setCursor(Qt.PointingHandCursor)

        self.card_foto = ActionCard(
            "\U0001F4F7", "Tomar Foto / Celular QR",
            "Captura problemas con la cámara de tu PC o escanea el QR con tu smartphone.",
            "#7C3AED", "#EDE9FE",
        )
        self.card_foto.setCursor(Qt.PointingHandCursor)

        self.card_historial = ActionCard(
            "\U0001F553", "Historial",
            "Consulta tus operaciones y resultados anteriores.",
            "#0D9488", "#CCFBF1",
        )
        self.card_historial.setCursor(Qt.PointingHandCursor)

        self.card_graficas = ActionCard(
            "\U0001F4C8", "Graficas",
            "Visualiza funciones matematicas en 2D de forma interactiva.",
            "#EA580C", "#FFF7ED",
        )
        self.card_graficas.setCursor(Qt.PointingHandCursor)

        self.card_info = ActionCard(
            "\U0001F4D6", "Informacion",
            "Detalles del sistema, version y estadisticas.",
            "#D97706", "#FEF3C7",
        )
        self.card_info.setCursor(Qt.PointingHandCursor)

        self.card_ajustes = ActionCard(
            "\u2699\uFE0F", "Ajustes",
            "Personaliza preferencias y configuraciones.",
            "#6366F1", "#E0E7FF",
        )
        self.card_ajustes.setCursor(Qt.PointingHandCursor)

        self.card_calculadora = ActionCard(
            "\U0001F522", "Calculadora Cientifica",
            "Realiza calculos avanzados: trigonometria, potencias, raices y mas.",
            "#0891B2", "#CFFAFE",
        )
        self.card_calculadora.setCursor(Qt.PointingHandCursor)

        cards_grid.addWidget(self.card_resolver, 0, 0)
        cards_grid.addWidget(self.card_foto, 0, 1)
        cards_grid.addWidget(self.card_historial, 1, 0)
        cards_grid.addWidget(self.card_graficas, 1, 1)
        cards_grid.addWidget(self.card_info, 2, 0)
        cards_grid.addWidget(self.card_ajustes, 2, 1)
        cards_grid.addWidget(self.card_calculadora, 3, 0)

        self._tarjetas_accion = [
            self.card_resolver,
            self.card_foto,
            self.card_historial,
            self.card_graficas,
            self.card_info,
            self.card_ajustes,
            self.card_calculadora,
        ]

        content_layout.addLayout(cards_grid)

        # =====================================================
        # MIS CLASES SECTION
        # =====================================================
        self.seccion_clases = QWidget()
        sc_layout = QVBoxLayout(self.seccion_clases)
        sc_layout.setContentsMargins(0, 6, 0, 0)
        sc_layout.setSpacing(12)

        clases_header = QHBoxLayout()
        clases_header.setSpacing(10)
        clases_titulos = QVBoxLayout()
        clases_titulos.setSpacing(2)
        lbl_clases = QLabel("Mis Clases")
        lbl_clases.setObjectName("sectionTitle")
        lbl_clases_sub = QLabel("Clases en las que participas. Cada una puede pedir tu voz o tu postura.")
        lbl_clases_sub.setObjectName("sectionSub")
        clases_titulos.addWidget(lbl_clases)
        clases_titulos.addWidget(lbl_clases_sub)

        self.btnUnirseClase = QPushButton("\U0001F511 Unirme a una clase")
        self.btnUnirseClase.setObjectName("btnUnirseClase")
        self.btnUnirseClase.setCursor(Qt.PointingHandCursor)
        self.btnNuevaClase = QPushButton("+ Nueva clase")
        self.btnNuevaClase.setObjectName("btnNuevaClase")
        self.btnNuevaClase.setCursor(Qt.PointingHandCursor)

        clases_header.addLayout(clases_titulos, 1)
        clases_header.addWidget(self.btnUnirseClase, 0, Qt.AlignBottom)
        clases_header.addWidget(self.btnNuevaClase, 0, Qt.AlignBottom)
        sc_layout.addLayout(clases_header)

        # Grid de clases (2 columnas); se reconstruye con _cargar_clases()
        self.grid_clases = QGridLayout()
        self.grid_clases.setSpacing(14)
        self.grid_clases.setColumnStretch(0, 1)
        self.grid_clases.setColumnStretch(1, 1)
        sc_layout.addLayout(self.grid_clases)

        self._tarjetas_clase = []
        content_layout.addWidget(self.seccion_clases)
        self._cargar_clases()

        # =====================================================
        # WELCOME CARD
        # =====================================================
        welcome = QFrame()
        welcome.setObjectName("welcomeCard")
        welcome.setFixedHeight(100)
        aplicar_sombra(welcome, radio=16, desplazamiento_y=3, alfa=35)

        w_layout = QHBoxLayout(welcome)
        w_layout.setContentsMargins(24, 16, 24, 16)
        w_layout.setSpacing(20)

        w_left = QVBoxLayout()
        w_left.setSpacing(4)
        w_saludo = QLabel(f"\U0001F44B \u00a1Bienvenido de vuelta, {self.nombre_usuario}!")
        w_saludo.setObjectName("welcomeTitle")
        w_desc1 = QLabel("Explora el poder de las matematicas con inteligencia artificial.")
        w_desc1.setObjectName("welcomeDesc")
        w_desc2 = QLabel("Resuelve problemas, visualiza graficas y aprende de forma interactiva.")
        w_desc2.setObjectName("welcomeDesc")
        w_left.addWidget(w_saludo)
        w_left.addWidget(w_desc1)
        w_left.addWidget(w_desc2)
        w_left.addStretch()

        w_right = QVBoxLayout()
        w_right.setAlignment(Qt.AlignCenter)
        w_formula = QLabel("f(x) = ax\u00b2 + bx + c")
        w_formula.setObjectName("welcomeFormula")
        w_formula.setAlignment(Qt.AlignCenter)
        w_quote = QLabel("\u00abLa matematica es el lenguaje del universo.\u00bb")
        w_quote.setObjectName("welcomeQuote")
        w_quote.setAlignment(Qt.AlignCenter)
        w_right.addWidget(w_formula)
        w_right.addWidget(w_quote)
        w_right.addStretch()

        w_layout.addLayout(w_left, 2)
        w_layout.addLayout(w_right, 1)

        content_layout.addWidget(welcome)

        # =====================================================
        # LOGOUT CARD
        # =====================================================
        self.card_cerrar_btn = QPushButton()
        self.card_cerrar_btn.setObjectName("logoutCard")
        self.card_cerrar_btn.setCursor(Qt.PointingHandCursor)
        self.card_cerrar_btn.setFixedHeight(56)

        cl = QHBoxLayout(self.card_cerrar_btn)
        cl.setContentsMargins(18, 0, 18, 0)
        cl.setSpacing(12)

        cl_icon = QLabel("\U0001F6AA")
        cl_icon.setStyleSheet("font-size: 20px; background: transparent;")
        cl_icon.setFixedSize(32, 32)
        cl_icon.setAlignment(Qt.AlignCenter)

        cl_info = QVBoxLayout()
        cl_info.setSpacing(1)
        cl_title = QLabel("Cerrar Sesion")
        cl_title.setObjectName("logoutTitle")
        cl_desc = QLabel("Salir de la aplicacion de forma segura.")
        cl_desc.setObjectName("logoutDesc")
        cl_info.addWidget(cl_title)
        cl_info.addWidget(cl_desc)

        cl_arrow = QLabel("\u2192")
        cl_arrow.setStyleSheet("color: #DC2626; font-size: 18px; font-weight: bold; background: transparent;")
        cl_arrow.setFixedSize(28, 28)
        cl_arrow.setAlignment(Qt.AlignCenter)

        cl.addWidget(cl_icon)
        cl.addLayout(cl_info, 1)
        cl.addWidget(cl_arrow)

        content_layout.addWidget(self.card_cerrar_btn)

        # =====================================================
        # FOOTER
        # =====================================================
        footer = QLabel("Software Matematico IA \u00b7 Version 1.1 \u00b7 Desarrollado con Python y PyQt5")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(footer)

        content_layout.addStretch()

        content_scroll.setWidget(content_widget)
        body.addWidget(content_scroll, 1)

        root.addLayout(body, 1)

        # =====================================================
        # EVENTOS
        # =====================================================
        self.card_resolver.clicked.connect(self.abrir_resolver)
        self.card_foto.clicked.connect(self.abrir_resolver_foto)
        self.card_historial.clicked.connect(self.abrir_historial)
        self.card_graficas.clicked.connect(self.abrir_graficador)
        self.card_info.clicked.connect(self.abrir_informacion)
        self.card_ajustes.clicked.connect(self.abrir_ajustes_ia)
        self.card_calculadora.clicked.connect(self.abrir_calculadora)
        self.card_cerrar_btn.clicked.connect(self.cerrar_sesion)

        self.btnNuevaClase.clicked.connect(self.nueva_clase)
        self.btnUnirseClase.clicked.connect(self.unirse_a_clase)

        self.btnDashboard.clicked.connect(lambda: self._nav_dashboard())
        self.btnClases.clicked.connect(self._nav_clases)
        self.btnResolver.clicked.connect(self.abrir_resolver)
        self.btnFoto.clicked.connect(self.abrir_resolver_foto)
        self.btnHistorial.clicked.connect(self.abrir_historial)
        self.btnGraficas.clicked.connect(self.abrir_graficador)
        self.btnCalculadora.clicked.connect(self.abrir_calculadora)
        self.btnInfo.clicked.connect(self.abrir_informacion)
        self.btnAjustes.clicked.connect(self.abrir_ajustes_ia)
        self.btnDesarrollador.clicked.connect(self._nav_desarrollador)
        self.btnVerManual.clicked.connect(self._nav_manual)

    # =====================================================
    # NAVEGACION SIDEBAR
    # =====================================================

    def _alternar_tema(self, oscuro):
        """Cambia entre tema claro y oscuro en todo el panel."""

        self._modo_oscuro = oscuro

        self.btnTema.setText(
            "\u2600\uFE0F Modo claro" if oscuro else "\U0001F312 Modo oscuro"
        )

        self.setStyleSheet(self._qss_oscuro if oscuro else self._qss_claro)

        for tarjeta in self._tarjetas_stat:
            tarjeta.aplicar_tema(oscuro)

        for tarjeta in self._tarjetas_accion + self._tarjetas_clase:
            tarjeta.aplicar_tema(oscuro)

    def _set_active_button(self, active_btn):
        for btn in self.sidebar_buttons:
            btn.set_active(False)
        if hasattr(active_btn, "set_active"):
            active_btn.set_active(True)

    def _nav_dashboard(self):
        self._set_active_button(self.btnDashboard)

    def _nav_clases(self):
        """Resalta 'Clases' y desplaza el contenido hasta la sección Mis Clases."""
        self._set_active_button(self.btnClases)
        self.content_scroll.verticalScrollBar().setValue(self.seccion_clases.y())

    def _nav_desarrollador(self):
        self._set_active_button(self.btnDesarrollador)
        self.abrir_informacion()

    def _nav_manual(self):
        # El manual no es un boton del sidebar: solo se limpia el resaltado
        for btn in self.sidebar_buttons:
            btn.set_active(False)
        self.abrir_informacion()

    # =====================================================
    # NAVEGACION PRINCIPAL (conservada)
    # =====================================================

    def obtener_total_consultas(self):
        try:
            from controllers.historial_controller import HistorialController
            return HistorialController.total_consultas(self.usuario)
        except Exception:
            return 0

    def abrir_resolver(self):
        self._set_active_button(self.btnResolver)
        from interfaces.resolver import Resolver
        self.resolver = Resolver(self.usuario)
        self.resolver.show()
        self.close()

    def abrir_resolver_foto(self):
        self._set_active_button(self.btnFoto)
        from interfaces.camara import VentanaCamara
        self.camara = VentanaCamara()
        self.camara.foto_capturada.connect(self.abrir_resolver_con_foto)
        self.camara.show()

    def abrir_resolver_con_foto(self, datos, mime):
        from interfaces.resolver import Resolver
        self.resolver = Resolver(self.usuario)
        self.resolver.set_imagen(datos, mime)
        self.resolver.show()
        self.close()

    def abrir_historial(self):
        self._set_active_button(self.btnHistorial)
        from interfaces.historial import Historial
        self.historial = Historial(self.usuario)
        self.historial.show()
        self.close()

    def abrir_informacion(self):
        self._set_active_button(self.btnInfo)
        from interfaces.informacion import Informacion
        self.informacion = Informacion(self.usuario)
        self.informacion.show()
        self.close()

    def abrir_ajustes_ia(self):
        from utils.dialogo_ajustes_ia import mostrar_dialogo_ajustes_ia
        mostrar_dialogo_ajustes_ia(self)

    # =====================================================
    # CLASES
    # =====================================================

    def _usuario_id(self):
        """Id del usuario en sesión (None si no se encuentra en la BD)."""
        if getattr(self, "_id_usuario", None) is None:
            from controllers.usuario_controller import UsuarioController
            datos = UsuarioController.buscar_usuario(self.usuario)
            self._id_usuario = datos["id"] if datos else None
        return self._id_usuario

    def _cargar_clases(self):
        """Reconstruye las tarjetas de 'Mis Clases' (o el estado vacío) desde la BD."""
        while self.grid_clases.count():
            item = self.grid_clases.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._tarjetas_clase = []

        clases = []
        try:
            from controllers.clase_controller import ClaseController
            if self._usuario_id() is not None:
                clases = ClaseController.clases_de_usuario(self._usuario_id())
        except Exception as error:
            print(f"[Clases] No se pudieron cargar las clases: {error}")

        if not clases:
            self.grid_clases.addWidget(self._crear_estado_vacio_clases(), 0, 0, 1, 2)
            return

        for indice, clase in enumerate(clases):
            tarjeta = ClaseCard(clase)
            tarjeta.aplicar_tema(self._modo_oscuro)
            tarjeta.clicked.connect(lambda c=clase: self.abrir_clase(c))
            self.grid_clases.addWidget(tarjeta, indice // 2, indice % 2)
            self._tarjetas_clase.append(tarjeta)

    def _crear_estado_vacio_clases(self):
        vacio = QFrame()
        vacio.setObjectName("claseVacia")
        lay = QVBoxLayout(vacio)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignCenter)

        icono = QLabel("\U0001F3EB")
        icono.setObjectName("claseVaciaIcono")
        icono.setAlignment(Qt.AlignCenter)
        titulo = QLabel("Todavía no tienes clases")
        titulo.setObjectName("claseVaciaTitulo")
        titulo.setAlignment(Qt.AlignCenter)
        desc = QLabel(
            "Crea tu primera clase para invitar a tus estudiantes, "
            "o únete a una con el código que te compartió tu docente."
        )
        desc.setObjectName("claseVaciaDesc")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        botones = QHBoxLayout()
        botones.setSpacing(10)
        botones.addStretch()
        btn_unirse = QPushButton("\U0001F511 Unirme a una clase")
        btn_unirse.setObjectName("btnUnirseClase")
        btn_unirse.setCursor(Qt.PointingHandCursor)
        btn_unirse.clicked.connect(self.unirse_a_clase)
        btn_crear = QPushButton("+ Crear mi primera clase")
        btn_crear.setObjectName("btnNuevaClase")
        btn_crear.setCursor(Qt.PointingHandCursor)
        btn_crear.clicked.connect(self.nueva_clase)
        botones.addWidget(btn_unirse)
        botones.addWidget(btn_crear)
        botones.addStretch()

        lay.addWidget(icono)
        lay.addWidget(titulo)
        lay.addWidget(desc)
        lay.addSpacing(8)
        lay.addLayout(botones)
        return vacio

    def _verificar_sesion_clases(self):
        if self._usuario_id() is None:
            QMessageBox.warning(
                self, "Clases",
                f"No se encontró el usuario '{self.usuario}' en la base de datos."
            )
            return False
        return True

    def nueva_clase(self):
        if not self._verificar_sesion_clases():
            return
        try:
            from interfaces.clases import DialogoNuevaClase
            dialogo = DialogoNuevaClase(self, self._usuario_id(), self._modo_oscuro)
            if dialogo.exec_():
                self._cargar_clases()
        except Exception as error:
            QMessageBox.critical(self, "Clases", f"No se pudo abrir el formulario de clase:\n{error}")

    def unirse_a_clase(self):
        if not self._verificar_sesion_clases():
            return
        try:
            from interfaces.clases import DialogoUnirseClase
            dialogo = DialogoUnirseClase(self, self._usuario_id(), self._modo_oscuro)
            if dialogo.exec_():
                self._cargar_clases()
        except Exception as error:
            QMessageBox.critical(self, "Clases", f"No se pudo unir a la clase:\n{error}")

    def abrir_clase(self, clase):
        """Pide la verificación biométrica configurada y, si se supera, abre la clase."""
        if not self._verificar_sesion_clases():
            return
        try:
            from interfaces.clases import VerificadorAccesoClase, VentanaClase

            def al_conceder(metodo):
                ventana = VentanaClase(
                    self, clase["id"], self._usuario_id(), self.usuario, metodo, self._modo_oscuro
                )
                ventana.exec_()
                # La configuración de acceso pudo cambiar: refrescar las tarjetas
                self._cargar_clases()

            self._verificador_clase = VerificadorAccesoClase(
                self, clase, self._usuario_id(), self.usuario, al_conceder
            )
            self._verificador_clase.iniciar()
        except Exception as error:
            QMessageBox.critical(self, "Clases", f"No se pudo abrir la clase:\n{error}")


    def abrir_graficador(self):
        self._set_active_button(self.btnGraficas)
        from interfaces.graficador import Graficador
        self.graficador = Graficador(usuario=self.usuario)
        self.graficador.show()
        self.close()

    def abrir_calculadora(self):
        self._set_active_button(self.btnCalculadora)
        from interfaces.calculadora import Calculadora
        self.calculadora = Calculadora(self.usuario)
        self.calculadora.show()
        self.close()

    def cerrar_sesion(self):
        respuesta = QMessageBox.question(
            self,
            "Cerrar Sesion",
            "\u00bfDesea cerrar la sesion?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if respuesta == QMessageBox.Yes:
            from interfaces.login import Login
            self.login = Login()
            self.login.show()
            self.close()


# -------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MenuPrincipal("Santiago Pena", "santiago", "Estudiante")
    ventana.show()
    sys.exit(app.exec_())
