from PyQt5.QtWidgets import QMessageBox


class Mensajes:

    # ==========================================
    # MENSAJE DE INFORMACIÓN
    # ==========================================

    @staticmethod
    def informacion(parent, titulo, mensaje):

        QMessageBox.information(
            parent,
            titulo,
            mensaje
        )

    # ==========================================
    # MENSAJE DE ADVERTENCIA
    # ==========================================

    @staticmethod
    def advertencia(parent, titulo, mensaje):

        QMessageBox.warning(
            parent,
            titulo,
            mensaje
        )

    # ==========================================
    # MENSAJE DE ERROR
    # ==========================================

    @staticmethod
    def error(parent, titulo, mensaje):

        QMessageBox.critical(
            parent,
            titulo,
            mensaje
        )

    # ==========================================
    # MENSAJE DE CONFIRMACIÓN
    # ==========================================

    @staticmethod
    def confirmar(parent, titulo, mensaje):

        respuesta = QMessageBox.question(

            parent,

            titulo,

            mensaje,

            QMessageBox.Yes | QMessageBox.No,

            QMessageBox.No

        )

        return respuesta == QMessageBox.Yes

    # ==========================================
    # MENSAJE DE ÉXITO
    # ==========================================

    @staticmethod
    def exito(parent, mensaje):

        QMessageBox.information(

            parent,

            "Operación Exitosa",

            mensaje

        )

    # ==========================================
    # MENSAJE DE ERROR SQLITE
    # ==========================================

    @staticmethod
    def error_bd(parent, error):

        QMessageBox.critical(

            parent,

            "Error de Base de Datos",

            str(error)

        )

    # ==========================================
    # MENSAJE DE ERROR API IA
    # ==========================================

    @staticmethod
    def error_api(parent):

        QMessageBox.critical(

            parent,

            "Error de Inteligencia Artificial",

            "No fue posible obtener una respuesta de la IA.\n"
            "Verifique la conexión a Internet o la API."

        )

    # ==========================================
    # MENSAJE DE CAMPO VACÍO
    # ==========================================

    @staticmethod
    def campo_vacio(parent):

        QMessageBox.warning(

            parent,

            "Campos Vacíos",

            "Debe completar todos los campos."

        )

    # ==========================================
    # MENSAJE DE USUARIO DUPLICADO
    # ==========================================

    @staticmethod
    def usuario_existente(parent):

        QMessageBox.warning(

            parent,

            "Usuario Existente",

            "Ese nombre de usuario ya está registrado."

        )

    # ==========================================
    # MENSAJE DE CONTRASEÑA INCORRECTA
    # ==========================================

    @staticmethod
    def contraseña_incorrecta(parent):

        QMessageBox.critical(

            parent,

            "Inicio de Sesión",

            "Usuario o contraseña incorrectos."

        )