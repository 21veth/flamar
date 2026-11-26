from decimal import Decimal

from PySide6.QtCore import QDate, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.ingresos_inventario_controller import IngresosInventarioController
from views.app_theme import zeyver_stylesheet
from views.import_shared import IMPORT_STYLES


HISTORIAL_COLUMNS = (
    'N.º de ingreso',
    'Fecha de registro',
    'Proveedor',
    'Archivo',
    'Productos',
    'Unidades ingresadas',
    'Costo total',
    'Estado',
    'Acciones',
)

DETALLE_COLUMNS = (
    'Fila',
    'Código',
    'Producto',
    'Marca',
    'Categoría',
    'Presentación',
    'Cantidad',
    'Unidad medida',
    'Precio compra',
    'Subtotal',
    'Precio venta',
    'Stock mínimo',
    'Fecha ingreso',
)

HISTORIAL_STYLES = zeyver_stylesheet('''
QFrame#supplierCard { background: white; border: 1px solid #dfe5ee; border-radius: 9px; }
QLabel#cardTitle { color: #09142f; font-size: 13px; font-weight: 800; }
QLabel#cardHint { color: #60708f; font-size: 10px; }
QTableWidget#supplierTable { background: white; color: #273754; border: none; border-radius: 0px; font-size: 10px; }
QTableWidget#supplierTable::item { border-bottom: 1px solid #e5eaf1; padding: 4px; }
QTableWidget#supplierTable QHeaderView::section { background: #f7f9fc; color: #12203a; border: none; border-bottom: 1px solid #dfe5ee; padding: 7px 5px; font-size: 10px; font-weight: 700; }
QLineEdit#supplierInput, QComboBox#supplierCombo, QDateEdit#supplierCombo { background: white; color: #263752; border: 1px solid #d4deea; border-radius: 6px; padding: 7px 9px; font-size: 10px; }
QComboBox#supplierCombo::drop-down { border: none; width: 22px; subcontrol-origin: padding; subcontrol-position: center right; }
QComboBox#supplierCombo QAbstractItemView { background: #ffffff; color: #263752; border: 1px solid #dfe5ee; border-radius: 6px; outline: 0; padding: 4px; selection-background-color: #ede9fe; selection-color: #5133f5; }
QComboBox#supplierCombo QAbstractItemView::item { padding: 6px 10px; min-height: 24px; border-radius: 4px; }
QPushButton#supplierSecondary { background: white; color: #5133f5; border: 1px solid #c9bcff; border-radius: 7px; padding: 8px 14px; font-size: 11px; font-weight: 700; }
QPushButton#supplierPrimary { background: #5133f5; color: white; border: 0; border-radius: 7px; padding: 9px 18px; font-size: 11px; font-weight: 700; }
QPushButton#historyMostrarButton { background: #ffffff; border: 1px solid #dfe5ee; border-radius: 6px; padding: 2px; width: 27px; height: 25px; }
QPushButton#historyMostrarButton:hover { background: #f4f1ff; border-color: #c9bcff; }
QLabel#goodChip { background: #e8f8f1; color: #087a51; border-radius: 6px; padding: 5px 8px; font-size: 10px; font-weight: 700; }
QLabel#miniLabel { color: #60708f; font-size: 9px; font-weight: 700; }
QLabel#miniValue { color: #09142f; font-size: 13px; font-weight: 800; }
''')

DETALLE_STYLES = zeyver_stylesheet('''
QDialog#IngresoHistorialDialog { background: #ffffff; color: #09142f; font-family: "Segoe UI"; }
QLabel#detalleTitulo { color: #09142f; font-size: 17px; font-weight: 800; }
QLabel#detalleSubtitulo { color: #60708f; font-size: 10px; }
''')


def _texto(valor, defecto='-'):
    if valor is None or valor == '':
        return defecto
    if isinstance(valor, Decimal):
        return f'{valor:,.2f}'
    return str(valor)


def _money(valor):
    if valor is None:
        return 'S/ 0.00'
    if isinstance(valor, Decimal):
        return f'S/ {valor:,.2f}'
    try:
        return f'S/ {Decimal(str(valor)):,.2f}'
    except (TypeError, ValueError):
        return f'S/ {valor}'


