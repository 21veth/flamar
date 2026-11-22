"""Componentes compartidos del modulo Importar datos.

Incluye la lectura real de archivos CSV/XLSX/XLS, los widgets reutilizables y
la clase base de cada pestana. No realiza ninguna operacion de base de datos.
"""

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


INK = '#09142f'
MUTED = '#60708f'
PURPLE = '#5133f5'
GREEN = '#08a66c'
RED = '#ef334e'
ORANGE = '#ff9815'
BLUE = '#268df0'
BORDER = '#dfe5ee'

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
MAX_FILE_BYTES = 50 * 1024 * 1024
PREVIEW_ROWS = 10
FULL_VIEW_LIMIT = 5000
EXPIRY_WINDOW_DAYS = 30


class ImportFileError(Exception):
    """El archivo no se pudo leer o no cumple el formato esperado."""


@dataclass
class TableData:
    path: Path | None
    name: str
    extension: str
    size_bytes: int
    modified: datetime | None
    headers: list
    rows: list
    total: int
    is_sample: bool = False
    sheet: str | None = None

    def value(self, row, index):
        if index is None or index < 0 or index >= len(row):
            return ''
        return row[index]


@dataclass
class RowError:
    row: object
    field: str
    problem: str


# ---------------------------------------------------------------------------
# Utilidades de datos
# ---------------------------------------------------------------------------

def normalize_header(text):
    value = unicodedata.normalize('NFKD', str(text or ''))
    value = ''.join(char for char in value if not unicodedata.combining(char))
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def header_indexes(headers, labels, aliases=None):
    """Devuelve un diccionario etiqueta -> indice de columna (o None)."""
    aliases = aliases or {}
    normalized = [normalize_header(header) for header in headers]
    result = {}
    for label in labels:
        candidates = [normalize_header(label)]
        candidates += [normalize_header(alias) for alias in aliases.get(label, ())]
        result[label] = next(
            (index for index, header in enumerate(normalized) if header in candidates),
            None,
        )
    return result


def parse_number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(' ', '').replace('\u00a0', '')
    text = text.replace('S/', '').replace('$', '').replace('€', '')
    if not text:
        return None
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        parts = text.split(',')
        if len(parts) == 2 and len(parts[-1]) == 3 and len(parts[0]) > 3:
            text = text.replace(',', '')
        else:
            text = text.replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or '').strip()
    if not text:
        return None
    text = text.split(' ')[0]
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%y', '%Y/%m/%d'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def cell_to_text(value):
    if value is None:
        return ''
    if isinstance(value, datetime):
        if value.hour == 0 and value.minute == 0 and value.second == 0:
            return value.strftime('%d/%m/%Y')
        return value.strftime('%d/%m/%Y %H:%M')
    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _elegir_hoja(nombres, solicitada=None, activa=None):
    if solicitada and solicitada in nombres:
        return solicitada
    for nombre in nombres:
        if normalize_header(nombre) == 'catalogo':
            return nombre
    if activa in nombres:
        return activa
    return nombres[0] if nombres else None


def _read_csv(path):
    last_error = None
    for encoding in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            with path.open('r', encoding=encoding, newline='') as source:
                sample = source.read(4096)
                source.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                except csv.Error:
                    dialect = csv.excel
                raw = [
                    row for row in csv.reader(source, dialect)
                    if any(str(cell).strip() for cell in row)
                ]
            if raw:
                return [[cell_to_text(cell) for cell in row] for row in raw]
        except (UnicodeError, OSError) as exc:
            last_error = exc
    if last_error is not None:
        raise ImportFileError('No se pudo leer el CSV. Verifica la codificacion del archivo.')
    raise ImportFileError('El archivo CSV esta vacio o no contiene datos.')


