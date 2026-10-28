"""
Módulo de Clases: diálogos para crear y unirse a clases, verificación biométrica
(voz / postura) al abrir una clase y ventana de detalle con la configuración de acceso.

Reutiliza la captura y verificación del login (interfaces/captura_biometrica.py,
interfaces/dialogo_voz.py, interfaces/camara.py) y ejecuta el análisis de los modelos
en hilos (QThread) para no bloquear la interfaz.
"""
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)
from PyQt5.QtCore import QObject, Qt

from controllers.clase_controller import ClaseController, LONGITUD_CODIGO
from controllers.usuario_controller import UsuarioController
from interfaces.captura_biometrica import (
    ESTILO_BOTONES_BIOMETRIA,
    SEGUNDOS_GRABACION_VOZ,
    UMBRAL_CONFIANZA_VERIFICACION_POSE,
    abrir_camara_pose,
    biometria_vinculada,
    campo,
    capturar_pose,
    capturar_voz,
)
from utils.hilos import ejecutar_en_hilo
from utils.mensajes import Mensajes
from utils.tema import transformar_a_oscuro


# =====================================================
# ESTILOS (paleta clara; el modo oscuro se genera con utils.tema)
# =====================================================

ESTILO_DIALOGO_CLASES = """
    QDialog { background: #F8FAFC; font-family: "Segoe UI"; }
    QLabel { color: #0F172A; font-size: 12px; background: transparent; }
    QLabel#tituloDialogo { font-size: 18px; font-weight: bold; color: #0F172A; }
    QLabel#subDialogo { color: #64748B; font-size: 12px; }
    QLabel#etiquetaCampo { color: #334155; font-size: 12px; font-weight: bold; }
    QLabel#seccion { color: #0F172A; font-size: 14px; font-weight: bold; }
    QLabel#codigo {
        color: #2563EB;
        font-family: Consolas, "Courier New", monospace;
        font-size: 22px;
        font-weight: bold;
        letter-spacing: 4px;
    }
    QLabel#pillRolClase {
        color: #2563EB;
        background: #EFF6FF;
        border: 1px solid #DBEAFE;
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: bold;
    }
    QFrame#tarjeta {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
    }
    QLineEdit, QPlainTextEdit {
        background: #FFFFFF;
        color: #0F172A;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 13px;
    }
    QLineEdit:focus, QPlainTextEdit:focus { border: 1.5px solid #2563EB; }
    QCheckBox { color: #1E293B; font-size: 13px; spacing: 8px; background: transparent; }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1.5px solid #CBD5E1;
        border-radius: 5px;
        background: #FFFFFF;
    }
    QCheckBox::indicator:hover { border: 1.5px solid #2563EB; }
    QCheckBox::indicator:checked { background: #2563EB; border: 1.5px solid #2563EB; }
    QListWidget {
        background: #FFFFFF;
        color: #1E293B;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        font-size: 12px;
        padding: 4px;
    }
    QPushButton#btnPrimario {
        background: #2563EB;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 18px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#btnPrimario:hover { background: #1D4ED8; }
    QPushButton#btnSecundario {
        background: transparent;
        color: #2563EB;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        padding: 9px 16px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#btnSecundario:hover { background: #EFF6FF; }
""" + ESTILO_BOTONES_BIOMETRIA

# Colores de estado (se adaptan al modo oscuro con el mismo mapa de utils.tema)
COLOR_OK = "#059669"
COLOR_NEUTRO = "#64748B"
COLOR_AVISO = "#D97706"


def aplicar_estilo(widget, oscuro, qss=ESTILO_DIALOGO_CLASES):
    """Aplica la hoja de estilos en claro u oscuro según el tema del Dashboard."""
    widget.setStyleSheet(transformar_a_oscuro(qss) if oscuro else qss)


def color_tema(color, oscuro):
    """Devuelve el color equivalente para el tema actual."""
    return transformar_a_oscuro(color) if oscuro else color


# =====================================================
# DIÁLOGO: NUEVA CLASE
# =====================================================

