import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
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


PURPLE = '#553cff'


class _DropPanel(QFrame):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, objectName='drop_panel')
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() in {'.csv', '.xlsx'}:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        path = event.mimeData().urls()[0].toLocalFile()
        self.file_dropped.emit(path)
        event.acceptProposedAction()


class _DataPage(QWidget):
    """Shared page shell and small factories for the two data views."""

    def __init__(self, parent=None):
        super().__init__(parent, objectName='data_page')
        self.setStyleSheet(self._styles())
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(objectName='page_scroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.content = QWidget(objectName='page_content')
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(28, 24, 28, 26)
        self.layout.setSpacing(16)
        scroll.setWidget(self.content)
        root.addWidget(scroll)

    def _header(self, title, subtitle):
        block = QVBoxLayout()
        block.setSpacing(3)
        block.addWidget(QLabel(title, objectName='page_title'))
        block.addWidget(QLabel(subtitle, objectName='subtitle'))
        return block

    @staticmethod
    def _card():
        return QFrame(objectName='card')

    @staticmethod
    def _button(text, primary=False):
        button = QPushButton(text, objectName='primary_button' if primary else 'secondary_button')
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(42)
        return button

    @staticmethod
    def _table(headers, rows, minimum_height):
        table = QTableWidget(len(rows), len(headers), objectName='data_table')
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setMinimumSectionSize(78)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setMinimumHeight(minimum_height)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                table.setItem(row_index, column_index, item)
        return table

    @staticmethod
    def _styles():
        return '''
            QWidget#data_page, QWidget#page_content, QScrollArea#page_scroll {
                background: #f8faff; color: #0b1739;
                font-family: "Segoe UI Variable", "Segoe UI"; border: none;
            }
            QScrollBar:vertical { background: #f1f4f9; width: 8px; }
            QScrollBar::handle:vertical { background: #cbd4e1; border-radius: 4px; min-height: 42px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QLabel#page_title { color: #09142f; font-size: 23px; font-weight: 800; }
            QLabel#subtitle, QLabel#muted { color: #64748b; font-size: 11px; }
            QLabel#section_title { color: #111827; font-size: 14px; font-weight: 750; }
            QFrame#card { background: white; border: 1px solid #dfe5ee; border-radius: 11px; }
            QPushButton#primary_button {
                background: #553cff; color: white; border: none; border-radius: 7px;
                padding: 8px 24px; font-size: 12px; font-weight: 700;
            }
            QPushButton#primary_button:hover { background: #4931eb; }
            QPushButton#primary_button:pressed { background: #3823cf; }
            QPushButton#secondary_button {
                background: white; color: #3f35ed; border: 1px solid #7163ff;
                border-radius: 7px; padding: 8px 22px; font-size: 12px; font-weight: 650;
            }
            QPushButton#secondary_button:hover { background: #f4f2ff; }
            QFrame#drop_panel { background: #fbfbff; border: 2px dashed #6654ff; border-radius: 10px; }
            QLabel#upload_icon { color: #553cff; font-size: 37px; font-weight: 700; }
            QLabel#upload_title { color: #121827; font-size: 14px; font-weight: 750; }
            QLabel#step_active {
                color: #4d35ff; border: 1px solid #553cff; border-radius: 19px;
                min-width: 36px; min-height: 36px; font-size: 12px; font-weight: 750;
            }
            QLabel#step_idle {
                color: #30415f; border: 1px solid #cbd3df; border-radius: 19px;
                min-width: 36px; min-height: 36px; font-size: 12px; font-weight: 700;
            }
            QLabel#step_label_active { color: #4d35ff; font-size: 12px; font-weight: 700; }
            QLabel#step_label { color: #23324c; font-size: 12px; }
            QFrame#step_line { background: #cbd3df; border: none; }
            QFrame#detail_row { border: none; border-bottom: 1px solid #e3e8f0; }
            QLabel#detail_icon { background: #f0edff; color: #553cff; border-radius: 14px; font-weight: 800; }
            QLabel#detail_icon_green { background: #e9f8f1; color: #08a66c; border-radius: 14px; font-weight: 800; }
            QLabel#detail_name { color: #344258; font-size: 11px; }
            QLabel#detail_value { color: #111827; font-size: 11px; font-weight: 700; }
            QTableWidget#data_table {
                background: white; color: #253552; border: 1px solid #dfe5ee;
                border-radius: 8px; gridline-color: #e4e9f1; font-size: 10px;
            }
            QTableWidget#data_table QHeaderView::section {
                background: #fafbfe; color: #111827; border: none;
                border-bottom: 1px solid #dfe5ee; padding: 8px; font-size: 10px; font-weight: 700;
            }
            QTableWidget#data_table::item { border-bottom: 1px solid #e4e9f1; padding: 6px 8px; }
            QLabel#metric_icon { border-radius: 26px; font-size: 24px; font-weight: 700; }
            QLabel#metric_value { font-size: 21px; font-weight: 800; }
            QLabel#metric_label { color: #111827; font-size: 10px; font-weight: 700; }
            QProgressBar#clean_progress {
                border: none; border-radius: 6px; background: #e9edf4; height: 12px; text-align: center;
            }
            QProgressBar#clean_progress::chunk { background: #5745ef; border-radius: 6px; }
            QLabel#progress_value { color: #2544be; font-size: 13px; font-weight: 800; }
        '''


class ImportDataView(_DataPage):
    MOCK_HEADERS = ('Fecha', 'Producto', 'Categoría', 'Cantidad', 'Precio (USD)', 'Stock actual', 'Proveedor', 'Campaña', 'Temporada')
    MOCK_ROWS = (
        ('01/08/2025', 'Audífonos Bluetooth', 'Tecnología', '12', '35.00', '45', 'TechSupply', 'Regreso a clases', 'Verano'),
        ('01/08/2025', 'Mochila escolar', 'Accesorios', '8', '28.50', '32', 'Mundo Escolar', 'Regreso a clases', 'Verano'),
        ('02/08/2025', 'Playera K-pop', 'Ropa', '25', '18.90', '60', 'KStyle', 'K-pop', 'Verano'),
        ('02/08/2025', 'Decoración Halloween', 'Decoración', '40', '12.00', '120', 'DecoMundo', 'Halloween', 'Otoño'),
        ('03/08/2025', 'Cuaderno universitario', 'Papelería', '30', '6.50', '80', 'OfiPlus', 'Regreso a clases', 'Verano'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = None
        self.layout.addLayout(self._header(
            'Importar datos', 'Carga y procesa archivos para integrarlos con tus análisis.'
        ))
        self.layout.addLayout(self._build_stepper())

        top = QGridLayout()
        top.setSpacing(14)
        top.addWidget(self._build_drop_panel(), 0, 0)
        top.addWidget(self._build_details_card(), 0, 1)
        top.setColumnStretch(0, 1)
        top.setColumnStretch(1, 1)
        self.layout.addLayout(top)
        self.layout.addWidget(self._build_preview_card())
        self.layout.addStretch()

    def _build_stepper(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(44, 5, 44, 3)
        for index, label in enumerate(('Seleccionar archivo', 'Validar datos', 'Procesar datos'), 1):
            number = QLabel(str(index), objectName='step_active' if index == 1 else 'step_idle')
            number.setAlignment(Qt.AlignCenter)
            number.setFixedSize(38, 38)
            text = QLabel(label, objectName='step_label_active' if index == 1 else 'step_label')
            layout.addWidget(number)
            layout.addWidget(text)
            if index < 3:
                line = QFrame(objectName='step_line')
                line.setFixedHeight(1)
                layout.addWidget(line, 1)
        return layout

    def _build_drop_panel(self):
        panel = _DropPanel()
        panel.setMinimumHeight(225)
        panel.file_dropped.connect(self._load_file)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 19, 22, 19)
        layout.setSpacing(5)
        layout.addStretch()
        icon = QLabel('☁↑', objectName='upload_icon')
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        title = QLabel('Arrastra y suelta tu archivo aquí', objectName='upload_title')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        or_label = QLabel('o', objectName='muted')
        or_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(or_label)
        choose = self._button('Seleccionar archivo')
        choose.setFixedWidth(215)
        choose.clicked.connect(self._choose_file)
        layout.addWidget(choose, alignment=Qt.AlignCenter)
        formats = QLabel('Formatos soportados: CSV, XLSX, XLS\nTamaño máximo: 50 MB', objectName='muted')
        formats.setAlignment(Qt.AlignCenter)
        layout.addWidget(formats)
        layout.addStretch()
        return panel

    def _build_details_card(self):
        card = self._card()
        card.setMinimumHeight(225)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 15)
        layout.setSpacing(0)
        layout.addWidget(QLabel('Detalles del archivo', objectName='section_title'))
        layout.addSpacing(8)
        self.file_name = QLabel('ventas_agosto_2025.xlsx', objectName='detail_value')
        self.record_count = QLabel('1,248', objectName='detail_value')
        self.import_date = QLabel('18/08/2025 10:24 a. m.', objectName='detail_value')
        for icon, label, value, green in (
            ('▣', 'Nombre del archivo', self.file_name, True),
            ('☷', 'Registros detectados', self.record_count, False),
            ('□', 'Fecha de importación', self.import_date, False),
        ):
            row = QFrame(objectName='detail_row')
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 7, 8, 7)
            badge = QLabel(icon, objectName='detail_icon_green' if green else 'detail_icon')
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(29, 29)
            row_layout.addWidget(badge)
            row_layout.addWidget(QLabel(label, objectName='detail_name'))
            row_layout.addStretch()
            row_layout.addWidget(value)
            layout.addWidget(row)
        return card

    def _build_preview_card(self):
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 13, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel('Vista previa de los datos', objectName='section_title'))
        self.preview = self._table(self.MOCK_HEADERS, self.MOCK_ROWS, 221)
        layout.addWidget(self.preview)
        footer = QHBoxLayout()
        self.preview_caption = QLabel('Mostrando 5 de 1,248 registros  ⓘ', objectName='muted')
        footer.addWidget(self.preview_caption)
        footer.addStretch()
        cancel = self._button('Cancelar')
        cancel.setMinimumWidth(150)
        cancel.clicked.connect(self._reset_mock_data)
        footer.addWidget(cancel)
        validate = self._button('Validar datos', primary=True)
        validate.setMinimumWidth(155)
        validate.clicked.connect(self._validate_data)
        footer.addWidget(validate)
        layout.addLayout(footer)
        return card

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Seleccionar archivo de datos', '', 'Archivos de datos (*.csv *.xlsx)'
        )
        if path:
            self._load_file(path)

    def _load_file(self, path):
        file_path = Path(path)
        if not file_path.is_file() or file_path.stat().st_size > 100 * 1024 * 1024:
            return
        self.selected_path = file_path
        rows = []
        headers = self.MOCK_HEADERS
        total = 0
        if file_path.suffix.lower() == '.csv':
            try:
                with file_path.open('r', encoding='utf-8-sig', newline='') as source:
                    reader = csv.reader(source)
                    headers = tuple(next(reader, self.MOCK_HEADERS))
                    for row in reader:
                        total += 1
                        if len(rows) < 5:
                            rows.append(tuple(row))
            except (OSError, UnicodeError, csv.Error):
                rows = []
        if not rows:
            headers, rows = self.MOCK_HEADERS, self.MOCK_ROWS
            total = 25430 if file_path.suffix.lower() == '.xlsx' else len(rows)
        modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        self.file_name.setText(file_path.name)
        self.record_count.setText(f'{total:,}')
        self.import_date.setText(modified.strftime('%d/%m/%Y %H:%M'))
        self._fill_preview(headers, rows, total)

    def _fill_preview(self, headers, rows, total):
        width = max(len(headers), max((len(row) for row in rows), default=0))
        normalized_headers = list(headers) + [f'Campo {index + 1}' for index in range(len(headers), width)]
        self.preview.setColumnCount(width)
        self.preview.setHorizontalHeaderLabels(normalized_headers)
        self.preview.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index in range(width):
                self.preview.setItem(row_index, column_index, QTableWidgetItem(str(row[column_index]) if column_index < len(row) else ''))
        self.preview_caption.setText(f'Mostrando {len(rows)} de {total:,} registros  ⓘ')

    def _reset_mock_data(self):
        self.selected_path = None
        self.file_name.setText('ventas_agosto_2025.xlsx')
        self.record_count.setText('1,248')
        self.import_date.setText('18/08/2025 10:24 a. m.')
        self._fill_preview(self.MOCK_HEADERS, self.MOCK_ROWS, 1248)

    def _validate_data(self):
        self.sender().setText('Datos validados ✓')
        self.sender().setEnabled(False)