def _read_xlsx(path, sheet=None):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ImportFileError('Falta la libreria openpyxl para leer archivos XLSX.') from exc
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except (OSError, ValueError, KeyError) as exc:
        raise ImportFileError('No se pudo abrir el archivo XLSX.') from exc
    try:
        nombre_hoja = _elegir_hoja(
            workbook.sheetnames, sheet, workbook.active.title
        )
        hoja = workbook[nombre_hoja]
        raw = []
        for row in hoja.iter_rows(values_only=True):
            if row is None:
                continue
            values = [cell_to_text(cell) for cell in row]
            if any(value.strip() for value in values):
                raw.append(values)
    finally:
        workbook.close()
    if not raw:
        raise ImportFileError('El archivo XLSX esta vacio o no contiene datos.')
    return raw, nombre_hoja


def _read_xls(path, sheet=None):
    try:
        import xlrd
    except ImportError as exc:
        raise ImportFileError('Falta la libreria xlrd para leer archivos XLS.') from exc
    try:
        workbook = xlrd.open_workbook(str(path))
    except (OSError, xlrd.XLRDError) as exc:
        raise ImportFileError('No se pudo abrir el archivo XLS.') from exc
    nombre_hoja = _elegir_hoja(workbook.sheet_names(), sheet)
    sheet = workbook.sheet_by_name(nombre_hoja)
    raw = []
    for row_index in range(sheet.nrows):
        values = []
        for column_index in range(sheet.ncols):
            cell = sheet.cell(row_index, column_index)
            value = cell.value
            if cell.ctype == xlrd.XL_CELL_DATE:
                try:
                    value = xlrd.xldate_as_datetime(value, workbook.datemode)
                except (ValueError, TypeError):
                    value = cell.value
            values.append(cell_to_text(value))
        if any(value.strip() for value in values):
            raw.append(values)
    if not raw:
        raise ImportFileError('El archivo XLS esta vacio o no contiene datos.')
    return raw, nombre_hoja


def read_table_file(path, sheet=None):
    file_path = Path(path)
    if not file_path.is_file():
        raise ImportFileError('El archivo seleccionado no existe.')
    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ImportFileError('Formato no soportado. Usa CSV, XLSX o XLS.')
    size = file_path.stat().st_size
    if size == 0:
        raise ImportFileError('El archivo esta vacio.')
    if size > MAX_FILE_BYTES:
        raise ImportFileError('El archivo supera el limite de 50 MB.')

    nombre_hoja = None
    if suffix == '.csv':
        raw = _read_csv(file_path)
    elif suffix == '.xlsx':
        raw, nombre_hoja = _read_xlsx(file_path, sheet)
    else:
        raw, nombre_hoja = _read_xls(file_path, sheet)

    headers = [str(header).strip() for header in raw[0]]
    rows = [list(row) for row in raw[1:]]
    total = len(rows)
    if total == 0:
        raise ImportFileError('El archivo solo contiene encabezados, sin registros.')

    return TableData(
        path=file_path,
        name=file_path.name,
        extension=suffix,
        size_bytes=size,
        modified=datetime.fromtimestamp(file_path.stat().st_mtime),
        headers=headers,
        rows=rows,
        total=total,
        sheet=nombre_hoja,
    )


def format_size(size_bytes):
    if size_bytes < 1024:
        return f'{size_bytes} B'
    if size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    return f'{size_bytes / 1024 / 1024:.1f} MB'


# ---------------------------------------------------------------------------
# Tablas y dialogos
# ---------------------------------------------------------------------------

def make_table(headers, rows, height=240, numbered=False, object_name='importTable'):
    labels = tuple(str(header) for header in headers)
    if numbered:
        labels = ('#',) + labels
    table = QTableWidget(len(rows), len(labels), objectName=object_name)
    table.setHorizontalHeaderLabels(labels)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.horizontalHeader().setMinimumSectionSize(64)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.NoSelection)
    table.setFocusPolicy(Qt.NoFocus)
    table.setShowGrid(False)
    table.setAlternatingRowColors(False)
    table.setMinimumHeight(height)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    update_table(table, headers, rows, numbered=numbered)
    return table


