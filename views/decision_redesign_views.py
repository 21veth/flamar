"""Content-only decision views matching the redesigned FLAMAR screens."""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


INK = "#081433"
MUTED = "#5f7097"
PURPLE = "#5525f5"
BLUE = "#2f80ed"
GREEN = "#09a868"
RED = "#ef334e"
ORANGE = "#f59e0b"
BG = "#f6f9fe"
BORDER = "#dde5f1"


BASE_STYLE = """
    QWidget#page, QWidget#canvas, QScrollArea#scroll { background: #f6f9fe; color: #081433; font-family: "Segoe UI Variable", "Segoe UI"; }
    QScrollArea#scroll { border: 0; }
    QScrollBar:vertical { width: 8px; background: #eef3fa; }
    QScrollBar:horizontal { height: 8px; background: #eef3fa; }
    QScrollBar::handle { background: #c6d1e2; border-radius: 4px; min-height: 36px; min-width: 36px; }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QLabel#title { font-size: 28px; font-weight: 800; color: #07122f; }
    QLabel#subtitle { font-size: 14px; color: #5f7097; }
    QLabel#sectionTitle { font-size: 15px; font-weight: 750; color: #081433; }
    QLabel#muted, QLabel#small { color: #5f7097; font-size: 10px; }
    QLabel#small { font-size: 9px; }
    QFrame#card, QFrame#panel { background: white; border: 1px solid #dde5f1; border-radius: 9px; }
    QComboBox, QLineEdit { background: white; color: #263556; border: 1px solid #d6dfec; border-radius: 7px; padding: 8px 10px; min-height: 18px; }
    QComboBox:hover, QLineEdit:focus { border-color: #7258ff; }
    QComboBox::drop-down { border: 0; width: 24px; }
    QPushButton { font-family: "Segoe UI Variable", "Segoe UI"; }
    QPushButton#primary { color: white; background: #5525f5; border: 0; border-radius: 7px; padding: 10px 18px; font-weight: 700; }
    QPushButton#primary:hover { background: #4518df; }
    QPushButton#outline { color: #5525f5; background: white; border: 1px solid #704fff; border-radius: 7px; padding: 9px 15px; }
    QPushButton#outline:hover { background: #f4f1ff; }
"""


def _label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def _panel(layout=None, name="card"):
    frame = QFrame(objectName=name)
    if layout is not None:
        frame.setLayout(layout)
    return frame


def _chip(text, foreground, background, width=70):
    chip = QLabel(text)
    chip.setAlignment(Qt.AlignCenter)
    chip.setFixedSize(width, 27)
    chip.setStyleSheet(
        f"color:{foreground}; background:{background}; border:0; border-radius:7px; font-size:9px; font-weight:700;"
    )
    return chip


def _icon(text, color, background, size=52):
    icon = QLabel(text)
    icon.setAlignment(Qt.AlignCenter)
    icon.setFixedSize(size, size)
    icon.setStyleSheet(
        f"color:{color}; background:{background}; border:0; border-radius:10px; font-size:{int(size * .42)}px; font-weight:800;"
    )
    return icon


