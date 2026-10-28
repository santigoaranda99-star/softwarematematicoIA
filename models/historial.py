class Historial:
    """
    Modelo que representa una consulta matemática realizada
    por un usuario.
    """

    def __init__(
        self,
        id=None,
        usuario="",
        problema="",
        respuesta="",
        procedimiento="",
        resultado="",
        fecha="",
        hora=""
    ):

        self.id = id
        self.usuario = usuario
        self.problema = problema
        self.respuesta = respuesta
        self.procedimiento = procedimiento
        self.resultado = resultado
        self.fecha = fecha
        self.hora = hora

    # ==========================================
    # GETTERS
    # ==========================================

    def get_id(self):
        """Devuelve el id de la consulta."""
        return self.id

    def get_usuario(self):
        """Devuelve el usuario que realizó la consulta."""
        return self.usuario

    def get_problema(self):
        """Devuelve el problema planteado."""
        return self.problema

    def get_respuesta(self):
        """Devuelve la respuesta completa de la IA."""
        return self.respuesta

    def get_procedimiento(self):
        """Devuelve el procedimiento de la solución."""
        return self.procedimiento

    def get_resultado(self):
        """Devuelve el resultado final de la solución."""
        return self.resultado

    def get_fecha(self):
        """Devuelve la fecha de la consulta."""
        return self.fecha

    def get_hora(self):
        """Devuelve la hora de la consulta."""
        return self.hora

    # ==========================================
    # SETTERS
    # ==========================================

    def set_usuario(self, usuario):
        """Establece el usuario de la consulta."""
        self.usuario = usuario

    def set_problema(self, problema):
        """Establece el problema planteado."""
        self.problema = problema

    def set_respuesta(self, respuesta):
        """Establece la respuesta completa de la IA."""
        self.respuesta = respuesta

    def set_procedimiento(self, procedimiento):
        """Establece el procedimiento de la solución."""
        self.procedimiento = procedimiento

    def set_resultado(self, resultado):
        """Establece el resultado final de la solución."""
        self.resultado = resultado

    def set_fecha(self, fecha):
        """Establece la fecha de la consulta."""
        self.fecha = fecha

    def set_hora(self, hora):
        """Establece la hora de la consulta."""
        self.hora = hora

    # ==========================================
    # CONVERTIR A DICCIONARIO
    # ==========================================

    def to_dict(self):

        return {

            "id": self.id,
            "usuario": self.usuario,
            "problema": self.problema,
            "respuesta": self.respuesta,
            "procedimiento": self.procedimiento,
            "resultado": self.resultado,
            "fecha": self.fecha,
            "hora": self.hora

        }

    # ==========================================
    # REPRESENTACIÓN DEL OBJETO
    # ==========================================

    def __str__(self):

        return (

            f"Historial("
            f"id={self.id}, "
            f"usuario='{self.usuario}', "
            f"fecha='{self.fecha}', "
            f"hora='{self.hora}')"

        )
