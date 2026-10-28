from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon
import sys

from interfaces.login import Login
from utils.rutas import ruta_recurso


class Splash(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Software Matemático IA")
        self.setWindowIcon(QIcon(ruta_recurso("images/logo.jpg")))
        self.setMinimumSize(600, 400)
        self.resize(700, 450)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)

        self.setStyleSheet("""
            QWidget{
                background:qlineargradient(
                    x1:0,y1:0,
                    x2:1,y2:1,
                    stop:0 #0F172A,
                    stop:1 #2563EB
                );
            }

            QLabel{
                color:white;
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # ----------------------------------
        # LOGO
        # ----------------------------------

        self.logo = QLabel()

        from utils.logos import crear_logo_circular

        pixmap = crear_logo_circular(ruta_recurso("images/logo.jpg"), 150)

        if not pixmap.isNull():
            self.logo.setPixmap(pixmap)

        self.logo.setAlignment(Qt.AlignCenter)

        # ----------------------------------
        # TÍTULO
        # ----------------------------------

        self.titulo = QLabel("Software Matemático Inteligente")
        self.titulo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.titulo.setAlignment(Qt.AlignCenter)

        # ----------------------------------
        # SUBTÍTULO
        # ----------------------------------

        self.subtitulo = QLabel("Potenciado con Inteligencia Artificial")
        self.subtitulo.setFont(QFont("Segoe UI", 12))
        self.subtitulo.setAlignment(Qt.AlignCenter)

        # ----------------------------------
        # VERSIÓN
        # ----------------------------------

        self.version = QLabel("Versión 1.0")
        self.version.setFont(QFont("Segoe UI", 10))
        self.version.setAlignment(Qt.AlignCenter)

        # ----------------------------------
        # MENSAJE DE CARGA
        # ----------------------------------

        self.cargando = QLabel("Cargando sistema...")
        self.cargando.setFont(QFont("Segoe UI", 11))
        self.cargando.setAlignment(Qt.AlignCenter)

        # Agregar widgets al layout

        layout.addStretch()

        layout.addWidget(self.logo)
        layout.addSpacing(15)

        layout.addWidget(self.titulo)
        layout.addWidget(self.subtitulo)

        layout.addSpacing(30)

        layout.addWidget(self.version)

        layout.addStretch()

        layout.addWidget(self.cargando)

        self.setLayout(layout)

        # Mostrar el Splash durante 3 segundos
        QTimer.singleShot(3000, self.abrir_login)

    # ----------------------------------
    # Abrir Login
    # ----------------------------------

    def abrir_login(self):

        self.login = Login()
        self.login.show()
        self.close()


# --------------------------------------
# PRUEBA DEL SPLASH
# --------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Splash()
    ventana.show()

    sys.exit(app.exec_())