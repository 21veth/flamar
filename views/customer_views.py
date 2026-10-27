import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


PURPLE = '#553cff'
INK = '#0b1739'
MUTED = '#64748b'
GREEN = '#08a66c'
BLUE = '#1479ed'
ORANGE = '#f28b00'
RED = '#ef4444'
TEAL = '#0cae9b'


CONSUMERS = (
    ('C0001', '26 - 35', '12', '2.1 / mes', '$320.50', 'Tecnología', 'Alta', 'Clientes frecuentes'),
    ('C0002', '36 - 45', '8', '1.4 / mes', '$215.30', 'Hogar', 'Media', 'Clientes leales'),
    ('C0003', '18 - 25', '5', '3.0 / mes', '$95.20', 'Belleza', 'Baja', 'Nuevos clientes'),
    ('C0004', '46 - 55', '15', '1.2 / mes', '$410.80', 'Tecnología', 'Alta', 'Clientes VIP'),
    ('C0005', '26 - 35', '9', '2.5 / mes', '$280.00', 'Deportes', 'Media', 'Clientes frecuentes'),
    ('C0006', '56 - 65', '7', '1.1 / mes', '$190.10', 'Hogar', 'Media', 'Clientes leales'),
    ('C0007', '18 - 25', '6', '2.8 / mes', '$130.40', 'Moda', 'Baja', 'Nuevos clientes'),
    ('C0008', '36 - 45', '11', '1.6 / mes', '$260.70', 'Tecnología', 'Alta', 'Clientes frecuentes'),
    ('C0009', '26 - 35', '4', '2.2 / mes', '$85.90', 'Belleza', 'Baja', 'Nuevos clientes'),
    ('C0010', '46 - 55', '10', '1.3 / mes', '$275.60', 'Deportes', 'Media', 'Clientes leales'),
)


