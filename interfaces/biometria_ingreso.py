"""
Palabra de ingreso (voz) y postura de ingreso propias de cada usuario: registro (3 muestras),
verificación en el login (1:1 con el usuario escrito o 1:N si no se escribió) y el diálogo de
Ajustes para cambiarlas.

Reutiliza DialogoVoz (grabación sin bloquear) y la cámara en modo postura; el análisis
(MFCC/DTW y PoseNet) se ejecuta en hilos con utils.hilos.ejecutar_en_hilo.
"""
import json

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from controllers.usuario_controller import UsuarioController
from interfaces.captura_biometrica import abrir_camara_pose, campo
from interfaces.clases import COLOR_NEUTRO, COLOR_OK, aplicar_estilo, color_tema
from utils import plantillas_biometricas as plantillas
from utils.hilos import ejecutar_en_hilo
from utils.mensajes import Mensajes
from utils.umbrales_biometria import UMBRAL_CONFIANZA_VOZ, UMBRAL_SIMILITUD_POSTURA

TOTAL = plantillas.MUESTRAS_REGISTRO


def _oscuro(widget):
    """Tema de la ventana que abre el diálogo (login, registro o panel principal)."""
    while widget is not None:
        if hasattr(widget, "_modo_oscuro"):
            return bool(widget._modo_oscuro)
        widget = widget.parentWidget()
    return False


# =====================================================
# DIÁLOGO: ELEGIR LA PALABRA DE INGRESO
# =====================================================

class DialogoPalabraIngreso(QDialog):
    """Pide la palabra de ingreso dos veces y la valida (y, si se indica, que sea nueva)."""

    def __init__(self, parent, usuario_actual=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual
        self.palabra = None

        self.setWindowTitle("🎤 Palabra de ingreso")
        self.setMinimumWidth(420)
        self.setModal(True)
        aplicar_estilo(self, _oscuro(parent))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(8)

        titulo = QLabel("🎤 Elija su palabra de ingreso")
        titulo.setObjectName("tituloDialogo")
        sub = QLabel(
            "Una sola palabra de al menos 3 letras, fácil de pronunciar y que otros no adivinen "
            f"(ej.: girasol, tigre). Luego la grabará {TOTAL} veces."
        )
        sub.setObjectName("subDialogo")
        sub.setWordWrap(True)

        self.txtPalabra = QLineEdit()
        self.txtPalabra.setPlaceholderText("Palabra de ingreso")
        self.txtPalabra.setMaxLength(20)
        self.txtPalabra.setEchoMode(QLineEdit.Password)
        self.txtConfirmar = QLineEdit()
        self.txtConfirmar.setPlaceholderText("Repita la palabra")
        self.txtConfirmar.setMaxLength(20)
        self.txtConfirmar.setEchoMode(QLineEdit.Password)

        btn_ver = QPushButton("👁 Mostrar")
        btn_ver.setObjectName("btnSecundario")
        btn_ver.setCursor(Qt.PointingHandCursor)
        btn_ver.setCheckable(True)
        btn_ver.toggled.connect(self._mostrar)

        lay.addWidget(titulo)
        lay.addWidget(sub)
        lay.addSpacing(6)
        lay.addWidget(self.txtPalabra)
        lay.addWidget(self.txtConfirmar)
        lay.addWidget(btn_ver, 0, Qt.AlignLeft)
        lay.addSpacing(8)

        botones = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_ok = QPushButton("Continuar")
        btn_ok.setObjectName("btnPrimario")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setDefault(True)
        botones.addStretch()
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_ok)
        lay.addLayout(botones)

        btn_cancelar.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._aceptar)

    def _mostrar(self, visible):
        modo = QLineEdit.Normal if visible else QLineEdit.Password
        self.txtPalabra.setEchoMode(modo)
        self.txtConfirmar.setEchoMode(modo)

    def _aceptar(self):
        palabra = self.txtPalabra.text().strip()
        error = plantillas.validar_palabra(palabra)
        if error:
            Mensajes.advertencia(self, "Palabra No Válida", error)
            self.txtPalabra.setFocus()
            return
        if palabra.lower() != self.txtConfirmar.text().strip().lower():
            Mensajes.advertencia(self, "Las Palabras No Coinciden", "Escriba la misma palabra en ambos campos.")
            self.txtConfirmar.setFocus()
            return
        if self.usuario_actual and UsuarioController.es_palabra_actual(self.usuario_actual, palabra):
            Mensajes.advertencia(self, "Misma Palabra", "Elija una palabra distinta a la que usa actualmente.")
            self.txtPalabra.selectAll()
            self.txtPalabra.setFocus()
            return
        self.palabra = palabra
        self.accept()

    @staticmethod
    def pedir(parent, usuario_actual=None):
        dlg = DialogoPalabraIngreso(parent, usuario_actual)
        return dlg.palabra if dlg.exec_() == QDialog.Accepted else None


