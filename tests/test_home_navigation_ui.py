import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from models.sesion_usuario import SesionUsuario
from views.decision_redesign_views import ReportsView, SupplyView
from views.home_view import HomeView, NativePageView
from views.intelligence_redesign_views import SmartRecommendationsView
from views.dashboard_theme import DASHBOARD_PALETTE, DASHBOARD_SHELL_STYLES


class HomeNavigationUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_menu_conserva_solo_recomendaciones_inteligentes(self):
        items = HomeView.PAGE_ITEMS + HomeView.INTELLIGENCE_ITEMS + HomeView.DECISION_ITEMS
        self.assertNotIn('recomendaciones', [item[1] for item in items])
        self.assertEqual(
            [item for item in items if item[0].startswith('Recomendaciones')],
            [('Recomendaciones inteligentes', 'recomendaciones_ia', 'spark', SmartRecommendationsView)],
        )
        self.assertEqual([item[1] for item in HomeView.DECISION_ITEMS], ['abastecimiento', 'reportes'])

    def home(self, rol='administrador'):
        # Keep all navigation entries without starting the radar data controller.
        intelligence = tuple(
            (text, key, icon, (lambda sesion: QWidget()) if key == 'tendencias' else view)
            for text, key, icon, view in HomeView.INTELLIGENCE_ITEMS
        )
        with patch.object(HomeView, 'INTELLIGENCE_ITEMS', intelligence), \
                patch('views.usuarios_view.UsuariosController'), \
                patch('views.solicitudes_recuperacion_view.RecuperacionController'), \
                patch('views.home_view.RecuperacionController'):
            home = HomeView(SesionUsuario(1, 'Usuario Prueba', rol))
        self.addCleanup(home.deleteLater)
        self.addCleanup(home.close)
        return home

    def test_navegacion_sin_pagina_duplicada(self):
        home = self.home()
        for mapping in (home.nav_buttons, home.page_indexes, home.page_views):
            self.assertNotIn('recomendaciones', mapping)
        self.assertEqual(home.pages.count(), len(home.nav_buttons))
        for key, view_class in (
            ('recomendaciones_ia', SmartRecommendationsView),
            ('abastecimiento', SupplyView),
            ('reportes', ReportsView),
            ('dashboard', HomeView.PAGE_ITEMS[0][3]),
        ):
            with self.subTest(key=key):
                home.nav_buttons[key].click()
                self.assertIs(home.pages.currentWidget(), home.page_views[key])
                self.assertIsInstance(home.page_views[key].page, view_class)
                self.assertTrue(home.nav_buttons[key].isChecked())

    def test_cuenta_solo_en_cabecera_en_todos_los_modulos(self):
        home = self.home()
        for key in home.page_views:
            for collapsed in (False, True):
                with self.subTest(key=key, collapsed=collapsed):
                    home.nav_buttons[key].click()
                    home._set_sidebar_collapsed(collapsed)
                    for name in ('sidebarAvatar', 'accountName', 'accountRole'):
                        self.assertIsNone(home.sidebar.findChild(QLabel, name))
                    layout = home.sidebar.layout()
                    self.assertIs(layout.itemAt(layout.count() - 1).widget(), home.logout_button)
                    if key != 'tendencias':
                        names = home.page_views[key].page.findChildren(QLabel, 'accountName')
                        self.assertIn(home.sesion.usuario, [label.text() for label in names])

    def test_cerrar_sesion_sigue_funcionando(self):
        home = self.home()
        logout = []
        home.logout_requested.connect(lambda: logout.append(True))
        home.logout_button.click()
        self.assertEqual(logout, [True])

    def test_notificacion_se_integra_en_gestion_sin_otro_apartado_en_sidebar(self):
        home = self.home()
        usuarios = home.page_views['usuarios'].page
        self.assertFalse(hasattr(home, 'recovery_notice'))
        self.assertFalse(hasattr(home, '_recovery_dialog'))
        home._recovery_received({'accion': 'notificaciones', 'ids': ['solicitud'], 'pendientes': 1})
        self.assertEqual(home.nav_buttons['usuarios'].notification_count, 1)
        self.assertIn('1', usuarios.tabs.tabText(1))
        home._set_sidebar_collapsed(True)
        self.assertEqual(home.nav_buttons['usuarios'].notification_count, 1)
        self.assertIn('1', home.nav_buttons['usuarios'].toolTip())
        home._recovery_received({'accion': 'notificaciones', 'ids': [], 'pendientes': 0})
        self.assertEqual(home.nav_buttons['usuarios'].notification_count, 0)
        self.assertIn('0', usuarios.tabs.tabText(1))
        trabajador = self.home('trabajador')
        self.assertIsNone(trabajador.recovery_controller)
        self.assertNotIn('usuarios', trabajador.page_views)

    def test_navegacion_usuarios_conserva_la_pestana_de_solicitudes(self):
        home = self.home()
        usuarios = home.page_views['usuarios'].page
        usuarios.tabs.setCurrentIndex(1)
        controller = usuarios.solicitudes.controller
        controller.ejecutar.assert_called_with('listar')
        controller.ejecutar.reset_mock()
        home.nav_buttons['ventas'].click()
        home.nav_buttons['usuarios'].click()
        self.assertEqual(usuarios.tabs.currentIndex(), 1)
        controller.ejecutar.assert_called_once_with('listar')

    def test_bandeja_visible_se_refresca_aunque_no_cambie_el_contador(self):
        home = self.home()
        home.nav_buttons['usuarios'].click()
        usuarios = home.page_views['usuarios'].page
        usuarios.tabs.setCurrentIndex(1)
        controller = usuarios.solicitudes.controller
        controller.ejecutar.reset_mock()
        notificacion = {'accion': 'notificaciones', 'ids': ['solicitud-1', 'solicitud-2'], 'pendientes': 2}
        with patch.object(home, 'isVisible', return_value=True):
            home._recovery_received(notificacion)
            home._recovery_received(notificacion)
        self.assertEqual(controller.ejecutar.call_count, 2)
        controller.ejecutar.assert_called_with('listar')
        self.assertEqual(home.nav_buttons['usuarios'].notification_count, 2)

    def test_solicitudes_y_confirmaciones_con_clics_reales_dentro_de_home(self):
        home = self.home()
        home.resize(1280, 800)
        home.show()
        home.nav_buttons['usuarios'].click()
        usuarios = home.page_views['usuarios'].page
        self.assertIsNone(usuarios.graphicsProxyWidget())
        usuarios.tabs.setCurrentIndex(1)
        bandeja = usuarios.solicitudes
        base = dict(id_usuario=2, usuario='Andrea', canal='correo', destino='a***@example.com',
                    estado='pendiente', solicitado_en=datetime.now(timezone.utc))
        solicitudes = [dict(base, id_solicitud='andrea-1'), dict(base, id_solicitud='andrea-2'),
                       dict(base, id_solicitud='margarita-1', id_usuario=3, usuario='Margarita',
                            destino='Sin correo registrado', correo_pendiente=True)]
        bandeja._recibir({'accion': 'listar', 'solicitudes': solicitudes})
        self.app.processEvents()
        self.assertEqual(bandeja.tabla.rowCount(), 3)
        controller = bandeja.controller
        controller.ejecutar.reset_mock()
        for fila, solicitud in enumerate(solicitudes):
            rect = bandeja.tabla.visualItemRect(bandeja.tabla.item(fila, 0))
            self.assertTrue(bandeja.tabla.viewport().rect().contains(rect.center()))
            QTest.mouseClick(bandeja.tabla.viewport(), Qt.LeftButton, pos=rect.center())
            self.assertEqual(bandeja._seleccion()['id_solicitud'], solicitud['id_solicitud'])
        self.assertFalse(bandeja.aprobar.isEnabled())
        self.assertTrue(bandeja.rechazar.isEnabled())
        QTest.mouseClick(bandeja.rechazar, Qt.LeftButton)
        self.app.processEvents()
        dialogo = bandeja._confirmacion
        self.assertIsNotNone(dialogo)
        self.assertIsNone(dialogo.graphicsProxyWidget())
        self.assertTrue(dialogo.isVisible())
        QTest.mouseClick(dialogo.cancelar, Qt.LeftButton)
        self.assertIsNone(bandeja._confirmacion)
        controller.ejecutar.assert_not_called()
        bandeja.tabla.selectRow(1)
        QTest.mouseClick(bandeja.aprobar, Qt.LeftButton)
        self.app.processEvents()
        self.assertTrue(bandeja._confirmacion.close())
        self.assertIsNone(bandeja._confirmacion)
        controller.ejecutar.assert_not_called()
        QTest.mouseClick(bandeja.aprobar, Qt.LeftButton)
        QTest.mouseClick(bandeja._confirmacion.confirmar, Qt.LeftButton)
        controller.ejecutar.assert_called_once_with('aprobar', id_solicitud='andrea-2')

    def test_todas_las_filas_son_legibles_sin_seleccionarlas_con_tema_oscuro_del_sistema(self):
        original = QPalette(self.app.palette())
        self.addCleanup(self.app.setPalette, original)
        oscuro = QPalette(original)
        for grupo in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            for rol in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
                oscuro.setColor(grupo, rol, QColor('#ffffff'))
            for rol in (QPalette.Base, QPalette.Window, QPalette.Button):
                oscuro.setColor(grupo, rol, QColor('#202225'))
        self.app.setPalette(oscuro)
        home = self.home()
        home.resize(1280, 800)
        home.show()
        home.nav_buttons['usuarios'].click()
        usuarios = home.page_views['usuarios'].page
        usuarios.tabs.setCurrentIndex(1)
        bandeja = usuarios.solicitudes
        base = dict(id_usuario=2, usuario='persona', canal='correo', destino='p***@example.com',
                    solicitado_en=datetime.now(timezone.utc))
        estados = ('pendiente', 'rechazada', 'rechazada', 'completada', 'expirada')
        bandeja._recibir({'accion': 'listar', 'solicitudes': [
            dict(base, id_solicitud=f'solicitud-{i}', estado=estado) for i, estado in enumerate(estados)
        ]})
        self.app.processEvents()
        tabla = bandeja.tabla
        self.assertEqual(tabla.rowCount(), 5)
        for grupo in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            self.assertEqual(tabla.palette().color(grupo, QPalette.Text).name(), DASHBOARD_PALETTE['ink'])
        # Verifica el texto pintado, no solo que haya registros en el modelo.
        imagen = tabla.viewport().grab().toImage()
        for fila in range(1, 5):
            with self.subTest(fila=fila):
                celda = tabla.item(fila, 0)
                self.assertFalse(celda.isSelected())
                rect = tabla.visualItemRect(celda).adjusted(5, 5, -5, -5)
                pixeles_texto = sum(
                    1 for y in range(rect.top(), rect.bottom() + 1)
                    for x in range(rect.left(), rect.right() + 1)
                    if max(imagen.pixelColor(x, y).getRgb()[:3]) < 120
                )
                self.assertGreater(pixeles_texto, 10, 'La fila sin seleccionar debe pintar texto oscuro legible.')

    def test_eliminar_usuario_con_confirmacion_real_dentro_de_home(self):
        home = self.home()
        home.resize(1280, 800)
        home.show()
        home.nav_buttons['usuarios'].click()
        usuarios = home.page_views['usuarios'].page
        usuarios._recibir({'accion': 'listar', 'usuarios': [dict(
            id_usuario=2, usuario='persona_prueba', rol='trabajador', activo=True,
            ultimo_acceso=None, fecha_creacion=datetime.now(timezone.utc))]})
        self.app.processEvents()
        usuarios.scroll.ensureWidgetVisible(usuarios.eliminar)
        controller = usuarios.controller
        controller.ejecutar.reset_mock()
        QTest.mouseClick(usuarios.eliminar, Qt.LeftButton)
        self.app.processEvents()
        dialogo = usuarios._confirmacion
        self.assertIsNotNone(dialogo)
        self.assertIsNone(dialogo.graphicsProxyWidget())
        self.assertTrue(dialogo.close())
        controller.ejecutar.assert_not_called()
        QTest.mouseClick(usuarios.eliminar, Qt.LeftButton)
        QTest.mouseClick(usuarios._confirmacion.confirmar, Qt.LeftButton)
        controller.ejecutar.assert_called_once_with('eliminar', id_usuario=2)

    def test_usuarios_solo_aparece_para_administrador_y_al_final(self):
        home = self.home()
        self.assertEqual(list(home.nav_buttons)[-1], 'usuarios')
        self.assertIn('usuarios', home.page_views)
        view = home.page_views['usuarios'].page
        view.controller.ejecutar.assert_not_called()
        home.nav_buttons['usuarios'].click()
        view.controller.ejecutar.assert_called_once_with('listar', buscar='', rol=None, activo=None)
        for rol in ('gerente', 'trabajador'):
            home = self.home(rol)
            self.assertNotIn('usuarios', home.nav_buttons)
            self.assertNotIn('usuarios', home.page_views)
            with self.assertRaises(PermissionError):
                home._show_page('usuarios')

    def test_marca_zeyver_es_unica_en_todos_los_modulos(self):
        home = self.home()
        for key in ('dashboard', 'usuarios', 'ventas'):
            with self.subTest(key=key):
                home.nav_buttons[key].click()
                self.assertTrue(home.zeyver_active)
                self.assertTrue(home.dashboard_active)
                self.assertIn(DASHBOARD_SHELL_STYLES, home.styleSheet())
                self.assertIn('Zeyver', home.windowTitle())
                self.assertIsInstance(home.page_views['usuarios'], NativePageView)
                self.assertIsNone(home.page_views['usuarios'].page.graphicsProxyWidget())
                for button in (*home.nav_buttons.values(), home.intelligence_button, home.logout_button):
                    self.assertTrue(button.dashboard_theme)
                self.assertTrue(home.brand.isHidden())
                self.assertFalse(home.dashboard_brand.isHidden())
                self.assertTrue(home.compact_logo.isHidden())
                home._set_sidebar_collapsed(True)
                self.assertFalse(home.dashboard_compact_logo.isHidden())
                home._set_sidebar_collapsed(False)
        self.assertEqual(home.styleSheet(), home._styles())


if __name__ == '__main__':
    unittest.main()
