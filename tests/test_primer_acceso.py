import os
import time
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import psycopg
from argon2 import PasswordHasher
from PySide6.QtCore import Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from models.sesion_usuario import SesionUsuario
from services.auth_service import (
    AuthService, CambioPasswordPendiente, CredencialesInvalidasError, ErrorDeConexionError,
)
from views.login_view import LoginView
from views.password_dialogs import CredencialesDialog


class AuthPrimerAccesoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hasher = PasswordHasher()
        cls.temporal_hash = cls.hasher.hash('01234567')

    def setUp(self):
        self.repo = MagicMock()
        self.registro = dict(id_usuario=2, usuario='persona', rol='trabajador', activo=True,
                             password_hash=self.temporal_hash, debe_cambiar_password=True)
        self.repo.obtener_por_usuario.side_effect = lambda _: dict(self.registro)
        self.repo.completar_password_inicial.side_effect = self._completar
        self.service = AuthService(self.repo)

    def _completar(self, id_usuario, anterior, nuevo):
        if (id_usuario != self.registro['id_usuario'] or not self.registro['activo']
                or not self.registro['debe_cambiar_password'] or anterior != self.registro['password_hash']):
            return None
        self.registro.update(password_hash=nuevo, debe_cambiar_password=False)
        return {key: self.registro[key] for key in ('id_usuario', 'usuario', 'rol')}

    def pendiente(self):
        return self.service.autenticar('persona', '01234567')

    def test_temporal_no_emite_sesion_ni_registra_acceso(self):
        pendiente = self.pendiente()
        self.assertIsInstance(pendiente, CambioPasswordPendiente)
        self.assertNotIsInstance(pendiente, SesionUsuario)
        self.assertFalse(hasattr(pendiente, 'rol'))
        self.assertFalse(hasattr(pendiente, 'id_usuario'))
        self.assertNotIn(pendiente.token, repr(pendiente))
        self.assertNotIn('01234567', repr(pendiente))
        self.repo.actualizar_ultimo_acceso.assert_not_called()

    def test_cambio_canjes_unicos_y_clave_temporal_deja_de_funcionar(self):
        pendiente = self.pendiente()
        self.registro.update(usuario='nombre-actual', rol='gerente')
        sesion = self.service.cambiar_password_inicial(pendiente.token, 'MiClaveNueva123', 'MiClaveNueva123')
        self.assertIsInstance(sesion, SesionUsuario)
        self.assertEqual(sesion.usuario, 'nombre-actual')
        self.assertEqual(sesion.rol, 'gerente')
        self.assertFalse(self.registro['debe_cambiar_password'])
        self.assertTrue(self.hasher.verify(self.registro['password_hash'], 'MiClaveNueva123'))
        with self.assertRaises(CredencialesInvalidasError):
            self.pendiente()
        with self.assertRaisesRegex(ValueError, 'caducado'):
            self.service.cambiar_password_inicial(pendiente.token, 'OtraClave123', 'OtraClave123')
        self.assertIsInstance(self.service.autenticar('nombre-actual', 'MiClaveNueva123'), SesionUsuario)

    def test_validacion_no_modifica_hash_ni_consume_acceso(self):
        pendiente = self.pendiente()
        for nueva, confirmacion in (('corta', 'corta'), (' ' * 8, ' ' * 8),
                                    ('Nueva123', 'Distinta123'), ('01234567', '01234567'),
                                    ('x' * 129, 'x' * 129), (None, None)):
            with self.subTest(nueva=nueva), self.assertRaises(ValueError):
                self.service.cambiar_password_inicial(pendiente.token, nueva, confirmacion)
        self.repo.completar_password_inicial.assert_not_called()
        self.assertEqual(self.registro['password_hash'], self.temporal_hash)
        self.assertIn(pendiente.token, self.service._pendientes)

    def test_cancelacion_caducidad_y_token_ajeno_impiden_cambio(self):
        pendiente = self.pendiente()
        self.service.cancelar_cambio(pendiente.token)
        for token in (pendiente.token, 'inventado', None, 123):
            with self.assertRaises(ValueError):
                self.service.cambiar_password_inicial(token, 'MiClaveNueva123', 'MiClaveNueva123')
        pendiente = self.pendiente()
        with patch('services.auth_service.time.monotonic', return_value=time.monotonic() + 601):
            with self.assertRaisesRegex(ValueError, 'caducado'):
                self.service.cambiar_password_inicial(pendiente.token, 'MiClaveNueva123', 'MiClaveNueva123')
        self.repo.completar_password_inicial.assert_not_called()

    def test_otra_autenticacion_invalida_el_acceso_anterior(self):
        anterior, nuevo = self.pendiente(), self.pendiente()
        self.assertNotEqual(anterior.token, nuevo.token)
        with self.assertRaises(ValueError):
            self.service.cambiar_password_inicial(anterior.token, 'MiClaveNueva123', 'MiClaveNueva123')

    def test_cancelar_durante_el_calculo_del_hash_impide_el_canje(self):
        pendiente = self.pendiente()
        original_hash = self.service._hasher.hash

        def calcular(nueva):
            self.service.cancelar_cambio(pendiente.token)
            return original_hash(nueva)

        with patch.object(PasswordHasher, 'hash', side_effect=calcular):
            with self.assertRaisesRegex(ValueError, 'caducado'):
                self.service.cambiar_password_inicial(pendiente.token, 'MiClaveNueva123', 'MiClaveNueva123')
        self.repo.completar_password_inicial.assert_not_called()

    def test_cuenta_desactivada_o_clave_cambiada_entre_pasos_no_crea_sesion(self):
        for cambio in ({'activo': False}, {'password_hash': 'otro-hash'}, {'debe_cambiar_password': False}):
            with self.subTest(cambio=cambio):
                self.setUp()
                pendiente = self.pendiente()
                self.registro.update(cambio)
                with self.assertRaisesRegex(ValueError, 'no están disponibles'):
                    self.service.cambiar_password_inicial(pendiente.token, 'MiClaveNueva123', 'MiClaveNueva123')

    def test_error_de_bd_es_seguro_y_permite_reintentar(self):
        pendiente = self.pendiente()
        self.repo.completar_password_inicial.side_effect = psycopg.OperationalError('detalle privado')
        with self.assertRaises(ErrorDeConexionError) as error:
            self.service.cambiar_password_inicial(pendiente.token, 'MiClaveNueva123', 'MiClaveNueva123')
        self.assertNotIn('detalle privado', str(error.exception))
        self.assertIn(pendiente.token, self.service._pendientes)
        self.repo.completar_password_inicial.side_effect = self._completar
        self.assertIsInstance(self.service.cambiar_password_inicial(pendiente.token, 'MiClaveNueva123', 'MiClaveNueva123'), SesionUsuario)

    def test_cuentas_existentes_entran_sin_cambio_y_errores_no_entregan_token(self):
        self.registro['debe_cambiar_password'] = False
        self.assertIsInstance(self.pendiente(), SesionUsuario)
        self.repo.actualizar_ultimo_acceso.assert_called_once_with(2)
        self.registro['debe_cambiar_password'] = True
        with self.assertRaises(CredencialesInvalidasError):
            self.service.autenticar('persona', 'incorrecta')
        self.registro['activo'] = False
        with self.assertRaises(CredencialesInvalidasError):
            self.pendiente()
        self.assertEqual(self.service._pendientes, {})