# =====================================================
# REGISTRO DE LA PALABRA DE INGRESO (voz)
# =====================================================

def registrar_palabra_ingreso(parent, al_terminar, usuario_actual=None, palabra=None):
    """
    Pide la palabra (si no se da), la graba TOTAL veces y crea la plantilla en un hilo.
    Llama a al_terminar(palabra, plantilla) si todo salió bien.
    """
    from interfaces.dialogo_voz import DialogoVoz
    from utils.reconocimiento_voz import ReconocedorVoz

    palabra = palabra or DialogoPalabraIngreso.pedir(parent, usuario_actual)
    if not palabra:
        return

    audios = []
    for i in range(1, TOTAL + 1):
        audio = DialogoVoz.obtener_audio(
            parent, palabra, plantillas.SEGUNDOS_PALABRA,
            f"🎤 Palabra de ingreso ({i}/{TOTAL})",
            "Pulse 'Grabar' y diga su palabra de ingreso con su voz normal, cerca del micrófono:"
            if i == 1 else f"Muestra {i} de {TOTAL}. Repita la misma palabra, igual que antes:"
        )
        if audio is None:
            return
        audios.append(audio)

    frecuencia = ReconocedorVoz._frecuencia_grabacion or ReconocedorVoz.FRECUENCIA_MUESTREO

    def fin(resultado, error):
        if error is not None:
            Mensajes.error(parent, "Error de Voz", f"No se pudieron analizar las grabaciones:\n{error}")
            return
        ok, plantilla, mensaje = resultado
        if not ok:
            if Mensajes.confirmar(parent, "Registro de Voz Fallido", f"{mensaje}\n\n¿Desea grabar de nuevo?"):
                registrar_palabra_ingreso(parent, al_terminar, usuario_actual, palabra)
            return
        al_terminar(palabra, plantilla)

    ejecutar_en_hilo(parent, plantillas.crear_plantilla_voz, (audios, frecuencia), fin,
                     "Analizando sus grabaciones...")


# =====================================================
# REGISTRO DE LA POSTURA DE INGRESO
# =====================================================

class RegistroPostura(QObject):
    """Captura la postura TOTAL veces (una ráfaga de cámara cada vez) y crea la plantilla."""

    def __init__(self, parent, al_terminar):
        super().__init__(parent)
        self.ventana = parent
        self.al_terminar = al_terminar
        self.capturas = []
        self._camara = None

    def iniciar(self):
        from utils.reconocimiento_pose import ReconocedorPose

        def con_modelo(cargado, error):
            if error is not None or not cargado:
                Mensajes.error(self.ventana, "Modelo No Disponible",
                               f"No se pudo cargar el modelo de postura:\n{error or ReconocedorPose._error_carga}")
                return
            self._siguiente_captura()

        ejecutar_en_hilo(self.ventana, ReconocedorPose.cargar_modelo, (), con_modelo,
                         "Cargando el detector de postura...")

    def _siguiente_captura(self):
        i = len(self.capturas) + 1
        texto = ("Póngase en la postura que quiera usar (ej.: brazos arriba, mano en el pecho)"
                 if i == 1 else "Repita exactamente la misma postura")
        try:
            self._camara = abrir_camara_pose(
                self.ventana, f"🧍 Postura de ingreso ({i}/{TOTAL})", texto, self._con_frames
            )
        except Exception as error:
            Mensajes.error(self.ventana, "Error de Cámara", f"No se pudo abrir la cámara:\n{error}")

    def _con_frames(self, frames):
        ejecutar_en_hilo(self.ventana, plantillas.puntos_postura, (frames,), self._con_puntos,
                         "Analizando la postura...")

    def _con_puntos(self, puntos, error):
        if error is not None:
            if Mensajes.confirmar(self.ventana, "Captura No Válida", f"{error}\n\n¿Desea repetir esta captura?"):
                self._siguiente_captura()
            return

        self.capturas.append(puntos)
        if len(self.capturas) < TOTAL:
            Mensajes.informacion(
                self.ventana, "Captura Lista ✓",
                f"Captura {len(self.capturas)} de {TOTAL} lista.\nAhora repita exactamente la misma postura."
            )
            self._siguiente_captura()
            return

        ok, plantilla, mensaje = plantillas.crear_plantilla_postura(self.capturas)
        if not ok:
            self.capturas = []
            if Mensajes.confirmar(self.ventana, "Registro de Postura Fallido",
                                  f"{mensaje}\n\n¿Desea empezar de nuevo?"):
                self._siguiente_captura()
            return
        self.al_terminar(plantilla)


