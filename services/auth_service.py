import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from models.sesion_usuario import SesionUsuario
from repositories.usuario_repository import UsuarioRepository


MENSAJE_CREDENCIALES = 'Usuario o contraseña incorrectos, o cuenta no disponible'
MENSAJE_CONEXION = 'No se pudo conectar con la base de datos. Verifica la conexión e inténtalo de nuevo.'


class CredencialesInvalidasError(Exception):
    """Usuario inexistente, contraseña incorrecta o cuenta no disponible."""


class ErrorDeConexionError(Exception):
    """No se pudo acceder a la base de datos."""


class AuthService:
    def __init__(self, repositorio=None):
        self._repositorio = repositorio if repositorio is not None else UsuarioRepository()
        self._hasher = PasswordHasher()

    def autenticar(self, usuario, contrasena):
        try:
            registro = self._repositorio.obtener_por_usuario(usuario)
        except psycopg.Error:
            raise ErrorDeConexionError(MENSAJE_CONEXION) from None

        if registro is None or not registro.get('activo'):
            raise CredencialesInvalidasError(MENSAJE_CREDENCIALES)

        try:
            self._hasher.verify(registro.get('password_hash') or '', contrasena)
        except (VerificationError, InvalidHashError):
            raise CredencialesInvalidasError(MENSAJE_CREDENCIALES) from None

        try:
            self._repositorio.actualizar_ultimo_acceso(registro['id_usuario'])
        except psycopg.Error:
            raise ErrorDeConexionError(MENSAJE_CONEXION) from None

        return SesionUsuario(
            id_usuario=registro['id_usuario'],
            usuario=registro['usuario'],
            rol=registro['rol'],
        )