class DialogoNuevaClase(QDialog):
    """Formulario para crear una clase. Al aceptar, self.clase_creada tiene sus datos."""

    def __init__(self, parent, usuario_id, oscuro=False):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.clase_creada = None

        self.setWindowTitle("➕ Nueva clase")
        self.setMinimumWidth(460)
        self.setModal(True)
        aplicar_estilo(self, oscuro)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(8)

        titulo = QLabel("🏫 Crear una nueva clase")
        titulo.setObjectName("tituloDialogo")
        sub = QLabel("Se generará un código de acceso para que otros usuarios se unan.")
        sub.setObjectName("subDialogo")
        sub.setWordWrap(True)
        lay.addWidget(titulo)
        lay.addWidget(sub)
        lay.addSpacing(8)

        lbl_nombre = QLabel("Nombre de la clase *")
        lbl_nombre.setObjectName("etiquetaCampo")
        self.txtNombre = QLineEdit()
        self.txtNombre.setPlaceholderText("Ej: Cálculo Diferencial — Grupo A")
        self.txtNombre.setMaxLength(80)

        lbl_desc = QLabel("Descripción")
        lbl_desc.setObjectName("etiquetaCampo")
        self.txtDescripcion = QPlainTextEdit()
        self.txtDescripcion.setPlaceholderText("¿De qué trata la clase? (opcional)")
        self.txtDescripcion.setFixedHeight(80)

        lay.addWidget(lbl_nombre)
        lay.addWidget(self.txtNombre)
        lay.addSpacing(4)
        lay.addWidget(lbl_desc)
        lay.addWidget(self.txtDescripcion)
        lay.addSpacing(6)

        lbl_acceso = QLabel("Acceso biométrico a la clase")
        lbl_acceso.setObjectName("etiquetaCampo")
        self.chkVoz = QCheckBox("🎤 Pedir verificación por voz")
        self.chkPostura = QCheckBox("🧍 Pedir verificación por postura")
        nota = QLabel("Se aplicará a los miembros que se unan; cada uno puede ajustarlo en la configuración de la clase.")
        nota.setObjectName("subDialogo")
        nota.setWordWrap(True)
        lay.addWidget(lbl_acceso)
        lay.addWidget(self.chkVoz)
        lay.addWidget(self.chkPostura)
        lay.addWidget(nota)
        lay.addSpacing(10)

        botones = QHBoxLayout()
        botones.setSpacing(10)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btnCrear = QPushButton("Crear clase")
        self.btnCrear.setObjectName("btnPrimario")
        self.btnCrear.setCursor(Qt.PointingHandCursor)
        self.btnCrear.setDefault(True)
        botones.addStretch()
        botones.addWidget(btn_cancelar)
        botones.addWidget(self.btnCrear)
        lay.addLayout(botones)

        btn_cancelar.clicked.connect(self.reject)
        self.btnCrear.clicked.connect(self.crear)
        self.txtNombre.returnPressed.connect(self.crear)

    def crear(self):
        nombre = self.txtNombre.text().strip()
        if not nombre:
            Mensajes.advertencia(self, "Campo Vacío", "Escriba el nombre de la clase.")
            self.txtNombre.setFocus()
            return

        try:
            ok, resultado = ClaseController.crear_clase(
                self.usuario_id,
                nombre,
                self.txtDescripcion.toPlainText(),
                self.chkVoz.isChecked(),
                self.chkPostura.isChecked(),
            )
        except Exception as error:
            Mensajes.error(self, "Error", f"No se pudo crear la clase:\n{error}")
            return

        if not ok:
            Mensajes.advertencia(self, "No se pudo crear la clase", resultado)
            self.txtNombre.setFocus()
            self.txtNombre.selectAll()
            return

        self.clase_creada = resultado
        Mensajes.informacion(
            self,
            "Clase Creada ✓",
            f"La clase '{resultado['nombre']}' se creó correctamente.\n\n"
            f"Código de acceso: {resultado['codigo_acceso']}\n\n"
            f"Compártalo para que otros usuarios se unan con 'Unirme a una clase'."
        )
        self.accept()


# =====================================================
# DIÁLOGO: UNIRSE A UNA CLASE
# =====================================================

