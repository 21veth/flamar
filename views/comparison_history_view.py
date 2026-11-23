from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from views.app_theme import zeyver_stylesheet
from views.import_shared import IMPORT_STYLES
from views.import_results_view import RESULT_STYLES


COMPARISON_DETAIL_STYLES = zeyver_stylesheet('''
QDialog#ComparisonDetailDialog { background:#ffffff; color:#09142f; font-family:"Segoe UI Variable","Segoe UI"; }
QLabel#comparisonTitle { color:#09142f; font-size:18px; font-weight:800; }
QLabel#comparisonSubtitle { color:#60708f; font-size:10px; }
QLabel#comparisonSection { color:#12203a; font-size:12px; font-weight:800; }
QLabel#comparisonValue { color:#5133f5; font-size:20px; font-weight:800; }
QLabel#comparisonReason { color:#34435e; font-size:11px; }
QFrame#comparisonCard { background:#f8fafc; border:1px solid #dfe5ee; border-radius:9px; }
QPushButton#comparisonPrimary { background:#5133f5; color:#ffffff; border:none; border-radius:7px; padding:9px 18px; font-size:11px; font-weight:800; min-width:130px; }
QPushButton#comparisonPrimary:hover { background:#4025c9; }
QPushButton#comparisonSecondary { background:#ffffff; color:#34435e; border:1px solid #dfe5ee; border-radius:7px; padding:9px 18px; font-size:11px; font-weight:800; }
QPushButton#comparisonSecondary:hover { background:#f7f9fc; }
QTableWidget#comparisonDetailTable { background:#ffffff; color:#273754; border:1px solid #dfe5ee; border-radius:8px; font-size:10px; selection-background-color:#ede9fe; selection-color:#5133f5; }
QTableWidget#comparisonDetailTable::item { border-bottom:1px solid #e5eaf1; padding:5px; }
QTableWidget#comparisonDetailTable QHeaderView::section { background:#f7f9fc; color:#12203a; border:none; border-bottom:1px solid #dfe5ee; padding:7px 5px; font-size:10px; font-weight:800; }
QLineEdit#comparisonEditInput, QComboBox#comparisonEditInput, QPlainTextEdit#comparisonEditInput { background:#ffffff; color:#12203a; border:1px solid #dfe5ee; border-radius:6px; padding:7px 9px; font-size:11px; }
QLabel#comparisonEditLabel { color:#34435e; font-size:11px; font-weight:700; }
''')



def _texto(valor):
    if valor is None:
        return '-'
    if isinstance(valor, Decimal):
        return f'{valor:,.2f}'
    return str(valor)


def _money(valor):
    return f'S/ {_texto(valor)}'


def _encabezado(tabla, encabezados):
    tabla.setHorizontalHeaderLabels(encabezados)
    tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
    tabla.setAlternatingRowColors(False)
    tabla.verticalHeader().setVisible(False)
    tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    tabla.horizontalHeader().setMinimumSectionSize(80)


