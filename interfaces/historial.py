from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QApplication,
    QHeaderView,
    QDialog,
    QTextEdit
)

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import sqlite3
import sys

from database.conexion import obtener_conexion
from utils.ventanas import centrar_ventana, centrar_dialogo


class Historial(QWidget):

    def __init__(self, usuario="Usuario"):
        super().__init__()

        self.usuario = usuario

        self.registros = []

        self.setWindowTitle("Historial de Consultas")
        self.setMinimumSize(850, 550)
        self.resize(1000, 650)
        from utils.ventanas import centrar_ventana
        centrar_ventana(self)

        self.setStyleSheet("""

            QWidget{
                background:#F1F5F9;
                font-family:"Segoe UI";
            }

            QLabel{
                color:#0F172A;
            }

            QTableWidget{
                background:white;
                border:2px solid #D1D5DB;
                border-radius:8px;
                font-size:12px;
                gridline-color:#E5E7EB;
                color:#0F172A;
            }

            QHeaderView::section{
                background:#2563EB;
                color:white;
                padding:8px;
                border:none;
                font-weight:bold;
            }

            QPushButton{

                background:#2563EB;
                color:white;
                border:none;
                border-radius:8px;
                padding:12px;
                font-size:14px;
                font-weight:bold;

            }

            QPushButton:hover{

                background:#1D4ED8;

            }

            QPushButton#btnPeligro{

                background:#DC2626;

            }

            QPushButton#btnPeligro:hover{

                background:#B91C1C;

            }

        """)

        layout = QVBoxLayout()

        layout.setContentsMargins(25,25,25,25)

        titulo = QLabel("Historial de Consultas Matemáticas")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Segoe UI",20,QFont.Bold))

        usuario = QLabel(f"Usuario: {self.usuario}")
        usuario.setAlignment(Qt.AlignCenter)

        self.tabla = QTableWidget()

        self.tabla.setColumnCount(5)

        self.tabla.setHorizontalHeaderLabels([

            "Fecha",
            "Hora",
            "Problema",
            "Procedimiento",
            "Resultado"

        ])

        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.tabla.setWordWrap(True)

        self.tabla.verticalHeader().setVisible(False)

        self.btnActualizar = QPushButton("🔄 Actualizar")

        self.btnVolver = QPushButton("⬅ Volver al Menú")

        self.btnBorrar = QPushButton("🗑 Borrar historial")
        self.btnBorrar.setObjectName("btnPeligro")
        self.btnBorrar.setToolTip(
            "Elimina TODAS las operaciones guardadas de este usuario"
        )

        self.btnActualizar.clicked.connect(self.cargar_historial)

        self.btnBorrar.clicked.connect(self.borrar_historial)

        self.btnVolver.clicked.connect(self.volver_menu)

        self.tabla.cellDoubleClicked.connect(self.ver_detalle)

        fila_botones = QHBoxLayout()
        fila_botones.addWidget(self.btnActualizar)
        fila_botones.addWidget(self.btnBorrar)

        layout.addWidget(titulo)

        layout.addWidget(usuario)

        layout.addWidget(self.tabla)

        layout.addLayout(fila_botones)

        layout.addWidget(self.btnVolver)

        self.setLayout(layout)

        centrar_ventana(self)

        from utils.tema import instalar_modo_oscuro

        instalar_modo_oscuro(self, self.styleSheet())

        self.cargar_historial()

    # ----------------------------------------------------
    # CARGAR HISTORIAL DEL USUARIO
    # ----------------------------------------------------

    def cargar_historial(self):

        try:

            conexion = obtener_conexion()

            cursor = conexion.cursor()

            cursor.execute("""

                SELECT fecha,hora,problema,procedimiento,resultado

                FROM historial

                WHERE usuario=?

                ORDER BY id DESC

            """,(self.usuario,))

            self.registros = cursor.fetchall()

            conexion.close()

            self.tabla.setRowCount(len(self.registros))

            for fila, registro in enumerate(self.registros):

                self.tabla.setItem(
                    fila,
                    0,
                    QTableWidgetItem(str(registro["fecha"]))
                )

                self.tabla.setItem(
                    fila,
                    1,
                    QTableWidgetItem(str(registro["hora"]))
                )

                self.tabla.setItem(
                    fila,
                    2,
                    QTableWidgetItem(str(registro["problema"]))
                )

                self.tabla.setItem(
                    fila,
                    3,
                    QTableWidgetItem(str(registro["procedimiento"]))
                )

                self.tabla.setItem(
                    fila,
                    4,
                    QTableWidgetItem(str(registro["resultado"]))
                )

        except sqlite3.Error as error:

            QMessageBox.critical(
                self,
                "SQLite",
                str(error)
            )

    # ----------------------------------------------------
    # BORRAR TODO EL HISTORIAL DEL USUARIO
    # ----------------------------------------------------

    def borrar_historial(self):

        if not self.registros:

            QMessageBox.information(
                self,
                "Historial",
                "No hay operaciones guardadas para borrar."
            )
            return

        respuesta = QMessageBox.question(
            self,
            "Borrar historial",
            f"¿Seguro que deseas eliminar las {len(self.registros)} "
            f"operaciones de {self.usuario}?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if respuesta != QMessageBox.Yes:
            return

        try:

            conexion = obtener_conexion()

            cursor = conexion.cursor()

            cursor.execute(
                "DELETE FROM historial WHERE usuario=?",
                (self.usuario,)
            )

            conexion.commit()

            conexion.close()

            self.registros = []

            self.tabla.setRowCount(0)

            QMessageBox.information(
                self,
                "Historial",
                "Historial borrado correctamente."
            )

        except sqlite3.Error as error:

            QMessageBox.critical(
                self,
                "SQLite",
                str(error)
            )

    # ----------------------------------------------------
    # VER DETALLE (procedimiento y resultado en secciones)
    # ----------------------------------------------------

    def ver_detalle(self, fila, _columna):

        if fila < 0 or fila >= len(self.registros):
            return

        registro = self.registros[fila]

        dialogo = QDialog(self)
        dialogo.setWindowTitle(
            f"Consulta - {registro['fecha']} {registro['hora']}"
        )
        dialogo.resize(760, 600)

        layout = QVBoxLayout(dialogo)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        lbl_problema = QLabel("📋 Problema")
        txt_problema = QTextEdit(str(registro["problema"]))
        txt_problema.setReadOnly(True)
        txt_problema.setFixedHeight(80)

        lbl_procedimiento = QLabel("🧮 Procedimiento")
        txt_procedimiento = QTextEdit(str(registro["procedimiento"]))
        txt_procedimiento.setReadOnly(True)

        lbl_resultado = QLabel("✅ Resultado")
        txt_resultado = QTextEdit(str(registro["resultado"]))
        txt_resultado.setReadOnly(True)
        txt_resultado.setFixedHeight(110)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialogo.accept)

        centrar_dialogo(dialogo, self)

        for widget in (
            lbl_problema,
            txt_problema,
            lbl_procedimiento,
            txt_procedimiento,
            lbl_resultado,
            txt_resultado,
            btn_cerrar
        ):
            layout.addWidget(widget)

        dialogo.exec_()
    # ----------------------------------------------------

    def volver_menu(self):

        from interfaces.menu import MenuPrincipal
        from controllers.usuario_controller import UsuarioController

        nombre = self.usuario

        datos = UsuarioController.buscar_usuario(self.usuario)

        if datos:
            nombre = datos["nombre"]

        self.menu = MenuPrincipal(nombre, self.usuario)
        self.menu.show()
        self.close()


# --------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = Historial("Santiago Peña")

    ventana.show()

    sys.exit(app.exec_())