class _Page(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName('customerPage')
        self.setStyleSheet(_STYLES)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName('pageScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        self.content = QWidget(objectName='pageContent')
        self.content.setMinimumWidth(900)
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(24, 21, 24, 24)
        self.layout.setSpacing(14)

        heading = QVBoxLayout()
        heading.setSpacing(3)
        heading.addWidget(QLabel(title, objectName='pageTitle'))
        heading.addWidget(QLabel(subtitle, objectName='pageSubtitle'))
        self.layout.addLayout(heading)
        scroll.setWidget(self.content)


class ConsumersView(_Page):
    """Consumer browser with local mock filtering and selection details."""

    def __init__(self, parent=None):
        super().__init__(
            'Consumidores',
            'Explora y analiza el comportamiento de tus consumidores.',
            parent,
        )
        self._visible_consumers = list(CONSUMERS)
        self.layout.addWidget(self._build_filters())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_table_card(), 4)
        body.addWidget(self._build_detail_card(), 1)
        self.layout.addLayout(body)
        self.layout.addStretch()
        self._populate_table(CONSUMERS)

    def _build_filters(self):
        card = QFrame(objectName='card')
        layout = QGridLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(7)

        controls = (
            ('Segmento', ('Todos los segmentos', 'Clientes frecuentes', 'Clientes leales', 'Nuevos clientes', 'Clientes VIP')),
            ('Rango de edad', ('Todos los rangos', '18 - 25', '26 - 35', '36 - 45', '46 - 55', '56 - 65')),
            ('Categoría', ('Todas las categorías', 'Tecnología', 'Hogar', 'Belleza', 'Deportes', 'Moda')),
        )
        self.filters = []
        for column, (label, values) in enumerate(controls):
            layout.addWidget(QLabel(label, objectName='fieldLabel'), 0, column)
            combo = QComboBox()
            combo.addItems(values)
            combo.setMinimumWidth(155)
            self.filters.append(combo)
            layout.addWidget(combo, 1, column)
            layout.setColumnStretch(column, 1)

        layout.addWidget(QLabel('Buscar consumidor', objectName='fieldLabel'), 0, 3)
        self.search = QLineEdit()
        self.search.setPlaceholderText('ID del consumidor')
        self.search.returnPressed.connect(self._apply_filters)
        layout.addWidget(self.search, 1, 3)
        layout.setColumnStretch(3, 1)

        clear = QPushButton('Limpiar')
        clear.setObjectName('secondaryButton')
        clear.clicked.connect(self._clear_filters)
        apply_button = QPushButton('Aplicar filtros')
        apply_button.setObjectName('primaryButton')
        apply_button.clicked.connect(self._apply_filters)
        layout.addWidget(clear, 1, 4)
        layout.addWidget(apply_button, 1, 5)
        return card

    def _build_table_card(self):
        card = QFrame(objectName='card')
        card.setMinimumHeight(500)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 15, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(QLabel('Listado de consumidores', objectName='cardTitle'))
        header.addStretch()
        self.result_label = QLabel('', objectName='hint')
        header.addWidget(self.result_label)
        layout.addLayout(header)

        columns = ('ID Consumidor', 'Rango de edad', 'N.º Compras', 'Frecuencia', 'Gasto promedio', 'Categoría favorita', 'Lealtad', 'Segmento')
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(39)
        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Stretch)
        table_header.setMinimumSectionSize(82)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.table)

        pagination = QHBoxLayout()
        pagination.addWidget(QLabel('Mostrar  10  registros por página', objectName='hint'))
        pagination.addStretch()
        for text in ('‹‹', '‹', '1', '2', '3', '4', '5', '›', '››'):
            button = QPushButton(text)
            button.setObjectName('pageActive' if text == '1' else 'pageButton')
            button.setFixedSize(32, 32)
            pagination.addWidget(button)
        pagination.addStretch()
        pagination.addWidget(QLabel('Página 1 de 25', objectName='hint'))
        layout.addLayout(pagination)
        return card

    def _build_detail_card(self):
        card = QFrame(objectName='detailCard')
        card.setMinimumWidth(235)
        card.setMaximumWidth(290)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(7)

        avatar = QLabel('●', objectName='consumerAvatar')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(72, 72)
        layout.addWidget(avatar, alignment=Qt.AlignHCenter)
        layout.addWidget(QLabel('Consumidor seleccionado', objectName='detailCaption'), alignment=Qt.AlignHCenter)
        self.detail_id = QLabel('', objectName='detailId')
        layout.addWidget(self.detail_id, alignment=Qt.AlignHCenter)
        layout.addWidget(QLabel('ID anonimizado', objectName='hint'), alignment=Qt.AlignHCenter)
        layout.addSpacing(8)

        self.detail_values = {}
        details = (
            ('Compras', 'N.º de compras', '#6d4aff'),
            ('Gasto', 'Gasto promedio', GREEN),
            ('Frecuencia', 'Frecuencia de visita', '#1479ed'),
            ('Lealtad', 'Lealtad', ORANGE),
        )
        for key, label, color in details:
            row = QFrame(objectName='detailRow')
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 9, 5, 9)
            badge = QLabel(key[0], objectName='detailBadge')
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(34, 34)
            badge.setStyleSheet(f'background: {color}18; color: {color}; border-radius: 9px; font-weight: 800;')
            row_layout.addWidget(badge)
            copy = QVBoxLayout()
            copy.setSpacing(0)
            copy.addWidget(QLabel(label, objectName='detailLabel'))
            value = QLabel('', objectName='detailValue')
            copy.addWidget(value)
            self.detail_values[key] = value
            row_layout.addLayout(copy, 1)
            layout.addWidget(row)
        layout.addStretch()

        profile = QPushButton('Ver perfil completo')
        profile.setObjectName('primaryButton')
        profile.clicked.connect(lambda: self.feedback.setText(f'Perfil {self.detail_id.text()} listo para consultar'))
        layout.addWidget(profile)
        self.feedback = QLabel('', objectName='feedback')
        self.feedback.setAlignment(Qt.AlignCenter)
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        return card

    def _populate_table(self, consumers):
        self._visible_consumers = list(consumers)
        self.table.setRowCount(len(consumers))
        category_colors = {'Tecnología': PURPLE, 'Hogar': ORANGE, 'Belleza': '#d6298f', 'Deportes': GREEN, 'Moda': '#d6298f'}
        loyalty_colors = {'Alta': GREEN, 'Media': ORANGE, 'Baja': RED}
        for row, consumer in enumerate(consumers):
            for column, text in enumerate(consumer):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if column in (2, 3, 6) else Qt.AlignLeft))
                if column == 5:
                    item.setForeground(QColor(category_colors.get(text, INK)))
                elif column == 6:
                    item.setForeground(QColor(loyalty_colors.get(text, INK)))
                elif column == 7:
                    item.setForeground(QColor(PURPLE))
                self.table.setItem(row, column, item)
        self.result_label.setText(f'Mostrando 1–{len(consumers)} de 250 consumidores' if consumers else 'Sin resultados')
        if consumers:
            self.table.selectRow(0)
        else:
            self._set_detail(None)

    def _selection_changed(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._visible_consumers):
            self._set_detail(self._visible_consumers[row])

    def _set_detail(self, consumer):
        if consumer is None:
            self.detail_id.setText('—')
            for label in self.detail_values.values():
                label.setText('—')
            return
        self.detail_id.setText(consumer[0])
        self.detail_values['Compras'].setText(consumer[2])
        self.detail_values['Gasto'].setText(consumer[4])
        self.detail_values['Frecuencia'].setText(consumer[3])
        self.detail_values['Lealtad'].setText(consumer[6])
        self.detail_values['Lealtad'].setStyleSheet(f"color: {GREEN if consumer[6] == 'Alta' else ORANGE if consumer[6] == 'Media' else RED};")
        self.feedback.clear()

    def _apply_filters(self):
        segment, age, category = (combo.currentText() for combo in self.filters)
        query = self.search.text().strip().lower()
        matches = [
            consumer for consumer in CONSUMERS
            if (segment.startswith('Todos') or consumer[7] == segment)
            and (age.startswith('Todos') or consumer[1] == age)
            and (category.startswith('Todas') or consumer[5] == category)
            and (not query or query in consumer[0].lower())
        ]
        self._populate_table(matches)

    def _clear_filters(self):
        for combo in self.filters:
            combo.setCurrentIndex(0)
        self.search.clear()
        self._populate_table(CONSUMERS)


