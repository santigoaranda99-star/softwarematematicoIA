class Usuario:
    """
    Modelo que representa un usuario del sistema.
    """

    def __init__(self, id=None, nombre="", usuario="", contraseña=""):

        self.id = id
        self.nombre = nombre
        self.usuario = usuario
        self.contraseña = contraseña

    # ==========================================
    # GETTERS
    # ==========================================

    def get_id(self):
        """Devuelve el id del usuario."""
        return self.id

    def get_nombre(self):
        """Devuelve el nombre completo del usuario."""
        return self.nombre

    def get_usuario(self):
        """Devuelve el nombre de usuario (login)."""
        return self.usuario

    def get_contraseña(self):
        """Devuelve la contraseña (hash almacenado)."""
        return self.contraseña

    # ==========================================
    # SETTERS
    # ==========================================

    def set_nombre(self, nombre):
        """Establece el nombre completo del usuario."""
        self.nombre = nombre

    def set_usuario(self, usuario):
        """Establece el nombre de usuario (login)."""
        self.usuario = usuario

    def set_contraseña(self, contraseña):
        """Establece la contraseña (se almacena el hash)."""
        self.contraseña = contraseña

    # ==========================================
    # CONVERTIR A DICCIONARIO
    # ==========================================

    def to_dict(self):

        return {

            "id": self.id,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "contraseña": self.contraseña

        }

    # ==========================================
    # REPRESENTACIÓN DEL OBJETO
    # ==========================================

    def __str__(self):

        return (

            f"Usuario("
            f"id={self.id}, "
            f"nombre='{self.nombre}', "
            f"usuario='{self.usuario}')"

        )