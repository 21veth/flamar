from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from views.ui_components import BarChart, BrandWidget, DonutChart, LineChart
from views.analytics_views import PredictionsView, PurchasePatternsView
from views.customer_views import ConsumersView, SegmentationView
from views.data_views import ImportDataView, PreprocessingView
from views.decision_views import RecommendationsView, ReportsView


class HomeView(QWidget):
    logout_requested = Signal()

    NAV_ITEMS = (
        ('▦', 'Dashboard', 'dashboard'),
        ('⇧', 'Importar datos', 'importar'),
        ('◉', 'Consumidores', 'consumidores'),
        ('⌘', 'Preprocesamiento', 'preprocesamiento'),
        ('◌', 'Segmentación', 'segmentacion'),
        ('⌁', 'Patrones de compra', 'patrones'),
        ('↗', 'Predicciones', 'predicciones'),
        ('☆', 'Recomendaciones', 'recomendaciones'),
        ('▤', 'Reportes', 'reportes'),
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics - Dashboard')
        self.setMinimumSize(1120, 700)
        self.resize(1440, 840)
        self.setStyleSheet(self._styles())

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        for page in (
            self._build_dashboard(),
            ImportDataView(),
            ConsumersView(),
            PreprocessingView(),
            SegmentationView(),
            PurchasePatternsView(),
            PredictionsView(),
            RecommendationsView(),
            ReportsView(),
        ):
            self.pages.addWidget(page)
        root.addWidget(self.pages, 1)

    def _build_sidebar(self):
        sidebar = QFrame(objectName='sidebar')
        sidebar.setFixedWidth(218)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(4)
        layout.addWidget(BrandWidget())
        layout.addSpacing(13)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        section_labels = {0: None, 1: 'DATOS', 4: 'ANÁLISIS', 7: 'DECISIONES'}
        for index, (icon, text, key) in enumerate(self.NAV_ITEMS):
            if section_labels.get(index):
                section = QLabel(section_labels[index], objectName='nav_section')
                layout.addSpacing(10)
                layout.addWidget(section)
            button = QPushButton(f'{icon}   {text}', objectName='nav_button')
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=index: self.pages.setCurrentIndex(page))
            self.nav_group.addButton(button, index)
            self.nav_buttons[key] = button
            layout.addWidget(button)
        self.nav_buttons['dashboard'].setChecked(True)

        layout.addStretch()
        logout_button = QPushButton('↪   Cerrar sesión', objectName='logout_button')
        logout_button.setCursor(Qt.PointingHandCursor)
        logout_button.clicked.connect(self.logout_requested.emit)
        layout.addWidget(logout_button)
        separator = QFrame(objectName='sidebar_line')
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        account = QHBoxLayout()
        avatar = QLabel('AA', objectName='avatar')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(38, 38)
        account.addWidget(avatar)
        account_text = QVBoxLayout()
        account_text.setSpacing(0)
        account_text.addWidget(QLabel('Administrador', objectName='account_name'))
        account_text.addWidget(QLabel('Sesión activa', objectName='account_role'))
        account.addLayout(account_text)
        layout.addLayout(account)
        return sidebar

    def _build_dashboard(self):
        page = QWidget(objectName='workspace')
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget(objectName='workspace')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(14)

        layout.addLayout(self._header('Dashboard', 'Hola, Administrador', 'Bienvenido de vuelta. Aquí tienes un resumen de tu negocio.'))

        metrics = QGridLayout()
        metrics.setSpacing(12)
        data = (
            ('♙', '25,430', 'Consumidores analizados', '↑ 14.8%', '#5b43f4', '#f0edff'),
            ('▾', '18,720', 'Compras registradas', '↑ 12.6%', '#1479ed', '#eaf4ff'),
            ('✦', '1,240', 'Clientes frecuentes', '↑ 9.3%', '#08a66c', '#e8f8f2'),
            ('%', '2x1', 'Promoción con mejor rendimiento', '↑ 21.7%', '#ff7417', '#fff2e7'),
        )
        for column, metric in enumerate(data):
            metrics.addWidget(self._metric_card(*metric), 0, column)
            metrics.setColumnStretch(column, 1)
        layout.addLayout(metrics)

        charts = QGridLayout()
        charts.setSpacing(12)
        charts.addWidget(self._chart_card('Ventas por mes', BarChart(
            [17, 19, 24, 22, 31, 32, 34, 35, 30, 26, 22, 16],
            ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
        )), 0, 0)
        charts.addWidget(self._chart_card('Categorías más compradas', DonutChart(
            [36, 24, 18, 14, 8], ['Ropa', 'Tecnología', 'Calzado', 'Comida', 'Accesorios'],
        )), 0, 1)
        charts.addWidget(self._chart_card('Distribución por segmento', DonutChart(
            [36, 28, 22, 10, 4], ['Frecuentes', 'Ocasionales', 'En riesgo', 'Nuevos', 'Inactivos'],
        )), 1, 0)
        charts.addWidget(self._chart_card('Horarios con más compras', LineChart(
            [160, 150, 230, 250, 380, 620, 820, 660, 380, 320, 470, 690, 510, 270],
            ['0h', '2h', '4h', '6h', '8h', '10h', '12h', '14h', '16h', '18h', '20h', '22h', '24h', ''],
        )), 1, 1)
        charts.setColumnStretch(0, 1)
        charts.setColumnStretch(1, 1)
        layout.addLayout(charts)

        findings = QFrame(objectName='card')
        findings_layout = QVBoxLayout(findings)
        findings_layout.setContentsMargins(18, 14, 18, 15)
        findings_layout.addWidget(QLabel('Hallazgos recientes', objectName='card_title'))
        row = QHBoxLayout()
        for icon, copy in (
            ('↗', 'Las compras aumentaron <b>14.8%</b><br>frente al período anterior.'),
            ('▢', 'La categoría <b>Ropa</b> lidera<br>las compras con <b>36%</b>.'),
            ('♙', 'Los clientes frecuentes generan<br><b>62%</b> del ingreso total.'),
        ):
            item = QFrame(objectName='finding')
            item_layout = QHBoxLayout(item)
            badge = QLabel(icon, objectName='finding_icon')
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(40, 40)
            item_layout.addWidget(badge)
            label = QLabel(copy, objectName='finding_copy')
            item_layout.addWidget(label, 1)
            row.addWidget(item)
        findings_layout.addLayout(row)
        layout.addWidget(findings)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page

    def _header(self, title, greeting=None, subtitle=None):
        wrapper = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(QLabel(title, objectName='page_title'))
        top.addStretch()
        search = QLabel('⌕   Buscar...', objectName='search')
        search.setFixedWidth(220)
        top.addWidget(search)
        top.addWidget(QLabel('♢', objectName='notification'))
        top.addWidget(QLabel('AA', objectName='top_avatar'))
        admin = QVBoxLayout()
        admin.setSpacing(0)
        admin.addWidget(QLabel('Administrador', objectName='top_name'))
        admin.addWidget(QLabel('Administrador', objectName='top_role'))
        top.addLayout(admin)
        wrapper.addLayout(top)
        if greeting:
            wrapper.addSpacing(3)
            wrapper.addWidget(QLabel(greeting, objectName='greeting'))
        if subtitle:
            wrapper.addWidget(QLabel(subtitle, objectName='subtitle'))
        return wrapper

    def _metric_card(self, icon, value, label, change, color, background):
        card = QFrame(objectName='card')
        card.setMinimumHeight(106)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 15, 14, 15)
        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(52, 52)
        badge.setStyleSheet(f'background: {background}; color: {color}; border-radius: 14px; font-size: 24px; font-weight: 700;')
        layout.addWidget(badge)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(QLabel(value, objectName='metric_value'))
        metric_label = QLabel(label, objectName='metric_label')
        metric_label.setWordWrap(True)
        text.addWidget(metric_label)
        change_label = QLabel(f'{change}  <span style="color:#64748b">vs. período anterior</span>', objectName='metric_change')
        text.addWidget(change_label)
        layout.addLayout(text, 1)
        return card

    def _chart_card(self, title, chart):
        card = QFrame(objectName='card')
        card.setMinimumHeight(210)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(3)
        layout.addWidget(QLabel(title, objectName='card_title'))
        layout.addWidget(chart, 1)
        return card

    def _build_placeholder(self, title, key):
        page = QWidget(objectName='workspace')
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 30)
        subtitles = {
            'importar': 'Carga y procesa archivos para integrarlos con tus análisis.',
            'consumidores': 'Explora y analiza el comportamiento de tus consumidores.',
            'preprocesamiento': 'Revisa la calidad de tus datos antes del análisis.',
            'segmentacion': 'Descubre grupos de consumidores con comportamientos similares.',
            'patrones': 'Descubre relaciones entre productos que suelen comprarse juntos.',
            'predicciones': 'Anticipa tendencias y comportamientos futuros.',
            'recomendaciones': 'Acciones sugeridas para impulsar tus resultados.',
            'reportes': 'Crea y exporta reportes con los insights de tu negocio.',
        }
        layout.addLayout(self._header(title))
        layout.addWidget(QLabel(subtitles[key], objectName='subtitle'))
        layout.addSpacing(18)
        empty = QFrame(objectName='empty_state')
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        mark = QLabel('FL', objectName='empty_mark')
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(64, 64)
        empty_layout.addWidget(mark, alignment=Qt.AlignCenter)
        empty_layout.addWidget(QLabel(f'Vista de {title}', objectName='empty_title'), alignment=Qt.AlignCenter)
        empty_layout.addWidget(QLabel('Módulo preparado para conectar sus datos y componentes.', objectName='subtitle'), alignment=Qt.AlignCenter)
        empty_layout.addStretch()
        layout.addWidget(empty, 1)
        return page

    @staticmethod
    def _styles():
        return '''
            QWidget { color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; }
            QFrame#sidebar { background: #071b37; }
            QLabel#nav_section { color: #8292aa; font-size: 9px; font-weight: 700; padding: 5px 10px 2px; }
            QPushButton#nav_button { background: transparent; color: #d8e2f1; border: none; border-radius: 8px; padding: 9px 11px; text-align: left; font-size: 12px; }
            QPushButton#nav_button:hover { background: #122c50; color: white; }
            QPushButton#nav_button:checked { background: #543cff; color: white; font-weight: 700; }
            QPushButton#logout_button { background: transparent; color: #d8e2f1; border: none; border-radius: 8px; padding: 9px 11px; text-align: left; font-size: 12px; }
            QPushButton#logout_button:hover { background: #422044; color: #ffced3; }
            QFrame#sidebar_line { background: #203752; border: none; }
            QLabel#avatar, QLabel#top_avatar { color: white; background: #573ff3; border-radius: 19px; font-size: 11px; font-weight: 700; }
            QLabel#account_name { color: white; font-size: 11px; font-weight: 700; }
            QLabel#account_role { color: #91a3ba; font-size: 9px; }
            QWidget#workspace, QScrollArea { background: #f8faff; border: none; }
            QScrollBar:vertical { background: #f2f5fa; width: 8px; }
            QScrollBar::handle:vertical { background: #cad3e0; border-radius: 4px; min-height: 40px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLabel#page_title { color: #09142f; font-size: 23px; font-weight: 800; }
            QLabel#greeting { color: #10182c; font-size: 16px; font-weight: 700; }
            QLabel#subtitle { color: #64748b; font-size: 11px; }
            QLabel#search { color: #718096; background: white; border: 1px solid #dce3ed; border-radius: 8px; padding: 10px 12px; }
            QLabel#notification { color: #2f4264; font-size: 22px; padding: 0 8px; }
            QLabel#top_name { color: #111827; font-size: 11px; font-weight: 700; }
            QLabel#top_role { color: #64748b; font-size: 9px; }
            QFrame#card { background: white; border: 1px solid #dfe5ee; border-radius: 11px; }
            QLabel#metric_value { color: #0b1020; font-size: 22px; font-weight: 800; }
            QLabel#metric_label { color: #273654; font-size: 10px; }
            QLabel#metric_change { color: #08a66c; font-size: 9px; font-weight: 700; }
            QLabel#card_title { color: #111827; font-size: 13px; font-weight: 750; }
            QFrame#finding { border: none; border-right: 1px solid #e5e9f0; }
            QLabel#finding_icon { color: #553cff; background: #f0edff; border-radius: 20px; font-size: 18px; font-weight: 700; }
            QLabel#finding_copy { color: #344258; font-size: 10px; }
            QFrame#empty_state { background: white; border: 1px solid #dfe5ee; border-radius: 12px; }
            QLabel#empty_mark { color: white; background: #553cff; border-radius: 32px; font-size: 20px; font-weight: 800; }
            QLabel#empty_title { color: #0b1739; font-size: 18px; font-weight: 750; }
        '''
