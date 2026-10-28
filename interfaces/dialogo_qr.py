# -*- coding: utf-8 -*-
"""Diálogo moderno para escanear Código QR y conectar la cámara del celular.

Muestra un código QR generado en tiempo real que apunta al servidor HTTP local.
Cuando el usuario toma la foto en su celular y la envía, este diálogo la recibe,
la entrega a la ventana principal de resolución y opcionalmente dispara la
resolución automática instantánea con IA.
"""

import sys
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QColor, QClipboard, QGuiApplication
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QCheckBox,
    QApplication,
    QMessageBox,
)

from services.servidor_movil import ServidorMovil


class DialogoQR(QDialog):
    """Ventana modal que muestra el código QR para capturar problemas con el smartphone."""

    # Señal emitida al recibir foto: (bytes_imagen, mime_type, nota_estudiante, auto_resolver)
    foto_recibida_senal = pyqtSignal(bytes, str, str, bool)

    def __init__(self, parent=None, auto_resolver_por_defecto=True):
        super().__init__(parent)

        self.setWindowTitle("📱 Conectar Cámara del Celular con Código QR")
        self.setMinimumWidth(420)
        self.resize(480, 680)
        self.setModal(True)

        self.servidor = ServidorMovil(self)
        self.auto_resolver_por_defecto = auto_resolver_por_defecto

        self._construir_ui()
        self._iniciar_servidor_y_qr()

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
                    stop:0.6 #1E40AF,
                    stop:1 #2563EB
                );
                border-radius: 14px;
            }
            QLabel#headerTitle {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 800;
                background: transparent;
            }
            QLabel#headerSub {
                color: rgba(255, 255, 255, 0.88);
                font-size: 12px;
                background: transparent;
            }
            QFrame#qrCard {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 16px;
            }
            QLabel#lblUrl {
                color: #1E40AF;
                font-size: 12px;
                font-weight: bold;
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QCheckBox {
                font-size: 13px;
                font-weight: 600;
                color: #1E293B;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1.5px solid #94A3B8;
            }
            QCheckBox::indicator:checked {
                background-color: #2563EB;
                border-color: #2563EB;
                image: none;
            }
            QLabel#badgeEstado {
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 10px;
                background: #EFF6FF;
                color: #1D4ED8;
                border: 1px solid #BFDBFE;
            }
            QFrame#instruccionesBox {
                background: #F1F5F9;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLabel#txtInstrucciones {
                color: #475569;
                font-size: 11px;
                line-height: 1.4;
                background: transparent;
            }
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton#btnCopiar {
                background: #F1F5F9;
                color: #334155;
                border: 1px solid #CBD5E1;
            }
            QPushButton#btnCopiar:hover {
                background: #E2E8F0;
            }
            QPushButton#btnCerrar {
                background: #64748B;
            }
            QPushButton#btnCerrar:hover {
                background: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. ENCABEZADO
        header = QFrame()
        header.setObjectName("headerCard")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(16, 14, 16, 14)
        h_layout.setSpacing(4)

        lbl_titulo = QLabel("📱 Escanear con tu Celular")
        lbl_titulo.setObjectName("headerTitle")
        lbl_sub = QLabel("Apunta la cámara de tu teléfono para enviar una foto directamente.")
        lbl_sub.setObjectName("headerSub")
        lbl_sub.setWordWrap(True)

        h_layout.addWidget(lbl_titulo)
        h_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # 2. TARJETA CON EL CÓDIGO QR
        qr_card = QFrame()
        qr_card.setObjectName("qrCard")
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setContentsMargins(16, 16, 16, 16)
        qr_layout.setSpacing(10)
        qr_layout.setAlignment(Qt.AlignCenter)

        self.lbl_qr = QLabel("Generando código QR...")
        self.lbl_qr.setFixedSize(220, 220)
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setStyleSheet("background: #FFFFFF; border-radius: 8px;")
        qr_layout.addWidget(self.lbl_qr, 0, Qt.AlignCenter)

        # Estado dinámico
        self.lbl_estado = QLabel("⏳ Esperando escaneo desde tu celular...")
        self.lbl_estado.setObjectName("badgeEstado")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.lbl_estado)

        layout.addWidget(qr_card)

        # 3. URL Y BOTÓN COPIAR
        fila_url = QHBoxLayout()
        fila_url.setSpacing(8)

        self.lbl_url = QLabel("http://...")
        self.lbl_url.setObjectName("lblUrl")
        self.lbl_url.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.btn_copiar = QPushButton("📋 Copiar")
        self.btn_copiar.setObjectName("btnCopiar")
        self.btn_copiar.setCursor(Qt.PointingHandCursor)
        self.btn_copiar.clicked.connect(self._copiar_url)

        fila_url.addWidget(self.lbl_url, 1)
        fila_url.addWidget(self.btn_copiar)
        layout.addLayout(fila_url)

        # 4. CASILLA DE AUTO-RESOLUCIÓN
        self.chk_auto_resolver = QCheckBox("⚡ Resolver automáticamente al recibir la foto")
        self.chk_auto_resolver.setChecked(self.auto_resolver_por_defecto)
        self.chk_auto_resolver.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.chk_auto_resolver)

        # 5. INSTRUCCIONES RÁPIDAS
        box_instrucciones = QFrame()
        box_instrucciones.setObjectName("instruccionesBox")
        box_layout = QVBoxLayout(box_instrucciones)
        box_layout.setContentsMargins(12, 10, 12, 10)
        box_layout.setSpacing(4)

        txt_inst = QLabel(
            "<b>Pasos:</b><br>"
            "1. Conecta el celular a la <b>misma red Wi-Fi</b> que esta PC.<br>"
            "2. Abre la cámara del celular y escanea el código QR de arriba.<br>"
            "3. En la página web que se abre, toma la foto y presiona <b>Enviar</b>."
        )
        txt_inst.setObjectName("txtInstrucciones")
        txt_inst.setWordWrap(True)
        box_layout.addWidget(txt_inst)
        layout.addWidget(box_instrucciones)

        # 6. BOTONES INFERIORES
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(10)

        self.btn_probar_navegador = QPushButton("🌐 Abrir en esta PC")
        self.btn_probar_navegador.setObjectName("btnCopiar")
        self.btn_probar_navegador.setCursor(Qt.PointingHandCursor)
        self.btn_probar_navegador.clicked.connect(self._abrir_en_navegador)

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setObjectName("btnCerrar")
        self.btn_cerrar.clicked.connect(self.close)

        fila_botones.addWidget(self.btn_probar_navegador)
        fila_botones.addStretch()
        fila_botones.addWidget(self.btn_cerrar)
        layout.addLayout(fila_botones)

    def _iniciar_servidor_y_qr(self):
        """Arranca el servidor local y genera el código QR."""
        ok, url_o_error = self.servidor.iniciar()

        if not ok:
            self.lbl_qr.setText("Error al iniciar el servidor local.")
            self.lbl_estado.setText("❌ Error: " + str(url_o_error))
            return

        self.url = self.servidor.obtener_url()
        self.lbl_url.setText(self.url)

        # Generar código QR
        pixmap_qr = self.servidor.generar_qr_pixmap(210)
        if pixmap_qr:
            self.lbl_qr.setPixmap(pixmap_qr)
        else:
            self.lbl_qr.setText("No se pudo dibujar el QR.\nPuede ingresar a la URL directamente.")

        # Conectar señales del servidor
        self.servidor.signals.dispositivo_conectado.connect(self._on_dispositivo_conectado)
        self.servidor.signals.foto_recibida.connect(self._on_foto_recibida)

    def _on_dispositivo_conectado(self, ip_cliente):
        """Actualiza el badge cuando el smartphone abre la página."""
        self.lbl_estado.setText(f"🟢 Celular conectado ({ip_cliente}). Listo para tomar foto.")
        self.lbl_estado.setStyleSheet(
            "font-size: 12px; font-weight: bold; padding: 6px 12px; "
            "border-radius: 10px; background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0;"
        )

    def _on_foto_recibida(self, imagen_bytes, mime, nota):
        """Maneja la recepción de la foto enviada desde el móvil."""
        self.lbl_estado.setText("🎉 ¡Foto recibida con éxito! Transfiriendo...")
        self.lbl_estado.setStyleSheet(
            "font-size: 12px; font-weight: bold; padding: 6px 12px; "
            "border-radius: 10px; background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A;"
        )

        auto_resolver = self.chk_auto_resolver.isChecked()

        # Emitir señal hacia la ventana Resolver
        self.foto_recibida_senal.emit(imagen_bytes, mime, nota, auto_resolver)

        # Cerrar automáticamente el modal tras 800ms para mostrar la resolución
        QTimer.singleShot(700, self.accept)

    def _copiar_url(self):
        clipboard = QApplication.clipboard()
        if hasattr(self, "url"):
            clipboard.setText(self.url)
            self.btn_copiar.setText("✅ ¡Copiado!")
            QTimer.singleShot(2000, lambda: self.btn_copiar.setText("📋 Copiar"))

    def _abrir_en_navegador(self):
        import webbrowser
        if hasattr(self, "url"):
            webbrowser.open(self.url)

    def closeEvent(self, event):
        # Detener el servidor al cerrar el diálogo
        if self.servidor:
            self.servidor.detener()
        super().closeEvent(event)


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = DialogoQR()
    dlg.foto_recibida_senal.connect(
        lambda b, m, n, ar: print(f"Foto recibida ({len(b)} bytes, nota='{n}', auto={ar})")
    )
    dlg.show()
    sys.exit(app.exec_())