class DialogoUnirseClase(QDialog):
    """Pide el código de acceso e inscribe al usuario como estudiante."""

    def __init__(self, parent, usuario_id, oscuro=False):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.clase_unida = None

        self.setWindowTitle("🔑 Unirme a una clase")
        self.setMinimumWidth(400)
        self.setModal(True)
        aplicar_estilo(self, oscuro)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(8)

        titulo = QLabel("🔑 Unirme a una clase")
        titulo.setObjectName("tituloDialogo")
        sub = QLabel("Escriba el código de acceso que le compartió el docente.")
        sub.setObjectName("subDialogo")
        sub.setWordWrap(True)

        self.txtCodigo = QLineEdit()
        self.txtCodigo.setPlaceholderText("Ej: K7M2QX")
        self.txtCodigo.setMaxLength(LONGITUD_CODIGO + 4)
        self.txtCodigo.setAlignment(Qt.AlignCenter)
        self.txtCodigo.setStyleSheet("font-size: 18px; font-weight: bold; letter-spacing: 3px;")
        # Mayúsculas automáticas mientras se escribe
        self.txtCodigo.textEdited.connect(
            lambda texto: self.txtCodigo.setText(texto.upper())
        )

        lay.addWidget(titulo)
        lay.addWidget(sub)
        lay.addSpacing(8)
        lay.addWidget(self.txtCodigo)
        lay.addSpacing(10)

        botones = QHBoxLayout()
        botones.setSpacing(10)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_unirme = QPushButton("Unirme")
        btn_unirme.setObjectName("btnPrimario")
        btn_unirme.setCursor(Qt.PointingHandCursor)
        btn_unirme.setDefault(True)
        botones.addStretch()
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_unirme)
        lay.addLayout(botones)

        btn_cancelar.clicked.connect(self.reject)
        btn_unirme.clicked.connect(self.unirse)
        self.txtCodigo.returnPressed.connect(self.unirse)

    def unirse(self):
        codigo = self.txtCodigo.text().strip()
        if not codigo:
            Mensajes.advertencia(self, "Campo Vacío", "Escriba el código de acceso de la clase.")
            self.txtCodigo.setFocus()
            return

        try:
            ok, resultado = ClaseController.unirse_por_codigo(self.usuario_id, codigo)
        except Exception as error:
            Mensajes.error(self, "Error", f"No se pudo unir a la clase:\n{error}")
            return

        if not ok:
            Mensajes.advertencia(self, "No se pudo unir", resultado)
            self.txtCodigo.selectAll()
            self.txtCodigo.setFocus()
            return

        self.clase_unida = resultado
        metodos = [m for m, activo in (("voz", resultado["voz_habilitada"]),
                                       ("postura", resultado["postura_habilitada"])) if activo]
        extra = (
            f"\n\nEsta clase pide verificación por {' y '.join(metodos)}. "
            f"Puede registrar una voz/postura propia para la clase desde su configuración."
            if metodos else ""
        )
        Mensajes.informacion(self, "Te uniste a la clase ✓",
                             f"Ahora eres estudiante de '{resultado['nombre']}'.{extra}")
        self.accept()


# =====================================================
# VERIFICACIÓN DE ACCESO (voz / postura / contraseña)
# =====================================================