class PreprocessingView(_DataPage):
    ISSUE_HEADERS = ('Fila', 'Campo', 'Valor original', 'Problema detectado', 'Corrección realizada')
    ISSUE_ROWS = (
        ('102', 'Correo', 'juan.perez@', 'Formato de correo inválido', 'juan.perez@email.com'),
        ('245', 'Teléfono', '+52 1 55 1234 5678', 'Formato de teléfono inválido', '+52 55 1234 5678'),
        ('389', 'Edad', '-5', 'Valor fuera de rango', 'Nulo (no aplica)'),
        ('512', 'Fecha de registro', '31/02/2024', 'Fecha inválida', '29/02/2024'),
        ('678', 'Ciudad', 'Cd. de México', 'Valor no estandarizado', 'Ciudad de México'),
        ('901', 'Monto', '12.5.0', 'Formato numérico inválido', '1250.00'),
        ('1,234', 'Nombre', ' Ana  María ', 'Espacios en blanco innecesarios', 'Ana María'),
        ('1,678', 'Código postal', '12A45', 'Caracteres no permitidos', '12445'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout.addLayout(self._header(
            'Preprocesamiento de datos',
            'Revise la calidad de sus datos y corrija problemas antes del análisis.',
        ))
        self.layout.addLayout(self._build_metrics())
        self.layout.addWidget(self._build_progress())
        self.layout.addWidget(self._build_issues())
        self.layout.addWidget(self._build_actions())
        self.layout.addStretch()

    def _build_metrics(self):
        grid = QGridLayout()
        grid.setSpacing(11)
        metrics = (
            ('▤', '25,430', 'Registros totales', 'Total de registros importados', '#5946ff', '#f0edff'),
            ('✓', '23,842', 'Registros válidos', 'Registros listos para analizar', '#079365', '#e8f7f1'),
            ('▱', '852', 'Registros duplicados', 'Posibles duplicados encontrados', '#e58a00', '#fff4df'),
            ('◌', '736', 'Datos incompletos', 'Campos con información faltante', '#f06b00', '#fff0e6'),
            ('!', '124', 'Errores detectados', 'Valores inválidos o fuera de rango', '#df2531', '#ffe9eb'),
        )
        for column, metric in enumerate(metrics):
            grid.addWidget(self._metric_card(*metric), 0, column)
            grid.setColumnStretch(column, 1)
        return grid

    def _metric_card(self, icon, value, label, detail, color, background):
        card = self._card()
        card.setMinimumHeight(125)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(13, 13, 13, 12)
        top = QHBoxLayout()
        badge = QLabel(icon, objectName='metric_icon')
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(52, 52)
        badge.setStyleSheet(f'background: {background}; color: {color};')
        top.addWidget(badge)
        values = QVBoxLayout()
        values.setSpacing(2)
        number = QLabel(value, objectName='metric_value')
        number.setStyleSheet(f'color: {color};')
        values.addWidget(number)
        values.addWidget(QLabel(label, objectName='metric_label'))
        top.addLayout(values, 1)
        layout.addLayout(top)
        detail_label = QLabel(detail, objectName='muted')
        detail_label.setWordWrap(True)
        layout.addWidget(detail_label)
        return card

    def _build_progress(self):
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 13)
        top = QHBoxLayout()
        top.addWidget(QLabel('Progreso de limpieza', objectName='section_title'))
        top.addStretch()
        self.progress_label = QLabel('75%', objectName='progress_value')
        top.addWidget(self.progress_label)
        layout.addLayout(top)
        self.progress = QProgressBar(objectName='clean_progress')
        self.progress.setRange(0, 100)
        self.progress.setValue(75)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        self.progress_detail = QLabel('19,072 de 25,430 registros procesados', objectName='muted')
        layout.addWidget(self.progress_detail)
        return card

    def _build_issues(self):
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 13, 14, 14)
        layout.addWidget(QLabel('Registros con problemas detectados', objectName='section_title'))
        self.issues_table = self._table(self.ISSUE_HEADERS, self.ISSUE_ROWS, 296)
        self.issues_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(self.issues_table)
        return card

    def _build_actions(self):
        card = self._card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 11, 16, 11)
        layout.addStretch()
        automatic = self._button('✣  Limpiar automáticamente')
        automatic.setMinimumWidth(220)
        automatic.clicked.connect(self._automatic_cleanup)
        layout.addWidget(automatic)
        manual = self._button('✎  Corregir manualmente')
        manual.setMinimumWidth(205)
        manual.clicked.connect(self._enable_manual_editing)
        layout.addWidget(manual)
        save = self._button('⇩  Guardar datos procesados', primary=True)
        save.setMinimumWidth(235)
        save.clicked.connect(lambda: save.setText('Datos procesados guardados ✓'))
        layout.addWidget(save)
        return card

    def _automatic_cleanup(self):
        self.progress.setValue(100)
        self.progress_label.setText('100%')
        self.progress_detail.setText('25,430 de 25,430 registros procesados')
        button = self.sender()
        button.setText('Limpieza completada ✓')
        button.setEnabled(False)

    def _enable_manual_editing(self):
        self.issues_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.issues_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sender().setText('Edición habilitada')
