import re

import psycopg
from argon2 import PasswordHasher

from repositories.usuario_repository import UsuarioRepository


ROLES = ('administrador', 'gerente', 'trabajador')


class UsuariosService:
    """Gestión administrativa sobre usuarios reales, sin exponer credenciales."""

    def __init__(self, sesion, repositorio=None, hasher=None):
        self.sesion = sesion
        self._repositorio = repositorio if repositorio is not None else UsuarioRepository()
        self._hasher = hasher if hasher is not None else PasswordHasher()

    @staticmethod
    def _id(valor):
        if type(valor) is not int or valor <= 0:
            raise ValueError('Selecciona un usuario válido.')
        return valor

    @staticmethod
    def _datos(usuario, rol, activo):
        if not isinstance(usuario, str) or not usuario.strip() or len(usuario.strip()) > 100:
            raise ValueError('El usuario debe tener entre 1 y 100 caracteres.')
        if any(ord(letra) < 32 or ord(letra) == 127 for letra in usuario):
            raise ValueError('El usuario no puede contener saltos de línea ni caracteres de control.')
        if rol not in ROLES:
            raise ValueError('Selecciona un rol válido.')
        if type(activo) is not bool:
            raise ValueError('Selecciona un estado válido.')
        return usuario.strip()

    def _password_hash(self, contrasena, obligatorio=False):
        if not isinstance(contrasena, str):
            raise ValueError('Introduce una contraseña válida.')
        if not contrasena and not obligatorio:
            return None
        if not 6 <= len(contrasena) <= 128 or not contrasena.strip():
            raise ValueError('La contraseña debe tener entre 6 y 128 caracteres y no puede contener solo espacios.')
        return self._hasher.hash(contrasena)

    @staticmethod
    def _correo(valor):
        if valor is None:
            return None
        if not isinstance(valor, str) or any(ord(c) < 32 or ord(c) == 127 for c in valor):
            raise ValueError('Introduce un correo electrónico válido.')
        valor = valor.strip().lower()
        if not valor:
            return None
        patron = r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+"
        if len(valor) > 254 or re.fullmatch(patron, valor) is None:
            raise ValueError('Introduce un correo válido, por ejemplo nombre@dominio.com.')
        local, dominio = valor.rsplit('@', 1)
        if len(local) > 64 or local.startswith('.') or local.endswith('.') or '..' in local or any(
            len(parte) > 63 or parte.startswith('-') or parte.endswith('-') for parte in dominio.split('.')
        ):
            raise ValueError('Introduce un correo electrónico válido.')
        return valor

    @staticmethod
    def _telefono(valor):
        if valor is None:
            return None
        if not isinstance(valor, str) or any(ord(c) < 32 or ord(c) == 127 for c in valor):
            raise ValueError('Introduce un teléfono válido con código de país.')
        valor = valor.strip()
        if not valor:
            return None
        if len(valor) > 40:
            raise ValueError('El teléfono es demasiado largo.')
        valor = re.sub(r'[ ()-]', '', valor)
        if re.fullmatch(r'\+[1-9][0-9]{7,14}', valor) is None:
            raise ValueError('Incluye el código de país con + y entre 8 y 15 dígitos, por ejemplo +51 987 654 321.')
        return valor

    def ejecutar(self, accion, **datos):
        if not self.sesion.es_administrador:
            raise PermissionError('Solo un administrador puede gestionar usuarios.')
        actor = self._id(self.sesion.id_usuario)
        try:
            if accion == 'listar':
                buscar = datos.get('buscar', '')
                rol, activo = datos.get('rol'), datos.get('activo')
                if not isinstance(buscar, str) or len(buscar) > 254:
                    raise ValueError('La búsqueda admite hasta 254 caracteres.')
                if rol is not None and rol not in ROLES:
                    raise ValueError('Selecciona un rol válido.')
                if activo is not None and type(activo) is not bool:
                    raise ValueError('Selecciona un estado válido.')
                usuarios = self._repositorio.listar(actor, buscar.strip(), rol, activo)
                return {'accion': accion, 'usuarios': usuarios}
            if accion not in ('crear', 'modificar', 'eliminar'):
                raise ValueError('Operación de usuarios no válida.')
            if accion == 'eliminar':
                destino = self._id(datos.get('id_usuario'))
                if destino == actor:
                    raise ValueError('No puedes eliminar tu propia cuenta.')
                self._repositorio.eliminar(actor, destino)
            else:
                nombre = self._datos(datos.get('usuario'), datos.get('rol'), datos.get('activo'))
                destino = self._id(datos.get('id_usuario')) if accion == 'modificar' else None
                if destino == actor and (datos['rol'] != 'administrador' or not datos['activo']):
                    raise ValueError('No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.')
                contacto = {}
                if 'correo' in datos:
                    contacto['correo'] = self._correo(datos['correo'])
                if 'telefono' in datos:
                    contacto['telefono'] = self._telefono(datos['telefono'])
                password_hash = self._password_hash(datos.get('contrasena', ''), obligatorio=accion == 'crear')
                if accion == 'crear':
                    destino = self._repositorio.crear(actor, nombre, password_hash, datos['rol'], datos['activo'], **contacto)
                else:
                    self._repositorio.modificar(actor, destino, nombre, datos['rol'], datos['activo'], password_hash, **contacto)
            return {
                'accion': accion, 'id_usuario': destino,
                'reautenticar': accion == 'modificar' and destino == actor,
            }
        except psycopg.errors.UniqueViolation as error:
            if error.diag.constraint_name == 'uq_usuarios_correo':
                raise ValueError('Ese correo ya pertenece a otro usuario. Introduce uno diferente.') from None
            if error.diag.constraint_name == 'uq_usuarios_telefono':
                raise ValueError('Ese teléfono ya pertenece a otro usuario. Introduce uno diferente.') from None
            raise ValueError('Ese nombre de usuario ya existe. Elige otro.') from None
        except psycopg.errors.UndefinedColumn:
            raise ValueError('La tabla usuarios no coincide con database/flamar_postgres.sql. Revisa las columnas de la base configurada.') from None
        except psycopg.errors.ForeignKeyViolation:
            raise ValueError('Este usuario tiene registros asociados y no se puede eliminar. Puedes desactivar su cuenta.') from None
        except psycopg.Error:
            raise ValueError('No se pudo completar la operación. Comprueba la conexión y vuelve a intentarlo.') from None