class VerificadorAccesoClase(QObject):
    """
    Pide, en orden, la verificación de voz y/o postura habilitada para el usuario en la
    clase. Usa la biometría registrada para la clase y, si no hay, la de la cuenta.
    Si una verificación falla permite reintentar o entrar con la contraseña.
    Al aprobar llama a al_conceder(metodo_texto).
    """

    NOMBRES = {"voz": "voz", "postura": "postura"}

    def __init__(self, parent, clase, usuario_id, usuario, al_conceder):
        super().__init__(parent)
        self.ventana = parent
        self.clase = clase
        self.usuario_id = usuario_id
        self.usuario = usuario
        self.al_conceder = al_conceder

        self._acceso = None
        self._pendientes = []
        self._aprobados = []
        self._metodo = None
        self._referencia = (None, None)
        self._ventana_pose = None

    # -------------------------------------------------
    # Flujo principal
    # -------------------------------------------------

    def iniciar(self):
        self._acceso = ClaseController.acceso_usuario(self.clase["id"], self.usuario_id)
        if self._acceso is None:
            Mensajes.error(self.ventana, "Error de Base de Datos",
                           "No se pudo leer la configuración de acceso de la clase.")
            return

        self._pendientes = [
            metodo for metodo, columna in (("voz", "voz_habilitada"), ("postura", "postura_habilitada"))
            if self._acceso[columna]
        ]
        self._aprobados = []

        if not self._pendientes:
            self.al_conceder("Sin verificación biométrica")
            return

        self._siguiente()

    def _siguiente(self):
        if not self._pendientes:
            self.al_conceder(" + ".join(self._aprobados))
            return

        self._metodo = self._pendientes[0]
        ejecutar_en_hilo(
            self.ventana, self._cargar_referencia, (self._metodo,), self._con_referencia,
            f"Preparando la verificación por {self._metodo}..."
        )

    def _cargar_referencia(self, metodo):
        """(Hilo) Carga el modelo y busca la biometría de la clase o, si no hay, la de la cuenta."""
        etiqueta, vector = biometria_vinculada(self._acceso, metodo)
        if etiqueta is not None:
            return etiqueta, vector

        datos_cuenta = UsuarioController.buscar_usuario(self.usuario)
        return biometria_vinculada(datos_cuenta, metodo)

    def _con_referencia(self, resultado, error):
        if error is not None:
            self._fallo(f"No se pudo preparar el reconocimiento de {self._metodo}:\n{error}", reintentar=False)
            return

        etiqueta, vector = resultado
        if etiqueta is None:
            error_modelo = self._error_modelo()
            if error_modelo:
                mensaje = f"El modelo de {self._metodo} no está disponible:\n{error_modelo}"
            else:
                mensaje = (
                    f"Esta clase pide verificación por {self._metodo}, pero no tiene una "
                    f"{self._metodo} registrada para la clase ni vinculada a su cuenta.\n\n"
                    f"Entre con su contraseña y regístrela en la configuración de la clase."
                )
            self._fallo(mensaje, reintentar=False)
            return

        self._referencia = (etiqueta, vector)
        self._capturar()

    def _capturar(self):
        if self._metodo == "voz":
            self._capturar_voz()
        else:
            self._capturar_postura()

    def _capturar_voz(self):
        from interfaces.dialogo_voz import DialogoVoz
        from utils.reconocimiento_voz import ReconocedorVoz

        etiqueta, vector = self._referencia
        # La grabación no bloquea: DialogoVoz usa un buffer asíncrono y un QTimer
        audio = DialogoVoz.obtener_audio(
            self.ventana, etiqueta, SEGUNDOS_GRABACION_VOZ,
            f"🎤 Acceso a «{self.clase['nombre']}»"
        )
        if audio is None:
            return  # el usuario canceló

        ejecutar_en_hilo(
            self.ventana, ReconocedorVoz.verificar_palabra, (audio, etiqueta, None, vector),
            self._con_resultado, "Verificando su voz..."
        )

    def _capturar_postura(self):
        from utils.reconocimiento_pose import ReconocedorPose

        etiqueta, vector = self._referencia

        def al_capturar(frames):
            ejecutar_en_hilo(
                self.ventana, ReconocedorPose.verificar_pose,
                (frames, etiqueta, UMBRAL_CONFIANZA_VERIFICACION_POSE, vector),
                self._con_resultado, "Verificando su postura..."
            )

        try:
            self._ventana_pose = abrir_camara_pose(
                self.ventana,
                f"🧍 Acceso a «{self.clase['nombre']}»",
                "Haga su postura registrada frente a la cámara",
                al_capturar,
            )
        except Exception as error:
            self._fallo(f"No se pudo abrir la cámara:\n{error}", reintentar=False)

    def _con_resultado(self, resultado, error):
        if error is not None:
            self._fallo(f"Ocurrió un error al analizar la {self._metodo}:\n{error}")
            return

        ok, _, confianza, mensaje = resultado
        if not ok:
            print(f"[Clases] ❌ Verificación de {self._metodo} fallida para '{self.usuario}': {mensaje}")
            self._fallo(mensaje)
            return

        print(f"[Clases] ✅ {self._metodo} verificada para '{self.usuario}' ({confianza * 100:.1f}%)")
        self._aprobados.append(f"{self._metodo.capitalize()} ({confianza * 100:.1f}%)")
        self._pendientes.pop(0)
        self._siguiente()

    def _error_modelo(self):
        try:
            if self._metodo == "voz":
                from utils.reconocimiento_voz import ReconocedorVoz as Reconocedor
            else:
                from utils.reconocimiento_pose import ReconocedorPose as Reconocedor
            return Reconocedor._error_carga
        except Exception as error:
            return str(error)

    # -------------------------------------------------
    # Fallos y respaldo con contraseña
    # -------------------------------------------------

    def _fallo(self, mensaje, reintentar=True):
        caja = QMessageBox(self.ventana)
        caja.setIcon(QMessageBox.Warning)
        caja.setWindowTitle(f"Verificación por {self._metodo} no superada")
        caja.setText(mensaje)
        caja.setInformativeText("¿Qué desea hacer?")
        btn_reintentar = caja.addButton("🔁 Reintentar", QMessageBox.AcceptRole) if reintentar else None
        btn_contrasena = caja.addButton("🔒 Usar contraseña", QMessageBox.ActionRole)
        caja.addButton("Cancelar", QMessageBox.RejectRole)
        caja.exec_()

        pulsado = caja.clickedButton()
        if btn_reintentar is not None and pulsado is btn_reintentar:
            self._capturar()
        elif pulsado is btn_contrasena:
            self._pedir_contrasena()

    def _pedir_contrasena(self, intentos=3):
        for intento in range(1, intentos + 1):
            texto, aceptado = QInputDialog.getText(
                self.ventana,
                "🔒 Acceso con contraseña",
                f"Escriba la contraseña de '{self.usuario}' para entrar a «{self.clase['nombre']}»:",
                QLineEdit.Password,
            )
            if not aceptado:
                return

            try:
                ok, _ = UsuarioController.iniciar_sesion(self.usuario, texto)
            except Exception as error:
                Mensajes.error(self.ventana, "Error", f"No se pudo validar la contraseña:\n{error}")
                return

            if ok:
                self.al_conceder("Contraseña")
                return

            restantes = intentos - intento
            if restantes:
                Mensajes.advertencia(self.ventana, "Contraseña Incorrecta",
                                     f"La contraseña no es correcta. Le quedan {restantes} intento(s).")

        Mensajes.error(self.ventana, "Acceso Denegado",
                       "Se agotaron los intentos. Vuelva a abrir la clase para intentarlo de nuevo.")