def update_table(table, headers, rows, numbered=False):
    offset = 1 if numbered else 0
    labels = tuple(str(header) for header in headers)
    if numbered:
        labels = ('#',) + labels
    table.setColumnCount(len(labels))
    table.setHorizontalHeaderLabels(labels)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        if numbered:
            table.setItem(row_index, 0, QTableWidgetItem(str(row_index + 1)))
        for column_index, header in enumerate(headers):
            value = row[column_index] if column_index < len(row) else ''
            item = QTableWidgetItem(str(value))
            alignment = Qt.AlignVCenter | (
                Qt.AlignLeft if column_index + offset in (0, 1, 2) else Qt.AlignCenter
            )
            item.setTextAlignment(alignment)
            table.setItem(row_index, column_index + offset, item)


def apply_row_color(table, row_index, color, background):
    from PySide6.QtGui import QColor
    for column_index in range(table.columnCount()):
        item = table.item(row_index, column_index)
        if item is not None:
            item.setForeground(QColor(color))
            item.setBackground(QColor(background))


class FullViewDialog(QDialog):
    def __init__(self, parent, title, headers, rows):
        super().__init__(parent)
        self.setWindowTitle(f'Vista completa - {title}')
        self.resize(1040, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel(
            f'{len(rows):,} registros en el archivo. Se muestran hasta {FULL_VIEW_LIMIT:,}.',
            objectName='muted',
        ))
        shown = rows[:FULL_VIEW_LIMIT]
        table = make_table(headers, shown, height=500, numbered=True, object_name='importTable')
        layout.addWidget(table)
        footer = QHBoxLayout()
        footer.addStretch()
        close = QPushButton('Cerrar', objectName='primaryButton')
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)


class ErrorsDialog(QDialog):
    def __init__(self, parent, errors, total):
        super().__init__(parent)
        self.setWindowTitle('Errores de validacion')
        self.resize(820, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel(
            f'{len(errors):,} problema(s) detectado(s) en {total:,} registros.',
            objectName='sectionTitle',
        ))
        layout.addWidget(QLabel(
            'Corrige el archivo de origen y vuelve a cargarlo para continuar.',
            objectName='muted',
        ))
        rows = [(error.row, error.field, error.problem) for error in errors[:500]]
        table = make_table(
            ('Fila', 'Campo', 'Problema detectado'),
            rows,
            height=380,
            object_name='importTable',
        )
        layout.addWidget(table)
        if len(errors) > 500:
            layout.addWidget(QLabel(
                f'Se muestran los primeros 500 de {len(errors):,} problemas.',
                objectName='muted',
            ))
        footer = QHBoxLayout()
        footer.addStretch()
        close = QPushButton('Entendido', objectName='primaryButton')
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)


# ---------------------------------------------------------------------------
# Widgets compartidos
# ---------------------------------------------------------------------------

class Stepper(QWidget):
    def __init__(self, titles, parent=None):
        super().__init__(parent)
        self.titles = titles
        self.numbers = []
        self.labels = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for index, title in enumerate(titles, 1):
            number = QLabel(str(index), objectName='step')
            number.setAlignment(Qt.AlignCenter)
            number.setFixedSize(34, 34)
            label = QLabel(title, objectName='stepTitle')
            layout.addWidget(number)
            layout.addWidget(label)
            self.numbers.append(number)
            self.labels.append(label)
            if index < len(titles):
                line = QFrame(objectName='stepLine')
                line.setFixedHeight(1)
                layout.addWidget(line, 1)
        self.set_step(1)

    def set_step(self, step):
        for index, (number, label) in enumerate(zip(self.numbers, self.labels), 1):
            active = index == step
            number.setObjectName('stepActive' if active else 'step')
            label.setObjectName('stepTitleActive' if active else 'stepTitle')
            for widget in (number, label):
                widget.style().unpolish(widget)
                widget.style().polish(widget)


