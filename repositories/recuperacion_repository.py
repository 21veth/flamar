import hashlib
import hmac
import uuid
from contextlib import contextmanager

from psycopg.rows import dict_row

from config.database import obtener_conexion
from config.recuperacion import ESPERA_REENVIO_SEGUNDOS, VIGENCIA_RECUPERACION_HORAS


ACTIVAS = ('pendiente', 'enviando', 'codigo_enviado', 'aprobada', 'envio_fallido')


def firma_password(password_hash):
    return hashlib.sha256(password_hash.encode('utf-8')).hexdigest()


class RecuperacionRepository:
    @contextmanager
    def _cursor(self):
        with obtener_conexion() as conexion:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '15s'")
                cursor.execute('LOCK TABLE public.usuarios IN SHARE ROW EXCLUSIVE MODE')
                cursor.execute('LOCK TABLE public.recuperaciones_password IN SHARE ROW EXCLUSIVE MODE')
                cursor.execute(
                    "UPDATE public.recuperaciones_password SET estado='expirada',codigo_hash=NULL "
                    "WHERE (estado IN ('pendiente','enviando','codigo_enviado','aprobada','envio_fallido') "
                    "AND caduca_en<=CURRENT_TIMESTAMP) OR (estado IN ('codigo_enviado','aprobada') "
                    'AND codigo_caduca_en<=CURRENT_TIMESTAMP) OR '
                    "(estado='aprobada' AND aprobacion_caduca_en<=CURRENT_TIMESTAMP)"
                )
                yield cursor

    @staticmethod
    def _administrador(cursor, id_administrador):
        if type(id_administrador) is not int or id_administrador <= 0:
            raise PermissionError('Solo un administrador activo puede revisar solicitudes.')
        cursor.execute('SELECT rol,activo,debe_cambiar_password FROM public.usuarios WHERE id_usuario=%s', (id_administrador,))
        usuario = cursor.fetchone()
        if not usuario or usuario['rol'] != 'administrador' or not usuario['activo'] or usuario.get('debe_cambiar_password'):
            raise PermissionError('Solo un administrador activo puede revisar solicitudes.')

    @staticmethod
    def _objetivo_valido(cursor, solicitud):
        cursor.execute('SELECT activo,password_hash,correo FROM public.usuarios WHERE id_usuario=%s',
                       (solicitud['id_usuario'],))
        usuario = cursor.fetchone()
        contacto_valido = (solicitud['estado'] == 'pendiente' and not solicitud['destino']) or (
            usuario and usuario['correo'] == solicitud['destino'])
        valido = (solicitud['canal'] == 'correo' and usuario and usuario['activo']
                  and contacto_valido
                  and hmac.compare_digest(firma_password(usuario['password_hash']), solicitud['password_firma']))
        if not valido:
            cursor.execute("UPDATE public.recuperaciones_password SET estado='cancelada',codigo_hash=NULL "
                           'WHERE id_solicitud=%s', (solicitud['id_solicitud'],))
        return bool(valido)

    @staticmethod
    def _aprobador_valido(cursor, solicitud):
        cursor.execute('SELECT rol,activo,debe_cambiar_password FROM public.usuarios WHERE id_usuario=%s', (solicitud['id_administrador'],))
        admin = cursor.fetchone()
        valido = (solicitud['id_administrador'] != solicitud['id_usuario'] and admin
                   and admin['rol'] == 'administrador' and admin['activo'] and not admin.get('debe_cambiar_password'))
        if not valido:
            cursor.execute("UPDATE public.recuperaciones_password SET estado='cancelada',codigo_hash=NULL "
                           'WHERE id_solicitud=%s', (solicitud['id_solicitud'],))
        return bool(valido)

    @staticmethod
    def _fallar_codigo(cursor, solicitud):
        cursor.execute(
            'UPDATE public.recuperaciones_password SET intentos=intentos+1, '
            "estado=CASE WHEN intentos+1>=5 THEN 'bloqueada' ELSE estado END, "
            'codigo_hash=CASE WHEN intentos+1>=5 THEN NULL ELSE codigo_hash END WHERE id_solicitud=%s',
            (solicitud['id_solicitud'],),
        )

    def preparar(self, usuario, canal, token_hash):
        """Encola y confirma la solicitud; no genera ni intenta enviar un código."""
        if canal != 'correo':
            raise ValueError('La recuperación solo está disponible por correo electrónico.')
        with self._cursor() as cursor:
            cursor.execute('SELECT id_usuario,password_hash,correo FROM public.usuarios '
                           'WHERE usuario=%s AND activo=TRUE', (usuario,))
            registro = cursor.fetchone()
            if not registro:
                return False
            cursor.execute(
                "SELECT COUNT(*) FILTER (WHERE solicitado_en>CURRENT_TIMESTAMP-(%s*INTERVAL '1 second')) AS espera, "
                'COUNT(*) AS hora FROM public.recuperaciones_password WHERE id_usuario=%s '
                "AND solicitado_en>CURRENT_TIMESTAMP-INTERVAL '1 hour'",
                (ESPERA_REENVIO_SEGUNDOS, registro['id_usuario']),
            )
            limite = cursor.fetchone()
            if limite['espera'] >= 1 or limite['hora'] >= 3:
                return False
            cursor.execute(
                'INSERT INTO public.recuperaciones_password '
                '(id_solicitud,id_usuario,canal,destino,token_hash,password_firma,estado,codigo_caduca_en,caduca_en) '
                "VALUES (%s,%s,%s,%s,%s,%s,'pendiente',CURRENT_TIMESTAMP+(%s*INTERVAL '1 hour'),"
                "CURRENT_TIMESTAMP+(%s*INTERVAL '1 hour'))",
                (uuid.uuid4(), registro['id_usuario'], canal, registro['correo'] or '', token_hash,
                 firma_password(registro['password_hash']), VIGENCIA_RECUPERACION_HORAS, VIGENCIA_RECUPERACION_HORAS),
            )
            return True

    def resolver(self, id_administrador, id_solicitud, aprobar, calcular_hash=None):
        """La decisión queda confirmada antes de contactar al servidor SMTP."""
        with self._cursor() as cursor:
            self._administrador(cursor, id_administrador)
            cursor.execute(
                'SELECT r.*,envio_intentado_en>CURRENT_TIMESTAMP-(%s*INTERVAL \'1 second\') AS esperar '
                'FROM public.recuperaciones_password r WHERE id_solicitud=%s',
                (ESPERA_REENVIO_SEGUNDOS, id_solicitud),
            )
            solicitud = cursor.fetchone()
            if not solicitud or solicitud['estado'] not in ACTIVAS:
                return {'estado': 'no_disponible'}
            if solicitud['id_usuario'] == id_administrador:
                raise PermissionError('Otro administrador debe revisar la recuperación de tu cuenta.')
            if not self._objetivo_valido(cursor, solicitud):
                return {'estado': 'cancelada'}
            if not aprobar:
                cursor.execute("UPDATE public.recuperaciones_password SET estado='rechazada',codigo_hash=NULL,"
                               'id_administrador=%s,resuelto_en=CURRENT_TIMESTAMP WHERE id_solicitud=%s',
                               (id_administrador, id_solicitud))
                return {'estado': 'rechazada'}
            if solicitud['estado'] not in ('pendiente', 'envio_fallido', 'enviando'):
                return {'estado': 'ya_autorizada'}
            if solicitud['esperar']:
                raise ValueError('Espera 2 minutos desde el último intento antes de volver a enviar el código.')
            if solicitud['envio_intentos'] >= 3:
                raise ValueError('Se alcanzaron 3 intentos de envío para esta solicitud. Revisa SMTP antes de pedir otra.')
            if not solicitud['destino']:
                cursor.execute('SELECT correo FROM public.usuarios WHERE id_usuario=%s', (solicitud['id_usuario'],))
                correo = cursor.fetchone()['correo']
                if not correo:
                    raise ValueError('Registra primero el correo del usuario en Gestión de usuarios. '
                                     'La solicitud sigue pendiente; todavía no se ha autorizado ni enviado el código.')
                cursor.execute('UPDATE public.recuperaciones_password SET destino=%s WHERE id_solicitud=%s',
                               (correo, id_solicitud))
                solicitud['destino'] = correo
            codigo_hash = calcular_hash(solicitud['token_hash'])
            cursor.execute(
                "UPDATE public.recuperaciones_password SET estado='enviando',codigo_hash=%s,intentos=0,"
                'verificado_en=NULL,id_administrador=%s,resuelto_en=CURRENT_TIMESTAMP,aprobacion_caduca_en=caduca_en,'
                'envio_intentado_en=CURRENT_TIMESTAMP,envio_intentos=envio_intentos+1,envio_error=NULL '
                'WHERE id_solicitud=%s', (codigo_hash, id_administrador, id_solicitud),
            )
            return {'estado': 'enviando', 'id_solicitud': id_solicitud, 'codigo_hash': codigo_hash,
                    'destino': solicitud['destino'], 'canal': solicitud['canal']}

    def confirmar_envio(self, id_solicitud, codigo_hash, enviado, motivo=None):
        with self._cursor() as cursor:
            cursor.execute(
                'UPDATE public.recuperaciones_password SET estado=%s,envio_error=%s,'
                'codigo_hash=CASE WHEN %s THEN codigo_hash ELSE NULL END '
                "WHERE id_solicitud=%s AND codigo_hash=%s AND estado='enviando' RETURNING estado",
                ('codigo_enviado' if enviado else 'envio_fallido', None if enviado else motivo,
                 enviado, id_solicitud, codigo_hash),
            )
            fila = cursor.fetchone()
            return fila['estado'] if fila else 'no_disponible'

    def verificar(self, token_hash, codigo_hash):
        with self._cursor() as cursor:
            cursor.execute('SELECT * FROM public.recuperaciones_password WHERE token_hash=%s', (token_hash,))
            solicitud = cursor.fetchone()
            if not solicitud or solicitud['estado'] not in ('codigo_enviado', 'aprobada'):
                return None
            if not self._objetivo_valido(cursor, solicitud) or not self._aprobador_valido(cursor, solicitud):
                return None
            if solicitud['estado'] == 'aprobada' and solicitud['verificado_en']:
                return 'aprobada'
            if not hmac.compare_digest(solicitud['codigo_hash'] or '', codigo_hash):
                self._fallar_codigo(cursor, solicitud)
                return None
            cursor.execute("UPDATE public.recuperaciones_password SET estado='aprobada',verificado_en=CURRENT_TIMESTAMP "
                           'WHERE id_solicitud=%s', (solicitud['id_solicitud'],))
            return 'aprobada'

    def retomar(self, usuario, calcular_hash, nuevo_token_hash, nuevo_codigo_hash):
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT r.* FROM public.recuperaciones_password r JOIN public.usuarios u USING (id_usuario) '
                "WHERE u.usuario=%s AND r.estado IN ('codigo_enviado','aprobada') AND r.codigo_hash IS NOT NULL "
                'ORDER BY r.solicitado_en DESC LIMIT 1', (usuario,),
            )
            solicitud = cursor.fetchone()
            if not solicitud or not self._objetivo_valido(cursor, solicitud) or not self._aprobador_valido(cursor, solicitud):
                return None
            if not hmac.compare_digest(solicitud['codigo_hash'], calcular_hash(solicitud['token_hash'])):
                self._fallar_codigo(cursor, solicitud)
                return None
            cursor.execute(
                "UPDATE public.recuperaciones_password SET token_hash=%s,codigo_hash=%s,estado='aprobada',"
                'verificado_en=COALESCE(verificado_en,CURRENT_TIMESTAMP) WHERE id_solicitud=%s',
                (nuevo_token_hash, nuevo_codigo_hash, solicitud['id_solicitud']),
            )
            return 'aprobada'

    def estado(self, token_hash):
        with self._cursor() as cursor:
            cursor.execute('SELECT * FROM public.recuperaciones_password WHERE token_hash=%s', (token_hash,))
            solicitud = cursor.fetchone()
            if not solicitud:
                return 'no_disponible'
            if solicitud['estado'] in ACTIVAS and not self._objetivo_valido(cursor, solicitud):
                return 'cancelada'
            return solicitud['estado']

    def listar(self, id_administrador, solo_notificaciones=False):
        with self._cursor() as cursor:
            self._administrador(cursor, id_administrador)
            if solo_notificaciones:
                cursor.execute("SELECT id_solicitud FROM public.recuperaciones_password WHERE estado IN ('pendiente','envio_fallido') "
                               'ORDER BY solicitado_en DESC')
                return [str(fila['id_solicitud']) for fila in cursor.fetchall()]
            cursor.execute(
                'SELECT r.id_solicitud,r.id_usuario,u.usuario,r.canal,'
                "CASE WHEN r.estado='pendiente' AND r.destino='' THEN COALESCE(u.correo,'') ELSE r.destino END AS destino,"
                "(r.estado='pendiente' AND r.destino='' AND NULLIF(u.correo,'') IS NULL) AS correo_pendiente,"
                'r.estado,r.solicitado_en,r.caduca_en,'
                'r.verificado_en,r.resuelto_en,r.cambiado_en,r.envio_error,r.envio_intentos,r.envio_intentado_en,a.usuario AS administrador '
                'FROM public.recuperaciones_password r JOIN public.usuarios u USING (id_usuario) '
                'LEFT JOIN public.usuarios a ON a.id_usuario=r.id_administrador '
                "ORDER BY (r.estado IN ('pendiente','envio_fallido')) DESC,r.solicitado_en DESC,r.id_solicitud DESC"
            )
            return cursor.fetchall()

    def cambiar_password(self, token_hash, password_hash):
        with self._cursor() as cursor:
            cursor.execute('SELECT * FROM public.recuperaciones_password WHERE token_hash=%s', (token_hash,))
            solicitud = cursor.fetchone()
            if not solicitud or solicitud['estado'] != 'aprobada' or not solicitud['verificado_en']:
                return False
            if not self._objetivo_valido(cursor, solicitud) or not self._aprobador_valido(cursor, solicitud):
                return False
            cursor.execute('UPDATE public.usuarios SET password_hash=%s,debe_cambiar_password=FALSE,correo_verificado_en=CURRENT_TIMESTAMP '
                           'WHERE id_usuario=%s', (password_hash, solicitud['id_usuario']))
            cursor.execute("UPDATE public.recuperaciones_password SET estado='completada',codigo_hash=NULL,cambiado_en=CURRENT_TIMESTAMP "
                           'WHERE id_solicitud=%s', (solicitud['id_solicitud'],))
            cursor.execute("UPDATE public.recuperaciones_password SET estado='cancelada',codigo_hash=NULL "
                           "WHERE id_usuario=%s AND id_solicitud<>%s AND estado IN ('pendiente','enviando','codigo_enviado','aprobada','envio_fallido')",
                           (solicitud['id_usuario'], solicitud['id_solicitud']))
            return True
