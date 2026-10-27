from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)


INK = '#0b1739'
MUTED = '#64748b'
VIOLET = '#553cff'
BLUE = '#1479ed'
GREEN = '#08a66c'
ORANGE = '#ed7a0a'
RED = '#e9424b'


class _SalesLineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = (7, 9, 13, 11, 12, 14, 11, 8, 17, 13, 12, 8, 11, 17, 14, 18, 15, 9, 12)
        self.setMinimumHeight(145)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(38, 12, -10, -25)
        painter.setFont(QFont('Segoe UI', 7))
        for index, text in enumerate(('$0', '$5K', '$10K', '$15K', '$20K')):
            y = area.bottom() - index * area.height() / 4
            painter.setPen(QColor('#e5eaf2'))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor('#7b889e'))
            painter.drawText(QRectF(0, y - 7, 34, 14), Qt.AlignRight | Qt.AlignVCenter, text)

        step = area.width() / (len(self.values) - 1)
        points = [
            QPointF(area.left() + i * step, area.bottom() - value / 20 * area.height())
            for i, value in enumerate(self.values)
        ]
        painter.setPen(QPen(QColor(VIOLET), 2.2))
        painter.drawPolyline(points)
        for point in points:
            painter.setPen(QPen(QColor(VIOLET), 1.5))
            painter.setBrush(QColor('white'))
            painter.drawEllipse(point, 2.7, 2.7)

        painter.setPen(QColor('#64748b'))
        for index, label in enumerate(('01 Abr', '06 Abr', '11 Abr', '16 Abr', '21 Abr', '26 Abr', '30 Abr')):
            x = area.left() + index * area.width() / 6
            painter.drawText(QRectF(x - 24, area.bottom() + 6, 48, 15), Qt.AlignCenter, label)


class _SegmentDonutChart(QWidget):
    COLORS = (VIOLET, BLUE, '#22ad78', '#f39a1e', RED)
    ITEMS = (('Hogares', 36), ('Familias', 28), ('Jovenes', 18), ('Profesionales', 10), ('Seniors', 8))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(145)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(92, self.height() - 28)
        circle = QRectF(8, (self.height() - size) / 2, size, size).adjusted(9, 9, -9, -9)
        pen = QPen()
        pen.setWidth(18)
        pen.setCapStyle(Qt.FlatCap)
        start = 90 * 16
        for (_, value), color in zip(self.ITEMS, self.COLORS):
            span = -int(value / 100 * 360 * 16)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(circle, start, span)
            start += span

        legend_x = min(125, self.width() * .48)
        top = (self.height() - len(self.ITEMS) * 22) / 2
        painter.setFont(QFont('Segoe UI', 8))
        for index, ((label, value), color) in enumerate(zip(self.ITEMS, self.COLORS)):
            y = top + index * 22
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(legend_x, y + 7), 3.5, 3.5)
            painter.setPen(QColor('#344258'))
            painter.drawText(QRectF(legend_x + 10, y, self.width() - legend_x - 42, 15), Qt.AlignVCenter, label)
            painter.drawText(QRectF(self.width() - 35, y, 30, 15), Qt.AlignRight | Qt.AlignVCenter, f'{value}%')


class _CategoryBarChart(QWidget):
    ITEMS = (
        ('Alimentos y Bebidas', 98.4), ('Cuidado Personal', 67.3),
        ('Limpieza del Hogar', 45.2), ('Electronicos', 38.9), ('Bebes y Ninos', 28.9),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(145)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        label_width = min(108, self.width() * .43)
        left = label_width + 5
        right = self.width() - 45
        top = 10
        row_height = 24
        gradient = QLinearGradient(left, 0, right, 0)
        gradient.setColorAt(0, QColor('#6854f5'))
        gradient.setColorAt(1, QColor('#4933e7'))
        painter.setFont(QFont('Segoe UI', 7))
        for index, (label, value) in enumerate(self.ITEMS):
            y = top + index * row_height
            painter.setPen(QColor('#344258'))
            painter.drawText(QRectF(0, y, label_width, 14), Qt.AlignRight | Qt.AlignVCenter, label)
            width = max(4, (right - left) * value / 110)
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(left, y + 2, width, 11), 2, 2)
            painter.setPen(QColor('#344258'))
            painter.drawText(QRectF(left + width + 5, y, 42, 14), Qt.AlignVCenter, f'${value:.1f}K')

        painter.setPen(QColor('#8995a8'))
        y = top + len(self.ITEMS) * row_height + 1
        for index, text in enumerate(('0', '25K', '50K', '75K', '100K')):
            x = left + index * (right - left) / 4
            painter.drawText(QRectF(x - 13, y, 28, 14), Qt.AlignCenter, text)


