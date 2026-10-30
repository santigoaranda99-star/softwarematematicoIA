
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QToolButton,
    QApplication
)

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

import sys

from controllers.usuario_controller import UsuarioController
from utils.validaciones import Validaciones
from utils.mensajes import Mensajes
from interfaces.captura_biometrica import ESTILO_BOTONES_BIOMETRIA
from interfaces.biometria_ingreso import RegistroPostura, registrar_palabra_ingreso
from utils.umbrales_biometria import INGRESO_RAPIDO_TM


class Registro(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Crear Cuenta")
        self.setMinimumSize(420, 580)
        self.resize(480, 660)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)
        from utils.tema import instalar_modo_oscuro_al_mostrar
        instalar_modo_oscuro_al_mostrar(self)

        self.etiqueta_facial = ""
        # Palabra de ingreso (palabra, plantilla) y plantilla de postura capturadas
        # antes de crear la cuenta; se guardan al pulsar "Crear cuenta"
        self._voz_capturada = None
        self._pose_capturada = None
        self._registro_postura = None

        self.setStyleSheet("""
            QWidget {
                background: #F1F5F9;
                font-family: "Segoe UI";
            }

            QLabel {
                color: #0F172A;
            }

            QLineEdit {
                padding: 10px;
                border: 2px solid #D1D5DB;
                border-radius: 8px;
                font-size: 14px;
                background: #FFFFFF;
                color: #0F172A;
            }

            QLineEdit:focus {
                border: 2px solid #2563EB;
            }

            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background: #1D4ED8;
            }

            QLabel#tituloBiometria {
                color: #334155;
                font-size: 12px;
                font-weight: bold;
            }

            QLabel#estadoBiometria {
                color: #64748B;
                font-size: 11px;
            }

            QToolButton {
                background: transparent;
                border: none;
                padding: 5px;
                font-size: 18px;
            }

            QToolButton:hover {
                background: #E5E7EB;
                border-radius: 5px;
            }
        """ + ESTILO_BOTONES_BIOMETRIA)

        # =====================================================
        # LAYOUT PRINCIPAL CENTRADO
        # =====================================================

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setMaximumWidth(460)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(10)

        root_layout.addStretch()
        root_layout.addWidget(container)
        root_layout.addStretch()

        # =====================================================
        # TÍTULO
        # =====================================================

        titulo = QLabel("Software Matemático IA")

        titulo.setAlignment(Qt.AlignCenter)

        titulo.setFont(
            QFont("Segoe UI", 20, QFont.Bold)
        )

        # =====================================================
        # SUBTÍTULO
        # =====================================================

        subtitulo = QLabel("Crear una cuenta")

        subtitulo.setAlignment(Qt.AlignCenter)

        subtitulo.setFont(
            QFont("Segoe UI", 12)
        )

        # =====================================================
        # NOMBRE
        # =====================================================

        self.txtNombre = QLineEdit()

        self.txtNombre.setPlaceholderText(
            "Nombre completo"
        )

        # =====================================================
        # USUARIO
        # =====================================================

        self.txtUsuario = QLineEdit()

        self.txtUsuario.setPlaceholderText(
            "Usuario"
        )

        # =====================================================
        # CONTRASEÑA
        # =====================================================

        self.txtPassword = QLineEdit()

        self.txtPassword.setPlaceholderText(
            "Contraseña"
        )

        self.txtPassword.setEchoMode(
            QLineEdit.Password
        )

        # =====================================================
        # OJO CONTRASEÑA
        # =====================================================

        self.btnMostrarPassword = QToolButton()

        self.btnMostrarPassword.setText("👁")

        self.btnMostrarPassword.setCursor(
            Qt.PointingHandCursor
        )

        self.btnMostrarPassword.setToolTip(
            "Mostrar contraseña"
        )

        self.btnMostrarPassword.clicked.connect(
            self.mostrar_ocultar_password
        )

        password_layout = QHBoxLayout()

        password_layout.setSpacing(0)

        password_layout.addWidget(
            self.txtPassword
        )

        password_layout.addWidget(
            self.btnMostrarPassword
        )

        # =====================================================
        # CONFIRMAR CONTRASEÑA
        # =====================================================

        self.txtConfirmarPassword = QLineEdit()

        self.txtConfirmarPassword.setPlaceholderText(
            "Confirmar contraseña"
        )

        self.txtConfirmarPassword.setEchoMode(
            QLineEdit.Password
        )

        # =====================================================
        # OJO CONFIRMAR CONTRASEÑA
        # =====================================================

        self.btnMostrarConfirmacion = QToolButton()

        self.btnMostrarConfirmacion.setText("👁")

        self.btnMostrarConfirmacion.setCursor(
            Qt.PointingHandCursor
        )

        self.btnMostrarConfirmacion.setToolTip(
            "Mostrar contraseña"
        )

        self.btnMostrarConfirmacion.clicked.connect(
            self.mostrar_ocultar_confirmacion
        )

        confirmar_layout = QHBoxLayout()

        confirmar_layout.setSpacing(0)

        confirmar_layout.addWidget(
            self.txtConfirmarPassword
        )

        confirmar_layout.addWidget(
            self.btnMostrarConfirmacion
        )

        # =====================================================
        # BIOMETRÍA OPCIONAL: ROSTRO / VOZ / POSTURA
        # =====================================================

        lblBiometria = QLabel("Vincular biometría (opcional, también puede hacerlo después)")
        lblBiometria.setObjectName("tituloBiometria")
        lblBiometria.setWordWrap(True)

        self.btnFacial = QPushButton("📷 Rostro")
        self.btnVoz = QPushButton("🎤 Voz")
        self.btnPose = QPushButton("🧍 Postura")
        self.lblEstadoRostro = QLabel("Sin vincular")
        self.lblEstadoVoz = QLabel("Sin vincular")
        self.lblEstadoPose = QLabel("Sin vincular")

        grid_biometria = QGridLayout()
        grid_biometria.setHorizontalSpacing(8)
        grid_biometria.setVerticalSpacing(4)
        for columna, (boton, nombre_obj, estado, ayuda) in enumerate((
            (self.btnFacial, "btnFacial", self.lblEstadoRostro, "Capturar su rostro para iniciar sesión con la cámara"),
            (self.btnVoz, "btnVoz", self.lblEstadoVoz, "Elegir y grabar su palabra de ingreso (3 veces)"),
            (self.btnPose, "btnPose", self.lblEstadoPose, "Capturar la postura que quiera usar para entrar (3 veces)"),
        )):
            boton.setObjectName(nombre_obj)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setToolTip(ayuda)
            estado.setObjectName("estadoBiometria")
            estado.setAlignment(Qt.AlignCenter)
            estado.setWordWrap(True)
            grid_biometria.addWidget(boton, 0, columna)
            grid_biometria.addWidget(estado, 1, columna)
            grid_biometria.setColumnStretch(columna, 1)

        # =====================================================
        # BOTONES
        # =====================================================

        self.btnRegistrar = QPushButton(
            "Crear cuenta"
        )

        self.btnVolver = QPushButton(
            "Volver al Login"
        )

        # =====================================================
        # CONEXIONES
        # =====================================================

        self.btnFacial.clicked.connect(
            self.capturar_rostro
        )

        self.btnVoz.clicked.connect(
            self.capturar_voz
        )

        self.btnPose.clicked.connect(
            self.capturar_pose
        )

        self.btnRegistrar.clicked.connect(
            self.registrar_usuario
        )

        self.btnVolver.clicked.connect(
            self.volver_login
        )

        # =====================================================
        # AGREGAR ELEMENTOS
        # =====================================================

        layout.addStretch()

        layout.addWidget(titulo)

        layout.addWidget(subtitulo)

        layout.addSpacing(10)

        layout.addWidget(
            self.txtNombre
        )

        layout.addWidget(
            self.txtUsuario
        )

        layout.addLayout(
            password_layout
        )

        layout.addLayout(
            confirmar_layout
        )

        layout.addSpacing(6)

        layout.addWidget(lblBiometria)
        layout.addLayout(grid_biometria)

        layout.addSpacing(10)

        layout.addWidget(
            self.btnRegistrar
        )

        layout.addWidget(
            self.btnVolver
        )

        layout.addStretch()


    # =====================================================
    # MOSTRAR / OCULTAR CONTRASEÑA
    # =====================================================

    def mostrar_ocultar_password(self):

        if self.txtPassword.echoMode() == QLineEdit.Password:

            self.txtPassword.setEchoMode(
                QLineEdit.Normal
            )

            self.btnMostrarPassword.setText("🙈")

            self.btnMostrarPassword.setToolTip(
                "Ocultar contraseña"
            )

        else:

            self.txtPassword.setEchoMode(
                QLineEdit.Password
            )

            self.btnMostrarPassword.setText("👁")

            self.btnMostrarPassword.setToolTip(
                "Mostrar contraseña"
            )

    # =====================================================
    # MOSTRAR / OCULTAR CONFIRMACIÓN
    # =====================================================

    def mostrar_ocultar_confirmacion(self):

        if self.txtConfirmarPassword.echoMode() == QLineEdit.Password:

            self.txtConfirmarPassword.setEchoMode(
                QLineEdit.Normal
            )

            self.btnMostrarConfirmacion.setText("🙈")

            self.btnMostrarConfirmacion.setToolTip(
                "Ocultar contraseña"
            )

        else:

            self.txtConfirmarPassword.setEchoMode(
                QLineEdit.Password
            )

            self.btnMostrarConfirmacion.setText("👁")

            self.btnMostrarConfirmacion.setToolTip(
                "Mostrar contraseña"
            )

    # =====================================================
    # REGISTRAR USUARIO
    # =====================================================

    def registrar_usuario(self):

        nombre = self.txtNombre.text().strip()

        usuario = self.txtUsuario.text().strip()

        password = self.txtPassword.text().strip()

        confirmar = self.txtConfirmarPassword.text().strip()

        # =================================================
        # VALIDAR NOMBRE
        # =================================================

        if Validaciones.campo_vacio(nombre):

            Mensajes.campo_vacio(self)

            self.txtNombre.setFocus()

            return

        # =================================================
        # VALIDAR USUARIO
        # =================================================

        if Validaciones.campo_vacio(usuario):

            Mensajes.campo_vacio(self)

            self.txtUsuario.setFocus()

            return

        # =================================================
        # VALIDAR CONTRASEÑA
        # =================================================

        if Validaciones.campo_vacio(password):

            Mensajes.campo_vacio(self)

            self.txtPassword.setFocus()

            return

        # =================================================
        # CONFIRMAR CONTRASEÑA
        # =================================================

        if password != confirmar:

            Mensajes.error(
                self,
                "Error",
                "Las contraseñas no coinciden."
            )

            self.txtConfirmarPassword.clear()

            self.txtConfirmarPassword.setFocus()

            return

        try:

            # =================================================
            # CREAR USUARIO
            # =================================================

            ok, mensaje = UsuarioController.registrar_usuario(
                nombre,
                usuario,
                password,
                etiqueta_facial=self.etiqueta_facial
            )

            # =================================================
            # REGISTRO CORRECTO
            # =================================================

            if ok:

                # Guardar embedding biométrico SFace en la BD (para autenticación 1:N sin contraseña)
                emb = getattr(self, "_embedding_facial", None)
                if emb:
                    guardado = UsuarioController.guardar_embedding_facial(usuario, emb)
                    if guardado:
                        print(f"[Registro] Embedding biométrico guardado en BD para usuario '{usuario}'.")
                    else:
                        print(f"[Registro] ⚠️ No se pudo guardar el embedding en la BD para '{usuario}'.")

                if self._voz_capturada:
                    palabra, plantilla, clase_voz = self._voz_capturada
                    if not UsuarioController.guardar_palabra_ingreso(usuario, palabra, plantilla):
                        print(f"[Registro] ⚠️ No se pudo guardar la palabra de ingreso para '{usuario}'.")
                    UsuarioController.guardar_clase_tm(usuario, "voz", clase_voz)

                if self._pose_capturada:
                    plantilla_pose, clase_pose = self._pose_capturada
                    if not UsuarioController.guardar_plantilla_postura(usuario, plantilla_pose):
                        print(f"[Registro] ⚠️ No se pudo guardar la postura de ingreso para '{usuario}'.")
                    UsuarioController.guardar_clase_tm(usuario, "postura", clase_pose)

                Mensajes.informacion(
                    self,
                    "Registro exitoso",
                    mensaje
                )

                self.volver_login()

            elif "ya existe" in mensaje:

                Mensajes.usuario_existente(self)

            else:

                Mensajes.error(
                    self,
                    "Error",
                    mensaje
                )

        except Exception as error:

            Mensajes.error(
                self,
                "Error",
                str(error)
            )

    # =====================================================
    # CAPTURAR Y VINCULAR ROSTRO DE USUARIO
    # =====================================================

    def capturar_rostro(self):

        try:
            from interfaces.camara import VentanaCamara
        except ImportError:
            Mensajes.error(
                self,
                "Error de Cámara",
                "No se pudo abrir el módulo de la cámara."
            )
            return

        self.ventana_camara = VentanaCamara(self)
        self.ventana_camara.modo_facial = True
        self.ventana_camara.setWindowTitle("📸 Registro de Reconocimiento Facial")
        self.ventana_camara.titulo.setText("Mire a la cámara para registrar su rostro")
        self.ventana_camara.lblEstado.setText("Mantenga su rostro centrado y presione 'Capturar Foto'.")
        self.ventana_camara.foto_capturada.connect(self.procesar_foto_registro)
        self.ventana_camara.show()

    def procesar_foto_registro(self, datos_bytes, mime):

        if not datos_bytes:
            return

        try:
            import cv2
            import numpy as np
            from services.clasificador_imagen import ClasificadorImagen
        except ImportError as err:
            Mensajes.error(
                self,
                "Error",
                f"Faltan dependencias para el reconocimiento facial: {err}"
            )
            return

        nparr = np.frombuffer(datos_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            Mensajes.error(
                self,
                "Error de Imagen",
                "No se pudo procesar la foto capturada por la cámara."
            )
            return

        usuario_ingresado = self.txtUsuario.text().strip()

        # Validación biométrica y fotométrica con reporte de errores descriptivo
        exito, etiqueta, confianza, motivo = ClasificadorImagen.clasificar_para_registro(
            frame,
            usuario_propuesto=usuario_ingresado
        )

        if not exito:
            print(f"[Registro] Validación facial rechazada: {motivo}")
            Mensajes.advertencia(
                self,
                "Captura No Válida",
                motivo
            )
            return

        self.etiqueta_facial = etiqueta

        # Extraer y guardar el embedding biométrico SFace 128D en la base de datos
        # Esto permite autenticación 1:N sin ingresar usuario (comparación directa de vectores)
        self._embedding_facial = None
        usuario_ingresado = self.txtUsuario.text().strip()
        try:
            exito_emb, embedding, bbox_emb, score_emb = ClasificadorImagen.extraer_embedding(frame)
            if exito_emb and embedding:
                self._embedding_facial = embedding
                print(f"[Registro] Embedding SFace extraído correctamente ({len(embedding)} dimensiones, confianza={score_emb:.2f})")
            else:
                print("[Registro] No se pudo extraer el embedding SFace del frame.")
        except Exception as e:
            print(f"[Registro] Error al extraer embedding SFace: {e}")

        self._marcar_capturado(self.lblEstadoRostro, f"✓ Capturado ({confianza * 100:.0f}%)")

        Mensajes.informacion(
            self,
            "Rostro Vinculado",
            f"¡Rostro capturado y vinculado correctamente!\n"
            f"Identificador facial: '{etiqueta}' ({confianza * 100:.1f}% de confianza)."
        )

    # =====================================================
    # CAPTURAR VOZ Y POSTURA (se guardan al crear la cuenta)
    # =====================================================

    def capturar_voz(self):
        def al_terminar(palabra, plantilla, clase=""):
            self._voz_capturada = (palabra, plantilla, clase)
            self._marcar_capturado(self.lblEstadoVoz, "✓ Palabra grabada")
            Mensajes.informacion(
                self,
                "Palabra de Ingreso Lista",
                "¡Su palabra de ingreso quedó grabada!\n\n"
                "Se vinculará a su cuenta al pulsar 'Crear cuenta'."
            )

        if INGRESO_RAPIDO_TM:
            # Registro adaptativo: se repite solo la grabación que salga mal
            from interfaces.ingreso_tm import capturar_palabra_clave
            capturada = capturar_palabra_clave(self)
            if capturada:
                al_terminar(*capturada)
            return
        registrar_palabra_ingreso(self, al_terminar)

    def capturar_pose(self):
        def al_terminar(plantilla, clase=""):
            self._pose_capturada = (plantilla, clase)
            self._marcar_capturado(self.lblEstadoPose, "✓ Postura capturada")
            Mensajes.informacion(
                self,
                "Postura de Ingreso Lista",
                "¡Su postura de ingreso quedó registrada!\n\n"
                "Se vinculará a su cuenta al pulsar 'Crear cuenta'."
            )

        if INGRESO_RAPIDO_TM:
            # Un solo escaneo con los puntos del cuerpo en pantalla, como en Teachable Machine
            from interfaces.ingreso_tm import capturar_postura
            capturada = capturar_postura(self)
            if capturada:
                al_terminar(capturada["plantilla"], capturada["clase"])
            return
        self._registro_postura = RegistroPostura(self, al_terminar)
        self._registro_postura.iniciar()

    @staticmethod
    def _marcar_capturado(etiqueta, texto):
        etiqueta.setText(texto)
        etiqueta.setStyleSheet("color: #059669; font-weight: bold; font-size: 11px;")

    # =====================================================
    # VOLVER AL LOGIN
    # =====================================================

    def volver_login(self):

        from interfaces.login import Login

        self.login = Login()

        self.login.show()

        self.close()


# ==========================================================
# PRUEBA
# ==========================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Registro()

    ventana.show()

    sys.exit(app.exec_())