# =====================================================
# VERIFICACIÓN EN EL LOGIN
# =====================================================

def _evaluar_voz(audio, frecuencia, candidatos, uno_a_uno):
    """(Hilo) Compara el audio con la plantilla de cada candidato. Devuelve (datos, confianza, mensaje)."""
    puntuaciones = []
    for datos in candidatos:
        confianza, error = plantillas.comparar_voz(audio, frecuencia, json.loads(datos["plantilla_voz"]))
        if error:
            return None, 0.0, error
        puntuaciones.append((datos, confianza))
    return _decidir(puntuaciones, UMBRAL_CONFIANZA_VOZ, uno_a_uno, "La palabra o la voz no coinciden")


def _evaluar_postura(frames, candidatos, uno_a_uno):
    """(Hilo) Extrae la postura y la compara con cada candidato."""
    try:
        puntos = plantillas.puntos_postura(frames)
    except ValueError as error:
        return None, 0.0, str(error)
    puntuaciones = [(d, plantillas.comparar_postura(puntos, json.loads(d["plantilla_postura"])))
                    for d in candidatos]
    return _decidir(puntuaciones, UMBRAL_SIMILITUD_POSTURA, uno_a_uno, "La postura no coincide")


def _decidir(puntuaciones, umbral, uno_a_uno, texto_fallo):
    if uno_a_uno:
        datos, valor = puntuaciones[0]
        if valor >= umbral:
            return datos, valor, ""
        return None, valor, (
            f"{texto_fallo} con las registradas ({valor * 100:.1f}% < {umbral * 100:.0f}%). Intente de nuevo."
        )
    return plantillas.identificar(puntuaciones, umbral)


def _evaluar_voz_desafio(audio, frecuencia, digitos, candidatos, uno_a_uno, recientes):
    """
    (Hilo) Prueba de vida de voz en una sola toma "palabra de ingreso + números":
    1) sin indicios de reproducción, 2) audio no usado antes, 3) Vosk reconoce exactamente los
    números pedidos, 4) el tramo anterior a los números coincide con la palabra del usuario.
    Devuelve (datos | None, confianza, mensaje, huellas).
    """
    from utils import liveness

    huellas = liveness.huellas_audio(audio, frecuencia)
    motivo = liveness.indicios_reproduccion(audio, frecuencia)
    if motivo:
        return None, 0.0, motivo, huellas
    if liveness.audio_repetido(huellas, recientes):
        return None, 0.0, "Este audio ya se usó antes. Cada ingreso debe grabarse en el momento.", huellas

    dichos, inicio = liveness.reconocer_numeros(audio, frecuencia)
    if dichos != digitos:
        pedidos = "-".join(str(d) for d in digitos)
        escuchados = "-".join(str(d) for d in dichos) or "ninguno"
        return None, 0.0, (
            f"No se escucharon los números pedidos ({pedidos}; se reconoció: {escuchados}). "
            f"Dígalos claramente después de su palabra."
        ), huellas
    if inicio is None or inicio < 0.3:
        return None, 0.0, "Diga primero su palabra de ingreso y después los números.", huellas

    tramo_palabra = audio[:max(0, int((inicio - 0.05) * frecuencia))]
    datos, confianza, mensaje = _evaluar_voz(tramo_palabra, frecuencia, candidatos, uno_a_uno)
    return datos, confianza, mensaje, huellas