class RecommendationsView(QWidget):
    """Content-only commercial recommendations page."""

    RECOMMENDATIONS = (
        {
            'icon': '%', 'color': VIOLET, 'background': '#f0edff', 'priority': 'Alta',
            'priority_color': '#d92c35', 'priority_background': '#ffe4e4',
            'title': 'Aumentar promociones en productos de alta demanda',
            'body': 'Los productos con mayor rotacion presentan alta sensibilidad al precio.\nSe recomienda impulsar promociones especificas.',
            'segment': 'Clientes frecuentes',
            'detail': 'Aplicar descuentos del 10% al 15% en los productos de mayor rotacion durante los proximos 14 dias. Prioriza canales digitales y mide conversion y margen.',
        },
        {
            'icon': 'R', 'color': GREEN, 'background': '#e7f8f1', 'priority': 'Media',
            'priority_color': '#d97800', 'priority_background': '#fff3df',
            'title': 'Fortalecer retencion de clientes inactivos',
            'body': 'Detectamos clientes con mas de 60 dias sin compras.\nReactivar con campanas personalizadas.',
            'segment': 'Clientes inactivos',
            'detail': 'Crear una campana de reactivacion en tres etapas: recordatorio, beneficio personalizado y ultimo incentivo. Excluir clientes contactados durante los ultimos 15 dias.',
        },
        {
            'icon': '+', 'color': BLUE, 'background': '#eaf3ff', 'priority': 'Baja',
            'priority_color': '#078552', 'priority_background': '#e5f7ef',
            'title': 'Impulsar asociaciones de productos complementarios',
            'body': 'Los analisis muestran oportunidades para aumentar el ticket promedio\nmediante asociaciones recomendadas.',
            'segment': 'Todos los clientes',
            'detail': 'Mostrar recomendaciones cruzadas en el punto de venta y los canales digitales. Iniciar con las cinco asociaciones de mayor confianza y revisar resultados semanalmente.',
        },
        {
            'icon': '18h', 'color': ORANGE, 'background': '#fff1e5', 'priority': 'Media',
            'priority_color': '#d97800', 'priority_background': '#fff3df',
            'title': 'Aprovechar horas pico de compra',
            'body': 'Las ventas aumentan significativamente entre 18:00 y 21:00.\nOptimiza campanas y disponibilidad en ese horario.',
            'segment': 'Todos los clientes',
            'detail': 'Concentrar inventario, personal y comunicaciones entre las 18:00 y las 21:00. Programar promociones breves para reducir la demanda en horas de menor actividad.',
        },
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('decisionPage')
        self.setStyleSheet(self._styles())
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(objectName='pageScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget(objectName='pageContent')
        content.setMinimumWidth(1040)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 26, 32, 30)
        layout.setSpacing(14)

        header = QHBoxLayout()
        headings = QVBoxLayout()
        headings.setSpacing(4)
        headings.addWidget(QLabel('Recomendaciones comerciales', objectName='pageTitle'))
        headings.addWidget(QLabel('Acciones sugeridas basadas en el analisis de datos para impulsar tus resultados.', objectName='pageSubtitle'))
        header.addLayout(headings)
        header.addStretch()
        help_button = QPushButton('?   Como funcionan', objectName='outlineButton')
        help_button.clicked.connect(self._show_help)
        header.addWidget(help_button)
        layout.addLayout(header)
        layout.addSpacing(10)

        for recommendation in self.RECOMMENDATIONS:
            layout.addWidget(self._recommendation_card(recommendation))
        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _recommendation_card(self, data):
        card = QFrame(objectName='recommendationCard')
        card.setMinimumHeight(150)
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 18, 20, 18)
        row.setSpacing(22)

        icon = QLabel(data['icon'])
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(112, 104)
        icon.setStyleSheet(
            f"background: {data['background']}; color: {data['color']}; "
            'border: none; border-radius: 12px; font-size: 28px; font-weight: 800;'
        )
        row.addWidget(icon)

        copy = QVBoxLayout()
        copy.setSpacing(7)
        copy.addWidget(QLabel(data['title'], objectName='recommendationTitle'))
        body = QLabel(data['body'], objectName='bodyText')
        body.setWordWrap(True)
        copy.addWidget(body)
        copy.addStretch()
        segment = QLabel(f"Segmento afectado:  <span style='color:{data['color']}'>{data['segment']}</span>", objectName='bodyText')
        copy.addWidget(segment)
        row.addLayout(copy, 1)

        priority = QVBoxLayout()
        priority.setSpacing(8)
        priority.addWidget(QLabel('Prioridad', objectName='priorityLabel'))
        chip = QLabel(data['priority'])
        chip.setAlignment(Qt.AlignCenter)
        chip.setFixedSize(82, 36)
        chip.setStyleSheet(
            f"background: {data['priority_background']}; color: {data['priority_color']}; "
            'border-radius: 9px; font-size: 13px; font-weight: 700;'
        )
        priority.addWidget(chip)
        priority.addStretch()
        row.addLayout(priority)
        row.addSpacing(22)

        details = QPushButton('Ver detalles   >', objectName='detailsButton')
        details.setFixedSize(148, 48)
        details.clicked.connect(lambda checked=False, item=data: self._show_details(item))
        row.addWidget(details, alignment=Qt.AlignVCenter)
        return card

    def _show_details(self, data):
        dialog = QDialog(self)
        dialog.setWindowTitle('Detalle de recomendacion')
        dialog.setMinimumWidth(480)
        dialog.setStyleSheet(self._dialog_styles())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(13)
        layout.addWidget(QLabel(data['title'], objectName='dialogTitle'))
        priority = QLabel(f"Prioridad {data['priority']}  |  {data['segment']}", objectName='dialogMeta')
        layout.addWidget(priority)
        description = QLabel(data['detail'], objectName='dialogBody')
        description.setWordWrap(True)
        description.setMinimumHeight(72)
        layout.addWidget(description)
        close = QPushButton('Entendido', objectName='primaryButton')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, alignment=Qt.AlignRight)
        dialog.exec()

    def _show_help(self):
        QMessageBox.information(
            self, 'Como funcionan',
            'Las recomendaciones combinan tendencias de venta, segmentos y patrones de compra. '
            'La prioridad estima el impacto y la urgencia de cada accion.',
        )

    @staticmethod
    def _dialog_styles():
        return '''
            QDialog { background: white; color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; }
            QLabel#dialogTitle { font-size: 17px; font-weight: 800; }
            QLabel#dialogMeta { color: #553cff; font-size: 11px; font-weight: 700; }
            QLabel#dialogBody { color: #52617a; font-size: 12px; }
            QPushButton#primaryButton { color: white; background: #553cff; border: none; border-radius: 7px; padding: 9px 18px; font-weight: 700; }
            QPushButton#primaryButton:hover { background: #442be8; }
        '''

    @staticmethod
    def _styles():
        return '''
            QWidget#decisionPage, QWidget#pageContent, QScrollArea#pageScroll { background: #f8faff; color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; }
            QScrollArea#pageScroll { border: none; }
            QScrollBar:vertical { background: #f2f5fa; width: 8px; }
            QScrollBar::handle:vertical { background: #cad3e0; border-radius: 4px; min-height: 40px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLabel#pageTitle { color: #09142f; font-size: 24px; font-weight: 800; }
            QLabel#pageSubtitle { color: #64748b; font-size: 12px; }
            QPushButton#outlineButton { color: #553cff; background: white; border: 1px solid #d7ddea; border-radius: 7px; padding: 9px 13px; font-size: 11px; }
            QPushButton#outlineButton:hover { background: #f2efff; border-color: #7764ff; }
            QFrame#recommendationCard { background: white; border: 1px solid #dfe5ee; border-radius: 10px; }
            QLabel#recommendationTitle { color: #0b1739; font-size: 15px; font-weight: 750; }
            QLabel#bodyText { color: #64748b; font-size: 11px; }
            QLabel#priorityLabel { color: #1e293b; font-size: 11px; }
            QPushButton#detailsButton { color: #553cff; background: white; border: 1px solid #684fff; border-radius: 8px; font-size: 13px; }
            QPushButton#detailsButton:hover { color: white; background: #553cff; }
        '''


