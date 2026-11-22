import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtGui import QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QTableWidget

from models.sesion_usuario import SesionUsuario
from views.core_inventory_views import (
    DashboardView, Donut, IconBadge, LineIcon, ProductsView, SalesChart, SalesView, STYLES,
)
from views.dashboard_theme import (
    DASHBOARD_PALETTE, DASHBOARD_SHELL_STYLES, DASHBOARD_STYLES, LOGO_PATH, ZeyverLogo,
)
from views.home_view import HomeView, NavButton
from views.ui_components import BrandWidget


class DashboardUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # The Windows offscreen platform does not discover installed fonts.
        for name in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf', 'seguisym.ttf', 'seguiemj.ttf'):
            path = Path('C:/Windows/Fonts') / name
            if path.is_file():
                QFontDatabase.addApplicationFont(str(path))

    def setUp(self):
        self.sesion = SesionUsuario(1, 'Usuario Prueba', 'administrador')

    def vista(self, view_class):
        view = view_class(self.sesion)
        self.addCleanup(view.deleteLater)
        self.addCleanup(view.close)
        return view

    def home(self):
        # Exercise navigation without constructing unrelated data controllers.
        items = tuple(item for item in HomeView.PAGE_ITEMS if item[1] in ('dashboard', 'productos', 'ventas'))
        with patch.object(HomeView, 'PAGE_ITEMS', items), \
                patch.object(HomeView, 'INTELLIGENCE_ITEMS', ()), \
                patch.object(HomeView, 'DECISION_ITEMS', ()), \
                patch.object(HomeView, 'ADMIN_ITEMS', ()), \
                patch('views.home_view.RecuperacionController'):
            return self.vista(HomeView)

    def test_dashboard_usa_paleta_zeyver_en_estilos_y_graficos(self):
        view = self.vista(DashboardView)
        self.assertEqual(view.styleSheet(), DASHBOARD_STYLES)
        self.assertEqual(view.findChild(SalesChart).colors, DASHBOARD_PALETTE)
        self.assertEqual(view.findChild(Donut).colors, DASHBOARD_PALETTE['categories'])
        for icon in view.findChildren(LineIcon):
            self.assertEqual(icon.colors, DASHBOARD_PALETTE)
        for icon in view.findChildren(IconBadge):
            self.assertNotEqual(icon.color.name(), '#5133f5')

    def test_ventas_e_inventario_conservan_estilos_originales(self):
        for view_class in (SalesView, ProductsView):
            view = self.vista(view_class)
            self.assertEqual(view.styleSheet(), STYLES)
            self.assertEqual(view.theme, {})
        chart = SalesChart()
        donut = Donut()
        self.addCleanup(chart.deleteLater)
        self.addCleanup(donut.deleteLater)
        self.assertEqual(chart.colors, {})
        self.assertEqual(donut.colors[0], '#5133f5')

    def test_barras_menores_suaves_y_maximo_en_naranja(self):
        chart = SalesChart(palette=DASHBOARD_PALETTE)
        self.addCleanup(chart.deleteLater)
        chart.resize(540, 240)
        self.assertEqual(chart._bar_color(min(chart.values)).name(), '#fdc39c')
        self.assertEqual(chart._bar_color(max(chart.values)).name(), '#ff4f12')
        colors = [chart._bar_color(value) for value in sorted(set(chart.values))]
        self.assertEqual([c.green() for c in colors], sorted((c.green() for c in colors), reverse=True))
        image = chart.grab().toImage()
        area = chart.rect().adjusted(45, 26, -18, -28)
        slot = area.width() / 12
        for index, value in enumerate(chart.values):
            x = int(area.left() + slot * (index + 0.5))
            self.assertEqual(image.pixelColor(x, area.bottom() - 10), chart._bar_color(value))

    def test_barras_con_ventas_iguales_no_dividen_por_cero(self):
        chart = SalesChart(palette=DASHBOARD_PALETTE)
        self.addCleanup(chart.deleteLater)
        chart.values = [10] * 12
        self.assertEqual(chart._bar_color(10).name(), '#ff4f12')
        chart.values = [0] * 12
        self.assertEqual(chart._bar_color(0).name(), '#fdc39c')

    def test_stock_critico_mantiene_alerta_roja(self):
        view = self.vista(DashboardView)
        self.assertEqual(view.findChild(QLabel, 'badChip').text(), '↑ 33%')
        table = view.findChild(QTableWidget)
        self.assertEqual(table.item(0, 2).foreground().color().name(), '#b63738')
        self.assertEqual(table.item(0, 2).background().color().name(), '#fff0f0')
        self.assertEqual(table.item(1, 2).foreground().color().name(), '#a85a12')
        self.assertTrue(table.alternatingRowColors())

    def test_blancos_y_plomos_contrastan_en_tarjetas_y_tabla(self):
        view = self.vista(DashboardView)
        view.resize(1280, 945)
        view.show()
        self.app.processEvents()
        cards = [card for card in view.findChildren(QFrame, 'card')]
        self.assertTrue(cards)
        for card in cards:
            self.assertEqual(card.palette().color(QPalette.Window).name(), '#ffffff')
        metrics = view.findChildren(QLabel, 'metricValue')
        self.assertEqual(len(metrics), 4)
        for metric in metrics:
            self.assertEqual(metric.palette().color(QPalette.WindowText).name(), '#24272b')
        sales_icon = next(icon for icon in view.findChildren(IconBadge) if icon.kind == 'bars')
        self.assertEqual(sales_icon.background.name(), '#fff0e5')
        table = view.findChild(QTableWidget)
        self.assertEqual(table.palette().color(QPalette.Base).name(), '#ffffff')
        self.assertEqual(table.palette().color(QPalette.AlternateBase).name(), '#f3f4f6')
        self.assertIn(DASHBOARD_PALETTE['graphite'], view.findChild(Donut).colors)

    def test_logo_original_disponible_en_ambos_formatos(self):
        self.assertTrue(LOGO_PATH.is_absolute())
        self.assertTrue(LOGO_PATH.is_file())
        for compact in (False, True):
            logo = ZeyverLogo(compact=compact)
            self.addCleanup(logo.deleteLater)
            logo.resize(28 if compact else 180, 42 if compact else 68)
            self.assertFalse(logo.pixmap.isNull())
            self.assertFalse(logo.grab().isNull())
            self.assertIn('Zeyver', logo.accessibleName())

    def test_navegacion_cambia_tema_solo_en_dashboard(self):
        home = self.home()
        self.assertTrue(home.dashboard_active)
        self.assertFalse(home.dashboard_brand.isHidden())
        self.assertTrue(home.brand.isHidden())
        self.assertIn('Zeyver', home.windowTitle())
        for key in ('ventas', 'productos', 'dashboard'):
            home.nav_buttons[key].click()
            active = key == 'dashboard'
            self.assertEqual(home.dashboard_active, active)
            self.assertEqual(home.pages.currentIndex(), home.page_indexes[key])
            self.assertEqual(home.styleSheet(), home._styles() + (DASHBOARD_SHELL_STYLES if active else ''))
            for button in (*home.nav_buttons.values(), home.intelligence_button, home.logout_button):
                self.assertEqual(button.dashboard_theme, active)
            self.assertEqual(home.dashboard_brand.isHidden(), not active)
            self.assertEqual(home.brand.isHidden(), active)
        self.assertEqual(home.page_views['dashboard'].backgroundBrush().color().name(), '#f1f2f4')
        self.assertEqual(home.page_views['ventas'].backgroundBrush().color().name(), '#f6f9fe')

    def test_logo_en_barra_contraida_y_cuenta_solo_en_cabecera(self):
        home = self.home()
        home._set_sidebar_collapsed(True)
        self.assertFalse(home.dashboard_compact_logo.isHidden())
        self.assertTrue(home.dashboard_brand.isHidden())
        self.assertTrue(home.compact_logo.isHidden())
        self.assertIsNone(home.sidebar.findChild(QLabel, 'accountName'))
        self.assertEqual(home.page_views['dashboard'].page.findChild(QLabel, 'accountName').text(), self.sesion.usuario)
        home._show_page('ventas')
        self.assertFalse(home.compact_logo.isHidden())
        self.assertTrue(home.dashboard_compact_logo.isHidden())
        home._show_page('dashboard')
        home._set_sidebar_collapsed(False)
        self.assertFalse(home.dashboard_brand.isHidden())
        self.assertIsNone(home.sidebar.findChild(QLabel, 'accountName'))
        self.assertEqual(home.page_views['dashboard'].page.findChild(QLabel, 'accountName').text(), self.sesion.usuario)

    def test_indicador_activo_degrada_de_naranja_a_amarillo_horizontalmente(self):
        button = NavButton('Dashboard', 'home')
        self.addCleanup(button.deleteLater)
        button.dashboard_theme = True
        button.setChecked(True)
        for compact, width in ((False, 218), (True, 60)):
            button.set_compact(compact)
            button.resize(width, 38)
            image = button.grab().toImage()
            left = image.pixelColor(5, 19)
            right = image.pixelColor(width - 6, 19)
            self.assertGreater(left.red(), 245)
            self.assertGreater(right.red(), 245)
            self.assertGreater(right.green() - left.green(), 70)
            self.assertGreater(right.blue(), left.blue())
            # Orange dominates; yellow is reserved for the rightmost edge.
            self.assertLess(image.pixelColor(int(width * 0.65), 5).green(), 115)
            self.assertLess(image.pixelColor(int(width * 0.8), 5).green(), 140)
            # Each column keeps its color from top to bottom.
            self.assertEqual(image.pixelColor(width - 11, 5), image.pixelColor(width - 11, 32))
        button.dashboard_theme = False
        image = button.grab().toImage()
        self.assertEqual(image.pixelColor(44, 5).name(), '#5527f5')

    def test_dashboard_renderiza_en_pantalla_grande_y_pequena(self):
        home = self.home()
        home.show()
        for width, height, compact in ((1680, 945, False), (1120, 700, True)):
            home.resize(width, height)
            home._set_sidebar_collapsed(compact)
            self.app.processEvents()
            self.assertFalse(home.grab().isNull())
            self.assertEqual(home.sidebar.width(), 84 if compact else 242)
            page = home.page_views['dashboard'].page
            self.assertLessEqual(page.content.width(), page.width())

    def test_marca_compartida_no_cambia_en_login(self):
        brand = BrandWidget()
        self.addCleanup(brand.deleteLater)
        self.assertIn('FLAMAR', [label.text() for label in brand.findChildren(QLabel)])


if __name__ == '__main__':
    unittest.main()
