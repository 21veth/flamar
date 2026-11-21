"""Pestana de importacion de inventario con calculo visual de stock."""

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from views.import_shared import (
    EXPIRY_WINDOW_DAYS,
    GREEN,
    ORANGE,
    PREVIEW_ROWS,
    PURPLE,
    RED,
    ImportTab,
    RowError,
    apply_row_color,
    header_indexes,
    make_table,
    normalize_header,
    parse_date,
    parse_number,
    update_table,
)


def _fmt(value):
    value = float(value)
    if value.is_integer():
        return f'{value:,.0f}'
    return f'{value:,.2f}'


def _fmt_signed(value):
    value = float(value)
    text = _fmt(abs(value))
    return f'+{text}' if value >= 0 else f'-{text}'


class InventoryImportTab(ImportTab):
    TITLE = 'Importar datos de inventario'
    SUBTITLE = 'Registra entradas, salidas y ajustes para calcular el stock por producto.'

    COLUMNS = (
        'Código del producto',
        'Producto',
        'Categoría',
        'Fecha del movimiento',
        'Tipo de movimiento',
        'Cantidad',
        'Stock anterior',
        'Stock resultante',
        'Fecha de vencimiento',
    )
    REQUIRED = COLUMNS[:-1]
    ALIASES = {
        'Código del producto': ('Codigo', 'Codigo producto', 'SKU'),
        'Fecha del movimiento': ('Fecha', 'Fecha movimiento'),
        'Tipo de movimiento': ('Tipo', 'Movimiento', 'Tipo movimiento'),
        'Stock anterior': ('Stock previo', 'Saldo anterior', 'Stock inicial'),
        'Stock resultante': ('Stock final', 'Saldo resultante', 'Stock nuevo'),
        'Fecha de vencimiento': ('Vencimiento', 'Fecha vencimiento', 'Vence'),
    }
    STOCK_COLUMNS = (
        'Código',
        'Producto',
        'Stock inicial',
        'Entradas',
        'Salidas',
        'Ajustes',
        'Stock final',
    )

    METRICS = (
        ('products', '▦', 'Total de productos', PURPLE, '#f0edff'),
        ('entries', '↑', 'Entradas', GREEN, '#e8f8f1'),
        ('exits', '↓', 'Salidas', RED, '#ffedf0'),
        ('expiring', '!', 'Proximos a vencer', ORANGE, '#fff5e5'),
    )

    def preview_headers(self):
        return self.COLUMNS

    def sample_rows(self):
        today = date.today()
        return (
            (
                'P001', 'Atun en lata 170 g', 'Conservas',
                (today - timedelta(days=12)).strftime('%d/%m/%Y'), 'Entrada',
                '60', '0', '60', (today + timedelta(days=20)).strftime('%d/%m/%Y'),
            ),
            (
                'P001', 'Atun en lata 170 g', 'Conservas',
                (today - timedelta(days=5)).strftime('%d/%m/%Y'), 'Salida',
                '18', '60', '42', '',
            ),
            (
                'P002', 'Durazno en almibar 820 g', 'Conservas',
                (today - timedelta(days=10)).strftime('%d/%m/%Y'), 'Entrada',
                '40', '0', '40', (today + timedelta(days=8)).strftime('%d/%m/%Y'),
            ),
            (
                'P003', 'Arroz extra 5 kg', 'Abarrotes',
                (today - timedelta(days=9)).strftime('%d/%m/%Y'), 'Entrada',
                '75', '0', '75', (today + timedelta(days=90)).strftime('%d/%m/%Y'),
            ),
            (
                'P003', 'Arroz extra 5 kg', 'Abarrotes',
                (today - timedelta(days=3)).strftime('%d/%m/%Y'), 'Salida',
                '25', '75', '50', '',
            ),
            (
                'P004', 'Azucar rubia 1 kg', 'Abarrotes',
                (today - timedelta(days=7)).strftime('%d/%m/%Y'), 'Ajuste',
                '-5', '30', '25', '',
            ),
            (
                'P005', 'Leche evaporada 400 g', 'Lacteos',
                (today - timedelta(days=6)).strftime('%d/%m/%Y'), 'Entrada',
                '48', '0', '48', (today + timedelta(days=25)).strftime('%d/%m/%Y'),
            ),
        )

    def build_extra(self):
        card = QFrame(objectName='card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(QLabel('Stock calculado por producto', objectName='sectionTitle'))
        head.addStretch()
        head.addWidget(QLabel('Filtrar movimientos', objectName='muted'))
        self.filter_combo = QComboBox(objectName='importFilter')
        self.filter_combo.addItems((
            'Todos los movimientos',
            'Solo entradas',
            'Solo salidas',
            'Solo ajustes',
        ))
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        head.addWidget(self.filter_combo)
        layout.addLayout(head)

        note = QLabel(
            'El stock se calcula con las entradas y salidas del archivo. '
            'Los ajustes se aplican como correcciones sobre el stock anterior.',
            objectName='importNote',
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.stock_table = make_table(self.STOCK_COLUMNS, (), height=172)
        layout.addWidget(self.stock_table)
        return card

    def validate_data(self, data):
        errors = []
        indexes = header_indexes(data.headers, self.COLUMNS, self.ALIASES)
        for label in self.REQUIRED:
            if indexes[label] is None:
                errors.append(RowError('-', label, 'Columna requerida no encontrada'))
        if errors:
            return errors

        expiry_index = indexes['Fecha de vencimiento']
        for number, row in enumerate(data.rows, start=2):
            fecha = parse_date(data.value(row, indexes['Fecha del movimiento']))
            if fecha is None:
                errors.append(RowError(number, 'Fecha del movimiento', 'Fecha invalida o vacia'))

            tipo = self._movement_type(data.value(row, indexes['Tipo de movimiento']))
            if not tipo:
                errors.append(RowError(
                    number,
                    'Tipo de movimiento',
                    'Debe ser Entrada, Salida o Ajuste',
                ))

            cantidad = parse_number(data.value(row, indexes['Cantidad']))
            if cantidad is None or cantidad == 0:
                errors.append(RowError(number, 'Cantidad', 'Debe ser un numero distinto de 0'))

            anterior = parse_number(data.value(row, indexes['Stock anterior']))
            if anterior is None:
                errors.append(RowError(number, 'Stock anterior', 'Debe ser un numero'))

            resultante = parse_number(data.value(row, indexes['Stock resultante']))
            if resultante is None:
                errors.append(RowError(number, 'Stock resultante', 'Debe ser un numero'))

            if tipo and cantidad is not None and anterior is not None and resultante is not None:
                if tipo == 'salida':
                    expected = anterior - cantidad
                else:
                    expected = anterior + cantidad
                if abs(expected - resultante) > 0.001:
                    errors.append(RowError(
                        number,
                        'Stock resultante',
                        f'No coincide: se esperaba {_fmt(expected)}',
                    ))

            if expiry_index is not None:
                raw_expiry = str(data.value(row, expiry_index)).strip()
                if raw_expiry and parse_date(raw_expiry) is None:
                    errors.append(RowError(
                        number,
                        'Fecha de vencimiento',
                        'Fecha invalida',
                    ))
        return errors

    def compute_metrics(self, data):
        analysis = self._analyze(data)
        return {
            'products': f'{analysis["products"]:,}',
            'entries': f'{analysis["entries"]:,.0f}',
            'exits': f'{analysis["exits"]:,.0f}',
            'expiring': f'{analysis["expiring"]:,}',
        }

    def on_data_loaded(self, data, is_sample=False):
        self._headers = list(data.headers)
        self._all_rows = [list(row) for row in data.rows]
        self._indexes = header_indexes(data.headers, self.COLUMNS, self.ALIASES)
        analysis = self._analyze(data)
        update_table(self.stock_table, self.STOCK_COLUMNS, analysis['stock_rows'])
        self._apply_filter()

    def process_summary(self, data):
        metrics = self.compute_metrics(data)
        return (
            f'Inventario procesado: {metrics["products"]} productos, '
            f'{metrics["entries"]} entradas y {metrics["exits"]} salidas.'
        )

    # -- calculos ----------------------------------------------------------
    @staticmethod
    def _movement_type(value):
        text = normalize_header(value)
        if text.startswith('entrada'):
            return 'entrada'
        if text.startswith('salida'):
            return 'salida'
        if text.startswith('ajuste'):
            return 'ajuste'
        return ''

    def _analyze(self, data):
        indexes = header_indexes(data.headers, self.COLUMNS, self.ALIASES)
        expiry_index = indexes['Fecha de vencimiento']
        today = date.today()
        entries = 0.0
        exits = 0.0
        expiring = 0
        groups = {}

        for row in data.rows:
            tipo = self._movement_type(data.value(row, indexes['Tipo de movimiento']))
            quantity = parse_number(data.value(row, indexes['Cantidad'])) or 0.0
            if tipo == 'entrada':
                entries += quantity
            elif tipo == 'salida':
                exits += quantity

            code = str(data.value(row, indexes['Código del producto'])).strip()
            name = str(data.value(row, indexes['Producto'])).strip()
            key = code or name
            if key:
                group = groups.setdefault(key, {'code': code, 'name': name, 'rows': []})
                group['rows'].append((
                    data.value(row, indexes['Fecha del movimiento']),
                    tipo,
                    quantity,
                    parse_number(data.value(row, indexes['Stock anterior'])),
                    parse_number(data.value(row, indexes['Stock resultante'])),
                ))

            if expiry_index is not None:
                expiry = parse_date(data.value(row, expiry_index))
                if expiry is not None and expiry <= today + timedelta(days=EXPIRY_WINDOW_DAYS):
                    expiring += 1

        return {
            'products': len(groups),
            'entries': entries,
            'exits': exits,
            'expiring': expiring,
            'stock_rows': self._stock_rows(groups),
        }

    @staticmethod
    def _stock_rows(groups):
        result = []
        for group in groups.values():
            movements = sorted(
                group['rows'],
                key=lambda item: parse_date(item[0]) or date.max,
            )
            start = next(
                (item[3] for item in movements if item[3] is not None),
                0.0,
            )
            entries = exits = adjustments = 0.0
            for _, tipo, quantity, _, _ in movements:
                if tipo == 'entrada':
                    entries += quantity
                elif tipo == 'salida':
                    exits += quantity
                elif tipo == 'ajuste':
                    adjustments += quantity
            final = start + entries - exits + adjustments
            result.append((
                group['code'],
                group['name'],
                _fmt(start),
                _fmt(entries),
                _fmt(exits),
                _fmt_signed(adjustments),
                _fmt(final),
            ))
        result.sort(key=lambda row: (row[0], row[1]))
        return result

    # -- filtros -----------------------------------------------------------
    def _apply_filter(self, *_args):
        if not hasattr(self, '_all_rows'):
            return
        selected = self.filter_combo.currentText() if hasattr(self, 'filter_combo') else ''
        wanted = {
            'Solo entradas': 'entrada',
            'Solo salidas': 'salida',
            'Solo ajustes': 'ajuste',
        }.get(selected)

        if wanted is None:
            filtered = self._all_rows
        else:
            filtered = [
                row for row in self._all_rows
                if self._movement_type(
                    self._value(row, self._indexes['Tipo de movimiento'])
                ) == wanted
            ]

        shown = filtered[:PREVIEW_ROWS]
        update_table(self.preview, self._headers, shown, numbered=True)
        if self.data is None:
            self.preview_caption.setText(
                f'Datos de ejemplo · {len(filtered)} movimientos'
            )
        else:
            self.preview_caption.setText(
                f'Mostrando {len(shown)} de {len(filtered):,} movimientos'
            )
        self._highlight_expiry(shown)

    def _highlight_expiry(self, rows):
        expiry_index = self._indexes.get('Fecha de vencimiento')
        if expiry_index is None:
            return
        limit = date.today() + timedelta(days=EXPIRY_WINDOW_DAYS)
        for row_index, row in enumerate(rows):
            expiry = parse_date(self._value(row, expiry_index))
            if expiry is not None and expiry <= limit:
                apply_row_color(self.preview, row_index, RED, '#ffe9eb')

    @staticmethod
    def _value(row, index):
        if index is None or index < 0 or index >= len(row):
            return ''
        return row[index]
