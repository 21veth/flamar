import hashlib
import hmac
import secrets
import string
import uuid

import psycopg
from argon2 import PasswordHasher

from repositories.recuperacion_repository import RecuperacionRepository
from services.envios_recuperacion import EnviosRecuperacion
from services.usuarios_service import UsuariosService


MENSAJE_SOLICITUD = ('Solicitud recibida. Si la cuenta está activa y no ha superado los límites, '
                      'quedará en espera de autorización del administrador. Puedes cerrar el sistema: la solicitud se conserva. '
                     'El administrador deberá completar el correo si falta. El código solo se enviará después de aprobarla. '
                     'Espera 2 minutos antes de volver a solicitar.')

MOTIVOS_ENVIO = {
    'configuracion': 'Revisa las variables SMTP y la activación del correo.',
    'autenticacion': 'El servidor rechazó las credenciales SMTP. Revisa la contraseña de aplicación.',
    'tls': 'No se pudo establecer TLS. Revisa el puerto y el modo SSL/STARTTLS.',
    'conexion': 'No se pudo conectar al servidor SMTP.',
    'destinatario': 'El servidor rechazó el correo del destinatario.',
    'remitente': 'El servidor rechazó el remitente configurado.',
    'proveedor': 'El proveedor no confirmó el envío.',
    'flujo_anterior': 'Solicitud trasladada al nuevo flujo de autorización previa.',
}


