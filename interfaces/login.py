from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QToolButton,
    QFrame,
    QApplication,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPixmap, QIcon

import sys

from controllers.usuario_controller import UsuarioController
from utils.validaciones import Validaciones
from utils.mensajes import Mensajes
from utils.rutas import ruta_recurso
from utils.umbrales_biometria import INGRESO_RAPIDO_TM, UMBRAL_ROSTRO_SFACE, UMBRAL_ROSTRO_TM
from interfaces.captura_biometrica import (
    ESTILO_BOTONES_BIOMETRIA,
    SEGUNDOS_GRABACION_VOZ,
    UMBRAL_CONFIANZA_VERIFICACION_POSE,
    abrir_camara_pose,
    avisar_no_vinculado,
    biometria_vinculada,
    campo as _campo,
)

from controllers.seguridad_controller import SeguridadController
from utils import liveness

# El segundo factor (por defecto desactivado, o por rol) y las pruebas de vida se configuran
# en utils/liveness.py: REQUERIR_SEGUNDO_FACTOR, ROLES_CON_SEGUNDO_FACTOR, LIVENESS_*.


class Login(QWidget):

    # Login por postura (el umbral de voz está en ReconocedorVoz.UMBRAL_CONFIANZA)
    UMBRAL_CONFIANZA_POSE = UMBRAL_CONFIANZA_VERIFICACION_POSE
    SEGUNDOS_GRABACION_VOZ = SEGUNDOS_GRABACION_VOZ

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Software Matemático IA — Iniciar sesión")
        self.setWindowIcon(QIcon(ruta_recurso("images/logo.jpg")))
        self.setMinimumWidth(820)
        self.resize(920, 660)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)
        from utils.tema import instalar_modo_oscuro_al_mostrar
        instalar_modo_oscuro_al_mostrar(self)

        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI";
            }

            QFrame#brandPanel {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0B1437,
                    stop:1 #111D4A
                );
            }

            QLabel {
                color: #0F172A;
                background: transparent;
            }

            QLabel#brandTitle { color: white; font-size: 15px; font-weight: bold; }
            QLabel#brandSub   { color: rgba(255,255,255,0.55); font-size: 10px; }

            QLabel#headline   { color: white; font-size: 23px; font-weight: bold; }
            QLabel#tagline    { color: rgba(255,255,255,0.65); font-size: 12px; }

            QLabel#featureText { color: rgba(255,255,255,0.85); font-size: 12px; }
            QLabel#featureCheck {
                color: #93C5FD; font-size: 11px; font-weight: bold;
                background: rgba(147, 197, 253, 0.14);
                border: 1px solid rgba(147, 197, 253, 0.28);
                border-radius: 10px;
            }
            QLabel#brandFoot { color: rgba(255,255,255,0.35); font-size: 10px; }

            QLabel#formTitulo { color: #0F172A; font-size: 22px; font-weight: bold; }
            QLabel#formSub    { color: #64748B; font-size: 12px; }
            QLabel#lblCampo   { color: #334155; font-size: 12px; font-weight: bold; }

            QFrame#campo {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#campo[focado="true"] {
                border: 1.5px solid #2563EB;
                background: #F8FAFF;
            }

            QLineEdit {
                background: transparent;
                border: none;
                padding: 0;
                font-size: 13px;
                color: #0F172A;
            }

            QToolButton#btnOjo {
                background: transparent;
                border: none;
                padding: 4px;
                font-size: 14px;
                border-radius: 6px;
            }
            QToolButton#btnOjo:hover { background: #EEF2F7; }

            QPushButton#btnLogin {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#btnLogin:hover { background: #1D4ED8; }
            QPushButton#btnLogin:pressed { background: #1E40AF; }

            QPushButton#btnRegistrar {
                background: transparent;
                color: #2563EB;
                border: 1.5px solid #CBD5E1;
                border-radius: 10px;
                padding: 11px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnRegistrar:hover { background: #F0F6FF; border-color: #93C5FD; }

            QLabel#divisor { color: #94A3B8; font-size: 11px; }
            QFrame#linea { background: #E2E8F0; border: none; }

            QLabel#pieForm { color: #94A3B8; font-size: 10px; }

            QWidget#formPanel { background: #FFFFFF; }
        """ + ESTILO_BOTONES_BIOMETRIA)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._construir_panel_marca(root)
        self._construir_panel_formulario(root)

        # El alto mínimo lo dicta el contenido: así Qt nunca aplasta campos ni botones
        self.ensurePolished()
        self.setMinimumHeight(root.minimumSize().height())

    # =====================================================
    # PANEL IZQUIERDO: MARCA
    # =====================================================

    def _construir_panel_marca(self, root):

        panel = QFrame()
        panel.setObjectName("brandPanel")
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(420)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(34, 30, 34, 26)
        lay.setSpacing(10)

        # ---------- Logo ----------
        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)

        chip = QLabel()
        chip.setFixedSize(58, 58)
        chip.setAlignment(Qt.AlignCenter)
        chip.setStyleSheet("""
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 29px;
        """)

        from utils.logos import crear_logo_circular

        pixmap_circular = crear_logo_circular(
            ruta_recurso("images/logo.jpg"), 52
        )
        if not pixmap_circular.isNull():
            chip.setPixmap(pixmap_circular)
        else:
            chip.setText("\u2211")
            chip.setStyleSheet(chip.styleSheet() + """
                color: #FFFFFF; font-size: 24px; font-weight: bold;
            """)

        marca = QVBoxLayout()
        marca.setSpacing(1)
        t = QLabel("Software Matemático IA")
        t.setObjectName("brandTitle")
        s = QLabel("Suite educativa de matemáticas")
        s.setObjectName("brandSub")
        marca.addWidget(t)
        marca.addWidget(s)

        logo_row.addWidget(chip)
        logo_row.addLayout(marca)
        logo_row.addStretch()
        lay.addLayout(logo_row)

        lay.addStretch()

        # ---------- Mensaje principal ----------
        headline = QLabel("La matemática,\nmás clara que nunca.")
        headline.setObjectName("headline")

        tagline = QLabel(
            "Resuelve ecuaciones paso a paso, visualiza funciones\n"
            "y refuerza tu aprendizaje con ayuda inteligente."
        )
        tagline.setObjectName("tagline")

        lay.addWidget(headline)
        lay.addSpacing(6)
        lay.addWidget(tagline)

        lay.addStretch()

        # ---------- Caracteristicas ----------
        for texto in (
            "Resolución paso a paso con IA",
            "Gráficas interactivas en 2D y 3D",
            "Historial y seguimiento de ejercicios",
        ):
            fila = QHBoxLayout()
            fila.setSpacing(10)

            check = QLabel("\u2713")
            check.setObjectName("featureCheck")
            check.setFixedSize(20, 20)
            check.setAlignment(Qt.AlignCenter)

            lbl = QLabel(texto)
            lbl.setObjectName("featureText")

            fila.addWidget(check)
            fila.addWidget(lbl, 1)
            lay.addLayout(fila)
            lay.addSpacing(2)

        lay.addStretch()

        pie = QLabel("© Software Matemático IA \u2022 v1.1")
        pie.setObjectName("brandFoot")
        pie.setAlignment(Qt.AlignLeft)
        lay.addWidget(pie)

        root.addWidget(panel)

    # =====================================================
    # PANEL DERECHO: FORMULARIO
    # =====================================================

    def _construir_panel_formulario(self, root):

        panel = QWidget()
        panel.setObjectName("formPanel")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(64, 32, 64, 20)
        lay.setSpacing(6)

        titulo = QLabel("Bienvenido de nuevo")
        titulo.setObjectName("formTitulo")

        subtitulo = QLabel("Ingresa tus credenciales para continuar")
        subtitulo.setObjectName("formSub")

        lay.addWidget(titulo)
        lay.addWidget(subtitulo)
        lay.addSpacing(14)

        # ---------- Usuario ----------
        l1 = QLabel("USUARIO")
        l1.setObjectName("lblCampo")
        lay.addWidget(l1)
        lay.addSpacing(4)

        self.campoUsuario = QFrame()
        self.campoUsuario.setObjectName("campo")
        cu = QHBoxLayout(self.campoUsuario)
        cu.setContentsMargins(14, 10, 14, 10)
        cu.setSpacing(10)

        ico_u = QLabel("\U0001F464")
        ico_u.setStyleSheet("font-size: 14px;")

        self.txtUsuario = QLineEdit()
        self.txtUsuario.setPlaceholderText("Tu nombre de usuario")

        cu.addWidget(ico_u)
        cu.addWidget(self.txtUsuario, 1)

        lay.addWidget(self.campoUsuario)
        lay.addSpacing(8)

        # ---------- Contraseña ----------
        l2 = QLabel("CONTRASEÑA")
        l2.setObjectName("lblCampo")
        lay.addWidget(l2)
        lay.addSpacing(4)

        self.campoPassword = QFrame()
        self.campoPassword.setObjectName("campo")
        cp = QHBoxLayout(self.campoPassword)
        # Márgenes verticales menores: el botón del ojo es más alto que el texto y
        # así el campo queda de la misma altura que el de usuario
        cp.setContentsMargins(14, 5, 8, 5)
        cp.setSpacing(10)

        ico_p = QLabel("\U0001F512")
        ico_p.setStyleSheet("font-size: 14px;")

        self.txtPassword = QLineEdit()
        self.txtPassword.setPlaceholderText("Tu contraseña")
        self.txtPassword.setEchoMode(QLineEdit.Password)

        self.btnMostrarPassword = QToolButton()
        self.btnMostrarPassword.setObjectName("btnOjo")
        self.btnMostrarPassword.setText("\U0001F441")
        self.btnMostrarPassword.setCursor(Qt.PointingHandCursor)
        self.btnMostrarPassword.setToolTip("Mostrar contraseña")
        self.btnMostrarPassword.clicked.connect(
            self.mostrar_ocultar_password
        )

        cp.addWidget(ico_p)
        cp.addWidget(self.txtPassword, 1)
        cp.addWidget(self.btnMostrarPassword)

        lay.addWidget(self.campoPassword)
        lay.addSpacing(16)

        # ---------- Botones ----------
        self.btnLogin = QPushButton("Iniciar Sesión")
        self.btnLogin.setObjectName("btnLogin")
        self.btnLogin.setCursor(Qt.PointingHandCursor)

        self.btnFacial = QPushButton("📷 Rostro")
        self.btnFacial.setObjectName("btnFacial")
        self.btnFacial.setCursor(Qt.PointingHandCursor)
        self.btnFacial.setToolTip("Iniciar sesión automáticamente mediante tu rostro")

        self.btnVoz = QPushButton("🎤 Voz")
        self.btnVoz.setObjectName("btnVoz")
        self.btnVoz.setCursor(Qt.PointingHandCursor)
        self.btnVoz.setToolTip("Di tu palabra de ingreso (escribir tu usuario antes la hace más precisa)")

        self.btnPose = QPushButton("🧍 Postura")
        self.btnPose.setObjectName("btnPose")
        self.btnPose.setCursor(Qt.PointingHandCursor)
        self.btnPose.setToolTip("Haz tu postura de ingreso frente a la cámara (escribir tu usuario antes la hace más precisa)")

        self.btnRegistrar = QPushButton("Crear una cuenta")
        self.btnRegistrar.setObjectName("btnRegistrar")
        self.btnRegistrar.setCursor(Qt.PointingHandCursor)

        # Rejilla de métodos biométricos: 3 columnas, o 2 si el panel es angosto
        self._botones_biometria = [self.btnFacial, self.btnVoz, self.btnPose]
        self._columnas_biometria = 0
        self.gridBiometria = QGridLayout()
        self.gridBiometria.setHorizontalSpacing(10)
        self.gridBiometria.setVerticalSpacing(10)
        self._reorganizar_botones_biometria(3)

        divisor_bio = QHBoxLayout()
        divisor_bio.setSpacing(12)
        for texto in (None, "o ingresa con biometría", None):
            if texto is None:
                linea = QFrame()
                linea.setObjectName("linea")
                linea.setFixedHeight(1)
                divisor_bio.addWidget(linea)
            else:
                lbl = QLabel(texto)
                lbl.setObjectName("divisor")
                divisor_bio.addWidget(lbl)

        divisor_row = QHBoxLayout()
        divisor_row.setSpacing(12)
        linea_i = QFrame()
        linea_i.setObjectName("linea")
        linea_i.setFixedHeight(1)
        linea_d = QFrame()
        linea_d.setObjectName("linea")
        linea_d.setFixedHeight(1)
        lbl_div = QLabel("¿No tienes una cuenta?")
        lbl_div.setObjectName("divisor")
        divisor_row.addWidget(linea_i)
        divisor_row.addWidget(lbl_div)
        divisor_row.addWidget(linea_d)

        pie = QLabel("Al iniciar sesión accedes a tu espacio personal de estudio.")
        pie.setObjectName("pieForm")
        pie.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.btnLogin)
        lay.addSpacing(8)
        lay.addLayout(divisor_bio)
        lay.addSpacing(2)
        lay.addLayout(self.gridBiometria)
        lay.addSpacing(10)
        lay.addLayout(divisor_row)
        lay.addSpacing(2)
        lay.addWidget(self.btnRegistrar)

        # Botón secundario para vincular rostro a cuenta existente
        self.btnVincularRostro = QPushButton("🔗 Vincular mi Biometría (cuenta existente)")
        self.btnVincularRostro.setObjectName("btnVincularRostro")
        self.btnVincularRostro.setCursor(Qt.PointingHandCursor)
        self.btnVincularRostro.setToolTip(
            "Si ya tienes cuenta, vincula aquí tu rostro, tu voz y tu postura usando tu usuario y contraseña."
        )
        self.btnVincularRostro.setStyleSheet("""
            QPushButton#btnVincularRostro {
                background: transparent;
                color: #0D9488;
                border: 1.5px solid #99F6E4;
                border-radius: 10px;
                padding: 9px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnVincularRostro:hover { background: #F0FDFA; border-color: #2DD4BF; }
        """)
        lay.addSpacing(2)
        lay.addWidget(self.btnVincularRostro)

        lay.addStretch()

        lay.addWidget(pie)

        root.addWidget(panel, 1)

        # =====================================================
        # CONEXIONES Y COMPORTAMIENTO
        # =====================================================

        self.btnLogin.clicked.connect(
            self.iniciar_sesion
        )

        self.btnFacial.clicked.connect(
            self.iniciar_sesion_facial
        )

        self.btnVoz.clicked.connect(
            self.iniciar_sesion_voz
        )

        self.btnPose.clicked.connect(
            self.iniciar_sesion_pose
        )

        self.btnRegistrar.clicked.connect(
            self.abrir_registro
        )

        self.btnVincularRostro.clicked.connect(
            self.vincular_rostro_cuenta_existente
        )

        self.txtUsuario.returnPressed.connect(
            self.txtPassword.setFocus
        )

        self.txtPassword.returnPressed.connect(
            self.iniciar_sesion
        )

        # Anillo de foco en los campos
        self.txtUsuario.installEventFilter(self)
        self.txtPassword.installEventFilter(self)

    # =====================================================
    # FOCO VISUAL DE CAMPOS
    # =====================================================

    # =====================================================
    # REJILLA RESPONSIVE DE BOTONES BIOMÉTRICOS
    # =====================================================

    def _reorganizar_botones_biometria(self, columnas):
        if columnas == self._columnas_biometria:
            return
        self._columnas_biometria = columnas
        for boton in self._botones_biometria:
            self.gridBiometria.removeWidget(boton)
            # Columnas de igual ancho: ignorar el ancho mínimo del texto de cada botón
            boton.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        total = len(self._botones_biometria)
        for i, boton in enumerate(self._botones_biometria):
            fila, columna = divmod(i, columnas)
            # El último botón de una fila incompleta ocupa el resto de la fila
            ancho = columnas - columna if i == total - 1 else 1
            self.gridBiometria.addWidget(boton, fila, columna, 1, ancho)
        for c in range(3):
            self.gridBiometria.setColumnStretch(c, 1 if c < columnas else 0)
        # 2 columnas agregan una fila: actualizar el alto mínimo para no aplastar el formulario
        if self.layout() is not None:
            self.layout().activate()
            self.setMinimumHeight(self.layout().minimumSize().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 3 columnas solo si el botón más ancho cabe tres veces en el ancho disponible
        espacio = self.gridBiometria.horizontalSpacing()
        mas_ancho = max(b.sizeHint().width() for b in self._botones_biometria)
        disponible = self.btnLogin.width()
        self._reorganizar_botones_biometria(3 if disponible >= 3 * mas_ancho + 2 * espacio else 2)

    def eventFilter(self, obj, event):

        if obj is self.txtUsuario or obj is self.txtPassword:

            campo = (
                self.campoUsuario if obj is self.txtUsuario
                else self.campoPassword
            )

            if event.type() == QEvent.FocusIn:
                campo.setProperty("focado", True)
            elif event.type() == QEvent.FocusOut:
                campo.setProperty("focado", False)

            campo.style().unpolish(campo)
            campo.style().polish(campo)

        return super().eventFilter(obj, event)

    # =====================================================
    # MOSTRAR / OCULTAR CONTRASEÑA
    # =====================================================

    def mostrar_ocultar_password(self):

        if self.txtPassword.echoMode() == QLineEdit.Password:

            # Mostrar contraseña
            self.txtPassword.setEchoMode(
                QLineEdit.Normal
            )

            self.btnMostrarPassword.setText("🙈")

            self.btnMostrarPassword.setToolTip(
                "Ocultar contraseña"
            )

        else:

            # Ocultar contraseña
            self.txtPassword.setEchoMode(
                QLineEdit.Password
            )

            self.btnMostrarPassword.setText("\U0001F441")

            self.btnMostrarPassword.setToolTip(
                "Mostrar contraseña"
            )

    # =====================================================
    # INICIAR SESIÓN
    # =====================================================

    def iniciar_sesion(self):

        usuario = self.txtUsuario.text().strip()
        password = self.txtPassword.text().strip()

        # -------------------------------------------------
        # Validar usuario
        # -------------------------------------------------

        if Validaciones.campo_vacio(usuario):

            Mensajes.campo_vacio(self)

            self.txtUsuario.setFocus()

            return

        # -------------------------------------------------
        # Validar contraseña
        # -------------------------------------------------

        if Validaciones.campo_vacio(password):

            Mensajes.campo_vacio(self)

            self.txtPassword.setFocus()

            return

        try:

            ok, datos = UsuarioController.iniciar_sesion(
                usuario,
                password
            )

            # -------------------------------------------------
            # Login correcto
            # -------------------------------------------------

            # La contraseña nunca se bloquea (es el respaldo), pero queda registrada
            SeguridadController.registrar_intento(
                "contraseña", ok, "" if ok else "Contraseña incorrecta", usuario
            )

            if ok:

                from interfaces.menu import MenuPrincipal

                self.menu = MenuPrincipal(
                    datos["nombre"],
                    datos["usuario"]
                )

                self.menu.show()

                self.close()

            # -------------------------------------------------
            # Login incorrecto
            # -------------------------------------------------

            else:

                Mensajes.contraseña_incorrecta(
                    self
                )

                self.txtPassword.clear()

                self.txtPassword.setFocus()

        except Exception as error:

            Mensajes.error(
                self,
                "Error",
                str(error)
            )

    # =====================================================
    # ABRIR REGISTRO
    # =====================================================

    def abrir_registro(self):

        from interfaces.registro import Registro

        self.registro = Registro()

        self.registro.show()

        self.close()

    # =====================================================
    # VINCULAR ROSTRO A CUENTA EXISTENTE
    # =====================================================

    def vincular_rostro_cuenta_existente(self):
        """
        Permite a un usuario ya registrado vincular su rostro sin crear
        una nueva cuenta. Pide usuario + contraseña, valida credenciales
        y luego permite elegir qué vincular: rostro (embedding SFace),
        voz y postura (clases de los modelos de Teachable Machine).
        """
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QLabel
        from PyQt5.QtCore import Qt as _Qt

        dlg = QDialog(self)
        dlg.setWindowTitle("🔗 Vincular Biometría a Cuenta Existente")
        dlg.setMinimumWidth(360)
        dlg.setStyleSheet("QDialog { background: #F8FAFC; font-family: 'Segoe UI'; }")

        form = QFormLayout(dlg)
        form.setContentsMargins(24, 20, 24, 16)
        form.setSpacing(12)

        lbl_info = QLabel(
            "Ingrese su usuario y contraseña para verificar su identidad\n"
            "y luego vincule su rostro, su voz y/o su postura a su cuenta."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #475569; font-size: 12px;")
        form.addRow(lbl_info)

        txt_usr = QLineEdit()
        txt_usr.setPlaceholderText("Usuario")
        form.addRow("Usuario:", txt_usr)

        txt_pwd = QLineEdit()
        txt_pwd.setPlaceholderText("Contraseña")
        txt_pwd.setEchoMode(QLineEdit.Password)
        form.addRow("Contraseña:", txt_pwd)

        # Prellenar si el usuario ya escribió su nombre en el campo principal
        if self.txtUsuario.text().strip():
            txt_usr.setText(self.txtUsuario.text().strip())
            txt_pwd.setFocus()

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Verificar y Continuar")
        botones.accepted.connect(dlg.accept)
        botones.rejected.connect(dlg.reject)
        form.addRow(botones)

        if dlg.exec_() != QDialog.Accepted:
            return

        usuario = txt_usr.text().strip()
        password = txt_pwd.text().strip()

        if not usuario or not password:
            Mensajes.campo_vacio(self)
            return

        # Verificar credenciales
        ok_cred, datos_cred = UsuarioController.iniciar_sesion(usuario, password)
        if not ok_cred:
            Mensajes.error(self, "Credenciales Incorrectas",
                           "El usuario o contraseña son incorrectos. No se puede vincular la biometría.")
            return

        self._dialogo_vincular_biometria(usuario)

    def _dialogo_vincular_biometria(self, usuario):
        """
        Tras verificar la contraseña, permite vincular cada método por separado: el rostro
        con el flujo de cámara de siempre, y la palabra y la postura de ingreso propias del
        usuario (interfaces/biometria_ingreso.py), guardadas como plantillas en la BD.
        """
        from PyQt5.QtWidgets import QDialog, QGridLayout
        from interfaces.biometria_ingreso import RegistroPostura, registrar_palabra_ingreso

        dlg = QDialog(self)
        dlg.setWindowTitle(f"🔗 Vincular Biometría — {usuario}")
        dlg.setMinimumWidth(440)
        dlg.setStyleSheet("""
            QDialog { background: #F8FAFC; font-family: 'Segoe UI'; }
            QLabel { color: #0F172A; font-size: 12px; }
            QLabel#infoVincular { color: #475569; }
            QPushButton#btnListo {
                background: transparent;
                color: #2563EB;
                border: 1.5px solid #CBD5E1;
                border-radius: 10px;
                padding: 9px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnListo:hover { background: #F0F6FF; border-color: #93C5FD; }
        """ + ESTILO_BOTONES_BIOMETRIA)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 20, 24, 16)
        lay.setSpacing(12)

        lbl_info = QLabel(
            "Elija qué desea vincular a su cuenta. Puede vincular uno, dos o los tres métodos "
            "y volver a capturarlos cuando quiera."
        )
        lbl_info.setObjectName("infoVincular")
        lbl_info.setWordWrap(True)
        lay.addWidget(lbl_info)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        estados = {}
        for fila, (metodo, texto, nombre_obj) in enumerate((
            ("rostro", "📷 Rostro", "btnFacial"),
            ("voz", "🎤 Voz", "btnVoz"),
            ("postura", "🧍 Postura", "btnPose"),
        )):
            boton = QPushButton(texto)
            boton.setObjectName(nombre_obj)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setMinimumWidth(130)
            estado = QLabel()
            estado.setWordWrap(True)
            estados[metodo] = estado
            grid.addWidget(boton, fila, 0)
            grid.addWidget(estado, fila, 1)
            boton.clicked.connect(lambda _=False, m=metodo: acciones[m]())
        lay.addLayout(grid)

        btn_listo = QPushButton("Listo")
        btn_listo.setObjectName("btnListo")
        btn_listo.setCursor(Qt.PointingHandCursor)
        btn_listo.clicked.connect(dlg.accept)
        lay.addSpacing(4)
        lay.addWidget(btn_listo)

        def refrescar():
            datos = UsuarioController.buscar_usuario(usuario)
            if INGRESO_RAPIDO_TM:
                vinculados = {
                    "rostro": _campo(datos, "clase_tm_rostro") and "escaneo rápido",
                    "voz": _campo(datos, "clase_tm_voz") and "escaneo rápido",
                    "postura": "postura de ingreso" if _campo(datos, "plantilla_postura") else "",
                }
            else:
                vinculados = {
                "rostro": (_campo(datos, "embedding_facial") or _campo(datos, "etiqueta_facial")) and "rostro",
                "voz": ("palabra de ingreso" if _campo(datos, "plantilla_voz") else
                        _campo(datos, "embedding_voz") and _campo(datos, "etiqueta_voz")
                        and f"{_campo(datos, 'etiqueta_voz')}, sistema anterior"),
                "postura": ("postura de ingreso" if _campo(datos, "plantilla_postura") else
                            _campo(datos, "embedding_pose") and _campo(datos, "etiqueta_pose")
                            and f"{_campo(datos, 'etiqueta_pose')}, sistema anterior"),
                }
            for metodo, estado in estados.items():
                valor = vinculados[metodo]
                if valor:
                    detalle = "" if valor == "rostro" else f" ({valor})"
                    estado.setText(f"✓ Vinculado{detalle}")
                    estado.setStyleSheet("color: #059669; font-weight: bold;")
                else:
                    estado.setText("Sin vincular")
                    estado.setStyleSheet("color: #64748B;")

        def vincular_voz():
            def guardar(palabra, plantilla):
                self._avisar_guardado(dlg, "palabra", UsuarioController.guardar_palabra_ingreso(
                    usuario, palabra, plantilla))
                refrescar()
            registrar_palabra_ingreso(dlg, guardar, usuario_actual=usuario)

        def vincular_postura():
            def guardar(plantilla):
                self._avisar_guardado(dlg, "postura", UsuarioController.guardar_plantilla_postura(
                    usuario, plantilla))
                refrescar()
            dlg._registro_postura = RegistroPostura(dlg, guardar)
            dlg._registro_postura.iniciar()

        acciones = {
            "rostro": lambda: self._abrir_camara_vinculacion(usuario, dlg, refrescar),
            "voz": vincular_voz,
            "postura": vincular_postura,
        }
        if INGRESO_RAPIDO_TM:
            from interfaces import ingreso_tm
            acciones["rostro"] = lambda: ingreso_tm.vincular(dlg, usuario, "rostro", refrescar)
            acciones["voz"] = lambda: ingreso_tm.vincular(dlg, usuario, "voz", refrescar)

        refrescar()
        dlg.exec_()

    def _avisar_guardado(self, parent, que, guardado):
        """Avisa si la palabra o la postura de ingreso se guardaron en la BD."""
        boton = "🎤 Voz" if que == "palabra" else "🧍 Postura"
        if not guardado:
            Mensajes.error(parent, "Error de Base de Datos",
                           f"No se pudo guardar la {que} de ingreso. Intente nuevamente.")
            return
        Mensajes.informacion(
            parent, f"{que.capitalize()} de Ingreso Vinculada ✓",
            f"¡Su {que} de ingreso quedó vinculada!\n\n"
            f"A partir de ahora puede iniciar sesión con el botón '{boton}'."
        )

    def _abrir_camara_vinculacion(self, usuario, parent=None, al_terminar=None):
        # Abrir cámara para capturar el rostro
        try:
            from interfaces.camara import VentanaCamara
        except ImportError:
            Mensajes.error(self, "Error de Cámara", "No se pudo cargar el módulo de la cámara.")
            return

        self._usuario_vincular = usuario
        self.ventana_camara_vincular = VentanaCamara(parent or self)
        self.ventana_camara_vincular.modo_facial = True
        self.ventana_camara_vincular.setWindowTitle("📸 Captura de Rostro para Vinculación")
        self.ventana_camara_vincular.titulo.setText("Mire a la cámara para vincular su rostro")
        self.ventana_camara_vincular.lblEstado.setText(
            "Mantenga su rostro centrado y presione 'Capturar Foto'."
        )
        self.ventana_camara_vincular.foto_capturada.connect(self._procesar_vinculacion_rostro)
        if al_terminar is not None:
            self.ventana_camara_vincular.foto_capturada.connect(lambda *_: al_terminar())
        self.ventana_camara_vincular.show()

    def _procesar_vinculacion_rostro(self, datos_bytes, mime):
        """Procesa la imagen capturada y guarda el embedding en la BD."""
        if not datos_bytes:
            return

        try:
            import cv2
            import numpy as np
            from services.clasificador_imagen import ClasificadorImagen
        except ImportError as err:
            Mensajes.error(self, "Error", f"Faltan dependencias: {err}")
            return

        nparr = np.frombuffer(datos_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            Mensajes.error(self, "Error de Imagen", "No se pudo procesar la imagen de la cámara.")
            return

        # Detectar rostro
        hay_rostro, _, score, _, _ = ClasificadorImagen.detectar_rostro(frame)
        if not hay_rostro:
            Mensajes.advertencia(self, "Sin Rostro",
                                 "No se detectó ningún rostro en la imagen. Vuelva a intentarlo.")
            return

        # Extraer embedding SFace
        exito_emb, embedding, _, score_emb = ClasificadorImagen.extraer_embedding(frame)
        if not exito_emb or not embedding:
            Mensajes.advertencia(self, "Error Biométrico",
                                 "No se pudo extraer el vector biométrico del rostro. "
                                 "Asegúrese de estar bien iluminado y mire de frente.")
            return

        # Guardar en la BD
        usuario = getattr(self, "_usuario_vincular", "")
        guardado = UsuarioController.guardar_embedding_facial(usuario, embedding)
        if guardado:
            Mensajes.informacion(
                self,
                "Rostro Vinculado ✓",
                f"¡Rostro registrado correctamente para '{usuario}'!\n\n"
                f"A partir de ahora puede iniciar sesión usando únicamente\n"
                f"el botón '📷 Rostro' sin ingresar contraseña."
            )
            print(f"[Vinculación] Embedding guardado para '{usuario}' ({score_emb:.2f} confianza).")
        else:
            Mensajes.error(self, "Error de Base de Datos",
                           "No se pudo guardar el rostro en la base de datos. Intente nuevamente.")

    # =====================================================
    # INICIAR SESIÓN CON RECONOCIMIENTO FACIAL
    # =====================================================

    def iniciar_sesion_facial(self):

        if INGRESO_RAPIDO_TM:
            from interfaces import ingreso_tm
            ingreso_tm.ingresar(self, "rostro")
            return

        if liveness.LIVENESS_ROSTRO:
            self._iniciar_sesion_facial_con_vida()
            return

        try:
            from interfaces.camara import VentanaCamara
        except ImportError:
            Mensajes.error(
                self,
                "Error de Cámara",
                "No se pudo cargar el módulo de la cámara."
            )
            return

        self.ventana_camara = VentanaCamara(self)
        self.ventana_camara.modo_facial = True
        self.ventana_camara.setWindowTitle("📷 Autenticación por Reconocimiento Facial")
        self.ventana_camara.titulo.setText("Acerque su rostro a la cámara")
        self.ventana_camara.lblEstado.setText("Mire a la cámara y presione 'Capturar Foto'.")
        self.ventana_camara.foto_capturada.connect(self.procesar_login_facial)
        self.ventana_camara.show()

    def procesar_login_facial(self, datos_bytes, mime):

        if not datos_bytes:
            return

        try:
            import cv2
            import numpy as np
            from services.clasificador_imagen import ClasificadorImagen
        except ImportError as err:
            Mensajes.error(
                self,
                "Error de Clasificación",
                f"Faltan dependencias para el reconocimiento facial: {err}"
            )
            return

        # Decodificar imagen capturada a frame de OpenCV
        nparr = np.frombuffer(datos_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            Mensajes.error(
                self,
                "Error de Imagen",
                "No se pudo procesar la imagen capturada por la cámara."
            )
            return

        # ─── PASO 1: Verificar iluminación y presencia real de rostro ───────
        luz_ok, luminosidad, msg_luz = ClasificadorImagen.analizar_iluminacion(frame)
        if not luz_ok:
            Mensajes.advertencia(self, "Condición de Imagen", msg_luz)
            return

        hay_rostro, _, score_rostro, bbox, msg_rostro = ClasificadorImagen.detectar_rostro(frame)
        if not hay_rostro:
            Mensajes.advertencia(
                self,
                "Rostro No Detectado",
                "No se detectó ningún rostro frente a la cámara.\n"
                "Por favor, mire de frente con buena iluminación y vuelva a intentarlo."
            )
            return

        # ─── PASO 2: Autenticación 1:N usando embeddings SFace ──────────────
        # Extrae el vector biométrico de 128 dimensiones del rostro capturado
        exito_emb, embedding_nuevo, _, _ = ClasificadorImagen.extraer_embedding(frame)

        datos_usuario = None
        similitud_final = 0.0
        metodo_auth = ""

        if exito_emb and embedding_nuevo:
            ok_emb, resultado_emb = UsuarioController.buscar_por_embedding(
                embedding_nuevo, umbral=UMBRAL_ROSTRO_SFACE
            )
            if ok_emb:
                datos_usuario = resultado_emb
                similitud_final = resultado_emb.get("_similitud_facial", 0.0)
                metodo_auth = f"Biometría SFace ({similitud_final * 100:.1f}%)"
                print(f"[Login] ✅ Autenticación 1:N exitosa por embedding: '{datos_usuario['usuario']}'")
        else:
            print("[Login] ⚠️ No se pudo extraer embedding SFace. Usando Teachable Machine como respaldo.")

        # ─── PASO 3: Fallback – Teachable Machine + nombre de usuario escrito ─
        if datos_usuario is None:
            usuario_ingresado = self.txtUsuario.text().strip()
            if usuario_ingresado:
                exito_tm, usuario_tm, conf_tm, msg_tm = ClasificadorImagen.validar_rostro(
                    frame,
                    usuario_esperado=usuario_ingresado,
                    umbral_confianza=UMBRAL_ROSTRO_TM
                )
                if exito_tm:
                    ok_db, resultado_db = UsuarioController.iniciar_sesion_por_rostro(usuario_ingresado)
                    if ok_db:
                        datos_usuario = resultado_db
                        similitud_final = conf_tm
                        metodo_auth = f"Teachable Machine ({conf_tm * 100:.1f}%)"
                        print(f"[Login] ✅ Autenticación TM exitosa: '{usuario_ingresado}'")
                    else:
                        Mensajes.advertencia(self, "Usuario No Encontrado", resultado_db)
                        return
                else:
                    datos_ingresado = UsuarioController.buscar_usuario(usuario_ingresado)
                    if datos_ingresado is not None and not (
                        _campo(datos_ingresado, "embedding_facial") or _campo(datos_ingresado, "etiqueta_facial")
                    ):
                        avisar_no_vinculado(self, usuario_ingresado, "rostro")
                    else:
                        Mensajes.advertencia(self, "Reconocimiento Facial Fallido", msg_tm)
                    return
            else:
                # Sin usuario escrito y sin embedding → informar al usuario
                Mensajes.advertencia(
                    self,
                    "Reconocimiento Facial Fallido",
                    "No se encontró ningún usuario registrado que coincida con su rostro.\n\n"
                    "Posibles causas:\n"
                    "• No registró su rostro al crear la cuenta.\n"
                    "• Las condiciones de iluminación son muy diferentes al registro.\n"
                    "• Intente escribir su nombre de usuario y vuelva a intentarlo."
                )
                return

        # El segundo factor (si está activo o lo exige el rol) se pide en _conceder_acceso;
        # _verificar_segundo_factor_voz se conserva por si se quiere volver a usar la voz.
        self._conceder_acceso(datos_usuario, metodo_auth, "reconocimiento facial")

    # =====================================================
    # PRUEBA DE VIDA: ROSTRO, BLOQUEO Y REGISTRO DE INTENTOS
    # =====================================================

    def _iniciar_sesion_facial_con_vida(self):
        """
        Rostro con desafío aleatorio (parpadear, girar, sonreír, abrir la boca) verificado con
        la malla facial, identidad sostenida y anti-spoofing. 1:1 si hay usuario escrito; si no,
        se identifica entre todos los usuarios con rostro vinculado.
        """
        import json
        from interfaces.dialogo_liveness import DialogoDesafioCamara

        if not self._puede_intentar():
            return

        usuario = self.txtUsuario.text().strip()
        datos = None
        if usuario:
            datos = UsuarioController.buscar_usuario(usuario)
            if datos is None:
                Mensajes.advertencia(self, "Usuario No Encontrado",
                                     f"El usuario '{usuario}' no está registrado en la base de datos.")
                return
            try:
                embedding = json.loads(_campo(datos, "embedding_facial") or "null")
            except ValueError:
                embedding = None
            if not embedding:
                avisar_no_vinculado(self, usuario, "rostro")
                return
            desafio = liveness.DesafioRostro(embedding_esperado=embedding)
        else:
            candidatos = []
            for fila in UsuarioController.usuarios_con_rostro():
                try:
                    candidatos.append((dict(fila), json.loads(fila["embedding_facial"])))
                except (ValueError, TypeError):
                    continue
            if not candidatos:
                Mensajes.advertencia(self, "Sin Rostros Vinculados",
                                     "Ningún usuario tiene su rostro vinculado. Use '🔗 Vincular mi Biometría'.")
                return
            desafio = liveness.DesafioRostro(candidatos=candidatos)

        resultado, error = DialogoDesafioCamara.ejecutar(
            self, "📷 Ingreso por Rostro", desafio, getattr(self, "_modo_oscuro", False))

        if error:
            self._fallo_facial(error, usuario)
        elif resultado is None:
            return  # cancelado por el usuario
        elif resultado.estado == "aprobado":
            datos_final = datos if datos is not None else resultado.datos["usuario"]
            similitud = resultado.datos["similitud"]
            print(f"[Login] ✅ Rostro con prueba de vida: '{datos_final['usuario']}' "
                  f"(acciones: {resultado.datos['acciones']}, similitud {similitud:.3f})")
            self._conceder_acceso(datos_final, f"Rostro + prueba de vida ({similitud * 100:.1f}%)",
                                  "reconocimiento facial con prueba de vida")
        else:
            self._fallo_facial(resultado.detalle, usuario)

    def _fallo_facial(self, motivo, usuario):
        from interfaces.biometria_ingreso import mostrar_fallo_biometrico

        print(f"[Login] ❌ Rostro con prueba de vida fallido: {motivo}")
        self._registrar_fallo("rostro", motivo, usuario)
        mostrar_fallo_biometrico(self, "rostro", motivo, self.iniciar_sesion_facial, self._usar_contrasena)

    def _puede_intentar(self):
        """False (y avisa) si hay un bloqueo temporal por intentos fallidos seguidos."""
        if not liveness.BLOQUEO_BIOMETRICO_ACTIVO:
            return True
        segundos = SeguridadController.segundos_bloqueo(
            liveness.INTENTOS_ANTES_DE_BLOQUEO, liveness.BLOQUEO_BASE_SEGUNDOS, liveness.BLOQUEO_MAXIMO_SEGUNDOS
        )
        if segundos <= 0:
            return True
        Mensajes.advertencia(
            self, "Ingreso Biométrico Bloqueado",
            f"Hubo {liveness.INTENTOS_ANTES_DE_BLOQUEO} intentos fallidos seguidos.\n"
            f"Espere {segundos} segundos para volver a intentarlo, o entre con su contraseña."
        )
        self.txtPassword.setFocus()
        return False

    @staticmethod
    def _registrar_fallo(metodo, motivo, usuario=""):
        SeguridadController.registrar_intento(metodo, False, motivo, usuario)

    def _segundo_factor_superado(self, datos_usuario):
        """
        Si el segundo factor está activo (o el rol del usuario lo exige), pide la contraseña
        tras el método biométrico. Devuelve True si no hace falta o si se superó.
        """
        from PyQt5.QtWidgets import QInputDialog, QLineEdit

        usuario = datos_usuario["usuario"]
        por_rol = "docente" in liveness.ROLES_CON_SEGUNDO_FACTOR and UsuarioController.es_docente(usuario)
        if not (liveness.REQUERIR_SEGUNDO_FACTOR or por_rol):
            return True

        for _ in range(3):
            texto, aceptado = QInputDialog.getText(
                self, "🔒 Segundo factor",
                f"Su cuenta requiere además la contraseña de '{usuario}':", QLineEdit.Password)
            if not aceptado:
                return False
            if UsuarioController.iniciar_sesion(usuario, texto)[0]:
                return True
            Mensajes.advertencia(self, "Contraseña Incorrecta", "La contraseña no es correcta.")
        self._registrar_fallo("segundo factor", "Contraseña incorrecta en el segundo factor", usuario)
        return False

    def _verificar_segundo_factor_voz(self, datos_usuario):
        """
        Si el usuario tiene una palabra de voz vinculada, la pide como segundo factor.
        Devuelve (ok, descripcion): ok=False si falló o se canceló; descripcion vacía
        si el usuario no tiene factor de voz o el modelo no está disponible.
        """
        try:
            from utils.reconocimiento_voz import ReconocedorVoz
            from interfaces.dialogo_voz import DialogoVoz
        except Exception as err:
            print(f"[Login] ⚠️ Verificación por voz no disponible: {err}")
            return True, ""

        clase_voz, vector_voz = self._biometria_vinculada(datos_usuario, "voz")
        if clase_voz is None:
            if ReconocedorVoz._error_carga:
                print(f"[Login] ⚠️ Modelo de voz no cargado ({ReconocedorVoz._error_carga}). Se omite el factor de voz.")
            return True, ""

        audio = DialogoVoz.obtener_audio(
            self, clase_voz, self.SEGUNDOS_GRABACION_VOZ, "🎤 Segundo Factor: Verificación por Voz"
        )
        if audio is None:
            Mensajes.advertencia(
                self,
                "Verificación por Voz Cancelada",
                "Su rostro fue reconocido, pero esta cuenta exige además la verificación por voz.\n"
                "Puede iniciar sesión con usuario y contraseña."
            )
            return False, ""

        ok, _, confianza, mensaje = ReconocedorVoz.verificar_palabra(
            audio, clase_voz, vector_referencia=vector_voz
        )
        if not ok:
            print(f"[Login] ❌ Verificación por voz fallida para '{datos_usuario['usuario']}': {mensaje}")
            Mensajes.advertencia(self, "Verificación por Voz Fallida", mensaje)
            return False, ""

        print(f"[Login] ✅ Voz verificada para '{datos_usuario['usuario']}' ({confianza * 100:.1f}%)")
        return True, f"Voz ({confianza * 100:.1f}%)"

    # =====================================================
    # INICIAR SESIÓN POR VOZ / POSTURA
    # =====================================================

    def _usuario_para_biometria(self, metodo):
        """
        Igual que el respaldo de Teachable Machine del login facial: la clase detectada
        se compara con el usuario escrito. Devuelve los datos del usuario o None.
        """
        usuario = self.txtUsuario.text().strip()
        if not usuario:
            Mensajes.advertencia(
                self,
                "Usuario Requerido",
                f"Escriba su nombre de usuario y vuelva a pulsar el botón de {metodo}."
            )
            self.txtUsuario.setFocus()
            return None

        datos = UsuarioController.buscar_usuario(usuario)
        if datos is None:
            Mensajes.advertencia(
                self,
                "Usuario No Encontrado",
                f"El usuario '{usuario}' no está registrado en la base de datos."
            )
            return None
        return datos

    def _avisar_biometria_no_vinculada(self, datos_usuario, metodo, error_carga):
        if error_carga:
            Mensajes.error(self, "Modelo No Disponible", f"No se pudo cargar el modelo de {metodo}:\n{error_carga}")
            return
        avisar_no_vinculado(self, datos_usuario["usuario"], metodo)

    def _biometria_vinculada(self, datos_usuario, metodo):
        """
        Devuelve (etiqueta, vector) guardados para 'voz' o 'postura', o (None, None) si el
        usuario no la vinculó (o la clase guardada ya no existe en el modelo).
        """
        return biometria_vinculada(datos_usuario, metodo)

    def iniciar_sesion_voz(self):
        """Escaneo rápido de voz; o la palabra de ingreso / sistema anterior si está desactivado."""
        if INGRESO_RAPIDO_TM:
            from interfaces import ingreso_tm
            ingreso_tm.ingresar(self, "voz")
            return
        self._iniciar_sesion_plantilla("voz", "plantilla_voz", self._iniciar_sesion_voz_anterior)

    def iniciar_sesion_pose(self):
        """Postura de ingreso propia si existe; si no, el sistema anterior (Teachable Machine)."""
        self._iniciar_sesion_plantilla("postura", "plantilla_postura", self._iniciar_sesion_pose_anterior)

    def _iniciar_sesion_plantilla(self, metodo, columna, flujo_anterior):
        """
        Con usuario escrito: verifica 1:1 contra su plantilla. Sin usuario: identifica 1:N entre
        todos los usuarios con plantilla. Si no hay plantilla aplicable, usa el flujo anterior.
        """
        from interfaces.biometria_ingreso import VerificacionIngreso

        nombre = "palabra de ingreso" if metodo == "voz" else "postura de ingreso"
        con_vida = liveness.LIVENESS_VOZ if metodo == "voz" else liveness.LIVENESS_POSTURA

        usuario = self.txtUsuario.text().strip()
        if usuario:
            datos = UsuarioController.buscar_usuario(usuario)
            if datos is None or not _campo(datos, columna):
                if con_vida and datos is not None:
                    # El sistema anterior no admite prueba de vida: hay que registrar la nueva plantilla
                    Mensajes.advertencia(
                        self, f"{nombre.capitalize()} No Registrada",
                        f"El usuario '{usuario}' no tiene {nombre} registrada.\n\n"
                        f"Regístrela en '🔗 Vincular mi Biometría' o entre con su contraseña."
                    )
                    return
                flujo_anterior()
                return
            candidatos = [datos]
        else:
            candidatos = UsuarioController.usuarios_con_plantilla(metodo)
            if not candidatos:
                if con_vida:
                    Mensajes.advertencia(self, "Usuario Requerido",
                                         f"Escriba su usuario: nadie tiene {nombre} registrada todavía.")
                    return
                flujo_anterior()
                return

        self._verificacion_ingreso = VerificacionIngreso(
            self, metodo, candidatos,
            lambda datos, confianza: self._conceder_acceso(
                datos, f"{nombre.capitalize()} ({confianza * 100:.1f}%)", f"su {nombre}"),
            self._usar_contrasena,
            al_fallar=lambda motivo: self._registrar_fallo(metodo, motivo, usuario),
            puede_intentar=self._puede_intentar,
        )
        self._verificacion_ingreso.iniciar()

    def _usar_contrasena(self):
        """Respaldo: deja el cursor en la contraseña para entrar con usuario y contraseña."""
        self.txtPassword.clear()
        (self.txtPassword if self.txtUsuario.text().strip() else self.txtUsuario).setFocus()
        Mensajes.informacion(self, "Ingresar con Contraseña",
                             "Escriba su usuario y contraseña y pulse 'Iniciar sesión'.")

    def _iniciar_sesion_voz_anterior(self):
        datos_usuario = self._usuario_para_biometria("voz")
        if datos_usuario is None:
            return

        try:
            from utils.reconocimiento_voz import ReconocedorVoz
            from interfaces.dialogo_voz import DialogoVoz
        except Exception as err:
            Mensajes.error(self, "Error de Voz", f"Faltan dependencias para el reconocimiento de voz: {err}")
            return

        clase_voz, vector_voz = self._biometria_vinculada(datos_usuario, "voz")
        if clase_voz is None:
            self._avisar_biometria_no_vinculada(datos_usuario, "voz", ReconocedorVoz._error_carga)
            return

        audio = DialogoVoz.obtener_audio(self, clase_voz, self.SEGUNDOS_GRABACION_VOZ, "🎤 Ingresar por Voz")
        if audio is None:
            return

        ok, _, confianza, mensaje = ReconocedorVoz.verificar_palabra(
            audio, clase_voz, vector_referencia=vector_voz
        )
        if not ok:
            print(f"[Login] ❌ Login por voz fallido para '{datos_usuario['usuario']}': {mensaje}")
            Mensajes.advertencia(self, "Reconocimiento por Voz Fallido", mensaje)
            return

        print(f"[Login] ✅ Autenticación por voz exitosa: '{datos_usuario['usuario']}'")
        self._conceder_acceso(datos_usuario, f"Voz ({confianza * 100:.1f}%)", "reconocimiento de voz")

    def _iniciar_sesion_pose_anterior(self):
        datos_usuario = self._usuario_para_biometria("postura")
        if datos_usuario is None:
            return

        try:
            from utils.reconocimiento_pose import ReconocedorPose
            from interfaces.camara import VentanaCamara  # noqa: F401 (verifica dependencias de cámara)
        except Exception as err:
            Mensajes.error(self, "Error de Cámara", f"Faltan dependencias para el reconocimiento de postura: {err}")
            return

        clase_pose, vector_pose = self._biometria_vinculada(datos_usuario, "postura")
        if clase_pose is None:
            self._avisar_biometria_no_vinculada(datos_usuario, "postura", ReconocedorPose._error_carga)
            return

        self.ventana_camara_pose = abrir_camara_pose(
            self,
            "🧍 Autenticación por Postura",
            "Haga su postura registrada frente a la cámara",
            lambda frames: self._procesar_login_pose(frames, datos_usuario, clase_pose, vector_pose)
        )

    def _procesar_login_pose(self, frames, datos_usuario, clase_pose, vector_pose=None):
        from utils.reconocimiento_pose import ReconocedorPose

        ok, _, confianza, mensaje = ReconocedorPose.verificar_pose(
            frames, clase_pose, umbral_confianza=self.UMBRAL_CONFIANZA_POSE, vector_referencia=vector_pose
        )
        if not ok:
            print(f"[Login] ❌ Login por postura fallido para '{datos_usuario['usuario']}': {mensaje}")
            Mensajes.advertencia(self, "Reconocimiento por Postura Fallido", mensaje)
            return

        print(f"[Login] ✅ Autenticación por postura exitosa: '{datos_usuario['usuario']}'")
        self._conceder_acceso(datos_usuario, f"Postura ({confianza * 100:.1f}%)", "reconocimiento de postura")

    def _conceder_acceso(self, datos_usuario, metodo_auth, via):
        # ─── PASO 4: Acceso permitido ────────────────────────────────────────
        from interfaces.menu import MenuPrincipal

        if not self._segundo_factor_superado(datos_usuario):
            return
        # Un acceso correcto reinicia la racha de intentos fallidos
        SeguridadController.registrar_intento(via, True, "", datos_usuario["usuario"])

        Mensajes.informacion(
            self,
            "Acceso Autorizado ✓",
            f"¡Bienvenido/a, {datos_usuario['nombre']}!\n\n"
            f"Autenticado correctamente mediante {via}.\n"
            f"Método: {metodo_auth}"
        )

        self.menu = MenuPrincipal(
            datos_usuario["nombre"],
            datos_usuario["usuario"]
        )

        self.menu.show()
        self.close()


# =========================================================
# PRUEBA DIRECTA
# =========================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Login()

    ventana.show()

    sys.exit(app.exec_())