def mostrar_fallo_biometrico(parent, metodo, mensaje, al_reintentar, al_usar_contrasena):
    """Aviso común de fallo con las opciones Reintentar / Usar contraseña / Cancelar."""
    caja = QMessageBox(parent)
    caja.setIcon(QMessageBox.Warning)
    caja.setWindowTitle(f"Verificación por {metodo} no superada")
    caja.setText(mensaje)
    caja.setInformativeText("¿Qué desea hacer?")
    btn_reintentar = caja.addButton("🔁 Reintentar", QMessageBox.AcceptRole)
    btn_contrasena = caja.addButton("🔒 Usar contraseña", QMessageBox.ActionRole)
    caja.addButton("Cancelar", QMessageBox.RejectRole)
    caja.exec_()

    if caja.clickedButton() is btn_reintentar:
        al_reintentar()
    elif caja.clickedButton() is btn_contrasena:
        al_usar_contrasena()


class VerificacionIngreso(QObject):
    """
    Pide la palabra (sin mostrarla) o la postura y la compara con la plantilla del usuario
    escrito, o con la de todos si no se escribió usuario. Con la prueba de vida activa usa
    el desafío de números (voz) o la secuencia de posturas (cámara). Si falla, ofrece
    reintentar o usar la contraseña.
    """

    def __init__(self, parent, metodo, candidatos, al_aprobar, al_usar_contrasena,
                 al_fallar=None, puede_intentar=None):
        super().__init__(parent)
        self.ventana = parent
        self.metodo = metodo                  # "voz" o "postura"
        self.candidatos = list(candidatos)
        self.uno_a_uno = len(self.candidatos) == 1
        self.al_aprobar = al_aprobar          # al_aprobar(datos_usuario, confianza)
        self.al_usar_contrasena = al_usar_contrasena
        self.al_fallar = al_fallar            # al_fallar(motivo): registra el intento fallido
        self.puede_intentar = puede_intentar  # puede_intentar() -> False si hay bloqueo temporal
        self._camara = None

    def iniciar(self):
        from utils import liveness

        if self.puede_intentar is not None and not self.puede_intentar():
            return
        if self.metodo == "voz":
            if liveness.LIVENESS_VOZ:
                self._capturar_voz_desafio()
            else:
                self._capturar_voz()
        elif liveness.LIVENESS_POSTURA:
            self._postura_con_vida()
        else:
            self._preparar_postura()

    # ---------- Voz ----------

    def _capturar_voz(self):
        from interfaces.dialogo_voz import DialogoVoz
        from utils.reconocimiento_voz import ReconocedorVoz

        audio = DialogoVoz.obtener_audio(
            self.ventana, None, plantillas.SEGUNDOS_PALABRA, "🎤 Ingresar por Voz",
            "Pulse 'Grabar' y diga su palabra de ingreso."
        )
        if audio is None:
            return
        frecuencia = ReconocedorVoz._frecuencia_grabacion or ReconocedorVoz.FRECUENCIA_MUESTREO
        ejecutar_en_hilo(self.ventana, _evaluar_voz, (audio, frecuencia, self.candidatos, self.uno_a_uno),
                         self._con_resultado, "Verificando su voz...")

    def _capturar_voz_desafio(self):
        from controllers.seguridad_controller import SeguridadController
        from interfaces.dialogo_voz import DialogoVoz
        from utils import liveness
        from utils.reconocimiento_voz import ReconocedorVoz

        # Números nuevos en cada intento; no se muestran hasta pulsar "Grabar"
        digitos = liveness.nuevo_desafio_voz()
        audio = DialogoVoz.obtener_audio(
            self.ventana, None, liveness.SEGUNDOS_DESAFIO_VOZ, "🎤 Ingresar por Voz",
            f"Al pulsar 'Grabar' aparecerán {liveness.DIGITOS_DESAFIO} números.\n"
            "Diga su palabra de ingreso y, enseguida, esos números.",
            texto_al_grabar=liveness.texto_desafio(digitos),
        )
        if audio is None:
            return
        frecuencia = ReconocedorVoz._frecuencia_grabacion or ReconocedorVoz.FRECUENCIA_MUESTREO
        recientes = SeguridadController.huellas_recientes()

        def fin(resultado, error):
            if resultado is not None:
                SeguridadController.guardar_huellas(resultado[3])   # ningún audio se acepta dos veces
                resultado = resultado[:3]
            self._con_resultado(resultado, error)

        ejecutar_en_hilo(self.ventana, _evaluar_voz_desafio,
                         (audio, frecuencia, digitos, self.candidatos, self.uno_a_uno, recientes),
                         fin, "Verificando su voz...")

    # ---------- Postura ----------

    def _postura_con_vida(self):
        from interfaces.dialogo_liveness import DialogoDesafioCamara
        from utils import liveness

        def embedding(d):
            try:
                return json.loads(campo(d, "embedding_facial") or "null")
            except ValueError:
                return None

        if self.uno_a_uno:
            datos = self.candidatos[0]
            desafio = liveness.DesafioPostura(json.loads(datos["plantilla_postura"]), embedding(datos),
                                              exigir_rostro=liveness.EXIGIR_ROSTRO_EN_POSTURA)
        else:
            # Sin usuario escrito se identifica por el rostro: solo candidatos con rostro vinculado
            candidatos = [(d, json.loads(d["plantilla_postura"]), embedding(d)) for d in self.candidatos]
            candidatos = [c for c in candidatos if c[2]]
            if not candidatos:
                Mensajes.advertencia(self.ventana, "Usuario Requerido",
                                     "Escriba su nombre de usuario y vuelva a pulsar 'Postura'.")
                return
            desafio = liveness.DesafioPostura(candidatos=candidatos, exigir_rostro=True)

        resultado, error = DialogoDesafioCamara.ejecutar(
            self.ventana, "🧍 Ingresar por Postura", desafio, _oscuro(self.ventana))
        if error:
            self._fallo(error)
        elif resultado is None:
            return  # cancelado por el usuario
        elif resultado.estado == "aprobado":
            datos = self.candidatos[0] if self.uno_a_uno else resultado.datos["usuario"]
            self._con_resultado((datos, resultado.datos["similitud"], ""), None)
        else:
            self._con_resultado((None, 0.0, resultado.detalle), None)

    def _preparar_postura(self):
        from utils.reconocimiento_pose import ReconocedorPose

        def con_modelo(cargado, error):
            if error is not None or not cargado:
                Mensajes.error(self.ventana, "Modelo No Disponible",
                               f"No se pudo cargar el modelo de postura:\n{error or ReconocedorPose._error_carga}")
                return
            self._capturar_postura()

        ejecutar_en_hilo(self.ventana, ReconocedorPose.cargar_modelo, (), con_modelo,
                         "Cargando el detector de postura...")

    def _capturar_postura(self):
        def con_frames(frames):
            ejecutar_en_hilo(self.ventana, _evaluar_postura, (frames, self.candidatos, self.uno_a_uno),
                             self._con_resultado, "Verificando su postura...")
        try:
            self._camara = abrir_camara_pose(
                self.ventana, "🧍 Ingresar por Postura", "Haga su postura de ingreso frente a la cámara", con_frames
            )
        except Exception as error:
            Mensajes.error(self.ventana, "Error de Cámara", f"No se pudo abrir la cámara:\n{error}")

    # ---------- Resultado ----------

    def _con_resultado(self, resultado, error):
        if error is not None:
            self._fallo(f"Ocurrió un error al analizar la {self.metodo}:\n{error}")
            return
        datos, confianza, mensaje = resultado
        if datos is None:
            print(f"[Ingreso] ❌ Verificación por {self.metodo} fallida: {mensaje}")
            self._fallo(mensaje)
            return
        print(f"[Ingreso] ✅ {self.metodo} verificada para '{datos['usuario']}' ({confianza * 100:.1f}%)")
        self.al_aprobar(datos, confianza)

    def _fallo(self, mensaje):
        if self.al_fallar is not None:
            self.al_fallar(mensaje)
        mostrar_fallo_biometrico(self.ventana, self.metodo, mensaje, self.iniciar, self.al_usar_contrasena)


