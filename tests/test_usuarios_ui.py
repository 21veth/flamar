import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QEvent, QEventLoop, QObject, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QEnterEvent, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QBoxLayout, QDialog, QFrame, QLabel, QLineEdit, QMessageBox

from controllers.usuarios_controller import UsuariosController
from models.sesion_usuario import SesionUsuario
from views.usuarios_view import UsuarioDialog, UsuariosView
from views.usuarios_theme import COLORS, DIALOG_STYLE, USERS_STYLE, UserDelegate
from views.dashboard_theme import DASHBOARD_PALETTE


class ControllerPrueba(QObject):
    actualizado = Signal(object)
    fallo = Signal(str)
    ocupado = Signal(bool)

    def __init__(self):
        super().__init__()
        self.llamadas = []
        self.trabajando = False

    def ejecutar(self, accion, **datos):
        if self.trabajando:
            return False
        self.trabajando = True
        self.llamadas.append((accion, datos))
        self.ocupado.emit(True)
        return True

    def completar(self, resultado):
        self.actualizado.emit(resultado)
        self.trabajando = False
        self.ocupado.emit(False)


class UsuariosUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.sesion = SesionUsuario(1, 'admin', 'administrador')
        self.controller = ControllerPrueba()
        self.recovery_controller = ControllerPrueba()
        self.view = UsuariosView(self.sesion, controller=self.controller, recovery_controller=self.recovery_controller)
        self.addCleanup(self.view.deleteLater)
        self.addCleanup(self.view.close)
        self.admin = dict(id_usuario=1, usuario='admin', rol='administrador', activo=True,
                          ultimo_acceso=None, fecha_creacion=datetime.now(timezone.utc),
                          correo='admin@example.com', telefono='+51900000001')
        self.otro = dict(self.admin, id_usuario=2, usuario='otro', rol='trabajador', activo=False,
                         correo='otro@example.com', telefono='+51900000002')

    def cargar(self):
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': [self.admin, self.otro]})

    def foto_prueba(self):
        directory = TemporaryDirectory(prefix='zeyver-foto-ui-')
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'retrato.png'
        image = QImage(180, 120, QImage.Format_RGB32)
        image.fill(QColor('#458ac1'))
        self.assertTrue(image.save(str(path)))
        return str(path)

    def test_listado_real_vacio_y_seleccion(self):
        self.assertEqual(self.controller.llamadas, [])
        self.assertEqual(self.view.tabla.rowCount(), 0)
        self.assertFalse(self.view.editar.isEnabled())
        self.cargar()
        self.assertEqual(self.view.tabla.rowCount(), 2)
        self.assertEqual(self.view.tabla.item(1, 3).text(), 'Inactivo')
        self.view.tabla.selectRow(1)
        self.assertTrue(self.view.editar.isEnabled())
        self.assertTrue(self.view.eliminar.isEnabled())
        self.view.tabla.selectRow(0)
        self.assertFalse(self.view.eliminar.isEnabled())
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': []})
        self.assertIn('No hay usuarios', self.view.resumen.text())
        self.assertFalse(self.view.editar.isEnabled())

    def test_paginacion_del_directorio_edita_el_usuario_de_la_pagina_visible(self):
        usuarios = [dict(self.otro, id_usuario=i + 2, usuario=f'persona-{i}') for i in range(15)]
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': usuarios})
        self.app.processEvents()
        self.assertEqual(self.view.tabla.rowCount(), 15)
        self.assertEqual(sum(not self.view.tabla.isRowHidden(i) for i in range(15)), 7)
        self.view.tabla.siguiente.click()
        self.assertEqual(self.view._seleccionado()['id_usuario'], 9)
        self.view.editar.click()
        self.assertEqual(self.view._dialogo.registro['id_usuario'], 9)
        self.assertEqual(self.view._dialogo.usuario.text(), 'persona-7')
        self.view._dialogo.reject()

    def test_busqueda_y_filtros(self):
        self.view.buscar.setText('otro')
        self.view.rol.setCurrentIndex(self.view.rol.findData('trabajador'))
        self.assertEqual(self.controller.llamadas[-1], ('listar', dict(buscar='otro', rol='trabajador', activo=None)))
        self.controller.completar({'accion': 'listar', 'usuarios': []})
        self.view.estado.setCurrentIndex(self.view.estado.findData(False))
        self.assertEqual(self.controller.llamadas[-1], ('listar', dict(buscar='otro', rol='trabajador', activo=False)))

    def test_busqueda_al_escribir_agrupa_teclas_y_al_borrar_recupera_la_lista(self):
        self.view.buscar.setText('o')
        self.view.buscar.setText('ot')
        self.view.buscar.setText('otro')
        self.assertEqual(self.controller.llamadas, [])
        for _ in range(20):
            if self.controller.llamadas:
                break
            QTest.qWait(50)
        self.assertEqual(self.controller.llamadas, [('listar', dict(buscar='otro', rol=None, activo=None))])
        self.controller.completar({'accion': 'listar', 'usuarios': [self.otro]})
        self.assertEqual(self.view.tabla.rowCount(), 1)
        self.assertEqual(self.view.metric_values['total'].text(), '1')
        self.view.buscar.clear()
        llamadas_antes = len(self.controller.llamadas)
        for _ in range(20):
            if len(self.controller.llamadas) > llamadas_antes:
                break
            QTest.qWait(50)
        self.assertEqual(self.controller.llamadas[-1], ('listar', dict(buscar='', rol=None, activo=None)))
        self.controller.completar({'accion': 'listar', 'usuarios': [self.admin, self.otro]})
        self.assertEqual(self.view.tabla.rowCount(), 2)

    def test_se_puede_seguir_escribiendo_y_se_ignoran_resultados_anteriores(self):
        self.view.buscar.setText('a')
        self.view.cargar()
        self.assertTrue(self.view.buscar.isEnabled())
        self.view.buscar.setText('otro')
        QTest.qWait(350)
        self.assertEqual(len(self.controller.llamadas), 1)
        self.controller.completar({'accion': 'listar', 'usuarios': [self.admin]})
        self.assertEqual(self.view.tabla.rowCount(), 0)
        self.assertEqual(self.controller.llamadas[-1], ('listar', dict(buscar='otro', rol=None, activo=None)))
        self.controller.completar({'accion': 'listar', 'usuarios': [self.otro]})
        self.assertEqual(self.view.tabla.item(0, 1).text(), 'otro')

    def test_enter_busca_sin_esperar_ni_duplicar_la_consulta(self):
        self.view.buscar.setText('otro')
        self.view.buscar.returnPressed.emit()
        self.assertEqual(len(self.controller.llamadas), 1)
        self.controller.completar({'accion': 'listar', 'usuarios': [self.otro]})
        QTest.qWait(350)
        self.assertEqual(len(self.controller.llamadas), 1)

    def test_ultima_busqueda_se_recupera_aunque_falle_una_consulta_anterior(self):
        self.view.buscar.setText('a')
        self.view.cargar()
        self.view.buscar.setText('otro')
        QTest.qWait(350)
        self.controller.fallo.emit('No se pudo conectar.')
        self.controller.trabajando = False
        self.controller.ocupado.emit(False)
        self.assertEqual(self.controller.llamadas[-1], ('listar', dict(buscar='otro', rol=None, activo=None)))

    def test_crear_sin_campos_password_y_conservar_formulario_en_error(self):
        self.view.nuevo.click()
        dialogo = self.view._dialogo
        self.assertIsInstance(dialogo, UsuarioDialog)
        self.assertFalse(hasattr(dialogo, 'contrasena'))
        dialogo.usuario.setText('nuevo')
        dialogo.correo.setText('nuevo@example.com')
        dialogo.telefono.setText('+51987654321')
        dialogo.guardar_button.click()
        self.assertEqual(self.controller.llamadas[-1], ('crear', dict(
            usuario='nuevo', rol='trabajador', activo=True,
            correo='nuevo@example.com', telefono='+51987654321')))
        self.assertFalse(dialogo.guardar_button.isEnabled())
        self.controller.fallo.emit('Ese nombre de usuario ya existe.')
        self.controller.trabajando = False
        self.controller.ocupado.emit(False)
        self.assertIs(self.view._dialogo, dialogo)
        self.assertEqual(dialogo.usuario.text(), 'nuevo')
        self.assertIn('ya existe', dialogo.error.text())
        self.assertTrue(dialogo.guardar_button.isEnabled())
        dialogo.guardar_button.click()
        resultado = {'accion': 'crear', 'id_usuario': 3, 'usuario': 'nuevo', 'contrasena_temporal': '01234567'}
        self.controller.completar(resultado)
        self.assertIsNone(self.view._dialogo)
        credenciales = self.view._credenciales
        self.assertEqual(credenciales.clave.text(), '01234567')
        self.assertNotIn('contrasena_temporal', resultado)
        credenciales.cerrar.click()
        self.assertEqual(credenciales.clave.text(), '')
        self.assertIsNone(self.view._credenciales)
        self.assertEqual(self.controller.llamadas[-1][0], 'listar')

    def test_editar_estado_y_rol_sin_campos_password(self):
        self.cargar()
        self.view.tabla.selectRow(1)
        self.view.editar.click()
        dialogo = self.view._dialogo
        self.assertFalse(hasattr(dialogo, 'contrasena'))
        self.assertFalse(hasattr(dialogo, 'confirmacion'))
        dialogo.rol.setCurrentIndex(dialogo.rol.findData('gerente'))
        dialogo.activo.setChecked(True)
        dialogo.guardar_button.click()
        self.assertEqual(self.controller.llamadas[-1], ('modificar', dict(
            id_usuario=2, usuario='otro', rol='gerente', activo=True,
            correo='otro@example.com', telefono='+51900000002')))

    def test_contactos_se_cargan_editan_y_muestran_sin_marcarlos_verificados(self):
        self.otro.update(correo='otro@example.com', telefono='+51987654321')
        self.cargar()
        self.view.tabla.selectRow(1)
        self.assertEqual(self.view.perfil_correo.text(), 'otro@example.com')
        self.assertEqual(self.view.perfil_telefono.text(), '+51987654321')
        self.assertNotIn('Verificación', [label.text() for label in self.view.carnet.findChildren(QLabel)])
        self.view.editar.click()
        dialogo = self.view._dialogo
        self.assertEqual(dialogo.correo.text(), 'otro@example.com')
        self.assertEqual(dialogo.telefono.text(), '+51987654321')
        dialogo.correo.setText('cambio@example.com')
        dialogo.telefono.clear()
        dialogo.guardar_button.click()
        self.assertIn('obligatorio', dialogo.error.text())
        self.assertEqual(self.controller.llamadas[-1][0], 'listar')
        dialogo.telefono.setText('+51987654322')
        dialogo.guardar_button.click()
        self.assertEqual(self.controller.llamadas[-1][1]['correo'], 'cambio@example.com')
        self.assertEqual(self.controller.llamadas[-1][1]['telefono'], '+51987654322')
        self.assertNotIn('correo_verificado_en', self.controller.llamadas[-1][1])

    def test_usuarios_antiguos_sin_contactos_se_pueden_editar(self):
        self.otro.update(correo=None, telefono=None)
        self.cargar()
        self.view.tabla.selectRow(1)
        self.assertEqual(self.view.perfil_correo.text(), 'Sin registrar')
        self.assertEqual(self.view.perfil_telefono.text(), 'Sin registrar')
        self.view.editar.click()
        self.assertEqual(self.view._dialogo.correo.text(), '')
        self.assertEqual(self.view._dialogo.telefono.text(), '')
        self.view._dialogo.establecer_ocupado(True)
        self.assertFalse(self.view._dialogo.correo.isEnabled())
        self.assertFalse(self.view._dialogo.telefono.isEnabled())

    def test_formulario_bloquea_contactos_vacios_invalidos_y_omitidos(self):
        self.view.nuevo.click()
        dialogo = self.view._dialogo
        dialogo.usuario.setText('nuevo')
        for correo, telefono, mensaje in (
            ('', '', 'correo'), ('nombre@example.com', '', 'teléfono'),
            ('incorrecto', '+51987654321', 'correo'), ('nombre@example.com', '123', 'país'),
        ):
            dialogo.correo.setText(correo)
            dialogo.telefono.setText(telefono)
            dialogo.guardar_button.click()
            self.assertIn(mensaje, dialogo.error.text())
            self.assertEqual(self.controller.llamadas, [])

    def test_agregar_foto_previsualiza_y_envia_el_archivo_solo_al_guardar(self):
        path = self.foto_prueba()
        self.view.nuevo.click()
        dialogo = self.view._dialogo
        with patch('views.usuarios_view.QFileDialog.getOpenFileName', return_value=(path, '')):
            dialogo.elegir_foto.click()
        self.assertFalse(dialogo.foto.imagen.isNull())
        self.assertTrue(dialogo.quitar_foto.isEnabled())
        self.assertEqual(self.controller.llamadas, [])
        dialogo.usuario.setText('nuevo')
        dialogo.correo.setText('nuevo@example.com')
        dialogo.telefono.setText('+51987654321')
        dialogo.guardar_button.click()
        self.assertEqual(self.controller.llamadas[-1][1]['foto_perfil'], path)
        self.assertFalse(dialogo.elegir_foto.isEnabled())
        self.assertFalse(dialogo.quitar_foto.isEnabled())

    def test_editar_conserva_reemplaza_y_quita_la_foto(self):
        path = self.foto_prueba()
        self.otro['foto_perfil'] = path
        dialogo = UsuarioDialog(self.sesion, self.otro, self.view)
        self.addCleanup(dialogo.deleteLater)
        enviados = []
        dialogo.guardar.connect(enviados.append)
        self.assertFalse(dialogo.foto.imagen.isNull())
        dialogo.guardar_button.click()
        self.assertNotIn('foto_perfil', enviados[-1])
        dialogo.quitar_foto.click()
        self.assertTrue(dialogo.foto.imagen.isNull())
        self.assertEqual(dialogo.foto.text(), 'O')
        dialogo.guardar_button.click()
        self.assertIsNone(enviados[-1]['foto_perfil'])
        with patch('views.usuarios_view.QFileDialog.getOpenFileName', return_value=(path, '')):
            dialogo.elegir_foto.click()
        dialogo.guardar_button.click()
        self.assertEqual(enviados[-1]['foto_perfil'], path)

    def test_cancelar_o_elegir_imagen_invalida_conserva_foto_anterior(self):
        path = self.foto_prueba()
        self.otro['foto_perfil'] = path
        dialogo = UsuarioDialog(self.sesion, self.otro, self.view)
        self.addCleanup(dialogo.deleteLater)
        for selection in ('', path + '.inexistente'):
            with patch('views.usuarios_view.QFileDialog.getOpenFileName', return_value=(selection, '')):
                dialogo.elegir_foto.click()
            self.assertFalse(dialogo._foto_cambiada)
            self.assertFalse(dialogo.foto.imagen.isNull())
        self.assertFalse(dialogo.error.isHidden())

    def test_foto_en_carnet_y_fallback_al_cambiar_usuario_o_archivo_perdido(self):
        self.otro['foto_perfil'] = self.foto_prueba()
        self.cargar()
        self.view.tabla.selectRow(1)
        self.assertFalse(self.view.perfil_avatar.imagen.isNull())
        self.view.tabla.selectRow(0)
        self.assertTrue(self.view.perfil_avatar.imagen.isNull())
        self.otro['foto_perfil'] += '.inexistente'
        self.view.tabla.item(1, 0).setData(Qt.UserRole, self.otro)
        self.view.tabla.selectRow(1)
        self.assertTrue(self.view.perfil_avatar.imagen.isNull())
        self.assertEqual(self.view.perfil_avatar.text(), 'O')

    def test_formulario_contacto_tiene_scroll_y_botones_fuera_del_scroll(self):
        self.view.nuevo.click()
        dialogo = self.view._dialogo
        dialogo.show()
        self.app.processEvents()
        self.assertIsNotNone(dialogo.form_scroll.widget())
        self.assertTrue(dialogo.form_scroll.widget().isAncestorOf(dialogo.correo))
        self.assertFalse(dialogo.form_scroll.widget().isAncestorOf(dialogo.guardar_button))

    def test_propia_cuenta_con_permisos_bloqueados_y_reautenticacion(self):
        self.cargar()
        self.view.tabla.selectRow(0)
        self.view.editar.click()
        dialogo = self.view._dialogo
        self.assertFalse(dialogo.rol.isEnabled())
        self.assertFalse(dialogo.activo.isEnabled())
        dialogo.establecer_ocupado(True)
        dialogo.establecer_ocupado(False)
        self.assertFalse(dialogo.rol.isEnabled())
        self.assertFalse(dialogo.activo.isEnabled())
        eventos = []
        self.view.reautenticar.connect(lambda: eventos.append(True))
        dialogo.guardar_button.click()
        with patch.object(QMessageBox, 'information'):
            self.controller.completar({'accion': 'modificar', 'id_usuario': 1, 'reautenticar': True})
        self.assertEqual(eventos, [True])
        self.assertEqual(self.controller.llamadas[-1][0], 'modificar')

    def test_eliminar_requiere_confirmacion_y_no_elimina_cuenta_propia(self):
        self.cargar()
        self.view.tabla.selectRow(0)
        self.view._eliminar()
        self.assertIsNone(self.view._confirmacion)
        self.view.tabla.selectRow(1)
        self.view.eliminar.click()
        self.view._confirmacion.cancelar.click()
        self.assertEqual(self.controller.llamadas[-1][0], 'listar')
        self.view.eliminar.click()
        self.view._confirmacion.confirmar.click()
        self.assertEqual(self.controller.llamadas[-1], ('eliminar', {'id_usuario': 2}))

    def test_confirmacion_eliminar_no_bloquea_y_x_escape_cancelan(self):
        self.cargar()
        self.view.tabla.selectRow(1)
        for cerrar in ('x', 'escape'):
            with self.subTest(cerrar=cerrar):
                self.view._eliminar()
                dialogo = self.view._confirmacion
                self.app.processEvents()
                self.assertTrue(dialogo.isVisible())
                if cerrar == 'x':
                    self.assertTrue(dialogo.close())
                else:
                    QTest.keyClick(dialogo, Qt.Key_Escape)
                self.app.processEvents()
                self.assertIsNone(self.view._confirmacion)
                self.assertEqual(self.controller.llamadas, [('listar', dict(buscar='', rol=None, activo=None))])

    def test_recarga_pendiente_no_interfiere_con_confirmacion_de_borrado(self):
        self.cargar()
        self.view.tabla.selectRow(1)
        self.view.eliminar.click()
        self.view.cargar()
        self.assertEqual(len(self.controller.llamadas), 1)
        self.view._confirmacion.confirmar.click()
        self.assertEqual(self.controller.llamadas[-1], ('eliminar', {'id_usuario': 2}))
        self.controller.completar({'accion': 'eliminar', 'id_usuario': 2})
        self.assertEqual(self.controller.llamadas[-1][0], 'listar')

    def test_sin_acceso_para_otros_roles(self):
        for rol in ('gerente', 'trabajador'):
            with self.assertRaises(PermissionError):
                UsuariosView(SesionUsuario(2, 'otro', rol), controller=self.controller)

    def test_renderizado_en_los_dos_tamanos(self):
        self.cargar()
        self.view.show()
        for ancho, alto in ((1280, 945), (900, 700)):
            self.view.resize(ancho, alto)
            self.app.processEvents()
            self.assertFalse(self.view.grab().isNull())

    def test_paleta_zeyver_en_pagina_y_formularios(self):
        self.assertEqual(self.view.styleSheet(), USERS_STYLE)
        for key in ('accent', 'background', 'graphite', 'ink'):
            self.assertEqual(COLORS[key], DASHBOARD_PALETTE[key])
        for color in ('#5525f5', '#263556', '#f6f9fe', '#081433'):
            self.assertNotIn(color, USERS_STYLE)
            self.assertNotIn(color, DIALOG_STYLE)
        self.assertIsInstance(self.view.tabla.itemDelegate(), UserDelegate)
        self.view.nuevo.click()
        self.assertEqual(self.view._dialogo.styleSheet(), DIALOG_STYLE)
        self.assertTrue(self.view._dialogo.error.isHidden())

    def test_sin_banner_y_formulario_informa_clave_temporal_automatica(self):
        self.assertIsNone(self.view.findChild(QFrame, 'hero'))
        self.assertIs(self.view.content.itemAt(1).widget(), self.view.tabs)
        self.assertIs(self.view.cuentas.layout().itemAt(0).layout(), self.view.metric_grid)
        self.assertNotIn('QFrame#hero', USERS_STYLE)
        self.view.nuevo.click()
        self.assertFalse(hasattr(self.view._dialogo, 'contrasena'))
        self.assertTrue(any('8 dígitos' in label.text() for label in self.view._dialogo.findChildren(QLabel)))

    def test_solicitudes_integradas_en_otra_pestana_sin_ventana_independiente(self):
        self.assertEqual(self.view.tabs.count(), 2)
        self.assertEqual(self.view.tabs.tabText(0), 'Usuarios')
        self.assertIs(self.view.tabs.widget(1), self.view.solicitudes)
        self.assertTrue(self.view.isAncestorOf(self.view.solicitudes))
        self.assertFalse(self.view.solicitudes.isWindow())
        self.assertEqual(self.recovery_controller.llamadas, [])
        self.view.tabs.setCurrentIndex(1)
        self.assertEqual(self.recovery_controller.llamadas, [('listar', {})])
        self.assertTrue(self.view.nuevo.isHidden())
        self.view.tabs.setCurrentIndex(0)
        self.assertFalse(self.view.nuevo.isHidden())

    def test_indicadores_solo_cuentan_los_resultados_recibidos(self):
        self.assertEqual(self.view.metric_values['total'].text(), '—')
        self.cargar()
        for key, value in (('total', '2'), ('activos', '1'), ('admins', '1'), ('inactivos', '1')):
            self.assertEqual(self.view.metric_values[key].text(), value)
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': [self.otro]})
        self.assertEqual(self.view.metric_values['total'].text(), '1')
        self.assertEqual(self.view.metric_values['admins'].text(), '0')

    def test_ficha_lateral_sigue_la_seleccion_y_la_conserva_al_recargar(self):
        self.cargar()
        self.view.tabla.selectRow(1)
        self.assertEqual(self.view.perfil_nombre.text(), 'otro')
        self.assertIn('Inactivo', self.view.perfil_estado.text())
        self.assertIn('Sin permisos', self.view.permisos.text())
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': [self.otro, self.admin]})
        self.assertEqual(self.view._seleccionado()['id_usuario'], 2)
        self.assertEqual(self.view.perfil_nombre.text(), 'otro')
        self.view.tabla.selectRow(1)
        self.assertIn('Tu cuenta', self.view.perfil_rol.text())
        self.assertFalse(self.view.eliminar.isEnabled())

    def test_carnet_arranca_por_el_frente_y_los_botones_estan_fuera(self):
        self.cargar()
        carnet = self.view.carnet
        self.assertFalse(carnet.back_visible)
        self.assertEqual(carnet.codigo.text(), 'ACC-001')
        self.assertTrue(carnet.isAncestorOf(self.view.perfil_nombre))
        self.assertTrue(carnet.isAncestorOf(self.view.perfil_correo))
        self.assertFalse(carnet.isAncestorOf(self.view.editar))
        self.assertFalse(carnet.isAncestorOf(self.view.eliminar))
        self.view.resize(1280, 945)
        self.view.show()
        self.app.processEvents()
        self.assertGreaterEqual(self.view.editar.y(), carnet.y() + carnet.height())

    def test_carnet_click_fija_el_reverso_y_segundo_click_vuelve(self):
        self.cargar()
        carnet = self.view.carnet
        QTest.mouseClick(carnet, Qt.LeftButton)
        QTest.qWait(480)
        self.assertTrue(carnet.back_visible)
        self.app.sendEvent(carnet, QEvent(QEvent.Leave))
        QTest.qWait(480)
        self.assertTrue(carnet.back_visible)
        QTest.mouseClick(carnet, Qt.LeftButton)
        QTest.qWait(480)
        self.assertFalse(carnet.back_visible)

    def test_carnet_hover_temporal_y_click_durante_hover_lo_fija(self):
        self.cargar()
        carnet = self.view.carnet
        enter = lambda: self.app.sendEvent(carnet, QEnterEvent(QPointF(), QPointF(), QPointF()))
        enter()
        QTest.qWait(800)
        self.assertTrue(carnet.back_visible)
        self.app.sendEvent(carnet, QEvent(QEvent.Leave))
        QTest.qWait(480)
        self.assertFalse(carnet.back_visible)
        enter()
        QTest.qWait(800)
        QTest.mouseClick(carnet, Qt.LeftButton)
        self.app.sendEvent(carnet, QEvent(QEvent.Leave))
        QTest.qWait(480)
        self.assertTrue(carnet.back_visible)

    def test_carnet_se_reinicia_al_cambiar_usuario_y_refleja_estado(self):
        self.cargar()
        carnet = self.view.carnet
        QTest.keyClick(carnet, Qt.Key_Space)
        QTest.qWait(480)
        self.assertTrue(carnet.back_visible)
        # Busy state changes must not turn over the selected person's card.
        self.view._establecer_ocupado(True)
        self.view._establecer_ocupado(False)
        self.assertTrue(carnet.back_visible)
        self.view.tabla.selectRow(1)
        self.assertFalse(carnet.back_visible)
        self.assertEqual(carnet.codigo.text(), 'ACC-002')
        self.assertFalse(carnet.estado.property('active'))
        QTest.keyClick(carnet, Qt.Key_Return)
        QTest.qWait(480)
        self.assertTrue(carnet.back_visible)
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': []})
        self.assertFalse(carnet.back_visible)
        self.assertEqual(carnet.codigo.text(), 'ACC-—')

    def test_carnet_renderiza_ambas_caras_en_tamanos_adaptables(self):
        self.otro.update(usuario='Nombre de usuario bastante largo para el carnet',
                         correo='contacto.largo.' * 8 + '@example.com', telefono='+51987654321')
        self.cargar()
        self.view.tabla.selectRow(1)
        self.view.show()
        for width in (900, 1280):
            self.view.resize(width, 945)
            self.app.processEvents()
            for progress in (0.0, .25, .5, .75, 1.0):
                self.view.carnet._animate(progress)
                self.assertFalse(self.view.carnet.grab().isNull())
        self.assertEqual(self.view.perfil_correo.text(), self.otro['correo'])

    def test_vacio_y_diseno_adaptable(self):
        self.cargar()
        self.assertTrue(self.view.vacio.isHidden())
        self.view.show()
        self.view.resize(900, 700)
        self.app.processEvents()
        self.assertEqual(self.view.body.direction(), QBoxLayout.TopToBottom)
        self.view.resize(1280, 945)
        self.app.processEvents()
        self.assertEqual(self.view.body.direction(), QBoxLayout.LeftToRight)
        self.view.cargar()
        self.controller.completar({'accion': 'listar', 'usuarios': []})
        self.assertFalse(self.view.vacio.isHidden())
        self.assertTrue(self.view.tabla.isHidden())
        self.assertEqual(self.view.contador.text(), '0')
        self.assertEqual(self.view.metric_values['total'].text(), '0')
        self.assertEqual(self.view.perfil_estado.text(), '—')

    def test_controller_en_segundo_plano_sin_doble_envio(self):
        class ServicioPrueba:
            def ejecutar(self, accion, **datos):
                return {'accion': accion, 'usuarios': []}

        controller = UsuariosController(self.sesion, servicio=ServicioPrueba())
        resultados, estados = [], []
        espera = QEventLoop()
        controller.actualizado.connect(resultados.append)
        controller.ocupado.connect(estados.append)
        controller.ocupado.connect(lambda ocupado: None if ocupado else espera.quit())
        self.assertTrue(controller.ejecutar('listar'))
        self.assertFalse(controller.ejecutar('listar'))
        QTimer.singleShot(5000, espera.quit)
        espera.exec()
        self.assertEqual(resultados, [{'accion': 'listar', 'usuarios': []}])
        self.assertEqual(estados, [True, False])
        self.assertIsNone(controller._worker)


if __name__ == '__main__':
    unittest.main()
