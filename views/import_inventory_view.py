"""Pestana de importacion de ingresos de inventario."""

import logging

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from views.app_theme import zeyver_stylesheet
from services.importacion_inventarios_pg import (
    ContextoPostgresIngresos,
    PersistenciaPostgresIngresos,
)
from services.importacion_inventarios_service import ImportacionIngresosService
from views.import_shared import (
    IMPORT_STYLES,
    FileDropZone,
    FileInfoCard,
    ImportTab,
    update_table,
)
from views.tabla_paginada import TablaPaginada


MAX_FILE_BYTES = 10 * 1024 * 1024
FILE_FILTER = 'Archivos Excel (*.xlsx)'
PREVIEW_COLUMNS = ('Fila', 'Código', 'Producto', 'Estado')
CONFIRM_COLUMNS = (
    'Fila',
    'Código',
    'Producto',
    'Categoría',
    'Marca',
    'Presentación',
    'Cantidad',
    'Precio compra',
    'Precio venta',
    'Fecha ingreso',
    'Unidad medida',
    'Stock mínimo',
    'Estado producto',
    'Estado',
)
DETALLE_INGRESO_COLUMNS = (
    'Fila',
    'Código',
    'Producto',
    'Categoría',
    'Cantidad',
    'Stock mínimo',
    'Precio compra',
    'Precio venta',
    'Unidad medida',
    'Fecha ingreso',
)


INVENTORY_STYLES = zeyver_stylesheet('''
QLabel#validationHeading { color: #08132d; font-size: 17px; font-weight: 800; }
QLabel#validationLead { color: #60708f; font-size: 11px; }
QLabel#validationError { color: #ef334e; font-size: 11px; font-weight: 700; }
QFrame#summaryCard { background: white; border: 1px solid #dfe5ee; border-radius: 9px; }
QFrame#summaryDivider { background: #e5e7eb; border: none; min-width: 1px; max-width: 1px; }
QLabel#confirmSummaryKey { color: #60708f; font-size: 10px; font-weight: 700; }
QLabel#confirmSummaryValue { color: #12203a; font-size: 11px; font-weight: 700; }
QLabel#confirmReadOnly { color: #60708f; font-size: 10px; }
QLabel#confirmCaption { color: #60708f; font-size: 10px; }
QLineEdit#confirmSearch { background: white; border: 1px solid #dfe5ee; border-radius: 6px; padding: 7px 10px; font-size: 11px; }
QComboBox#confirmFilter { background: white; border: 1px solid #dfe5ee; border-radius: 6px; padding: 6px 10px; font-size: 11px; }
QPushButton#primaryButton:disabled { background: #c7cfda; color: #f4f7fb; }
''')


@dataclass
class ArchivoIngresoSeleccionado:
    path: Path
    name: str
    extension: str
    size_bytes: int
    modified: datetime | None
    total: int = 0


class IngresoDropZone(FileDropZone):
    def __init__(self, parent=None):
        super().__init__(parent)
        for label in self.findChildren(QLabel):
            if label.text().startswith('Formatos soportados'):
                label.setText('Formato permitido: XLSX · Tamaño máximo sugerido: 10 MB')

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() == '.xlsx':
            event.acceptProposedAction()


class InventoryFileInfoCard(FileInfoCard):
    def set_data(self, data):
        super().set_data(data)
        self.record_count.setText('Pendiente de validación' if data is not None else '-')