def _item(valor, alineacion=Qt.AlignLeft):
    celda = QTableWidgetItem(str(valor))
    celda.setTextAlignment(Qt.AlignVCenter | alineacion)
    celda.setFlags(celda.flags() & ~Qt.ItemIsEditable)
    return celda


def _icono_ver():
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#5133f5'), 1.6, Qt.SolidLine, Qt.RoundCap))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(2, 6, 16, 8))
    painter.drawEllipse(QRectF(7, 8, 6, 4))
    painter.end()
    return QIcon(pixmap)


def _make_table(encabezados, altura, expandir=()):
    tabla = QTableWidget(0, len(encabezados), objectName='supplierTable')
    tabla.setHorizontalHeaderLabels(encabezados)
    tabla.verticalHeader().hide()
    tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tabla.setSelectionMode(QAbstractItemView.NoSelection)
    tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
    tabla.setFocusPolicy(Qt.NoFocus)
    tabla.setShowGrid(False)
    tabla.setFrameShape(QFrame.NoFrame)
    tabla.setMinimumHeight(altura)
    tabla.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    cabecera = tabla.horizontalHeader()
    cabecera.setMinimumSectionSize(70)
    for indice in range(len(encabezados)):
        modo = QHeaderView.Stretch if indice in expandir else QHeaderView.ResizeToContents
        cabecera.setSectionResizeMode(indice, modo)
    return tabla


def _estado_visible(estado):
    return {
        'completada': 'Completado',
        'completado': 'Completado',
        'fallida': 'Fallido',
        'con_errores': 'Con errores',
    }.get(estado or '', _texto(estado))


