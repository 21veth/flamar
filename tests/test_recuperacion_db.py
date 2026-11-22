"""Flujo autorización -> correo -> código, exclusivamente en esquemas de prueba."""

import os
import re
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import psycopg
from argon2 import PasswordHasher

from config.database import obtener_conexion
from models.sesion_usuario import SesionUsuario
from repositories.recuperacion_repository import RecuperacionRepository
from repositories.usuario_repository import UsuarioRepository
from services.auth_service import AuthService, CredencialesInvalidasError
from services.recuperacion_service import RecuperacionService


class EnviosPrueba:
    config = {'secreto': 'clave_solo_de_pruebas_' * 3}

    def __init__(self):
        self.enviados = []

    def disponibles(self):
        return {'correo': True}

    def enviar(self, canal, destino, codigo):
        self.enviados.append((canal, destino, codigo))


@unittest.skipUnless(os.getenv('FLAMAR_TEST_DB') == '1', 'Requiere FLAMAR_TEST_DB=1 y PostgreSQL configurado')
class RecuperacionPostgresTests(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion()
        self.addCleanup(self.conexion.close)
        self.addCleanup(self.conexion.rollback)
        esquema = 'recuperacion_test_' + uuid.uuid4().hex

        class CursorAislado(psycopg.Cursor):
            def execute(self, query, params=None, **kwargs):
                return super().execute(query.replace('public.', esquema + '.') if isinstance(query, str) else query, params, **kwargs)

        self.conexion.cursor_factory = CursorAislado
        self.sql = (Path(__file__).resolve().parents[1] / 'database' / 'flamar_postgres.sql').read_text(encoding='utf-8')
        self.sql = re.sub(r'^\s*(?:BEGIN|COMMIT);\s*$', '', self.sql, flags=re.MULTILINE)
        self.password_inicial = PasswordHasher().hash('Original123')
        with self.conexion.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA {esquema}')
            cursor.execute(f'SET LOCAL search_path TO {esquema}')
            cursor.execute(self.sql)
            cursor.execute("INSERT INTO usuarios(usuario,password_hash,rol,correo,telefono) VALUES "
                           "('admin',%s,'administrador','admin@example.com',NULL),"
                           "('persona',%s,'trabajador','persona@example.com','+51987654321') RETURNING id_usuario",
                           (self.password_inicial, self.password_inicial))
            self.id_admin, self.id_usuario = [fila[0] for fila in cursor.fetchall()]

        @contextmanager
        def conexion_aislada():
            with self.conexion.transaction():
                yield self.conexion

        for modulo in ('repositories.recuperacion_repository', 'repositories.usuario_repository'):
            parche = patch(modulo + '.obtener_conexion', conexion_aislada)
            parche.start()
            self.addCleanup(parche.stop)
        self.envios = EnviosPrueba()
        self.repo = RecuperacionRepository()
        self.service = RecuperacionService(repositorio=self.repo, envios=self.envios)
        self.admin = RecuperacionService(SesionUsuario(self.id_admin, 'admin', 'administrador'), self.repo, self.envios)

    def pedir(self, usuario='persona'):
        resultado = self.service.ejecutar('solicitar', usuario=usuario, canal='correo')
        return resultado['token'], self.admin.ejecutar('listar')['solicitudes'][0]['id_solicitud']

    def autorizar(self, usuario='persona'):
        token, identificador = self.pedir(usuario)
        resultado = self.admin.ejecutar('aprobar', id_solicitud=identificador)
        self.assertEqual(resultado['estado'], 'codigo_enviado')
        return token, identificador, self.envios.enviados[-1][2]

    def test_pedir_no_envia_correo_y_guarda_pendiente_notificable_sin_codigo(self):
        token, identificador = self.pedir()
        self.assertEqual(self.envios.enviados, [])
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'pendiente')
        self.assertEqual(self.admin.ejecutar('notificaciones')['ids'], [identificador])
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT codigo_hash,id_administrador,verificado_en,envio_intentos FROM recuperaciones_password')
            self.assertEqual(cursor.fetchone(), (None, None, None, 0))

    def test_historial_incluye_resueltas_caducadas_y_autorizadas_ademas_de_pendientes(self):
        token, identificador = self.pedir()
        with self.conexion.cursor() as cursor:
            for estado in ('rechazada', 'completada', 'expirada', 'codigo_enviado'):
                cursor.execute(
                    'INSERT INTO recuperaciones_password '
                    '(id_solicitud,id_usuario,canal,destino,token_hash,password_firma,estado,codigo_hash,'
                    'id_administrador,resuelto_en,verificado_en,aprobacion_caduca_en) '
                    'SELECT %s,id_usuario,canal,destino,%s,password_firma,%s,%s,%s,'
                    'CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,caduca_en FROM recuperaciones_password WHERE id_solicitud=%s',
                    (uuid.uuid4(), uuid.uuid4().hex * 2, estado, 'c' * 64 if estado == 'codigo_enviado' else None,
                     self.id_admin, identificador),
                )
        filas = self.admin.ejecutar('listar')['solicitudes']
        self.assertEqual(len(filas), 5)
        self.assertEqual({fila['estado'] for fila in filas},
                         {'pendiente', 'rechazada', 'completada', 'expirada', 'codigo_enviado'})
        self.assertEqual(self.admin.ejecutar('notificaciones')['pendientes'], 1)
        resuelta = next(fila for fila in filas if fila['estado'] == 'rechazada')
        self.assertEqual(resuelta['administrador'], 'admin')
        self.assertIsNotNone(resuelta['resuelto_en'])
        self.assertEqual(self.envios.enviados, [])

    def test_historial_no_recorta_las_solicitudes_despues_de_cien_registros(self):
        token, identificador = self.pedir()
        with self.conexion.cursor() as cursor:
            for _ in range(105):
                cursor.execute(
                    'INSERT INTO recuperaciones_password '
                    '(id_solicitud,id_usuario,canal,destino,token_hash,password_firma,estado,id_administrador,resuelto_en) '
                    "SELECT %s,id_usuario,canal,destino,%s,password_firma,'rechazada',%s,CURRENT_TIMESTAMP "
                    'FROM recuperaciones_password WHERE id_solicitud=%s',
                    (uuid.uuid4(), uuid.uuid4().hex * 2, self.id_admin, identificador),
                )
        filas = self.admin.ejecutar('listar')['solicitudes']
        self.assertEqual(len(filas), 106)
        self.assertEqual(sum(fila['estado'] == 'rechazada' for fila in filas), 105)
        self.assertEqual(self.admin.ejecutar('notificaciones')['pendientes'], 1)
        self.assertEqual(self.envios.enviados, [])

    def test_pedir_funciona_sin_smtp_y_sin_secreto(self):
        self.envios.config = {}
        with patch.object(self.envios, 'disponibles', return_value={'correo': False}):
            token, identificador = self.pedir()
        self.assertEqual(self.envios.enviados, [])
        self.assertEqual(self.admin.ejecutar('listar')['solicitudes'][0]['estado'], 'pendiente')

    def test_sin_correo_solicitud_se_conserva_y_no_se_autoriza_hasta_registrarlo(self):
        with self.conexion.cursor() as cursor:
            cursor.execute('UPDATE usuarios SET correo=NULL WHERE id_usuario=%s', (self.id_usuario,))
        token, identificador = self.pedir()
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'pendiente')
        fila = self.admin.ejecutar('listar')['solicitudes'][0]
        self.assertTrue(fila['correo_pendiente'])
        self.assertEqual(fila['destino'], 'Sin correo registrado')
        self.assertEqual(self.admin.ejecutar('notificaciones')['pendientes'], 1)
        with self.assertRaisesRegex(ValueError, 'Registra primero el correo'):
            self.admin.ejecutar('aprobar', id_solicitud=identificador)
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'pendiente')
        self.assertEqual(self.envios.enviados, [])
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT codigo_hash,id_administrador,envio_intentos FROM recuperaciones_password')
            self.assertEqual(cursor.fetchone(), (None, None, 0))
            cursor.execute("UPDATE usuarios SET correo='nuevo@example.com' WHERE id_usuario=%s", (self.id_usuario,))
        fila = self.admin.ejecutar('listar')['solicitudes'][0]
        self.assertFalse(fila['correo_pendiente'])
        self.assertEqual(fila['destino'], 'n***@example.com')
        self.assertEqual(self.admin.ejecutar('aprobar', id_solicitud=identificador)['estado'], 'codigo_enviado')
        self.assertEqual(self.envios.enviados[0][:2], ('correo', 'nuevo@example.com'))
        codigo = self.envios.enviados[0][2]
        self.service.ejecutar('verificar', token=token, codigo=codigo)
        self.service.ejecutar('restablecer', token=token, contrasena='Nueva1')

    def test_denegar_solicitud_sin_correo_no_la_oculta_ni_envia_mensajes(self):
        with self.conexion.cursor() as cursor:
            cursor.execute('UPDATE usuarios SET correo=NULL WHERE id_usuario=%s', (self.id_usuario,))
        token, identificador = self.pedir()
        self.assertEqual(self.admin.ejecutar('rechazar', id_solicitud=identificador)['estado'], 'rechazada')
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'rechazada')
        self.assertEqual(self.envios.enviados, [])

    def test_dos_solicitudes_de_una_cuenta_y_otra_sin_correo_coinciden_con_contador(self):
        self.service.ejecutar('solicitar', usuario='persona')
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE recuperaciones_password SET solicitado_en=CURRENT_TIMESTAMP-INTERVAL '2 minutes'")
            cursor.execute("INSERT INTO usuarios(usuario,password_hash,rol) VALUES ('sin_correo_prueba',%s,'trabajador')",
                           (self.password_inicial,))
        self.service.ejecutar('solicitar', usuario='persona')
        self.service.ejecutar('solicitar', usuario='sin_correo_prueba')
        filas = self.admin.ejecutar('listar')['solicitudes']
        self.assertEqual(len(filas), 3)
        self.assertEqual(sum(fila['usuario'] == 'persona' for fila in filas), 2)
        self.assertEqual(sum(fila['usuario'] == 'sin_correo_prueba' for fila in filas), 1)
        self.assertEqual(self.admin.ejecutar('notificaciones')['pendientes'], 3)
        self.assertEqual(self.envios.enviados, [])

    def test_denegar_pendiente_no_envia_codigo_y_no_cambia_password(self):
        token, identificador = self.pedir()
        self.admin.ejecutar('rechazar', id_solicitud=identificador)
        self.assertEqual(self.envios.enviados, [])
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'rechazada')
        with self.assertRaises(ValueError):
            self.service.ejecutar('restablecer', token=token, contrasena='Nueva1')

    def test_autorizar_antes_del_codigo_y_validarlo_es_obligatorio_para_cambiar(self):
        token, identificador, codigo = self.autorizar()
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'codigo_enviado')
        with self.assertRaises(ValueError):
            self.service.ejecutar('restablecer', token=token, contrasena='Nueva1')
        self.assertEqual(self.service.ejecutar('verificar', token=token, codigo=codigo)['estado'], 'aprobada')
        self.service.ejecutar('restablecer', token=token, contrasena='Nueva1')
        auth = AuthService(UsuarioRepository())
        self.assertEqual(auth.autenticar('persona', 'Nueva1').id_usuario, self.id_usuario)
        with self.assertRaises(CredencialesInvalidasError):
            auth.autenticar('persona', 'Original123')
        with self.assertRaises(ValueError):
            self.service.ejecutar('restablecer', token=token, contrasena='Otra12')
        with self.assertRaises(ValueError):
            self.service.ejecutar('retomar', usuario='persona', codigo=codigo)

    def test_no_se_puede_validar_un_codigo_antes_de_la_autorizacion(self):
        token, identificador = self.pedir()
        with self.assertRaises(ValueError):
            self.service.ejecutar('verificar', token=token, codigo='ABCD2345')
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'pendiente')

    def test_otro_administrador_y_rol_vigente_son_obligatorios(self):
        token, identificador = self.pedir('admin')
        with self.assertRaises(PermissionError):
            self.admin.ejecutar('aprobar', id_solicitud=identificador)
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE usuarios SET rol='trabajador' WHERE id_usuario=%s", (self.id_admin,))
        with self.assertRaises(PermissionError):
            self.admin.ejecutar('listar')
        self.assertEqual(self.envios.enviados, [])

    def test_fallo_smtp_conserva_autorizacion_y_permite_reintentar_despues_de_dos_minutos(self):
        token, identificador = self.pedir()
        with patch.object(self.envios, 'enviar', side_effect=ValueError('detalle privado')):
            resultado = self.admin.ejecutar('aprobar', id_solicitud=identificador)
        self.assertEqual(resultado['estado'], 'envio_fallido')
        filas = self.admin.ejecutar('listar')['solicitudes']
        self.assertEqual(filas[0]['estado'], 'envio_fallido')
        self.assertIsNotNone(filas[0]['administrador'])
        self.assertEqual(filas[0]['envio_intentos'], 1)
        self.assertNotIn('detalle privado', str(filas))
        with self.assertRaisesRegex(ValueError, '2 minutos'):
            self.admin.ejecutar('aprobar', id_solicitud=identificador)
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE recuperaciones_password SET envio_intentado_en=CURRENT_TIMESTAMP-INTERVAL '120 seconds'")
        self.assertEqual(self.admin.ejecutar('aprobar', id_solicitud=identificador)['estado'], 'codigo_enviado')
        self.assertEqual(len(self.envios.enviados), 1)
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'codigo_enviado')

    def test_tres_intentos_de_envio_por_solicitud_no_se_superan(self):
        token, identificador = self.pedir()
        with patch.object(self.envios, 'enviar', side_effect=ValueError('fallo')):
            for _ in range(3):
                self.admin.ejecutar('aprobar', id_solicitud=identificador)
                with self.conexion.cursor() as cursor:
                    cursor.execute("UPDATE recuperaciones_password SET envio_intentado_en=CURRENT_TIMESTAMP-INTERVAL '2 minutes'")
            with self.assertRaisesRegex(ValueError, '3 intentos'):
                self.admin.ejecutar('aprobar', id_solicitud=identificador)

    def test_cinco_codigos_erroneos_bloquean_y_los_intentos_se_guardan(self):
        token, identificador, codigo = self.autorizar()
        for _ in range(5):
            with self.assertRaises(ValueError):
                self.service.ejecutar('retomar', usuario='persona', codigo='00000000')
        with self.assertRaises(ValueError):
            self.service.ejecutar('verificar', token=token, codigo=codigo)
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'bloqueada')
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT intentos,codigo_hash FROM recuperaciones_password')
            self.assertEqual(cursor.fetchone(), (5, None))

    def test_duracion_tres_horas_no_se_extiende_al_autorizar_o_retomar(self):
        token, identificador, codigo = self.autorizar()
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT codigo_caduca_en-solicitado_en,caduca_en-solicitado_en,'
                           'aprobacion_caduca_en=caduca_en,caduca_en FROM recuperaciones_password')
            duracion_codigo, duracion_solicitud, igual, caduca = cursor.fetchone()
        self.assertEqual(duracion_codigo.total_seconds(), 10800)
        self.assertEqual(duracion_solicitud.total_seconds(), 10800)
        self.assertTrue(igual)
        self.service.ejecutar('retomar', usuario='persona', codigo=codigo)
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT caduca_en FROM recuperaciones_password')
            self.assertEqual(cursor.fetchone()[0], caduca)

    def test_caducadas_y_denegadas_no_se_pueden_retomar(self):
        token, identificador, codigo = self.autorizar()
        self.admin.ejecutar('rechazar', id_solicitud=identificador)
        with self.assertRaises(ValueError):
            self.service.ejecutar('retomar', usuario='persona', codigo=codigo)
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE recuperaciones_password SET solicitado_en=CURRENT_TIMESTAMP-INTERVAL '2 minutes'")
        token, identificador, codigo = self.autorizar()
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE recuperaciones_password SET caduca_en=CURRENT_TIMESTAMP-INTERVAL '1 second'")
        with self.assertRaises(ValueError):
            self.service.ejecutar('retomar', usuario='persona', codigo=codigo)

    def test_rol_revocado_del_aprobador_o_contacto_modificado_invalidan_codigo(self):
        token, identificador, codigo = self.autorizar()
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE usuarios SET activo=FALSE WHERE id_usuario=%s", (self.id_admin,))
        with self.assertRaises(ValueError):
            self.service.ejecutar('verificar', token=token, codigo=codigo)
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'cancelada')

    def test_cambiar_contacto_o_password_por_otro_medio_cancela_solicitud(self):
        token, identificador, codigo = self.autorizar()
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE usuarios SET correo='otro@example.com' WHERE id_usuario=%s", (self.id_usuario,))
        with self.assertRaises(ValueError):
            self.service.ejecutar('retomar', usuario='persona', codigo=codigo)
        self.assertEqual(self.service.ejecutar('estado', token=token)['estado'], 'cancelada')

    def test_limites_de_dos_minutos_y_tres_solicitudes_por_hora(self):
        self.pedir()
        self.service.ejecutar('solicitar', usuario='persona')
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM recuperaciones_password')
            self.assertEqual(cursor.fetchone()[0], 1)
        for _ in range(2):
            with self.conexion.cursor() as cursor:
                cursor.execute("UPDATE recuperaciones_password SET solicitado_en=CURRENT_TIMESTAMP-INTERVAL '2 minutes'")
            self.service.ejecutar('solicitar', usuario='persona')
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE recuperaciones_password SET solicitado_en=CURRENT_TIMESTAMP-INTERVAL '2 minutes'")
        self.service.ejecutar('solicitar', usuario='persona')
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM recuperaciones_password')
            self.assertEqual(cursor.fetchone()[0], 3)
        self.assertEqual(self.envios.enviados, [])

    def test_codigo_solo_verifica_correo_al_completar_y_no_telefono(self):
        token, identificador, codigo = self.autorizar()
        retomada = self.service.ejecutar('retomar', usuario='persona', codigo=codigo)
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT correo_verificado_en FROM usuarios WHERE id_usuario=%s', (self.id_usuario,))
            self.assertIsNone(cursor.fetchone()[0])
        self.service.ejecutar('restablecer', token=retomada['token'], contrasena='Nueva1')
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT correo_verificado_en,telefono_verificado_en FROM usuarios WHERE id_usuario=%s', (self.id_usuario,))
            correo, telefono = cursor.fetchone()
            self.assertIsNotNone(correo)
            self.assertIsNone(telefono)

    def test_otro_canal_no_se_encola(self):
        with self.assertRaises(ValueError):
            self.service.ejecutar('solicitar', usuario='persona', canal='whatsapp')
        self.assertEqual(self.envios.enviados, [])

    def test_transacciones_reales_persisten_al_cerrar_conexiones_y_reabrir_como_admin(self):
        # Esta prueba usa conexiones físicamente distintas, sin tocar public ni cuentas reales.
        esquema = 'recup_persistencia_test_' + uuid.uuid4().hex

        class CursorPersistencia(psycopg.Cursor):
            def execute(self, query, params=None, **kwargs):
                return super().execute(query.replace('public.', esquema + '.') if isinstance(query, str) else query, params, **kwargs)

        @contextmanager
        def conectar():
            with obtener_conexion() as conexion:
                conexion.cursor_factory = CursorPersistencia
                yield conexion

        creado = False
        try:
            with obtener_conexion() as conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(f'CREATE SCHEMA {esquema}')
                    cursor.execute(f'SET LOCAL search_path TO {esquema}')
                    cursor.execute(self.sql)
                    cursor.execute("INSERT INTO usuarios(usuario,password_hash,rol,correo) VALUES "
                                   "('administrador_test',%s,'administrador','admin@example.com'),"
                                   "('solicitante_test',%s,'trabajador','persona@example.com') RETURNING id_usuario",
                                   (self.password_inicial, self.password_inicial))
                    admin_id = cursor.fetchone()[0]
            creado = True
            with patch('repositories.recuperacion_repository.obtener_conexion', conectar), \
                    patch('repositories.usuario_repository.obtener_conexion', conectar):
                envios = EnviosPrueba()
                token = RecuperacionService(envios=envios).ejecutar('solicitar', usuario='solicitante_test')['token']
                self.assertEqual(envios.enviados, [])
                bandeja = RecuperacionService(SesionUsuario(admin_id, 'administrador_test', 'administrador'), envios=envios)
                filas = bandeja.ejecutar('listar')['solicitudes']
                self.assertEqual(len(filas), 1)
                self.assertEqual(filas[0]['estado'], 'pendiente')
                bandeja.ejecutar('aprobar', id_solicitud=filas[0]['id_solicitud'])
                codigo = envios.enviados[0][2]
                login_nuevo = RecuperacionService(envios=envios)
                recuperada = login_nuevo.ejecutar('retomar', usuario='solicitante_test', codigo=codigo)
                self.assertEqual(login_nuevo.ejecutar('estado', token=token)['estado'], 'no_disponible')
                login_nuevo.ejecutar('restablecer', token=recuperada['token'], contrasena='Nueva1')
                self.assertEqual(AuthService().autenticar('solicitante_test', 'Nueva1').usuario, 'solicitante_test')
        finally:
            if creado:
                with obtener_conexion() as conexion:
                    with conexion.cursor() as cursor:
                        cursor.execute(f'DROP SCHEMA {esquema} CASCADE')


if __name__ == '__main__':
    unittest.main()