# =====================================================
# AJUSTES: CAMBIAR PALABRA Y POSTURA DE INGRESO
# =====================================================

class DialogoBiometriaIngreso(QDialog):
    """Muestra el estado de la palabra y la postura de ingreso y permite cambiarlas."""

    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.oscuro = _oscuro(parent)
        self._registro_postura = None

        self.setWindowTitle("🔐 Palabra y postura de ingreso")
        self.setMinimumWidth(480)
        self.setModal(True)
        aplicar_estilo(self, self.oscuro)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(10)

        titulo = QLabel("🔐 Palabra y postura de ingreso")
        titulo.setObjectName("tituloDialogo")
        sub = QLabel("Úselas para entrar con los botones 🎤 Voz y 🧍 Postura de la pantalla de inicio.")
        sub.setObjectName("subDialogo")
        sub.setWordWrap(True)
        lay.addWidget(titulo)
        lay.addWidget(sub)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        grid = QGridLayout(tarjeta)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)

        lbl_voz = QLabel("🎤 Palabra de ingreso")
        lbl_voz.setObjectName("seccion")
        self.lblEstadoVoz = QLabel()
        btn_voz = QPushButton("Cambiar palabra")
        btn_voz.setObjectName("btnVoz")
        btn_voz.setCursor(Qt.PointingHandCursor)

        lbl_pose = QLabel("🧍 Postura de ingreso")
        lbl_pose.setObjectName("seccion")
        self.lblEstadoPostura = QLabel()
        btn_pose = QPushButton("Registrar de nuevo")
        btn_pose.setObjectName("btnPose")
        btn_pose.setCursor(Qt.PointingHandCursor)

        grid.addWidget(lbl_voz, 0, 0)
        grid.addWidget(self.lblEstadoVoz, 1, 0)
        grid.addWidget(btn_voz, 0, 1, 2, 1, Qt.AlignVCenter)
        grid.addWidget(lbl_pose, 2, 0)
        grid.addWidget(self.lblEstadoPostura, 3, 0)
        grid.addWidget(btn_pose, 2, 1, 2, 1, Qt.AlignVCenter)
        lay.addWidget(tarjeta)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnPrimario")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(btn_cerrar)
        lay.addLayout(fila)

        btn_voz.clicked.connect(self._cambiar_palabra)
        btn_pose.clicked.connect(self._cambiar_postura)
        self._refrescar()

    def _refrescar(self):
        datos = UsuarioController.buscar_usuario(self.usuario)
        for lbl, columna, nombre in ((self.lblEstadoVoz, "plantilla_voz", "palabra"),
                                     (self.lblEstadoPostura, "plantilla_postura", "postura")):
            if campo(datos, columna):
                lbl.setText(f"✓ {nombre.capitalize()} registrada")
                color = COLOR_OK
            else:
                lbl.setText(f"Sin {nombre} de ingreso registrada")
                color = COLOR_NEUTRO
            lbl.setStyleSheet(f"color: {color_tema(color, self.oscuro)}; font-size: 11px;")

    def _cambiar_palabra(self):
        def guardar(palabra, plantilla):
            if UsuarioController.guardar_palabra_ingreso(self.usuario, palabra, plantilla):
                Mensajes.informacion(self, "Palabra Actualizada ✓",
                                     "Su nueva palabra de ingreso quedó registrada.")
            else:
                Mensajes.error(self, "Error de Base de Datos", "No se pudo guardar la palabra de ingreso.")
            self._refrescar()

        registrar_palabra_ingreso(self, guardar, usuario_actual=self.usuario)

    def _cambiar_postura(self):
        def guardar(plantilla):
            if UsuarioController.guardar_plantilla_postura(self.usuario, plantilla):
                Mensajes.informacion(self, "Postura Actualizada ✓",
                                     "Su nueva postura de ingreso quedó registrada.")
            else:
                Mensajes.error(self, "Error de Base de Datos", "No se pudo guardar la postura de ingreso.")
            self._refrescar()

        self._registro_postura = RegistroPostura(self, guardar)
        self._registro_postura.iniciar()


def abrir_ajustes_biometria(parent, usuario):
    """Pide la contraseña (por seguridad) y abre el diálogo de palabra y postura de ingreso."""
    for intento in range(3):
        texto, aceptado = QInputDialog.getText(
            parent, "🔒 Confirmar identidad",
            f"Escriba la contraseña de '{usuario}' para cambiar su palabra o postura de ingreso:",
            QLineEdit.Password,
        )
        if not aceptado:
            return
        ok, _ = UsuarioController.iniciar_sesion(usuario, texto)
        if ok:
            DialogoBiometriaIngreso(parent, usuario).exec_()
            return
        Mensajes.advertencia(parent, "Contraseña Incorrecta", "La contraseña no es correcta.")
