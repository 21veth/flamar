import unittest
import uuid
from unittest.mock import MagicMock, patch

import psycopg

from config.recuperacion import configuracion
from models.sesion_usuario import SesionUsuario
from services.envios_recuperacion import EnviosRecuperacion, ErrorEnvioRecuperacion
from services.recuperacion_service import MENSAJE_SOLICITUD, RecuperacionService


class RecuperacionServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.envios, self.hasher = MagicMock(), MagicMock(), MagicMock()
        self.envios.config = {'secreto': 's' * 48}
        self.envios.disponibles.return_value = {'correo': True}
        self.repo.preparar.return_value = True
        self.hasher.hash.return_value = 'hash_argon2'
        self.service = RecuperacionService(repositorio=self.repo, envios=self.envios, hasher=self.hasher)
        self.token = 't' * 43

    def test_codigo_seguro_contiene_letras_y_numeros(self):
        codigos = {self.service.generar_codigo() for _ in range(100)}
        self.assertEqual(len(codigos), 100)
        for codigo in codigos:
            self.assertEqual(len(codigo), 8)
            self.assertTrue(any(c.isalpha() for c in codigo))
            self.assertTrue(any(c.isdigit() for c in codigo))

    def test_solicitud_solo_se_encola_no_genera_ni_envia_codigo(self):
        resultado = self.service.ejecutar('solicitar', usuario='persona', canal='correo')
        self.assertEqual(resultado['mensaje'], MENSAJE_SOLICITUD)
        parametros = self.repo.preparar.call_args.args
        self.assertNotEqual(parametros[2], resultado['token'])
        self.assertEqual(len(parametros), 3)
        self.envios.enviar.assert_not_called()
        self.repo.confirmar_envio.assert_not_called()

    def test_cuenta_inexistente_tiene_respuesta_generica(self):
        self.repo.preparar.return_value = False
        resultado = self.service.ejecutar('solicitar', usuario='no_existe', canal='correo')
        self.envios.enviar.assert_not_called()
        self.assertEqual(resultado['mensaje'], MENSAJE_SOLICITUD)

    def test_solicitud_se_guarda_aunque_smtp_no_este_configurado(self):
        self.envios.disponibles.return_value = {'correo': False}
        self.envios.config = {}
        resultado = self.service.ejecutar('solicitar', usuario='persona', canal='correo')
        self.assertIn('token', resultado)
        self.repo.preparar.assert_called_once()
        self.envios.enviar.assert_not_called()

    def test_solo_autorizar_genera_y_envia_codigo_sin_mostrarlo_al_admin(self):
        service = RecuperacionService(SesionUsuario(1, 'admin', 'administrador'), self.repo, self.envios)
        self.repo.resolver.return_value = dict(estado='enviando', canal='correo', destino='persona@example.com', codigo_hash='h' * 64)
        self.repo.confirmar_envio.return_value = 'codigo_enviado'
        resultado = service.ejecutar('aprobar', id_solicitud=str(uuid.uuid4()))
        self.assertEqual(resultado['estado'], 'codigo_enviado')
        canal, destino, codigo = self.envios.enviar.call_args.args
        self.assertEqual((canal, destino), ('correo', 'persona@example.com'))
        self.assertEqual(len(codigo), 8)
        self.assertNotIn(codigo, str(resultado))
        calcular = self.repo.resolver.call_args.kwargs['calcular_hash']
        self.assertEqual(len(calcular('t' * 64)), 64)

    def test_fallo_de_correo_no_borra_la_autorizacion_y_explica_motivo_seguro(self):
        service = RecuperacionService(SesionUsuario(1, 'admin', 'administrador'), self.repo, self.envios)
        self.repo.resolver.return_value = dict(estado='enviando', canal='correo', destino='persona@example.com', codigo_hash='h' * 64)
        self.repo.confirmar_envio.return_value = 'envio_fallido'
        self.envios.enviar.side_effect = ErrorEnvioRecuperacion('autenticacion')
        resultado = service.ejecutar('aprobar', id_solicitud=str(uuid.uuid4()))
        self.assertEqual(resultado['estado'], 'envio_fallido')
        self.assertIn('autorización quedó guardada', resultado['mensaje'])
        self.assertFalse(self.repo.confirmar_envio.call_args.args[2])
        self.assertEqual(self.repo.confirmar_envio.call_args.args[3], 'autenticacion')

    def test_otros_canales_se_rechazan_aunque_una_configuracion_antigua_los_anuncie(self):
        self.envios.disponibles.return_value = {'correo': True, 'whatsapp': True}
        self.assertEqual(self.service.ejecutar('configuracion')['canales'], {'correo': True})
        with self.assertRaisesRegex(ValueError, 'solo.*correo'):
            self.service.ejecutar('solicitar', usuario='persona', canal='whatsapp')
        self.repo.preparar.assert_not_called()
        self.envios.enviar.assert_not_called()

    def test_no_se_puede_cambiar_password_sin_aprobacion(self):
        for estado in ('codigo_enviado', 'pendiente', 'rechazada', 'expirada', 'completada'):
            self.repo.estado.return_value = estado
            with self.assertRaises(ValueError):
                self.service.ejecutar('restablecer', token=self.token, contrasena='123456')
        self.hasher.hash.assert_not_called()
        self.repo.cambiar_password.assert_not_called()

    def test_password_aprobado_respeta_minimo_seis_y_consumo_atomico(self):
        self.repo.estado.return_value = 'aprobada'
        self.repo.cambiar_password.return_value = True
        resultado = self.service.ejecutar('restablecer', token=self.token, contrasena='abc123')
        self.assertEqual(resultado['estado'], 'completada')
        self.hasher.hash.assert_called_once_with('abc123')
        self.repo.cambiar_password.assert_called_once_with(self.service._token_hash(self.token), 'hash_argon2')
        self.repo.cambiar_password.return_value = False
        with self.assertRaises(ValueError):
            self.service.ejecutar('restablecer', token=self.token, contrasena='abc123')

    def test_solo_administradores_pueden_revisar_y_resolver(self):
        for sesion in (None, SesionUsuario(2, 'persona', 'trabajador'), SesionUsuario(2, 'persona', 'gerente')):
            service = RecuperacionService(sesion, self.repo, self.envios)
            for accion in ('listar', 'notificaciones', 'aprobar', 'rechazar'):
                with self.assertRaises(PermissionError):
                    service.ejecutar(accion, id_solicitud=str(uuid.uuid4()))

    def test_bandeja_oculta_contactos_y_no_incluye_secretos(self):
        service = RecuperacionService(SesionUsuario(1, 'admin', 'administrador'), self.repo, self.envios)
        self.repo.listar.return_value = [dict(id_solicitud=uuid.uuid4(), canal='correo', destino='persona@example.com')]
        item = service.ejecutar('listar')['solicitudes'][0]
        self.assertEqual(item['destino'], 'p***@example.com')
        self.assertEqual(service._ocultar('+51987654321', 'whatsapp'), '+••••••321')
        self.assertEqual(service._ocultar('', 'correo'), 'Sin correo registrado')

    def test_errores_de_bd_no_exponen_diagnosticos(self):
        self.repo.preparar.side_effect = psycopg.OperationalError('password=privado')
        with self.assertRaisesRegex(ValueError, 'conexión') as resultado:
            self.service.ejecutar('solicitar', usuario='persona', canal='correo')
        self.assertNotIn('privado', str(resultado.exception))

    def test_retomar_revalida_codigo_y_emite_un_acceso_nuevo(self):
        self.repo.retomar.return_value = 'aprobada'
        resultado = self.service.ejecutar('retomar', usuario='persona', codigo='abcd2345')
        self.assertEqual(resultado['estado'], 'aprobada')
        self.assertIn('token', resultado)
        self.envios.enviar.assert_not_called()
        self.assertEqual(self.repo.retomar.call_args.args[0], 'persona')
        self.assertNotIn('ABCD2345', str(resultado))
        self.repo.retomar.return_value = None
        with self.assertRaisesRegex(ValueError, 'No se pudo retomar'):
            self.service.ejecutar('retomar', usuario='persona', codigo='ABCD2345')