class FileDropZone(QFrame):
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, objectName='dropZone')
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMinimumHeight(262)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(5)
        layout.addStretch()
        icon = QLabel('☁↑', objectName='dropIcon')
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        title = QLabel('Arrastra y suelta tu archivo aqui', objectName='uploadTitle')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        hint = QLabel('o haz clic para seleccionar', objectName='muted')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        choose = QPushButton('Seleccionar archivo', objectName='secondaryButton')
        choose.setFixedWidth(230)
        choose.clicked.connect(self.clicked.emit)
        layout.addWidget(choose, alignment=Qt.AlignCenter)
        formats = QLabel('Formatos soportados: CSV, XLSX, XLS\nTamano maximo: 50 MB', objectName='muted')
        formats.setAlignment(Qt.AlignCenter)
        layout.addWidget(formats)
        layout.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() in ALLOWED_EXTENSIONS:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        path = event.mimeData().urls()[0].toLocalFile()
        self.file_dropped.emit(path)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class FileInfoCard(QFrame):
    replace_requested = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, objectName='card')
        self.setMinimumHeight(262)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.addWidget(QLabel('Detalles del archivo', objectName='sectionTitle'))
        header.addStretch()
        self.status = QLabel('Sin archivo', objectName='idleChip')
        header.addWidget(self.status)
        layout.addLayout(header)
        layout.addSpacing(8)

        self.file_name = QLabel('Sin archivo seleccionado', objectName='detailValue')
        self.file_type = QLabel('-', objectName='detailValue')
        self.file_size = QLabel('-', objectName='detailValue')
        self.record_count = QLabel('-', objectName='detailValue')
        self.modified = QLabel('-', objectName='detailValue')

        for icon, name, value in (
            ('▣', 'Nombre del archivo', self.file_name),
            ('▤', 'Tipo de archivo', self.file_type),
            ('●', 'Tamano del archivo', self.file_size),
            ('☷', 'Registros detectados', self.record_count),
            ('□', 'Fecha de modificacion', self.modified),
        ):
            row = QFrame(objectName='detailRow')
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(7, 3, 7, 3)
            badge = QLabel(icon, objectName='detailIcon')
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(27, 27)
            row_layout.addWidget(badge)
            row_layout.addWidget(QLabel(name, objectName='muted'))
            row_layout.addStretch()
            row_layout.addWidget(value)
            layout.addWidget(row)

        layout.addSpacing(6)
        actions = QHBoxLayout()
        actions.addStretch()
        self.replace_button = QPushButton('Reemplazar archivo', objectName='secondaryButton')
        self.replace_button.clicked.connect(self.replace_requested.emit)
        self.delete_button = QPushButton('Eliminar archivo', objectName='dangerButton')
        self.delete_button.clicked.connect(self.delete_requested.emit)
        actions.addWidget(self.replace_button)
        actions.addWidget(self.delete_button)
        layout.addLayout(actions)
        self.set_data(None)

    def set_data(self, data):
        if data is None:
            self.status.setText('Sin archivo')
            self.status.setObjectName('idleChip')
            self.file_name.setText('Sin archivo seleccionado')
            self.file_type.setText('-')
            self.file_size.setText('-')
            self.record_count.setText('-')
            self.modified.setText('-')
            self.replace_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            self.status.setText('Archivo cargado')
            self.status.setObjectName('goodChip')
            self.file_name.setText(data.name)
            self.file_type.setText(data.extension.replace('.', '').upper())
            self.file_size.setText(format_size(data.size_bytes))
            self.record_count.setText(f'{data.total:,}')
            self.modified.setText(
                data.modified.strftime('%d/%m/%Y %H:%M') if data.modified else '-'
            )
            self.replace_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)


# ---------------------------------------------------------------------------
# Clase base de pestana
# ---------------------------------------------------------------------------

