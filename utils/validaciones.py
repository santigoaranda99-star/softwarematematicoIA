import re


class Validaciones:

    # ==========================================
    # CAMPOS VACÍOS
    # ==========================================

    @staticmethod
    def campo_vacio(texto):

        return texto.strip() == ""

    # ==========================================
    # LONGITUD MÍNIMA
    # ==========================================

    @staticmethod
    def longitud_minima(texto, minimo):

        return len(texto.strip()) >= minimo

    # ==========================================
    # VALIDAR USUARIO
    # ==========================================

    @staticmethod
    def usuario_valido(usuario):

        patron = r"^[a-zA-Z0-9_]{4,20}$"

        return re.match(patron, usuario) is not None

    # ==========================================
    # VALIDAR CONTRASEÑA
    # ==========================================

    @staticmethod
    def contraseña_valida(contraseña):

        """
        Mínimo:
        - 8 caracteres
        - una mayúscula
        - una minúscula
        - un número
        """

        patron = (
            r"^(?=.*[a-z])"
            r"(?=.*[A-Z])"
            r"(?=.*\d)"
            r".{8,}$"
        )

        return re.match(patron, contraseña) is not None

    # ==========================================
    # VALIDAR NOMBRE
    # ==========================================

    @staticmethod
    def nombre_valido(nombre):

        patron = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$"

        return re.match(patron, nombre) is not None

    # ==========================================
    # VALIDAR EMAIL (OPCIONAL)
    # ==========================================

    @staticmethod
    def email_valido(email):

        patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        return re.match(patron, email) is not None

    # ==========================================
    # COMPARAR CONTRASEÑAS
    # ==========================================

    @staticmethod
    def contraseñas_iguales(c1, c2):

        return c1 == c2

    # ==========================================
    # VALIDAR PROBLEMA MATEMÁTICO
    # ==========================================

    @staticmethod
    def problema_valido(problema):

        return len(problema.strip()) > 0