class ScatterPlot(QWidget):
    """Deterministic four-cluster plot rendered without a chart package."""

    COLORS = ('#ff352f', '#ff960d', '#0caf9f', '#6246ed')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(270)
        self._points = []
        randomizer = random.Random(73450)
        clusters = ((9.2, 930, 1.0, 140), (6.7, 520, 1.25, 190), (4.0, 590, 1.0, 170), (10.3, 380, 1.0, 135))
        for group, (center_x, center_y, spread_x, spread_y) in enumerate(clusters):
            for _ in range(72):
                x = max(.2, min(13.5, randomizer.gauss(center_x, spread_x)))
                y = max(20, min(1180, randomizer.gauss(center_y, spread_y)))
                self._points.append((x, y, group))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(58, 16, -18, -42)
        painter.setFont(QFont('Segoe UI', 8))

        for value in range(0, 1201, 300):
            y = area.bottom() - value / 1200 * area.height()
            painter.setPen(QPen(QColor('#e3e9f2'), 1, Qt.DashLine))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(0, y - 8, 50, 16), Qt.AlignRight | Qt.AlignVCenter, str(value))
        for value in range(0, 15, 2):
            x = area.left() + value / 14 * area.width()
            painter.setPen(QPen(QColor('#e3e9f2'), 1, Qt.DashLine))
            painter.drawLine(int(x), area.top(), int(x), area.bottom())
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(x - 14, area.bottom() + 6, 28, 16), Qt.AlignCenter, str(value))

        painter.setPen(QPen(QColor('#afbdd0'), 1))
        painter.drawLine(area.bottomLeft(), area.bottomRight())
        painter.drawLine(area.bottomLeft(), area.topLeft())
        painter.setFont(QFont('Segoe UI', 9, QFont.DemiBold))
        painter.setPen(QColor(INK))
        painter.drawText(QRectF(area.left(), area.bottom() + 24, area.width(), 18), Qt.AlignCenter, 'Frecuencia de compra (compras/mes)')
        painter.save()
        painter.translate(13, area.center().y())
        painter.rotate(-90)
        painter.drawText(QRectF(-area.height() / 2, -9, area.height(), 18), Qt.AlignCenter, 'Gasto promedio ($)')
        painter.restore()

        painter.setOpacity(.9)
        painter.setPen(Qt.NoPen)
        for x_value, y_value, group in self._points:
            x = area.left() + x_value / 14 * area.width()
            y = area.bottom() - y_value / 1200 * area.height()
            painter.setBrush(QColor(self.COLORS[group]))
            painter.drawEllipse(QPointF(x, y), 3.1, 3.1)


