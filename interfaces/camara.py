from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QGuiApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

import sys

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from services.clasificador_imagen import ClasificadorImagen
except ImportError:
    ClasificadorImagen = None


class VentanaCamara(QWidget):

    foto_capturada = pyqtSignal(bytes, str)
    # Modo postura: emite la ráfaga de frames BGR capturados
    rafaga_pose_capturada = pyqtSignal(list)

    SEGUNDOS_CUENTA_POSE = 3
    FRAMES_RAFAGA_POSE = 10

    def __init__(self, parent=None):
        # Es fundamental Qt.Window para que nunca se incruste como widget hijo
        # dentro del formulario padre ni se monte sobre los campos de texto
        super().__init__(parent, Qt.Window)

        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinMaxButtonsHint
        )

        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.cap = None
        self.foto_bytes = None
        self.mime = "image/jpeg"
        self.camara_disponible = False
        self.rotacion = 0
        self._captura_forzada = False

        # Configuración de modo facial seguro y tracking biométrico
        self.modo_facial = False
        self._muestras_rafaga = []
        self._capturando_rafaga = False
        self._frame_count = 0
        self._ultimo_bbox = None
        self._ultimo_score = 0.0
        self._timer_rafaga = None

        # Modo postura (cuenta regresiva + ráfaga para el modelo de pose)
        self.modo_pose = False
        self._cuenta_pose = 0

        self.setWindowTitle("📷 Tomar Foto")
        self.setMinimumSize(660, 540)
        self.resize(700, 580)
        self.centrar()

        self.setStyleSheet("""
            QWidget {
                background: #F1F5F9;
                font-family: "Segoe UI";
            }

            QLabel {
                color: #0F172A;
                font-size: 13px;
            }

            QLabel#titulo {
                font-size: 18px;
                font-weight: bold;
            }

            QLabel#preview {
                background: #0F172A;
                border: 2px solid #2563EB;
                border-radius: 10px;
            }

            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background: #1D4ED8;
            }

            QPushButton#btnCancelar {
                background: #EF4444;
            }

            QPushButton#btnCancelar:hover {
                background: #DC2626;
            }

            QPushButton#btnRotar {
                background: #0D9488;
            }

            QPushButton#btnRotar:hover {
                background: #0F766E;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(12)

        self.titulo = QLabel("Acerque la cámara al problema")
        self.titulo.setObjectName("titulo")
        self.titulo.setAlignment(Qt.AlignCenter)

        # Contenedor con tamaño proporcional razonable (proporción 4:3) centrado
        self.lblPreview = QLabel("Cargando cámara...")
        self.lblPreview.setObjectName("preview")
        self.lblPreview.setAlignment(Qt.AlignCenter)
        self.lblPreview.setFixedSize(560, 360)

        self.lblEstado = QLabel("")
        self.lblEstado.setAlignment(Qt.AlignCenter)

        self.btnCapturar = QPushButton("📸 Capturar Foto")
        self.btnRotar = QPushButton("🔄 Rotar 90°")
        self.btnRotar.setObjectName("btnRotar")
        self.btnCancelar = QPushButton("✖ Cancelar")
        self.btnCancelar.setObjectName("btnCancelar")

        botones = QHBoxLayout()
        botones.addWidget(self.btnCapturar)
        botones.addWidget(self.btnRotar)
        botones.addWidget(self.btnCancelar)

        layout.addWidget(self.titulo)
        layout.addWidget(self.lblPreview, 0, Qt.AlignCenter)
        layout.addWidget(self.lblEstado)
        layout.addLayout(botones)

        self.setLayout(layout)

        from utils.tema import instalar_modo_oscuro_al_mostrar
        instalar_modo_oscuro_al_mostrar(self)

        self.btnCapturar.clicked.connect(self.capturar)
        self.btnRotar.clicked.connect(self.rotar)
        self.btnCancelar.clicked.connect(self.cancelar)

        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_frame)

        self.iniciar_camara()

    # =====================================================
    # CENTRAR LA VENTANA EN LA PANTALLA
    # =====================================================

    def centrar(self):

        pantalla = QGuiApplication.primaryScreen()

        if pantalla is None:
            return

        geometria = pantalla.availableGeometry()

        x = geometria.x() + (geometria.width() - self.width()) // 2
        y = geometria.y() + (geometria.height() - self.height()) // 2

        self.move(x, y)

    def iniciar_camara(self):

        if cv2 is None:
            self.mostrar_sin_camara(
                "No se encontró el módulo OpenCV (cv2).\n"
                "Instale con: pip install opencv-python"
            )
            return

        try:
            self.cap = cv2.VideoCapture(0)

            if not self.cap.isOpened():
                self.mostrar_sin_camara(
                    "No se detectó ninguna cámara.\n"
                    "Puede usar 'Cargar imagen' en la ventana anterior."
                )
                return

            self.camara_disponible = True
            self.lblPreview.setText("")
            self.timer.start(30)

        except Exception as error:
            self.mostrar_sin_camara(f"Error al abrir la cámara:\n{error}")

    def mostrar_sin_camara(self, mensaje):

        self.camara_disponible = False
        self.lblPreview.setText(mensaje)
        self.lblEstado.setText("Cámara no disponible")
        self.btnCapturar.setEnabled(False)

    def actualizar_frame(self):

        if not self.camara_disponible or self.cap is None:
            return

        ret, frame = self.cap.read()

        if not ret or frame is None:
            return

        frame = self.rotar_frame(frame)

        # Tracking biométrico en tiempo real (HUD) si está en modo facial
        if self.modo_facial and ClasificadorImagen is not None:
            self._frame_count += 1
            if self._frame_count % 3 == 0:
                hay, _, sc, bbox, _ = ClasificadorImagen.detectar_rostro(frame)
                if hay:
                    self._ultimo_bbox = bbox
                    self._ultimo_score = sc
                else:
                    self._ultimo_bbox = None
                    self._ultimo_score = 0.0

            if self._ultimo_bbox is not None:
                frame = ClasificadorImagen.dibujar_hud_biometrico(
                    frame.copy(),
                    self._ultimo_bbox,
                    self._ultimo_score
                )

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        alto, ancho, canal = frame_rgb.shape
        bytes_por_linea = canal * ancho

        imagen = QImage(
            frame_rgb.data,
            ancho,
            alto,
            bytes_por_linea,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(imagen)

        target_w = self.lblPreview.width()
        target_h = self.lblPreview.height()

        if target_w > 50 and target_h > 50:
            pixmap_escalado = pixmap.scaled(
                target_w,
                target_h,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.lblPreview.setPixmap(pixmap_escalado)
        else:
            self.lblPreview.setPixmap(pixmap)

    def rotar_frame(self, frame):

        rot = self.rotacion % 360

        if rot == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        if rot == 180:
            return cv2.flip(frame, -1)

        if rot == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        return frame

    def rotar(self):

        self.rotacion = (self.rotacion + 90) % 360
        self._captura_forzada = False

        if self.camara_disponible:
            self.actualizar_frame()

        self.lblEstado.setText(f"Rotación: {self.rotacion}°")

    def capturar(self):

        if not self.camara_disponible or self.cap is None:
            return

        if self.modo_pose:
            if not self._capturando_rafaga:
                self._iniciar_cuenta_pose()
            return

        # Si está activado el modo facial seguro, ejecutar ráfaga multi-muestra
        if self.modo_facial and not self._capturando_rafaga:
            self._iniciar_rafaga_facial()
            return

        self._capturar_simple()

    def _iniciar_rafaga_facial(self):
        """Inicia una secuencia de 5 capturas en ráfaga para verificar prueba de vida y calidad."""
        self._capturando_rafaga = True
        self._muestras_rafaga = []
        self.btnCapturar.setEnabled(False)
        self.lblEstado.setText("🛡️ Escaneando biometría... [○○○○○] 0/5")

        self._timer_rafaga = QTimer(self)
        self._timer_rafaga.setInterval(160)  # Muestreo cada 160ms (~0.8 seg total)
        self._timer_rafaga.timeout.connect(self._recolectar_muestra_facial)
        self._timer_rafaga.start()

    def _recolectar_muestra_facial(self):
        if not self.camara_disponible or self.cap is None:
            self._finalizar_rafaga()
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        frame = self.rotar_frame(frame)
        self._muestras_rafaga.append(frame)

        num = len(self._muestras_rafaga)
        barra = ("●" * num).ljust(5, "○")
        self.lblEstado.setText(f"🛡️ Escaneando biometría... [{barra}] Muestra {num}/5")

        if num >= 5:
            self._timer_rafaga.stop()
            self._timer_rafaga = None
            self._procesar_rafaga_completada()

    def _procesar_rafaga_completada(self):
        self._capturando_rafaga = False
        self.btnCapturar.setEnabled(True)

        if not self._muestras_rafaga:
            self.lblEstado.setText("No se pudieron obtener muestras.")
            return

        if ClasificadorImagen is None:
            self._emitir_frame(self._muestras_rafaga[-1])
            return

        exito, mejor_frame, etiqueta, confianza, motivo = ClasificadorImagen.analizar_rafaga_facial(
            self._muestras_rafaga
        )

        if not exito:
            self.lblEstado.setText(f"⚠️ {motivo}")
            return

        self.lblEstado.setText(f"✓ Biometría verificada ({confianza * 100:.0f}%).")
        self._emitir_frame(mejor_frame if mejor_frame is not None else self._muestras_rafaga[-1])

    def _iniciar_cuenta_pose(self):
        """Cuenta regresiva para que el usuario se aleje y adopte su postura antes de la ráfaga."""
        self._capturando_rafaga = True
        self._muestras_rafaga = []
        self._cuenta_pose = self.SEGUNDOS_CUENTA_POSE
        self.btnCapturar.setEnabled(False)
        self.lblEstado.setText(f"🧍 Adopte su postura... {self._cuenta_pose}")

        self._timer_rafaga = QTimer(self)
        self._timer_rafaga.setInterval(1000)
        self._timer_rafaga.timeout.connect(self._tick_cuenta_pose)
        self._timer_rafaga.start()

    def _tick_cuenta_pose(self):
        if not self.camara_disponible or self.cap is None:
            self._finalizar_rafaga()
            return

        self._cuenta_pose -= 1
        if self._cuenta_pose > 0:
            self.lblEstado.setText(f"🧍 Adopte su postura... {self._cuenta_pose}")
            return

        self._timer_rafaga.stop()
        self._timer_rafaga = QTimer(self)
        self._timer_rafaga.setInterval(120)
        self._timer_rafaga.timeout.connect(self._recolectar_muestra_pose)
        self._timer_rafaga.start()

    def _recolectar_muestra_pose(self):
        if not self.camara_disponible or self.cap is None:
            self._finalizar_rafaga()
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self._muestras_rafaga.append(self.rotar_frame(frame))
        num = len(self._muestras_rafaga)
        self.lblEstado.setText(f"📸 Capturando postura... {num}/{self.FRAMES_RAFAGA_POSE}")

        if num >= self.FRAMES_RAFAGA_POSE:
            self._finalizar_rafaga()
            frames = self._muestras_rafaga
            self._muestras_rafaga = []
            self.cerrar_camara()
            self.close()
            self.rafaga_pose_capturada.emit(frames)

    def _capturar_simple(self):
        """Captura única de fotograma (para imágenes generales o problemas matemáticos)."""
        ret, frame = self.cap.read()

        if not ret or frame is None:
            self.lblEstado.setText("No se pudo capturar. Intente de nuevo.")
            return

        frame = self.rotar_frame(frame)

        # Clasificación de calidad con modelo Teachable Machine
        if ClasificadorImagen is not None:
            try:
                clase, confianza = ClasificadorImagen.predecir(frame)
                if clase:
                    clase_lower = clase.lower()
                    if not self._captura_forzada and confianza > 0.75:
                        if clase_lower == "oscuro":
                            self.lblEstado.setText("⚠️ La imagen está muy oscura. Por favor mejore la iluminación.")
                            self._captura_forzada = True
                            return
                        elif clase_lower == "movil":
                            self.lblEstado.setText("⚠️ Parece estar fotografiando una pantalla en vez de un papel físico.")
                            self._captura_forzada = True
                            return
            except Exception as e:
                print(f"[FaceAuth] Error al clasificar: {e}")

        self._captura_forzada = False
        self._emitir_frame(frame)

    def _emitir_frame(self, frame):
        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            self.foto_bytes = buffer.tobytes()
            self.mime = "image/jpeg"
            self.foto_capturada.emit(self.foto_bytes, self.mime)
            self.cerrar_camara()
            self.close()
        else:
            self.lblEstado.setText("No se pudo guardar la foto.")

    def _finalizar_rafaga(self):
        if self._timer_rafaga is not None:
            self._timer_rafaga.stop()
            self._timer_rafaga = None
        self._capturando_rafaga = False
        self.btnCapturar.setEnabled(True)

    def cancelar(self):

        self.foto_bytes = None
        self.cerrar_camara()
        self.close()

    def cerrar_camara(self):

        self.timer.stop()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def closeEvent(self, event):

        self.cerrar_camara()
        super().closeEvent(event)


# ---------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = VentanaCamara()
    ventana.foto_capturada.connect(
        lambda datos, mime: print("Foto capturada:", len(datos), "bytes")
    )
    ventana.show()

    sys.exit(app.exec_())