class RecuperacionService:
    def __init__(self, sesion=None, repositorio=None, envios=None, hasher=None):
        self.sesion = sesion
        self.repo = repositorio if repositorio is not None else RecuperacionRepository()
        self.envios = envios if envios is not None else EnviosRecuperacion()
        self.hasher = hasher if hasher is not None else PasswordHasher()

    @staticmethod
    def generar_codigo():
        alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        while True:
            codigo = ''.join(secrets.choice(alfabeto) for _ in range(8))
            if any(c in string.ascii_uppercase for c in codigo) and any(c.isdigit() for c in codigo):
                return codigo

    @staticmethod
    def _token_hash(token):
        if not isinstance(token, str) or not 32 <= len(token) <= 128:
            raise ValueError('Solicitud no válida. Solicita un nuevo código.')
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def _codigo_hash(self, token_hash, codigo):
        secreto = self.envios.config.get('secreto', '')
        if len(secreto) < 32:
            raise ValueError('La recuperación todavía no está configurada. Contacta al administrador.')
        return hmac.new(secreto.encode('utf-8'), (token_hash + ':' + codigo).encode('utf-8'), hashlib.sha256).hexdigest()

    def _admin(self):
        if not self.sesion or not self.sesion.es_administrador:
            raise PermissionError('Solo un administrador puede revisar solicitudes.')
        return self.sesion.id_usuario

    @staticmethod
    def _ocultar(destino, canal):
        if not destino:
            return 'Sin correo registrado'
        if canal == 'correo':
            local, dominio = destino.rsplit('@', 1)
            return local[:1] + '***@' + dominio
        return '+' + '•' * 6 + destino[-3:]

    def ejecutar(self, accion, **datos):
        try:
            return self._ejecutar(accion, datos)
        except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedColumn):
            raise ValueError('El esquema de recuperación no está instalado. Contacta al administrador; su definición está en database/flamar_postgres.sql.') from None
        except psycopg.Error:
            raise ValueError('No se pudo completar la operación. Comprueba la conexión e inténtalo de nuevo.') from None

    def _ejecutar(self, accion, datos):
        if accion == 'configuracion':
            return {'accion': accion, 'canales': {'correo': bool(self.envios.disponibles().get('correo'))}}
        if accion == 'solicitar':
            usuario, canal = datos.get('usuario'), datos.get('canal', 'correo')
            if not isinstance(usuario, str) or not usuario.strip() or len(usuario) > 100:
                raise ValueError('Introduce tu nombre de usuario.')
            if canal != 'correo':
                raise ValueError('La recuperación solo está disponible por correo electrónico.')
            token = secrets.token_urlsafe(32)
            token_hash = self._token_hash(token)
            self.repo.preparar(usuario.strip(), canal, token_hash)
            return {'accion': accion, 'token': token, 'mensaje': MENSAJE_SOLICITUD}
        if accion == 'retomar':
            usuario, codigo = datos.get('usuario'), datos.get('codigo', '')
            if not isinstance(usuario, str) or not usuario.strip() or len(usuario) > 100:
                raise ValueError('Introduce tu nombre de usuario.')
            if not isinstance(codigo, str) or len(codigo.strip()) != 8 or not codigo.strip().isascii() or not codigo.strip().isalnum():
                raise ValueError('Introduce el código de 8 letras y números.')
            codigo = codigo.strip().upper()
            token = secrets.token_urlsafe(32)
            token_hash = self._token_hash(token)
            estado = self.repo.retomar(usuario.strip(), lambda anterior: self._codigo_hash(anterior, codigo),
                                      token_hash, self._codigo_hash(token_hash, codigo))
            if not estado:
                raise ValueError('No se pudo retomar: usuario o código no válidos, solicitud caducada o sin intentos disponibles.')
            return {'accion': accion, 'token': token, 'estado': estado}
        if accion in ('verificar', 'estado', 'restablecer'):
            token_hash = self._token_hash(datos.get('token'))
            if accion == 'verificar':
                codigo = datos.get('codigo', '')
                if not isinstance(codigo, str) or len(codigo.strip()) != 8 or not codigo.strip().isascii() or not codigo.strip().isalnum():
                    raise ValueError('Introduce el código de 8 letras y números.')
                estado = self.repo.verificar(token_hash, self._codigo_hash(token_hash, codigo.strip().upper()))
                if not estado:
                    raise ValueError('Código no válido, caducado o sin intentos disponibles. Puedes solicitar otro.')
                return {'accion': accion, 'estado': estado}
            if accion == 'estado':
                return {'accion': accion, 'estado': self.repo.estado(token_hash)}
            if self.repo.estado(token_hash) != 'aprobada':
                raise ValueError('La solicitud no está aprobada, ha caducado o ya no es válida. Consulta su estado o solicita otro código.')
            contrasena = datos.get('contrasena')
            # Comparte la política de 6 a 128 caracteres con Gestión de usuarios.
            validacion = UsuariosService(None, hasher=self.hasher)
            password_hash = validacion._password_hash(contrasena, obligatorio=True)
            if not self.repo.cambiar_password(token_hash, password_hash):
                raise ValueError('La solicitud no está aprobada, ha caducado o ya no es válida. Consulta su estado o solicita otro código.')
            return {'accion': accion, 'estado': 'completada'}
        if accion in ('listar', 'notificaciones'):
            actor = self._admin()
            filas = self.repo.listar(actor, solo_notificaciones=accion == 'notificaciones')
            if accion == 'notificaciones':
                return {'accion': accion, 'ids': filas, 'pendientes': len(filas)}
            solicitudes = []
            for fila in filas:
                item = dict(fila)
                item['id_solicitud'] = str(item['id_solicitud'])
                item['destino'] = self._ocultar(item['destino'], item['canal'])
                item['detalle_envio'] = MOTIVOS_ENVIO.get(item.get('envio_error'), '')
                solicitudes.append(item)
            return {'accion': accion, 'solicitudes': solicitudes}
        if accion in ('aprobar', 'rechazar'):
            actor = self._admin()
            try:
                identificador = uuid.UUID(str(datos.get('id_solicitud')))
            except (ValueError, AttributeError):
                raise ValueError('Selecciona una solicitud válida.') from None
            codigo = self.generar_codigo() if accion == 'aprobar' else None
            decision = self.repo.resolver(actor, identificador, aprobar=accion == 'aprobar',
                                          calcular_hash=(lambda token: self._codigo_hash(token, codigo)) if codigo else None)
            if decision['estado'] == 'rechazada':
                return {'accion': accion, 'estado': 'rechazada', 'mensaje': 'Solicitud denegada. No se envió ningún código.'}
            if decision['estado'] != 'enviando':
                raise ValueError('La solicitud ya no está disponible o ya tiene un código enviado. Actualiza la lista.')
            motivo = None
            try:
                self.envios.enviar(decision['canal'], decision['destino'], codigo)
                enviado = True
            except ValueError as error:
                enviado = False
                motivo = getattr(error, 'motivo', 'proveedor')
                if motivo not in MOTIVOS_ENVIO:
                    motivo = 'proveedor'
            estado = self.repo.confirmar_envio(identificador, decision['codigo_hash'], enviado, motivo)
            mensaje = ('Solicitud autorizada. El servidor aceptó el código por correo.' if estado == 'codigo_enviado'
                       else 'La autorización quedó guardada, pero el correo no pudo enviarse. '
                       + MOTIVOS_ENVIO.get(motivo, 'Actualiza la lista para consultar el estado.'))
            return {'accion': accion, 'estado': estado, 'mensaje': mensaje}
        raise ValueError('Operación de recuperación no válida.')