class SegmentationView(_Page):
    """Segmentation overview with deterministic visualization and mock execution."""

    SEGMENTS = (
        ('1', 'Compradores recurrentes', 'Alta frecuencia, ticket elevado y fidelidad a categorías clave.', '#7647ed'),
        ('2', 'Sensibles a promociones', 'Aumentan sus compras ante promociones y descuentos.', TEAL),
        ('3', 'Exploradores de tendencias', 'Interés en novedades y alta rotación de categorías.', '#f28b00'),
        ('4', 'Compradores estacionales', 'Concentran sus compras en temporadas específicas.', '#1479ed'),
    )

    def __init__(self, parent=None):
        super().__init__(
            'Segmentación comercial',
            'Descubre y analiza segmentos de clientes para diseñar estrategias comerciales más efectivas.',
            parent,
        )
        self._progress_value = 0
        self._timer = QTimer(self)
        self._timer.setInterval(55)
        self._timer.timeout.connect(self._advance_progress)
        self.layout.addLayout(self._build_metrics())
        self.layout.addLayout(self._build_analysis())
        self.layout.addWidget(self._build_comparison())
        self.layout.addStretch()

    def _build_metrics(self):
        grid = QGridLayout()
        grid.setSpacing(14)
        cards = (
            ('3,450', 'Registros analizados', '+12% vs. mes anterior', GREEN, 'C'),
            ('4', 'Segmentos detectados', 'Sin cambios vs. mes anterior', BLUE, 'S'),
            ('12/08/2025', 'Última actualización', 'Hace 3 días', RED, 'A'),
        )
        for column, data in enumerate(cards):
            grid.addWidget(self._metric_card(*data), 0, column)
            grid.setColumnStretch(column, 1)

        action = QFrame(objectName='card')
        action_layout = QVBoxLayout(action)
        action_layout.setContentsMargins(16, 13, 16, 13)
        self.execute_button = QPushButton('▶  Ejecutar segmentación')
        self.execute_button.setObjectName('primaryButton')
        self.execute_button.clicked.connect(self._execute)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.status = QLabel('Modelo listo para ejecutar', objectName='feedback')
        action_layout.addWidget(self.execute_button)
        action_layout.addWidget(self.progress)
        action_layout.addWidget(self.status)
        grid.addWidget(action, 0, 3)
        grid.setColumnStretch(3, 1)
        return grid

    @staticmethod
    def _metric_card(value, label, note, color, icon):
        card = QFrame(objectName='card')
        card.setMinimumHeight(104)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(48, 48)
        badge.setStyleSheet(f'background: {color}18; color: {color}; border-radius: 12px; font-size: 18px; font-weight: 800;')
        layout.addWidget(badge)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        copy.addWidget(QLabel(value, objectName='metricValue'))
        copy.addWidget(QLabel(label, objectName='metricLabel'))
        note_label = QLabel(note, objectName='positive' if note.startswith('+') else 'hint')
        copy.addWidget(note_label)
        layout.addLayout(copy, 1)
        return card

    def _build_analysis(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        plot_card = QFrame(objectName='card')
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(15, 13, 15, 10)
        plot_layout.addWidget(QLabel('Visualización de segmentos (clusters)', objectName='cardTitle'))
        plot_layout.addWidget(ScatterPlot(), 1)
        row.addWidget(plot_card, 3)

        descriptions = QFrame(objectName='card')
        descriptions.setMinimumWidth(320)
        descriptions_layout = QVBoxLayout(descriptions)
        descriptions_layout.setContentsMargins(14, 13, 14, 13)
        descriptions_layout.addWidget(QLabel('Descripción de segmentos', objectName='cardTitle'))
        for number, name, summary, color in self.SEGMENTS:
            item = QFrame(objectName='segmentItem')
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(10, 8, 10, 8)
            marker = QLabel(number)
            marker.setAlignment(Qt.AlignCenter)
            marker.setFixedSize(28, 28)
            marker.setStyleSheet(f'background: {color}; color: white; border-radius: 9px; font-weight: 800;')
            item_layout.addWidget(marker)
            copy = QVBoxLayout()
            copy.setSpacing(0)
            copy.addWidget(QLabel(f'Segmento {number}', objectName='segmentTitle'))
            name_label = QLabel(name, objectName='segmentName')
            name_label.setStyleSheet(f'color: {color}; font-size: 10px; font-weight: 700;')
            copy.addWidget(name_label)
            item_layout.addLayout(copy, 1)
            summary_label = QLabel(summary, objectName='segmentSummary')
            summary_label.setWordWrap(True)
            summary_label.setFixedWidth(150)
            item_layout.addWidget(summary_label)
            descriptions_layout.addWidget(item)
        row.addWidget(descriptions, 2)
        return row

    def _build_comparison(self):
        card = QFrame(objectName='card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 13, 14, 14)
        layout.addWidget(QLabel('Comparación de características por segmento', objectName='cardTitle'))
        rows = (
            ('Frecuencia de compra (promedio/mes)', '9.8', '5.2', '4.1', '3.6'),
            ('Ticket promedio ($)', '$220', '$95', '$140', '$110'),
            ('Respuesta a promociones', 'Media', 'Alta', 'Alta', 'Media'),
            ('Afinidad estacional', 'Baja', 'Media', 'Media', 'Alta'),
            ('Potencial de abastecimiento', 'Alto', 'Medio', 'Medio', 'Alto'),
        )
        table = QTableWidget(len(rows), 5)
        table.setHorizontalHeaderLabels(('Característica', '●  Recurrentes', '●  Sensibles a promociones', '●  Exploradores', '●  Estacionales'))
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setShowGrid(True)
        table.setMinimumHeight(246)
        table.verticalHeader().setDefaultSectionSize(32)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for column in range(1, 5):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if column == 0 else Qt.AlignCenter))
                if row_index >= 4 and column > 0:
                    color = GREEN if value in ('Baja', 'Alta') and (row_index, value) in ((4, 'Baja'), (5, 'Alta')) else ORANGE if value == 'Media' else RED
                    item.setForeground(QColor(color))
                table.setItem(row_index, column, item)
        layout.addWidget(table)
        note = QLabel('ⓘ  Los valores mostrados son promedios por segmento y pueden variar según el período analizado.', objectName='hint')
        layout.addWidget(note)
        return card

    def _execute(self):
        if self._timer.isActive():
            return
        self._progress_value = 0
        self.progress.setValue(0)
        self.progress.show()
        self.execute_button.setEnabled(False)
        self.status.setText('Preparando datos…')
        self._timer.start()

    def _advance_progress(self):
        self._progress_value = min(100, self._progress_value + 4)
        self.progress.setValue(self._progress_value)
        if self._progress_value < 45:
            self.status.setText('Preparando datos…')
        elif self._progress_value < 85:
            self.status.setText('Identificando clusters…')
        else:
            self.status.setText('Generando resultados…')
        if self._progress_value == 100:
            self._timer.stop()
            self.execute_button.setEnabled(True)
            self.execute_button.setText('▶  Ejecutar nuevamente')
            self.status.setText('Segmentación completada: 4 segmentos identificados')