class ImportTab(QWidget):
    TITLE = 'Importar datos'
    SUBTITLE = ''
    METRICS = ()
    STEP_TITLES = ('Seleccionar archivo', 'Validar datos', 'Procesar datos')
    PREVIEW_HEIGHT = 286

    def __init__(self, parent=None):
        super().__init__(parent, objectName='importTab')
        self.setStyleSheet(IMPORT_STYLES)
        self.data = None
        self.errors = []
        self.metric_labels = {}

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 8, 0, 0)
        self.root.setSpacing(12)

        self._build_header()
        self._build_metrics()
        self._build_stepper()
        self._build_top()
        self._build_preview()
        self._build_extra()
        self.reset()

    # -- construccion ------------------------------------------------------
    def _build_header(self):
        block = QVBoxLayout()
        block.setSpacing(2)
        block.addWidget(QLabel(self.TITLE, objectName='importTabTitle'))
        if self.SUBTITLE:
            block.addWidget(QLabel(self.SUBTITLE, objectName='subtitle'))
        self.root.addLayout(block)

    def _build_metrics(self):
        if not self.METRICS:
            return
        grid = QGridLayout()
        grid.setSpacing(10)
        for column, (key, icon, label, color, background) in enumerate(self.METRICS):
            card = QFrame(objectName='importMetric')
            card.setFixedHeight(90)
            layout = QHBoxLayout(card)
            layout.setContentsMargins(13, 11, 13, 11)
            layout.setSpacing(11)
            badge = QLabel(icon, objectName='importMetricIcon')
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(44, 44)
            badge.setStyleSheet(f'background: {background}; color: {color};')
            layout.addWidget(badge)
            text = QVBoxLayout()
            text.setSpacing(1)
            text.addStretch()
            value = QLabel('0', objectName='importMetricValue')
            value.setStyleSheet(f'color: {color};')
            self.metric_labels[key] = value
            text.addWidget(value)
            text.addWidget(QLabel(label, objectName='importMetricLabel'))
            text.addStretch()
            layout.addLayout(text, 1)
            grid.addWidget(card, 0, column)
            grid.setColumnStretch(column, 1)
        self.root.addLayout(grid)

    def _build_stepper(self):
        self.stepper = Stepper(self.STEP_TITLES)
        self.root.addWidget(self.stepper)

    def _build_top(self):
        grid = QGridLayout()
        grid.setSpacing(12)
        self.drop = FileDropZone()
        self.drop.file_dropped.connect(self.load_file)
        self.drop.clicked.connect(self.choose_file)
        self.details = FileInfoCard()
        self.details.replace_requested.connect(self.choose_file)
        self.details.delete_requested.connect(self.clear_file)
        grid.addWidget(self.drop, 0, 0)
        grid.addWidget(self.details, 0, 1)
        grid.setColumnStretch(0, 11)
        grid.setColumnStretch(1, 10)
        self.root.addLayout(grid)

    def _build_preview(self):
        card = QFrame(objectName='card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(9)
        head = QHBoxLayout()
        head.addWidget(QLabel('Vista previa de los datos', objectName='sectionTitle'))
        head.addStretch()
        self.preview_caption = QLabel('', objectName='muted')
        head.addWidget(self.preview_caption)
        self.full_button = QPushButton('↗  Vista completa', objectName='secondaryButton')
        self.full_button.clicked.connect(self.show_full_view)
        self.full_button.setEnabled(False)
        head.addWidget(self.full_button)
        layout.addLayout(head)

        self.preview = make_table(
            self.preview_headers(),
            self.sample_rows(),
            height=self.PREVIEW_HEIGHT,
            numbered=True,
        )
        layout.addWidget(self.preview)

        foot = QHBoxLayout()
        self.footer_message = QLabel('Selecciona un archivo para comenzar.', objectName='muted')
        self.footer_message.setWordWrap(True)
        foot.addWidget(self.footer_message, 1)
        self.cancel_button = QPushButton('Cancelar', objectName='secondaryButton')
        self.cancel_button.clicked.connect(self.clear_file)
        self.validate_button = QPushButton('Validar datos', objectName='secondaryButton')
        self.validate_button.clicked.connect(self.validate_file)
        self.process_button = QPushButton('Procesar datos', objectName='primaryButton')
        self.process_button.clicked.connect(self.process_file)
        for button in (self.cancel_button, self.validate_button, self.process_button):
            button.setMinimumHeight(38)
            foot.addWidget(button)
        layout.addLayout(foot)
        self.root.addWidget(card)

    def _build_extra(self):
        extra = self.build_extra()
        if extra is not None:
            self.root.addWidget(extra)

    # -- hooks para subclases ---------------------------------------------
    def preview_headers(self):
        return ('Datos',)

    def sample_rows(self):
        return ()

    def build_extra(self):
        return None

    def validate_data(self, data):
        return []

    def compute_metrics(self, data):
        return {}

    def on_data_loaded(self, data, is_sample=False):
        pass

    def process_summary(self, data):
        return f'Se procesarian {data.total:,} registros de "{self.TITLE}".'

    # -- estado ------------------------------------------------------------
    def reset(self):
        self.data = None
        self.errors = []
        sample = TableData(
            path=None,
            name='',
            extension='',
            size_bytes=0,
            modified=None,
            headers=list(self.preview_headers()),
            rows=[list(row) for row in self.sample_rows()],
            total=len(self.sample_rows()),
            is_sample=True,
        )
        self.details.set_data(None)
        self.set_step(1)
        self.validate_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.full_button.setEnabled(False)
        self._render(sample)
        self.preview_caption.setText(f'Datos de ejemplo · {sample.total} registros')
        self.footer_message.setText(
            'Datos de ejemplo. Selecciona un archivo real para reemplazarlos.'
        )
        self.on_data_loaded(sample, is_sample=True)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Seleccionar archivo de datos',
            '',
            'Archivos de datos (*.csv *.xlsx *.xls)',
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            data = read_table_file(path)
        except ImportFileError as exc:
            QMessageBox.warning(self, 'No se pudo leer el archivo', str(exc))
            return
        self.data = data
        self.errors = []
        self.details.set_data(data)
        self.set_step(1)
        self._render(data)
        self.preview_caption.setText(
            f'Mostrando {min(PREVIEW_ROWS, data.total)} de {data.total:,} registros'
        )
        self.footer_message.setText(
            f'Archivo cargado: {data.name}. Pulsa "Validar datos" para revisar {data.total:,} registros.'
        )
        self.validate_button.setEnabled(True)
        self.process_button.setEnabled(False)
        self.full_button.setEnabled(True)
        self.on_data_loaded(data, is_sample=False)

    def clear_file(self):
        self.reset()

    def _render(self, data):
        update_table(
            self.preview,
            data.headers,
            data.rows[:PREVIEW_ROWS],
            numbered=True,
        )
        self.update_metrics(self.compute_metrics(data))

    def update_metrics(self, values):
        for key, label in self.metric_labels.items():
            label.setText(str(values.get(key, '0')))

    def set_step(self, step):
        if hasattr(self, 'stepper'):
            self.stepper.set_step(step)

    def show_full_view(self):
        if self.data is None:
            return
        FullViewDialog(self.window(), self.TITLE, self.data.headers, self.data.rows).exec()

    def validate_file(self):
        if self.data is None:
            QMessageBox.information(
                self, 'Sin archivo', 'Selecciona un archivo antes de validar.'
            )
            return
        self.errors = self.validate_data(self.data)
        self.set_step(2)
        if self.errors:
            self.process_button.setEnabled(False)
            self.footer_message.setText(
                f'{len(self.errors):,} problema(s) detectado(s). Revisa el detalle para corregirlos.'
            )
            ErrorsDialog(self.window(), self.errors, self.data.total).exec()
        else:
            self.process_button.setEnabled(True)
            self.footer_message.setText(
                f'Validacion correcta: {self.data.total:,} registros listos para procesar.'
            )
            QMessageBox.information(
                self,
                'Validacion correcta',
                f'No se encontraron problemas en {self.data.total:,} registros.',
            )

    def process_file(self):
        if self.data is None:
            return
        self.set_step(3)
        rejected_rows = {error.row for error in self.errors if error.row}
        rejected = len(rejected_rows)
        valid = max(self.data.total - rejected, 0)
        summary = self.process_summary(self.data)
        details = (
            f'Registros leidos: {self.data.total:,}\n'
            f'Registros validos: {valid:,}\n'
            f'Registros rechazados: {rejected:,}\n'
            f'Advertencias: {len(self.errors):,}'
        )
        self.footer_message.setText(
            'Procesamiento demostrativo completado. No se guardo informacion en la base de datos.'
        )
        QMessageBox.information(
            self,
            'Procesamiento demostrativo',
            f'{summary}\n\n{details}\n\n'
            'Esta es una demostracion: no se guardo nada en la base de datos.',
        )


# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------

IMPORT_STYLES = '''
QWidget#importTab { background: transparent; }
QLabel#importTabTitle { color: #08132d; font-size: 20px; font-weight: 800; }
QFrame#importMetric { background: white; border: 1px solid #dfe5ee; border-radius: 9px; }
QLabel#importMetricIcon { border-radius: 22px; font-size: 18px; font-weight: 800; }
QLabel#importMetricValue { font-size: 19px; font-weight: 800; }
QLabel#importMetricLabel { color: #34435e; font-size: 10px; font-weight: 700; }
QLabel#dropIcon { color: #5133f5; font-size: 40px; font-weight: 700; }
QFrame#dropZone:hover { background: #f7f5ff; border-color: #5133f5; }
QLabel#idleChip { background: #eef2f7; color: #60708f; border-radius: 6px; padding: 4px 7px; font-size: 10px; font-weight: 700; }
QPushButton#dangerButton { background: white; color: #e62e45; border: 1px solid #f2b8c0; border-radius: 7px; padding: 9px 17px; font-size: 11px; font-weight: 650; }
QPushButton#dangerButton:hover { background: #fff1f3; }
QPushButton#dangerButton:disabled { color: #c7cfda; border-color: #e3e8ef; }
QFrame#stepLine { background: #c4cddb; border: none; }
QLabel#stepTitle { color: #35435d; font-size: 11px; font-weight: 650; }
QTableWidget#importTable { background: white; color: #273754; border: 1px solid #e0e6ef; border-radius: 7px; font-size: 10px; }
QTableWidget#importTable::item { border-bottom: 1px solid #e5eaf1; padding: 3px; }
QTableWidget#importTable QHeaderView::section { background: #f7f9fc; color: #12203a; border: none; border-bottom: 1px solid #dfe5ee; padding: 6px 3px; font-size: 10px; font-weight: 700; }
QLabel#importNote { color: #4e31ed; background: #f3f0ff; border: 1px solid #ded7ff; border-radius: 7px; padding: 8px 10px; font-size: 10px; }
QComboBox#importFilter { background: white; color: #263752; border: 1px solid #d4deea; border-radius: 6px; padding: 6px 8px; font-size: 10px; min-height: 16px; }
'''

__all__ = [
    'ImportFileError',
    'TableData',
    'RowError',
    'read_table_file',
    'normalize_header',
    'header_indexes',
    'parse_number',
    'parse_date',
    'format_size',
    'make_table',
    'update_table',
    'apply_row_color',
    'FullViewDialog',
    'ErrorsDialog',
    'Stepper',
    'FileDropZone',
    'FileInfoCard',
    'ImportTab',
    'IMPORT_STYLES',
    'INK',
    'MUTED',
    'PURPLE',
    'GREEN',
    'RED',
    'ORANGE',
    'BLUE',
    'BORDER',
    'PREVIEW_ROWS',
    'EXPIRY_WINDOW_DAYS',
]
