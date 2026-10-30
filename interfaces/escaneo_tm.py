"""
Escaneo rápido para el ingreso con los modelos de Teachable Machine:

- DialogoEscaneoRostro: abre la cámara y, desde que aparece una cara, la analiza durante
  SEGUNDOS_ESCANEO_ROSTRO (cada cuadro: YuNet + clasificador de rostro + vector SFace de
  algunos cuadros). Al terminar devuelve el veredicto combinado.
- DialogoEscaneoVoz: graba SEGUNDOS_ESCANEO_VOZ con un medidor de nivel y clasifica el audio
  en ventanas de 1 s.

La cámara, el micrófono y los modelos trabajan en un QThread: la ventana nunca se congela.
"""
import time

import numpy as np
from PyQt5.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

try:
    import cv2
except ImportError:
    cv2 = None

from interfaces.clases import ESTILO_DIALOGO_CLASES, aplicar_estilo, color_tema
from interfaces.dialogo_liveness import ESTILO_LIVENESS
from utils import umbrales_biometria as U
from utils import detectores_vida as dv
from utils.decision_tm import Veredicto, decidir, evaluar_antispoof, registrar_escaneo

SEGUNDOS_ESPERA_ROSTRO = 10.0   # tiempo máximo para que aparezca una cara antes de rendirse
VECTORES_SFACE = 5              # cuadros de los que se extrae el vector SFace (verificación extra)


# =====================================================
# ROSTRO
# =====================================================