class _HomePrueba(QWidget):
    logout_requested = Signal()

    def __init__(self, sesion):
        super().__init__()
        self.sesion = sesion


class PrimerAccesoUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temporal_hash = PasswordHasher().hash('01234567')

    def setUp(self):
        repo = MagicMock()
        repo.obtener_por_usuario.return_value = dict(id_usuario=2, usuario='persona', rol='trabajador',
            activo=True, password_hash=self.temporal_hash, debe_cambiar_password=True)
        repo.completar_password_inicial.return_value = dict(id_usuario=2, usuario='persona', rol='trabajador')
        self.service = AuthService(repo)
        self.login = LoginView(self.service)
        self.home_patch = patch('views.login_view.HomeView', side_effect=_HomePrueba)
        self.home = self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.addCleanup(self._cerrar)

    def _cerrar(self):
        worker = self.login._controller._worker
        if worker:
            worker.wait()
            self.app.processEvents()
        if self.login.home_view:
            self.login.home_view.close()
        self.login.close()
        self.login.deleteLater()

    def esperar(self, predicate):
        for _ in range(150):
            QTest.qWait(20)
            if predicate():
                return
        self.fail('El flujo de autenticación no terminó a tiempo.')

    def iniciar(self):
        self.login.show()
        self.login.user_input.setText('persona')
        self.login.password_input.setText('01234567')
        self.login.handle_login()
        self.esperar(lambda: self.login.cambio_dialog is not None and self.login._controller._worker is None)
        return self.login.cambio_dialog

    def test_home_no_abre_hasta_guardar_nueva_password(self):
        dialogo = self.iniciar()
        self.home.assert_not_called()
        self.assertEqual(self.login.password_input.text(), '')
        self.assertEqual(dialogo.nueva.echoMode(), QLineEdit.Password)
        dialogo.nueva.setText('MiClaveNueva123')
        dialogo.confirmacion.setText('MiClaveNueva123')
        dialogo.guardar_button.click()
        self.assertFalse(dialogo.cancelar.isEnabled())
        self.esperar(lambda: self.login.home_view is not None and self.login._controller._worker is None)
        self.home.assert_called_once()
        self.assertEqual(self.login.home_view.sesion.id_usuario, 2)
        self.assertIsNone(self.login._cambio_pendiente)
        self.assertIsNone(self.login.cambio_dialog)

    def test_cancelar_impide_acceso_y_anula_token(self):
        dialogo = self.iniciar()
        token = self.login._cambio_pendiente.token
        QTest.keyClick(dialogo, Qt.Key_Escape)
        self.assertIsNone(self.login.cambio_dialog)
        self.assertNotIn(token, self.service._pendientes)
        self.home.assert_not_called()

    def test_clave_igual_y_confirmacion_incorrecta_no_abren_home(self):
        dialogo = self.iniciar()
        dialogo.nueva.setText('MiClaveNueva123')
        dialogo.confirmacion.setText('distinta')
        dialogo.guardar_button.click()
        self.assertIn('no coinciden', dialogo.error.text())
        dialogo.nueva.setText('01234567')
        dialogo.confirmacion.setText('01234567')
        dialogo.guardar_button.click()
        self.esperar(lambda: self.login._controller._worker is None)
        self.assertIn('diferente', dialogo.error.text())
        self.home.assert_not_called()

    def test_cerrar_entrega_de_credenciales_limpia_la_clave(self):
        for cierre in ('accept', 'reject', 'close'):
            dialogo = CredencialesDialog('persona', '01234567', self.login)
            dialogo.open()
            self.assertEqual(dialogo.clave.text(), '01234567')
            getattr(dialogo, cierre)()
            self.assertEqual(dialogo.clave.text(), '')
            self.assertFalse(dialogo.clave.isUndoAvailable())
            dialogo.deleteLater()


if __name__ == '__main__':
    unittest.main()