class _Page(QWidget):
    """Shared scroll canvas and reference account/date header."""

    def __init__(self, title, subtitle, minimum_width=1160, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setStyleSheet(BASE_STYLE + self.extra_style())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(objectName="scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.canvas = QWidget(objectName="canvas")
        self.canvas.setMinimumWidth(0)
        self.content = QVBoxLayout(self.canvas)
        self.content.setContentsMargins(24, 18, 24, 18)
        self.content.setSpacing(13)
        self.content.addLayout(self._header(title, subtitle))
        scroll.setWidget(self.canvas)
        outer.addWidget(scroll)

    def _header(self, title, subtitle):
        row = QHBoxLayout()
        headings = QVBoxLayout()
        headings.setSpacing(1)
        headings.addWidget(_label(title, "title"))
        headings.addWidget(_label(subtitle, "subtitle"))
        row.addLayout(headings)
        row.addStretch()

        date = QPushButton("📅   01/08/2025 - 31/08/2025    v", objectName="dateButton")
        date.setFixedSize(230, 42)
        date.clicked.connect(self._date_info)
        row.addWidget(date)
        bell = QPushButton("🔔", objectName="bellButton")
        bell.setToolTip("1 notificación")
        bell.setFixedSize(42, 42)
        bell.clicked.connect(lambda: QMessageBox.information(self, "Notificaciones", "Tienes 1 notificación pendiente."))
        row.addWidget(bell)
        row.addWidget(_icon("AA", PURPLE, "#e6e0ff", 42))
        account = QVBoxLayout()
        account.setSpacing(0)
        account.addWidget(_label("Administrador", "accountName"))
        account.addWidget(_label("Administrador", "small"))
        row.addLayout(account)
        row.addWidget(_label("v", "accountName"))
        return row

    def _date_info(self):
        QMessageBox.information(self, "Rango de fechas", "Período activo: 01/08/2025 - 31/08/2025")

    @staticmethod
    def extra_style():
        return """
            QPushButton#dateButton { color:#17254a; background:white; border:1px solid #d5deec; border-radius:8px; font-size:11px; text-align:left; padding-left:15px; }
            QPushButton#bellButton { color:#3c4d78; background:transparent; border:0; font-size:18px; }
            QLabel#accountName { color:#081433; font-size:11px; font-weight:700; }
        """


class RecommendationsView(_Page):
    RECOMMENDATIONS = (
        ("👕🎤", "Promoción", "Combo K-pop", "Crear paquete promocional de playera + póster + sticker.\nAlta afinidad de compra entre estos productos.", "+18%", "Alta", "92%", "Jóvenes 13-25 años", "Fans de K-pop"),
        ("🎃", "Promoción", "Descuento Halloween", "Aplicar 20% de descuento en decoración seleccionada\npara incrementar la rotación en octubre.", "+22%", "Media", "85%", "Familias", "Compras por temporada"),
        ("🎒", "Promoción", "Paquete escolar", "Promocionar mochila + cuaderno + lápices al inicio\nde temporada escolar.", "+15%", "Media", "78%", "Padres de familia", "Regreso a clases"),
        ("📘", "Abastecimiento", "Reabastecer cuadernos universitarios", "El stock está por debajo del nivel mínimo y la demanda\nmuestra tendencia al alza en las próximas semanas.", "+12%", "Alta", "94%", "Estudiantes", "Universidad y preparatoria"),
        ("🎄", "Abastecimiento", "Reforzar stock de decoración navideña", "La demanda de productos navideños comienza a aumentar\nen septiembre. Se recomienda anticipar el inventario.", "+28%", "Media", "88%", "Familias", "Compras de temporada"),
        ("👕", "Abastecimiento", "Monitorear playeras K-pop", "Aumento en la tasa de rotación. Se recomienda monitorear\nniveles de stock para evitar quiebres.", "+10%", "Baja", "76%", "Jóvenes 13-25 años", "Fans de K-pop"),
    )

    def __init__(self, parent=None):
        super().__init__(
            "Recomendaciones inteligentes",
            "Sugerencias personalizadas para impulsar tus ventas y optimizar tu inventario.",
            1180,
            parent,
        )
        self._active_type = "Todos los tipos"
        self.content.addSpacing(8)
        self.content.addWidget(self._tabs())
        metrics = QHBoxLayout()
        metrics.setSpacing(11)
        for args in (
            ("⚑", "3", "Promociones sugeridas", "para aumentar ventas", PURPLE, "#eeeaff"),
            ("📦", "3", "Reabastecimientos sugeridos", "para evitar quiebres", GREEN, "#e8faf3"),
            ("|||", "+25%", "Impacto estimado en ventas", "si aplicas todas las recomendaciones", BLUE, "#e8f2ff"),
            ("O", "92%", "Confianza promedio", "en las recomendaciones", ORANGE, "#fff5df"),
        ):
            metrics.addWidget(self._metric(*args), 1)
        self.content.addLayout(metrics)
        self.content.addSpacing(4)
        self.content.addWidget(self._list_panel(), 1)

    def _tabs(self):
        frame = QFrame()
        frame.setMinimumHeight(54)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(0)
        self.tab_group = QButtonGroup(self)
        for index, (text, icon) in enumerate((("Promociones", "⚑"), ("Abastecimiento", "◇"))):
            button = QPushButton(f"{icon}    {text}", objectName="tab")
            button.setCheckable(True)
            button.setFixedSize(220, 46)
            button.clicked.connect(lambda checked=False, kind=text: self._set_type(kind))
            self.tab_group.addButton(button)
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)
        layout.addStretch()
        return frame

    @staticmethod
    def _metric(symbol, value, title, copy, color, background):
        card = _panel()
        card.setMinimumHeight(108)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 12, 12, 12)
        row.addWidget(_icon(symbol, color, background, 62))
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(_label(value, "metricValue"))
        text.addWidget(_label(title, "metricTitle"))
        text.addWidget(_label(copy, "small"))
        row.addLayout(text, 1)
        return card

    def _list_panel(self):
        panel = _panel(name="panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 11, 8, 8)
        layout.setSpacing(8)
        tools = QHBoxLayout()
        tools.addWidget(_label("LISTA DE RECOMENDACIONES", "sectionTitle"))
        tools.addStretch()
        self.type_filter = QComboBox()
        self.type_filter.addItems(("Todos los tipos", "Promoción", "Abastecimiento"))
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(("Todas las prioridades", "Alta", "Media", "Baja"))
        segment = QComboBox()
        segment.addItems(("Todos los segmentos", "Familias", "Estudiantes", "Jóvenes 13-25 años"))
        self.search = QLineEdit(placeholderText="⌕   Buscar recomendación...")
        for widget in (self.type_filter, self.priority_filter, segment):
            widget.setFixedWidth(150)
            tools.addWidget(widget)
        self.search.setFixedWidth(235)
        tools.addWidget(self.search)
        layout.addLayout(tools)
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(8)
        layout.addLayout(self.rows_layout)
        self.type_filter.currentTextChanged.connect(self._refresh)
        self.priority_filter.currentTextChanged.connect(self._refresh)
        segment.currentTextChanged.connect(self._refresh)
        self.segment_filter = segment
        self.search.textChanged.connect(self._refresh)
        self._refresh()
        return panel

    def _set_type(self, kind):
        self.type_filter.setCurrentText(kind)

    def _refresh(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        needle = self.search.text().lower().strip()
        for data in self.RECOMMENDATIONS:
            if self.type_filter.currentText() != "Todos los tipos" and data[1] != self.type_filter.currentText():
                continue
            if self.priority_filter.currentText() != "Todas las prioridades" and data[5] != self.priority_filter.currentText():
                continue
            if self.segment_filter.currentText() != "Todos los segmentos" and data[7] != self.segment_filter.currentText():
                continue
            if needle and needle not in (data[2] + " " + data[3]).lower():
                continue
            self.rows_layout.addWidget(self._recommendation(data))

    def _recommendation(self, data):
        emoji, kind, title, body, impact, priority, confidence, segment, segment_copy = data
        card = _panel(name="recommendation")
        card.setMinimumHeight(88)
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(12)
        row.addWidget(_icon(emoji, "#333", "#f4f5f8", 58))
        kind_color = GREEN if kind == "Abastecimiento" else PURPLE
        row.addWidget(_chip(kind, kind_color, "#e7faf1" if kind == "Abastecimiento" else "#f0edff", 92), alignment=Qt.AlignTop)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        copy.addWidget(_label(title, "rowTitle"))
        copy.addWidget(_label(body, "muted"))
        row.addLayout(copy, 2)
        row.addWidget(self._column("Impacto esperado", f"↑  {impact}", "en ventas de la categoría", "impact"), 1)
        colors = {"Alta": ("#cf2333", "#ffe8eb"), "Media": ("#b66a00", "#fff4dc"), "Baja": ("#087b53", "#e5f9f0")}
        priority_box = QVBoxLayout()
        priority_box.addWidget(_label("Prioridad", "small"))
        priority_box.addWidget(_chip(priority, *colors[priority], 74))
        row.addLayout(priority_box)
        row.addWidget(self._column("Confianza", f"◯  {confidence}", "", "confidence"))
        row.addWidget(self._column("Segmento afectado", segment, segment_copy, "segment"), 1)
        button = QPushButton("Ver detalles    →", objectName="outline")
        button.clicked.connect(lambda checked=False, item=data: self._detail(item))
        row.addWidget(button)
        return card

    @staticmethod
    def _column(caption, value, sub, name):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(3)
        layout.addWidget(_label(caption, "small"))
        layout.addWidget(_label(value, name))
        if sub:
            layout.addWidget(_label(sub, "small"))
        return box

    def _detail(self, data):
        QMessageBox.information(
            self,
            data[2],
            f"{data[3].replace(chr(10), ' ')}\n\nImpacto esperado: {data[4]}\nPrioridad: {data[5]}\nConfianza: {data[6]}\nSegmento: {data[7]}",
        )

    @staticmethod
    def extra_style():
        return _Page.extra_style() + """
            QPushButton#tab { color:#465677; background:white; border:1px solid #dde5f1; font-size:12px; font-weight:700; }
            QPushButton#tab:first { border-radius:8px; }
            QPushButton#tab:checked { color:white; background:#5525f5; border-color:#5525f5; }
            QLabel#metricValue { color:#081433; font-size:20px; font-weight:800; }
            QLabel#metricTitle { color:#26365b; font-size:11px; }
            QFrame#recommendation { background:white; border:1px solid #e0e7f0; border-radius:9px; }
            QLabel#rowTitle, QLabel#segment { color:#081433; font-size:11px; font-weight:750; }
            QLabel#impact { color:#07865b; font-size:12px; font-weight:800; }
            QLabel#confidence { color:#081433; font-size:11px; font-weight:800; }
        """


class SupplyView(_Page):
    PRODUCTS = (
        ("🎧", "Audífonos Bluetooth", "Tecnología", 40, 8, 15, 0, 47, "12/08/2025", "Crítica"),
        ("🎒", "Mochila escolar", "Escolar", 60, 12, 25, 20, 53, "15/08/2025", "Alta"),
        ("👕", "Playera K-pop", "Ropa", 55, 15, 20, 0, 60, "12/08/2025", "Alta"),
        ("🎃", "Decoración Halloween", "Decoración", 80, 20, 30, 50, 60, "20/08/2025", "Media"),
        ("📘", "Cuaderno universitario", "Escolar", 45, 18, 25, 0, 32, "14/08/2025", "Media"),
        ("🎄", "Adorno navideño LED", "Navidad", 70, 5, 25, 0, 90, "01/09/2025", "Crítica"),
        ("🧍", "Figura de colección", "Coleccionables", 25, 10, 15, 10, 30, "18/08/2025", "Media"),
        ("🎮", "Control inalámbrico", "Tecnología", 35, 6, 15, 0, 44, "12/08/2025", "Alta"),
        ("🧴", "Botella térmica", "Accesorios", 28, 14, 15, 0, 24, "18/08/2025", "Media"),
        ("💡", "Lámpara LED", "Hogar", 32, 9, 15, 20, 28, "19/08/2025", "Baja"),
    )

    def __init__(self, parent=None):
        super().__init__(
            "Planificación del abastecimiento",
            "Convierte el análisis de ventas en acciones de compra. Define qué reponer, cuánto y cuándo.",
            1220,
            parent,
        )
        self.content.addSpacing(14)
        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        for args in (
            ("📦", "18", "Productos a reponer", "Stock por debajo del nivel óptimo", "UP 38%", RED, "#ffeaee"),
            ("🛒", "$12,450", "Compra sugerida", "Inversión estimada para reponer", "↓  12%", GREEN, "#e6f9f0"),
            ("🚚", "6", "Pedidos en tránsito", "Productos ya en camino", "UP 50%", BLUE, "#e8f2ff"),
            ("!", "4", "Riesgos de quiebre", "Productos críticos sin cobertura", "UP 100%", ORANGE, "#fff2e5"),
        ):
            metrics.addWidget(self._metric(*args), 1)
        self.content.addLayout(metrics)
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._plan(), 3)
        body.addWidget(self._alerts(), 1)
        self.content.addLayout(body, 1)

    @staticmethod
    def _metric(symbol, value, title, copy, delta, color, background):
        card = _panel()
        card.setMinimumHeight(114)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 11, 12, 11)
        row.addWidget(_icon(symbol, color, background, 58))
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(_label(value, "metricValue"))
        text.addWidget(_label(title, "metricTitle"))
        text.addWidget(_label(copy, "small"))
        row.addLayout(text, 1)
        row.addWidget(_chip(delta, GREEN if "↓" in delta or "50" in delta else RED, "#e7f9f1" if "↓" in delta or "50" in delta else "#ffe9ed", 62), alignment=Qt.AlignTop)
        return card

    def _plan(self):
        panel = _panel(name="panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(13, 12, 13, 10)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        heading.addWidget(_label("Plan de reposición de productos  ⓘ", "sectionTitle"))
        heading.addStretch()
        layout.addLayout(heading)
        tools = QHBoxLayout()
        self.product_search = QLineEdit(placeholderText="⌕   Buscar producto...")
        self.product_search.setFixedWidth(160)
        self.category_filter = QComboBox()
        self.category_filter.addItems(("Todas las categorías", "Tecnología", "Escolar", "Ropa", "Decoración", "Navidad"))
        self.supply_priority = QComboBox()
        self.supply_priority.addItems(("Todas las prioridades", "Crítica", "Alta", "Media", "Baja"))
        risk = QComboBox()
        risk.addItems(("Todos los riesgos", "Stock bajo", "Sin cobertura"))
        for widget in (self.product_search, self.category_filter, self.supply_priority, risk):
            tools.addWidget(widget, 1)
        generate = QPushButton("⚒   Generar plan automático", objectName="primary")
        generate.clicked.connect(self._generate_plan)
        tools.addWidget(generate)
        layout.addLayout(tools)

        headers = ("", "Producto", "Demanda estimada\n(próx. 30 días)", "Stock actual", "Stock seguridad", "En tránsito", "Cantidad\nsugerida", "Fecha sugerida\nde pedido", "Prioridad")
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setMinimumHeight(548)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 32)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.product_search.textChanged.connect(self._fill_table)
        self.category_filter.currentTextChanged.connect(self._fill_table)
        self.supply_priority.currentTextChanged.connect(self._fill_table)
        self._fill_table()
        layout.addWidget(self.table)
        footer = QHBoxLayout()
        self.count_label = _label("Mostrando 10 de 42 productos", "muted")
        footer.addWidget(self.count_label)
        footer.addStretch()
        for text in ("‹", "1", "2", "3", "4", "5", "›"):
            button = QPushButton(text, objectName="pageButton")
            button.setFixedSize(34, 32)
            if text == "1":
                button.setProperty("active", True)
            footer.addWidget(button)
        footer.addStretch()
        footer.addWidget(_label("Productos por página:", "small"))
        per_page = QComboBox()
        per_page.addItems(("10", "20", "50"))
        footer.addWidget(per_page)
        layout.addLayout(footer)
        return panel

    def _fill_table(self):
        needle = self.product_search.text().lower().strip()
        category = self.category_filter.currentText()
        priority = self.supply_priority.currentText()
        items = [p for p in self.PRODUCTS if (not needle or needle in p[1].lower()) and (category == "Todas las categorías" or p[2] == category) and (priority == "Todas las prioridades" or p[9] == priority)]
        self.table.setRowCount(len(items))
        for row, product in enumerate(items):
            check = QCheckBox()
            holder = QWidget()
            box = QHBoxLayout(holder)
            box.setContentsMargins(7, 0, 0, 0)
            box.addWidget(check)
            self.table.setCellWidget(row, 0, holder)
            name = QTableWidgetItem(f"{product[0]}  {product[1]}\n     {product[2]}")
            name.setData(Qt.UserRole, product)
            self.table.setItem(row, 1, name)
            for column, value in enumerate(product[3:9], 2):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                if column == 3 and product[4] < product[5]:
                    item.setForeground(QColor(RED))
                self.table.setItem(row, column, item)
            priority_item = QTableWidgetItem(product[9])
            priority_item.setTextAlignment(Qt.AlignCenter)
            priority_item.setForeground(QColor({"Crítica": RED, "Alta": "#dd6814", "Media": "#bd7600", "Baja": GREEN}[product[9]]))
            self.table.setItem(row, 8, priority_item)
            self.table.setRowHeight(row, 46)
        if hasattr(self, "count_label"):
            self.count_label.setText(f"Mostrando {len(items)} de 42 productos")

    def _alerts(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        stock = self._side_panel("Alertas de stock  ⓘ", (
            ("🎃", "Decoración Halloween", "Stock actual: 20 (mín. 30)\nDemanda estimada: 80 un.\nSugerido: 60 un.", "Stock bajo"),
            ("🎄", "Adorno navideño LED", "Stock actual: 5 (mín. 25)\nDemanda estimada: 70 un.\nSugerido: 90 un.", "Stock bajo"),
            ("🎧", "Audífonos Bluetooth", "Stock actual: 8 (mín. 15)\nDemanda estimada: 40 un.\nSugerido: 47 un.", "Stock bajo"),
        ))
        prices = self._side_panel("Antes que suba de precio  ⓘ", (
            ("🎅", "Productos Navideños", "Se espera un aumento de precios de\n10% - 20% desde septiembre.", "Revisión temprana"),
            ("🎃", "Decoración Halloween", "Alta demanda estacional. Asegurar\ninventario antes del 15 de agosto.", "Revisión temprana"),
            ("🎒", "Mochilas Escolares", "Incremento de precios esperado en\nseptiembre por temporada escolar.", "Revisión temprana"),
            ("🎮", "Accesorios de Tecnología", "Posible aumento de 8% - 15% en Q4\npor alta demanda.", "Revisión temprana"),
        ))
        layout.addWidget(stock)
        layout.addWidget(prices)
        return wrapper

    @staticmethod
    def _side_panel(title, items):
        panel = _panel(name="panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        heading = QHBoxLayout()
        heading.addWidget(_label(title, "sectionTitle"))
        heading.addStretch()
        heading.addWidget(_label("Ver todas", "link"))
        layout.addLayout(heading)
        for emoji, name, copy, badge in items:
            card = _panel(name="miniCard")
            card.setMinimumHeight(78 if badge == "Stock bajo" else 67)
            row = QHBoxLayout(card)
            row.setContentsMargins(7, 7, 7, 7)
            row.addWidget(_icon(emoji, "#333", "#f4f5f8", 48))
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(_label(name, "miniTitle"))
            text.addWidget(_label(copy, "small"))
            row.addLayout(text, 1)
            color = RED if badge == "Stock bajo" else PURPLE
            row.addWidget(_chip(badge, color, "#ffeaee" if badge == "Stock bajo" else "#f0edff", 86), alignment=Qt.AlignTop)
            layout.addWidget(card)
        return panel

    def _generate_plan(self):
        selected = []
        for row in range(self.table.rowCount()):
            holder = self.table.cellWidget(row, 0)
            if holder.findChild(QCheckBox).isChecked():
                selected.append(self.table.item(row, 1).data(Qt.UserRole)[1])
        scope = ", ".join(selected) if selected else "todos los productos visibles"
        QMessageBox.information(self, "Plan automático", f"Plan de reposición generado para {scope}.")

    @staticmethod
    def extra_style():
        return _Page.extra_style() + """
            QLabel#metricValue { font-size:19px; font-weight:800; }
            QLabel#metricTitle { color:#29395d; font-size:11px; }
            QLabel#link { color:#5525f5; font-size:10px; font-weight:700; }
            QTableWidget { color:#152343; background:white; border:0; font-size:9px; selection-background-color:#f1edff; gridline-color:#e4eaf2; }
            QTableWidget::item { border-bottom:1px solid #e6ebf3; padding:3px; }
            QHeaderView::section { color:#152343; background:#f7f9fd; border:0; border-bottom:1px solid #dfe6f0; padding:7px 3px; font-size:8px; font-weight:700; }
            QFrame#miniCard { background:white; border:1px solid #e2e8f1; border-radius:8px; }
            QLabel#miniTitle { font-size:9px; font-weight:750; }
            QPushButton#pageButton { color:#344263; background:white; border:1px solid #dce4ef; border-radius:6px; }
            QPushButton#pageButton[active="true"] { color:white; background:#5525f5; }
        """


class _SalesChart(QWidget):
    VALUES = (9, 12, 16, 19, 22, 24, 28, 34, 26, 22, 18, 15)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(225)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(38, 16, -12, -25)
        painter.setFont(QFont("Segoe UI", 7))
        for i in range(5):
            y = area.bottom() - i * area.height() / 4
            painter.setPen(QPen(QColor("#e5eaf2"), 1))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor(MUTED))
            painter.drawText(QRectF(0, y - 7, 32, 14), Qt.AlignRight, f"{i * 10}K")
        slot = area.width() / len(self.VALUES)
        points = []
        gradient = QLinearGradient(0, area.top(), 0, area.bottom())
        gradient.setColorAt(0, QColor("#6c4ef7"))
        gradient.setColorAt(1, QColor("#a892ff"))
        for i, value in enumerate(self.VALUES):
            x = area.left() + slot * (i + .5)
            height = area.height() * value / 40
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(QRectF(x - slot * .28, area.bottom() - height, slot * .56, height), 2, 2)
            points.append(QPointF(x, area.bottom() - height))
        painter.setPen(QPen(QColor(PURPLE), 2))
        painter.drawPolyline(points)
        painter.setPen(QColor(MUTED))
        for i, month in enumerate(("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")):
            painter.drawText(QRectF(area.left() + slot * i, area.bottom() + 6, slot, 14), Qt.AlignCenter, month)


class _CategoryDonut(QWidget):
    ITEMS = (("Ropa", 35, "#5423ee"), ("Tecnología", 22, "#3894ee"), ("Colección K-pop", 15, "#f64d8b"), ("Decoración", 12, "#ffad18"), ("Papelería", 10, "#0ab26c"), ("Accesorios", 6, "#94a5bd"))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(225)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(145, self.height() - 20)
        circle = QRectF(12, (self.height() - size) / 2, size, size).adjusted(13, 13, -13, -13)
        pen = QPen()
        pen.setWidth(25)
        start = 90 * 16
        for _, value, color in self.ITEMS:
            span = -int(value * 3.6 * 16)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(circle, start, span)
            start += span
        painter.setPen(QColor(INK))
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(circle, Qt.AlignCenter, "$25,430")
        x = min(190, self.width() * .55)
        painter.setFont(QFont("Segoe UI", 8))
        top = 20
        for i, (name, value, color) in enumerate(self.ITEMS):
            y = top + i * 24
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(x, y + 6), 4, 4)
            painter.setPen(QColor("#263556"))
            painter.drawText(QRectF(x + 12, y, self.width() - x - 48, 15), name)
            painter.drawText(QRectF(self.width() - 38, y, 34, 15), Qt.AlignRight, f"{value}%")