class EnviosRecuperacionTests(unittest.TestCase):
    def config(self):
        return dict(secreto='s' * 48, correo_habilitado=True, smtp_host='smtp.example.com', smtp_port='465',
                    smtp_seguridad='ssl', smtp_usuario='usuario', smtp_password='privado', smtp_desde='zeyver@example.com')

    def test_correo_necesita_configuracion_y_activacion_explicita(self):
        self.assertEqual(EnviosRecuperacion({}).disponibles(), {'correo': False})
        for cambio in (dict(secreto=''), dict(correo_habilitado=False)):
            self.assertEqual(EnviosRecuperacion(dict(self.config(), **cambio)).disponibles(), {'correo': False})

    def test_smtp_cifrado_envia_codigo_y_nunca_password_del_usuario(self):
        envios = EnviosRecuperacion(self.config())
        with patch('services.envios_recuperacion.smtplib.SMTP_SSL') as smtp:
            # El contexto SMTP devuelve la misma conexión.
            smtp.return_value.__enter__.return_value = smtp.return_value
            smtp.return_value.send_message.return_value = {}
            envios.enviar('correo', 'persona@example.com', 'ABCD2345')
            mensaje = smtp.return_value.send_message.call_args.args[0]
            self.assertIn('ABCD2345', mensaje.get_content())
            self.assertIn('3 horas', mensaje.get_content())
            self.assertIn('Retomar con mi código', mensaje.get_content())
            self.assertNotIn('privado', mensaje.get_content())
            smtp.return_value.login.assert_called_once_with('usuario', 'privado')

    def test_starttls_cifra_antes_de_enviar_credenciales(self):
        with patch('services.envios_recuperacion.smtplib.SMTP') as smtp:
            smtp.return_value.send_message.return_value = {}
            EnviosRecuperacion(dict(self.config(), smtp_seguridad='starttls', smtp_port='587')).enviar(
                'correo', 'persona@example.com', 'ABCD2345')
            llamadas = [llamada[0] for llamada in smtp.return_value.method_calls]
            self.assertLess(llamadas.index('starttls'), llamadas.index('login'))

    def test_puerto_587_sin_modo_explicito_usa_starttls_y_465_usa_ssl(self):
        with patch.dict('os.environ', {'RECOVERY_SMTP_PORT': '587'}, clear=True):
            self.assertEqual(configuracion()['smtp_seguridad'], 'starttls')
        with patch.dict('os.environ', {'RECOVERY_SMTP_PORT': '465'}, clear=True):
            self.assertEqual(configuracion()['smtp_seguridad'], 'ssl')

    def test_proveedor_solo_admite_correo(self):
        with patch('services.envios_recuperacion.smtplib.SMTP_SSL') as smtp:
            with self.assertRaisesRegex(ValueError, 'solo.*correo'):
                EnviosRecuperacion(self.config()).enviar('whatsapp', '+51987654321', 'ABCD2345')
            smtp.assert_not_called()

    def test_fallo_de_proveedor_no_filtra_cuerpo_tokens_o_codigos(self):
        with patch('services.envios_recuperacion.smtplib.SMTP_SSL', side_effect=Exception('privado ABCD2345')):
            with self.assertRaises(ValueError) as resultado:
                EnviosRecuperacion(self.config()).enviar('correo', 'persona@example.com', 'ABCD2345')
            self.assertNotIn('privado', str(resultado.exception))
            self.assertNotIn('ABCD2345', str(resultado.exception))


if __name__ == '__main__':
    unittest.main()
