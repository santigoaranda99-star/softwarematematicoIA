from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QScrollArea,
    QGridLayout,
    QApplication,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

import sys

from utils.rutas import ruta_recurso


class Informacion(QWidget):

    def __init__(self, usuario="Usuario"):
        super().__init__()

        self.usuario = usuario

        self.setWindowTitle("Software Matemático IA — Información del Sistema")
        self.setMinimumSize(850, 560)
        self.resize(960, 640)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)
        from utils.tema import instalar_modo_oscuro_al_mostrar
        instalar_modo_oscuro_al_mostrar(self)

        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI";
            }

            QWidget#fondo { background: #F1F5F9; }

            /* ===== ENCABEZADO ===== */
            QFrame#encabezado {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0B1437,
                    stop:1 #111D4A
                );
            }
            QLabel#encTitulo { color: #FFFFFF; font-size: 18px; font-weight: bold; background: transparent; }
            QLabel#encSub    { color: rgba(255,255,255,0.55); font-size: 11px; background: transparent; }
            QLabel#logoChip {
                color: #FFFFFF; font-size: 20px; font-weight: bold;
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 12px;
            }
            QLabel#badgeVersion {
                color: #93C5FD; font-size: 11px; font-weight: bold;
                background: rgba(147,197,253,0.14);
                border: 1px solid rgba(147,197,253,0.30);
                border-radius: 10px;
            }

            /* ===== TARJETAS ===== */
            QFrame#tarjeta {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QLabel#seccionTitulo {
                color: #2563EB; font-size: 11px; font-weight: bold; background: transparent;
            }
            QLabel#textoInfo { color: #334155; font-size: 12px; background: transparent; }
            QLabel#datoValor { color: #0F172A; font-size: 13px; font-weight: bold; background: transparent; }
            QLabel#datoLlave { color: #64748B; font-size: 10px; background: transparent; }

            /* ===== PILLS DE TECNOLOGIA ===== */
            QLabel#pill {
                color: #1E40AF; font-size: 11px; font-weight: bold;
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 10px;
            }

            /* ===== MODULOS ===== */
            QLabel#moduloCheck {
                color: #059669; font-size: 10px; font-weight: bold;
                background: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 9px;
            }
            QLabel#moduloTexto { color: #334155; font-size: 12px; background: transparent; }

            /* ===== IMAGEN ===== */
            QFrame#marcoImagen {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QLabel#pieImagen { color: #64748B; font-size: 10px; background: transparent; }

            /* ===== BOTON VOLVER ===== */
            QPushButton#btnVolver {
                background: rgba(255,255,255,0.10);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.22);
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnVolver:hover { background: rgba(255,255,255,0.20); }

            /* ===== PIE ===== */
            QLabel#pieSistema { color: #94A3B8; font-size: 10px; background: transparent; }

            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { border: none; background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 3px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        fondo = QWidget()
        fondo.setObjectName("fondo")
        root.addWidget(fondo, 1)

        lay = QVBoxLayout(fondo)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._construir_encabezado(lay)
        self._construir_cuerpo(lay)
        self._construir_pie(lay)

    # =====================================================
    # ENCABEZADO
    # =====================================================

    def _construir_encabezado(self, lay):

        barra = QFrame()
        barra.setObjectName("encabezado")
        barra.setFixedHeight(84)

        h = QHBoxLayout(barra)
        h.setContentsMargins(28, 14, 24, 14)
        h.setSpacing(14)

        chip = QLabel("\u2211")
        chip.setObjectName("logoChip")
        chip.setFixedSize(44, 44)
        chip.setAlignment(Qt.AlignCenter)

        titulos = QVBoxLayout()
        titulos.setSpacing(1)
        t = QLabel("Información del Sistema")
        t.setObjectName("encTitulo")
        s = QLabel("Software Matemático Inteligente con IA")
        s.setObjectName("encSub")
        titulos.addWidget(t)
        titulos.addWidget(s)

        badge = QLabel("v1.1")
        badge.setObjectName("badgeVersion")
        badge.setFixedSize(46, 22)
        badge.setAlignment(Qt.AlignCenter)

        self.btnVolver = QPushButton("\u2B05  Volver al Menú")
        self.btnVolver.setObjectName("btnVolver")
        self.btnVolver.setCursor(Qt.PointingHandCursor)
        self.btnVolver.clicked.connect(self.volver_menu)

        h.addWidget(chip)
        h.addLayout(titulos)
        h.addStretch()
        h.addWidget(badge)
        h.addWidget(self.btnVolver)

        lay.addWidget(barra)

    # =====================================================
    # CUERPO
    # =====================================================

    def _construir_cuerpo(self, lay):

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(24, 18, 24, 10)
        cuerpo.setSpacing(16)

        cuerpo.addWidget(self._columna_izquierda(), 0)
        cuerpo.addWidget(self._columna_derecha(), 1)

        lay.addLayout(cuerpo, 1)

    # -----------------------------------------------------

    def _columna_izquierda(self):

        col = QVBoxLayout()
        col.setSpacing(14)

        # ---------- Imagen de presentacion ----------
        marco = QFrame()
        marco.setObjectName("marcoImagen")
        marco.setFixedWidth(320)

        mv = QVBoxLayout(marco)
        mv.setContentsMargins(14, 14, 14, 12)
        mv.setSpacing(8)

        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignCenter)

        ruta = ruta_recurso("images/presentacion.png")

        pix = QPixmap(ruta)

        if not pix.isNull():
            lbl_img.setPixmap(
                pix.scaledToWidth(272, Qt.SmoothTransformation)
            )
        else:
            lbl_img.setText("\U0001F4CA")
            lbl_img.setStyleSheet("font-size: 60px;")
            lbl_img.setFixedSize(272, 200)

        pie = QLabel("Software Matemático IA en acción")
        pie.setObjectName("pieImagen")
        pie.setAlignment(Qt.AlignCenter)

        mv.addWidget(lbl_img)
        mv.addWidget(pie)

        col.addWidget(marco)

        # ---------- Desarrollador ----------
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        tarjeta.setFixedWidth(320)

        tv = QVBoxLayout(tarjeta)
        tv.setContentsMargins(16, 14, 16, 14)
        tv.setSpacing(8)

        st = QLabel("DESARROLLADOR")
        st.setObjectName("seccionTitulo")
        tv.addWidget(st)

        nombre = QLabel("Santiago Peña Aranda")
        nombre.setObjectName("datoValor")
        tv.addWidget(nombre)

        linea = QFrame()
        linea.setFixedHeight(1)
        linea.setStyleSheet("background: #EEF2F7; border: none;")
        tv.addWidget(linea)

        for llave, valor in (
            ("PROGRAMA", "Análisis y Desarrollo de Software (ADSO)"),
            ("INSTITUCIÓN", "SENA"),
        ):
            k = QLabel(llave)
            k.setObjectName("datoLlave")
            v = QLabel(valor)
            v.setObjectName("textoInfo")
            v.setWordWrap(True)
            tv.addWidget(k)
            tv.addWidget(v)

        col.addWidget(tarjeta)
        col.addStretch()

        widget = QWidget()
        widget.setLayout(col)
        return widget

    # -----------------------------------------------------

    def _columna_derecha(self):

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        contenido = QWidget()
        contenido.setStyleSheet("background: transparent;")

        col = QVBoxLayout(contenido)
        col.setContentsMargins(0, 0, 8, 0)
        col.setSpacing(14)

        # ---------- Descripcion ----------
        col.addWidget(self._tarjeta_descripcion())

        # ---------- Tecnologias ----------
        col.addWidget(self._tarjeta_tecnologias())

        # ---------- Modulos ----------
        col.addWidget(self._tarjeta_modulos())

        col.addStretch()

        scroll.setWidget(contenido)
        return scroll

    # -----------------------------------------------------

    def _tarjeta_descripcion(self):

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")

        v = QVBoxLayout(tarjeta)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)

        st = QLabel("¿QUÉ ES?")
        st.setObjectName("seccionTitulo")
        v.addWidget(st)

        texto = QLabel(
            "Software desarrollado para resolver problemas matemáticos "
            "utilizando Inteligencia Artificial. Permite registrar usuarios "
            "e iniciar sesión, resolver ejercicios escribiendo el problema o "
            "tomándole una foto con la cámara, almacenar el historial de "
            "consultas y mostrar el procedimiento completo de cada solución."
        )
        texto.setObjectName("textoInfo")
        texto.setWordWrap(True)
        v.addWidget(texto)

        return tarjeta

    # -----------------------------------------------------

    def _tarjeta_tecnologias(self):

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")

        v = QVBoxLayout(tarjeta)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(10)

        st = QLabel("TECNOLOGÍAS UTILIZADAS")
        st.setObjectName("seccionTitulo")
        v.addWidget(st)

        grid = QGridLayout()
        grid.setSpacing(8)

        tecnologias = (
            ("\U0001F40D", "Python"),
            ("\U0001F5A5", "PyQt5"),
            ("\U0001F5C4", "SQLite"),
            ("\U0001F916", "API de IA (Group API Key)"),
            ("\U0001F4F7", "OpenCV (cámara)"),
        )

        for i, (icono, nombre) in enumerate(tecnologias):
            pill = QLabel(f"{icono}  {nombre}")
            pill.setObjectName("pill")
            pill.setAlignment(Qt.AlignCenter)
            grid.addWidget(pill, i // 3, i % 3)

        v.addLayout(grid)

        return tarjeta

    # -----------------------------------------------------

    def _tarjeta_modulos(self):

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")

        v = QVBoxLayout(tarjeta)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(10)

        st = QLabel("MÓDULOS DEL SISTEMA")
        st.setObjectName("seccionTitulo")
        v.addWidget(st)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        modulos = (
            "Splash",
            "Login",
            "Registro",
            "Panel Principal (Dashboard)",
            "Resolver Problemas",
            "Resolver con Foto",
            "Historial",
            "Información",
        )

        for i, nombre in enumerate(modulos):

            fila = QHBoxLayout()
            fila.setSpacing(8)

            check = QLabel("\u2713")
            check.setObjectName("moduloCheck")
            check.setFixedSize(18, 18)
            check.setAlignment(Qt.AlignCenter)

            lbl = QLabel(nombre)
            lbl.setObjectName("moduloTexto")

            fila.addWidget(check)
            fila.addWidget(lbl, 1)
            fila.addStretch()

            contenedor = QWidget()
            contenedor.setLayout(fila)
            contenedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            grid.addWidget(contenedor, i // 2, i % 2)

        v.addLayout(grid)

        return tarjeta

    # =====================================================
    # PIE
    # =====================================================

    def _construir_pie(self, lay):

        pie_row = QHBoxLayout()
        pie_row.setContentsMargins(24, 4, 24, 10)

        pie = QLabel("© 2026 Software Matemático IA \u2022 Versión 1.1 \u2022 Proyecto educativo SENA")
        pie.setObjectName("pieSistema")

        pie_row.addWidget(pie)
        pie_row.addStretch()

        lay.addLayout(pie_row)

    # ------------------------------------------------

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


# ------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Informacion()

    ventana.show()

    sys.exit(app.exec_())
