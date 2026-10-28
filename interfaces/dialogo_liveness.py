"""
Ventana de prueba de vida con cámara: muestra el video (espejado, como un espejo), la
instrucción del momento en grande ("Parpadee ahora", "Gire a su izquierda"...) y una barra
con el tiempo restante. La lectura de la cámara y el análisis de cada cuadro se hacen en un
QThread, así la interfaz nunca se bloquea.
"""
from PyQt5.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

try:
    import cv2
except ImportError:
    cv2 = None

from interfaces.clases import ESTILO_DIALOGO_CLASES, aplicar_estilo, color_tema

ESTILO_LIVENESS = """
    QLabel#video { background: #0B0F19; border: 2px solid #2563EB; border-radius: 12px; }
    QLabel#instruccion { font-size: 22px; font-weight: bold; color: #2563EB; }
    QLabel#detalle { font-size: 12px; color: #D97706; }
    QLabel#tiempo { font-size: 16px; font-weight: bold; color: #334155; }
    QProgressBar {
        border: 1.5px solid #CBD5E1;
        border-radius: 6px;
        background: #FFFFFF;
        height: 10px;
    }
    QProgressBar::chunk { background: #2563EB; border-radius: 5px; }
"""


class HiloDesafio(QThread):
    """Lee la cámara y pasa cada cuadro al desafío hasta que se apruebe, falle o se cancele."""

    cuadro = pyqtSignal(QImage)
    resultado = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, desafio, indice_camara=0):
        super().__init__()
        self.desafio = desafio
        self.indice_camara = indice_camara
        self._detener = False

    def detener(self):
        self._detener = True

    def run(self):
        if cv2 is None:
            self.error.emit("OpenCV no está instalado.")
            return
        try:
            # Cargar los modelos antes de empezar a contar el tiempo de las acciones
            if hasattr(self.desafio, "preparar"):
                self.desafio.preparar()
            camara = cv2.VideoCapture(self.indice_camara)
            if not camara.isOpened():
                self.error.emit("No se detectó ninguna cámara.")
                return
        except Exception as error:
            self.error.emit(f"No se pudo iniciar la prueba: {error}")
            return

        try:
            while not self._detener:
                ok, frame = camara.read()
                if not ok or frame is None:
                    continue
                espejo = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                alto, ancho = espejo.shape[:2]
                self.cuadro.emit(QImage(espejo.data, ancho, alto, 3 * ancho, QImage.Format_RGB888).copy())

                # El desafío recibe el cuadro original (sin espejar)
                paso = self.desafio.procesar(frame)
                self.resultado.emit(paso)
                if paso.estado != "continuar":
                    break
        except Exception as error:
            self.error.emit(f"Error durante la prueba de vida: {error}")
        finally:
            camara.release()


class DialogoDesafioCamara(QDialog):
    """Ejecuta un desafío de cámara (DesafioRostro o DesafioPostura) y guarda el resultado final."""

    def __init__(self, parent, titulo, desafio, oscuro=False):
        super().__init__(parent)
        self.resultado = None
        self.error = None
        self.oscuro = oscuro

        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(620)
        aplicar_estilo(self, oscuro, ESTILO_DIALOGO_CLASES + ESTILO_LIVENESS)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(10)

        self.lblInstruccion = QLabel("Preparando la cámara...")
        self.lblInstruccion.setObjectName("instruccion")
        self.lblInstruccion.setAlignment(Qt.AlignCenter)
        self.lblVideo = QLabel("Cargando...")
        self.lblVideo.setObjectName("video")
        self.lblVideo.setAlignment(Qt.AlignCenter)
        self.lblVideo.setFixedSize(576, 360)
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setTextVisible(False)
        # Fase del rostro: "Prepárese... 3", "¡Ahora!", "✔ Parpadeo detectado"
        self.lblFase = QLabel("")
        self.lblFase.setAlignment(Qt.AlignCenter)
        self.lblFase.hide()
        self.lblTiempo = QLabel("")
        self.lblTiempo.setObjectName("tiempo")
        self.lblTiempo.setAlignment(Qt.AlignCenter)
        self.lblDetalle = QLabel("")
        self.lblDetalle.setObjectName("detalle")
        self.lblDetalle.setAlignment(Qt.AlignCenter)
        self.lblDetalle.setWordWrap(True)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(btn_cancelar)

        lay.addWidget(self.lblInstruccion)
        lay.addWidget(self.lblFase)
        lay.addWidget(self.lblVideo, 0, Qt.AlignCenter)
        lay.addWidget(self.barra)
        lay.addWidget(self.lblTiempo)
        lay.addWidget(self.lblDetalle)
        lay.addLayout(fila)

        self.hilo = HiloDesafio(desafio)
        self.hilo.cuadro.connect(self._mostrar_cuadro)
        self.hilo.resultado.connect(self._con_resultado)
        self.hilo.error.connect(self._con_error)

    def showEvent(self, evento):
        super().showEvent(evento)
        if not self.hilo.isRunning() and self.resultado is None:
            self.hilo.start()

    def _mostrar_cuadro(self, imagen):
        self.lblVideo.setPixmap(QPixmap.fromImage(imagen).scaled(
            self.lblVideo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # Color del texto grande de cada fase (alto contraste en claro y oscuro)
    _COLORES_FASE = {"referencia": "#334155", "lectura": "#B45309", "accion": "#2563EB", "confirmacion": "#047857"}

    def _con_resultado(self, paso):
        self.lblInstruccion.setText(paso.instruccion)
        self.lblDetalle.setText(paso.detalle)
        if paso.fase:
            # Rostro: instrucción grande, fase con color y barra del tiempo restante
            self.lblInstruccion.setStyleSheet(
                f"font-size: 28px; font-weight: bold; color: {color_tema('#0F172A', self.oscuro)};")
            self.lblFase.setText(paso.aviso)
            self.lblFase.setStyleSheet(
                f"font-size: 24px; font-weight: bold; "
                f"color: {color_tema(self._COLORES_FASE.get(paso.fase, '#2563EB'), self.oscuro)};")
            self.lblFase.show()
            self.barra.setValue(int((paso.restante if paso.restante is not None else paso.progreso) * 100))
            self.lblTiempo.setText(f"Quedan {paso.segundos} s" if paso.segundos is not None else "")
        else:
            self.barra.setValue(int(paso.progreso * 100))
        if paso.estado == "continuar":
            return
        self.resultado = paso
        if paso.estado == "aprobado":
            self.lblInstruccion.setText("✓ ¡Listo!")
            QTimer.singleShot(400, self.accept)
        else:
            self.done(QDialog.Rejected)

    def _con_error(self, mensaje):
        self.error = mensaje
        self.done(QDialog.Rejected)

    def done(self, codigo):
        # Detener la cámara antes de cerrar (también al cancelar o cerrar la ventana)
        self.hilo.detener()
        self.hilo.wait(3000)
        super().done(codigo)

    @staticmethod
    def ejecutar(parent, titulo, desafio, oscuro=False):
        """Muestra la prueba y devuelve (resultado_final | None si se canceló, mensaje_de_error | None)."""
        dlg = DialogoDesafioCamara(parent, titulo, desafio, oscuro)
        dlg.exec_()
        return dlg.resultado, dlg.error
