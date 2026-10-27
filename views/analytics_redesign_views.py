"""Content-only analytics views recreated from the supplied FLAMAR references."""

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


INK = '#081433'
MUTED = '#60708f'
PURPLE = '#5425f5'
GREEN = '#10b875'
ORANGE = '#ff9f16'
BLUE = '#2380f5'
RED = '#ee4161'
BORDER = '#dce4f0'
TINTS = {
    PURPLE: '#f0edff', GREEN: '#eaf9f2', ORANGE: '#fff5e7',
    BLUE: '#edf5ff', RED: '#fff0f3',
}


class _Header(QWidget):
    def __init__(self, title, subtitle='', greeting='', date='01/08/2025 - 31/08/2025', parent=None):
        super().__init__(parent)
        self.setMinimumHeight(106 if greeting else 66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        copy.addWidget(QLabel(title, objectName='pageTitle'))
        if greeting:
            copy.addWidget(QLabel(greeting, objectName='greeting'))
        if subtitle:
            copy.addWidget(QLabel(subtitle, objectName='subtitle'))
        layout.addLayout(copy, 1)
        date_box = QLabel(f'DATE   {date}      v', objectName='dateBox')
        date_box.setMinimumWidth(225)
        layout.addWidget(date_box, alignment=Qt.AlignTop)
        bell = QLabel('!', objectName='bell')
        bell.setAlignment(Qt.AlignCenter)
        bell.setFixedSize(36, 36)
        layout.addWidget(bell, alignment=Qt.AlignTop)
        avatar = QLabel('AA', objectName='avatar')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(42, 42)
        layout.addWidget(avatar, alignment=Qt.AlignTop)
        account = QVBoxLayout()
        account.setSpacing(1)
        account.addWidget(QLabel('Administrador', objectName='accountName'))
        account.addWidget(QLabel('Administrador', objectName='accountRole'))
        layout.addLayout(account)
        layout.addWidget(QLabel('v', objectName='chevron'), alignment=Qt.AlignTop)


class _Page(QWidget):
    def __init__(self, title, subtitle='', greeting='', date='01/08/2025 - 31/08/2025', parent=None):
        super().__init__(parent)
        self.setObjectName('analyticsPage')
        self.setStyleSheet(_STYLES)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(objectName='pageScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget(objectName='pageContent')
        self.content.setMinimumWidth(0)
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(22, 17, 22, 22)
        self.layout.setSpacing(13)
        self.layout.addWidget(_Header(title, subtitle, greeting, date))
        scroll.setWidget(self.content)
        outer.addWidget(scroll)

    @staticmethod
    def card(title='', action=''):
        frame = QFrame(objectName='card')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(8)
        if title:
            heading = QHBoxLayout()
            heading.addWidget(QLabel(title, objectName='cardTitle'))
            heading.addWidget(QLabel('ⓘ', objectName='info'))
            heading.addStretch()
            if action:
                heading.addWidget(QLabel(action, objectName='link'))
            layout.addLayout(heading)
        return frame, layout


class _ScatterChart(QWidget):
    COLORS = (PURPLE, GREEN, ORANGE, BLUE)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(330)
        rng = random.Random(80425)
        centers = ((10.4, 188, 1.25, 35), (5.8, 180, .95, 33), (3.0, 102, 1.05, 30), (8.3, 62, 1.25, 25))
        self.points = []
        for group, (cx, cy, sx, sy) in enumerate(centers):
            for _ in range(75):
                self.points.append((max(.3, min(14.5, rng.gauss(cx, sx))), max(5, min(290, rng.gauss(cy, sy))), group))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(62, 12, -12, -46)
        p.setFont(QFont('Sans Serif', 9))
        for value in range(0, 301, 50):
            y = area.bottom() - value / 300 * area.height()
            p.setPen(QPen(QColor('#dce4ee'), 1))
            p.drawLine(area.left(), int(y), area.right(), int(y))
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(8, y - 8, 43, 16), Qt.AlignRight | Qt.AlignVCenter, str(value))
        for value in range(0, 15, 2):
            x = area.left() + value / 15 * area.width()
            p.setPen(QPen(QColor('#e4eaf2'), 1))
            p.drawLine(int(x), area.top(), int(x), area.bottom())
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(x - 14, area.bottom() + 6, 28, 16), Qt.AlignCenter, str(value))
        p.setPen(Qt.NoPen)
        for xv, yv, group in self.points:
            color = QColor(self.COLORS[group])
            color.setAlpha(205)
            p.setBrush(color)
            p.drawEllipse(QPointF(area.left() + xv / 15 * area.width(), area.bottom() - yv / 300 * area.height()), 3.2, 3.2)
        p.setPen(QColor('#435273'))
        p.drawText(QRectF(area.left(), area.bottom() + 27, area.width(), 17), Qt.AlignCenter, 'Frecuencia de compra (compras/mes)')
        p.save()
        p.translate(15, area.center().y())
        p.rotate(-90)
        p.drawText(QRectF(-area.height() / 2, -9, area.height(), 18), Qt.AlignCenter, 'Ticket promedio (S/)')
        p.restore()


