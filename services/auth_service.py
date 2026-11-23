import secrets
import threading
import time
from dataclasses import dataclass, field

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


@dataclass(frozen=True)
class CambioPasswordPendiente:
    """No es una sesión: no permite abrir el sistema ni contiene roles o contraseñas."""

    usuario: str
    token: str = field(repr=False)


class AuthService:
    def __init__(self, repositorio=None):
        self._repositorio = repositorio if repositorio is not None else UsuarioRepository()
        self._hasher = PasswordHasher()
        self._pendientes = {}
        self._lock = threading.Lock()

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

        if registro.get('debe_cambiar_password'):
            now = time.monotonic()
            token = secrets.token_urlsafe(32)
            with self._lock:
                self._pendientes = {key: item for key, item in self._pendientes.items()
                                    if item[2] > now and item[0] != registro['id_usuario']}
                if len(self._pendientes) >= 100:
                    self._pendientes.pop(next(iter(self._pendientes)))
                self._pendientes[token] = (registro['id_usuario'], registro['password_hash'], now + 600)
            return CambioPasswordPendiente(registro['usuario'], token)

        try:
            self._repositorio.actualizar_ultimo_acceso(registro['id_usuario'])
        except psycopg.Error:
            raise ErrorDeConexionError(MENSAJE_CONEXION) from None

        return SesionUsuario(
            id_usuario=registro['id_usuario'],
            usuario=registro['usuario'],
            rol=registro['rol'],
        )

    def cancelar_cambio(self, token):
        if not isinstance(token, str):
            return
        with self._lock:
            self._pendientes.pop(token, None)

    def cambiar_password_inicial(self, token, nueva, confirmacion):
        with self._lock:
            pendiente = self._pendientes.get(token) if isinstance(token, str) else None
        if pendiente is None or pendiente[2] <= time.monotonic():
            if isinstance(token, str):
                self.cancelar_cambio(token)
            raise ValueError('Este acceso ha caducado. Vuelve a iniciar sesión con tu clave temporal.')
        if not isinstance(nueva, str) or not 8 <= len(nueva) <= 128 or not nueva.strip():
            raise ValueError('La nueva contraseña debe tener entre 8 y 128 caracteres y no contener solo espacios.')
        if nueva != confirmacion:
            raise ValueError('Las contraseñas no coinciden.')
        try:
            self._hasher.verify(pendiente[1], nueva)
        except VerificationError:
            pass
        else:
            raise ValueError('Elige una contraseña diferente de la clave temporal.')
        password_hash = self._hasher.hash(nueva)
        with self._lock:
            if self._pendientes.get(token) != pendiente or pendiente[2] <= time.monotonic():
                self._pendientes.pop(token, None)
                raise ValueError('Este acceso ha caducado. Vuelve a iniciar sesión con tu clave temporal.')
            try:
                registro = self._repositorio.completar_password_inicial(pendiente[0], pendiente[1], password_hash)
            except psycopg.Error:
                raise ErrorDeConexionError(MENSAJE_CONEXION) from None
            self._pendientes.pop(token, None)
        if registro is None:
            raise ValueError('La cuenta o su clave temporal ya no están disponibles. Vuelve a iniciar sesión.')
        return SesionUsuario(registro['id_usuario'], registro['usuario'], registro['rol'])
