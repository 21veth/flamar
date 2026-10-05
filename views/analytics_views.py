from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


INK = '#0b1739'
MUTED = '#64748b'
PURPLE = '#553cff'
GREEN = '#08a66c'
ORANGE = '#f57c00'
RED = '#ef4444'


PATTERN_ROWS = (
    ('Pan blanco', 'Mantequilla', '1,248', '4.32%', '68.7%', 'Alto', 'Alimentos'),
    ('Café molido', 'Azúcar', '1,105', '3.82%', '64.1%', 'Alto', 'Bebidas'),
    ('Leche entera', 'Cereal', '987', '3.41%', '61.3%', 'Alto', 'Alimentos'),
    ('Jabón líquido', 'Esponja', '782', '2.70%', '58.2%', 'Medio', 'Limpieza'),
    ('Pasta dental', 'Cepillo dental', '761', '2.63%', '72.4%', 'Alto', 'Higiene personal'),
    ('Arroz', 'Frijoles', '690', '2.39%', '54.6%', 'Medio', 'Despensa'),
    ('Shampoo', 'Acondicionador', '642', '2.22%', '66.8%', 'Alto', 'Higiene personal'),
    ('Detergente', 'Suavizante', '598', '2.07%', '57.9%', 'Medio', 'Limpieza'),
    ('Atún en lata', 'Mayonesa', '512', '1.77%', '53.1%', 'Medio', 'Despensa'),
    ('Galletas', 'Leche entera', '467', '1.62%', '49.8%', 'Bajo', 'Alimentos'),
)


def _label(text, name=None, word_wrap=False):
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(word_wrap)
    return label


def _card():
    return QFrame(objectName='analyticsCard')


def _configure_table(table):
    table.setAlternatingRowColors(False)
    table.setShowGrid(False)
    table.setFocusPolicy(Qt.NoFocus)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.verticalHeader().hide()
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