class _NetworkChart(QWidget):
    NODES = (
        (.50, .48, 47, 'MS', 'Mochila\nescolar', PURPLE), (.72, .51, 40, 'KP', 'Playera\nK-pop', '#35c56b'),
        (.50, .75, 39, 'DH', 'Decoración\nHalloween', '#ff7622'), (.31, .48, 25, 'AU', 'Audífonos', ORANGE),
        (.50, .18, 19, 'CU', 'Cuaderno\nuniversitario', '#8356ef'), (.70, .23, 18, 'PL', 'Plumas', '#37c978'),
        (.30, .23, 18, 'LP', 'Lapicera', '#438bf1'), (.17, .40, 14, 'ES', 'Estuche', '#f75a91'),
        (.15, .58, 14, 'TE', 'Tecnología', ORANGE), (.76, .73, 16, 'DI', 'Disfraces', '#f274a8'),
        (.30, .78, 16, 'LU', 'Luces', '#ffc538'), (.50, .92, 16, 'AC', 'Accesorios', '#55a5ef'),
        (.90, .36, 14, 'ST', 'Sticker', '#f45a91'), (.93, .54, 14, 'LL', 'Llavero', '#4e8dec'),
        (.88, .69, 14, 'PO', 'Póster', '#7855ef'),
    )
    EDGES = ((0, 4), (0, 6), (0, 7), (0, 3), (0, 1), (0, 2), (0, 5), (1, 12), (1, 13), (1, 14), (2, 9), (2, 10), (2, 11), (3, 8))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(480)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(8, 5, -8, -25)
        points = [QPointF(area.left() + x * area.width(), area.top() + y * area.height()) for x, y, *_ in self.NODES]
        for a, b in self.EDGES:
            p.setPen(QPen(QColor(self.NODES[b][5]), 1.4))
            p.drawLine(points[a], points[b])
        for point, (_, _, radius, icon, label, color) in zip(points, self.NODES):
            p.setPen(QPen(QColor('white'), 2))
            p.setBrush(QColor(color))
            p.drawEllipse(point, radius, radius)
            if icon:
                p.setFont(QFont('Sans Serif', 11 if radius > 25 else 7, QFont.Bold))
                p.setPen(QColor('white' if radius > 25 else INK))
                p.drawText(QRectF(point.x() - radius, point.y() - radius + 7, radius * 2, radius), Qt.AlignCenter, icon)
            p.setFont(QFont('Sans Serif', 9, QFont.DemiBold if radius > 25 else QFont.Normal))
            p.setPen(QColor('white') if radius > 25 else QColor(INK))
            y = point.y() + (3 if radius > 25 else radius + 3)
            p.drawText(QRectF(point.x() - 48, y, 96, 32), Qt.AlignHCenter | Qt.AlignTop, label)


