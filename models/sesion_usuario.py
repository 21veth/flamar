class SesionUsuario:
    """Usuario autenticado: contiene únicamente id_usuario, usuario y rol."""

    def __init__(self, id_usuario, usuario, rol):
        self.id_usuario = id_usuario
        self.usuario = usuario
        self.rol = rol

    @property
    def iniciales(self):
        palabras = self.usuario.strip().split()
        letras = [palabra[:1] for palabra in palabras[:2] if palabra]
        return ''.join(letras).upper()

    @property
    def rol_mostrar(self):
        return (self.rol or '').strip().capitalize()
