import time

from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
)
from PyQt5.QtCore import Qt, QTimer


class DialogoVoz(QDialog):
    """
    Diálogo que pide al usuario decir su palabra clave y graba el micrófono
    sin bloquear la interfaz. El audio queda en self.audio al aceptar.
    """

    INSTRUCCION = "Pulse 'Grabar' y diga en voz alta, cerca del micrófono:"

    def __init__(self, parent, palabra, segundos=2.0, titulo="🎤 Verificación por Voz", instruccion=None,
                 texto_al_grabar=None):
        super().__init__(parent)

        self.setWindowTitle(titulo)
        self.setMinimumWidth(380)
        self.setModal(True)

        self.segundos = segundos
        self.audio = None
        self._buffer = None
        self._inicio = 0.0
        self._grabando = False
        # Desafío (p. ej. números al azar) que solo se muestra al pulsar "Grabar"
        self._texto_al_grabar = texto_al_grabar

        self.setStyleSheet("""
            QDialog { background: #F8FAFC; font-family: "Segoe UI"; }
            QLabel { color: #0F172A; font-size: 13px; }
            QLabel#icono { font-size: 46px; }
            QLabel#palabra { font-size: 22px; font-weight: bold; color: #4F46E5; }
            QLabel#estado { color: #475569; font-size: 12px; }
            QProgressBar {
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                background: #FFFFFF;
                height: 14px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk { background: #4F46E5; border-radius: 6px; }
            QPushButton {
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: bold;
                color: white;
            }
            QPushButton#btnGrabar { background: #4F46E5; }
            QPushButton#btnGrabar:hover { background: #4338CA; }
            QPushButton#btnGrabar:disabled { background: #A5B4FC; }
            QPushButton#btnCancelar { background: #EF4444; }
            QPushButton#btnCancelar:hover { background: #DC2626; }
            QPushButton#btnCancelar:disabled { background: #FCA5A5; }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(10)

        icono = QLabel("🎤")
        icono.setObjectName("icono")
        icono.setAlignment(Qt.AlignCenter)

        instruccion = QLabel(instruccion or self.INSTRUCCION)
        instruccion.setWordWrap(True)
        instruccion.setAlignment(Qt.AlignCenter)

        lbl_palabra = QLabel(f"«{palabra}»")
        lbl_palabra.setObjectName("palabra")
        lbl_palabra.setAlignment(Qt.AlignCenter)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        self.barra.setFormat("")

        self.lblEstado = QLabel(f"Tendrá {segundos:g} segundos para hablar.")
        self.lblEstado.setObjectName("estado")
        self.lblEstado.setAlignment(Qt.AlignCenter)
        self.lblEstado.setWordWrap(True)

        self.btnGrabar = QPushButton("🎙️ Grabar")
        self.btnGrabar.setObjectName("btnGrabar")
        self.btnGrabar.setCursor(Qt.PointingHandCursor)
        self.btnCancelar = QPushButton("✖ Cancelar")
        self.btnCancelar.setObjectName("btnCancelar")
        self.btnCancelar.setCursor(Qt.PointingHandCursor)

        botones = QHBoxLayout()
        botones.setSpacing(10)
        botones.addWidget(self.btnGrabar, 1)
        botones.addWidget(self.btnCancelar, 1)

        lay.addWidget(icono)
        lay.addWidget(instruccion)
        # Sin palabra (p. ej. palabra de ingreso secreta) no se muestra nada en pantalla
        if palabra or texto_al_grabar:
            lay.addWidget(lbl_palabra)
        if not palabra:
            lbl_palabra.hide()
        self.lblPalabra = lbl_palabra
        lay.addSpacing(4)
        lay.addWidget(self.barra)
        lay.addWidget(self.lblEstado)
        lay.addSpacing(6)
        lay.addLayout(botones)

        from utils.tema import instalar_modo_oscuro_al_mostrar
        instalar_modo_oscuro_al_mostrar(self)

        self.btnGrabar.clicked.connect(self.grabar)
        self.btnCancelar.clicked.connect(self.reject)

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._actualizar_progreso)

    def grabar(self):
        from utils.reconocimiento_voz import ReconocedorVoz

        try:
            self._buffer = ReconocedorVoz.iniciar_grabacion(self.segundos)
        except Exception as err:
            self.lblEstado.setText(f"⚠️ No se pudo acceder al micrófono: {err}")
            return

        self._grabando = True
        self._inicio = time.monotonic()
        self.btnGrabar.setEnabled(False)
        self.btnCancelar.setEnabled(False)
        self.lblEstado.setText("🔴 Grabando... hable ahora.")
        if self._texto_al_grabar:
            self.lblPalabra.setText(self._texto_al_grabar)
            self.lblPalabra.show()
        self._timer.start()

    def _actualizar_progreso(self):
        from utils.reconocimiento_voz import ReconocedorVoz

        progreso = (time.monotonic() - self._inicio) / self.segundos
        self.barra.setValue(min(100, int(progreso * 100)))
        if progreso < 1.0:
            return

        self._timer.stop()
        self.audio = ReconocedorVoz.terminar_grabacion(self._buffer)
        self._grabando = False
        self.accept()

    def reject(self):
        # No cerrar a mitad de una grabación: el buffer de sounddevice sigue llenándose
        if self._grabando:
            return
        super().reject()

    @staticmethod
    def obtener_audio(parent, palabra, segundos=2.0, titulo="🎤 Verificación por Voz", instruccion=None,
                      texto_al_grabar=None):
        """Muestra el diálogo y devuelve el audio grabado (np.ndarray) o None si se canceló."""
        dlg = DialogoVoz(parent, palabra, segundos, titulo, instruccion, texto_al_grabar)
        if dlg.exec_() != QDialog.Accepted:
            return None
        return dlg.audio