class _ForecastChart(QWidget):
    ACTUAL = (3, 4.5, 7, 7, 7, 10.5, 14, 13, 17, 20)
    FORECAST = (20, 28, 38, 32, 28, 24, 24, 20, 19, 17, 19, 21)
    LABELS = ('Ene\n2025', 'Feb\n2025', 'Mar\n2025', 'Abr\n2025', 'May\n2025', 'Jun\n2025', 'Jul\n2025', 'Ago\n2025', 'Sep\n2025', 'Oct\n2025', 'Nov\n2025', 'Dic\n2025', 'Ene\n2026', 'Feb\n2026', 'Mar\n2026', 'Abr\n2026', 'May\n2026', 'Jun\n2026', 'Jul\n2026', 'Ago\n2026')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(295)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(57, 46, -12, -48)
        p.setFont(QFont('Sans Serif', 8))
        for value in range(0, 51, 10):
            y = area.bottom() - value / 50 * area.height()
            p.setPen(QPen(QColor('#dfe6f0'), 1))
            p.drawLine(area.left(), int(y), area.right(), int(y))
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(2, y - 8, 43, 16), Qt.AlignRight | Qt.AlignVCenter, '0' if value == 0 else f'{value}K')
        step = area.width() / 19
        for i, label in enumerate(self.LABELS):
            x = area.left() + i * step
            p.setPen(QPen(QColor('#edf1f6'), 1))
            p.drawLine(int(x), area.top(), int(x), area.bottom())
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(x - 20, area.bottom() + 7, 40, 31), Qt.AlignHCenter | Qt.AlignTop, label)
        forecast_points = [QPointF(area.left() + (i + 9) * step, area.bottom() - value / 50 * area.height()) for i, value in enumerate(self.FORECAST)]
        upper = [QPointF(pt.x(), max(area.top(), pt.y() - (22 if i < 4 else 30))) for i, pt in enumerate(forecast_points)]
        lower = [QPointF(pt.x(), min(area.bottom(), pt.y() + (30 if i < 5 else 38))) for i, pt in enumerate(forecast_points)]
        band = QPainterPath(upper[0])
        for point in upper[1:]:
            band.lineTo(point)
        for point in reversed(lower):
            band.lineTo(point)
        band.closeSubpath()
        p.fillPath(band, QColor(102, 75, 238, 35))
        actual_points = [QPointF(area.left() + i * step, area.bottom() - value / 50 * area.height()) for i, value in enumerate(self.ACTUAL)]
        p.setPen(QPen(QColor(PURPLE), 2.4))
        p.drawPolyline(actual_points)
        dashed = QPen(QColor('#6a48f4'), 2.2, Qt.DashLine)
        p.setPen(dashed)
        p.drawPolyline(forecast_points)
        for point in actual_points + forecast_points:
            p.setPen(QPen(QColor(PURPLE), 1.5))
            p.setBrush(QColor(PURPLE))
            p.drawEllipse(point, 3, 3)
        divider_x = area.left() + 9 * step
        p.setPen(QPen(QColor('#8b97ab'), 1, Qt.DashLine))
        p.drawLine(int(divider_x), area.top() - 8, int(divider_x), area.bottom())
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(area.left() + 6 * step, 5, 58, 24), Qt.AlignCenter, 'Histórico')
        p.drawText(QRectF(divider_x + 18, 5, 64, 24), Qt.AlignCenter, 'Pronóstico')