class HiloEscaneoRostro(QThread):
    cuadro = pyqtSignal(QImage)
    progreso = pyqtSignal(float, str)
    terminado = pyqtSignal(object)     # dict con el veredicto y los vectores SFace
    error = pyqtSignal(str)

    def __init__(self, segundos):
        super().__init__()
        self.segundos = segundos
        self._detener = False

    def detener(self):
        self._detener = True

    def run(self):
        from services.clasificador_imagen import ClasificadorImagen
        from services.modelos_tm import ModeloRostroTM

        if cv2 is None:
            self.error.emit("OpenCV no está instalado.")
            return
        self.progreso.emit(0.0, "Cargando el modelo de rostro...")
        if not ModeloRostroTM.cargar():
            self.error.emit(f"No se pudo cargar el modelo de rostro:\n{ModeloRostroTM.error_carga()}")
            return
        ClasificadorImagen.cargar_detector_facial()
        ClasificadorImagen.cargar_reconocedor_facial()
        # Celular/foto: MiniFASNetV2 (modelo anti-suplantación dedicado) en vez de la clase
        # "movil" de Teachable Machine, que también se activaba con caras reales.
        usar_antispoof = U.SUPLANTACION_ROSTRO == "antispoof" and dv.cargar_modelos()
        if U.SUPLANTACION_ROSTRO == "antispoof" and not usar_antispoof:
            print(f"[EscaneoRostro] ⚠️ Anti-spoofing no disponible ({dv.error_carga()}); se usa la clase 'movil'.")

        camara = cv2.VideoCapture(0, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(0)
        if not camara.isOpened():
            camara = cv2.VideoCapture(0)
        if not camara.isOpened():
            self.error.emit("No se detectó ninguna cámara.")
            return

        probabilidades, vectores, mejores = [], [], []
        reales, pantallas = [], []
        cuadros, con_rostro = 0, 0
        inicio_espera = time.monotonic()
        inicio = None
        try:
            while not self._detener:
                ok, frame = camara.read()
                if not ok or frame is None:
                    continue
                rostros = dv.detectar_rostros(frame)
                hay = len(rostros) > 0
                rostro = rostros[0] if hay else None
                bbox = tuple(int(v) for v in rostro[:4]) if hay else None
                score = float(rostro[-1]) if hay else 0.0
                ahora = time.monotonic()

                if inicio is None:
                    if hay:
                        inicio = ahora
                    elif ahora - inicio_espera > SEGUNDOS_ESPERA_ROSTRO:
                        self.error.emit("No se detectó ningún rostro. Colóquese de frente a la cámara "
                                        "con buena iluminación e intente de nuevo.")
                        return
                    else:
                        self.progreso.emit(0.0, "Colóquese de frente a la cámara...")

                if inicio is not None:
                    cuadros += 1
                    if hay:
                        con_rostro += 1
                        # Fuera del cuadro facial no se clasifica: "otros" / "fondo" no deben votar
                        probabilidades.append(ModeloRostroTM.predecir([frame])[0])
                        mejores.append((score, frame))
                        if usar_antispoof:
                            reales.append(dv.puntuacion_real(frame, rostro))
                            pantallas.append(dv.indicios_pantalla(frame, rostro))
                    transcurrido = ahora - inicio
                    self.progreso.emit(min(transcurrido / self.segundos, 1.0), "Escaneando su rostro...")
                    if transcurrido >= self.segundos:
                        break

                self.cuadro.emit(self._vista(frame, bbox if hay else None, inicio is not None))
        except Exception as error:
            self.error.emit(f"Error durante el escaneo: {error}")
            return
        finally:
            camara.release()

        if self._detener:
            return

        # Vectores SFace de los cuadros más nítidos (para la verificación extra 1:1)
        for _, frame in sorted(mejores, key=lambda m: m[0], reverse=True)[:VECTORES_SFACE]:
            ok, emb, _, _ = ClasificadorImagen.extraer_embedding(frame)
            if ok and emb:
                vectores.append(emb)

        etiquetas = ModeloRostroTM.etiquetas()
        suplantacion = ModeloRostroTM.CLASES_SUPLANTACION
        antispoof = {}
        conteo_tm = {}
        for i in np.asarray(probabilidades).argmax(axis=1) if probabilidades else []:
            conteo_tm[etiquetas[i]] = conteo_tm.get(etiquetas[i], 0) + 1
        if usar_antispoof:
            # La clase "movil" se quita y se reparte su probabilidad entre las demás
            quedan = [i for i, e in enumerate(etiquetas) if e.lower() not in suplantacion]
            if probabilidades:
                p = np.asarray(probabilidades)[:, quedan]
                probabilidades = p / np.maximum(p.sum(axis=1, keepdims=True), 1e-6)
            etiquetas, suplantacion = [etiquetas[i] for i in quedan], set()
            antispoof = evaluar_antispoof(reales, pantallas)

        if antispoof.get("rechazar"):
            veredicto = Veredicto(False, motivo="⚠️ La imagen parece una foto o la pantalla de un celular. "
                                                "Debe estar usted en persona frente a la cámara.")
        else:
            veredicto = decidir(
                probabilidades, etiquetas, ModeloRostroTM.clases_persona(),
                suplantacion, U.UMBRAL_ROSTRO_ESCANEO, U.VOTOS_ROSTRO_ESCANEO,
                muestras_minimas=max(5, int(cuadros * U.FRACCION_CON_ROSTRO)),
                fraccion_suplantacion=U.FRACCION_SUPLANTACION, que="rostro",
            )
        registrar_escaneo("rostro", veredicto, cuadros=cuadros, con_rostro=con_rostro,
                          vectores_sface=len(vectores), antispoof=antispoof, conteo_tm_original=conteo_tm)
        print(f"[EscaneoRostro] {cuadros} cuadros, {con_rostro} con rostro, votos={veredicto.conteo} "
              f"→ {'✅' if veredicto.aprobado else '❌'} {veredicto.clase} "
              f"({veredicto.confianza * 100:.1f}%, {veredicto.votos * 100:.0f}% votos)")
        self.terminado.emit({"veredicto": veredicto, "vectores": vectores})

    @staticmethod
    def _vista(frame, bbox, escaneando):
        vista = frame.copy()
        if bbox is not None:
            x, y, w, h = bbox
            color = (80, 200, 120) if escaneando else (235, 99, 37)
            cv2.rectangle(vista, (x, y), (x + w, y + h), color, 2)
        vista = cv2.cvtColor(cv2.flip(vista, 1), cv2.COLOR_BGR2RGB)
        alto, ancho = vista.shape[:2]
        return QImage(vista.data, ancho, alto, 3 * ancho, QImage.Format_RGB888).copy()


class _DialogoEscaneo(QDialog):
    """Base visual común: título, área central, barra de progreso, estado y Cancelar."""

    def __init__(self, parent, titulo, instruccion, oscuro):
        super().__init__(parent)
        self.resultado = None
        self.error = None
        self.oscuro = oscuro
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(620)
        aplicar_estilo(self, oscuro, ESTILO_DIALOGO_CLASES + ESTILO_LIVENESS)

        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(22, 18, 22, 16)
        self.lay.setSpacing(10)
        self.lblInstruccion = QLabel(instruccion)
        self.lblInstruccion.setObjectName("instruccion")
        self.lblInstruccion.setAlignment(Qt.AlignCenter)
        self.lblInstruccion.setWordWrap(True)
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setTextVisible(False)
        self.lblEstado = QLabel("")
        self.lblEstado.setObjectName("tiempo")
        self.lblEstado.setAlignment(Qt.AlignCenter)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)
        self._fila = QHBoxLayout()
        self._fila.addStretch()
        self._fila.addWidget(btn_cancelar)

    def _armar(self, central):
        self.lay.addWidget(self.lblInstruccion)
        self.lay.addWidget(central, 0, Qt.AlignCenter)
        self.lay.addWidget(self.barra)
        self.lay.addWidget(self.lblEstado)
        self.lay.addLayout(self._fila)

    def _progreso(self, fraccion, texto):
        self.barra.setValue(int(fraccion * 100))
        self.lblEstado.setText(texto)

    def _con_resultado(self, resultado):
        self.resultado = resultado
        aprobado = resultado["veredicto"].aprobado
        self.lblEstado.setText("✓ Reconocido" if aprobado else "Analizado")
        self.lblEstado.setStyleSheet(
            f"color: {color_tema('#047857' if aprobado else '#B45309', self.oscuro)}; font-weight: bold;")
        QTimer.singleShot(250, self.accept)

    def _con_error(self, mensaje):
        self.error = mensaje
        self.done(QDialog.Rejected)

    def done(self, codigo):
        self.hilo.detener()
        self.hilo.wait(3000)
        super().done(codigo)

    @classmethod
    def ejecutar(cls, parent, oscuro=False, **opciones):
        """Devuelve (resultado | None si se canceló, mensaje_de_error | None)."""
        dlg = cls(parent, oscuro, **opciones)
        dlg.exec_()
        return dlg.resultado, dlg.error


