"""Content-only intelligence dashboards matching the FLAMAR reference designs."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


INK = "#0b1647"
TEXT = "#243568"
MUTED = "#6473a1"
PURPLE = "#5b32f5"
BLUE = "#2478f3"
GREEN = "#0a9f67"
PINK = "#f12678"
ORANGE = "#f27b15"
BORDER = "#dfe4f2"


def _label(text, name=None, wrap=False, alignment=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    if alignment is not None:
        widget.setAlignment(alignment)
    return widget


def _badge(text, foreground, background, width=None):
    badge = QLabel(text)
    badge.setAlignment(Qt.AlignCenter)
    badge.setFixedHeight(23)
    if width:
        badge.setFixedWidth(width)
    badge.setStyleSheet(
        f"color:{foreground}; background:{background}; border:0; border-radius:5px; "
        "font-size:10px; font-weight:700; padding:0 7px;"
    )
    return badge


def _icon(text, color=PURPLE, background="#eee9ff", size=44, font_size=22):
    icon = QLabel(text)
    icon.setAlignment(Qt.AlignCenter)
    icon.setFixedSize(size, size)
    icon.setStyleSheet(
        f"color:{color}; background:{background}; border:0; border-radius:10px; "
        f"font-family:'Segoe UI Emoji'; font-size:{font_size}px; font-weight:800;"
    )
    return icon


def _button(text):
    button = QPushButton(text)
    button.setObjectName("outlineButton")
    button.setCursor(Qt.PointingHandCursor)
    button.setMinimumHeight(21)
    return button


def _interest(value):
    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(value)
    progress.setFormat(f"{value}%")
    progress.setTextVisible(True)
    progress.setStyleSheet(
        "QProgressBar { color:#243568; background:#eceaf8; border:0; border-radius:5px; "
        "text-align:right; padding-right:2px; font-size:9px; }"
        "QProgressBar::chunk { background:#6134f4; border-radius:5px; margin-right:30px; }"
    )
    return progress


def _panel(title, subtitle="", icon=None, link=None):
    panel = QFrame()
    panel.setObjectName("panel")
    outer = QVBoxLayout(panel)
    outer.setContentsMargins(12, 10, 12, 10)
    outer.setSpacing(8)
    heading = QHBoxLayout()
    heading.setSpacing(9)
    if icon:
        heading.addWidget(_icon(icon[0], icon[1], icon[2], 36, 18))
    copy = QVBoxLayout()
    copy.setSpacing(1)
    copy.addWidget(_label(title, "sectionTitle"))
    if subtitle:
        copy.addWidget(_label(subtitle, "sectionSubtitle"))
    heading.addLayout(copy)
    heading.addStretch()
    if link:
        heading.addWidget(_label(link, "link"), alignment=Qt.AlignTop)
    outer.addLayout(heading)
    return panel, outer


class _MultiLineChart(QWidget):
    """Smooth, filled multi-series line chart used by calendar and trends."""

    def __init__(self, series, labels, maximum, y_labels, legend=(), parent=None):
        super().__init__(parent)
        self.series = series
        self.labels = labels
        self.maximum = maximum
        self.y_labels = y_labels
        self.legend = legend
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        legend_h = 18 if self.legend else 0
        area = self.rect().adjusted(44, 8 + legend_h, -8, -24)
        painter.setFont(QFont("Segoe UI", 7))
        if self.legend:
            x = area.left()
            for text, color in self.legend:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(color))
                painter.drawEllipse(QPointF(x + 4, 8), 4, 4)
                painter.setPen(QColor(TEXT))
                painter.drawText(QRectF(x + 12, 0, 105, 16), Qt.AlignVCenter, text)
                x += 120
        for index, text in enumerate(self.y_labels):
            y = area.bottom() - index * area.height() / max(1, len(self.y_labels) - 1)
            painter.setPen(QPen(QColor("#e7eaf3"), 1))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(0, y - 7, 39, 14), Qt.AlignRight | Qt.AlignVCenter, text)
        for index, label in enumerate(self.labels):
            x = area.left() + index * area.width() / max(1, len(self.labels) - 1)
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(x - 22, area.bottom() + 5, 44, 16), Qt.AlignCenter, label)

        for values, color in self.series:
            points = [
                QPointF(
                    area.left() + i * area.width() / max(1, len(values) - 1),
                    area.bottom() - value / self.maximum * area.height(),
                )
                for i, value in enumerate(values)
            ]
            path = QPainterPath(points[0])
            for i in range(1, len(points)):
                previous, point = points[i - 1], points[i]
                middle = (previous.x() + point.x()) / 2
                path.cubicTo(middle, previous.y(), middle, point.y(), point.x(), point.y())
            fill = QPainterPath(path)
            fill.lineTo(points[-1].x(), area.bottom())
            fill.lineTo(points[0].x(), area.bottom())
            fill.closeSubpath()
            gradient = QLinearGradient(0, area.top(), 0, area.bottom())
            top = QColor(color)
            top.setAlpha(38)
            bottom = QColor(color)
            bottom.setAlpha(3)
            gradient.setColorAt(0, top)
            gradient.setColorAt(1, bottom)
            painter.fillPath(fill, gradient)
            painter.setPen(QPen(QColor(color), 1.8))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)


class _SalesBars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = (11, 15, 17, 20, 23, 25)
        self.recommended = (15, 24, 28, 32, 34, 37)
        self.labels = ("Ago", "Sep", "Oct", "Nov", "Dic", "Ene")
        self.setMinimumHeight(145)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(46, 25, -8, -24)
        painter.setFont(QFont("Segoe UI", 7))
        for i, text in enumerate(("$0", "$10,000", "$20,000", "$30,000", "$40,000")):
            y = area.bottom() - i * area.height() / 4
            painter.setPen(QPen(QColor("#e7eaf3"), 1))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(0, y - 7, 42, 14), Qt.AlignRight, text)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#dcd7f9"))
        painter.drawRect(QRectF(area.left(), 4, 8, 8))
        painter.setPen(QColor(TEXT))
        painter.drawText(QRectF(area.left() + 12, 1, 90, 14), "Ventas actuales")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#7139ed"))
        painter.drawRect(QRectF(area.left() + 105, 4, 8, 8))
        painter.setPen(QColor(TEXT))
        painter.drawText(QRectF(area.left() + 117, 1, 145, 14), "Ventas con recomendaciones")
        slot = area.width() / 6
        for index, (current, recommended) in enumerate(zip(self.current, self.recommended)):
            x = area.left() + index * slot + slot * .25
            for offset, value, color in ((0, current, "#dcd7f9"), (slot * .23, recommended, "#7139ed")):
                height = value / 40 * area.height()
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(color))
                painter.drawRect(QRectF(x + offset, area.bottom() - height, slot * .2, height))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(area.left() + index * slot, area.bottom() + 5, slot, 15), Qt.AlignCenter, self.labels[index])


class _BaseIntelligenceView(QWidget):
    TITLE = ""
    SUBTITLE = ""
    PAGE_ICON = ""
    PAGE_COLOR = PURPLE
    PAGE_BACKGROUND = "#eee9ff"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("intelligencePage")
        self.setStyleSheet(self._styles())
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._top_bar())
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("pageContent")
        content.setMinimumWidth(0)
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(18, 14, 18, 18)
        self.content_layout.setSpacing(10)
        self.content_layout.addLayout(self._title_row())
        self._build_content(self.content_layout)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _top_bar(self):
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(50)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 6, 24, 6)
        layout.addStretch()
        date = QPushButton("📅   01/08/2025 - 31/08/2025     ⌄")
        date.setObjectName("dateButton")
        date.setFixedSize(225, 35)
        layout.addWidget(date)
        bell = QLabel("🔔")
        bell.setObjectName("bell")
        bell.setAlignment(Qt.AlignCenter)
        bell.setFixedWidth(48)
        layout.addWidget(bell)
        avatar = QLabel("AA")
        avatar.setObjectName("avatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(38, 38)
        layout.addWidget(avatar)
        account = QVBoxLayout()
        account.setSpacing(0)
        account.addWidget(_label("Administrador", "accountName"))
        account.addWidget(_label("Administrador", "accountRole"))
        layout.addLayout(account)
        layout.addSpacing(24)
        layout.addWidget(_label("⌄", "accountName"))
        return bar

    def _title_row(self):
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(_icon(self.PAGE_ICON, self.PAGE_COLOR, self.PAGE_BACKGROUND, 68, 30))
        copy = QVBoxLayout()
        copy.setSpacing(1)
        copy.addWidget(_label(self.TITLE, "pageTitle"))
        subtitle = _label(self.SUBTITLE, "pageSubtitle", True)
        subtitle.setMinimumWidth(0)
        subtitle.setMaximumWidth(1000)
        copy.addWidget(subtitle)
        row.addLayout(copy)
        row.addStretch()
        return row

    def _metrics(self, items):
        row = QHBoxLayout()
        row.setSpacing(10)
        for icon, color, background, value, title, note, delta, delta_color in items:
            card = QFrame()
            card.setObjectName("metricCard")
            card.setFixedHeight(92)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(11)
            card_layout.addWidget(_icon(icon, color, background, 50, 23))
            copy = QVBoxLayout()
            copy.setSpacing(1)
            copy.addWidget(_label(value, "metricValue"))
            copy.addWidget(_label(title, "metricTitle"))
            copy.addWidget(_label(note, "metricNote"))
            card_layout.addLayout(copy, 1)
            change = QVBoxLayout()
            change.addWidget(_badge(f"↑ {delta}", delta_color, "#e5f8ef" if delta_color == GREEN else "#ffe7ef"))
            change.addWidget(_label("vs. período anterior", "tinyText", alignment=Qt.AlignCenter))
            change.addStretch()
            card_layout.addLayout(change)
            row.addWidget(card, 1)
        return row

    @staticmethod
    def _table(headers, rows, widths=None, row_height=42):
        table = QTableWidget(len(rows), len(headers))
        table.setObjectName("dataTable")
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide()
        table.setShowGrid(False)
        table.setFocusPolicy(Qt.NoFocus)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if widths:
            for index, width in enumerate(widths):
                table.horizontalHeader().setSectionResizeMode(index, QHeaderView.Interactive)
                table.setColumnWidth(index, width)
            table.horizontalHeader().setStretchLastSection(True)
        for row_index, row in enumerate(rows):
            table.setRowHeight(row_index, row_height)
            for column, value in enumerate(row):
                if isinstance(value, QWidget):
                    holder = QWidget()
                    holder.setStyleSheet("background:transparent;")
                    holder_layout = QHBoxLayout(holder)
                    holder_layout.setContentsMargins(2, 2, 2, 2)
                    holder_layout.addWidget(value)
                    table.setCellWidget(row_index, column, holder)
                else:
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if column > 0 else Qt.AlignLeft))
                    table.setItem(row_index, column, item)
        table.setFixedHeight(31 + len(rows) * row_height + 2)
        return table

    @staticmethod
    def _product_card(icon, title, subtitle, status, status_color=GREEN, status_bg="#e1f8ed"):
        card = QFrame()
        card.setObjectName("productCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        picture = QLabel(icon)
        picture.setAlignment(Qt.AlignCenter)
        picture.setFixedHeight(45)
        picture.setStyleSheet("font-size:31px; border:0; background:#fbfcff; border-radius:6px;")
        layout.addWidget(picture)
        layout.addWidget(_label(title, "productTitle", True, Qt.AlignCenter))
        layout.addWidget(_label(subtitle, "productSubtitle", True, Qt.AlignCenter))
        layout.addWidget(_badge(status, status_color, status_bg))
        return card

    def _build_content(self, layout):
        raise NotImplementedError

    @staticmethod
    def _styles():
        return """
            QWidget#intelligencePage, QWidget#pageContent, QScrollArea#pageScroll {
                background:#f9faff; color:#0b1647; font-family:"Segoe UI Variable", "Segoe UI";
            }
            QFrame#topBar { background:#fbfbff; border-bottom:1px solid #e0e4ef; }
            QPushButton#dateButton { color:#17285d; background:white; border:1px solid #d5dcef; border-radius:9px; font-size:11px; text-align:left; padding-left:12px; }
            QLabel#bell { color:#314173; font-size:23px; }
            QLabel#avatar { color:#5634ed; background:#e9e3ff; border-radius:19px; font-size:13px; font-weight:800; }
            QLabel#accountName { color:#101b46; font-size:11px; font-weight:750; }
            QLabel#accountRole { color:#61709b; font-size:9px; }
            QLabel#pageTitle { color:#091447; font-size:27px; font-weight:800; }
            QLabel#pageSubtitle { color:#6173a7; font-size:12px; }
            QFrame#metricCard, QFrame#panel, QFrame#productCard { background:white; border:1px solid #dfe4f2; border-radius:9px; }
            QLabel#metricValue { color:#091447; font-size:20px; font-weight:800; }
            QLabel#metricTitle { color:#142353; font-size:11px; font-weight:650; }
            QLabel#metricNote, QLabel#tinyText { color:#7080aa; font-size:8px; }
            QLabel#sectionTitle { color:#101b4c; font-size:14px; font-weight:800; }
            QLabel#sectionSubtitle { color:#6475a7; font-size:10px; }
            QLabel#link { color:#5029f2; font-size:10px; font-weight:750; }
            QLabel#productTitle { color:#111c48; font-size:10px; font-weight:750; }
            QLabel#productSubtitle { color:#6373a0; font-size:9px; }
            QPushButton#outlineButton { color:#4c2af2; background:white; border:1px solid #bcaeff; border-radius:6px; padding:2px 7px; font-size:9px; font-weight:650; }
            QPushButton#outlineButton:hover { background:#f0edff; }
            QTableWidget#dataTable { color:#263762; background:white; border:1px solid #e2e6f0; border-radius:7px; font-size:10px; gridline-color:#e6e9f2; }
            QTableWidget#dataTable::item { border-bottom:1px solid #e8ebf3; padding:3px; }
            QHeaderView::section { color:#142250; background:#fafbfe; border:0; border-bottom:1px solid #dfe4ee; padding:6px; font-size:9px; font-weight:750; }
            QComboBox { color:#243568; background:white; border:1px solid #d9dfed; border-radius:6px; padding:6px 10px; font-size:9px; }
            QScrollArea#pageScroll { border:0; }
            QScrollBar:vertical { width:8px; background:#f1f3f9; }
            QScrollBar::handle:vertical { background:#cbd2e2; border-radius:4px; min-height:40px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """


class CalendarView(_BaseIntelligenceView):
    TITLE = "Calendario comercial"
    SUBTITLE = "Planifica tus campañas de temporada y organiza tus compras con anticipación\npara maximizar tus ventas."
    PAGE_ICON = "📅"
    PAGE_COLOR = PINK
    PAGE_BACKGROUND = "#ffe8f1"

    def _build_content(self, layout):
        layout.addLayout(self._metrics((
            ("📅", PURPLE, "#eee9ff", "6", "Temporadas activas", "En los próximos 12 meses", "20%", GREEN),
            ("🛒", GREEN, "#e5f8ef", "$ 18,450", "Compra anticipada sugerida", "Valor estimado de inventario", "18%", GREEN),
            ("🔔", PINK, "#ffe8f1", "5", "Alertas de compra", "Productos por adquirir", "67%", PINK),
            ("📦", BLUE, "#e8f0ff", "127", "Productos estacionales", "En temporadas activas", "32%", GREEN),
        )))

        body = QHBoxLayout()
        body.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(10)
        seasons, seasons_layout = _panel(
            "Calendario de temporadas comerciales  ⓘ",
            "Fechas clave, recomendaciones y acciones para planificar tu inventario y campañas.",
        )
        combo = QComboBox()
        combo.addItem("Próximos 12 meses")
        combo.setFixedWidth(145)
        seasons.layout().itemAt(0).layout().addWidget(combo)
        season_rows = (
            ("OCT 31   🎃  Halloween", "01 - 15 oct", "15 - 20 oct", "Disfraces, decoración,\ndulces, artículos de fiesta", _button("Ver detalles  ›")),
            ("AGO 30   🎒  Regreso a clases", "01 - 15 ago", "20 - 25 ago", "Mochilas, cuadernos,\nplumones, uniformes", _button("Ver detalles  ›")),
            ("MAY 10   🌷  Día de la Madre", "15 - 30 abr", "01 - 05 may", "Regalos, cosméticos,\njoyería, cuidado personal", _button("Ver detalles  ›")),
            ("DIC 25   🎄  Navidad", "01 - 15 dic", "20 - 25 nov", "Decoración, juguetes,\nregalos, electrónica", _button("Ver detalles  ›")),
            ("SEP 16   🇲🇽  Fiestas Patrias", "01 - 15 sep", "05 - 10 sep", "Decoración, artículos patrios,\nropa, alimentos típicos", _button("Ver detalles  ›")),
            ("ENE 15   ☀️  Verano", "01 - 15 ene", "20 - 25 ene", "Ropa de verano, trajes de baño,\nlentes, accesorios de playa", _button("Ver detalles  ›")),
        )
        seasons_layout.addWidget(self._table(
            ("Temporada / Evento", "Fecha clave", "Revisar antes", "Productos / Categorías sugeridas", "Acciones"),
            season_rows, (190, 92, 100, 175, 90), 73,
        ))
        left.addWidget(seasons)
        history, history_layout = _panel("Análisis de ventas históricas", "Desempeño de ventas en temporadas anteriores.", ("📊", PURPLE, "#eee9ff"))
        history_chart = _MultiLineChart(
            (((12, 16, 38, 12, 15, 42, 37, 43, 38, 53, 47, 15), BLUE),
             ((10, 13, 16, 18, 22, 16, 17, 22, 50, 25, 20, 13), PURPLE),
             ((8, 10, 12, 31, 49, 18, 17, 20, 22, 18, 69, 30), PINK)),
            ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"),
            75, ("$0", "$20,000", "$40,000", "$60,000"),
            (("2023", BLUE), ("2024", PURPLE), ("2025", PINK)),
        )
        history_chart.setMinimumHeight(70)
        history_layout.addWidget(history_chart)
        left.addWidget(history)

        right = QVBoxLayout()
        right.setSpacing(10)
        suggestions, suggestion_layout = _panel("Productos sugeridos por temporada", "Productos recomendados según la temporada seleccionada.", ("📊", PURPLE, "#eee9ff"), "Ver todos")
        tabs = QHBoxLayout()
        for index, tab in enumerate(("Halloween", "Regreso a clases", "Día de la Madre", "Navidad", "Fiestas Patrias", "Verano")):
            label = _badge(tab, "white" if index == 0 else TEXT, PURPLE if index == 0 else "#f3f2fa")
            tabs.addWidget(label, 1)
        suggestion_layout.addLayout(tabs)
        products = QHBoxLayout()
        products.setSpacing(6)
        for item in (
            ("🧙", "Sombrero de bruja", "Disfraces", "Alta demanda", GREEN, "#e1f8ed"),
            ("🎃", "Calabaza decorativa", "Decoración", "Alta demanda", GREEN, "#e1f8ed"),
            ("💄", "Kit de maquillaje", "Artículos de fiesta", "Demanda media", ORANGE, "#fff1dd"),
            ("💀", "Disfraz esqueleto", "Disfraces", "Alta demanda", GREEN, "#e1f8ed"),
            ("🕷️", "Decoración araña", "Decoración", "Demanda media", ORANGE, "#fff1dd"),
        ):
            products.addWidget(self._product_card(*item), 1)
        suggestion_layout.addLayout(products)
        right.addWidget(suggestions)

        alerts, alerts_layout = _panel("Alertas de compra anticipada", "Productos que debes adquirir antes de la temporada.", ("🔔", PINK, "#ffe8f1"), "Ver todas")
        alert_rows = (
            ("Disfraz de superhéroe", "Halloween", "12", "100", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Comprar")),
            ("Mochila escolar", "Regreso a clases", "25", "150", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Comprar")),
            ("Juego de luces navideñas", "Navidad", "8", "80", _badge("Sin stock", PINK, "#ffe5ed"), _button("Comprar")),
            ("Bloques de construcción", "Navidad", "32", "120", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Comprar")),
        )
        alerts_layout.addWidget(self._table(("Producto", "Temporada", "Stock actual", "Stock sugerido", "Estado", "Acción"), alert_rows, row_height=29))
        right.addWidget(alerts)
        quick, quick_layout = _panel("Recomendaciones rápidas", "Sugerencias basadas en el análisis de temporadas y ventas.", ("✨", PURPLE, "#eee9ff"), "Ver todas")
        recommendations = (
            ("🛒", "Comienza la compra de productos de Halloween", "Se recomienda adquirir inventario entre el 1 - 15 de octubre."),
            ("📦", "Aumenta el stock de mochilas escolares", "La demanda suele incrementarse 3 semanas antes del regreso a clases."),
            ("↗", "Considera nuevos productos de decoración navideña", "Las ventas crecieron 35% el año anterior."),
            ("%", "Prepara promociones combinadas", "Los combos de productos incrementan las ventas hasta 28%."),
        )
        for icon, title, note in recommendations:
            row = QFrame()
            row.setObjectName("recommendationRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(7, 3, 7, 3)
            row_layout.addWidget(_icon(icon, PURPLE, "#f0eaff", 31, 15))
            copy = QVBoxLayout()
            copy.setSpacing(0)
            copy.addWidget(_label(title, "productTitle"))
            copy.addWidget(_label(note, "productSubtitle"))
            row_layout.addLayout(copy, 1)
            row_layout.addWidget(_label("›", "link"))
            quick_layout.addWidget(row)
        right.addWidget(quick)
        body.addLayout(left, 53)
        body.addLayout(right, 47)
        layout.addLayout(body)


class TrendsView(_BaseIntelligenceView):
    TITLE = "Radar de tendencias"
    SUBTITLE = "Detecta nuevas oportunidades, monitorea la popularidad de productos y analiza señales del mercado\npara anticipar la demanda."
    PAGE_ICON = "🎯"

    def _build_content(self, layout):
        layout.addLayout(self._metrics((
            ("📈", PURPLE, "#eee9ff", "24", "Tendencias detectadas", "En el periodo seleccionado", "41%", GREEN),
            ("🛍️", GREEN, "#e5f8ef", "18", "Productos en tendencia", "Con alta demanda potencial", "32%", GREEN),
            ("📊", PINK, "#ffe8f1", "9", "Categorías en crecimiento", "Con señales positivas", "28%", GREEN),
            ("🔔", PINK, "#ffe8f1", "6", "Alertas de cambio", "Variaciones significativas", "50%", PINK),
        )))
        body = QHBoxLayout()
        body.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(10)
        opportunities, op_layout = _panel("Oportunidades de tendencia  ⓘ", "Productos y categorías con mayor potencial según señales del mercado.")
        combo = QComboBox()
        combo.addItem("Todas las categorías")
        combo.setFixedWidth(155)
        opportunities.layout().itemAt(0).layout().addWidget(combo)
        opportunity_rows = (
            ("👚  Guerreras K-pop\n     Álbumes, figuras, ropa y accesorios.", _interest(92), _badge("↑  120%", GREEN, "#e2f8ed"), _badge("Ropa", PURPLE, "#eee9ff"), _badge("Alta demanda", GREEN, "#e2f8ed"), _button("Aumentar inventario  ›")),
            ("🎃  Decoración de Halloween\n     Decoración, disfraces y artículos temáticos.", _interest(78), _badge("↑  85%", GREEN, "#e2f8ed"), _badge("Decoración", PINK, "#ffe9ef"), _badge("En crecimiento", BLUE, "#e7f1ff"), _button("Preparar campaña  ›")),
            ("🎒  Útiles escolares virales\n     Mochilas, lapiceras, cuadernos de personajes.", _interest(70), _badge("↑  60%", GREEN, "#e2f8ed"), _badge("Papelería", ORANGE, "#fff2df"), _badge("En crecimiento", BLUE, "#e7f1ff"), _button("Comprar anticipado  ›")),
            ("🧸  Colección Stumble Guys\n     Figuras coleccionables y accesorios.", _interest(65), _badge("↑  45%", GREEN, "#e2f8ed"), _badge("Juguetes", BLUE, "#e7f1ff"), _badge("Tendencia estable", TEXT, "#edf1f8"), _button("Monitorear precios  ›")),
            ("🎧  Accesorios tecnológicos\n     Audífonos, smartwatches y accesorios.", _interest(58), _badge("↑  38%", GREEN, "#e2f8ed"), _badge("Tecnología", PURPLE, "#eee9ff"), _badge("Oportunidad", GREEN, "#e2f8ed"), _button("Revisar proveedores  ›")),
            ("🎨  Juguetes sorpresa\n     Figuras sorpresa, mini juguetes y coleccionables.", _interest(52), _badge("↑  35%", GREEN, "#e2f8ed"), _badge("Juguetes", BLUE, "#e7f1ff"), _badge("En crecimiento", BLUE, "#e7f1ff"), _button("Crear combo  ›")),
        )
        op_layout.addWidget(self._table(("Tendencia / Producto", "Nivel de interés", "Crecimiento", "Categoría", "Estado", "Acción recomendada"), opportunity_rows, (210, 100, 100, 95, 115, 135), 69))
        left.addWidget(opportunities)
        new_products, new_layout = _panel("Oportunidades de nuevos productos  ⓘ", "Ideas de productos con potencial según tendencias emergentes.", ("✨", PURPLE, "#eee9ff"), "Ver todas")
        cards = QHBoxLayout()
        cards.setSpacing(7)
        for data in (
            ("👕", "Sudaderas K-pop", "Alta demanda potencial", "Evaluar producto  ›"),
            ("🎃", "Luces decorativas Halloween", "Tendencia en alza", "Agregar al catálogo  ›"),
            ("🧴", "Tomatodos virales", "Interés creciente", "Analizar demanda  ›"),
            ("🧸", "Figuras sorpresa", "Oportunidad de mercado", "Revisar proveedores  ›"),
        ):
            card = self._product_card(data[0], data[1], data[2], data[3], PURPLE, "white")
            cards.addWidget(card, 1)
        new_layout.addLayout(cards)
        left.addWidget(new_products)

        right = QVBoxLayout()
        right.setSpacing(10)
        sources, sources_layout = _panel("Fuentes de señal  ⓘ", "Análisis de tendencias a partir de múltiples fuentes de datos.")
        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        for icon, title, value, color, bg in (
            ("♪", "Redes sociales", "42%", PURPLE, "#f0eaff"),
            ("G", "Búsquedas", "28%", BLUE, "#e9f3ff"),
            ("🛒", "Ventas internas", "20%", GREEN, "#e4f8ef"),
            ("📰", "Medios y noticias", "10%", PURPLE, "#eee9ff"),
        ):
            box = QFrame()
            box.setObjectName("sourceCard")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(7, 7, 7, 7)
            box_layout.setSpacing(1)
            box_layout.addWidget(_icon(icon, color, bg, 39, 20), alignment=Qt.AlignCenter)
            box_layout.addWidget(_label(title, "productTitle", alignment=Qt.AlignCenter))
            value_label = _label(value, "sourceValue", alignment=Qt.AlignCenter)
            value_label.setStyleSheet(f"color:{color}; font-size:14px; font-weight:800; border:0;")
            box_layout.addWidget(value_label)
            box_layout.addWidget(_label("del análisis", "productSubtitle", alignment=Qt.AlignCenter))
            source_row.addWidget(box, 1)
        sources_layout.addLayout(source_row)
        right.addWidget(sources)
        popularity, popularity_layout = _panel("Seguimiento de popularidad  ⓘ", "Interés de búsqueda y menciones en redes sociales.")
        popularity_layout.addWidget(_MultiLineChart(
            (((35, 58, 49, 62, 60, 80, 62), PURPLE), ((32, 42, 34, 43, 88, 103, 76), PINK), ((12, 18, 15, 24, 42, 36, 30), BLUE)),
            ("Mar", "Abr", "May", "Jun", "Jul", "", "Ago"), 110,
            ("20,000", "40,000", "60,000", "80,000", "100,000"),
            (("Guerreras K-pop", PURPLE), ("Halloween", PINK), ("Útiles escolares", BLUE)),
        ))
        right.addWidget(popularity)
        validation, validation_layout = _panel("Validación con inventario y categorías  ⓘ", "Verifica disponibilidad y sugiere acciones por categoría.", ("📦", PURPLE, "#eee9ff"), "Ver todas")
        validation_rows = (
            ("👚  Ropa", "6", "320", _badge("Stock bajo", PINK, "#ffe6ed"), _button("Comprar  ›")),
            ("🎃  Decoración", "4", "650", _badge("Stock suficiente", GREEN, "#e2f8ed"), _button("Monitorear  ›")),
            ("📒  Papelería", "5", "280", _badge("Stock bajo", PINK, "#ffe6ed"), _button("Comprar  ›")),
            ("🧸  Juguetes", "6", "420", _badge("Stock suficiente", GREEN, "#e2f8ed"), _button("Monitorear  ›")),
            ("🎧  Tecnología", "3", "150", _badge("Stock bajo", PINK, "#ffe6ed"), _button("Comprar  ›")),
        )
        validation_layout.addWidget(self._table(("Categoría", "Productos en tendencia", "Stock actual", "Estado", "Acción sugerida"), validation_rows, row_height=25))
        right.addWidget(validation)
        body.addLayout(left, 63)
        body.addLayout(right, 37)
        layout.addLayout(body)


class SmartRecommendationsView(_BaseIntelligenceView):
    TITLE = "Recomendaciones inteligentes"
    SUBTITLE = "Promociones, combos, descuentos y sugerencias de abastecimiento basadas en el análisis de tus ventas e inventario\npara impulsar tus resultados."
    PAGE_ICON = "✨"

    def _build_content(self, layout):
        layout.addLayout(self._metrics((
            ("🏷️", PINK, "#ffe8f1", "15", "Promociones sugeridas", "Para las próximas semanas", "25%", GREEN),
            ("🛒", PURPLE, "#eee9ff", "8", "Combos recomendados", "Con alta probabilidad de venta", "40%", GREEN),
            ("📦", BLUE, "#e8f0ff", "12", "Reposiciones sugeridas", "Productos con alta demanda", "33%", GREEN),
            ("📊", ORANGE, "#fff0d9", "$ 28,450", "Impacto estimado", "en ventas adicionales", "38%", GREEN),
        )))
        top = QHBoxLayout()
        top.setSpacing(10)
        generated, generated_layout = _panel("Recomendaciones generadas  ⓘ", "Sugerencias personalizadas basadas en el análisis de ventas, inventario y tendencias del mercado.")
        combo = QComboBox()
        combo.addItem("Todas las recomendaciones")
        combo.setFixedWidth(170)
        generated.layout().itemAt(0).layout().addWidget(combo)
        recommendation_rows = (
            ("🎒  Mochilas escolares\n     Mochilas, útiles escolares", _badge("🏷️  Promoción", GREEN, "#e2f8ed"), "Aumento del 120% en búsquedas.\nAlta demanda para regreso a clases.", _badge("Alta", PINK, "#ffe5ed"), "+ $8,500\n(+35% en ventas)", _button("Ver detalles  ›")),
            ("🎃  Decoración Halloween\n     Decoración y artículos temáticos", _badge("🛒  Combo", PURPLE, "#eee9ff"), "Productos complementarios\ncon alta afinidad de compra.", _badge("Alta", PINK, "#ffe5ed"), "+ $6,200\n(+28% en ventas)", _button("Ver detalles  ›")),
            ("🎁  Regalos Día de la Madre\n     Regalos y cosméticos", _badge("🏷️  Descuento", PINK, "#ffe9ef"), "Incremento histórico de ventas\nen esta temporada.", _badge("Media", ORANGE, "#fff0da"), "+ $5,800\n(+32% en ventas)", _button("Ver detalles  ›")),
            ("🧸  Juguetes navideños\n     Juguetes y juegos", _badge("📦  Abastecimiento", BLUE, "#e7f1ff"), "Tendencia creciente identificada.\nStock actual por debajo del óptimo.", _badge("Alta", PINK, "#ffe5ed"), "+ $7,300\n(+45% en ventas)", _button("Ver detalles  ›")),
            ("🍿  Snacks de alta rotación\n     Alimentos y bebidas", _badge("🏷️  Promoción", GREEN, "#e2f8ed"), "Alta rotación y margen favorable.\nOportunidad de aumentar volumen.", _badge("Media", ORANGE, "#fff0da"), "+ $4,100\n(+18% en ventas)", _button("Ver detalles  ›")),
            ("🎧  Accesorio tecnológico\n     Tecnología y accesorios", _badge("🛒  Combo", PURPLE, "#eee9ff"), "Frecuente compra conjunta\ncon audífonos y cargadores.", _badge("Media", ORANGE, "#fff0da"), "+ $3,900\n(+22% en ventas)", _button("Ver detalles  ›")),
        )
        generated_layout.addWidget(self._table(("Producto / Categoría", "Tipo de recomendación", "Motivo / Insight", "Prioridad", "Impacto estimado", "Acción"), recommendation_rows, (190, 125, 190, 75, 110, 95), 57))
        top.addWidget(generated, 62)

        offers = QVBoxLayout()
        offers.setSpacing(10)
        promotions, promotion_layout = _panel("Sugerencias de promociones", "Productos ideales para promociones en las próximas semanas.", ("🏷️", PINK, "#ffe8f1"), "Ver todas")
        promotion_row = QHBoxLayout()
        promotion_row.setSpacing(6)
        for product in (
            ("🎒", "Mochilas escolares", "-20% sugerido", "Alta demanda", GREEN, "#e2f8ed"),
            ("🍿", "Snacks y golosinas", "2x1 sugerido", "Alta rotación", BLUE, "#e7f1ff"),
            ("🧴", "Botellas y termos", "15% sugerido", "Tendencia al alza", PURPLE, "#eee9ff"),
            ("📚", "Útiles escolares", "-25% sugerido", "Buen margen", GREEN, "#e2f8ed"),
        ):
            promotion_row.addWidget(self._product_card(*product), 1)
        promotion_layout.addLayout(promotion_row)
        offers.addWidget(promotions)
        combos, combo_layout = _panel("Propuestas de combos y descuentos", "Combinaciones de productos con alta probabilidad de venta.", ("🛒", PURPLE, "#eee9ff"), "Ver todas")
        combo_row = QHBoxLayout()
        combo_row.setSpacing(6)
        for product in (
            ("🎒 👜", "Mochila + Lonchera", "Combo sugerido", "+28% en ventas", ORANGE, "#fff0da"),
            ("🎮 🎧", "Control + Audífonos", "Combo sugerido", "+25% en ventas", GREEN, "#e2f8ed"),
            ("🎃 💡", "Decoración Halloween", "Combo sugerido", "+32% en ventas", PURPLE, "#eee9ff"),
            ("📓 🖊️", "Cuaderno + Plumones", "Combo sugerido", "+20% en ventas", BLUE, "#e7f1ff"),
        ):
            combo_row.addWidget(self._product_card(*product), 1)
        combo_layout.addLayout(combo_row)
        offers.addWidget(combos)
        top.addLayout(offers, 38)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        restock, restock_layout = _panel("Recomendaciones de abastecimiento  ⓘ", "Productos que requieren reposición o aumento de inventario.", ("📦", BLUE, "#e8f0ff"), "Ver todas")
        restock_rows = (
            ("Mochilas escolares", "18", "150", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Generar OC")),
            ("Juguetes navideños", "25", "200", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Generar OC")),
            ("Decoración Halloween", "12", "100", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Generar OC")),
            ("Útiles escolares", "32", "120", _badge("Por reponer", ORANGE, "#fff0da"), _button("Generar OC")),
            ("Accesorios tecnológicos", "28", "100", _badge("Stock bajo", PINK, "#ffe5ed"), _button("Generar OC")),
        )
        restock_layout.addWidget(self._table(("Producto", "Stock actual", "Stock sugerido", "Estado", "Acción"), restock_rows, row_height=26))
        bottom.addWidget(restock, 36)
        critical, critical_layout = _panel("Productos con stock crítico", "Productos con inventario por debajo del nivel mínimo.", ("🔔", PINK, "#ffe8f1"), "Ver todas")
        critical_rows = (
            ("🎒  Mochila escolar básica\n     SKU: MOCH-001", "8 unidades", _badge("Stock crítico", PINK, "#ffe5ed"), _button("Reponer")),
            ("🎃  Decoración calabaza LED\n     SKU: DECO-045", "5 unidades", _badge("Stock crítico", PINK, "#ffe5ed"), _button("Reponer")),
            ("🖊️  Set de plumones\n     SKU: ESC-023", "7 unidades", _badge("Stock crítico", PINK, "#ffe5ed"), _button("Reponer")),
            ("🎧  Audífonos inalámbricos\n     SKU: TEC-078", "6 unidades", _badge("Stock crítico", PINK, "#ffe5ed"), _button("Reponer")),
        )
        critical_layout.addWidget(self._table(("Producto", "", "", ""), critical_rows, row_height=34))
        bottom.addWidget(critical, 33)
        chart, chart_layout = _panel("Integración con análisis de ventas", "Impacto estimado de las recomendaciones en tus ventas.", ("📊", PURPLE, "#eee9ff"))
        chart_layout.addWidget(_SalesBars())
        bottom.addWidget(chart, 31)
        layout.addLayout(bottom)