class ReportsView(_Page):
    REPORTS = (
        ("|||", "Informe general de ventas", "Resumen completo de ventas, ingresos y\nproductos más vendidos.", PURPLE, "#efebff"),
        ("📦", "Inventario y stock crítico", "Estado de inventario, productos críticos\ny rotación de stock.", GREEN, "#e6f9f0"),
        ("/", "Predicción de demanda", "Proyecciones de demanda por producto\ny temporada.", BLUE, "#e8f2ff"),
        ("⚑", "Promociones recomendadas", "Análisis de efectividad y sugerencias\nde promociones.", ORANGE, "#fff2e1"),
        ("🚚", "Planificación de abastecimiento", "Recomendaciones y planificación de\nreabastecimiento.", PURPLE, "#eeeaff"),
        ("|||", "Temporadas y tendencias", "Análisis de estacionalidad y tendencias\nde mercado.", RED, "#ffeaef"),
    )

    def __init__(self, parent=None):
        super().__init__("Reportes", "Genera y visualiza reportes personalizados para analizar el desempeño de tu negocio.", 1200, parent)
        self.content.addWidget(self._filters())
        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._types())
        body.addWidget(self._report(), 1)
        self.content.addLayout(body, 1)
        self.content.addLayout(self._actions())

    def _filters(self):
        panel = _panel(name="panel")
        panel.setMinimumHeight(92)
        row = QHBoxLayout(panel)
        row.setContentsMargins(16, 10, 16, 10)
        fields = (
            ("Tipo de reporte", ("Todos los reportes", "Ventas", "Inventario")),
            ("Rango de fechas", ("01/08/2025 - 31/08/2025", "01/07/2025 - 31/07/2025")),
            ("Tienda", ("Todas las tiendas", "Tienda Centro", "Tienda Norte", "Tienda Sur", "Tienda Online")),
            ("Categoría", ("Todas las categorías", "Ropa", "Tecnología", "Decoración")),
            ("Temporada", ("Todas las temporadas", "Escolar", "Halloween", "Navidad")),
        )
        self.filters = []
        for label, values in fields:
            box = QVBoxLayout()
            box.setSpacing(4)
            field_label = _label(label, "filterLabel")
            field_label.setMinimumHeight(15)
            box.addWidget(field_label)
            combo = QComboBox()
            combo.addItems(values)
            box.addWidget(combo)
            row.addLayout(box, 1)
            self.filters.append(combo)
        generate = QPushButton("Generar reporte", objectName="primary")
        generate.clicked.connect(self._generate)
        row.addWidget(generate, alignment=Qt.AlignBottom)
        return panel

    def _types(self):
        panel = _panel(name="panel")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(11)
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(_label("Tipos de reportes", "sectionTitle"))
        layout.addWidget(_label("Selecciona un tipo de reporte para visualizar su contenido.", "small"))
        self.report_group = QButtonGroup(self)
        for index, report in enumerate(self.REPORTS):
            icon, title, copy, color, background = report
            button = QPushButton(objectName="reportType")
            button.setCheckable(True)
            button.setFixedHeight(80)
            inner = QHBoxLayout(button)
            inner.setContentsMargins(8, 7, 8, 7)
            inner.addWidget(_icon(icon, color, background, 46))
            text = QVBoxLayout()
            text.addWidget(_label(title, "typeTitle"))
            text.addWidget(_label(copy, "small"))
            inner.addLayout(text, 1)
            button.clicked.connect(lambda checked=False, i=index: self._select_report(i))
            self.report_group.addButton(button, index)
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)
        layout.addStretch()
        return panel

    def _report(self):
        panel = _panel(name="panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        self.report_title = _label("Informe general de ventas", "reportTitle")
        title_box.addWidget(self.report_title)
        title_box.addWidget(_label("Resumen completo del desempeño de ventas en el período seleccionado.", "muted"))
        heading.addLayout(title_box)
        heading.addStretch()
        heading.addWidget(_label("ⓘ  Período: 01/08/2025 - 31/08/2025", "small"))
        heading.addWidget(_chip("✓ Datos actualizados", GREEN, "#e8f9f1", 112))
        layout.addLayout(heading)
        layout.addSpacing(10)

        metrics = QHBoxLayout()
        for args in (
            ("|||", "$ 25,430", "Ventas totales", "↑ 12%", PURPLE, "#efebff"),
            ("$", "$ 320,850", "Ingresos estimados", "↑ 8%", GREEN, "#e6f9f0"),
            ("📦", "3,450", "Productos vendidos", "↓ 4%", RED, "#ffeaef"),
            ("%", "92.9%", "Margen promedio", "↑ 6%", ORANGE, "#fff2df"),
        ):
            metrics.addWidget(self._report_metric(*args), 1)
        layout.addLayout(metrics)
        charts = QHBoxLayout()
        charts.setSpacing(9)
        charts.addWidget(self._chart_card("Evolución de ventas  ⓘ", _SalesChart()), 1)
        charts.addWidget(self._chart_card("Distribución de ventas por categoría  ⓘ", _CategoryDonut()), 1)
        layout.addLayout(charts)
        tables = QHBoxLayout()
        tables.addWidget(self._products_table(), 1)
        tables.addWidget(self._stores_table(), 1)
        layout.addLayout(tables)
        return panel

    @staticmethod
    def _report_metric(symbol, value, caption, delta, color, background):
        card = _panel(name="metricCard")
        card.setMinimumHeight(80)
        row = QHBoxLayout(card)
        row.setContentsMargins(8, 8, 8, 8)
        row.addWidget(_icon(symbol, color, background, 44))
        text = QVBoxLayout()
        text.addWidget(_label(value, "reportMetric"))
        text.addWidget(_label(caption, "small"))
        row.addLayout(text, 1)
        row.addWidget(_chip(delta, GREEN if "↑" in delta else RED, "#e8f9f1" if "↑" in delta else "#ffeaef", 50))
        return card

    @staticmethod
    def _chart_card(title, chart):
        card = _panel(name="chartCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 6)
        layout.addWidget(_label(title, "sectionTitle"))
        layout.addWidget(chart)
        return card

    @staticmethod
    def _products_table():
        data = (
            ("1", "🎧  Audífonos Bluetooth", "Tecnología", "320", "$ 5,760", "↑ 18%"),
            ("2", "🎒  Mochila escolar", "Escolar", "280", "$ 5,040", "↑ 12%"),
            ("3", "👕  Playera K-pop", "Ropa", "250", "$ 4,750", "↑ 8%"),
            ("4", "🎃  Decoración Halloween", "Decoración", "200", "$ 3,800", "↓ 5%"),
            ("5", "📘  Cuaderno universitario", "Papelería", "180", "$ 2,880", "↑ 11%"),
        )
        return ReportsView._small_table("Productos más vendidos", ("#", "Producto", "Categoría", "Unidades", "Ingresos", "Variación"), data)

    @staticmethod
    def _stores_table():
        data = (
            ("Tienda Centro", "$ 9,850", "██████  38%", "↑ 14%"),
            ("Tienda Norte", "$ 6,780", "████  27%", "↑ 9%"),
            ("Tienda Sur", "$ 5,230", "███  21%", "↓ 3%"),
            ("Tienda Online", "$ 3,570", "██  14%", "↑ 22%"),
        )
        return ReportsView._small_table("Ventas por tienda", ("Tienda", "Ventas", "Participación", "Variación"), data)

    @staticmethod
    def _small_table(title, headers, data):
        panel = _panel(name="chartCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 7, 8, 7)
        heading = QHBoxLayout()
        heading.addWidget(_label(title + "  ⓘ", "sectionTitle"))
        heading.addStretch()
        heading.addWidget(_label("Ver todos", "link"))
        layout.addLayout(heading)
        table = QTableWidget(len(data), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide()
        table.setShowGrid(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setFixedHeight(190)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, values in enumerate(data):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if "↑" in value:
                    item.setForeground(QColor(GREEN))
                elif "↓" in value:
                    item.setForeground(QColor(RED))
                elif "█" in value:
                    item.setForeground(QColor(PURPLE))
                table.setItem(row, column, item)
            table.setRowHeight(row, 23)
        layout.addWidget(table)
        return panel

    def _actions(self):
        row = QHBoxLayout()
        for text, color, callback in (
            ("PDF   Exportar PDF", "#e52643", lambda: self._export("PDF", "pdf")),
            ("XLS   Exportar Excel", "#08a757", lambda: self._export("Excel", "xlsx")),
            ("PRINT   Imprimir", "#2864e8", self._print),
        ):
            button = QPushButton(text, objectName="export")
            button.setStyleSheet(f"background:{color};")
            button.clicked.connect(callback)
            row.addWidget(button, 1)
        return row

    def _select_report(self, index):
        self.report_title.setText(self.REPORTS[index][1])

    def _generate(self):
        QMessageBox.information(self, "Reporte generado", f"{self.report_title.text()} actualizado con los filtros seleccionados.")

    def _export(self, name, extension):
        path, _ = QFileDialog.getSaveFileName(self, f"Exportar {name}", str(Path.home() / f"reporte_flamar.{extension}"), f"{name} (*.{extension})")
        if path:
            QMessageBox.information(self, "Exportación", f"El reporte se exportará en:\n{path}")

    def _print(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Imprimir reporte")
        dialog.exec()

    @staticmethod
    def extra_style():
        return _Page.extra_style() + """
            QLabel#filterLabel { color:#081433; font-size:9px; font-weight:700; }
            QPushButton#reportType { background:white; border:1px solid #e0e6ef; border-radius:8px; text-align:left; }
            QPushButton#reportType:hover { border-color:#9b8aff; }
            QPushButton#reportType:checked { background:#fbfaff; border:1px solid #694cff; }
            QLabel#typeTitle { color:#081433; font-size:10px; font-weight:750; }
            QLabel#reportTitle { color:#081433; font-size:20px; font-weight:800; }
            QFrame#metricCard, QFrame#chartCard { background:white; border:1px solid #e1e7f0; border-radius:8px; }
            QLabel#reportMetric { color:#081433; font-size:15px; font-weight:800; }
            QLabel#link { color:#5525f5; font-size:9px; font-weight:700; }
            QTableWidget { color:#152343; background:white; border:0; font-size:8px; }
            QTableWidget::item { border-bottom:1px solid #e8edf3; padding:2px; }
            QHeaderView::section { color:#152343; background:#f7f9fc; border:0; border-bottom:1px solid #e1e7f0; padding:4px; font-size:7px; font-weight:700; }
            QPushButton#export { color:white; border:0; border-radius:7px; min-height:38px; font-size:11px; font-weight:750; }
        """