class SegmentationView(_Page):
    SEGMENTS = (
        ('Compradores recurrentes', 'Alta frecuencia de compra, ticket promedio elevado y\nfidelidad a categorías clave.', '28% del total', PURPLE, 'CR'),
        ('Sensibles a promociones', 'Aumentan significativamente sus compras ante\npromociones y descuentos.', '24% del total', GREEN, 'SP'),
        ('Exploradores de tendencias', 'Interés en novedades y lanzamientos, alta rotación\nde categorías.', '18% del total', ORANGE, '↗'),
        ('Compradores estacionales', 'Concentran sus compras en temporadas específicas\ndel año (ej. escolar, navidad, halloween).', '30% del total', BLUE, 'CE'),
    )

    def __init__(self, parent=None):
        super().__init__('Segmentación comercial', 'Descubre y analiza segmentos de clientes para diseñar estrategias comerciales más efectivas.', parent=parent)
        self.layout.addLayout(self._metrics())
        body = QHBoxLayout()
        body.setSpacing(12)
        chart_card, chart_layout = self.card('Visualización de segmentos')
        controls = QHBoxLayout()
        controls.addStretch()
        mode = QComboBox()
        mode.addItems(('Segmentos', 'Densidad', 'Distribución'))
        controls.addWidget(mode)
        chart_layout.addLayout(controls)
        chart_layout.addWidget(_ScatterChart(), 1)
        body.addWidget(chart_card, 3)
        body.addWidget(self._segment_card(), 2)
        self.layout.addLayout(body)
        self.layout.addWidget(self._comparison())
        self.layout.addStretch()

    def _metrics(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        data = (
            ('CL', '3,450', 'Registros analizados', '+ 12%', 'vs. mes anterior', GREEN),
            ('SG', '4', 'Segmentos detectados', '+ 0%', 'vs. mes anterior', BLUE),
            ('DT', '12/08/2025', 'Última actualización', '+ 3 días', 'vs. periodo anterior', RED),
            ('TOP', 'Compradores recurrentes', 'Segmento con mayor\npotencial', '+ 28%', 'potencial estimado', ORANGE),
        )
        for icon, value, label, delta, note, color in data:
            card = QFrame(objectName='metricCard')
            card.setMinimumHeight(102)
            box = QHBoxLayout(card)
            box.setContentsMargins(15, 13, 15, 13)
            badge = QLabel(icon)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(53, 53)
            badge.setStyleSheet(f'background:{TINTS[color]};color:{color};border-radius:12px;font-size:11px;font-weight:800;border:none;')
            box.addWidget(badge)
            copy = QVBoxLayout()
            copy.setSpacing(2)
            copy.addWidget(QLabel(value, objectName='metricValue' if len(value) < 12 else 'metricName'))
            copy.addWidget(QLabel(label, objectName='metricLabel'))
            box.addLayout(copy, 1)
            trend = QVBoxLayout()
            chip = QLabel(delta, objectName='trendGreen' if color != RED else 'trendRed')
            chip.setAlignment(Qt.AlignCenter)
            trend.addWidget(chip)
            trend.addWidget(QLabel(note, objectName='tiny'), alignment=Qt.AlignCenter)
            box.addLayout(trend)
            row.addWidget(card, 1)
        return row

    def _segment_card(self):
        card, layout = self.card('Descripción de segmentos', 'Ver todos')
        for index, (name, description, share, color, icon) in enumerate(self.SEGMENTS, 1):
            item = QFrame(objectName='listItem')
            line = QHBoxLayout(item)
            line.setContentsMargins(11, 8, 9, 8)
            dot = QLabel('●')
            dot.setStyleSheet(f'color:{color};font-size:18px;border:none;')
            line.addWidget(dot)
            badge = QLabel(icon)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(45, 45)
            badge.setStyleSheet(f'background:{TINTS[color]};color:{color};border-radius:10px;border:none;font-size:10px;font-weight:800;')
            line.addWidget(badge)
            copy = QVBoxLayout()
            title = QHBoxLayout()
            title.addWidget(QLabel(name, objectName='rowTitle'))
            title.addStretch()
            title.addWidget(QLabel(f'Segmento {index}', objectName='tiny'))
            title.addWidget(QLabel(share, objectName='softChip'))
            copy.addLayout(title)
            copy.addWidget(QLabel(description, objectName='rowCopy'))
            line.addLayout(copy, 1)
            layout.addWidget(item)
        return card

    def _comparison(self):
        card, layout = self.card('Comparación de características por segmento')
        rows = (
            ('Frecuencia de compra (promedio/mes)', '9.8', '5.2', '4.1', '3.6'),
            ('Ticket promedio (S/)', 'S/ 220', 'S/ 95', 'S/ 140', 'S/ 110'),
            ('Respuesta a promociones', 'Media', 'Alta', 'Alta', 'Media'),
            ('Afinidad estacional', 'Baja', 'Media', 'Media', 'Alta'),
            ('Potencial de abastecimiento', 'Alto', 'Medio', 'Medio', 'Alto'),
        )
        table = _table(rows, ('Característica', '●  Compradores recurrentes', '●  Sensibles a promociones', '●  Exploradores de tendencias', '●  Compradores estacionales'), 188)
        for row in range(2, 5):
            for col in range(1, 5):
                text = table.item(row, col).text()
                table.item(row, col).setForeground(QColor(GREEN if text in ('Alta', 'Alto') else RED if text == 'Baja' else ORANGE))
        layout.addWidget(table)
        return card


class PurchasePatternsView(_Page):
    ROWS = (
        ('1', 'MS   Mochila escolar', 'CU   Cuaderno universitario', '18.2%', '72.3%', 'Alta', 'Ver detalles'),
        ('2', 'KP   Playera K-pop', 'ST   Sticker K-pop', '15.6%', '68.1%', 'Alta', 'Ver detalles'),
        ('3', 'DH   Decoración Halloween', 'LU   Luces decorativas', '12.4%', '64.7%', 'Alta', 'Ver detalles'),
        ('4', 'PA   Papelera', 'PL   Plumas', '10.9%', '59.2%', 'Media', 'Ver detalles'),
        ('5', 'AU   Tecnología - Audífonos', 'ES   Estuche', '9.8%', '56.1%', 'Media', 'Ver detalles'),
        ('6', 'KP   Playera K-pop', 'LL   Llavero colgante', '8.7%', '53.6%', 'Media', 'Ver detalles'),
        ('7', 'MS   Mochila escolar', 'LP   Lapicera', '8.1%', '51.4%', 'Media', 'Ver detalles'),
        ('8', 'CP   Cuidado personal', 'CF   Cosmético facial', '6.9%', '48.7%', 'Baja', 'Ver detalles'),
        ('9', 'DN   Decoración Navidad', 'SL   Serie de luces', '6.4%', '47.1%', 'Baja', 'Ver detalles'),
        ('10', 'AC   Accesorios', 'LL   Llavero', '5.9%', '45.3%', 'Baja', 'Ver detalles'),
    )

    def __init__(self, parent=None):
        super().__init__('Patrones de compra', 'Descubre qué productos se compran juntos para crear mejores promociones y estrategias comerciales.', parent=parent)
        self.layout.addWidget(self._filters())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._relations(), 6)
        network, network_layout = self.card('Visualización de relaciones')
        network_layout.addWidget(_NetworkChart())
        legend = QLabel('●  Escolar       ●  Tecnología       ●  K-pop       ●  Decoración       ●  Papelería       ●  Accesorios', objectName='legend')
        legend.setAlignment(Qt.AlignCenter)
        network_layout.addWidget(legend)
        body.addWidget(network, 5)
        self.layout.addLayout(body)
        self.layout.addWidget(self._insight())
        self.layout.addStretch()

    def _filters(self):
        card = QFrame(objectName='card')
        card.setMinimumHeight(91)
        grid = QGridLayout(card)
        grid.setContentsMargins(15, 11, 15, 14)
        labels = ('Tienda', 'Categoría', 'Segmento', 'Rango de fechas')
        values = (('Todas las tiendas', 'Tienda Centro', 'Tienda Norte'), ('Todas las categorías', 'Escolar', 'K-pop'), ('Todos los segmentos', 'Recurrentes', 'Estacionales'), ('01/08/2025 - 31/08/2025', '01/07/2025 - 31/07/2025'))
        self.filters = []
        for col, (label, options) in enumerate(zip(labels, values)):
            grid.addWidget(QLabel(label, objectName='fieldLabel'), 0, col)
            combo = QComboBox()
            combo.addItems(options)
            self.filters.append(combo)
            grid.addWidget(combo, 1, col)
            grid.setColumnStretch(col, 1)
        button = QPushButton('Aplicar filtros', objectName='primaryButton')
        button.clicked.connect(self._apply_filters)
        grid.addWidget(button, 1, 4)
        self.filter_status = QLabel('', objectName='status')
        grid.addWidget(self.filter_status, 2, 0, 1, 5)
        self.filter_status.hide()
        return card

    def _relations(self):
        card, layout = self.card('Relaciones detectadas', 'Mostrando 1–10 de 42     Ver todas')
        self.relations_table = _table(self.ROWS, ('#', 'Producto A', 'Producto B', 'Soporte', 'Confianza', 'Prioridad', 'Acción'), 498)
        self.relations_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.relations_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for row in range(len(self.ROWS)):
            priority = self.relations_table.item(row, 5).text()
            self.relations_table.item(row, 5).setForeground(QColor(RED if priority == 'Alta' else ORANGE if priority == 'Media' else GREEN))
            self.relations_table.item(row, 6).setForeground(QColor(PURPLE))
        layout.addWidget(self.relations_table)
        return card

    def _apply_filters(self):
        self.filter_status.setText(f'Filtros aplicados: {self.filters[0].currentText()} - 10 relaciones encontradas')
        self.filter_status.show()

    @staticmethod
    def _insight():
        panel = QFrame(objectName='insight')
        panel.setMinimumHeight(135)
        row = QHBoxLayout(panel)
        row.setContentsMargins(16, 13, 16, 13)
        bulb = QLabel('●', objectName='bulb')
        bulb.setAlignment(Qt.AlignCenter)
        bulb.setFixedSize(52, 52)
        row.addWidget(bulb)
        copy = QVBoxLayout()
        copy.addWidget(QLabel('Insight destacado     <span style="color:#ee4161">● Alta oportunidad</span>', objectName='insightLabel'))
        copy.addWidget(QLabel('Combo escolar: Mochila + Cuaderno + Lapicera', objectName='insightTitle'))
        text = QLabel('El 72% de los clientes que compran una mochila también adquieren un cuaderno universitario.\nSe recomienda crear un combo promocional que incluya mochila, cuaderno y lapicera, con un descuento del 15–20%.', objectName='rowCopy')
        copy.addWidget(text)
        row.addLayout(copy, 3)
        for value, label, detail in (('18.2%', 'Soporte', 'de las compras incluyen\nambos productos'), ('72.3%', 'Confianza', 'de quienes compran la\nmochila también compran'), ('+28%', 'Incremento estimado', 'en ventas con la\npromoción sugerida')):
            tile = QFrame(objectName='insightTile')
            box = QVBoxLayout(tile)
            box.addWidget(QLabel(value, objectName='tileValue'))
            box.addWidget(QLabel(label, objectName='metricLabel'))
            box.addWidget(QLabel(detail, objectName='tiny'))
            row.addWidget(tile, 1)
        row.addWidget(QPushButton('Crear promoción', objectName='primaryButton'))
        return panel