class ReportsView(QWidget):
    """Content-only reports page with filters, preview, and export actions."""

    REPORT_TYPES = (
        ('G', 'Informe general de ventas', 'Resumen completo de ventas, ingresos y productos más vendidos.', VIOLET, '#f0edff'),
        ('S', 'Inventario y stock crítico', 'Estado del inventario, productos críticos y rotación de stock.', GREEN, '#e9f8f1'),
        ('C', 'Predicción de demanda', 'Proyecciones de demanda por producto y temporada.', BLUE, '#eaf3ff'),
        ('P', 'Promociones recomendadas', 'Análisis de efectividad y sugerencias de promociones.', ORANGE, '#fff1e5'),
        ('%', 'Planificación de abastecimiento', 'Recomendaciones y planificación de reabastecimiento.', RED, '#ffedf0'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('reportsPage')
        self.setStyleSheet(self._styles())
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(objectName='reportsScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget(objectName='reportsContent')
        content.setMinimumWidth(1080)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(QLabel('Reportes', objectName='reportPageTitle'))
        layout.addWidget(QLabel('Genera y visualiza reportes personalizados para analizar el desempeño de tu negocio.', objectName='reportSubtitle'))

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self._build_type_panel())

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self._build_filters())
        right.addWidget(self._build_preview())
        body.addLayout(right, 1)
        layout.addLayout(body)
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_type_panel(self):
        panel = QFrame(objectName='panel')
        panel.setFixedWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 14)
        layout.setSpacing(8)
        layout.addWidget(QLabel('Tipos de reportes', objectName='sectionTitle'))
        layout.addWidget(QLabel('Selecciona el tipo de reporte que deseas generar.', objectName='smallText'))
        layout.addSpacing(4)

        self.type_group = QButtonGroup(self)
        self.type_group.setExclusive(True)
        for index, (icon, title, description, color, background) in enumerate(self.REPORT_TYPES):
            button = QPushButton(objectName='reportType')
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(72)
            button.setProperty('report_index', index)
            button.clicked.connect(lambda checked=False, item=index: self._select_report(item))
            button_layout = QHBoxLayout(button)
            button_layout.setContentsMargins(10, 8, 8, 8)
            button_layout.setSpacing(9)
            badge = QLabel(icon)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(34, 34)
            badge.setStyleSheet(f'background:{background}; color:{color}; border:none; border-radius:8px; font-size:14px; font-weight:800;')
            button_layout.addWidget(badge)
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(QLabel(title, objectName='typeTitle'))
            copy = QLabel(description, objectName='typeCopy')
            copy.setWordWrap(True)
            text.addWidget(copy)
            button_layout.addLayout(text, 1)
            self.type_group.addButton(button, index)
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)

        layout.addStretch()
        help_box = QFrame(objectName='helpBox')
        help_layout = QHBoxLayout(help_box)
        help_layout.setContentsMargins(10, 9, 10, 9)
        help_layout.addWidget(QLabel('?', objectName='helpIcon'))
        help_text = QVBoxLayout()
        help_text.setSpacing(1)
        help_text.addWidget(QLabel('Necesitas ayuda?', objectName='helpTitle'))
        help_text.addWidget(QLabel('Consulta nuestra guia de reportes', objectName='smallText'))
        help_layout.addLayout(help_text, 1)
        layout.addWidget(help_box)
        return panel

    def _build_filters(self):
        panel = QFrame(objectName='panel')
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        self.date_filter = self._filter_box('Rango de fechas', ('01/04/2025 - 30/04/2025', '01/03/2025 - 31/03/2025', 'Este ano'))
        self.store_filter = self._filter_box('Tienda', ('Todas las tiendas', 'Centro', 'Norte', 'Online'))
        self.segment_filter = self._filter_box('Segmento', ('Todos los segmentos', 'Hogares', 'Familias', 'Jovenes'))
        layout.addLayout(self.date_filter[0], 1)
        layout.addLayout(self.store_filter[0], 1)
        layout.addLayout(self.segment_filter[0], 1)
        generate = QPushButton('Generar reporte', objectName='generateButton')
        generate.clicked.connect(self._generate_report)
        layout.addWidget(generate, alignment=Qt.AlignBottom)
        return panel

    @staticmethod
    def _filter_box(label, items):
        wrapper = QVBoxLayout()
        wrapper.setSpacing(4)
        wrapper.addWidget(QLabel(label, objectName='filterLabel'))
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumWidth(150)
        wrapper.addWidget(combo)
        return wrapper, combo

    def _build_preview(self):
        preview = QFrame(objectName='preview')
        layout = QVBoxLayout(preview)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        heading = QFrame(objectName='previewHeading')
        heading_layout = QHBoxLayout(heading)
        heading_layout.setContentsMargins(18, 14, 18, 12)
        title = QVBoxLayout()
        title.setSpacing(2)
        self.preview_title = QLabel(self.REPORT_TYPES[0][1], objectName='previewTitle')
        self.preview_subtitle = QLabel('Resumen ejecutivo del 01 de abril al 30 de abril de 2025', objectName='reportSubtitle')
        title.addWidget(self.preview_title)
        title.addWidget(self.preview_subtitle)
        heading_layout.addLayout(title)
        heading_layout.addStretch()
        brand = QLabel('FLAMAR\nA N A L Y T I C S', objectName='reportBrand')
        brand.setAlignment(Qt.AlignCenter)
        heading_layout.addWidget(brand)
        layout.addWidget(heading)

        report_body = QWidget(objectName='previewBody')
        body = QVBoxLayout(report_body)
        body.setContentsMargins(18, 14, 18, 16)
        body.setSpacing(12)

        summary = QHBoxLayout()
        copy = QVBoxLayout()
        copy.addWidget(QLabel('Resumen ejecutivo', objectName='sectionTitle'))
        paragraph = QLabel(
            'Durante el periodo seleccionado, se analizaron los comportamientos de compra y la actividad de los consumidores. '
            'A continuacion se presentan los indicadores clave y hallazgos principales.', objectName='summaryText',
        )
        paragraph.setWordWrap(True)
        paragraph.setFixedWidth(205)
        copy.addWidget(paragraph)
        copy.addStretch()
        summary.addLayout(copy)

        metrics = (
            ('Ventas totales', '$25,430', '12%'), ('Ingresos estimados', '$320,850', '8%'),
            ('Productos vendidos', '3,450', '4%'), ('Margen promedio', '92.9%', '6%'),
        )
        for label, value, change in metrics:
            summary.addWidget(self._metric_card(label, value, change), 1)
        body.addLayout(summary)

        charts = QHBoxLayout()
        charts.setSpacing(10)
        charts.addWidget(self._chart_card('Ventas diarias', 'Evolucion de ventas en el periodo', _SalesLineChart()), 1)
        charts.addWidget(self._chart_card('Distribucion por segmento', 'Participacion de ventas por segmento', _SegmentDonutChart()), 1)
        charts.addWidget(self._chart_card('Top 5 categorias por ventas', 'Ventas totales por categoria', _CategoryBarChart()), 1)
        body.addLayout(charts)
        body.addWidget(self._findings())
        layout.addWidget(report_body)

        actions = QFrame(objectName='actions')
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(16, 12, 16, 12)
        action_layout.setSpacing(28)
        for text, name, handler in (
            ('Exportar PDF', 'pdfButton', lambda: self._export('PDF', 'pdf')),
            ('Exportar Excel', 'excelButton', lambda: self._export('Excel', 'xlsx')),
            ('Imprimir', 'printButton', self._print_report),
        ):
            button = QPushButton(text, objectName=name)
            button.clicked.connect(handler)
            action_layout.addWidget(button, 1)
        layout.addWidget(actions)

        self.status_label = QLabel('', objectName='statusLabel')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        return preview

    @staticmethod
    def _metric_card(label, value, change):
        card = QFrame(objectName='metricCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(6)
        title = QLabel(label, objectName='metricLabel')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        number = QLabel(value, objectName='metricValue')
        number.setAlignment(Qt.AlignCenter)
        layout.addWidget(number)
        delta = QLabel(f'+ {change}  vs. periodo anterior', objectName='metricChange')
        delta.setAlignment(Qt.AlignCenter)
        layout.addWidget(delta)
        return card

    @staticmethod
    def _chart_card(title, subtitle, chart):
        card = QFrame(objectName='chartCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 9, 10, 8)
        layout.setSpacing(2)
        layout.addWidget(QLabel(title, objectName='chartTitle'))
        layout.addWidget(QLabel(subtitle, objectName='chartSubtitle'))
        layout.addWidget(chart, 1)
        return card

    @staticmethod
    def _findings():
        panel = QFrame(objectName='findings')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(QLabel('  Hallazgos principales', objectName='findingsTitle'))
        grid = QGridLayout()
        findings = (
            'Las ventas totales aumentaron un 15.7% en comparacion con el periodo anterior.',
            'La categoria Alimentos y Bebidas representa el 30.7% del total de ventas.',
            'El segmento Hogares lidera en participacion con el 36% de las ventas totales.',
            'El ticket promedio muestra un crecimiento del 5.3% respecto al periodo anterior.',
        )
        for index, finding in enumerate(findings):
            grid.addWidget(QLabel(f'+  {finding}', objectName='findingText'), index // 2, index % 2)
        layout.addLayout(grid)
        return panel

    def _select_report(self, index):
        self.preview_title.setText(self.REPORT_TYPES[index][1])
        self._show_status(f'Reporte seleccionado: {self.REPORT_TYPES[index][1]}')

    def _generate_report(self):
        selected = self.type_group.checkedId()
        self.preview_title.setText(self.REPORT_TYPES[selected][1])
        date_text = self.date_filter[1].currentText()
        self.preview_subtitle.setText(f'Resumen ejecutivo | {date_text}')
        self._show_status(
            f'Reporte actualizado para {self.store_filter[1].currentText()} y {self.segment_filter[1].currentText()}.'
        )

    def _export(self, format_name, extension):
        default_name = Path.home() / f'reporte_flamar.{extension}'
        filters = f'{format_name} (*.{extension})'
        filename, _ = QFileDialog.getSaveFileName(self, f'Exportar {format_name}', str(default_name), filters)
        if filename:
            self._show_status(f'Ruta seleccionada para {format_name}: {filename}')

    def _print_report(self):
        self._show_status('Vista de impresion preparada correctamente.')
        QMessageBox.information(self, 'Imprimir reporte', 'El reporte esta listo para enviarse a la impresora.')

    def _show_status(self, message):
        self.status_label.setText(message)
        self.status_label.setVisible(True)

    @staticmethod
    def _styles():
        return '''
            QWidget#reportsPage, QWidget#reportsContent, QScrollArea#reportsScroll { background: #f8faff; color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; }
            QScrollArea#reportsScroll { border: none; }
            QScrollBar:vertical { background: #f2f5fa; width: 8px; }
            QScrollBar::handle:vertical { background: #cad3e0; border-radius: 4px; min-height: 40px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLabel#reportPageTitle { color: #09142f; font-size: 23px; font-weight: 800; }
            QLabel#reportSubtitle { color: #64748b; font-size: 10px; }
            QFrame#panel, QFrame#preview { background: white; border: 1px solid #dfe5ee; border-radius: 9px; }
            QLabel#sectionTitle { color: #111827; font-size: 12px; font-weight: 750; }
            QLabel#smallText { color: #64748b; font-size: 8px; }
            QPushButton#reportType { background: white; border: 1px solid #e1e6ef; border-radius: 8px; text-align: left; }
            QPushButton#reportType:hover { background: #faf9ff; border-color: #c1b8ff; }
            QPushButton#reportType:checked { background: #fbfaff; border: 1px solid #715cff; }
            QLabel#typeTitle { color: #111827; font-size: 9px; font-weight: 750; border: none; background: transparent; }
            QLabel#typeCopy { color: #52617a; font-size: 8px; border: none; background: transparent; }
            QFrame#helpBox { background: #fbfcff; border: 1px solid #e3e8f0; border-radius: 8px; }
            QLabel#helpIcon { color: #553cff; background: #efecff; border-radius: 13px; font-weight: 800; padding: 4px 8px; }
            QLabel#helpTitle { color: #111827; font-size: 9px; font-weight: 700; }
            QLabel#filterLabel { color: #111827; font-size: 9px; font-weight: 700; }
            QComboBox { color: #26324a; background: white; border: 1px solid #d9e0ea; border-radius: 7px; padding: 8px 10px; font-size: 9px; }
            QComboBox:hover { border-color: #806eff; }
            QComboBox::drop-down { border: none; width: 22px; }
            QPushButton#generateButton { color: white; background: #553cff; border: none; border-radius: 7px; padding: 10px 17px; font-size: 9px; font-weight: 700; }
            QPushButton#generateButton:hover { background: #442be8; }
            QFrame#previewHeading { background: white; border: none; border-bottom: 1px solid #e5e9f0; }
            QLabel#previewTitle { color: #09142f; font-size: 17px; font-weight: 800; }
            QLabel#reportBrand { color: #553cff; font-size: 12px; font-weight: 800; }
            QWidget#previewBody { background: white; }
            QLabel#summaryText { color: #52617a; font-size: 8px; }
            QFrame#metricCard, QFrame#chartCard { background: white; border: 1px solid #e2e7ef; border-radius: 8px; }
            QLabel#metricLabel { color: #344258; font-size: 8px; }
            QLabel#metricValue { color: #0b1739; font-size: 17px; font-weight: 800; }
            QLabel#metricChange { color: #08a66c; font-size: 7px; font-weight: 650; }
            QLabel#chartTitle { color: #111827; font-size: 9px; font-weight: 750; }
            QLabel#chartSubtitle { color: #64748b; font-size: 7px; }
            QFrame#findings { background: #f8f7ff; border: 1px solid #dcd6ff; border-radius: 8px; }
            QLabel#findingsTitle { color: #553cff; font-size: 9px; font-weight: 750; }
            QLabel#findingText { color: #43516a; font-size: 8px; padding: 2px; }
            QFrame#actions { background: white; border: none; border-top: 1px solid #e5e9f0; }
            QPushButton#pdfButton, QPushButton#excelButton, QPushButton#printButton { color: white; border: none; border-radius: 6px; padding: 10px; font-size: 10px; font-weight: 700; }
            QPushButton#pdfButton { background: #ea3f49; }
            QPushButton#pdfButton:hover { background: #d42f39; }
            QPushButton#excelButton { background: #079557; }
            QPushButton#excelButton:hover { background: #087b4b; }
            QPushButton#printButton { background: #3267e9; }
            QPushButton#printButton:hover { background: #2455c9; }
            QLabel#statusLabel { color: #087b4b; background: #effaf5; border-top: 1px solid #d6eee3; padding: 7px; font-size: 8px; }
        '''