class DialogoEscaneoRostro(_DialogoEscaneo):
    def __init__(self, parent, oscuro=False):
        super().__init__(parent, "📷 Ingreso por Rostro",
                         f"Mire a la cámara unos {U.SEGUNDOS_ESCANEO_ROSTRO:g} segundos", oscuro)
        self.lblVideo = QLabel("Abriendo la cámara...")
        self.lblVideo.setObjectName("video")
        self.lblVideo.setAlignment(Qt.AlignCenter)
        self.lblVideo.setFixedSize(576, 360)
        self._armar(self.lblVideo)

        self.hilo = HiloEscaneoRostro(U.SEGUNDOS_ESCANEO_ROSTRO)
        self.hilo.cuadro.connect(self._mostrar_cuadro)
        self.hilo.progreso.connect(self._progreso)
        self.hilo.terminado.connect(self._con_resultado)
        self.hilo.error.connect(self._con_error)

    def showEvent(self, evento):
        super().showEvent(evento)
        if not self.hilo.isRunning() and self.resultado is None:
            self.hilo.start()

    def _mostrar_cuadro(self, imagen):
        self.lblVideo.setPixmap(QPixmap.fromImage(imagen).scaled(
            self.lblVideo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


# =====================================================
# POSTURA
# =====================================================

class HiloEscaneoPostura(QThread):
    cuadro = pyqtSignal(QImage)
    progreso = pyqtSignal(float, str)
    terminado = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, segundos_preparar, segundos):
        super().__init__()
        self.segundos_preparar = segundos_preparar
        self.segundos = segundos
        self._detener = False

    def detener(self):
        self._detener = True

    def run(self):
        from services.clasificador_imagen import ClasificadorImagen
        from services.modelos_tm import ModeloPosturaTM

        if cv2 is None:
            self.error.emit("OpenCV no está instalado.")
            return
        self.progreso.emit(0.0, "Cargando el modelo de postura...")
        if not ModeloPosturaTM.cargar():
            self.error.emit(f"No se pudo cargar el modelo de postura:\n{ModeloPosturaTM.error_carga()}")
            return
        ClasificadorImagen.cargar_reconocedor_facial()
        usar_antispoof = dv.cargar_modelos()

        camara = cv2.VideoCapture(0, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(0)
        if not camara.isOpened():
            camara = cv2.VideoCapture(0)
        if not camara.isOpened():
            self.error.emit("No se detectó ninguna cámara.")
            return

        probabilidades, caras, reales, pantallas = [], [], [], []
        cuerpos = []     # (segundo del escaneo, puntos [17, 3]) de los cuadros con cuerpo visible
        cuadros = 0
        etiquetas = ModeloPosturaTM.etiquetas()
        inicio = time.monotonic()
        try:
            while not self._detener:
                ok, frame = camara.read()
                if not ok or frame is None:
                    continue
                transcurrido = time.monotonic() - inicio
                probs, visibles, puntos = ModeloPosturaTM.predecir(frame)
                completo = visibles >= U.PUNTOS_POSTURA_MINIMOS
                texto = f"{etiquetas[int(probs.argmax())]} {probs.max() * 100:.0f}%" if completo else ""

                if transcurrido < self.segundos_preparar:
                    restante = int(self.segundos_preparar - transcurrido) + 1
                    aviso = "" if completo else " (aléjese: no se ve su cuerpo)"
                    self.progreso.emit(0.0, f"Colóquese en su postura... {restante}{aviso}")
                    self.cuadro.emit(self._vista(frame, puntos, texto, False))
                    continue

                escaneo = transcurrido - self.segundos_preparar
                cuadros += 1
                if completo:
                    probabilidades.append(probs)
                    cuerpos.append((escaneo, puntos))
                rostros = dv.detectar_rostros(frame)
                if len(rostros):
                    rostro = rostros[0]
                    caras.append((float(rostro[-1]), frame))
                    if usar_antispoof:
                        reales.append(dv.puntuacion_real(frame, rostro))
                        pantallas.append(dv.indicios_pantalla(frame, rostro))
                self.progreso.emit(min(escaneo / self.segundos, 1.0), "Escaneando su postura... no se mueva")
                self.cuadro.emit(self._vista(frame, puntos, texto, True))
                if escaneo >= self.segundos:
                    break
        except Exception as error:
            self.error.emit(f"Error durante el escaneo: {error}")
            return
        finally:
            camara.release()
        if self._detener:
            return

        vectores = []
        for _, frame in sorted(caras, key=lambda c: c[0], reverse=True)[:VECTORES_SFACE]:
            ok, emb, _, _ = ClasificadorImagen.extraer_embedding(frame)
            if ok and emb:
                vectores.append(emb)

        antispoof = evaluar_antispoof(reales, pantallas) if usar_antispoof else {}
        if antispoof.get("rechazar"):
            veredicto = Veredicto(False, motivo="⚠️ La imagen parece una foto o una pantalla. Debe estar "
                                                "usted en persona frente a la cámara.")
        else:
            veredicto = decidir(
                probabilidades, ModeloPosturaTM.etiquetas(), ModeloPosturaTM.clases_persona(), set(),
                U.UMBRAL_POSTURA_ESCANEO, U.VOTOS_POSTURA_ESCANEO,
                muestras_minimas=max(5, int(cuadros * 0.5)),
                fraccion_suplantacion=U.FRACCION_SUPLANTACION, que="postura",
            )
        registrar_escaneo("postura", veredicto, cuadros=cuadros, con_cuerpo=len(probabilidades),
                          con_rostro=len(caras), vectores_sface=len(vectores), antispoof=antispoof)
        print(f"[EscaneoPostura] {cuadros} cuadros, {len(probabilidades)} con cuerpo, votos={veredicto.conteo} "
              f"→ {'✅' if veredicto.aprobado else '❌'} {veredicto.clase} ({veredicto.confianza * 100:.1f}%)")
        self.terminado.emit({"veredicto": veredicto, "vectores": vectores,
                             "antispoof_rechazo": bool(antispoof.get("rechazar")),
                             **self._puntos_promedio(cuerpos)})

    def _puntos_promedio(self, cuerpos):
        """
        Puntos del cuerpo promediados (lista de 51 valores y, x, puntuación, como las plantillas
        de postura): de todo el escaneo, y de sus tres tercios por separado, que sirven como las
        3 capturas de la plantilla de un usuario nuevo sin tener que repetir la postura 3 veces.
        """
        def promedio(lista):
            return [round(float(v), 4) for v in np.mean(lista, axis=0).reshape(-1)] if lista else None

        tercio = self.segundos / 3
        capturas = [promedio([p for t, p in cuerpos if i * tercio <= t < (i + 1) * tercio or
                              (i == 2 and t >= self.segundos)]) for i in range(3)]
        return {"puntos": promedio([p for _, p in cuerpos]),
                "capturas": [c for c in capturas if c is not None]}

    @staticmethod
    def _vista(frame, puntos, texto, escaneando):
        """Vista espejada con los puntos y el esqueleto de PoseNet, como en Teachable Machine."""
        from services.modelos_tm import ModeloPosturaTM

        vista = cv2.flip(frame, 1)
        alto, ancho = vista.shape[:2]
        pts = ModeloPosturaTM.puntos_en_imagen(puntos, ancho, alto)
        color_linea = (80, 200, 120) if escaneando else (235, 160, 37)
        for a, b in ModeloPosturaTM.ESQUELETO:
            if pts[a][2] >= ModeloPosturaTM.PUNTO_VISIBLE and pts[b][2] >= ModeloPosturaTM.PUNTO_VISIBLE:
                cv2.line(vista, pts[a][:2], pts[b][:2], color_linea, 3, cv2.LINE_AA)
        for x, y, p in pts:
            if p >= ModeloPosturaTM.PUNTO_VISIBLE:
                cv2.circle(vista, (x, y), 6, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(vista, (x, y), 4, (37, 99, 235), -1, cv2.LINE_AA)
        if texto:
            cv2.rectangle(vista, (10, 10), (20 + 14 * len(texto), 48), (15, 23, 42), -1)
            cv2.putText(vista, texto, (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        vista = cv2.cvtColor(vista, cv2.COLOR_BGR2RGB)
        return QImage(vista.data, ancho, alto, 3 * ancho, QImage.Format_RGB888).copy()


class DialogoEscaneoPostura(DialogoEscaneoRostro):
    def __init__(self, parent, oscuro=False, registro=False):
        _DialogoEscaneo.__init__(
            self, parent, "🧍 Registrar postura" if registro else "🧍 Ingreso por Postura",
            "Haga la postura que quiera usar para entrar (que se vean su cara y su torso)" if registro
            else "Aléjese para que se vea su torso y haga su postura", oscuro)
        self.lblVideo = QLabel("Abriendo la cámara...")
        self.lblVideo.setObjectName("video")
        self.lblVideo.setAlignment(Qt.AlignCenter)
        self.lblVideo.setFixedSize(576, 360)
        self._armar(self.lblVideo)

        self.hilo = HiloEscaneoPostura(U.SEGUNDOS_PREPARAR_POSTURA, U.SEGUNDOS_ESCANEO_POSTURA)
        self.hilo.cuadro.connect(self._mostrar_cuadro)
        self.hilo.progreso.connect(self._progreso)
        self.hilo.terminado.connect(self._con_resultado)
        self.hilo.error.connect(self._con_error)


# =====================================================
# VOZ
# =====================================================

class HiloEscaneoVoz(QThread):
    nivel = pyqtSignal(float)
    progreso = pyqtSignal(float, str)
    terminado = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, segundos):
        super().__init__()
        self.segundos = segundos
        self._detener = False

    def detener(self):
        self._detener = True

    def run(self):
        from services.modelos_tm import ModeloVozTM

        try:
            import sounddevice as sd
        except Exception as error:
            self.error.emit(f"No se pudo usar el micrófono (sounddevice): {error}")
            return
        self.progreso.emit(0.0, "Cargando el modelo de voz...")
        if not ModeloVozTM.cargar():
            self.error.emit(f"No se pudo cargar el modelo de voz:\n{ModeloVozTM.error_carga()}")
            return

        frecuencia = ModeloVozTM.FRECUENCIA
        bloques = []
        try:
            with sd.InputStream(samplerate=frecuencia, channels=1, dtype="float32", blocksize=2048) as flujo:
                inicio = time.monotonic()
                while not self._detener:
                    datos, _ = flujo.read(2048)
                    bloques.append(datos[:, 0].copy())
                    self.nivel.emit(float(np.sqrt(np.mean(datos ** 2))))
                    transcurrido = time.monotonic() - inicio
                    self.progreso.emit(min(transcurrido / self.segundos, 1.0), "🔴 Grabando... hable ahora")
                    if transcurrido >= self.segundos:
                        break
        except Exception as error:
            self.error.emit(f"No se pudo grabar desde el micrófono:\n{error}")
            return
        if self._detener:
            return

        self.progreso.emit(1.0, "Analizando su voz...")
        audio = np.concatenate(bloques) if bloques else np.zeros(0, np.float32)
        try:
            probabilidades = ModeloVozTM.predecir(audio, frecuencia)
        except Exception as error:
            self.error.emit(f"Error al analizar la voz: {error}")
            return

        veredicto = decidir(
            probabilidades, ModeloVozTM.etiquetas(), ModeloVozTM.clases_persona(),
            ModeloVozTM.CLASES_SUPLANTACION, U.UMBRAL_VOZ_ESCANEO, U.VOTOS_VOZ_ESCANEO,
            muestras_minimas=U.VENTANAS_VOZ_MINIMAS,
            fraccion_suplantacion=U.FRACCION_SUPLANTACION, que="voz", contar_sin_persona=False,
        )
        registrar_escaneo("voz", veredicto, ventanas=len(probabilidades))
        print(f"[EscaneoVoz] {len(probabilidades)} ventanas con sonido, votos={veredicto.conteo} "
              f"→ {'✅' if veredicto.aprobado else '❌'} {veredicto.clase} "
              f"({veredicto.confianza * 100:.1f}%, {veredicto.votos * 100:.0f}% votos)")
        self.terminado.emit({"veredicto": veredicto, "audio": audio, "frecuencia": frecuencia})


class DialogoEscaneoVoz(_DialogoEscaneo):
    def __init__(self, parent, oscuro=False, instruccion="Diga su palabra clave con su voz normal",
                 titulo="🎤 Ingreso por Voz"):
        super().__init__(parent, titulo, instruccion, oscuro)
        self.lblMicro = QLabel("🎤")
        self.lblMicro.setAlignment(Qt.AlignCenter)
        self.lblMicro.setFixedSize(576, 150)
        self.lblMicro.setStyleSheet("font-size: 64px;")
        self.medidor = QProgressBar()
        self.medidor.setRange(0, 100)
        self.medidor.setTextVisible(False)
        self.medidor.setFixedHeight(8)
        self._armar(self.lblMicro)
        self.lay.insertWidget(2, self.medidor)

        self.hilo = HiloEscaneoVoz(U.SEGUNDOS_ESCANEO_VOZ)
        self.hilo.nivel.connect(lambda rms: self.medidor.setValue(min(100, int(rms * 600))))
        self.hilo.progreso.connect(self._progreso)
        self.hilo.terminado.connect(self._con_resultado)
        self.hilo.error.connect(self._con_error)

    def showEvent(self, evento):
        super().showEvent(evento)
        # Un instante para que la persona lea la instrucción antes de grabar
        QTimer.singleShot(600, self._iniciar)

    def _iniciar(self):
        if self.isVisible() and not self.hilo.isRunning() and self.resultado is None:
            self.hilo.start()