class DemandView(_Page):
    PRODUCTS = (
        ('DH   Decoración\nHalloween', '32,400', '87%', 'Medio', 'Aumentar\ninventario'),
        ('AN   Árbol de Navidad', '28,600', '82%', 'Medio', 'Preparar\ncampaña'),
        ('MS   Mochila escolar', '22,100', '78%', 'Alto', 'Asegurar\nabastecimiento'),
        ('AU   Audífonos\nBluetooth', '18,500', '80%', 'Medio', 'Monitorear'),
        ('KP   Figura K-pop', '15,300', '76%', 'Medio', 'Reabastecer'),
    )

    def __init__(self, parent=None):
        super().__init__('Estimación de demanda', 'Predice la demanda futura de tus productos utilizando modelos de análisis de series de tiempo y patrones estacionales.', 'Hola, Administrador', '01/08/2025 - 31/08/2026', parent)
        self.layout.addWidget(self._filters())
        self.layout.addLayout(self._metrics())
        body = QHBoxLayout()
        body.setSpacing(12)
        chart, chart_layout = self.card('Ventas históricas vs demanda estimada')
        chart_layout.addWidget(QLabel('━  Ventas históricas      ┄  Demanda estimada      ■  Intervalo de confianza', objectName='legend'), alignment=Qt.AlignRight)
        self.forecast = _ForecastChart()
        chart_layout.addWidget(self.forecast)
        body.addWidget(chart, 5)
        body.addWidget(self._predictions(), 3)
        self.layout.addLayout(body)
        self.layout.addWidget(self._seasonality())
        self.layout.addStretch()

    def _filters(self):
        card = QFrame(objectName='card')
        card.setMinimumHeight(96)
        grid = QGridLayout(card)
        grid.setContentsMargins(15, 10, 15, 13)
        controls = (
            ('Producto', ('Decoración Halloween', 'Árbol de Navidad', 'Mochila escolar')),
            ('Categoría', ('Todas las categorías', 'Decoración', 'Escolar')),
            ('Periodo de análisis', ('Próximos 12 meses', 'Próximos 6 meses')),
        )
        self.demand_filters = []
        for col, (label, options) in enumerate(controls):
            grid.addWidget(QLabel(label, objectName='fieldLabel'), 0, col)
            combo = QComboBox()
            combo.addItems(options)
            self.demand_filters.append(combo)
            grid.addWidget(combo, 1, col)
            grid.setColumnStretch(col, 1)
        self.update_button = QPushButton('Actualizar estimación', objectName='primaryButton')
        self.update_button.clicked.connect(self._update_estimate)
        grid.addWidget(self.update_button, 1, 3)
        self.update_status = QLabel('', objectName='status')
        grid.addWidget(self.update_status, 2, 0, 1, 4)
        self.update_status.hide()
        return card

    def _metrics(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        data = (
            ('OK', GREEN, 'Precisión estimada', '87%', 'Basada en validación histórica\ndel modelo.'),
            ('MAX', PURPLE, 'Producto con mayor\ndemanda futura', 'Decoración Halloween', '+135% vs. promedio mensual'),
            ('12M', BLUE, 'Horizonte evaluado', '12 meses', 'De sep 2025 a ago 2026'),
            ('TEMP', ORANGE, 'Temporada relevante', 'Halloween', 'Pico de demanda en octubre\n2025 (+220%)'),
        )
        for icon, color, title, value, note in data:
            card = QFrame(objectName='metricCard')
            card.setMinimumHeight(144)
            line = QHBoxLayout(card)
            line.setContentsMargins(14, 13, 14, 13)
            badge = QLabel(icon)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(58, 58)
            badge.setStyleSheet(f'background:{TINTS[color]};color:{color};border-radius:13px;border:none;font-size:10px;font-weight:800;')
            line.addWidget(badge)
            copy = QVBoxLayout()
            copy.addWidget(QLabel(title, objectName='metricLabel'))
            value_label = QLabel(value, objectName='metricValue' if len(value) < 13 else 'purpleValue')
            copy.addWidget(value_label)
            note_label = QLabel(note, objectName='positive' if note.startswith('+') else 'rowCopy')
            copy.addWidget(note_label)
            line.addLayout(copy, 1)
            row.addWidget(card, 1)
        return row

    def _predictions(self):
        card, layout = self.card('Predicciones por producto', 'Ver todas')
        table = _table(self.PRODUCTS, ('Producto', 'Próximo periodo\n(unidades)', 'Confianza', 'Riesgo', 'Acción sugerida'), 306)
        for row in range(len(self.PRODUCTS)):
            table.item(row, 2).setForeground(QColor(GREEN))
            table.item(row, 3).setForeground(QColor(RED if self.PRODUCTS[row][3] == 'Alto' else ORANGE))
            table.item(row, 4).setForeground(QColor(PURPLE))
        layout.addWidget(table)
        return card

    def _update_estimate(self):
        self.update_button.setEnabled(False)
        self.update_button.setText('Actualizando...')
        self.update_status.setText(f'Estimación actualizada para {self.demand_filters[0].currentText()}')
        self.update_status.show()
        QTimer.singleShot(550, self._finish_update)

    def _finish_update(self):
        self.update_button.setEnabled(True)
        self.update_button.setText('Actualizar estimación')
        self.forecast.update()

    @staticmethod
    def _seasonality():
        card, layout = _Page.card('Información estacional relevante')
        card.setMinimumHeight(132)
        row = QHBoxLayout()
        seasons = (
            ('H', 'Halloween', 'Incremento promedio de 220% en la\ndemanda durante octubre. Se recomienda\naumentar inventario 6 semanas antes.', '#fff5ed'),
            ('N', 'Navidad', 'Crecimiento de demanda de 180% entre\nnoviembre y diciembre. Los productos de\ndecoración y regalos son los más afectados.', '#eefaf6'),
            ('R', 'Regreso a clases', 'Aumento de 150% en mochilas y papelería\nen agosto. Preparar inventario desde julio\npara cubrir la demanda.', '#f3f1ff'),
        )
        for icon, title, text, background in seasons:
            panel = QFrame(objectName='season')
            panel.setStyleSheet(f'QFrame#season{{background:{background};}}')
            line = QHBoxLayout(panel)
            badge = QLabel(icon)
            badge.setStyleSheet('font-size:16px;font-weight:800;border:none;background:transparent;')
            line.addWidget(badge)
            copy = QVBoxLayout()
            copy.addWidget(QLabel(title, objectName='rowTitle'))
            copy.addWidget(QLabel(text, objectName='rowCopy'))
            line.addLayout(copy, 1)
            row.addWidget(panel, 1)
        layout.addLayout(row)
        return card


def _table(rows, headers, minimum_height):
    table = QTableWidget(len(rows), len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().hide()
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.NoSelection)
    table.setShowGrid(False)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setMinimumHeight(minimum_height)
    table.verticalHeader().setDefaultSectionSize(max(28, int((minimum_height - 36) / max(1, len(rows)))))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if column in (0, 1, 2) else Qt.AlignCenter))
            table.setItem(row, column, item)
    return table