_STYLES = '''
    QWidget#customerPage, QWidget#pageContent, QScrollArea#pageScroll {
        background: #f8faff; color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI";
    }
    QScrollArea#pageScroll { border: none; }
    QScrollBar:vertical { background: #f1f4f9; width: 8px; }
    QScrollBar::handle:vertical { background: #c8d1df; border-radius: 4px; min-height: 36px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QLabel#pageTitle { color: #09142f; font-size: 23px; font-weight: 800; }
    QLabel#pageSubtitle, QLabel#hint { color: #64748b; font-size: 10px; }
    QFrame#card, QFrame#detailCard {
        background: white; border: 1px solid #dfe5ee; border-radius: 11px;
    }
    QFrame#detailCard { background: #fbfaff; }
    QLabel#cardTitle { color: #111827; font-size: 13px; font-weight: 750; }
    QLabel#fieldLabel { color: #1b263b; font-size: 10px; font-weight: 700; }
    QComboBox, QLineEdit {
        background: white; color: #25324a; border: 1px solid #d8e0eb; border-radius: 7px;
        padding: 8px 10px; min-height: 18px; font-size: 10px;
    }
    QComboBox::drop-down { border: none; width: 24px; }
    QPushButton { font-size: 10px; font-weight: 650; }
    QPushButton#primaryButton {
        color: white; background: #553cff; border: none; border-radius: 7px; padding: 10px 14px;
    }
    QPushButton#primaryButton:hover { background: #4631df; }
    QPushButton#primaryButton:disabled { background: #a49af3; }
    QPushButton#secondaryButton {
        color: #273654; background: white; border: 1px solid #d8e0eb; border-radius: 7px; padding: 9px 13px;
    }
    QTableWidget {
        color: #17233c; background: white; alternate-background-color: white;
        border: 1px solid #dfe5ee; border-radius: 7px; gridline-color: #e5eaf1; font-size: 9px;
        selection-background-color: #f0edff; selection-color: #17233c;
    }
    QHeaderView::section {
        color: #17233c; background: #f9fbfe; border: none; border-bottom: 1px solid #dfe5ee;
        padding: 9px 5px; font-size: 9px; font-weight: 700;
    }
    QPushButton#pageButton, QPushButton#pageActive {
        color: #526177; background: white; border: 1px solid #dce3ed; border-radius: 6px;
    }
    QPushButton#pageActive { color: white; background: #553cff; border-color: #553cff; }
    QLabel#consumerAvatar {
        color: #553cff; background: #ebe8ff; border: 2px solid white; border-radius: 36px; font-size: 34px;
    }
    QLabel#detailCaption, QLabel#detailLabel { color: #28354d; font-size: 9px; }
    QLabel#detailId { color: #10182c; font-size: 18px; font-weight: 800; }
    QLabel#detailValue { color: #10182c; font-size: 14px; font-weight: 750; }
    QFrame#detailRow { background: white; border: none; border-bottom: 1px solid #e6eaf1; }
    QLabel#feedback { color: #56657b; font-size: 9px; }
    QLabel#metricValue { color: #0b1020; font-size: 19px; font-weight: 800; }
    QLabel#metricLabel { color: #273654; font-size: 10px; font-weight: 650; }
    QLabel#positive { color: #08a66c; font-size: 9px; font-weight: 700; }
    QFrame#segmentItem { background: #ffffff; border: 1px solid #e0e6ef; border-radius: 8px; }
    QLabel#segmentTitle { color: #111827; font-size: 10px; font-weight: 750; }
    QLabel#segmentSummary { color: #41516a; font-size: 9px; }
    QProgressBar { background: #eceffa; border: none; border-radius: 3px; height: 6px; }
    QProgressBar::chunk { background: #553cff; border-radius: 3px; }
'''


__all__ = ['ConsumersView', 'SegmentationView']