class RelationshipGraph(QWidget):
    """Small painter-based product relationship graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.strength = 'Alta'
        self.selected_pair = ('Pan blanco', 'Mantequilla')

    def set_strength(self, strength):
        self.strength = strength
        self.update()

    def set_selected_pair(self, first, second):
        self.selected_pair = (first, second)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = self.rect().adjusted(18, 12, -18, -36)
        nodes = {
            'Pan blanco': (.29, .35, '#5943ed', 27),
            'Mantequilla': (.29, .08, '#7655ed', 13),
            'Mermelada': (.10, .24, '#9b83ee', 13),
            'Galletas': (.32, .62, '#718ee8', 12),
            'Leche entera': (.50, .39, '#55b864', 27),
            'Cereal': (.59, .13, '#71c878', 14),
            'Café molido': (.70, .43, '#3573df', 27),
            'Azúcar': (.87, .35, '#5a88e6', 13),
            'Shampoo': (.75, .70, '#50bfd9', 12),
            'Arroz': (.55, .75, '#ea5961', 18),
            'Pasta dental': (.48, .95, '#ee8090', 12),
            'Aceite': (.66, .88, '#ed7e95', 12),
            'Jabón líquido': (.12, .65, '#f2b34d', 12),
            'Esponja': (.24, .80, '#f2cd82', 12),
            'Detergente': (.08, .89, '#70c7c2', 12),
            'Suavizante': (.21, 1.05, '#72c9c4', 12),
        }
        points = {
            name: QPointF(bounds.left() + x * bounds.width(), bounds.top() + min(y, .96) * bounds.height())
            for name, (x, y, _, _) in nodes.items()
        }
        edges = (
            ('Pan blanco', 'Mantequilla', 3), ('Pan blanco', 'Mermelada', 2),
            ('Pan blanco', 'Galletas', 2), ('Pan blanco', 'Leche entera', 3),
            ('Leche entera', 'Cereal', 2), ('Leche entera', 'Café molido', 3),
            ('Leche entera', 'Arroz', 2), ('Café molido', 'Azúcar', 2),
            ('Café molido', 'Shampoo', 1), ('Arroz', 'Pasta dental', 1),
            ('Arroz', 'Aceite', 1), ('Jabón líquido', 'Esponja', 1),
            ('Detergente', 'Suavizante', 1),
        )
        opacity = {'Alta': 1.0, 'Media': .58, 'Todas': .75}.get(self.strength, .75)
        selected = set(self.selected_pair)
        for first, second, weight in edges:
            highlight = {first, second} == selected
            color = QColor(PURPLE if highlight else '#cbd3e4')
            color.setAlphaF(1.0 if highlight else opacity)
            painter.setPen(QPen(color, weight + (1 if highlight else 0)))
            painter.drawLine(points[first], points[second])

        painter.setFont(QFont('Segoe UI', 8))
        for name, (_, _, color, radius) in nodes.items():
            point = points[name]
            active = name in selected
            painter.setPen(QPen(QColor('white'), 3 if active else 1))
            painter.setBrush(QColor(color))
            painter.drawEllipse(point, radius, radius)
            short_name = name.replace(' ', '\n', 1) if radius >= 18 else name
            if radius >= 18:
                painter.setPen(QColor('white'))
                painter.setFont(QFont('Segoe UI', 8, QFont.DemiBold))
                painter.drawText(QRectF(point.x() - radius, point.y() - radius, radius * 2, radius * 2), Qt.AlignCenter, short_name)
            else:
                painter.setPen(QColor(INK))
                painter.setFont(QFont('Segoe UI', 7))
                painter.drawText(QRectF(point.x() - 44, point.y() + radius + 3, 88, 28), Qt.AlignHCenter | Qt.AlignTop, short_name)

        painter.setPen(QColor(MUTED))
        painter.setFont(QFont('Segoe UI', 8))
        painter.drawText(QRectF(bounds.left(), self.height() - 23, bounds.width(), 18), Qt.AlignRight, 'Relación más fuerte  ━━━━━  Más débil')


class FutureTrendChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(275)
        self.chart_metric = 'Ventas proyectadas'
        self.frequency = 'Mensual'

    def set_metric(self, value):
        self.chart_metric = value
        self.update()

    def set_frequency(self, value):
        self.frequency = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(48, 24, -16, -35)
        labels = ['Ago 2025', 'Sep 2025', 'Oct 2025', 'Nov 2025', 'Dic 2025', 'Ene 2026', 'Feb 2026']
        series = {
            'Ventas proyectadas': [120, 151, 177, 196, 205, 224, 239],
            'Órdenes proyectadas': [102, 130, 146, 172, 184, 198, 218],
            'Clientes proyectados': [92, 120, 154, 165, 181, 207, 226],
        }
        values = series.get(self.chart_metric, series['Ventas proyectadas'])
        if self.frequency == 'Trimestral':
            values = [values[0], values[0], values[2], values[2], values[4], values[4], values[6]]

        painter.setFont(QFont('Segoe UI', 8))
        for index, value in enumerate((0, 50, 100, 150, 200, 250)):
            y = area.bottom() - index * area.height() / 5
            painter.setPen(QPen(QColor('#e8edf5'), 1))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(0, y - 8, 40, 16), Qt.AlignRight | Qt.AlignVCenter, '0' if value == 0 else f'{value}K')

        step = area.width() / (len(values) - 1)
        points = [QPointF(area.left() + i * step, area.bottom() - value / 250 * area.height()) for i, value in enumerate(values)]
        boundary_x = points[4].x()
        painter.setPen(QPen(QColor('#c9c6ff'), 1, Qt.DashLine))
        painter.drawLine(int(boundary_x), area.top(), int(boundary_x), area.bottom())
        painter.setPen(QColor(PURPLE))
        painter.setBrush(QColor('#f0edff'))
        painter.drawRoundedRect(QRectF(boundary_x + 8, area.top() - 14, 63, 20), 5, 5)
        painter.drawText(QRectF(boundary_x + 8, area.top() - 14, 63, 20), Qt.AlignCenter, 'Proyección')

        fill = QPainterPath(points[0])
        for point in points[1:]:
            fill.lineTo(point)
        fill.lineTo(points[-1].x(), area.bottom())
        fill.lineTo(points[0].x(), area.bottom())
        fill.closeSubpath()
        gradient = QLinearGradient(0, area.top(), 0, area.bottom())
        gradient.setColorAt(0, QColor(85, 60, 255, 55))
        gradient.setColorAt(1, QColor(85, 60, 255, 3))
        painter.fillPath(fill, gradient)

        painter.setPen(QPen(QColor(PURPLE), 2.5))
        painter.drawPolyline(points[:5])
        painter.setPen(QPen(QColor(PURPLE), 2, Qt.DashLine))
        painter.drawPolyline(points[4:])
        for point in points:
            painter.setPen(QPen(QColor(PURPLE), 2))
            painter.setBrush(QColor('white'))
            painter.drawEllipse(point, 3.5, 3.5)

        painter.setPen(QColor(MUTED))
        painter.setFont(QFont('Segoe UI', 7))
        for index, text in enumerate(labels):
            painter.drawText(QRectF(points[index].x() - 32, area.bottom() + 8, 64, 18), Qt.AlignCenter, text)


class _ScrollablePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('analyticsPage')
        self.setStyleSheet(self._styles())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setObjectName('analyticsScroll')
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.content = QWidget(objectName='analyticsContent')
        self.content.setMinimumWidth(1080)
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(26, 22, 26, 24)
        self.layout.setSpacing(16)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)

    def _page_header(self, title, subtitle):
        header = QVBoxLayout()
        header.setSpacing(3)
        header.addWidget(_label(title, 'analyticsTitle'))
        header.addWidget(_label(subtitle, 'analyticsSubtitle'))
        return header

    @staticmethod
    def _styles():
        return '''
            QWidget { color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; font-size: 11px; }
            QWidget#analyticsPage, QWidget#analyticsContent, QScrollArea#analyticsScroll { background: #f8faff; border: none; }
            QScrollBar:vertical { background: #f2f5fa; width: 8px; }
            QScrollBar::handle:vertical { background: #cad3e0; border-radius: 4px; min-height: 40px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLabel#analyticsTitle { color: #09142f; font-size: 23px; font-weight: 800; }
            QLabel#analyticsSubtitle { color: #64748b; font-size: 11px; }
            QFrame#analyticsCard { background: white; border: 1px solid #dfe5ee; border-radius: 11px; }
            QLabel#cardTitle { color: #111827; font-size: 14px; font-weight: 750; }
            QLabel#fieldTitle { color: #1f2937; font-size: 9px; font-weight: 700; }
            QLabel#muted { color: #64748b; font-size: 10px; }
            QComboBox { background: white; border: 1px solid #dce3ed; border-radius: 7px; padding: 8px 10px; min-height: 16px; color: #1f2937; }
            QComboBox:hover { border-color: #9e91ff; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView { background: white; border: 1px solid #dce3ed; selection-background-color: #eeeaff; selection-color: #3021ba; }
            QPushButton { background: white; color: #314363; border: 1px solid #d4ddea; border-radius: 7px; padding: 8px 13px; font-weight: 600; }
            QPushButton:hover { border-color: #553cff; color: #553cff; background: #faf9ff; }
            QPushButton#primaryButton { background: #553cff; color: white; border: none; padding: 9px 17px; }
            QPushButton#primaryButton:hover { background: #4630e7; color: white; }
            QTableWidget { background: white; alternate-background-color: white; border: none; gridline-color: transparent; selection-background-color: #f2f0ff; selection-color: #0b1739; }
            QTableWidget::item { border-bottom: 1px solid #e8edf4; padding: 7px; }
            QHeaderView::section { background: #f8faff; color: #17213a; border: none; border-bottom: 1px solid #dfe5ee; padding: 8px 6px; font-size: 9px; font-weight: 700; }
            QLabel#insightTitle { color: #553cff; font-size: 13px; font-weight: 750; }
            QLabel#insightIcon { color: white; background: #553cff; border-radius: 25px; font-size: 20px; font-weight: 700; }
            QLabel#kpiValue { font-size: 21px; font-weight: 800; }
            QLabel#kpiTitle { color: #314363; font-size: 10px; }
            QLabel#kpiChange { color: #08a66c; font-size: 9px; font-weight: 650; }
            QFrame#infoBanner { background: #f5f4ff; border: 1px solid #dfdcff; border-radius: 7px; }
            QLabel#infoText { color: #3e4fa3; font-size: 9px; }
        '''


class PurchasePatternsView(_ScrollablePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout.addLayout(self._page_header(
            'Patrones de compra',
            'Descubre relaciones entre productos que los clientes suelen comprar juntos.',
        ))
        self.layout.addWidget(self._build_filters())

        body = QGridLayout()
        body.setSpacing(14)
        body.addWidget(self._build_table_card(), 0, 0)
        body.addWidget(self._build_graph_card(), 0, 1)
        body.setColumnStretch(0, 10)
        body.setColumnStretch(1, 12)
        self.layout.addLayout(body)
        self.layout.addWidget(self._build_insight())
        self.layout.addStretch()
        self._populate_patterns(PATTERN_ROWS)

    def _build_filters(self):
        card = _card()
        grid = QGridLayout(card)
        grid.setContentsMargins(15, 13, 15, 13)
        grid.setHorizontalSpacing(16)
        fields = (
            ('Tienda', ('Todas las tiendas', 'Centro', 'Norte', 'En línea')),
            ('Categoría', ('Todas las categorías', 'Alimentos', 'Bebidas', 'Higiene personal', 'Limpieza', 'Despensa')),
            ('Segmento', ('Todos los segmentos', 'Clientes frecuentes', 'Clientes leales', 'Nuevos clientes')),
            ('Rango de fechas', ('01/08/2025 - 12/08/2025', 'Últimos 30 días', 'Últimos 90 días')),
        )
        self.filters = []
        for column, (title, options) in enumerate(fields):
            grid.addWidget(_label(title, 'fieldTitle'), 0, column)
            combo = QComboBox()
            combo.addItems(options)
            grid.addWidget(combo, 1, column)
            self.filters.append(combo)
            grid.setColumnStretch(column, 1)
        button = QPushButton('⌁  Aplicar filtros', objectName='primaryButton')
        button.clicked.connect(self._apply_filters)
        grid.addWidget(button, 1, 4)
        return card

    def _build_table_card(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 13, 12, 10)
        layout.setSpacing(9)
        title = QHBoxLayout()
        title.addWidget(_label('⌘  Relaciones detectadas', 'cardTitle'))
        title.addStretch()
        self.result_count = _label('', 'muted')
        title.addWidget(self.result_count)
        layout.addLayout(title)
        self.pattern_table = QTableWidget(0, 6)
        self.pattern_table.setHorizontalHeaderLabels(('Producto A', 'Producto B', 'Frecuencia', 'Soporte', 'Confianza', 'Nivel'))
        self.pattern_table.setMinimumHeight(390)
        _configure_table(self.pattern_table)
        self.pattern_table.itemSelectionChanged.connect(self._pattern_selected)
        layout.addWidget(self.pattern_table)
        return card

    def _build_graph_card(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 11)
        header = QHBoxLayout()
        header.addWidget(_label('⌘  Visualización de relaciones', 'cardTitle'))
        header.addStretch()
        self.strength_combo = QComboBox()
        self.strength_combo.addItems(('Alta', 'Media', 'Todas'))
        self.strength_combo.currentTextChanged.connect(self._graph_strength_changed)
        header.addWidget(_label('Fuerza:', 'muted'))
        header.addWidget(self.strength_combo)
        layout.addLayout(header)
        self.graph = RelationshipGraph()
        layout.addWidget(self.graph, 1)
        return card

    def _build_insight(self):
        card = QFrame(objectName='infoBanner')
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        icon = _label('✦', 'insightIcon')
        icon.setFixedSize(50, 50)
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(_label('Insight detectado', 'insightTitle'))
        self.insight_copy = _label('', word_wrap=True)
        text.addWidget(self.insight_copy)
        self.insight_detail = _label('', 'muted')
        text.addWidget(self.insight_detail)
        layout.addLayout(text, 1)
        recommend = QPushButton('↗  Ver recomendaciones')
        recommend.clicked.connect(self._show_recommendation)
        layout.addWidget(recommend)
        return card

    def _populate_patterns(self, rows):
        self.pattern_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row[:6]):
                item = QTableWidgetItem(value)
                if column >= 2:
                    item.setTextAlignment(Qt.AlignCenter)
                if column == 5:
                    colors = {'Alto': GREEN, 'Medio': '#cf8600', 'Bajo': RED}
                    item.setForeground(QColor(colors[value]))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                item.setData(Qt.UserRole, row)
                self.pattern_table.setItem(row_index, column, item)
            self.pattern_table.setRowHeight(row_index, 34)
        self.result_count.setText(f'{len(rows)} relaciones')
        if rows:
            self.pattern_table.selectRow(0)
        else:
            self.insight_copy.setText('No se encontraron relaciones para los filtros seleccionados.')
            self.insight_detail.clear()

    def _apply_filters(self):
        category = self.filters[1].currentText()
        rows = PATTERN_ROWS if category == 'Todas las categorías' else tuple(row for row in PATTERN_ROWS if row[6] == category)
        self._populate_patterns(rows)

    def _pattern_selected(self):
        row_index = self.pattern_table.currentRow()
        if row_index < 0 or not self.pattern_table.item(row_index, 0):
            return
        row = self.pattern_table.item(row_index, 0).data(Qt.UserRole)
        self.insight_copy.setText(
            f'Los clientes que compran <b>{row[0]}</b> tienen un {row[4]} de probabilidad '
            f'de también comprar <b>{row[1]}</b>.'
        )
        self.insight_detail.setText(f'Soporte: {row[3]}   •   Frecuencia conjunta: {row[2]}')
        self.graph.set_selected_pair(row[0], row[1])

    def _graph_strength_changed(self, strength):
        self.graph.set_strength(strength)
        if strength == 'Todas':
            self.filters[1].setCurrentIndex(0)

    def _show_recommendation(self):
        row = self.pattern_table.currentRow()
        if row < 0:
            return
        first = self.pattern_table.item(row, 0).text()
        second = self.pattern_table.item(row, 1).text()
        QMessageBox.information(self, 'Recomendación', f'Ubica {first} y {second} cerca y crea una promoción combinada para elevar la compra conjunta.')


class PredictionsView(_ScrollablePage):
    export_requested = Signal(str)

    SEGMENTS = (
        ('Clientes sensibles', 'Aumentará compras\ncon promociones', '78%', 'Alta', 'Aplicar promociones\nsegmentadas', '#08a66c'),
        ('Clientes leales', 'Mantendrá comportamiento\nactual', '65%', 'Media', 'Ofrecer beneficios\nexclusivos', '#f57c00'),
        ('Nuevos clientes', 'Probable repetición\nde compra', '62%', 'Media', 'Automatizar seguimiento\ny onboarding', '#08a66c'),
        ('Clientes ocasionales', 'Podría aumentar frecuencia\nde compra', '48%', 'Baja', 'Incentivar con promociones\npersonalizadas', '#f57c00'),
        ('Clientes en riesgo', 'Probable disminución\nde compras', '28%', 'Baja', 'Activar campañas\nde retención', '#ef4444'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        top = QHBoxLayout()
        top.addLayout(self._page_header(
            'Predicciones de comportamiento',
            'Anticipa tendencias y comportamientos futuros para tomar mejores decisiones.',
        ))
        top.addStretch()
        self.period_combo = QComboBox()
        self.period_combo.addItems(('01/08/2025 - 31/01/2026', 'Próximos 3 meses', 'Próximos 12 meses'))
        self.period_combo.setMinimumWidth(220)
        self.period_combo.currentTextChanged.connect(self._period_changed)
        top.addWidget(self.period_combo, alignment=Qt.AlignBottom)
        export = QPushButton('⇩  Exportar')
        export.clicked.connect(self._export)
        top.addWidget(export, alignment=Qt.AlignBottom)
        self.layout.addLayout(top)

        metrics = QGridLayout()
        metrics.setSpacing(13)
        cards = (
            ('⌘', 'Probabilidad general de\nrecompra', '72%', '↑ 6% vs. periodo anterior', PURPLE, '#f0edff'),
            ('↗', 'Segmento con mayor crecimiento', 'Clientes sensibles', '+18% crecimiento proyectado', GREEN, '#e8f8f2'),
            ('%', 'Mayor sensibilidad a\npromociones', 'Tecnología', '87% responden a promociones', ORANGE, '#fff2df'),
            ('◇', 'Categoría con mayor crecimiento\nproyectado', 'Cuidado personal', '+22% crecimiento proyectado', PURPLE, '#eef0ff'),
        )
        for column, data in enumerate(cards):
            metrics.addWidget(self._kpi_card(*data), 0, column)
            metrics.setColumnStretch(column, 1)
        self.layout.addLayout(metrics)

        body = QGridLayout()
        body.setSpacing(14)
        body.addWidget(self._build_chart_card(), 0, 0)
        body.addWidget(self._build_segment_card(), 0, 1)
        body.setColumnStretch(0, 10)
        body.setColumnStretch(1, 11)
        self.layout.addLayout(body)
        self.layout.addWidget(self._update_banner())
        self.layout.addStretch()

    def _kpi_card(self, icon, title, value, change, color, background):
        card = _card()
        card.setMinimumHeight(125)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 15, 14, 15)
        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(52, 52)
        badge.setStyleSheet(f'background: {background}; color: {color}; border-radius: 12px; font-size: 23px; font-weight: 700;')
        layout.addWidget(badge)
        copy = QVBoxLayout()
        copy.setSpacing(5)
        copy.addWidget(_label(title, 'kpiTitle', True))
        value_label = _label(value, 'kpiValue', True)
        value_label.setStyleSheet(f'color: {color};')
        copy.addWidget(value_label)
        change_label = _label(change, 'kpiChange', True)
        if not change.startswith(('+', '↑')):
            change_label.setStyleSheet('color: #64748b;')
        copy.addWidget(change_label)
        layout.addLayout(copy, 1)
        return card

    def _build_chart_card(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 13, 14, 12)
        header = QHBoxLayout()
        header.addWidget(_label('Tendencia de ventas futuras (proyección)  ⓘ', 'cardTitle'))
        header.addStretch()
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(('Ventas proyectadas', 'Órdenes proyectadas', 'Clientes proyectados'))
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(('Mensual', 'Trimestral'))
        header.addWidget(self.metric_combo)
        header.addWidget(self.frequency_combo)
        layout.addLayout(header)
        self.trend_chart = FutureTrendChart()
        self.metric_combo.currentTextChanged.connect(self.trend_chart.set_metric)
        self.frequency_combo.currentTextChanged.connect(self.trend_chart.set_frequency)
        layout.addWidget(self.trend_chart)
        info = QFrame(objectName='infoBanner')
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.addWidget(_label('ⓘ  Las proyecciones se basan en modelos de aprendizaje automático entrenados con datos históricos.', 'infoText', True))
        layout.addWidget(info)
        return card

    def _build_segment_card(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 13, 0, 0)
        title = _label('Predicciones por segmento', 'cardTitle')
        title.setContentsMargins(14, 0, 14, 7)
        layout.addWidget(title)
        table = QTableWidget(len(self.SEGMENTS), 5)
        table.setHorizontalHeaderLabels(('Segmento', 'Comportamiento previsto', 'Probabilidad', 'Confianza', 'Recomendación'))
        table.setMinimumHeight(337)
        _configure_table(table)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for row_index, row in enumerate(self.SEGMENTS):
            values = row[:5]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                if column == 2:
                    item.setForeground(QColor(row[5]))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif column == 3:
                    item.setForeground(QColor(GREEN if value == 'Alta' else ORANGE if value == 'Media' else RED))
                elif column == 4:
                    item.setForeground(QColor(PURPLE))
                table.setItem(row_index, column, item)
            table.setRowHeight(row_index, 58)
        layout.addWidget(table)
        return card

    def _update_banner(self):
        banner = QFrame(objectName='infoBanner')
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 13, 16, 13)
        self.update_label = _label(
            '✦  Estas predicciones se actualizan automáticamente conforme se incorporan nuevos datos. Última actualización: 12/08/2025 08:30 a. m.',
            'infoText', True,
        )
        layout.addWidget(self.update_label)
        return banner

    def _period_changed(self, period):
        self.update_label.setText(f'✦  Periodo de predicción activo: {period}. Las métricas y la tendencia se han recalculado con datos históricos.')
        self.trend_chart.update()

    def _export(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            'Exportar predicciones',
            str(Path.home() / 'predicciones_flamar.csv'),
            'Archivo CSV (*.csv);;Documento PDF (*.pdf)',
        )
        if not filename:
            self.update_label.setText('ⓘ  Exportación cancelada. No se creó ningún archivo.')
            return
        self.export_requested.emit(filename)
        self.update_label.setText(f'✓  Exportación preparada: {filename}')
        QMessageBox.information(self, 'Exportar predicciones', 'La exportación se preparó correctamente.')


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    preview = PredictionsView()
    preview.resize(1140, 760)
    preview.show()
    sys.exit(app.exec())