_STYLES = '''
    QWidget#analyticsPage, QWidget#pageContent, QScrollArea#pageScroll {
        background: #f7f9fd; color: #081433; font-family: "Sans Serif";
    }
    QScrollArea#pageScroll { border: none; }
    QScrollBar:vertical { background: #edf1f6; width: 8px; }
    QScrollBar::handle:vertical { background: #c8d1df; border-radius: 4px; min-height: 42px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QLabel#pageTitle { color: #081433; font-size: 28px; font-weight: 800; }
    QLabel#greeting { color: #081433; font-size: 19px; font-weight: 750; }
    QLabel#subtitle { color: #60708f; font-size: 12px; }
    QLabel#dateBox { color: #1b2a4a; background: white; border: 1px solid #d6dfeb; border-radius: 8px; padding: 10px 13px; font-size: 11px; }
    QLabel#bell { color: #34456b; font-size: 19px; }
    QLabel#avatar { color: #5425f5; background: #e5e0ff; border-radius: 21px; font-size: 12px; font-weight: 800; }
    QLabel#accountName { color: #081433; font-size: 12px; font-weight: 750; }
    QLabel#accountRole, QLabel#chevron { color: #64738f; font-size: 10px; }
    QFrame#card, QFrame#metricCard { background: white; border: 1px solid #dce4f0; border-radius: 9px; }
    QLabel#cardTitle { color: #0a1735; font-size: 16px; font-weight: 750; }
    QLabel#info, QLabel#link { color: #5b6e91; font-size: 10px; }
    QLabel#link { color: #5425f5; font-weight: 700; }
    QLabel#metricValue { color: #081433; font-size: 22px; font-weight: 800; }
    QLabel#metricName { color: #081433; font-size: 12px; font-weight: 750; }
    QLabel#purpleValue { color: #4215d8; font-size: 16px; font-weight: 800; }
    QLabel#metricLabel { color: #253451; font-size: 10px; font-weight: 650; }
    QLabel#rowCopy { color: #60708f; font-size: 10px; }
    QLabel#rowTitle { color: #0a1735; font-size: 11px; font-weight: 750; }
    QLabel#tiny { color: #6a7893; font-size: 9px; }
    QLabel#positive { color: #08a66c; font-size: 10px; font-weight: 700; }
    QLabel#trendGreen, QLabel#trendRed, QLabel#softChip { border: none; border-radius: 7px; padding: 5px 7px; font-size: 9px; font-weight: 700; }
    QLabel#trendGreen { color: #08a66c; background: #e9faf2; }
    QLabel#trendRed { color: #ee3157; background: #fff0f3; }
    QLabel#softChip { color: #5425f5; background: #f0edff; }
    QFrame#listItem { background: white; border: 1px solid #e0e7f0; border-radius: 8px; }
    QLabel#fieldLabel { color: #172440; font-size: 10px; font-weight: 700; }
    QComboBox { color: #22314f; background: white; border: 1px solid #d7dfeb; border-radius: 7px; padding: 8px 10px; min-height: 18px; font-size: 10px; }
    QComboBox::drop-down { border: none; width: 22px; }
    QPushButton#primaryButton { color: white; background: #5425f5; border: none; border-radius: 7px; padding: 10px 15px; font-size: 10px; font-weight: 700; }
    QPushButton#primaryButton:hover { background: #4215d8; }
    QPushButton#primaryButton:disabled { background: #a99af1; }
    QLabel#status { color: #087b4b; font-size: 8px; padding-top: 3px; }
    QTableWidget { color: #14213d; background: white; border: 1px solid #e0e6ef; border-radius: 7px; gridline-color: #e3e9f1; font-size: 9px; }
    QTableWidget::item { border-bottom: 1px solid #e6ebf2; padding: 3px; }
    QHeaderView::section { color: #12203c; background: #f3f6fa; border: none; border-right: 1px solid #e0e6ef; border-bottom: 1px solid #dce4ee; padding: 8px 4px; font-size: 9px; font-weight: 750; }
    QLabel#legend { color: #556682; font-size: 9px; }
    QFrame#insight { background: #f8f6ff; border: 1px solid #dcd5ff; border-radius: 9px; }
    QLabel#bulb { color: #5425f5; background: #e4ddff; border-radius: 26px; font-size: 30px; }
    QLabel#insightLabel { color: #5425f5; font-size: 10px; font-weight: 700; }
    QLabel#insightTitle { color: #081433; font-size: 14px; font-weight: 800; }
    QFrame#insightTile { background: white; border: none; border-radius: 7px; }
    QLabel#tileValue { color: #5425f5; font-size: 14px; font-weight: 800; }
    QFrame#season { border: 1px solid #e0e6ef; border-radius: 8px; }
'''


__all__ = ['SegmentationView', 'PurchasePatternsView', 'DemandView']
