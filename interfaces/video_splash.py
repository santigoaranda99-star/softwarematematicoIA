from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QFont, QIcon
import sys

from interfaces.login import Login
from utils.rutas import ruta_recurso


class VideoSplash(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Software Matemático IA")
        self.setWindowIcon(QIcon(ruta_recurso("images/logo.jpg")))
        self.setMinimumSize(720, 480)
        self.resize(900, 560)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)

        self.setStyleSheet("""
            QWidget {
                background: #0F172A;
            }
            QLabel {
                color: white;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        layout.addWidget(self.video_widget)

        # Mensaje de respaldo si el video falla
        self.lbl_fallback = QLabel("Cargando sistema...")
        self.lbl_fallback.setFont(QFont("Segoe UI", 14))
        self.lbl_fallback.setAlignment(Qt.AlignCenter)
        self.lbl_fallback.setStyleSheet("color: #94A3B8; padding: 20px;")
        self.lbl_fallback.hide()
        layout.addWidget(self.lbl_fallback)

        self.setLayout(layout)

        # Media player
        self.player = QMediaPlayer(self, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)

        # Conectar señales
        self.player.stateChanged.connect(self._on_state_changed)
        self.player.error.connect(self._on_error)

        # Cargar y reproducir video
        video_path = ruta_recurso("images/bienvenida.mp4")
        media = QMediaContent(QUrl.fromLocalFile(video_path))
        self.player.setMedia(media)
        self.player.play()

        # Timeout de seguridad (máx 15 segundos). Es un QTimer propio para poder cancelarlo:
        # un singleShot suelto seguía disparándose tras abrir el login y abría un segundo login.
        self._login_abierto = False
        self._timer_seguridad = QTimer(self)
        self._timer_seguridad.setSingleShot(True)
        self._timer_seguridad.timeout.connect(self._forzar_login)
        self._timer_seguridad.start(15000)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.StoppedState:
            # Video terminó o se detuvo
            self.abrir_login()

    def _on_error(self):
        # Si falla el video, mostrar mensaje y continuar
        self.video_widget.hide()
        self.lbl_fallback.show()
        QTimer.singleShot(2000, self.abrir_login)

    def _forzar_login(self):
        # Por si el video es muy largo o se queda colgado
        self.player.stop()
        self.abrir_login()

    def abrir_login(self):
        # Fin del video, error y timeout pueden llamar aquí: el login se abre una sola vez
        if self._login_abierto:
            return
        self._login_abierto = True
        self._timer_seguridad.stop()
        self.player.stateChanged.disconnect(self._on_state_changed)
        self.player.stop()

        self.login = Login()
        self.login.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VideoSplash()
    ventana.show()
    sys.exit(app.exec_())