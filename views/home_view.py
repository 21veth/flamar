from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QGridLayout, QProgressBar,
)
from PySide6.QtCore import Qt


class HomeView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics - Inicio')
        self.setMinimumSize(1020, 640)
        self.setStyleSheet('''
            QWidget { color: #172b4d; font-family: "Segoe UI Variable", "Segoe UI"; }
            QWidget#workspace { background: #f5f8fc; }
            QFrame#sidebar { background: #102a43; }
            QLabel#brand_mark { color: #102a43; background: #57d3c7; border-radius: 16px; font-size: 19px; font-weight: 800; }
            QLabel#brand_title { color: #ffffff; font-size: 18px; font-weight: 700; }
            QLabel#brand_caption { color: #91abc2; font-size: 11px; }
            QPushButton#nav_button { background: transparent; color: #b8cad9; border: none; border-radius: 8px; padding: 12px 14px; font-size: 14px; font-weight: 600; text-align: left; }
            QPushButton#nav_button:hover { background: #1c3b59; color: #ffffff; }
            QPushButton#nav_button:checked { background: #57d3c7; color: #102a43; font-weight: 700; }
            QLabel#page_title { color: #102a43; font-size: 27px; font-weight: 750; }
            QLabel#page_subtitle { color: #71869c; font-size: 13px; }
            QFrame#hero { background: #173f5f; border-radius: 16px; }
            QLabel#hero_title { color: #ffffff; font-size: 21px; font-weight: 700; }
            QLabel#hero_copy { color: #c8dce9; font-size: 12px; }
            QLabel#hero_metric { color: #57d3c7; font-size: 28px; font-weight: 750; }
            QFrame#metric_card, QFrame#panel, QFrame#section { background: #ffffff; border: 1px solid #e3ebf3; border-radius: 13px; }
            QLabel#metric_label, QLabel#panel_caption { color: #8295a8; font-size: 11px; font-weight: 600; }
            QLabel#metric_value { color: #173f5f; font-size: 22px; font-weight: 750; }
            QLabel#metric_change { color: #2a9d8f; font-size: 11px; font-weight: 700; }
            QLabel#panel_title { color: #173f5f; font-size: 15px; font-weight: 700; }
            QLabel#activity_title { color: #27445e; font-size: 12px; font-weight: 600; }
            QLabel#activity_meta { color: #8a9bad; font-size: 10px; }
            QLabel#dot { color: #f26b5b; font-size: 18px; font-weight: 700; }
            QPushButton#action_button { background: #f26b5b; color: #ffffff; border: none; border-radius: 8px; padding: 10px 16px; font-size: 12px; font-weight: 700; }
            QPushButton#action_button:hover { background: #d9554c; }
            QProgressBar#health_bar { background: #eaf0f5; border: none; border-radius: 4px; height: 8px; }
            QProgressBar#health_bar::chunk { background: #57d3c7; border-radius: 4px; }
        ''')

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.sidebar = QFrame(objectName='sidebar')
        self.sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(22, 26, 22, 24)
        sidebar_layout.setSpacing(7)

        brand_row = QHBoxLayout()
        brand_mark = QLabel('F', objectName='brand_mark')
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_mark.setFixedSize(34, 34)
        brand_row.addWidget(brand_mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_text.addWidget(QLabel('FLAMAR', objectName='brand_title'))
        brand_text.addWidget(QLabel('Analytics suite', objectName='brand_caption'))
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(34)
        sidebar_layout.addWidget(QLabel('ESPACIO DE TRABAJO', objectName='brand_caption'))
        sidebar_layout.addSpacing(6)

        self.nav_buttons = {}
        sections = [
            ('▦   Panel general', 'inicio'), ('◌   Segmentación', 'segmentacion'),
            ('↗   Predicciones', 'prediccion'), ('⇩   Importaciones', 'importacion'),
            ('⚙   Configuración', 'configuracion'),
        ]
        for label, key in sections:
            btn = QPushButton(label)
            btn.setObjectName('nav_button')
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, k=key: self.on_nav_toggled(checked, k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(QLabel('Sesión activa', objectName='brand_caption'))
        sidebar_layout.addWidget(QLabel('●  Administrador', objectName='brand_caption'))

        self.content = QWidget(objectName='workspace')
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(38, 30, 38, 30)
        content_layout.setSpacing(18)
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        header_text.addWidget(QLabel('Buenos días, equipo', objectName='page_title'))
        header_text.addWidget(QLabel('Aquí tienes una lectura clara de lo que ocurre en tu negocio.', objectName='page_subtitle'))
        header.addLayout(header_text)
        header.addStretch()
        header.addWidget(QLabel('●  Datos actualizados', objectName='metric_change'), alignment=Qt.AlignTop)
        content_layout.addLayout(header)

        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(0)
        self.home_section = QFrame(objectName='section')
        self.home_layout = QVBoxLayout(self.home_section)
        self.home_layout.setContentsMargins(22, 22, 22, 22)
        self.home_layout.setSpacing(16)
        self._build_home_content()
        self.seg_section = self._placeholder_section('Segmentación de consumidores')
        self.pred_section = self._placeholder_section('Predicciones')
        self.imp_section = self._placeholder_section('Importaciones')
        self.cfg_section = self._placeholder_section('Configuración')
        for section in (self.home_section, self.seg_section, self.pred_section, self.imp_section, self.cfg_section):
            self.stack_layout.addWidget(section)
        content_layout.addWidget(self.stack)
        content_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content, 1)
        self.on_nav_toggled(True, 'inicio')

    def _build_home_content(self):
        hero = QFrame(objectName='hero')
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_text = QVBoxLayout()
        hero_text.setSpacing(5)
        hero_text.addWidget(QLabel('Tu negocio, en perspectiva.', objectName='hero_title'))
        hero_text.addWidget(QLabel('Detecta patrones, entiende a tus clientes y decide con confianza.', objectName='hero_copy'))
        hero_text.addSpacing(7)
        explore_btn = QPushButton('Explorar insights  →', objectName='action_button')
        explore_btn.setFixedWidth(142)
        explore_btn.clicked.connect(lambda: self.nav_buttons['segmentacion'].click())
        hero_text.addWidget(explore_btn, alignment=Qt.AlignLeft)
        hero_layout.addLayout(hero_text, 3)
        hero_metric_box = QVBoxLayout()
        hero_metric_box.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hero_metric_box.addWidget(QLabel('SALUD DEL ANÁLISIS', objectName='brand_caption'), alignment=Qt.AlignRight)
        hero_metric_box.addWidget(QLabel('92%', objectName='hero_metric'), alignment=Qt.AlignRight)
        hero_metric_box.addWidget(QLabel('Excelente esta semana', objectName='hero_copy'), alignment=Qt.AlignRight)
        hero_layout.addLayout(hero_metric_box, 1)
        self.home_layout.addWidget(hero)

        metrics = QGridLayout()
        metrics.setSpacing(12)
        metric_data = [
            ('Clientes analizados', '12,480', '+8.4%  vs. mes anterior'),
            ('Segmentos activos', '24', '+3 nuevos segmentos'),
            ('Precisión predictiva', '87.6%', '+4.2%  mejora continua'),
        ]
        for index, (label, value, change) in enumerate(metric_data):
            card = QFrame(objectName='metric_card')
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(5)
            card_layout.addWidget(QLabel(label.upper(), objectName='metric_label'))
            card_layout.addWidget(QLabel(value, objectName='metric_value'))
            card_layout.addWidget(QLabel(change, objectName='metric_change'))
            metrics.addWidget(card, 0, index)
        self.home_layout.addLayout(metrics)

        lower_grid = QGridLayout()
        lower_grid.setSpacing(12)
        activity = QFrame(objectName='panel')
        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(18, 16, 18, 15)
        activity_layout.setSpacing(10)
        activity_layout.addWidget(QLabel('Actividad reciente', objectName='panel_title'))
        activity_layout.addWidget(QLabel('MOVIMIENTOS DEL ESPACIO DE TRABAJO', objectName='panel_caption'))
        for title, meta in [('Segmento “Clientes fieles” actualizado', 'Hace 12 minutos'), ('Nueva predicción mensual disponible', 'Hace 1 hora'), ('Importación de ventas completada', 'Ayer, 18:42')]:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(QLabel('•', objectName='dot'))
            text = QVBoxLayout()
            text.setSpacing(1)
            text.addWidget(QLabel(title, objectName='activity_title'))
            text.addWidget(QLabel(meta, objectName='activity_meta'))
            row.addLayout(text)
            row.addStretch()
            activity_layout.addLayout(row)
        lower_grid.addWidget(activity, 0, 0)

        health = QFrame(objectName='panel')
        health_layout = QVBoxLayout(health)
        health_layout.setContentsMargins(18, 16, 18, 15)
        health_layout.setSpacing(9)
        health_layout.addWidget(QLabel('Calidad de datos', objectName='panel_title'))
        health_layout.addWidget(QLabel('Tu base está lista para generar insights.', objectName='panel_caption'))
        health_layout.addSpacing(4)
        health_layout.addWidget(QLabel('Completitud  ·  96%', objectName='activity_title'))
        progress = QProgressBar(objectName='health_bar')
        progress.setRange(0, 100)
        progress.setValue(96)
        progress.setTextVisible(False)
        health_layout.addWidget(progress)
        health_layout.addSpacing(5)
        health_layout.addWidget(QLabel('Última revisión: hoy, 09:24', objectName='activity_meta'))
        lower_grid.addWidget(health, 0, 1)
        lower_grid.setColumnStretch(0, 3)
        lower_grid.setColumnStretch(1, 2)
        self.home_layout.addLayout(lower_grid)

    def _placeholder_section(self, title):
        section = QFrame(objectName='section')
        layout = QVBoxLayout(section)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.addStretch()
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet('color: #173f5f; font-size: 18px; font-weight: 700;')
        layout.addWidget(label)
        layout.addStretch()
        return section

    def on_nav_toggled(self, checked, section_key):
        if not checked:
            return
        for key, widget in self._sections().items():
            widget.setVisible(key == section_key)
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == section_key)

    def _sections(self):
        return {
            'inicio': self.home_section,
            'segmentacion': self.seg_section,
            'prediccion': self.pred_section,
            'importacion': self.imp_section,
            'configuracion': self.cfg_section,
        }