class InventoryImportTab(ImportTab):
    ingreso_guardado = Signal(object)
    TITLE = 'Registro de ingreso de productos'
    SUBTITLE = 'Importa la mercadería recibida por ZEYVER.'
    STEP_TITLES = (
        'Seleccionar archivo Excel',
        'Vista previa y validación',
        'Guardar y mostrar resultado',
    )

    def __init__(self, parent=None, sesion=None, servicio=None):
        self.sesion = sesion
        if servicio is None:
            contexto = ContextoPostgresIngresos()
            servicio = ImportacionIngresosService(
                contexto=contexto,
                persistencia=PersistenciaPostgresIngresos(contexto=contexto),
            )
        self.servicio = servicio
        super().__init__(parent)
        self.setStyleSheet(IMPORT_STYLES + INVENTORY_STYLES)
        self.archivo = None
        self.reporte = None
        self.confirmacion = None
        self.resultado_guardado = None
        self._productos_vista_previa = ()
        self.validate_button.setText('Cargar archivo')
        self.reset()

    def preview_headers(self):
        return ('Archivo',)

    def sample_rows(self):
        return ()

    def _build_header(self):
        self.header_block = QWidget()
        block = QVBoxLayout(self.header_block)
        block.setContentsMargins(0, 0, 0, 0)
        block.setSpacing(2)
        block.addWidget(QLabel(self.TITLE, objectName='importTabTitle'))
        if self.SUBTITLE:
            block.addWidget(QLabel(self.SUBTITLE, objectName='subtitle'))
        self.root.addWidget(self.header_block)

    def _build_top(self):
        self.upload_page = QWidget()
        grid = QGridLayout(self.upload_page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        self.drop = IngresoDropZone()
        self.drop.file_dropped.connect(self.load_file)
        self.drop.clicked.connect(self.choose_file)
        self.details = InventoryFileInfoCard()
        self.details.replace_requested.connect(self.choose_file)
        self.details.delete_requested.connect(self.clear_file)
        grid.addWidget(self.drop, 0, 0)
        grid.addWidget(self.details, 0, 1)
        grid.setColumnStretch(0, 11)
        grid.setColumnStretch(1, 10)
        self.root.addWidget(self.upload_page)

    def _build_preview(self):
        super()._build_preview()
        self.upload_actions = self.root.itemAt(self.root.count() - 1).widget()

    def _build_extra(self):
        self._build_preview_page()
        self._build_result_page()

    def _build_preview_page(self):
        self.preview_page = QFrame(objectName='card')
        self.confirm_page = self.preview_page
        layout = QVBoxLayout(self.preview_page)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        cabecera = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(QLabel('Vista previa del ingreso', objectName='validationHeading'))
        self.validation_lead = QLabel(
            'Productos, cantidades, precios y resultado de las validaciones.',
            objectName='validationLead',
        )
        textos.addWidget(self.validation_lead)
        cabecera.addLayout(textos, 1)
        self.validation_status = QLabel('Sin revisar', objectName='warningChip')
        cabecera.addWidget(self.validation_status)
        layout.addLayout(cabecera)

        resumen = QFrame(objectName='summaryCard')
        resumen_layout = QHBoxLayout(resumen)
        resumen_layout.setContentsMargins(14, 12, 14, 12)
        resumen_layout.setSpacing(14)
        self.preview_summary_values = {}
        bloques = []
        for clave, titulo in (
            ('proveedor', 'Proveedor'),
            ('archivo', 'Archivo Excel'),
            ('registros', 'Registros'),
            ('validos', 'Válidos'),
            ('unidades', 'Total de unidades'),
            ('fecha', 'Fecha de ingreso'),
        ):
            columna = QVBoxLayout()
            columna.setSpacing(2)
            columna.addWidget(QLabel(titulo, objectName='confirmSummaryKey'))
            valor = QLabel('-', objectName='confirmSummaryValue')
            valor.setWordWrap(True)
            columna.addWidget(valor)
            self.preview_summary_values[clave] = valor
            bloques.append(columna)
        for indice, bloque in enumerate(bloques):
            resumen_layout.addLayout(bloque, 1)
            if indice < len(bloques) - 1:
                divisor = QFrame(objectName='summaryDivider')
                divisor.setFixedWidth(1)
                resumen_layout.addWidget(divisor)
        self.confirm_summary_values = self.preview_summary_values
        layout.addWidget(resumen)

        herramientas = QHBoxLayout()
        herramientas.setSpacing(8)
        self.confirm_search = QLineEdit(objectName='confirmSearch')
        self.confirm_search.setPlaceholderText('Buscar por código o nombre...')
        self.confirm_search.setFixedWidth(240)
        self.confirm_filter = QComboBox(objectName='confirmFilter')
        self.confirm_filter.addItem('Todas las categorías')
        self.confirm_filter.setFixedWidth(180)
        self.confirm_filter.setView(QListView())
        self.confirm_filter.setMaxVisibleItems(12)
        self.confirm_search.textChanged.connect(self._filtrar_confirmacion)
        self.confirm_filter.currentTextChanged.connect(self._filtrar_confirmacion)
        herramientas.addWidget(self.confirm_search)
        herramientas.addWidget(self.confirm_filter)
        herramientas.addStretch()
        herramientas.addWidget(QLabel(
            'Solo lectura · Vuelve a cargar el Excel desde el paso 1 para actualizar la vista.',
            objectName='confirmReadOnly',
        ))
        layout.addLayout(herramientas)

        self.confirm_table = TablaPaginada(
            0, len(CONFIRM_COLUMNS), objectName='importTable'
        )
        self.confirm_table.setHorizontalHeaderLabels(CONFIRM_COLUMNS)
        self.confirm_table.verticalHeader().hide()
        self.confirm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.confirm_table.horizontalHeader().setMinimumSectionSize(78)
        self.confirm_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.confirm_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.confirm_table.setFocusPolicy(Qt.NoFocus)
        self.confirm_table.setShowGrid(False)
        self.confirm_table.setMinimumHeight(330)
        self.confirm_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.confirm_table)

        self.confirm_status = QLabel('', objectName='validationLead')
        self.confirm_status.setWordWrap(True)
        layout.addWidget(self.confirm_status)

        pie = QHBoxLayout()
        self.confirm_caption = QLabel(
            'Mostrando 0 de 0 productos · Solo lectura',
            objectName='confirmCaption',
        )
        pie.addWidget(self.confirm_caption)
        pie.addStretch()
        self.confirm_back = QPushButton('Volver', objectName='secondaryButton')
        self.confirm_back.clicked.connect(self._volver_paso_1)
        self.confirm_button = QPushButton('Confirmar y guardar', objectName='primaryButton')
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self._confirmar)
        for boton in (self.confirm_back, self.confirm_button):
            boton.setMinimumHeight(38)
        pie.addWidget(self.confirm_back)
        pie.addWidget(self.confirm_button)
        layout.addLayout(pie)
        self.root.addWidget(self.preview_page)

    def _build_result_page(self):
        self.result_page = QFrame(objectName='card')
        layout = QVBoxLayout(self.result_page)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel('Resultado de la importación', objectName='validationHeading'))
        self.result_detail = QLabel('', objectName='validationLead')
        self.result_detail.setWordWrap(True)
        layout.addWidget(self.result_detail)
        self.result_status = QLabel('', objectName='confirmReadOnly')
        self.result_status.setWordWrap(True)
        layout.addWidget(self.result_status)

        self.result_metric_values = {}
        metricas = QGridLayout()
        metricas.setSpacing(10)
        for columna, (clave, titulo) in enumerate((
            ('productos', 'Productos procesados'),
            ('lineas', 'Líneas guardadas'),
            ('incidencias', 'Incidencias'),
            ('estado', 'Estado'),
        )):
            tarjeta = QFrame(objectName='summaryCard')
            tarjeta_layout = QVBoxLayout(tarjeta)
            tarjeta_layout.setContentsMargins(12, 10, 12, 10)
            tarjeta_layout.setSpacing(4)
            tarjeta_layout.addWidget(QLabel(titulo, objectName='confirmSummaryKey'))
            valor = QLabel('-', objectName='confirmSummaryValue')
            self.result_metric_values[clave] = valor
            tarjeta_layout.addWidget(valor)
            metricas.addWidget(tarjeta, 0, columna)
        layout.addLayout(metricas)

        pie = QHBoxLayout()
        pie.addStretch()
        self.result_back = QPushButton('Ver ingreso registrado', objectName='secondaryButton')
        self.result_back.setEnabled(False)
        self.result_back.clicked.connect(self._ver_ingreso)
        self.result_finish = QPushButton('Importar otro Excel', objectName='primaryButton')
        self.result_finish.clicked.connect(self.reset)
        for boton in (self.result_back, self.result_finish):
            boton.setMinimumHeight(38)
        pie.addWidget(self.result_back)
        pie.addWidget(self.result_finish)
        layout.addLayout(pie)
        self.root.addWidget(self.result_page)

    def _mostrar_paso(self, paso):
        self.header_block.setVisible(paso == 1)
        self.upload_page.setVisible(paso == 1)
        self.upload_actions.setVisible(paso == 1)
        self.preview_page.setVisible(paso == 2)
        self.result_page.setVisible(paso == 3)
        self.stepper.set_step(paso)

    def _volver_paso_1(self):
        self._mostrar_paso(1)

    def _volver_paso_2(self):
        self._mostrar_paso(2)

    def _reset_vista_previa(self):
        self.confirmacion = None
        self._productos_vista_previa = ()
        self.validation_status.setText('Sin revisar')
        self.validation_status.setObjectName('warningChip')
        self.validation_status.style().unpolish(self.validation_status)
        self.validation_status.style().polish(self.validation_status)
        self.validation_lead.setText(
            'Productos, cantidades, precios y resultado de las validaciones.'
        )
        for valor in self.preview_summary_values.values():
            valor.setText('-')
        self._set_confirm_status('')
        self.confirm_caption.setText('Mostrando 0 de 0 productos · Solo lectura')
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText('Confirmar y guardar')
        self.confirm_search.blockSignals(True)
        self.confirm_search.clear()
        self.confirm_search.blockSignals(False)
        self.confirm_filter.blockSignals(True)
        self.confirm_filter.clear()
        self.confirm_filter.addItem('Todas las categorías')
        self.confirm_filter.setCurrentIndex(0)
        self.confirm_filter.blockSignals(False)
        update_table(self.confirm_table, CONFIRM_COLUMNS, ())
        self.confirm_table.actualizar_paginacion()

    @staticmethod
    def _estado_visible(estado):
        return {'Válido': 'Listo', 'Error': 'Revisar'}.get(estado, estado)

    def _filtrar_confirmacion(self):
        termino = self.confirm_search.text().strip().casefold()
        categoria = self.confirm_filter.currentText()
        filas = []
        for producto in self._productos_vista_previa:
            if (
                categoria != 'Todas las categorías'
                and producto.categoria != categoria
            ):
                continue
            if termino and (
                termino not in producto.codigo.casefold()
                and termino not in producto.producto.casefold()
            ):
                continue
            filas.append((
                producto.numero_fila,
                producto.codigo,
                producto.producto,
                producto.categoria,
                producto.marca,
                producto.presentacion,
                producto.cantidad,
                producto.precio_compra,
                producto.precio_venta,
                producto.fecha_ingreso,
                producto.unidad_medida,
                producto.stock_minimo,
                producto.estado_producto,
                self._estado_visible(producto.estado),
            ))
        update_table(self.confirm_table, CONFIRM_COLUMNS, filas)
        self.confirm_table.actualizar_paginacion()
        self.confirm_caption.setText(
            f'Mostrando {len(filas)} de {len(self._productos_vista_previa)} productos · Solo lectura'
        )

    def _reset_resultado(self):
        self.resultado_guardado = None
        self.result_detail.clear()
        self.result_status.clear()
        for valor in self.result_metric_values.values():
            valor.setText('-')
        self.result_back.setEnabled(False)

    def _set_confirm_status(self, mensaje, error=False):
        object_name = 'validationError' if error else 'validationLead'
        self.confirm_status.setObjectName(object_name)
        self.confirm_status.setText(mensaje)
        self.confirm_status.style().unpolish(self.confirm_status)
        self.confirm_status.style().polish(self.confirm_status)

    @staticmethod
    def _detalle_error(exc):
        texto = str(exc).strip()
        if not texto:
            diagnostico = getattr(exc, 'diag', None)
            texto = str(getattr(diagnostico, 'message', '') or '').strip()
        if not texto:
            texto = 'sin mensaje del servidor'
        return f'{type(exc).__name__}: {texto}'

    @staticmethod
    def _mensaje_errores(reporte):
        errores = list(reporte.errores)
        if not errores:
            return ''
        detalles = []
        for aviso in errores[:3]:
            fila = f'Fila {aviso.numero_fila} · ' if aviso.numero_fila else ''
            valor = (
                f' "{aviso.valor_original}"'
                if aviso.valor_original not in (None, '') else ''
            )
            detalles.append(f'{fila}{aviso.campo}:{valor} {aviso.problema}')
        if len(errores) > 3:
            detalles.append(f'+{len(errores) - 3} más')
        return (
            f'Validación con {len(errores)} error(es) bloqueante(s): '
            + '; '.join(detalles)
            + '. Vuelve a cargar un Excel corregido para continuar.'
        )

    def _mensaje_bloqueo(self, reporte):
        if reporte is None:
            return 'No hay una validación disponible. Carga el archivo de nuevo.'
        if not reporte.es_valido:
            return self._mensaje_errores(reporte)
        if not reporte.filas_validas:
            return 'No hay productos válidos para guardar. Revisa el Excel y vuelve a cargarlo.'
        return 'No se puede guardar este ingreso.'

    def _confirmar(self):
        if (
            self.reporte is None
            or not self.reporte.es_valido
            or not self.reporte.filas_validas
        ):
            self._set_confirm_status(self._mensaje_bloqueo(self.reporte), error=True)
            return
        id_usuario = getattr(self.sesion, 'id_usuario', None)
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText('Guardando...')
        try:
            resultado = self.servicio.confirmar_y_guardar(self.reporte, id_usuario)
        except Exception as exc:
            logging.getLogger(__name__).exception('No se pudo guardar el ingreso')
            detalle = self._detalle_error(exc)
            self.reporte = None
            self.confirmacion = None
            self._set_confirm_status(
                f'Guardado fallido: {detalle}. '
                'Vuelve a cargar el archivo para revalidar.',
                error=True,
            )
            self.confirm_button.setEnabled(False)
            self.confirm_button.setText('Confirmar y guardar')
            return

        self.confirm_button.setEnabled(True)
        self.confirm_button.setText('Confirmar y guardar')
        self.resultado_guardado = resultado
        fecha = resultado.fecha_ingreso.strftime('%d/%m/%Y') if resultado.fecha_ingreso else '-'
        self.result_detail.setText(
            f'Proveedor: {resultado.proveedor}\n'
            f'Archivo: {resultado.archivo}\n'
            f'Ingreso registrado: N.º {resultado.id_ingreso}\n'
            f'Fecha ingreso: {fecha}'
        )
        self.result_status.setText('Guardado en PostgreSQL. Estado: Completado.')
        self.result_metric_values['productos'].setText(str(resultado.productos))
        self.result_metric_values['lineas'].setText(str(resultado.unidades))
        self.result_metric_values['incidencias'].setText(str(resultado.incidencias))
        self.result_metric_values['estado'].setText(resultado.estado)
        self.result_back.setEnabled(True)
        self._mostrar_paso(3)
        self.ingreso_guardado.emit(resultado.id_ingreso)

    def _ver_ingreso(self):
        resultado = self.resultado_guardado
        if resultado is None:
            return
        try:
            ingreso = self.servicio.obtener_ingreso(resultado.id_ingreso)
        except Exception as exc:
            QMessageBox.critical(self, 'No se pudo abrir el ingreso', str(exc))
            return
        if ingreso is None:
            QMessageBox.information(
                self, 'Ingreso registrado', 'No se encontró el detalle de este ingreso.'
            )
            return
        IngresoGuardadoDialog(ingreso, self).exec()

    def reset(self):
        self.archivo = None
        self.reporte = None
        self.data = None
        self.errors = []
        self.details.set_data(None)
        self._mostrar_paso(1)
        self.validate_button.setEnabled(False)
        self.validate_button.setText('Cargar archivo')
        self.process_button.setEnabled(False)
        self.process_button.setVisible(False)
        self.full_button.setEnabled(False)
        self.full_button.setVisible(False)
        self.preview.setVisible(False)
        self.preview_caption.clear()
        self.footer_message.setText('Selecciona un Excel de ingreso para comenzar.')
        self._reset_vista_previa()
        self._reset_resultado()

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Seleccionar Excel de ingreso',
            '',
            FILE_FILTER,
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        candidate = Path(path)
        if candidate.suffix.lower() != '.xlsx':
            QMessageBox.warning(
                self,
                'Formato no permitido',
                'Solo se aceptan archivos .xlsx.',
            )
            return

        try:
            stat = candidate.stat()
        except OSError as exc:
            QMessageBox.warning(self, 'No se pudo leer el archivo', str(exc))
            return

        if stat.st_size > MAX_FILE_BYTES:
            QMessageBox.warning(
                self,
                'Archivo demasiado grande',
                'El archivo supera el límite sugerido de 10 MB.',
            )
            return

        self.reporte = None
        self._reset_vista_previa()
        self._reset_resultado()
        self.archivo = ArchivoIngresoSeleccionado(
            path=candidate,
            name=candidate.name,
            extension=candidate.suffix.lower(),
            size_bytes=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
        )
        self.details.set_data(self.archivo)
        self.validate_button.setEnabled(True)
        self.preview.setVisible(False)
        self.preview_caption.clear()
        self.footer_message.setText(
            f'Archivo listo: {candidate.name}. Pulsa "Cargar archivo" para validarlo '
            'y ver la vista previa.'
        )

    def clear_file(self):
        self.reset()

    def validate_file(self):
        if self.archivo is None:
            return
        self.validate_button.setEnabled(False)
        id_usuario = getattr(self.sesion, 'id_usuario', None)
        try:
            self.reporte = self.servicio.validar(self.archivo.path, id_usuario)
        except Exception as exc:
            self.validate_button.setEnabled(True)
            QMessageBox.critical(self, 'No se pudo cargar el archivo', str(exc))
            return
        self._render_reporte()
        self.validate_button.setEnabled(True)

    def _render_reporte(self):
        reporte = self.reporte
        resumen = self.servicio.construir_resumen(reporte)
        self._productos_vista_previa = self.servicio.construir_productos_vista_previa(reporte)
        valores = self.preview_summary_values
        valores['proveedor'].setText(resumen.proveedor or '-')
        valores['archivo'].setText(resumen.archivo or '-')
        valores['registros'].setText(str(reporte.total_filas))
        valores['validos'].setText(str(reporte.correctas))
        valores['unidades'].setText(str(resumen.total_unidades))
        valores['fecha'].setText(resumen.fecha_rango)

        if reporte.es_valido:
            self.validation_status.setText('Listo')
            self.validation_status.setObjectName('goodChip')
            self.validation_lead.setText(
                f'Validación completada. {reporte.correctas} producto(s) listos.'
            )
        else:
            self.validation_status.setText('Pendiente')
            self.validation_status.setObjectName('warningChip')
            self.validation_lead.setText(
                'Revisa el estado de cada fila antes de continuar.'
            )
        self.validation_status.style().unpolish(self.validation_status)
        self.validation_status.style().polish(self.validation_status)

        if not reporte.es_valido:
            self._set_confirm_status(self._mensaje_errores(reporte), error=True)
        elif not reporte.filas_validas:
            self._set_confirm_status(
                'No hay productos válidos para guardar. Revisa el Excel y vuelve a cargarlo.',
                error=True,
            )
        elif reporte.total_advertencias:
            sufijo = 'advertencia' if reporte.total_advertencias == 1 else 'advertencias'
            self._set_confirm_status(
                f'Validación correcta con {reporte.total_advertencias} {sufijo}. '
                'El archivo está listo para registrarse.'
            )
        else:
            self._set_confirm_status(
                'Validación correcta. El archivo está listo para registrarse.'
            )

        self.confirm_filter.blockSignals(True)
        self.confirm_filter.clear()
        self.confirm_filter.addItem('Todas las categorías')
        self.confirm_filter.addItems(list(resumen.categorias))
        self.confirm_filter.setCurrentIndex(0)
        self.confirm_filter.blockSignals(False)
        self.confirm_search.blockSignals(True)
        self.confirm_search.clear()
        self.confirm_search.blockSignals(False)
        self._filtrar_confirmacion()

        self.confirmacion = None
        self.confirm_button.setEnabled(
            reporte.es_valido and bool(reporte.filas_validas)
        )
        self.confirm_button.setText('Confirmar y guardar')
        self._mostrar_paso(2)

    def process_file(self):
        return None