class ComparisonDetailDialog(QDialog):
    repetir = Signal(int)

    def __init__(self, detalle, parent=None):
        super().__init__(parent)
        self.setObjectName('ComparisonDetailDialog')
        self.setWindowTitle(f"Detalle de comparación · {detalle.comparacion.nombre}")
        self.setStyleSheet(IMPORT_STYLES + RESULT_STYLES + COMPARISON_DETAIL_STYLES)
        self.resize(1080, 660)
        self.setMinimumSize(900, 520)
        self.detalle = detalle

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel(detalle.comparacion.nombre, objectName='comparisonTitle'))
        fecha = detalle.comparacion.fecha_creacion
        subtitulo = (
            f"{fecha.strftime('%d/%m/%Y %H:%M')} · "
            f"{detalle.comparacion.tipo_productos or 'Sin categoría'}"
        ) if fecha else (detalle.comparacion.tipo_productos or 'Sin categoría')
        layout.addWidget(QLabel(subtitulo, objectName='comparisonSubtitle'))
        estado_chip = QLabel(
            detalle.comparacion.estado or 'Completada',
            objectName=(
                'resultSuccessChip'
                if detalle.comparacion.estado == 'completada'
                else 'resultNeutralChip'
            ),
        )
        layout.addWidget(estado_chip, alignment=Qt.AlignLeft)

        recomendacion = QFrame(objectName='comparisonCard')
        recomendacion_layout = QVBoxLayout(recomendacion)
        recomendacion_layout.setContentsMargins(14, 12, 14, 12)
        recomendacion_layout.setSpacing(4)
        recomendacion_layout.addWidget(
            QLabel('Proveedor recomendado', objectName='comparisonSection')
        )
        recomendacion_layout.addWidget(
            QLabel(detalle.comparacion.proveedor_recomendado or '-', objectName='comparisonValue')
        )
        costos = QHBoxLayout()
        costos.setSpacing(18)
        costos.addWidget(QLabel(
            f"Costo estimado: {_money(detalle.comparacion.costo_proveedor_recomendado)}",
            objectName='comparisonReason',
        ))
        costos.addWidget(QLabel(
            f"Ahorro estimado: {_money(detalle.comparacion.ahorro_estimado)}",
            objectName='comparisonReason',
        ))
        costos.addWidget(QLabel(
            f"Mejor compra combinada: {_money(detalle.comparacion.costo_compra_combinada)}",
            objectName='comparisonReason',
        ))
        costos.addStretch()
        recomendacion_layout.addLayout(costos)
        layout.addWidget(recomendacion)

        layout.addWidget(QLabel('¿Por qué fue recomendado?', objectName='comparisonSection'))
        razones = QLabel(detalle.comparacion.justificacion or 'Sin justificación guardada.', objectName='comparisonReason')
        razones.setWordWrap(True)
        layout.addWidget(razones)

        layout.addWidget(QLabel('Tabla comparativa guardada', objectName='comparisonSection'))
        self.tabla = QTableWidget(0, 6, objectName='comparisonDetailTable')
        _encabezado(self.tabla, (
            'Producto', 'Categoría', 'Proveedor',
            'Precio evaluado', 'Cantidad', 'Combinada',
        ))
        self.tabla.setRowCount(len(detalle.filas))
        for fila, oferta in enumerate(detalle.filas):
            valores = (
                oferta.producto,
                oferta.categoria,
                oferta.proveedor,
                _money(oferta.precio_evaluado),
                oferta.cantidad_requerida,
                'Sí' if oferta.seleccionado_combinada else 'No',
            )
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(_texto(valor))
                celda.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.tabla.setItem(fila, columna, celda)
        self.tabla.setMinimumHeight(230)
        layout.addWidget(self.tabla, 1)

        acciones = QHBoxLayout()
        acciones.addStretch()
        cerrar = QPushButton('Cerrar', objectName='comparisonSecondary')
        cerrar.clicked.connect(self.accept)
        acciones.addWidget(cerrar)
        layout.addLayout(acciones)

    def _repetir(self):
        self.repetir.emit(self.detalle.comparacion.id_comparacion)
        self.accept()


class ComparisonEditDialog(QDialog):
    guardada = Signal(dict)

    def __init__(self, comparacion, categorias=(), parent=None):
        super().__init__(parent)
        self.setObjectName('ComparisonDetailDialog')
        self.setWindowTitle(f"Editar comparación · {comparacion.nombre}")
        self.setStyleSheet(IMPORT_STYLES + RESULT_STYLES + COMPARISON_DETAIL_STYLES)
        self.resize(520, 420)
        self.setMinimumSize(460, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(QLabel('Editar comparación guardada', objectName='comparisonTitle'))

        formulario = QFormLayout()
        formulario.setSpacing(10)
        self.nombre = QLineEdit(comparacion.nombre, objectName='comparisonEditInput')
        self.categoria = QComboBox(objectName='comparisonEditInput')
        self.categoria.setView(QListView())
        self.categoria.addItem('')
        opciones = list(categorias)
        if comparacion.tipo_productos and comparacion.tipo_productos not in opciones:
            opciones.append(comparacion.tipo_productos)
        self.categoria.addItems(sorted(opciones))
        self.categoria.setCurrentText(comparacion.tipo_productos or '')
        self.justificacion = QPlainTextEdit(
            comparacion.justificacion or '', objectName='comparisonEditInput'
        )
        self.justificacion.setMinimumHeight(130)
        for etiqueta, campo in (
            ('Nombre', self.nombre),
            ('Categoría principal', self.categoria),
            ('Justificación', self.justificacion),
        ):
            formulario.addRow(QLabel(etiqueta, objectName='comparisonEditLabel'), campo)
        layout.addLayout(formulario, 1)

        acciones = QHBoxLayout()
        acciones.addStretch()
        guardar = QPushButton('Guardar cambios', objectName='comparisonPrimary')
        guardar.clicked.connect(self._guardar)
        cancelar = QPushButton('Cancelar', objectName='comparisonSecondary')
        cancelar.clicked.connect(self.reject)
        acciones.addWidget(guardar)
        acciones.addWidget(cancelar)
        layout.addLayout(acciones)

    def _guardar(self):
        nombre = self.nombre.text().strip()
        if not nombre:
            self.nombre.setFocus()
            return
        self.guardada.emit({
            'nombre': nombre,
            'tipo_productos': self.categoria.currentText().strip(),
            'justificacion': self.justificacion.toPlainText().strip(),
        })
        self.accept()


__all__ = [
    'ComparisonDetailDialog',
    'ComparisonEditDialog',
    'COMPARISON_DETAIL_STYLES',
]