# =====================================================
# VENTANA: DETALLE Y CONFIGURACIÓN DE LA CLASE
# =====================================================

class VentanaClase(QDialog):
    """Muestra la clase (código, miembros) y la configuración de acceso del usuario."""

    def __init__(self, parent, clase_id, usuario_id, usuario, metodo_acceso="", oscuro=False):
        super().__init__(parent)
        self.clase_id = clase_id
        self.usuario_id = usuario_id
        self.usuario = usuario
        self.oscuro = oscuro
        self._ventana_pose = None

        self.clase = ClaseController.obtener_clase(clase_id, usuario_id)

        self.setWindowTitle(f"🏫 {self.clase['nombre'] if self.clase else 'Clase'}")
        self.setMinimumSize(560, 600)
        self.setModal(True)
        aplicar_estilo(self, oscuro)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(12)

        if self.clase is None:
            lay.addWidget(QLabel("No se encontró la clase o ya no pertenece a ella."))
            return

        # --- Encabezado ---
        fila_titulo = QHBoxLayout()
        titulo = QLabel(f"🏫 {self.clase['nombre']}")
        titulo.setObjectName("tituloDialogo")
        titulo.setWordWrap(True)
        rol = QLabel("👩‍🏫 Docente" if self.clase["rol"] == "docente" else "🎓 Estudiante")
        rol.setObjectName("pillRolClase")
        fila_titulo.addWidget(titulo, 1)
        fila_titulo.addWidget(rol, 0, Qt.AlignTop)
        lay.addLayout(fila_titulo)

        desc = QLabel(self.clase["descripcion"] or "Sin descripción.")
        desc.setObjectName("subDialogo")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        if metodo_acceso:
            acceso = QLabel(f"✓ Acceso verificado: {metodo_acceso}")
            acceso.setStyleSheet(f"color: {color_tema(COLOR_OK, oscuro)}; font-weight: bold;")
            lay.addWidget(acceso)

        # --- Código de acceso ---
        tarjeta_codigo = QFrame()
        tarjeta_codigo.setObjectName("tarjeta")
        tc = QHBoxLayout(tarjeta_codigo)
        tc.setContentsMargins(16, 10, 16, 10)
        info_codigo = QVBoxLayout()
        lbl_cod = QLabel("Código de acceso")
        lbl_cod.setObjectName("subDialogo")
        codigo = QLabel(self.clase["codigo_acceso"])
        codigo.setObjectName("codigo")
        codigo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_codigo.addWidget(lbl_cod)
        info_codigo.addWidget(codigo)
        btn_copiar = QPushButton("📋 Copiar")
        btn_copiar.setObjectName("btnSecundario")
        btn_copiar.setCursor(Qt.PointingHandCursor)
        btn_copiar.clicked.connect(lambda: self._copiar_codigo(btn_copiar))
        tc.addLayout(info_codigo, 1)
        tc.addWidget(btn_copiar)
        lay.addWidget(tarjeta_codigo)

        # --- Miembros ---
        miembros = ClaseController.miembros(clase_id)
        lbl_miembros = QLabel(f"👥 Miembros ({len(miembros)})")
        lbl_miembros.setObjectName("seccion")
        lista = QListWidget()
        lista.setFixedHeight(110)
        for m in miembros:
            icono = "👩‍🏫" if m["rol"] == "docente" else "🎓"
            lista.addItem(f"{icono}  {m['nombre']}  (@{m['usuario']}) — {m['rol'].capitalize()}")
        lay.addWidget(lbl_miembros)
        lay.addWidget(lista)

        # --- Mi acceso a la clase ---
        lbl_config = QLabel("🔐 Mi acceso a esta clase")
        lbl_config.setObjectName("seccion")
        lay.addWidget(lbl_config)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        grid = QGridLayout(tarjeta)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)

        self.chkVoz = QCheckBox("🎤 Pedir mi voz al abrir esta clase")
        self.chkPostura = QCheckBox("🧍 Pedir mi postura al abrir esta clase")
        self.lblEstadoVoz = QLabel()
        self.lblEstadoPostura = QLabel()
        for lbl in (self.lblEstadoVoz, self.lblEstadoPostura):
            lbl.setWordWrap(True)

        btn_voz = QPushButton("🎤 Registrar voz")
        btn_voz.setObjectName("btnVoz")
        btn_voz.setCursor(Qt.PointingHandCursor)
        btn_pose = QPushButton("🧍 Registrar postura")
        btn_pose.setObjectName("btnPose")
        btn_pose.setCursor(Qt.PointingHandCursor)

        grid.addWidget(self.chkVoz, 0, 0)
        grid.addWidget(btn_voz, 0, 1, 2, 1, Qt.AlignVCenter)
        grid.addWidget(self.lblEstadoVoz, 1, 0)
        grid.addWidget(self.chkPostura, 2, 0)
        grid.addWidget(btn_pose, 2, 1, 2, 1, Qt.AlignVCenter)
        grid.addWidget(self.lblEstadoPostura, 3, 0)
        lay.addWidget(tarjeta)

        lay.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnPrimario")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)
        fila_cerrar = QHBoxLayout()
        fila_cerrar.addStretch()
        fila_cerrar.addWidget(btn_cerrar)
        lay.addLayout(fila_cerrar)

        self._refrescar()

        self.chkVoz.toggled.connect(lambda activo: self._cambiar_metodo("voz", activo))
        self.chkPostura.toggled.connect(lambda activo: self._cambiar_metodo("postura", activo))
        btn_voz.clicked.connect(lambda: self._registrar("voz"))
        btn_pose.clicked.connect(lambda: self._registrar("postura"))

    # -------------------------------------------------
    # Estado de la configuración
    # -------------------------------------------------

    def _origen_biometria(self, metodo):
        """'clase', 'cuenta' o None según dónde haya voz/postura guardada (sin cargar modelos)."""
        sufijo = "voz" if metodo == "voz" else "pose"
        if campo(self._acceso, f"etiqueta_{sufijo}") and campo(self._acceso, f"embedding_{sufijo}"):
            return "clase"
        datos = UsuarioController.buscar_usuario(self.usuario)
        if campo(datos, f"etiqueta_{sufijo}") and campo(datos, f"embedding_{sufijo}"):
            return "cuenta"
        return None

    def _refrescar(self):
        self._acceso = ClaseController.acceso_usuario(self.clase_id, self.usuario_id)

        for metodo, chk, lbl, columna in (
            ("voz", self.chkVoz, self.lblEstadoVoz, "voz_habilitada"),
            ("postura", self.chkPostura, self.lblEstadoPostura, "postura_habilitada"),
        ):
            chk.blockSignals(True)
            chk.setChecked(bool(self._acceso and self._acceso[columna]))
            chk.blockSignals(False)

            origen = self._origen_biometria(metodo)
            if origen == "clase":
                texto, color = f"✓ {metodo.capitalize()} registrada para esta clase", COLOR_OK
            elif origen == "cuenta":
                texto, color = f"Se usará la {metodo} vinculada a su cuenta", COLOR_NEUTRO
            else:
                texto, color = f"⚠ Sin {metodo} registrada", COLOR_AVISO
            lbl.setText(texto)
            lbl.setStyleSheet(f"color: {color_tema(color, self.oscuro)}; font-size: 11px;")

    def _cambiar_metodo(self, metodo, activo):
        if activo and self._origen_biometria(metodo) is None:
            Mensajes.advertencia(
                self, f"{metodo.capitalize()} No Registrada",
                f"Primero registre su {metodo} con el botón 'Registrar {metodo}' "
                f"para poder pedirla al abrir la clase."
            )
            self._refrescar()
            return

        if not ClaseController.actualizar_metodos(
            self.clase_id, self.usuario_id, self.chkVoz.isChecked(), self.chkPostura.isChecked()
        ):
            Mensajes.error(self, "Error de Base de Datos", "No se pudo guardar la configuración de acceso.")
        self._refrescar()

    def _copiar_codigo(self, boton):
        QApplication.clipboard().setText(self.clase["codigo_acceso"])
        boton.setText("✓ Copiado")

    # -------------------------------------------------
    # Registro de voz / postura para la clase
    # -------------------------------------------------

    def _registrar(self, metodo):
        """Carga el modelo en un hilo y luego abre la captura del login en modo registro."""
        if metodo == "voz":
            from utils.reconocimiento_voz import ReconocedorVoz as Reconocedor
        else:
            from utils.reconocimiento_pose import ReconocedorPose as Reconocedor

        def con_modelo(_resultado, error):
            if error is not None:
                Mensajes.error(self, "Modelo No Disponible", f"No se pudo cargar el modelo de {metodo}:\n{error}")
                return
            if metodo == "voz":
                resultado = capturar_voz(self, SEGUNDOS_GRABACION_VOZ)
                if resultado is not None:
                    self._guardar(metodo, resultado)
            else:
                self._ventana_pose = capturar_pose(self, lambda res: self._guardar(metodo, res))

        ejecutar_en_hilo(self, Reconocedor.cargar_modelo, (), con_modelo,
                         f"Cargando el modelo de {metodo}...")

    def _guardar(self, metodo, resultado):
        etiqueta, vector, confianza = resultado
        tipo = "voz" if metodo == "voz" else "pose"
        if not ClaseController.guardar_biometria(self.clase_id, self.usuario_id, tipo, etiqueta, vector):
            Mensajes.error(self, "Error de Base de Datos",
                           f"No se pudo guardar la {metodo}. Intente nuevamente.")
            return

        Mensajes.informacion(
            self, f"{metodo.capitalize()} Registrada ✓",
            f"Su {metodo} quedó registrada para «{self.clase['nombre']}» "
            f"como '{etiqueta}' ({confianza * 100:.1f}% de confianza)."
        )

        columna = "voz_habilitada" if metodo == "voz" else "postura_habilitada"
        acceso = ClaseController.acceso_usuario(self.clase_id, self.usuario_id)
        if acceso is not None and not acceso[columna] and Mensajes.confirmar(
            self, "Activar Acceso", f"¿Desea que se le pida la {metodo} al abrir esta clase?"
        ):
            ClaseController.actualizar_metodos(
                self.clase_id, self.usuario_id,
                metodo == "voz" or bool(acceso["voz_habilitada"]),
                metodo == "postura" or bool(acceso["postura_habilitada"]),
            )
        self._refrescar()