class IngresoGuardadoDialog(QDialog):
    def __init__(self, ingreso, parent=None):
        super().__init__(parent, objectName='ingresoGuardadoDialog')
        self.setWindowTitle(f'Ingreso registrado N.º {ingreso.id_ingreso}')
        self.setMinimumSize(980, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(
            QLabel(
                f'{ingreso.proveedor} · {ingreso.archivo} · '
                f'{ingreso.numero_productos} producto(s) · {ingreso.total_unidades} unidad(es)',
                objectName='validationLead',
            )
        )

        tabla = QTableWidget(len(ingreso.filas), len(DETALLE_INGRESO_COLUMNS))
        tabla.setHorizontalHeaderLabels(DETALLE_INGRESO_COLUMNS)
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.verticalHeader().setVisible(False)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        for fila_actual, fila in enumerate(ingreso.filas):
            fecha = (
                fila.fecha_ingreso.strftime('%d/%m/%Y')
                if fila.fecha_ingreso else '-'
            )
            valores = (
                fila.numero_fila,
                fila.codigo,
                fila.producto,
                fila.categoria,
                fila.cantidad,
                fila.stock_minimo,
                f'{fila.precio_compra:.2f}' if fila.precio_compra is not None else '-',
                f'{fila.precio_venta:.2f}' if fila.precio_venta is not None else '-',
                fila.unidad_medida,
                fecha,
            )
            for columna, valor in enumerate(valores):
                tabla.setItem(
                    fila_actual, columna, QTableWidgetItem(str(valor))
                )
        layout.addWidget(tabla)

        pie = QHBoxLayout()
        pie.addStretch()
        cerrar = QPushButton('Cerrar', objectName='primaryButton')
        cerrar.setMinimumHeight(38)
        cerrar.clicked.connect(self.accept)
        pie.addWidget(cerrar)
        layout.addLayout(pie)
