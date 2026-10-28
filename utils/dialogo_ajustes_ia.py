# -*- coding: utf-8 -*-
"""Diálogo moderno de configuración de Inteligencia Artificial.

Permite al usuario ver, ingresar y editar:
- GROUP_BASE_URL (URL base del proveedor)
- GROUP_MODEL (Modelo de IA)
- GROUP_API_KEY (Clave de acceso a la API)

Incluye un botón para probar la conexión en tiempo real y guardar
los cambios directamente en el archivo .env y en memoria.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QMessageBox,
    QApplication,
)

from utils.config import (
    GROUP_API_KEY,
    GROUP_BASE_URL,
    GROUP_MODEL,
    guardar_configuracion_env,
)
from services.ia_service import IAService


class DialogoAjustesIA(QDialog):
    """Ventana modal para editar y guardar la configuración del motor de IA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes — Configuración de Inteligencia Artificial")
        self.setFixedWidth(520)
        self.setModal(True)

        self._construir_ui()
        self._cargar_valores_actuales()

    def _construir_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #F8FAFC;
                font-family: "Segoe UI";
            }
            QFrame#headerCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0F2F66,
                    stop:1 #1E40AF
                );
                border-radius: 12px;
            }
            QLabel#headerTitle {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
            QLabel#headerSub {
                color: rgba(255, 255, 255, 0.85);
                font-size: 11px;
                background: transparent;
            }
            QLabel#formLabel {
                font-size: 12px;
                font-weight: bold;
                color: #1E293B;
                margin-top: 2px;
            }
            QLabel#formDesc {
                font-size: 11px;
                color: #64748B;
                margin-bottom: 2px;
            }
            QLineEdit {
                background: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #0F172A;
                selection-background-color: #BFDBFE;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
                background: #FFFFFF;
            }
            QPushButton#btnToggleVer {
                background: #F1F5F9;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: bold;
                color: #334155;
            }
            QPushButton#btnToggleVer:hover {
                background: #E2E8F0;
                border-color: #94A3B8;
            }
            QPushButton#btnPreset {
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #1D4ED8;
            }
            QPushButton#btnPreset:hover {
                background: #DBEAFE;
            }
            QPushButton#btnProbar {
                background: #7C3AED;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnProbar:hover {
                background: #6D28D9;
            }
            QPushButton#btnGuardar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563EB,
                    stop:1 #1D4ED8
                );
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnGuardar:hover {
                background: #1E40AF;
            }
            QPushButton#btnCancelar {
                background: #FFFFFF;
                color: #475569;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 9px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnCancelar:hover {
                background: #F1F5F9;
                border-color: #94A3B8;
            }
            QLabel#statusBox {
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # -----------------------------------------------------
        # ENCABEZADO
        # -----------------------------------------------------
        header = QFrame()
        header.setObjectName("headerCard")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(16, 14, 16, 14)
        h_layout.setSpacing(4)

        lbl_titulo = QLabel("⚙️ Configuración del Motor de IA")
        lbl_titulo.setObjectName("headerTitle")
        lbl_sub = QLabel(
            "Configura tu proveedor de IA, modelo y API Key para resolver problemas."
        )
        lbl_sub.setObjectName("headerSub")
        lbl_sub.setWordWrap(True)

        h_layout.addWidget(lbl_titulo)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # -----------------------------------------------------
        # FORMULARIO
        # -----------------------------------------------------
        # 1. BASE URL
        lbl_url = QLabel("Proveedor / URL Base:")
        lbl_url.setObjectName("formLabel")
        lbl_url_desc = QLabel("Dirección del endpoint compatible con OpenAI (Ej: Groq, OpenAI).")
        lbl_url_desc.setObjectName("formDesc")

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://api.groq.com/openai/v1")

        # Presets rápidos
        fila_presets_url = QHBoxLayout()
        fila_presets_url.setSpacing(6)
        lbl_sug = QLabel("Sugerencias:")
        lbl_sug.setStyleSheet("color: #64748B; font-size: 11px;")
        fila_presets_url.addWidget(lbl_sug)

        btn_preset_groq = QPushButton("⚡ Groq (Ultra Rápido)")
        btn_preset_groq.setObjectName("btnPreset")
        btn_preset_groq.setCursor(Qt.PointingHandCursor)
        btn_preset_groq.clicked.connect(
            lambda: self._aplicar_preset("https://api.groq.com/openai/v1", "qwen/qwen3.8-27b")
        )
        fila_presets_url.addWidget(btn_preset_groq)

        btn_preset_openai = QPushButton("OpenAI")
        btn_preset_openai.setObjectName("btnPreset")
        btn_preset_openai.setCursor(Qt.PointingHandCursor)
        btn_preset_openai.clicked.connect(
            lambda: self._aplicar_preset("https://api.openai.com/v1", "gpt-4o-mini")
        )
        fila_presets_url.addWidget(btn_preset_openai)
        fila_presets_url.addStretch()

        layout.addWidget(lbl_url)
        layout.addWidget(lbl_url_desc)
        layout.addWidget(self.txt_url)
        layout.addLayout(fila_presets_url)

        layout.addSpacing(2)

        # 2. MODELO
        lbl_modelo = QLabel("Modelo de IA:")
        lbl_modelo.setObjectName("formLabel")
        lbl_modelo_desc = QLabel("Nombre del modelo compatible con visión y texto.")
        lbl_modelo_desc.setObjectName("formDesc")

        self.txt_modelo = QLineEdit()
        self.txt_modelo.setPlaceholderText("qwen/qwen3.8-27b")

        layout.addWidget(lbl_modelo)
        layout.addWidget(lbl_modelo_desc)
        layout.addWidget(self.txt_modelo)

        layout.addSpacing(2)

        # 3. API KEY
        lbl_key = QLabel("Clave de API (API Key):")
        lbl_key.setObjectName("formLabel")
        lbl_key_desc = QLabel("Tu clave secreta proporcionada por el proveedor (se guarda localmente).")
        lbl_key_desc.setObjectName("formDesc")

        fila_key = QHBoxLayout()
        fila_key.setSpacing(8)

        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("gsk_... o sk-...")
        self.txt_key.setEchoMode(QLineEdit.Password)

        self.btn_toggle_ver = QPushButton("👁️ Ver")
        self.btn_toggle_ver.setObjectName("btnToggleVer")
        self.btn_toggle_ver.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_ver.clicked.connect(self._toggle_ver_clave)

        fila_key.addWidget(self.txt_key, 1)
        fila_key.addWidget(self.btn_toggle_ver)

        layout.addWidget(lbl_key)
        layout.addWidget(lbl_key_desc)
        layout.addLayout(fila_key)

        # -----------------------------------------------------
        # ÁREA DE ESTADO / PRUEBA
        # -----------------------------------------------------
        self.lbl_estado = QLabel("")
        self.lbl_estado.setObjectName("statusBox")
        self.lbl_estado.setVisible(False)
        self.lbl_estado.setWordWrap(True)
        layout.addWidget(self.lbl_estado)

        layout.addSpacing(4)

        # -----------------------------------------------------
        # SEGURIDAD: PALABRA Y POSTURA DE INGRESO (solo con sesión iniciada)
        # -----------------------------------------------------
        usuario = getattr(self.parent(), "usuario", None)
        if usuario:
            separador = QFrame()
            separador.setFrameShape(QFrame.HLine)
            separador.setStyleSheet("color: #E2E8F0;")
            lbl_seg = QLabel("Seguridad de la cuenta:")
            lbl_seg.setObjectName("formLabel")
            btn_biometria = QPushButton("🔐 Cambiar palabra / postura de ingreso")
            btn_biometria.setObjectName("btnPreset")
            btn_biometria.setCursor(Qt.PointingHandCursor)
            btn_biometria.clicked.connect(lambda: self._abrir_biometria_ingreso(usuario))
            fila_seg = QHBoxLayout()
            fila_seg.addWidget(lbl_seg)
            fila_seg.addStretch()
            fila_seg.addWidget(btn_biometria)
            layout.addWidget(separador)
            layout.addLayout(fila_seg)

        # -----------------------------------------------------
        # BOTONES INFERIORES
        # -----------------------------------------------------
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(10)

        self.btn_probar = QPushButton("🔌 Probar Conexión")
        self.btn_probar.setObjectName("btnProbar")
        self.btn_probar.setCursor(Qt.PointingHandCursor)
        self.btn_probar.clicked.connect(self._probar_conexion)

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.setObjectName("btnGuardar")
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self._guardar_configuracion)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)

        fila_botones.addWidget(self.btn_probar)
        fila_botones.addStretch()
        fila_botones.addWidget(self.btn_cancelar)
        fila_botones.addWidget(self.btn_guardar)

        layout.addLayout(fila_botones)

    def _abrir_biometria_ingreso(self, usuario):
        """Abre el cambio de palabra y postura de ingreso (pide la contraseña antes)."""
        try:
            from interfaces.biometria_ingreso import abrir_ajustes_biometria
            abrir_ajustes_biometria(self, usuario)
        except Exception as error:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la configuración de ingreso:\n{error}")

    def _cargar_valores_actuales(self):
        """Carga los valores actuales en los campos de texto."""
        import os
        import utils.config as cfg

        url = os.getenv("GROUP_BASE_URL") or cfg.GROUP_BASE_URL or ""
        modelo = os.getenv("GROUP_MODEL") or cfg.GROUP_MODEL or ""
        key = os.getenv("GROUP_API_KEY") or cfg.GROUP_API_KEY or ""

        self.txt_url.setText(url)
        self.txt_modelo.setText(modelo)
        self.txt_key.setText(key)

    def _aplicar_preset(self, url, modelo):
        """Aplica valores recomendados para proveedores comunes."""
        self.txt_url.setText(url)
        self.txt_modelo.setText(modelo)

    def _toggle_ver_clave(self):
        """Alterna entre mostrar y ocultar la API Key."""
        if self.txt_key.echoMode() == QLineEdit.Password:
            self.txt_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_ver.setText("🙈 Ocultar")
        else:
            self.txt_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_ver.setText("👁️ Ver")

    def _mostrar_estado(self, mensaje, exito=True):
        """Muestra un mensaje de estado en la caja de retroalimentación."""
        if exito:
            self.lbl_estado.setStyleSheet(
                "background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; padding: 8px 12px; border-radius: 8px; font-weight: bold;"
            )
        else:
            self.lbl_estado.setStyleSheet(
                "background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; padding: 8px 12px; border-radius: 8px; font-weight: bold;"
            )
        self.lbl_estado.setText(mensaje)
        self.lbl_estado.setVisible(True)

    def _probar_conexion(self):
        """Prueba la conexión con los parámetros ingresados."""
        api_key = self.txt_key.text().strip()
        base_url = self.txt_url.text().strip()
        modelo = self.txt_modelo.text().strip()

        if not api_key:
            self._mostrar_estado("⚠️ Debe ingresar una API Key para probar la conexión.", exito=False)
            return

        if not base_url:
            self._mostrar_estado("⚠️ Debe ingresar la URL base del proveedor.", exito=False)
            return

        if not modelo:
            self._mostrar_estado("⚠️ Debe ingresar el nombre del modelo.", exito=False)
            return

        self._mostrar_estado("⏳ Probando conexión con el proveedor de IA...", exito=True)
        self.lbl_estado.setStyleSheet(
            "background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; padding: 8px 12px; border-radius: 8px; font-weight: bold;"
        )
        self.btn_probar.setEnabled(False)
        QApplication.processEvents()

        try:
            ia = IAService(api_key=api_key, base_url=base_url, modelo=modelo)
            ok, respuesta = ia.probar_conexion()

            if ok:
                self._mostrar_estado("✅ ¡Conexión exitosa! El proveedor respondió correctamente.", exito=True)
            else:
                self._mostrar_estado(f"❌ Error de conexión:\n{respuesta}", exito=False)
        except Exception as error:
            self._mostrar_estado(f"❌ Error inesperado: {error}", exito=False)
        finally:
            self.btn_probar.setEnabled(True)

    def _guardar_configuracion(self):
        """Guarda la configuración ingresada en .env y variables en memoria."""
        api_key = self.txt_key.text().strip()
        base_url = self.txt_url.text().strip()
        modelo = self.txt_modelo.text().strip()

        if not api_key or not base_url or not modelo:
            confirmar = QMessageBox.question(
                self,
                "Campos incompletos",
                "Uno o más campos están vacíos. ¿Deseas guardar de todas formas?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirmar != QMessageBox.Yes:
                return

        try:
            guardar_configuracion_env(
                api_key=api_key,
                base_url=base_url,
                modelo=modelo,
            )
            QMessageBox.information(
                self,
                "Configuración Guardada",
                "La configuración de la Inteligencia Artificial se ha guardado exitosamente.",
            )
            self.accept()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"No se pudo guardar la configuración:\n{error}",
            )


def mostrar_dialogo_ajustes_ia(parent=None):
    """Función de utilidad para abrir el diálogo de ajustes de IA."""
    dialogo = DialogoAjustesIA(parent)
    return dialogo.exec_()
