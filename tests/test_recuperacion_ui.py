import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox

from controllers.recuperacion_controller import RecuperacionController
from models.sesion_usuario import SesionUsuario
from views.login_view import LoginView
from views.recuperacion_dialog import RecuperacionDialog
from views.solicitudes_recuperacion_view import SolicitudesRecuperacionView


class ControllerPrueba(QObject):
    actualizado = Signal(object)
    fallo = Signal(str)
    ocupado = Signal(bool)

    def __init__(self):
        super().__init__()
        self.llamadas = []

    def ejecutar(self, accion, **datos):
        self.llamadas.append((accion, datos))
        self.ocupado.emit(True)
        return True

    def completar(self, **resultado):
        self.actualizado.emit(resultado)
        self.ocupado.emit(False)


class RecuperacionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialogo(self):
        controller = ControllerPrueba()
        dialogo = RecuperacionDialog('persona', controller=controller)
        dialogo._init_timer.stop()
        self.addCleanup(dialogo.deleteLater)
        self.addCleanup(dialogo.close)
        return dialogo, controller

    def test_correo_sin_configurar_no_simula_envio_y_no_hay_selector_de_canales(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='configuracion', canales={'correo': False})
        self.assertTrue(dialogo.solicitar.isEnabled())
        self.assertIn('Puedes registrar la solicitud', dialogo.configuracion.text())
        self.assertEqual(dialogo.findChildren(QComboBox), [])
        self.assertEqual(controller.llamadas, [])

    def test_flujo_visible_y_limpieza_de_secretos(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='configuracion', canales={'correo': True})
        dialogo.solicitar.click()
        self.assertEqual(controller.llamadas[-1], ('solicitar', {'usuario': 'persona', 'canal': 'correo'}))
        controller.completar(accion='solicitar', token='t' * 43, mensaje='Solicitud recibida.')
        self.assertEqual(dialogo.pasos.currentIndex(), 2)
        self.assertTrue(dialogo.timer.isActive())
        self.assertEqual(dialogo.codigo.text(), '')
        controller.completar(accion='estado', estado='codigo_enviado')
        self.assertEqual(dialogo.pasos.currentIndex(), 1)
        dialogo.codigo.setText('ABCD2345')
        dialogo.validar.click()
        self.assertEqual(controller.llamadas[-1][0], 'verificar')
        controller.completar(accion='verificar', estado='aprobada')
        self.assertEqual(dialogo.pasos.currentIndex(), 3)
        self.assertFalse(dialogo.timer.isActive())
        dialogo.password.setText('Nueva1')
        dialogo.confirmacion.setText('Distinta1')
        dialogo.guardar.click()
        self.assertIn('no coinciden', dialogo.error.text())
        dialogo.confirmacion.setText('Nueva1')
        dialogo.guardar.click()
        self.assertEqual(controller.llamadas[-1][0], 'restablecer')
        controller.completar(accion='restablecer', estado='completada')
        self.assertEqual(dialogo.pasos.currentIndex(), 4)
        self.assertIsNone(dialogo.token)
        self.assertEqual(dialogo.password.text(), '')

    def test_rechazo_no_muestra_formulario_de_password(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='estado', estado='rechazada')
        self.assertEqual(dialogo.pasos.currentIndex(), 2)
        self.assertIn('Denegada', dialogo.estado_label.text())
        self.assertFalse(dialogo.timer.isActive())

    def test_retomar_con_codigo_desde_un_dialogo_nuevo_no_pide_otro_correo(self):
        dialogo, controller = self.dialogo()
        dialogo.retomar.click()
        self.assertEqual(dialogo.pasos.currentIndex(), 1)
        dialogo.codigo.setText('ABCD2345')
        dialogo.validar.click()
        self.assertEqual(controller.llamadas[-1], ('retomar', {'usuario': 'persona', 'codigo': 'ABCD2345'}))
        controller.completar(accion='retomar', estado='aprobada', token='nuevo' * 10)
        self.assertEqual(dialogo.pasos.currentIndex(), 3)
        self.assertEqual(dialogo.token, 'nuevo' * 10)
        self.assertFalse(any(accion == 'solicitar' for accion, _ in controller.llamadas))

    def test_reenvio_muestra_dos_minutos_y_se_habilita_solo_al_terminar(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='configuracion', canales={'correo': True})
        with patch('views.recuperacion_dialog.monotonic', return_value=1000) as reloj:
            controller.completar(accion='solicitar', token='t' * 43, mensaje='Solicitud recibida.')
            self.assertEqual(dialogo.reintentar.text(), 'Solicitar otro código (02:00)')
            self.assertFalse(dialogo.reintentar.isEnabled())
            self.assertFalse(dialogo.reiniciar.isEnabled())
            self.assertTrue(dialogo.validar.isEnabled())
            dialogo._reiniciar()
            dialogo._solicitar()
            self.assertEqual(dialogo.pasos.currentIndex(), 2)
            self.assertEqual(controller.llamadas, [])
            reloj.return_value = 1119
            dialogo._actualizar_reenvio()
            self.assertIn('00:01', dialogo.reintentar.text())
            self.assertFalse(dialogo.reintentar.isEnabled())
            reloj.return_value = 1120
            dialogo._actualizar_reenvio()
            self.assertEqual(dialogo.reintentar.text(), 'Solicitar otro código')
            self.assertTrue(dialogo.reintentar.isEnabled())
            self.assertFalse(dialogo._reenvio_timer.isActive())
            dialogo.reintentar.click()
            self.assertEqual(dialogo.pasos.currentIndex(), 0)
            self.assertTrue(dialogo.solicitar.isEnabled())

    def test_respuestas_del_worker_no_eliminan_la_espera_y_cerrar_detiene_timer(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='configuracion', canales={'correo': True})
        with patch('views.recuperacion_dialog.monotonic', return_value=1000):
            controller.completar(accion='solicitar', token='t' * 43, mensaje='Solicitud recibida.')
            controller.completar(accion='estado', estado='pendiente')
            self.assertFalse(dialogo.reiniciar.isEnabled())
            self.assertIn('02:00', dialogo.reiniciar.text())
            dialogo.reject()
            self.assertFalse(dialogo._reenvio_timer.isActive())
            self.assertFalse(dialogo.timer.isActive())

    def test_segundo_envio_reinicia_la_cuenta_regresiva_y_no_depende_de_ticks(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='configuracion', canales={'correo': True})
        with patch('views.recuperacion_dialog.monotonic', return_value=1000) as reloj:
            controller.completar(accion='solicitar', token='t' * 43, mensaje='Solicitud recibida.')
            reloj.return_value = 1090
            dialogo._actualizar_reenvio()
            self.assertIn('00:30', dialogo.reintentar.text())
            reloj.return_value = 1120
            dialogo._actualizar_reenvio()
            dialogo.reintentar.click()
            controller.completar(accion='solicitar', token='u' * 43, mensaje='Solicitud recibida.')
            self.assertIn('02:00', dialogo.reintentar.text())
            self.assertFalse(dialogo.reintentar.isEnabled())

    def test_login_abre_recuperacion_en_lugar_de_mensaje_estatico(self):
        login = LoginView()
        self.addCleanup(login.deleteLater)
        self.addCleanup(login.close)
        login.user_input.setText('persona')
        with patch('views.login_view.RecuperacionDialog') as dialogo:
            login._show_recovery()
            dialogo.assert_called_once_with('persona', parent=login)
            dialogo.return_value.open.assert_called_once()

    def test_bandeja_admin_restringe_aprobacion_y_pide_confirmacion(self):
        controller = ControllerPrueba()
        sesion = SesionUsuario(1, 'admin', 'administrador')
        dialogo = SolicitudesRecuperacionView(sesion, controller=controller)
        self.addCleanup(dialogo.deleteLater)
        self.addCleanup(dialogo.close)
        base = dict(id_solicitud='solicitud', id_usuario=2, usuario='persona', canal='correo',
                    destino='p***@example.com', estado='codigo_enviado', solicitado_en=datetime.now(timezone.utc))
        controller.completar(accion='listar', solicitudes=[base])
        dialogo.tabla.selectRow(0)
        self.assertFalse(dialogo.aprobar.isEnabled())
        self.assertTrue(dialogo.rechazar.isEnabled())
        controller.completar(accion='listar', solicitudes=[dict(base, estado='pendiente')])
        dialogo.tabla.selectRow(0)
        self.assertTrue(dialogo.aprobar.isEnabled())
        dialogo.aprobar.click()
        self.assertEqual(controller.llamadas, [])
        dialogo._confirmacion.confirmar.click()
        self.assertEqual(controller.llamadas[-1], ('aprobar', {'id_solicitud': 'solicitud'}))
        controller.completar(accion='listar', solicitudes=[dict(base, id_usuario=1, estado='pendiente')])
        dialogo.tabla.selectRow(0)
        self.assertFalse(dialogo.aprobar.isEnabled())
        self.assertFalse(dialogo.rechazar.isEnabled())

    def test_bandeja_no_disponible_para_trabajador(self):
        with self.assertRaises(PermissionError):
            SolicitudesRecuperacionView(SesionUsuario(2, 'persona', 'trabajador'))

    def test_tres_solicitudes_misma_cuenta_se_muestran_y_seleccionan_sin_aprobar(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        base = dict(id_usuario=2, usuario='persona', canal='correo', destino='p***@example.com',
                    estado='pendiente', solicitado_en=datetime.now(timezone.utc), envio_intentos=0)
        solicitudes = [dict(base, id_solicitud=f'solicitud-{i}') for i in range(3)]
        view.cargar()
        controller.completar(accion='listar', solicitudes=solicitudes)
        self.assertEqual(view.tabla.rowCount(), 3)
        self.assertIn('3 solicitud(es)', view.resumen.text())
        self.assertIn('3 por revisar', view.resumen.text())
        self.assertEqual(view.tabla.currentRow(), 0)
        self.assertTrue(view.aprobar.isEnabled())
        self.assertTrue(view.rechazar.isEnabled())
        self.assertIn('Puedes autorizar', view.seleccion_label.text())
        self.assertEqual(controller.llamadas, [('listar', {})])
        view.tabla.selectRow(2)
        controller.completar(accion='listar', solicitudes=solicitudes)
        self.assertEqual(view.tabla.rowCount(), 3)
        self.assertEqual(view._seleccion()['id_solicitud'], 'solicitud-2')
        view.aprobar.click()
        view._confirmacion.confirmar.click()
        self.assertEqual(controller.llamadas[-1], ('aprobar', {'id_solicitud': 'solicitud-2'}))

    def test_pagina_dos_conserva_la_solicitud_correcta_para_autorizar_y_al_refrescar(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        base = dict(id_usuario=2, usuario='persona', canal='correo', destino='p***@example.com',
                    estado='pendiente', solicitado_en=datetime.now(timezone.utc))
        solicitudes = [dict(base, id_solicitud=f'solicitud-{i}') for i in range(15)]
        controller.completar(accion='listar', solicitudes=solicitudes)
        self.app.processEvents()
        self.assertEqual(sum(not view.tabla.isRowHidden(i) for i in range(15)), 7)
        view.tabla.siguiente.click()
        self.assertEqual(view._seleccion()['id_solicitud'], 'solicitud-7')
        view.aprobar.click()
        view._confirmacion.confirmar.click()
        self.assertEqual(controller.llamadas[-1], ('aprobar', {'id_solicitud': 'solicitud-7'}))
        controller.completar(accion='listar', solicitudes=[dict(base, id_solicitud='nueva')] + solicitudes)
        self.app.processEvents()
        self.assertEqual(view.tabla.rowCount(), 16)
        self.assertEqual(view.tabla.pagina_actual, 1)
        self.assertEqual(view._seleccion()['id_solicitud'], 'solicitud-7')
        self.assertFalse(view.tabla.isRowHidden(view.tabla.currentRow()))

    def test_historial_muestra_todos_los_estados_y_no_solo_la_pendiente(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        ahora = datetime.now(timezone.utc)
        base = dict(id_usuario=2, usuario='persona', canal='correo', destino='p***@example.com',
                    solicitado_en=ahora, envio_intentos=0)
        estados = ['pendiente', 'rechazada', 'rechazada', 'completada', 'expirada']
        solicitudes = [dict(base, id_solicitud=f'historial-{i}', estado=estado,
                            administrador='admin' if estado in ('rechazada', 'completada') else None,
                            resuelto_en=ahora if estado in ('rechazada', 'completada') else None)
                       for i, estado in enumerate(estados)]
        controller.completar(accion='listar', solicitudes=solicitudes)
        self.assertEqual(view.tabla.rowCount(), 5)
        self.assertIn('5 solicitud(es) en total', view.resumen.text())
        self.assertIn('1 por revisar', view.resumen.text())
        self.assertEqual(view.tabla.item(1, 3).text(), 'Denegada')
        self.assertEqual(view.tabla.item(3, 3).text(), 'Contraseña cambiada')
        self.assertEqual(view.tabla.item(4, 3).text(), 'Caducada')
        self.assertEqual(view.tabla.item(1, 7).text(), 'admin')
        self.assertNotEqual(view.tabla.item(1, 8).text(), '—')
        self.assertIn('historial-1', view.tabla.item(1, 6).toolTip())
        self.assertTrue(view.tabla.isColumnHidden(6))
        for fila in range(1, 5):
            self.assertFalse(view.tabla.isRowHidden(fila))
            view.tabla.selectRow(fila)
            self.assertFalse(view.aprobar.isEnabled())
            self.assertFalse(view.rechazar.isEnabled())
        view.tabla.selectRow(0)
        view.rechazar.click()
        view._confirmacion.confirmar.click()
        controller.completar(accion='rechazar', estado='rechazada')
        solicitudes[0] = dict(solicitudes[0], estado='rechazada', administrador='admin', resuelto_en=ahora)
        controller.completar(accion='listar', solicitudes=solicitudes)
        self.assertEqual(view.tabla.rowCount(), 5)
        self.assertIn('0 por revisar', view.resumen.text())
        self.assertEqual(view.tabla.item(0, 3).text(), 'Denegada')

    def test_confirmacion_denegar_se_cierra_con_x_escape_y_cancelar_sin_decidir(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        view.show()
        controller.completar(accion='listar', solicitudes=[dict(
            id_solicitud='solicitud', id_usuario=2, usuario='persona', canal='correo',
            destino='p***@example.com', estado='pendiente', solicitado_en=datetime.now(timezone.utc))])
        for cerrar in ('x', 'escape', 'cancelar'):
            with self.subTest(cerrar=cerrar):
                QTest.mouseClick(view.rechazar, Qt.LeftButton)
                self.app.processEvents()
                dialogo = view._confirmacion
                self.assertIsNotNone(dialogo)
                self.assertTrue(dialogo.isVisible())
                if cerrar == 'x':
                    self.assertTrue(dialogo.close())
                elif cerrar == 'escape':
                    QTest.keyClick(dialogo, Qt.Key_Escape)
                else:
                    QTest.mouseClick(dialogo.cancelar, Qt.LeftButton)
                self.app.processEvents()
                self.assertIsNone(view._confirmacion)
                self.assertEqual(controller.llamadas, [])
        QTest.mouseClick(view.rechazar, Qt.LeftButton)
        QTest.mouseClick(view._confirmacion.confirmar, Qt.LeftButton)
        self.assertEqual(controller.llamadas, [('rechazar', {'id_solicitud': 'solicitud'})])

    def test_solicitud_sin_correo_se_ve_y_puede_denegarse_pero_no_enviarse(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        base = dict(id_solicitud='solicitud', id_usuario=2, usuario='persona', canal='correo',
                    destino='Sin correo registrado', estado='pendiente', solicitado_en=datetime.now(timezone.utc),
                    correo_pendiente=True)
        controller.completar(accion='listar', solicitudes=[base])
        self.assertEqual(view.tabla.rowCount(), 1)
        self.assertIn('Falta registrar correo', view.tabla.item(0, 4).text())
        self.assertFalse(view.aprobar.isEnabled())
        self.assertTrue(view.rechazar.isEnabled())
        self.assertIn('Editar acceso', view.seleccion_label.text())
        controller.completar(accion='listar', solicitudes=[dict(base, destino='p***@example.com', correo_pendiente=False)])
        self.assertTrue(view.aprobar.isEnabled())

    def test_refresco_periodico_no_interfiere_con_confirmacion_abierta(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        controller.completar(accion='listar', solicitudes=[dict(
            id_solicitud='solicitud', id_usuario=2, usuario='persona', canal='correo',
            destino='p***@example.com', estado='pendiente', solicitado_en=datetime.now(timezone.utc))])
        view.aprobar.click()
        view.cargar()
        self.assertEqual(controller.llamadas, [])
        self.assertTrue(view._recargar)
        view._confirmacion.confirmar.click()
        self.assertEqual(controller.llamadas, [('aprobar', {'id_solicitud': 'solicitud'})])
        controller.completar(accion='aprobar', estado='codigo_enviado')
        self.assertEqual(controller.llamadas[-1], ('listar', {}))

    def test_bandeja_prioriza_solicitud_pendiente_ajena_y_explica_bloqueos(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        base = dict(id_solicitud='propia', id_usuario=1, usuario='admin', canal='correo',
                    destino='a***@example.com', estado='pendiente', solicitado_en=datetime.now(timezone.utc))
        solicitudes = [base, dict(base, id_solicitud='caducada', id_usuario=2, estado='expirada'),
                       dict(base, id_solicitud='ajena', id_usuario=2, usuario='persona')]
        controller.completar(accion='listar', solicitudes=solicitudes)
        self.assertEqual(view.tabla.currentRow(), 2)
        self.assertTrue(view.aprobar.isEnabled())
        view.tabla.selectRow(0)
        self.assertFalse(view.aprobar.isEnabled())
        self.assertIn('Otro administrador', view.seleccion_label.text())
        view.tabla.selectRow(1)
        self.assertFalse(view.aprobar.isEnabled())
        self.assertIn('Caducada', view.seleccion_label.text())
        controller.completar(accion='listar', solicitudes=[])
        self.assertEqual(view.tabla.rowCount(), 0)
        self.assertFalse(view.aprobar.isEnabled())
        self.assertIn('0 solicitud(es)', view.resumen.text())

    def test_bandeja_separa_autorizacion_y_fallo_del_correo_y_permite_reintentar(self):
        controller = ControllerPrueba()
        view = SolicitudesRecuperacionView(SesionUsuario(1, 'admin', 'administrador'), controller=controller)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        controller.completar(accion='listar', solicitudes=[dict(
            id_solicitud='solicitud', id_usuario=2, usuario='persona', canal='correo',
            destino='p***@example.com', estado='envio_fallido', solicitado_en=datetime.now(timezone.utc))])
        view.tabla.selectRow(0)
        self.assertIn('Autorizada', view.tabla.item(0, 3).text())
        self.assertEqual(view.tabla.item(0, 4).text(), 'No enviado')
        self.assertIn('autorizada', view.mensaje.text())
        self.assertTrue(view.aprobar.isEnabled())
        self.assertEqual(view.aprobar.text(), 'Reintentar envío')

    def test_cerrar_tras_solicitar_no_envia_ninguna_orden_de_cancelacion(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='configuracion', canales={'correo': True})
        dialogo.solicitar.click()
        controller.completar(accion='solicitar', token='t' * 43, mensaje='En espera de autorización.')
        dialogo.reject()
        self.assertEqual([accion for accion, _ in controller.llamadas], ['solicitar'])
        self.assertIsNone(dialogo.token)
        self.assertFalse(dialogo.timer.isActive())

    def test_correo_fallido_no_muestra_password_ni_confunde_una_solicitud_denegada(self):
        dialogo, controller = self.dialogo()
        controller.completar(accion='estado', estado='envio_fallido')
        self.assertEqual(dialogo.pasos.currentIndex(), 2)
        self.assertIn('autorizada', dialogo.estado_label.text())
        self.assertIn('correo no pudo enviarse', dialogo.estado_label.text())
        self.assertTrue(dialogo.timer.isActive())

    def test_worker_no_bloquea_y_rechaza_operacion_simultanea(self):
        class ServicioPrueba:
            def ejecutar(self, accion, **datos):
                return {'accion': accion, 'canales': {}}

        controller = RecuperacionController(servicio=ServicioPrueba())
        resultados, estados = [], []
        espera = QEventLoop()
        controller.actualizado.connect(resultados.append)
        controller.ocupado.connect(estados.append)
        controller.ocupado.connect(lambda ocupado: None if ocupado else espera.quit())
        self.assertTrue(controller.ejecutar('configuracion'))
        self.assertFalse(controller.ejecutar('configuracion'))
        QTimer.singleShot(5000, espera.quit)
        espera.exec()
        self.assertEqual(len(resultados), 1)
        self.assertEqual(estados, [True, False])


if __name__ == '__main__':
    unittest.main()