class HistorialIngresosView(QWidget):
    def __init__(self, controlador=None, parent=None):
        super().__init__(parent, objectName='historialIngresos')
        self.setStyleSheet(IMPORT_STYLES + HISTORIAL_STYLES)
        self.controlador = controlador or IngresosInventarioController()
        self.controlador.listado.connect(self._al_listar)
        self.controlador.detalle_consultado.connect(self._al_detalle)
        self.controlador.fallo.connect(self._al_fallo)
        self.ingresos = []
        self._construir()

    def _construir(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        tarjeta = QFrame(objectName='supplierCard')
        tarjeta_layout = QVBoxLayout(tarjeta)
        tarjeta_layout.setContentsMargins(13, 11, 13, 11)
        tarjeta_layout.setSpacing(8)

        cabecera = QHBoxLayout()
        cabecera.addWidget(
            QLabel('Historial de ingresos de inventario', objectName='cardTitle')
        )
        cabecera.addStretch()
        self.contador = QLabel('0 ingresos', objectName='cardHint')
        cabecera.addWidget(self.contador)
        tarjeta_layout.addLayout(cabecera)
        tarjeta_layout.addWidget(
            QLabel('Consulta la mercadería registrada anteriormente', objectName='cardHint')
        )

        filtros = QHBoxLayout()
        filtros.setSpacing(8)
        self.busqueda = QLineEdit(objectName='supplierInput')
        self.busqueda.setPlaceholderText('Buscar por proveedor o archivo')
        self.proveedor = QComboBox(objectName='supplierCombo')
        self.proveedor.setView(QListView())
        self.proveedor.addItem('Todos los proveedores')
        self.estado = QComboBox(objectName='supplierCombo')
        self.estado.setView(QListView())
        self.estado.addItems(('Completado', 'Todos los estados'))
        self.fecha = QDateEdit(objectName='supplierCombo')
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat('dd/MM/yyyy')
        self.fecha.setMinimumDate(QDate(2000, 1, 1))
        self.fecha.setSpecialValueText('Todas las fechas')
        self.fecha.setDate(self.fecha.minimumDate())
        self.actualizar = QPushButton('Actualizar', objectName='supplierSecondary')
        self.actualizar.clicked.connect(self.recargar)
        filtros.addWidget(self.busqueda, 2)
        filtros.addWidget(self.proveedor, 1)
        filtros.addWidget(self.estado, 1)
        filtros.addWidget(self.fecha, 1)
        filtros.addWidget(self.actualizar)
        tarjeta_layout.addLayout(filtros)

        self.tabla = _make_table(HISTORIAL_COLUMNS, 320, (2, 3))
        tarjeta_layout.addWidget(self.tabla)
        layout.addWidget(tarjeta)

        self.estado_texto = QLabel('', objectName='cardHint')
        layout.addWidget(self.estado_texto)

        self.busqueda.textChanged.connect(self.recargar)
        self.proveedor.currentTextChanged.connect(self.recargar)
        self.estado.currentTextChanged.connect(self.recargar)
        self.fecha.dateChanged.connect(self.recargar)

    def recargar(self):
        self.estado_texto.setText('')
        self.controlador.listar(
            busqueda=self.busqueda.text(),
            proveedor=self._proveedor_filtro(),
            estado=self._estado_filtro(),
            fecha=self._fecha_filtro(),
        )

    def _proveedor_filtro(self):
        valor = self.proveedor.currentText()
        return '' if valor.startswith('Todos') else valor

    def _estado_filtro(self):
        return '' if self.estado.currentText().startswith('Todos') else 'completada'

    def _fecha_filtro(self):
        if self.fecha.date() == self.fecha.minimumDate():
            return ''
        return self.fecha.date().toString('yyyy-MM-dd')

    def _sin_filtros(self):
        return (
            not self.busqueda.text().strip()
            and not self._proveedor_filtro()
            and not self._fecha_filtro()
        )

    def _al_listar(self, ingresos):
        self.ingresos = list(ingresos or [])
        if self._sin_filtros():
            self._actualizar_proveedores()
        self.contador.setText(f'{len(self.ingresos)} ingreso(s)')
        self._llenar_tabla()
        if not self.ingresos:
            self.estado_texto.setText('No hay ingresos registrados.')

    def _actualizar_proveedores(self):
        anterior = self.proveedor.currentText()
        opciones = sorted({
            str(ingreso.proveedor)
            for ingreso in self.ingresos
            if getattr(ingreso, 'proveedor', None)
        })
        self.proveedor.blockSignals(True)
        self.proveedor.clear()
        self.proveedor.addItem('Todos los proveedores')
        self.proveedor.addItems(opciones)
        indice = self.proveedor.findText(anterior)
        self.proveedor.setCurrentIndex(indice if indice >= 0 else 0)
        self.proveedor.blockSignals(False)

    def _llenar_tabla(self):
        self.tabla.setRowCount(len(self.ingresos))
        for fila_actual, ingreso in enumerate(self.ingresos):
            fecha = getattr(ingreso, 'creado_en', None)
            fecha_texto = (
                fecha.strftime('%d/%m/%Y')
                if hasattr(fecha, 'strftime') else _texto(fecha)
            )
            valores = (
                f"#{getattr(ingreso, 'id_ingreso', '-')}",
                fecha_texto,
                _texto(getattr(ingreso, 'proveedor', None)),
                _texto(getattr(ingreso, 'archivo', None)),
                _texto(getattr(ingreso, 'productos', 0), '0'),
                _texto(getattr(ingreso, 'unidades', 0), '0'),
                _money(getattr(ingreso, 'costo_total', None)),
                _estado_visible(getattr(ingreso, 'estado', None)),
            )
            for columna, valor in enumerate(valores):
                alineacion = Qt.AlignLeft if columna in (2, 3) else Qt.AlignCenter
                self.tabla.setItem(fila_actual, columna, _item(valor, alineacion))
            acciones = QWidget()
            disposicion = QHBoxLayout(acciones)
            disposicion.setContentsMargins(2, 0, 2, 0)
            disposicion.setSpacing(4)
            boton = QPushButton(objectName='historyMostrarButton')
            boton.setIcon(_icono_ver())
            boton.setToolTip('Ver detalle')
            boton.clicked.connect(
                lambda checked=False, fila=fila_actual: self._ver(fila)
            )
            disposicion.addWidget(boton)
            self.tabla.setCellWidget(fila_actual, 8, acciones)
        self.tabla.resizeRowsToContents()

    def _ver(self, indice):
        try:
            ingreso = self.ingresos[indice]
        except IndexError:
            return
        self.controlador.obtener_detalle(ingreso.id_ingreso)

    def _al_detalle(self, detalle):
        if detalle is None:
            self.estado_texto.setText('No se pudo abrir el detalle del ingreso.')
            return
        dialogo = IngresoHistorialDialog(detalle, parent=self.window() or self)
        dialogo.exec()

    def _al_fallo(self, mensaje):
        self.estado_texto.setText(f'No se pudo cargar el historial: {mensaje}')


class IngresoHistorialDialog(QDialog):
    def __init__(self, ingreso, parent=None):
        super().__init__(parent, objectName='IngresoHistorialDialog')
        self.setModal(True)
        self.setWindowTitle(f'Detalle del ingreso N.º {ingreso.id_ingreso}')
        self.setStyleSheet(IMPORT_STYLES + HISTORIAL_STYLES + DETALLE_STYLES)
        self.resize(1180, 640)
        self.setMinimumSize(980, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel(
            f'Ingreso N.º {ingreso.id_ingreso:03d} — {ingreso.proveedor}',
            objectName='detalleTitulo',
        ))
        fecha = getattr(ingreso, 'creado_en', None)
        fecha_texto = (
            fecha.strftime('%d/%m/%Y %H:%M')
            if hasattr(fecha, 'strftime') else _texto(fecha)
        )
        layout.addWidget(QLabel(
            f'{ingreso.archivo} · Registrado: {fecha_texto} · '
            f'Responsable: {_texto(getattr(ingreso, "responsable", None))} · '
            f'Estado: {_estado_visible(getattr(ingreso, "estado", None))}',
            objectName='detalleSubtitulo',
        ))

        resumen = QFrame(objectName='supplierCard')
        resumen_layout = QHBoxLayout(resumen)
        resumen_layout.setContentsMargins(14, 12, 14, 12)
        resumen_layout.setSpacing(14)
        for titulo, valor in (
            ('Productos distintos', _texto(ingreso.numero_productos, '0')),
            ('Unidades ingresadas', _texto(ingreso.total_unidades, '0')),
            ('Costo total', _money(getattr(ingreso, 'costo_total', None))),
            ('Estado', _estado_visible(getattr(ingreso, 'estado', None))),
        ):
            bloque = QVBoxLayout()
            bloque.setSpacing(2)
            bloque.addWidget(QLabel(titulo, objectName='miniLabel'))
            bloque.addWidget(QLabel(valor, objectName='miniValue'))
            resumen_layout.addLayout(bloque, 1)
        layout.addWidget(resumen)

        tabla = _make_table(DETALLE_COLUMNS, 300, (2,))
        tabla.setRowCount(len(ingreso.filas))
        for fila_actual, fila in enumerate(ingreso.filas):
            fecha_ingreso = (
                fila.fecha_ingreso.strftime('%d/%m/%Y')
                if hasattr(fila.fecha_ingreso, 'strftime')
                else _texto(fila.fecha_ingreso)
            )
            valores = (
                fila.numero_fila,
                _texto(fila.codigo),
                _texto(fila.producto),
                _texto(fila.marca),
                _texto(fila.categoria),
                _texto(fila.presentacion),
                fila.cantidad,
                _texto(fila.unidad_medida),
                _money(fila.precio_compra),
                _money(fila.subtotal),
                _money(fila.precio_venta),
                fila.stock_minimo,
                fecha_ingreso,
            )
            for columna, valor in enumerate(valores):
                alineacion = Qt.AlignLeft if columna in (1, 2, 3, 4, 5) else Qt.AlignCenter
                tabla.setItem(fila_actual, columna, _item(valor, alineacion))
        layout.addWidget(tabla, 1)

        pie = QHBoxLayout()
        pie.addStretch()
        cerrar = QPushButton('Cerrar', objectName='supplierPrimary')
        cerrar.clicked.connect(self.accept)
        pie.addWidget(cerrar)
        layout.addLayout(pie)


__all__ = ['HistorialIngresosView', 'IngresoHistorialDialog']
