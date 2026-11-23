"""Pestana de comparacion de precios de proveedores."""

import csv
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from views.app_theme import zeyver_color, zeyver_stylesheet
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.comparaciones_controller import ComparacionesController
from controllers.proveedores_import_controller import ProveedoresImportController
from models.comparacion import ComparacionGuardada
from repositories.comparacion_repository import ComparacionRepository
from repositories.resultado_importacion_repository import ResultadoImportacionRepository
from services.comparacion_service import ComparacionService
from services.importacion_proveedores_pg import ContextoPostgres, PersistenciaPostgres
from services.importacion_proveedores_service import (
    ImportacionProveedoresService,
    combinar_reportes,
    construir_vista_previa,
    filtrar_filas_vista_previa,
    preparar_confirmacion,
)
from views.import_shared import (
    BLUE,
    GREEN,
    IMPORT_STYLES,
    ORANGE,
    PURPLE,
    ImportFileError,
    Stepper,
    format_size,
)
from views.comparison_history_view import ComparisonDetailDialog, ComparisonEditDialog
from views.import_results_view import (
    RESULT_STYLES,
    ImportResultPanel,
    SavedOffersDialog,
)


INK = zeyver_color('#09142f')
MUTED = zeyver_color('#60708f')
BORDER = zeyver_color('#dfe5ee')

SUPPLIER_EXTENSIONS = {'.xlsx'}
MAX_PROVEEDORES = 10


def _lista_nombres(nombres):
    if isinstance(nombres, (str, Path)):
        return [str(nombres)]
    return [str(nombre) for nombre in (nombres or [])]


def validar_seleccion_archivos(rutas):
    """Valida la Etapa 1: hasta 10 archivos .xlsx, uno por proveedor."""
    archivos = [Path(ruta) for ruta in (rutas or [])]
    if not archivos:
        raise ImportFileError('Selecciona al menos un archivo Excel.')
    if len(archivos) > MAX_PROVEEDORES:
        raise ImportFileError(f'Selecciona como máximo {MAX_PROVEEDORES} archivos.')
    vistos = set()
    resultado = []
    for ruta in archivos:
        if ruta.suffix.lower() not in SUPPLIER_EXTENSIONS:
            raise ImportFileError('Todos los archivos deben ser de tipo .xlsx.')
        clave = str(ruta.resolve())
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(ruta)
    if not resultado:
        raise ImportFileError('Selecciona al menos un archivo Excel.')
    return resultado


def texto_confirmacion_validacion(nombres):
    """Textos del dialogo de confirmacion de la Etapa 1."""
    lista = _lista_nombres(nombres)
    if len(lista) == 1:
        return (
            'Validar archivo',
            '¿Estás seguro de validar este archivo?',
            lista[0],
        )
    return (
        'Validar archivos',
        f'¿Estás seguro de validar estos {len(lista)} archivos?',
        '\n'.join(lista),
    )


def mensaje_confirmacion(nombres):
    """Estado que se muestra tras confirmar la seleccion."""
    lista = _lista_nombres(nombres)
    if len(lista) == 1:
        return f'Archivo confirmado: {lista[0]} · validación en Etapa 2'
    nombres_legibles = ', '.join(lista)
    return f'{len(lista)} archivos confirmados: {nombres_legibles} · validación en Etapa 2'


def _estilo_dialogo(dialogo, ancho, alto):
    dialogo.setModal(True)
    dialogo.setMinimumSize(ancho, alto)
    dialogo.setStyleSheet(zeyver_stylesheet(
        'QDialog{background:#ffffff;color:#09142f;'
        'font-family:"Segoe UI";font-size:12px;}'
        'QLabel{color:#09142f;font-size:12px;}'
        'QLabel#detalleArchivo{color:#4e31ed;font-size:12px;font-weight:700;}'
        'QPushButton{background:#ffffff;color:#5133f5;border:1px solid #c9bcff;'
        'border-radius:7px;padding:9px 16px;min-width:95px;font-weight:700;}'
        'QPushButton#aceptar{background:#5133f5;color:#ffffff;border:none;}'
    ))


def _icono_accion(tipo, color):
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    if tipo == 'mostrar':
        painter.drawEllipse(QRectF(2, 6, 16, 8))
        painter.drawEllipse(QRectF(7, 8, 4, 4))
    elif tipo == 'editar':
        trazo = QPainterPath()
        trazo.moveTo(4, 16)
        trazo.lineTo(4, 12)
        trazo.lineTo(13, 3)
        trazo.lineTo(17, 7)
        trazo.lineTo(8, 16)
        trazo.closeSubpath()
        painter.drawPath(trazo)
        painter.drawLine(4, 16, 8, 16)
    else:
        painter.drawLine(4, 6, 16, 6)
        painter.drawLine(8, 4, 12, 4)
        trazo = QPainterPath()
        trazo.moveTo(5, 6)
        trazo.lineTo(6, 17)
        trazo.lineTo(14, 17)
        trazo.lineTo(15, 6)
        painter.drawPath(trazo)
        painter.drawLine(8, 9, 8, 14)
        painter.drawLine(12, 9, 12, 14)
    painter.end()
    return QIcon(pixmap)


ICONOS_ACCION_HISTORIAL = {}


def _icono_accion_historial(tipo):
    if tipo not in ICONOS_ACCION_HISTORIAL:
        colores = {
            'mostrar': zeyver_color('#5133f5'),
            'editar': '#0b7a75',
            'borrar': '#c8384a',
        }
        ICONOS_ACCION_HISTORIAL[tipo] = _icono_accion(tipo, colores[tipo])
    return ICONOS_ACCION_HISTORIAL[tipo]


def mostrar_mensaje(titulo, texto, parent=None):
    """Muestra un aviso con el mismo estilo que el dialogo de confirmacion."""
    dialogo = QDialog(parent)
    dialogo.setWindowTitle(titulo)
    _estilo_dialogo(dialogo, 420, 150)
    layout = QVBoxLayout(dialogo)
    layout.setContentsMargins(22, 20, 22, 18)
    layout.setSpacing(14)
    etiqueta = QLabel(texto)
    etiqueta.setWordWrap(True)
    layout.addWidget(etiqueta)
    botones = QHBoxLayout()
    botones.addStretch()
    aceptar = QPushButton('Aceptar')
    aceptar.setObjectName('aceptar')
    aceptar.clicked.connect(dialogo.accept)
    botones.addWidget(aceptar)
    layout.addLayout(botones)
    dialogo.exec()


def confirmar_validacion(nombres, parent=None):
    """Muestra el dialogo de confirmacion y devuelve True si se acepta."""
    titulo, pregunta, archivos = texto_confirmacion_validacion(nombres)
    cantidad = len(_lista_nombres(nombres))
    dialogo = QDialog(parent)
    dialogo.setWindowTitle(titulo)
    _estilo_dialogo(dialogo, 460, 180 + min(cantidad - 1, 10) * 18)
    layout = QVBoxLayout(dialogo)
    layout.setContentsMargins(22, 20, 22, 18)
    layout.setSpacing(14)
    texto = QLabel(pregunta)
    texto.setWordWrap(True)
    layout.addWidget(texto)
    etiqueta = 'Archivo: ' if cantidad == 1 else f'Archivos ({cantidad}): '
    detalle = QLabel(f'{etiqueta}{archivos}')
    detalle.setObjectName('detalleArchivo')
    detalle.setWordWrap(True)
    layout.addWidget(detalle)
    botones = QHBoxLayout()
    botones.addStretch()
    cancelar = QPushButton('Cancelar')
    aceptar = QPushButton('Aceptar')
    aceptar.setObjectName('aceptar')
    cancelar.clicked.connect(dialogo.reject)
    aceptar.clicked.connect(dialogo.accept)
    botones.addWidget(cancelar)
    botones.addWidget(aceptar)
    layout.addLayout(botones)
    return dialogo.exec() == QDialog.Accepted


def confirmar_borrado(nombre, parent=None):
    """Muestra una confirmacion clara antes de borrar una comparacion."""
    dialogo = QDialog(parent)
    dialogo.setWindowTitle('Borrar comparación')
    _estilo_dialogo(dialogo, 430, 190)
    layout = QVBoxLayout(dialogo)
    layout.setContentsMargins(22, 20, 22, 18)
    layout.setSpacing(14)
    texto = QLabel(
        f'¿Borrar "{nombre}"? Se eliminarán la comparación, las cotizaciones, '
        'las ofertas y los errores del Excel asociado. Quedará como si nunca '
        'se hubiera subido.'
    )
    texto.setWordWrap(True)
    layout.addWidget(texto)
    botones = QHBoxLayout()
    botones.addStretch()
    cancelar = QPushButton('Cancelar')
    borrar = QPushButton('Sí, borrar')
    borrar.setObjectName('aceptar')
    cancelar.clicked.connect(dialogo.reject)
    borrar.clicked.connect(dialogo.accept)
    botones.addWidget(cancelar)
    botones.addWidget(borrar)
    layout.addLayout(botones)
    return dialogo.exec() == QDialog.Accepted


SUPPLIER_STYLES = zeyver_stylesheet('''
QLabel#supplierTitle { color: #09142f; font-size: 20px; font-weight: 800; }
QLabel#supplierSubtitle { color: #60708f; font-size: 11px; }
QPushButton#segment { background: #eef2f8; color: #4c5b76; border: 0; border-radius: 7px; padding: 9px 16px; font-size: 11px; font-weight: 700; }
QPushButton#segmentActive { background: #5133f5; color: white; border: 0; border-radius: 7px; padding: 9px 16px; font-size: 11px; font-weight: 700; }
QFrame#supplierCard { background: white; border: 1px solid #dfe5ee; border-radius: 9px; }
QLabel#cardTitle { color: #09142f; font-size: 13px; font-weight: 800; padding: 0px; margin: 0px; }
QLabel#cardHint { color: #60708f; font-size: 10px; }

QFrame#supplierDrop:hover { background: #fff0e5; border-color: #ff4f12; }
QLabel#dropTitle { color: #09142f; font-size: 15px; font-weight: 800; }
QTableWidget#supplierTable { background: white; color: #273754; border: none; border-radius: 0px; font-size: 10px; }
QTableWidget#supplierTable::item { border-bottom: 1px solid #e5eaf1; padding: 4px; }
QTableWidget#supplierTable QHeaderView::section { background: #f7f9fc; color: #12203a; border: none; border-bottom: 1px solid #dfe5ee; padding: 7px 5px; font-size: 10px; font-weight: 700; }
QLineEdit#supplierInput, QComboBox#supplierCombo, QDateEdit#supplierCombo { background: white; color: #263752; border: 1px solid #d4deea; border-radius: 6px; padding: 7px 9px; font-size: 10px; }
QComboBox#supplierCombo::drop-down { border: none; width: 22px; subcontrol-origin: padding; subcontrol-position: center right; }
QComboBox#supplierCombo QAbstractItemView { background: #ffffff; color: #263752; border: 1px solid #dfe5ee; border-radius: 6px; outline: 0; padding: 4px; selection-background-color: #ede9fe; selection-color: #5133f5; }
QComboBox#supplierCombo QAbstractItemView::item { padding: 6px 10px; min-height: 24px; border-radius: 4px; }
QComboBox#supplierCombo QAbstractItemView::item:hover { background: #f7f9fc; color: #273754; }
QComboBox#supplierCombo QAbstractItemView::item:selected { background: #ede9fe; color: #5133f5; }
QPushButton#supplierPrimary { background: #5133f5; color: white; border: 0; border-radius: 7px; padding: 10px 18px; font-size: 11px; font-weight: 700; }
QPushButton#supplierPrimary:disabled { background: #c7cfda; color: #f4f7fb; }
QPushButton#supplierSecondary { background: white; color: #5133f5; border: 1px solid #c9bcff; border-radius: 7px; padding: 9px 16px; font-size: 11px; font-weight: 700; }
QPushButton#supplierGhost { background: transparent; color: #5133f5; border: 0; font-size: 10px; font-weight: 700; }
QPushButton#historyMostrarButton, QPushButton#historyEditarButton, QPushButton#historyBorrarButton { background: #ffffff; border: 1px solid #dfe5ee; border-radius: 6px; padding: 2px; width: 27px; height: 25px; }
QPushButton#historyMostrarButton:hover, QPushButton#historyEditarButton:hover, QPushButton#historyBorrarButton:hover { background: #f4f1ff; border-color: #c9bcff; }
QLabel#warningChip { background: #fff5e5; color: #b66a00; border-radius: 6px; padding: 5px 8px; font-size: 10px; font-weight: 700; }
QLabel#goodChip { background: #e8f8f1; color: #087a51; border-radius: 6px; padding: 5px 8px; font-size: 10px; font-weight: 700; }
QLabel#fileCount { color: #60708f; font-size: 10px; font-weight: 700; }
QLabel#recoChip { color: #5133f5; font-size: 9px; font-weight: 800; letter-spacing: 1px; }
QLabel#recoProvider { color: #09142f; font-size: 20px; font-weight: 800; }
QLabel#recoTitle { color: #09142f; font-size: 15px; font-weight: 800; }
QLabel#miniValue { color: #09142f; font-size: 13px; font-weight: 800; }
QLabel#miniLabel { color: #60708f; font-size: 9px; font-weight: 700; }
QTableWidget#supplierTable QScrollBar:horizontal { background: #f7f9fc; height: 8px; border-top: 1px solid #e5eaf1; }
QTableWidget#supplierTable QScrollBar::handle:horizontal { background: #cbd4e1; border: 1px solid #b8c4d6; border-radius: 4px; min-width: 30px; }
QTableWidget#supplierTable QScrollBar::handle:horizontal:hover { background: #b8c4d6; }
QTableWidget#supplierTable QScrollBar::add-line:horizontal, QTableWidget#supplierTable QScrollBar::sub-line:horizontal { width: 0px; background: transparent; }
QTableWidget#supplierTable QScrollBar::add-page:horizontal, QTableWidget#supplierTable QScrollBar::sub-page:horizontal { background: #f7f9fc; }
QTableWidget#supplierTable QScrollBar:vertical { background: #f7f9fc; width: 8px; border-left: 1px solid #e5eaf1; }
QTableWidget#supplierTable QScrollBar::handle:vertical { background: #cbd4e1; border: 1px solid #b8c4d6; border-radius: 4px; min-height: 30px; }
QTableWidget#supplierTable QScrollBar::handle:vertical:hover { background: #b8c4d6; }
QTableWidget#supplierTable QScrollBar::add-line:vertical, QTableWidget#supplierTable QScrollBar::sub-line:vertical { height: 0px; background: transparent; }
QTableWidget#supplierTable QScrollBar::add-page:vertical, QTableWidget#supplierTable QScrollBar::sub-page:vertical { background: #f7f9fc; }
QTableWidget#supplierTable QTableCornerButton::section { background: #f7f9fc; border: 1px solid #e5eaf1; }
QTabWidget#resultTabs::pane { background: #ffffff; border: 1px solid #dfe5ee; border-radius: 8px; top: -1px; }
QTabWidget#resultTabs QTabBar::tab { background: #f7f9fc; color: #60708f; border: 1px solid #dfe5ee; border-bottom: none; padding: 7px 14px; margin-right: 3px; border-top-left-radius: 7px; border-top-right-radius: 7px; font-size: 11px; font-weight: 600; }
QTabWidget#resultTabs QTabBar::tab:selected { background: #ffffff; color: #5133f5; border-color: #dfe5ee; border-bottom: 1px solid #ffffff; margin-bottom: -1px; font-weight: 700; }
QTabWidget#resultTabs QTabBar::tab:hover:!selected { color: #5133f5; background: #fbfaff; }
QTabWidget#resultTabs QTabBar::tab:!selected { margin-top: 2px; }
''')


def _money(value):
    if value is None:
        return '-'
    return f'S/ {float(value):,.2f}'


def _qty(value):
    if value is None:
        return '-'
    value = float(value)
    if value.is_integer():
        return f'{value:,.0f}'
    return f'{value:,.2f}'


def _porcentaje(value):
    if value is None:
        return '-'
    return f'{_qty(float(value) * 100)}%'


def _item(text, align=Qt.AlignCenter, bold=False, foreground=None, background=None, tooltip=None):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignVCenter | align)
    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    if foreground is not None:
        item.setForeground(QColor(foreground))
    if background is not None:
        item.setBackground(QColor(background))
    if tooltip is not None:
        item.setToolTip(tooltip)
    return item


def _fixed_item(item):
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    return item


def _make_table(headers, height, stretch_columns=()):
    table = QTableWidget(0, len(headers), objectName='supplierTable')
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().hide()
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.NoSelection)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setFocusPolicy(Qt.NoFocus)
    table.setShowGrid(False)
    table.setFrameShape(QFrame.NoFrame)
    table.setMinimumHeight(height)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    header = table.horizontalHeader()
    header.setMinimumSectionSize(70)
    for index in range(len(headers)):
        mode = QHeaderView.Stretch if index in stretch_columns else QHeaderView.ResizeToContents
        header.setSectionResizeMode(index, mode)
    return table


DEMO_BASE = (
    ('Lejía', 'Limpieza', 5.80, 4.76, 6.32, 'LIM'),
    ('Lejía aromatizada', 'Limpieza', 6.40, 6.02, 5.76, 'LAR'),
    ('Desinfectante pino', 'Limpieza', 8.90, 9.79, 7.74, 'PIN'),
    ('Limpiador multiusos', 'Limpieza', 7.20, 6.85, 7.60, 'MUL'),
    ('Detergente líquido', 'Limpieza', 11.50, 10.90, 12.10, 'DET'),
    ('Suavizante', 'Limpieza', 9.40, 8.95, 9.80, 'SUA'),
    ('Alcohol etílico', 'Limpieza', 10.20, 9.60, 10.80, 'ALC'),
    ('Desengrasante', 'Limpieza', 12.80, 12.10, 13.40, 'DES'),
    ('Limpiavidrios', 'Limpieza', 6.70, 6.35, 7.05, 'VID'),
    ('Jabón líquido', 'Limpieza', 5.40, 5.10, 5.75, 'JAB'),
)
DEMO_SIZES = (('1 L', 1.0), ('2 L', 1.85), ('4 L', 3.4))
DEMO_PROVIDERS = (
    ('LimpiaSur', 'a', 'LimpiaSur.xlsx'),
    ('HigieneTotal', 'b', 'HigieneTotal.xlsx'),
    ('CleanMax', 'c', 'CleanMax.xlsx'),
)


def _demo_catalog():
    catalog = []
    index = 0
    for name, category, price_a, price_b, price_c, prefix in DEMO_BASE:
        for size, factor in DEMO_SIZES:
            index += 1
            catalog.append({
                'index': index,
                'name': f'{name} {size}',
                'category': category,
                'code': f'{prefix}-{index:03d}',
                'prices': {
                    'a': round(price_a * factor, 2),
                    'b': round(price_b * factor, 2),
                    'c': round(price_c * factor, 2),
                },
                'minimum': 12 + (index % 5) * 6,
                'stock': 80 + (index % 7) * 20 - (index % 3) * 10,
                'bonus': 0 if index % 4 else 6,
                'validity': date.today() + timedelta(days=20 + (index % 5) * 7),
            })
    return catalog


class SupplierDropZone(QFrame):
    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, objectName='supplierDrop')
        self.setObjectName('supplierDrop')
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(210)
        self.setStyleSheet(
            'QFrame#supplierDrop { background: #fff0e5; border: 3px dashed #ff8a24; border-radius: 10px; }'
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(4)
        layout.addStretch()
        icon = QLabel('☁↑', objectName='dropIcon')
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        title = QLabel('Arrastra los Excel de tus proveedores', objectName='dropTitle')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        hint = QLabel('Un archivo por proveedor · CSV, XLSX o XLS · máximo 50 MB', objectName='cardHint')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        choose = QPushButton('Seleccionar archivos', objectName='supplierSecondary')
        choose.setFixedWidth(190)
        choose.clicked.connect(self.clicked.emit)
        layout.addWidget(choose, alignment=Qt.AlignCenter)
        layout.addStretch()

    def dragEnterEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        try:
            validar_seleccion_archivos(paths)
        except ImportFileError:
            return
        event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SuppliersImportTab(QWidget):
    TITLE = 'Comparación de precios de proveedores'
    SUBTITLE = 'Carga una cotización por proveedor y decide con base en precios, stock y condiciones.'

    def __init__(self, parent=None, sesion=None):
        super().__init__(parent)
        self.setStyleSheet(IMPORT_STYLES + SUPPLIER_STYLES + RESULT_STYLES)
        self._sesion = sesion
        self.demo_catalog = _demo_catalog()
        self.files = []
        self.offers = []
        self.issues = []
        self.info_notes = []
        self.excluded = set()
        self.provider_names = []
        self.matrix_rows_data = []
        self.comparisons = []
        self._decision_actual = None
        self._ids_importacion_actuales = []
        self._comparacion_guardada_ids = None
        self._historial_sincronizado = False
        self._excluidas = {}
        self._pending_record = True
        self._reporte = None
        self._vista_previa = None
        self._confirmacion = None
        self._guardado_demo = False
        self._resultados_actuales = []
        self._resumen_actual = []
        self._detalle_resultado = None
        self._ultimo_id_importacion = None
        self._ultimo_mensaje_fallo = ''
        self._fallo_importacion_en_curso = False
        self.preview_disponibilidad = 'Todas'
        self.preview_rows = []
        servicio = ImportacionProveedoresService(
            contexto=ContextoPostgres(),
            persistencia=PersistenciaPostgres(),
            resultados=ResultadoImportacionRepository(),
        )
        self._controller = ProveedoresImportController(servicio=servicio, parent=self)
        self._comparaciones_controller = ComparacionesController(
            servicio=ComparacionService(ComparacionRepository()), parent=self
        )
        self._controller.preparada.connect(self._al_preparar)
        self._controller.validada.connect(self._al_validar)
        self._controller.guardada.connect(self._al_guardar)
        self._controller.fallo.connect(self._al_fallar)
        self._controller.fallo_detallado.connect(self._al_fallo_detallado)
        self._controller.resultado_consultado.connect(self._al_consultar_resultado)
        self._controller.detalle_consultado.connect(self._al_consultar_detalle)
        self._controller.resumen_consultado.connect(self._al_consultar_resumen)
        self._comparaciones_controller.guardada.connect(self._al_guardar_comparacion)
        self._comparaciones_controller.sincronizada.connect(
            self._al_sincronizar_comparaciones
        )
        self._comparaciones_controller.editada.connect(self._al_editar_comparacion)
        self._comparaciones_controller.eliminada.connect(self._al_eliminar_comparacion)
        self._comparaciones_controller.listado.connect(self._al_listar_comparaciones)
        self._comparaciones_controller.detalle_consultado.connect(
            self._al_detalle_comparacion
        )
        self._comparaciones_controller.fallo.connect(self._al_fallo_comparacion)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(10)
        root.addLayout(self._build_header())
        root.addWidget(self._build_segments())
        root.addWidget(self._build_pages(), 1)

        self._refresh_file_table()
        self._refresh_history()
        self._actualizar_estado_carga()
        self._go_step(1)
        self._set_segment(0)
        self._sincronizar_historial_inicial()
        self._recargar_historial()

    # -- construccion ------------------------------------------------------
    def _build_header(self):
        block = QVBoxLayout()
        block.setSpacing(2)
        block.addWidget(QLabel(self.TITLE, objectName='supplierTitle'))
        block.addWidget(QLabel(self.SUBTITLE, objectName='supplierSubtitle'))
        return block

    def _build_segments(self):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        self.segment_group = QButtonGroup(self)
        self.segment_group.setExclusive(True)
        self.new_button = QPushButton('Nueva comparación', objectName='segment')
        self.new_button.setCheckable(True)
        self.history_button = QPushButton(f'Historial · {len(self.comparisons)}', objectName='segment')
        self.history_button.setCheckable(True)
        self.segment_group.addButton(self.new_button)
        self.segment_group.addButton(self.history_button)
        self.new_button.clicked.connect(lambda: self._set_segment(0))
        self.history_button.clicked.connect(self._ir_historial)
        layout.addWidget(self.new_button)
        layout.addWidget(self.history_button)
        layout.addStretch()
        return frame

    def _build_pages(self):
        self.pages = QStackedWidget()
        self.workspace = QWidget()
        self.history_view = self._build_history()
        self.pages.addWidget(self.workspace)
        self.pages.addWidget(self.history_view)

        layout = QVBoxLayout(self.workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.stepper = Stepper((
            'Seleccionar archivo', 'Validar datos', 'Vista previa y confirmar',
            'Resultado de importación',
        ))
        layout.addWidget(self.stepper)
        self.steps = QStackedWidget()
        self.steps.addWidget(self._build_upload_step())
        self.steps.addWidget(self._build_validation_step())
        self.steps.addWidget(self._build_comparison_step())
        self.steps.addWidget(self._build_result_step())
        layout.addWidget(self.steps, 1)
        return self.pages

    def _build_upload_step(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.drop_zone = SupplierDropZone()
        self.drop_zone.clicked.connect(self._choose_files)
        self.drop_zone.files_dropped.connect(self._load_paths)
        top.addWidget(self.drop_zone, 3)
        top.addWidget(self._build_comparison_card(), 2)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        files_card = QFrame(objectName='supplierCard')
        files_layout = QVBoxLayout(files_card)
        files_layout.setContentsMargins(10, 8, 10, 8)
        files_layout.setSpacing(6)
        title_label = QLabel('Archivos de proveedores', objectName='cardTitle')
        title_label.setContentsMargins(0, 0, 0, 2)
        files_layout.addWidget(title_label)

        self.file_table = _make_table(
            ('Archivo', 'Tipo', 'Tamaño', 'Estado', ''), 140, (0,)
        )
        files_layout.addWidget(self.file_table)

        foot = QHBoxLayout()
        self.validate_button = QPushButton('Validar archivo', objectName='supplierPrimary')
        self.validate_button.clicked.connect(self._validate)
        foot.addStretch()
        foot.addWidget(self.validate_button)
        files_layout.addLayout(foot)
        bottom.addWidget(files_card, 3)

        self.upload_summary_card = self._build_upload_summary_card()
        bottom.addWidget(self.upload_summary_card, 2)

        layout.addLayout(bottom)
        return page

    def _build_upload_summary_card(self):
        card = QFrame(objectName='supplierCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel('Resumen de carga', objectName='cardTitle'))
        self.upload_summary_status = QLabel(
            'Aún no has cargado archivos.', objectName='cardHint'
        )
        self.upload_summary_status.setWordWrap(True)
        layout.addWidget(self.upload_summary_status)

        self.upload_summary_metrics = QLabel(
            f'Archivos: 0/{MAX_PROVEEDORES} · Proveedores: 0',
            objectName='metricLabel',
        )
        self.upload_summary_metrics.setWordWrap(True)
        layout.addWidget(self.upload_summary_metrics)

        layout.addWidget(QLabel('Archivos cargados', objectName='cardTitle'))
        self.upload_summary_files = QLabel('—', objectName='cardHint')
        self.upload_summary_files.setWordWrap(True)
        self.upload_summary_files.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.upload_summary_files.setMinimumHeight(70)
        layout.addWidget(self.upload_summary_files, 1)

        guide = QLabel(
            'Formato .xlsx · 1 archivo por proveedor · máx. 10 · hoja "Catalogo"',
            objectName='importNote',
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)
        return card

    def _refresh_upload_summary(self):
        if not hasattr(self, 'upload_summary_status'):
            return
        count = len(self.files)
        providers = len({
            str(entry.get('provider') or '').strip()
            for entry in self.files
            if str(entry.get('provider') or '').strip()
        })
        self.upload_summary_metrics.setText(
            f'Archivos: {count}/{MAX_PROVEEDORES} · Proveedores: {providers}'
        )
        if count == 0:
            self.upload_summary_status.setText('Aún no has cargado archivos.')
            self.upload_summary_files.setText('—')
            return
        self.upload_summary_status.setText(
            f'{count} archivo(s) listos para validar.'
        )
        lineas = []
        for entry in self.files:
            nombre = entry.get('name', '')
            proveedor = str(entry.get('provider') or Path(nombre).stem).strip()
            tamano = entry.get('size', '')
            lineas.append(f'• {nombre} — {proveedor} · {tamano} · Listo')
        self.upload_summary_files.setText('\n'.join(lineas))

    def _build_comparison_card(self):
        card = QFrame(objectName='supplierCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        layout.addWidget(QLabel('Datos de la comparación', objectName='cardTitle'))
        layout.addWidget(QLabel(
            'Define el nombre que aparecerá en el historial.', objectName='cardHint'
        ))

        self.name_edit = QLineEdit('Productos de limpieza', objectName='supplierInput')
        self.category_combo = QComboBox(objectName='supplierCombo')
        self.category_combo.setEditable(True)
        self.category_combo.setView(QListView())
        self.category_combo.addItems((
            'Limpieza', 'Dulces', 'Bebidas', 'Snacks', 'Ropa', 'Juguetes',
            'Alimentos', 'Cuidado personal', 'Hogar', 'Ferretería', 'Papelería',
            'Deportes', 'Electrónica', 'Mascotas', 'Farmacia', 'Bebés',
            'Calzado', 'Accesorios', 'Jardinería', 'Automotriz', 'Otros',
        ))
        self.category_combo.setCurrentText('Limpieza')
        self.category_combo.setMaxVisibleItems(10)
        for label, widget in (
            ('Nombre de la comparación', self.name_edit),
            ('Categoría principal', self.category_combo),
        ):
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(3)
            box_layout.addWidget(QLabel(label, objectName='cardHint'))
            box_layout.addWidget(widget)
            layout.addWidget(box)

        layout.addWidget(QLabel(
            f'Fecha de creación · {date.today().strftime("%d/%m/%Y")}', objectName='cardHint'
        ))
        layout.addStretch()
        return card

    def _build_validation_step(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        summary = QFrame(objectName='supplierCard')
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.setSpacing(8)
        summary_layout.addWidget(QLabel('Revisión de archivos', objectName='cardTitle'))
        self.validation_status = QLabel('Sin revisar', objectName='warningChip')
        summary_layout.addWidget(self.validation_status)
        summary_layout.addStretch()
        summary_layout.addWidget(QLabel(
            'Revisa errores y advertencias antes de continuar.', objectName='cardHint'
        ))
        layout.addWidget(summary)

        card = QFrame(objectName='supplierCard')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(13, 11, 13, 11)
        card_layout.setSpacing(8)
        card_layout.addWidget(QLabel('Resultado de la validación', objectName='cardTitle'))
        self.issue_table = _make_table(
            ('Proveedor', 'Fila', 'Campo', 'Aviso detectado', 'Acción'), 258, (3,)
        )
        card_layout.addWidget(self.issue_table)

        foot = QHBoxLayout()
        self.correct_button = QPushButton('Corregir y volver a validar', objectName='supplierSecondary')
        self.correct_button.clicked.connect(self._corregir_archivo)
        self.preview_button = QPushButton('Continuar a vista previa', objectName='supplierPrimary')
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self._ir_a_vista_previa)
        foot.addStretch()
        foot.addWidget(self.correct_button)
        foot.addWidget(self.preview_button)
        card_layout.addLayout(foot)
        layout.addWidget(card)
        return page

    def _build_comparison_step(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.result_tabs = QTabWidget(objectName='resultTabs')
        self.result_tabs.addTab(self._build_preview_card(), 'Detalle de importación')
        comparison = QWidget()
        body = QHBoxLayout(comparison)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        body.addWidget(self._build_matrix_card(), 3)
        body.addWidget(self._build_decision_card(), 1)
        self.result_tabs.addTab(comparison, 'Comparativa de precios')
        self.result_tabs.currentChanged.connect(self._al_cambiar_tab_resultado)
        layout.addWidget(self.result_tabs, 1)
        return page

    def _build_result_step(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.result_panel = ImportResultPanel()
        self.result_panel.importar_otro.connect(self._reset_workspace)
        self.result_panel.ver_datos.connect(self._ver_datos_guardados)
        layout.addWidget(self.result_panel, 1)
        return page

    def _metric_icon_pixmap(self, kind, color, size=26):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        scale = size / 38.0
        c = QColor(color)
        pen = QPen(c, 2.2 * scale)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        if kind == 'import':
            tray = QPainterPath()
            tray.addRoundedRect(QRectF(8 * scale, 23 * scale, 22 * scale, 9 * scale), 2.5 * scale, 2.5 * scale)
            painter.drawPath(tray)
            painter.drawLine(QRectF(19 * scale, 8 * scale, 0, 0).topLeft(), QRectF(19 * scale, 21 * scale, 0, 0).topLeft())
            head = QPainterPath()
            head.moveTo(13 * scale, 16 * scale)
            head.lineTo(19 * scale, 22 * scale)
            head.lineTo(25 * scale, 16 * scale)
            painter.drawPath(head)
        elif kind == 'nostock':
            painter.drawRoundedRect(QRectF(9 * scale, 12 * scale, 20 * scale, 17 * scale), 3 * scale, 3 * scale)
            painter.drawLine(QRectF(12 * scale, 12 * scale, 0, 0).topLeft(), QRectF(15 * scale, 8 * scale, 0, 0).topLeft())
            painter.drawLine(QRectF(26 * scale, 12 * scale, 0, 0).topLeft(), QRectF(23 * scale, 8 * scale, 0, 0).topLeft())
            painter.drawLine(QRectF(15 * scale, 8 * scale, 0, 0).topLeft(), QRectF(23 * scale, 8 * scale, 0, 0).topLeft())
            painter.drawLine(QRectF(14 * scale, 20 * scale, 0, 0).topLeft(), QRectF(24 * scale, 20 * scale, 0, 0).topLeft())
        else:
            painter.drawEllipse(QRectF(7 * scale, 7 * scale, 24 * scale, 24 * scale))
            painter.drawLine(QRectF(19 * scale, 13 * scale, 0, 0).topLeft(), QRectF(19 * scale, 21 * scale, 0, 0).topLeft())
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QRectF(17.7 * scale, 24.2 * scale, 2.6 * scale, 2.6 * scale))
        painter.end()
        return pixmap

    def _metric(self, kind, value, label, color, background):
        card = QFrame(objectName='importMetric')
        card.setFixedHeight(90)
        row = QHBoxLayout(card)
        row.setContentsMargins(13, 11, 13, 11)
        row.setSpacing(11)
        badge = QLabel(objectName='importMetricIcon')
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(44, 44)
        badge.setStyleSheet(f'background: {background}; color: {color}; border-radius: 22px;')
        badge.setPixmap(self._metric_icon_pixmap(kind, color, size=26))
        row.addWidget(badge)
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.addStretch()
        value_label = QLabel(value, objectName='importMetricValue')
        value_label.setStyleSheet(f'color: {color};')
        text_col.addWidget(value_label)
        text_col.addWidget(QLabel(label, objectName='importMetricLabel'))
        text_col.addStretch()
        row.addLayout(text_col, 1)
        return card

    def _build_preview_card(self):
        card = QFrame(objectName='supplierCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(QLabel('Vista previa de importación', objectName='cardTitle'))
        head.addStretch()
        layout.addLayout(head)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        specs = (
            ('import', 'Productos a importar', BLUE, '#eaf3ff', 'preview_count_value'),
            ('nostock', 'Sin stock', ORANGE, '#fff5e5', 'preview_stock_value'),
            ('error', 'Errores detectados', PURPLE, '#f0edff', 'preview_error_value'),
        )
        for kind, label, color, background, attribute in specs:
            metric = self._metric(kind, '0', label, color, background)
            setattr(self, attribute, metric.findChild(QLabel, 'importMetricValue'))
            metrics.addWidget(metric, 1)
        layout.addLayout(metrics)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.preview_search = QLineEdit(objectName='supplierInput')
        self.preview_search.setPlaceholderText('Buscar por nombre o código...')
        self.preview_search.setFixedWidth(210)
        self.preview_filter = QComboBox(objectName='supplierCombo')
        self.preview_filter.addItem('Todas las categorías')
        self.preview_filter.setFixedWidth(160)
        self.preview_filter.setView(QListView())
        self.preview_filter.setMaxVisibleItems(12)
        self.preview_search.textChanged.connect(self._refresh_preview)
        self.preview_filter.currentTextChanged.connect(self._refresh_preview)
        tools.addWidget(self.preview_search)
        tools.addWidget(self.preview_filter)
        tools.addStretch()

        self.preview_availability_group = QButtonGroup(self)
        self.preview_availability_group.setExclusive(True)
        self.preview_availability_buttons = []
        opciones = (
            ('Todos', 'Todas'),
            ('Con stock', 'Con stock'),
            ('Sin stock', 'Sin stock'),
        )
        for index, (texto, valor) in enumerate(opciones):
            button = QPushButton(texto, objectName='segment')
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setObjectName('segmentActive' if index == 0 else 'segment')
            button.clicked.connect(
                lambda checked=False, indice=index: self._set_preview_availability(indice)
            )
            self.preview_availability_group.addButton(button, index)
            self.preview_availability_buttons.append(button)
            tools.addWidget(button)
        layout.addLayout(tools)

        layout.addWidget(QLabel(
            'Solo lectura · Si un dato es incorrecto, corrígelo en el Excel y valida nuevamente.',
            objectName='cardHint',
        ))

        self.preview_table = _make_table(
            (
                'Archivo', 'Proveedor', 'Fila', 'Código', 'Producto', 'Categoría',
                'Marca', 'Presentación', 'Precio', 'Stock', 'Mínimo', 'Desc. desde',
                'Desc. %', 'Entrega', 'Estado',
            ),
            340,
            (4,),
        )
        layout.addWidget(self.preview_table)

        foot = QHBoxLayout()
        self.preview_caption = QLabel('Mostrando 0 de 0 registros', objectName='cardHint')
        foot.addWidget(self.preview_caption)
        foot.addStretch()
        back = QPushButton('Volver', objectName='supplierGhost')
        back.clicked.connect(lambda: self._go_step(2))
        self.confirm_button = QPushButton('Confirmar', objectName='supplierPrimary')
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self._confirmar_importacion)
        foot.addWidget(back)
        foot.addWidget(self.confirm_button)
        layout.addLayout(foot)
        return card

    def _build_matrix_card(self):
        card = QFrame(objectName='supplierCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(QLabel('Comparativa de precios', objectName='cardTitle'))
        head.addStretch()
        head.addWidget(QLabel('Mejor precio', objectName='goodChip'))
        export = QPushButton('↧  Exportar', objectName='supplierSecondary')
        export.clicked.connect(self._export_results)
        head.addWidget(export)
        layout.addLayout(head)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.matrix_search = QLineEdit(objectName='supplierInput')
        self.matrix_search.setPlaceholderText('Buscar producto...')
        self.matrix_search.setFixedWidth(190)
        self.matrix_filter = QComboBox(objectName='supplierCombo')
        self.matrix_filter.addItem('Todas las categorías')
        self.matrix_filter.setFixedWidth(160)
        self.matrix_filter.setView(QListView())
        self.matrix_filter.setMaxVisibleItems(12)
        self.matrix_search.textChanged.connect(self._refresh_matrix)
        self.matrix_filter.currentTextChanged.connect(self._refresh_matrix)
        tools.addWidget(self.matrix_search)
        tools.addWidget(self.matrix_filter)
        tools.addStretch()
        layout.addLayout(tools)

        layout.addWidget(QLabel(
            'Verde = mejor precio por producto · La etiqueta muestra el proveedor recomendado en cada fila',
            objectName='cardHint',
        ))

        self.matrix_table = _make_table(('#', 'Producto', 'Categoría'), 360, ())
        self.matrix_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.matrix_table)

        foot = QHBoxLayout()
        self.matrix_caption = QLabel('Mostrando 0 de 0 productos', objectName='cardHint')
        foot.addWidget(self.matrix_caption)
        foot.addStretch()
        back = QPushButton('Volver a validar', objectName='supplierGhost')
        back.clicked.connect(lambda: self._go_step(2))
        foot.addWidget(back)
        layout.addLayout(foot)
        return card

    def _build_decision_card(self):
        card = QFrame(objectName='supplierCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel('Mejor opción', objectName='recoTitle'))
        title_row.addStretch()
        title_row.addWidget(QLabel('Recomendado', objectName='goodChip'))
        layout.addLayout(title_row)

        self.reco_provider = QLabel('HigieneTotal', objectName='recoProvider')
        layout.addWidget(self.reco_provider)

        indicators = QHBoxLayout()
        indicators.setSpacing(6)
        self.ind_wins_value = QLabel('0 de 0', objectName='miniValue')
        self.ind_average_value = QLabel(_money(0), objectName='miniValue')
        self.ind_advantage_value = QLabel(_money(0), objectName='miniValue')
        for value, label in (
            (self.ind_wins_value, 'Productos con mejor precio'),
            (self.ind_average_value, 'Precio promedio'),
            (self.ind_advantage_value, 'Ventaja acumulada'),
        ):
            box = QVBoxLayout()
            box.setSpacing(1)
            box.addWidget(value)
            box.addWidget(QLabel(label, objectName='miniLabel'))
            indicators.addLayout(box, 1)
        layout.addLayout(indicators)

        layout.addWidget(QLabel('¿Por qué se recomienda?', objectName='cardTitle'))
        self.reasons = QLabel('', objectName='cardHint')
        self.reasons.setWordWrap(True)
        layout.addWidget(self.reasons)
        layout.addStretch()
        return card

    def _build_history(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        card = QFrame(objectName='supplierCard')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(13, 11, 13, 11)
        card_layout.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(QLabel('Historial de comparaciones', objectName='cardTitle'))
        head.addStretch()
        self.historial_count = QLabel(f'{len(self.comparisons)} guardadas', objectName='cardHint')
        head.addWidget(self.historial_count)
        card_layout.addLayout(head)

        filtros = QHBoxLayout()
        filtros.setSpacing(8)
        self.historial_busqueda = QLineEdit(objectName='supplierInput')
        self.historial_busqueda.setPlaceholderText(
            'Buscar por nombre, categoría, fecha o proveedor'
        )
        self.historial_busqueda.textChanged.connect(self._recargar_historial)
        self.historial_categoria = QComboBox(objectName='supplierCombo')
        self.historial_categoria.setView(QListView())
        self.historial_categoria.addItem('Todas las categorías')
        self.historial_categoria.currentTextChanged.connect(self._recargar_historial)
        self.historial_proveedor = QComboBox(objectName='supplierCombo')
        self.historial_proveedor.setView(QListView())
        self.historial_proveedor.addItem('Todos los proveedores')
        self.historial_proveedor.currentTextChanged.connect(self._recargar_historial)
        self.historial_fecha = QDateEdit(objectName='supplierCombo')
        self.historial_fecha.setCalendarPopup(True)
        self.historial_fecha.setDisplayFormat('dd/MM/yyyy')
        self.historial_fecha.setMinimumDate(QDate(2000, 1, 1))
        self.historial_fecha.setSpecialValueText('Todas las fechas')
        self.historial_fecha.setDate(self.historial_fecha.minimumDate())
        self.historial_fecha.dateChanged.connect(self._recargar_historial)
        filtros.addWidget(self.historial_busqueda, 2)
        filtros.addWidget(self.historial_categoria, 1)
        filtros.addWidget(self.historial_proveedor, 1)
        filtros.addWidget(self.historial_fecha, 1)
        card_layout.addLayout(filtros)

        self.history_table = _make_table(
            (
                'Comparación', 'Categoría principal', 'Proveedor con mejor precio', 'Fecha',
                'Hora', 'Productos', 'Ahorro', 'Acciones',
            ),
            320,
            (0, 2),
        )
        card_layout.addWidget(self.history_table)
        self.historial_estado_texto = QLabel('', objectName='cardHint')
        layout.addWidget(card)
        return page

    # -- navegacion --------------------------------------------------------
    def _set_segment(self, index):
        button = self.new_button if index == 0 else self.history_button
        button.setChecked(True)
        self._polish_segment()
        self.pages.setCurrentIndex(index)

    def _ir_historial(self):
        self._set_segment(1)
        self._sincronizar_historial_inicial()
        self._recargar_historial()

    def _sincronizar_historial_inicial(self):
        if self._historial_sincronizado:
            return
        self._historial_sincronizado = True
        self._comparaciones_controller.sincronizar_historial(self._id_usuario())

    def _polish_segment(self):
        for button, active in (
            (self.new_button, self.new_button.isChecked()),
            (self.history_button, self.history_button.isChecked()),
        ):
            button.setObjectName('segmentActive' if active else 'segment')
            button.style().unpolish(button)
            button.style().polish(button)

    def _go_step(self, step):
        self.stepper.set_step(step)
        self.steps.setCurrentIndex(step - 1)

    # -- carga de archivos -------------------------------------------------
    def _choose_files(self):
        rutas, _ = QFileDialog.getOpenFileNames(
            self,
            'Seleccionar Excel de proveedores',
            '',
            'Archivos Excel (*.xlsx)',
        )
        if rutas:
            self._load_paths(rutas)

    def _load_paths(self, paths):
        try:
            rutas = validar_seleccion_archivos(paths)
        except ImportFileError as error:
            mostrar_mensaje('Archivo no válido', str(error), self.window() or self)
            return
        existentes = {
            str(Path(entry['ruta']).resolve()) for entry in self.files
        }
        agregados = 0
        for ruta in rutas:
            clave = str(ruta.resolve())
            if clave in existentes:
                continue
            existentes.add(clave)
            try:
                stat = ruta.stat()
                size_bytes = stat.st_size
                size = format_size(size_bytes)
            except OSError:
                size_bytes = 0
                size = '48.2 KB'
            self.files.append({
                'ruta': ruta,
                'name': ruta.name,
                'provider': ruta.stem,
                'total': 0,
                'size': size,
                'size_bytes': size_bytes,
                'headers': [],
                'indexes': {},
                'offers': [],
                'is_demo': False,
                'preparada': None,
                'id_importacion': None,
            })
            agregados += 1
        if not agregados:
            return
        self._invalidar_confirmacion()
        self.issues = []
        self.excluded = set()
        self._excluidas = {}
        self.offers = []
        self.matrix_rows_data = []
        self._reporte = None
        self.preview_button.setEnabled(False)
        self._refresh_issues()
        self._refresh_file_table()
        self._actualizar_estado_carga()

    def _load_demo_files(self):
        ruta = Path('Proveedor_01_LimpiaSur_ZEYVER.xlsx')
        self.files = []
        self._load_paths([ruta])
        if not self.files:
            return
        self.files[0].update({
            'total': len(self.demo_catalog),
            'size': '48.2 KB',
            'size_bytes': 49357,
            'provider': 'LimpiaSur',
            'is_demo': True,
        })
        self._refresh_file_table()
        self._actualizar_estado_carga()

    def _grupos_demo(self):
        proveedor, clave, archivo = DEMO_PROVIDERS[0]
        return [{
            'proveedor': proveedor,
            'archivo': archivo,
            'productos': [
                {
                    'name': fila['name'],
                    'category': fila['category'],
                    'price': fila['prices'][clave],
                    'minimum': fila['minimum'],
                    'stock': fila['stock'],
                    'code': fila['code'],
                    'bonus': fila['bonus'],
                    'validity': fila['validity'],
                }
                for fila in self.demo_catalog
            ],
        }]

    def _cargar_avisos(self, preparadas):
        self.issues = []
        for preparada in preparadas:
            proveedor_mostrar = str(getattr(preparada, 'proveedor', '') or '').strip()
            if not proveedor_mostrar:
                proveedor_mostrar = preparada.archivo.nombre
            for aviso in preparada.avisos:
                etiqueta = 'Error' if aviso.grave else 'Advertencia'
                self.issues.append({
                    'archivo': preparada.archivo.nombre,
                    'proveedor': proveedor_mostrar,
                    'numero_fila': str(aviso.numero_fila),
                    'campo': aviso.campo,
                    'problema': f'[{etiqueta}] {aviso.problema}',
                    'grave': aviso.grave,
                    'excluido': False,
                    'id_importacion': preparada.id_importacion,
                })
        self.excluded = set()
        self._excluidas = {}
        self._refresh_issues()

    def _al_preparar(self, preparadas):
        self._invalidar_confirmacion()
        entradas = []
        for preparada in preparadas:
            size_bytes = preparada.archivo.tamano_bytes or (
                49357 if preparada.archivo.es_demo else 0
            )
            size = (
                '48.2 KB' if preparada.archivo.es_demo
                else format_size(size_bytes)
            )
            entradas.append({
                'ruta': preparada.archivo.ruta,
                'name': preparada.archivo.nombre,
                'provider': preparada.proveedor,
                'total': len(preparada.filas),
                'size': size,
                'size_bytes': size_bytes,
                'headers': preparada.columnas,
                'indexes': preparada.indices,
                'offers': preparada.ofertas,
                'is_demo': preparada.archivo.es_demo,
                'preparada': preparada,
                'id_importacion': None,
            })
        self.files = entradas
        self._guardado_demo = bool(entradas) and all(
            entry['is_demo'] for entry in entradas
        )
        self.offers = []
        self.matrix_rows_data = []
        self._reporte = combinar_reportes(preparadas)
        self._cargar_avisos(preparadas)
        self._refresh_file_table()
        self._actualizar_estado_carga()
        self.preview_button.setEnabled(self._reporte.es_valido)
        self._go_step(2)

    def _al_validar(self, preparadas):
        self._invalidar_confirmacion()
        self._reporte = combinar_reportes(preparadas)
        self._cargar_avisos(preparadas)
        self.preview_button.setEnabled(self._reporte.es_valido)
        self._go_step(2)

    def _corregir_archivo(self):
        self._invalidar_confirmacion()
        self.files = []
        self.offers = []
        self.issues = []
        self.excluded = set()
        self._excluidas = {}
        self.matrix_rows_data = []
        self._reporte = None
        self.preview_button.setEnabled(False)
        self._refresh_issues()
        self._refresh_file_table()
        self._actualizar_estado_carga()
        self._go_step(1)

    def _ir_a_vista_previa(self):
        if not self._reporte or not self._reporte.es_valido:
            mostrar_mensaje(
                'Validación',
                'Corrige los errores antes de continuar a la vista previa.',
                self.window() or self,
            )
            return
        preparadas = [
            entry['preparada'] for entry in self.files
            if entry.get('preparada') is not None
        ]
        if not preparadas:
            mostrar_mensaje(
                'Vista previa', 'No hay filas válidas para revisar.', self.window() or self
            )
            return
        excluidas = self._excluidas_para_preview()
        self._vista_previa = construir_vista_previa(preparadas, excluidas)
        resumen = self._vista_previa.resumen
        self.preview_count_value.setText(str(resumen.productos))
        self.preview_stock_value.setText(str(resumen.sin_stock))
        self.preview_error_value.setText(str(resumen.errores))
        self.preview_filter.blockSignals(True)
        self.preview_filter.clear()
        self.preview_filter.addItem('Todas las categorías')
        self.preview_filter.addItems(self._vista_previa.categorias)
        self.preview_filter.blockSignals(False)
        self.confirm_button.setEnabled(self._vista_previa.es_confirmable)
        self._refresh_preview()
        self.result_tabs.setCurrentIndex(0)
        self._go_step(3)

    def _al_cambiar_tab_resultado(self, index):
        if index == 1:
            self._asegurar_comparacion()

    def _asegurar_comparacion(self):
        if self.matrix_rows_data:
            return
        self._aplicar_comparacion(True, preservar_vista=True)

    def _preparar_datos_comparacion(self, record=True):
        if not any(entry.get('preparada') is not None for entry in self.files):
            return None
        self._excluidas = self._excluidas_para_preview()
        self._reconstruir_ofertas()
        if not self.offers:
            return None
        self.provider_names = []
        for entry in self.files:
            name = (entry.get('provider') or '').strip() or 'Proveedor'
            if name not in self.provider_names:
                self.provider_names.append(name)
        categories = sorted({
            offer.get('category') for offer in self.offers if offer.get('category')
        })
        self.matrix_search.blockSignals(True)
        self.matrix_search.clear()
        self.matrix_search.blockSignals(False)
        self.matrix_filter.blockSignals(True)
        self.matrix_filter.clear()
        self.matrix_filter.addItem('Todas las categorías')
        self.matrix_filter.addItems(categories)
        self.matrix_filter.blockSignals(False)
        self.name_edit.setText(self.name_edit.text().strip() or 'Productos de limpieza')
        self._refresh_matrix()
        decision = self._refresh_decision()
        self._decision_actual = decision
        if record and decision:
            self._guardar_comparacion_actual(decision)
        return decision

    def _excluidas_para_preview(self):
        excluidas = {}
        for issue in self.issues:
            if issue['excluido']:
                excluidas.setdefault(issue['archivo'], set()).add(
                    int(issue['numero_fila'])
                )
        return excluidas

    def _set_preview_availability(self, index):
        valores = ('Todas', 'Con stock', 'Sin stock')
        if not 0 <= index < len(valores):
            return
        self.preview_disponibilidad = valores[index]
        for position, button in enumerate(self.preview_availability_buttons):
            button.setObjectName('segmentActive' if position == index else 'segment')
            button.style().unpolish(button)
            button.style().polish(button)
        self._refresh_preview()

    def _refresh_preview(self):
        if self._vista_previa is None:
            return
        filas = filtrar_filas_vista_previa(
            self._vista_previa.filas,
            self.preview_search.text(),
            self.preview_filter.currentText(),
            self.preview_disponibilidad,
        )
        self.preview_rows = filas
        tabla = self.preview_table
        tabla.blockSignals(True)
        tabla.setRowCount(len(filas))
        for row, fila in enumerate(filas):
            descuento = (
                '-' if fila.descuento_desde is None else _qty(fila.descuento_desde)
            )
            porcentaje = _qty(float(fila.descuento_porcentaje) * 100)
            estado = 'Excluida' if fila.excluida else fila.estado_producto
            valores = (
                fila.archivo, fila.proveedor, fila.numero_fila, fila.codigo,
                fila.producto, fila.categoria, fila.marca, fila.presentacion,
                _money(fila.precio), _qty(fila.stock), _qty(fila.compra_minima),
                descuento, f'{porcentaje}%', fila.entrega_dias, estado,
            )
            izquierda = {3, 4, 5, 6, 7, 14}
            for column, valor in enumerate(valores):
                item = _fixed_item(_item(
                    valor,
                    Qt.AlignLeft if column in izquierda else Qt.AlignCenter,
                    foreground=MUTED if fila.excluida else None,
                ))
                tabla.setItem(row, column, item)
        tabla.blockSignals(False)
        self.preview_caption.setText(
            f'Mostrando {len(filas)} de {len(self._vista_previa.filas)} registros'
        )

    def _confirmar_importacion(self):
        if self._vista_previa is None or not self._vista_previa.es_confirmable:
            return
        excluidas = self._excluidas_para_preview()
        self._confirmacion = preparar_confirmacion(self._vista_previa, excluidas)
        if self._guardado_demo:
            self.confirm_button.setEnabled(False)
            self.confirm_button.setText('Datos confirmados · Demo')
            mostrar_mensaje(
                'Importación de demostración',
                f'{len(self._confirmacion.filas)} producto(s) confirmados. '
                'Los datos demo no se guardan en PostgreSQL.',
                self.window() or self,
            )
            return
        preparadas = [
            entry['preparada']
            for entry in self.files
            if entry.get('preparada') is not None
        ]
        if not preparadas:
            return
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText('Guardando…')
        self._ultimo_mensaje_fallo = ''
        self._fallo_importacion_en_curso = True
        self._controller.guardar(
            preparadas,
            excluidas,
            getattr(self._sesion, 'id_usuario', None),
        )

    def _invalidar_confirmacion(self):
        self._vista_previa = None
        self._confirmacion = None
        self._guardado_demo = False
        self._resultados_actuales = []
        self._resumen_actual = []
        self._detalle_resultado = None
        self._ultimo_id_importacion = None
        self._ids_importacion_actuales = []
        self._comparacion_guardada_ids = None
        self._decision_actual = None
        if hasattr(self, 'result_panel'):
            self.result_panel.limpiar()
        self.offers = []
        self.matrix_rows_data = []
        self.provider_names = []
        if hasattr(self, 'confirm_button'):
            self.confirm_button.setEnabled(False)
            self.confirm_button.setText('Confirmar')
        if hasattr(self, 'preview_table'):
            self.preview_table.setRowCount(0)
            self.preview_caption.setText('Mostrando 0 de 0 registros')
        if hasattr(self, 'matrix_table'):
            self.matrix_table.setRowCount(0)
            self.matrix_caption.setText('Mostrando 0 de 0 productos')
        if hasattr(self, 'reco_provider'):
            self.reco_provider.setText('-')
            self.ind_wins_value.setText('0 de 0')
            self.ind_average_value.setText(_money(0))
            self.ind_advantage_value.setText(_money(0))
            self.reasons.setText('')

    def _al_guardar(self, resultados):
        resultados = list(resultados or [])
        self._fallo_importacion_en_curso = False
        por_proveedor = {resultado.proveedor: resultado for resultado in resultados}
        for entry in self.files:
            resultado = por_proveedor.get(entry.get('provider'))
            if resultado is not None:
                entry['id_importacion'] = resultado.id_importacion
        ids = [
            resultado.id_importacion
            for resultado in resultados
            if resultado.id_importacion is not None
        ]
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText('Importación completada')
        self._ids_importacion_actuales = ids
        self._comparacion_guardada_ids = None
        if ids:
            self._preparar_datos_comparacion(record=True)
            self._controller.consultar_resultado(ids)
        else:
            self.result_panel.mostrar_error_local(
                'No se pudo identificar la importación guardada.'
            )
            self._go_step(4)
        self._controller.consultar_resumen()

    def _al_fallar(self, mensaje):
        self._ultimo_mensaje_fallo = mensaje
        if hasattr(self, 'confirm_button'):
            self.confirm_button.setEnabled(True)
            self.confirm_button.setText('Confirmar')
        if self._fallo_importacion_en_curso:
            return
        mostrar_mensaje('Importación de proveedores', mensaje, self.window() or self)

    def _al_fallo_detallado(self, intentos):
        self._fallo_importacion_en_curso = False
        intentos = list(intentos or [])
        ids = [
            intento.id_importacion
            for intento in intentos
            if getattr(intento, 'id_importacion', None) is not None
        ]
        if ids:
            self._controller.consultar_resultado(ids)
        else:
            self.result_panel.mostrar_error_local(
                self._ultimo_mensaje_fallo or 'Error no identificado en la importación.'
            )
            self._go_step(4)
        self._controller.consultar_resumen()

    def _al_consultar_resultado(self, resultados):
        self._resultados_actuales = list(resultados or [])
        if not self._resultados_actuales:
            self.result_panel.mostrar_error_local(
                'No se pudo consultar el resultado en PostgreSQL.'
            )
        else:
            self.result_panel.mostrar_resultados(
                self._resultados_actuales, self._resumen_actual
            )
            self._ultimo_id_importacion = self._resultados_actuales[-1].id_importacion
        self._go_step(4)

    def _al_consultar_resumen(self, resumen):
        self._resumen_actual = list(resumen or [])
        self.result_panel.actualizar_resumen(self._resumen_actual)

    def _ver_datos_guardados(self):
        if not self._resultados_actuales:
            mostrar_mensaje(
                'Datos guardados',
                'Todavía no hay una importación confirmada para consultar.',
                self.window() or self,
            )
            return
        seleccionado = next(
            (
                resultado
                for resultado in self._resultados_actuales
                if resultado.id_importacion == self._ultimo_id_importacion
            ),
            self._resultados_actuales[-1],
        )
        self._detalle_resultado = seleccionado
        self._controller.consultar_detalle(seleccionado.id_importacion)

    def _al_consultar_detalle(self, ofertas):
        if self._detalle_resultado is None:
            return
        dialogo = SavedOffersDialog(
            self._detalle_resultado,
            list(ofertas or []),
            self.window() or self,
        )
        dialogo.exec()

    def _reset_workspace(self):
        self._invalidar_confirmacion()
        for entry in self.files:
            self._controller.descartar(entry.get('id_importacion'))
        self.files = []
        self.offers = []
        self.issues = []
        self.excluded = set()
        self._excluidas = {}
        self._reporte = None
        self.preview_button.setEnabled(False)
        self.name_edit.setText('Nueva comparación')
        self.matrix_search.clear()
        self.matrix_filter.setCurrentIndex(0)
        self._refresh_file_table()
        self._actualizar_estado_carga()
        self._actualizar_boton_historial()
        self._set_segment(0)
        self._go_step(1)

    def _refresh_file_table(self):
        self.file_table.blockSignals(True)
        self.file_table.setRowCount(len(self.files))
        for row, entry in enumerate(self.files):
            nombre = _item(entry['name'], Qt.AlignLeft, bold=True)
            tipo = Path(entry['name']).suffix.lstrip('.').upper()
            self.file_table.setItem(row, 0, _fixed_item(nombre))
            self.file_table.setItem(row, 1, _fixed_item(_item(tipo, foreground=MUTED)))
            self.file_table.setItem(row, 2, _fixed_item(_item(entry['size'])))
            self.file_table.setItem(row, 3, _fixed_item(_item('Listo', foreground=GREEN, bold=True)))
            remove = QPushButton('Quitar', objectName='supplierGhost')
            remove.clicked.connect(lambda checked=False, index=row: self._remove_file(index))
            self.file_table.setCellWidget(row, 4, remove)
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.file_table.blockSignals(False)

    def _remove_file(self, index):
        self._invalidar_confirmacion()
        if 0 <= index < len(self.files):
            entry = self.files.pop(index)
            self._controller.descartar(entry.get('id_importacion'))
        self.issues = []
        self.offers = []
        self.matrix_rows_data = []
        self._excluidas = {}
        self._reporte = None
        self.preview_button.setEnabled(False)
        self._refresh_issues()
        self._refresh_file_table()
        self._actualizar_estado_carga()

    def _actualizar_estado_carga(self):
        listo = 1 <= len(self.files) <= MAX_PROVEEDORES
        self.validate_button.setEnabled(listo)
        self._refresh_upload_summary()

    # -- validacion --------------------------------------------------------
    def _validate(self):
        if not self.files:
            return
        nombres = [entry['name'] for entry in self.files]
        if not confirmar_validacion(nombres, self.window() or self):
            return
        if all(entry['is_demo'] for entry in self.files):
            self._controller.preparar_demo(self._grupos_demo())
            return
        rutas = [str(entry['ruta']) for entry in self.files if not entry['is_demo']]
        self._controller.preparar(
            rutas, getattr(self._sesion, 'id_usuario', None)
        )

    def _refresh_issues(self):
        self.issue_table.blockSignals(True)
        self.issue_table.setRowCount(len(self.issues))
        for row, issue in enumerate(self.issues):
            valores = (
                issue.get('proveedor') or issue['archivo'],
                issue['numero_fila'],
                issue['campo'],
                issue['problema'],
            )
            for column, value in enumerate(valores):
                self.issue_table.setItem(
                    row, column,
                    _fixed_item(_item(
                        value, Qt.AlignLeft if column in (0, 3) else Qt.AlignCenter
                    )),
                )
            button = QPushButton(
                'Incluir' if issue['excluido'] else 'Excluir', objectName='supplierGhost'
            )
            button.setCheckable(True)
            button.setChecked(issue['excluido'])
            button.clicked.connect(lambda checked=False, index=row: self._toggle_exclude(index))
            self.issue_table.setCellWidget(row, 4, button)
        header = self.issue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.resizeSection(0, 130)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.resizeSection(2, 130)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.issue_table.blockSignals(False)
        self._actualizar_estado_avisos()

    def _actualizar_estado_avisos(self):
        if self._reporte is not None:
            errores = self._reporte.total_errores
            advertencias = self._reporte.total_advertencias
            con_error = sorted({
                issue['archivo'] for issue in self.issues if issue['grave']
            })
            texto = f'{errores} error(es)'
            if con_error:
                nombres = ', '.join(con_error[:2])
                if len(con_error) > 2:
                    nombres += f' (+{len(con_error) - 2})'
                texto += f' en {nombres}'
            texto += (
                f' · {advertencias} advertencia(s) · '
                f'{self._reporte.correctas} correctas'
            )
            self.validation_status.setText(texto)
            self.validation_status.setObjectName(
                'goodChip' if self._reporte.es_valido else 'warningChip'
            )
        else:
            pendientes = sum(
                1 for issue in self.issues if issue['grave'] and not issue['excluido']
            )
            self.validation_status.setText(
                f'{pendientes} aviso(s) · {len(self.excluded)} excluido(s)'
                if self.issues else 'Sin revisar'
            )
            self.validation_status.setObjectName(
                'warningChip' if pendientes else 'goodChip'
            )
        self.validation_status.style().unpolish(self.validation_status)
        self.validation_status.style().polish(self.validation_status)

    def _toggle_exclude(self, row):
        if not 0 <= row < len(self.issues):
            return
        issue = self.issues[row]
        issue['excluido'] = not issue['excluido']
        if issue['excluido']:
            self.excluded.add(row)
        else:
            self.excluded.discard(row)
        color = MUTED if issue['excluido'] else INK
        background = '#f3f5f8' if issue['excluido'] else 'white'
        for column in range(4):
            cell = self.issue_table.item(row, column)
            if cell is not None:
                cell.setForeground(QColor(color))
                cell.setBackground(QColor(background))
        button = self.issue_table.cellWidget(row, 4)
        if button is not None:
            button.setText('Incluir' if issue['excluido'] else 'Excluir')
        self._actualizar_estado_avisos()
        self._invalidar_confirmacion()

    # -- comparacion -------------------------------------------------------
    def _reconstruir_ofertas(self):
        self.offers = []
        for entry in self.files:
            preparada = entry.get('preparada')
            if preparada is None:
                continue
            clave = (
                preparada.id_importacion
                if preparada.id_importacion is not None
                else preparada.archivo.nombre
            )
            saltos = self._excluidas.get(clave, set())
            for oferta in preparada.ofertas:
                if oferta['numero_fila'] in saltos:
                    continue
                item = dict(oferta)
                item['provider'] = (entry.get('provider') or '').strip() or 'Proveedor'
                self.offers.append(item)

    def _compare(self, record=True):
        if not self.files:
            mostrar_mensaje('Sin datos', 'Carga archivos antes de comparar.', self.window() or self)
            return
        self._pending_record = record
        self._reconstruir_ofertas()
        self._aplicar_comparacion(record)

    def _aplicar_comparacion(self, record=True, preservar_vista=False):
        decision = self._preparar_datos_comparacion(record)
        if decision is None:
            mostrar_mensaje(
                'Sin datos', 'No hay ofertas válidas para comparar.', self.window() or self
            )
            return
        if not preservar_vista:
            self._go_step(3)

    @staticmethod
    def _clave_producto(offer):
        codigo = str(offer.get('code') or '').strip()
        if not codigo or codigo == '-':
            texto = str(offer.get('product') or '')
            prefijo = 'nombre'
        else:
            texto = codigo
            prefijo = 'codigo'
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join(char for char in texto if not unicodedata.combining(char))
        normalizado = re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()
        return f'{prefijo}:{normalizado}' if normalizado else prefijo

    def _visible_products(self):
        grouped = {}
        for offer in self.offers:
            clave = self._clave_producto(offer)
            if clave not in grouped:
                grouped[clave] = {'nombre': offer['product'], 'ofertas': {}}
            grouped[clave]['ofertas'][offer['provider']] = offer
        needle = self.matrix_search.text().strip().lower()
        category = self.matrix_filter.currentText()
        result = []
        for _, grupo in sorted(grouped.items()):
            product = grupo['nombre']
            by_provider = grupo['ofertas']
            if needle and needle not in product.lower():
                continue
            first = next(iter(by_provider.values()))
            if category != 'Todas las categorías' and first['category'] != category:
                continue
            prices = [offer['price'] for offer in by_provider.values() if offer['price'] is not None]
            best_price = min(prices) if prices else None
            best_provider = next(
                (name for name, offer in by_provider.items() if offer['price'] == best_price), '-'
            )
            spread = max(prices) - best_price if prices else 0.0
            result.append({
                'product': product,
                'offers': by_provider,
                'best_price': best_price,
                'best_provider': best_provider,
                'spread': spread,
            })
        return result

    def _refresh_matrix(self):
        if not self.offers:
            return
        rows_data = self._visible_products()
        self.matrix_rows_data = rows_data
        provider_count = len(self.provider_names)
        headers = (
            ('#', 'Producto', 'Categoría')
            + tuple(self.provider_names)
            + ('Mejor precio', 'Recomendación')
        )
        self.matrix_table.blockSignals(True)
        self.matrix_table.setColumnCount(len(headers))
        self.matrix_table.setHorizontalHeaderLabels(headers)
        self.matrix_table.setRowCount(len(rows_data))
        for row, data in enumerate(rows_data):
            category = next(iter(data['offers'].values())).get('category', '')
            self.matrix_table.setItem(row, 0, _fixed_item(_item(str(row + 1), foreground=INK)))
            self.matrix_table.setItem(row, 1, _fixed_item(_item(
                data['product'], Qt.AlignLeft, bold=True
            )))
            self.matrix_table.setItem(row, 2, _fixed_item(_item(category, Qt.AlignLeft)))
            for offset, provider in enumerate(self.provider_names, start=3):
                offer = data['offers'].get(provider)
                if offer is None:
                    cell = _fixed_item(_item('—', foreground=MUTED))
                else:
                    best = offer['price'] == data['best_price']
                    tooltip = (
                        f"Código: {offer.get('code', '-')}\n"
                        f"Mínimo: {_qty(offer.get('minimum'))} unidades\n"
                        f"Stock: {_qty(offer.get('stock'))} unidades\n"
                        f"Descuento desde: {_qty(offer.get('descuento_desde'))} unidades\n"
                        f"Descuento: {_porcentaje(offer.get('descuento_porcentaje'))}\n"
                        f"Entrega: {_qty(offer.get('entrega_dias'))} días"
                    )
                    cell = _fixed_item(_item(
                        _money(offer['price']),
                        bold=best,
                        foreground=INK,
                        background='#e8f8f1' if best else 'white',
                        tooltip=tooltip,
                    ))
                self.matrix_table.setItem(row, offset, cell)
            best_column = 3 + provider_count
            reco_column = best_column + 1
            self.matrix_table.setItem(row, best_column, _fixed_item(_item(
                _money(data['best_price']), foreground=INK, bold=True
            )))
            self.matrix_table.setItem(row, reco_column, _fixed_item(_item(
                data['best_provider'], foreground=INK, background='#f7f8f9', bold=True
            )))
        header = self.matrix_table.horizontalHeader()
        header.setMinimumSectionSize(80)
        for column in (0, 1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        for column in range(3, 3 + provider_count):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            header.resizeSection(column, 125)
        header.setSectionResizeMode(3 + provider_count, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4 + provider_count, QHeaderView.ResizeToContents)
        self.matrix_table.blockSignals(False)
        self.matrix_caption.setText(
            f'Mostrando {len(rows_data)} de {len(rows_data)} productos'
        )

    def _compute_decision(self):
        wins = Counter(data['best_provider'] for data in self.matrix_rows_data)
        price_sums = {provider: 0.0 for provider in self.provider_names}
        price_counts = Counter()
        for data in self.matrix_rows_data:
            for provider, offer in data['offers'].items():
                if provider not in price_sums or offer.get('price') is None:
                    continue
                price_sums[provider] += float(offer['price'])
                price_counts[provider] += 1
        averages = {
            provider: price_sums[provider] / price_counts[provider]
            for provider in self.provider_names
            if price_counts[provider]
        }
        ranked = sorted(
            self.provider_names,
            key=lambda provider: (
                -wins[provider],
                averages.get(provider, float('inf')),
                provider,
            ),
        )
        recommended = ranked[0] if ranked else '-'
        runner_up = ranked[1] if len(ranked) > 1 else None
        advantage = 0.0
        for data in self.matrix_rows_data:
            if data['best_provider'] != recommended:
                continue
            prices = sorted(
                float(offer['price'])
                for offer in data['offers'].values()
                if offer.get('price') is not None
            )
            if len(prices) > 1:
                advantage += prices[1] - prices[0]
        return {
            'recommended': recommended,
            'wins': wins[recommended],
            'runner_up': runner_up,
            'runner_up_wins': wins[runner_up] if runner_up else 0,
            'product_count': len(self.matrix_rows_data),
            'provider_count': len(self.provider_names),
            'average': averages.get(recommended, 0.0),
            'advantage': advantage,
        }

    def _decision_reasons(self, decision):
        reasons = [
            f"Obtuvo el mejor precio en {decision['wins']} de "
            f"{decision['product_count']} productos comparados.",
            f"Su precio promedio es {_money(decision['average'])}, "
            f"el más bajo entre los {decision['provider_count']} proveedores.",
        ]
        if decision['runner_up']:
            gap = decision['wins'] - decision['runner_up_wins']
            if gap > 0:
                reasons.append(
                    f"Supera a {decision['runner_up']} por {gap} productos con mejor precio."
                )
            else:
                reasons.append(
                    f"Empata en mejores precios con {decision['runner_up']}; "
                    "se eligió por menor precio promedio."
                )
        return reasons

    def _refresh_decision(self):
        if not self.matrix_rows_data:
            return None
        decision = self._compute_decision()
        self.reco_provider.setText(decision['recommended'])
        self.ind_wins_value.setText(
            f"{decision['wins']} de {decision['product_count']}"
        )
        self.ind_average_value.setText(_money(decision['average']))
        self.ind_advantage_value.setText(_money(decision['advantage']))
        reasons = self._decision_reasons(decision)
        self.reasons.setText('\n'.join(f'• {line}' for line in reasons))
        return decision


    def _export_results(self):
        if not self.matrix_rows_data:
            mostrar_mensaje(
                'Sin datos', 'Compara archivos antes de exportar.', self.window() or self
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Exportar comparación', 'comparacion_proveedores.xlsx', 'Excel (*.xlsx)'
        )
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter

        decision = self._compute_decision()
        reasons = self._decision_reasons(decision)
        wins = Counter(data['best_provider'] for data in self.matrix_rows_data)

        wb = Workbook()
        ws = wb.active
        ws.title = 'Comparativa'

        headers = ['#', 'Producto', 'Categoría'] + list(self.provider_names) + [
            'Mejor precio', 'Proveedor recomendado', 'Código recomendado',
            'Stock recomendado', 'Mínimo recomendado', 'Desc. desde recomendado',
            'Desc. % recomendado', 'Entrega recomendada',
        ]
        ws.append(headers)

        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill('solid', fgColor='5133F5')
        header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        thin = Side(style='thin', color='DFE5EE')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        best_fill = PatternFill('solid', fgColor='E8F8F1')
        best_font = Font(bold=True, color='087A51')
        reco_fill = PatternFill('solid', fgColor='F0EDFF')
        reco_font = Font(bold=True, color='5133F5')
        center = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')

        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = border

        for index, data in enumerate(self.matrix_rows_data, start=1):
            category = next(iter(data['offers'].values())).get('category', '')
            row_idx = index + 1
            ws.cell(row=row_idx, column=1, value=index)
            ws.cell(row=row_idx, column=2, value=data['product'])
            ws.cell(row=row_idx, column=3, value=category)
            for offset, provider in enumerate(self.provider_names):
                col = 4 + offset
                offer = data['offers'].get(provider)
                cell = ws.cell(row=row_idx, column=col)
                if offer is None or offer.get('price') is None:
                    cell.value = '-'
                    cell.alignment = center
                else:
                    price = float(offer['price'])
                    cell.value = price
                    cell.number_format = '"S/" #,##0.00'
                    cell.alignment = center
                    if provider == data['best_provider']:
                        cell.fill = best_fill
                        cell.font = best_font
            base = 4 + len(self.provider_names)
            winner = data['offers'].get(data['best_provider'], {})
            best_cell = ws.cell(row=row_idx, column=base, value=float(data['best_price']))
            best_cell.number_format = '"S/" #,##0.00'
            best_cell.font = best_font
            best_cell.alignment = center
            reco_cell = ws.cell(row=row_idx, column=base + 1, value=data['best_provider'])
            reco_cell.fill = reco_fill
            reco_cell.font = reco_font
            reco_cell.alignment = center
            detail_values = [
                winner.get('code', '-'),
                winner.get('stock'),
                winner.get('minimum'),
                winner.get('descuento_desde'),
                (float(winner.get('descuento_porcentaje') or 0) * 100) if winner.get('descuento_porcentaje') is not None else None,
                winner.get('entrega_dias'),
            ]
            for i, val in enumerate(detail_values, start=2):
                cell = ws.cell(row=row_idx, column=base + i)
                if val is None or val == '':
                    cell.value = '-'
                else:
                    cell.value = val
                cell.alignment = center
            ws.cell(row=row_idx, column=2).alignment = left_align
            ws.cell(row=row_idx, column=3).alignment = left_align
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col).border = border

        last_row = len(self.matrix_rows_data) + 1
        ws.freeze_panes = 'D2'
        if last_row >= 1:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{last_row}"
        widths = {1: 5, 2: 34, 3: 18}
        for col in range(4, 4 + len(self.provider_names)):
            widths[col] = 16
        base = 4 + len(self.provider_names)
        for col, w in [
            (base, 14), (base + 1, 22), (base + 2, 16), (base + 3, 12),
            (base + 4, 12), (base + 5, 14), (base + 6, 12), (base + 7, 12),
        ]:
            widths[col] = w
        for col, width in widths.items():
            ws.column_dimensions[get_column_letter(col)].width = width

        # Hoja Resumen
        ws2 = wb.create_sheet('Resumen')
        title_font = Font(bold=True, size=14, color='09142F')
        section_font = Font(bold=True, color='5133F5')
        label_font = Font(bold=True, color='34435E')
        note_font = Font(italic=True, color='60708F')
        ws2['A1'] = 'Resumen de comparación de precios'
        ws2['A1'].font = title_font
        ws2.merge_cells('A1:D1')

        row = 3
        ws2[f'A{row}'] = 'Datos generales'
        ws2[f'A{row}'].font = section_font
        row += 1
        info = [
            ('Nombre de la comparación', self.name_edit.text().strip() or 'Comparación'),
            ('Fecha de exportación', datetime.now().strftime('%d/%m/%Y %H:%M')),
            ('Proveedores comparados', ', '.join(self.provider_names)),
            ('Productos comparados', decision['product_count']),
        ]
        for label, value in info:
            ws2[f'A{row}'] = label
            ws2[f'A{row}'].font = label_font
            ws2[f'B{row}'] = value
            row += 1

        row += 1
        costo_combinada = sum(float(d['best_price']) for d in self.matrix_rows_data)
        ws2[f'A{row}'] = 'Recomendación y costos'
        ws2[f'A{row}'].font = section_font
        row += 1
        resumen_rows = [
            ('Proveedor recomendado', decision['recommended']),
            ('Productos donde es mejor precio', f"{decision['wins']} de {decision['product_count']}"),
            ('Precio promedio (recomendado)', float(decision['average'])),
            ('Ventaja estimada (ahorro vs alternativa)', float(decision['advantage'])),
            ('Costo compra combinada (mejor precio por producto)', float(costo_combinada)),
        ]
        for label, value in resumen_rows:
            ws2[f'A{row}'] = label
            ws2[f'A{row}'].font = label_font
            c = ws2[f'B{row}']
            c.value = value
            if isinstance(value, float):
                c.number_format = '"S/" #,##0.00'
            row += 1

        row += 1
        ws2[f'A{row}'] = 'Desglose por proveedor'
        ws2[f'A{row}'].font = section_font
        row += 1
        head = ['Proveedor', 'Ofertas', 'Productos ganados', 'Precio promedio']
        for col, h in enumerate(head, start=1):
            cell = ws2.cell(row=row, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = border
        row += 1
        for provider in self.provider_names:
            prices = [
                float(o['price']) for d in self.matrix_rows_data
                for p, o in d['offers'].items()
                if p == provider and o.get('price') is not None
            ]
            avg = (sum(prices) / len(prices)) if prices else None
            values = [provider, len(prices), wins.get(provider, 0), avg if avg is not None else '-']
            for col, val in enumerate(values, start=1):
                cell = ws2.cell(row=row, column=col, value=val)
                cell.border = border
                cell.alignment = left_align if col == 1 else center
                if col == 4 and isinstance(val, float):
                    cell.number_format = '"S/" #,##0.00'
            row += 1

        row += 1
        ws2[f'A{row}'] = 'Razones'
        ws2[f'A{row}'].font = section_font
        row += 1
        for reason in reasons:
            ws2[f'A{row}'] = f'• {reason}'
            ws2.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
            row += 1

        row += 1
        ws2[f'A{row}'] = 'Nota: estimaciones según los precios y ofertas cargadas en la comparación.'
        ws2[f'A{row}'].font = note_font
        ws2.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)

        ws2.column_dimensions['A'].width = 42
        ws2.column_dimensions['B'].width = 28
        ws2.column_dimensions['C'].width = 22
        ws2.column_dimensions['D'].width = 22

        wb.save(path)
        mostrar_mensaje(
            'Exportación completada',
            f'Se exportó la comparación ({len(self.matrix_rows_data)} productos) a:\n{path}',
            self.window() or self,
        )

    # -- historial ---------------------------------------------------------
    def _id_usuario(self):
        return getattr(self._sesion, 'id_usuario', None)

    def _valor_comparacion(self, comparacion, clave, defecto=None):
        if isinstance(comparacion, ComparacionGuardada):
            return getattr(comparacion, clave, defecto)
        return (comparacion or {}).get(clave, defecto)

    def _id_comparacion(self, comparacion):
        valor = self._valor_comparacion(comparacion, 'id_comparacion')
        return valor if isinstance(valor, int) else None

    def _actualizar_boton_historial(self):
        self.history_button.setText(f'Historial · {len(self.comparisons)}')
        if hasattr(self, 'historial_count'):
            self.historial_count.setText(f'{len(self.comparisons)} guardadas')

    def _fecha_filtro_historial(self):
        fecha = self.historial_fecha.date()
        if fecha == self.historial_fecha.minimumDate():
            return ''
        return fecha.toString('yyyy-MM-dd')

    def _recargar_historial(self):
        if not hasattr(self, 'historial_busqueda'):
            return
        categoria = self.historial_categoria.currentText()
        proveedor = self.historial_proveedor.currentText()
        self._comparaciones_controller.listar(
            self._id_usuario(),
            busqueda=self.historial_busqueda.text(),
            categoria='' if categoria.startswith('Todas') else categoria,
            proveedor='' if proveedor.startswith('Todos') else proveedor,
            fecha=self._fecha_filtro_historial(),
        )

    def _al_listar_comparaciones(self, comparaciones):
        self.comparisons = list(comparaciones or [])
        sin_filtros = (
            not self.historial_busqueda.text().strip()
            and self.historial_categoria.currentText().startswith('Todas')
            and self.historial_proveedor.currentText().startswith('Todos')
            and not self._fecha_filtro_historial()
        )
        if sin_filtros:
            self._actualizar_filtros_historial()
        self._actualizar_boton_historial()
        self._refresh_history()
        mensaje = self.historial_estado_texto.text()
        if not self.comparisons:
            self.historial_estado_texto.setText('No hay comparaciones guardadas.')
        elif mensaje.startswith(('No hay comparaciones', 'Historial:')):
            self.historial_estado_texto.setText('')

    def _actualizar_filtros_historial(self):
        actuales = (
            self.historial_categoria.currentText(),
            self.historial_proveedor.currentText(),
            self.historial_fecha.date(),
        )
        categorias = sorted({
            str(self._valor_comparacion(item, 'tipo_productos') or '')
            for item in self.comparisons
            if self._valor_comparacion(item, 'tipo_productos')
        })
        proveedores = sorted({
            str(self._valor_comparacion(item, 'proveedor_recomendado') or '')
            for item in self.comparisons
            if self._valor_comparacion(item, 'proveedor_recomendado')
        })
        for combo, opciones, texto in (
            (self.historial_categoria, categorias, 'Todas las categorías'),
            (self.historial_proveedor, proveedores, 'Todos los proveedores'),
        ):
            anterior = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(texto)
            combo.addItems(opciones)
            indice = combo.findText(anterior)
            combo.setCurrentIndex(indice if indice >= 0 else 0)
            combo.blockSignals(False)
        cambio = False
        for combo, anterior in zip(
            (self.historial_categoria, self.historial_proveedor),
            actuales[:2],
        ):
            if combo.currentText() != anterior:
                cambio = True
        if self.historial_fecha.date() != actuales[2]:
            cambio = True
        if cambio:
            self._recargar_historial()

    def _guardar_comparacion_actual(self, decision):
        id_usuario = self._id_usuario()
        clave = tuple(self._ids_importacion_actuales)
        if self._guardado_demo or not id_usuario or not clave:
            return
        if self._comparacion_guardada_ids == clave:
            return
        self._comparacion_guardada_ids = clave
        self._comparaciones_controller.guardar(
            self.name_edit.text().strip() or 'Productos de limpieza',
            self.category_combo.currentText().strip(),
            id_usuario,
            self._ids_importacion_actuales,
            decision,
            self.matrix_rows_data,
            self._decision_reasons(decision),
        )

    def _al_sincronizar_comparaciones(self, id_comparacion):
        if id_comparacion:
            self._al_guardar_comparacion(id_comparacion)
        else:
            self._recargar_historial()

    def _al_guardar_comparacion(self, id_comparacion):
        if not id_comparacion:
            self._comparacion_guardada_ids = None
            self.historial_estado_texto.setText(
                'No se pudo guardar la comparación en el historial.'
            )
            if self.confirm_button.text() == 'Importación completada':
                self.confirm_button.setText(
                    'Importación completada · comparación no guardada'
                )
            return
        self.historial_estado_texto.setText(
            f'Comparación #{id_comparacion} guardada en el historial.'
        )
        self._recargar_historial()

    def _al_fallo_comparacion(self, mensaje):
        self._comparacion_guardada_ids = None
        if hasattr(self, 'historial_estado_texto'):
            self.historial_estado_texto.setText(f'Historial: {mensaje}')
        if (
            hasattr(self, 'confirm_button')
            and self.confirm_button.text() == 'Importación completada'
        ):
            self.confirm_button.setText(
                'Importación completada · comparación no guardada'
            )

    def _al_detalle_comparacion(self, detalle):
        if detalle is None:
            self.historial_estado_texto.setText('No se pudo abrir la comparación.')
            return
        dialogo = ComparisonDetailDialog(detalle, parent=self.window() or self)
        dialogo.repetir.connect(self._repetir_desde_detalle)
        dialogo.exec()

    def _refresh_history(self):
        if not hasattr(self, 'history_table'):
            return
        self.history_table.blockSignals(True)
        self.history_table.setRowCount(len(self.comparisons))
        for row, comparison in enumerate(self.comparisons):
            fecha = self._valor_comparacion(comparison, 'fecha_creacion')
            fecha_texto = (
                fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha or '-')
            )
            hora_texto = fecha.strftime('%H:%M') if hasattr(fecha, 'strftime') else '-'
            values = (
                self._valor_comparacion(comparison, 'nombre', '-'),
                self._valor_comparacion(comparison, 'tipo_productos', '-') or '-',
                self._valor_comparacion(comparison, 'proveedor_recomendado', '-') or '-',
                fecha_texto,
                hora_texto,
                str(self._valor_comparacion(comparison, 'productos', 0)),
                _money(self._valor_comparacion(comparison, 'ahorro_estimado', 0)),
            )
            for column, value in enumerate(values):
                self.history_table.setItem(
                    row, column,
                    _fixed_item(
                        _item(value, Qt.AlignLeft if column in (0, 1, 2) else Qt.AlignCenter)
                    ),
                )
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)
            for nombre, icono, tooltip, funcion in (
                ('mostrar', _icono_accion_historial('mostrar'), 'Mostrar', self._open_comparison),
                ('editar', _icono_accion_historial('editar'), 'Editar', self._editar_comparacion),
                ('borrar', _icono_accion_historial('borrar'), 'Borrar', self._borrar_comparacion),
            ):
                boton = QPushButton(objectName=f'history{nombre.title()}Button')
                boton.setIcon(icono)
                boton.setToolTip(tooltip)
                boton.clicked.connect(
                    lambda checked=False, index=row, accion=funcion: accion(index)
                )
                actions_layout.addWidget(boton)
            self.history_table.setCellWidget(row, 7, actions)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        for column in (3, 4, 5, 6, 7):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.history_table.blockSignals(False)
        self._actualizar_boton_historial()

    def _open_comparison(self, index):
        comparison = self.comparisons[index]
        id_comparacion = self._id_comparacion(comparison)
        if id_comparacion is None:
            self.historial_estado_texto.setText('Esta comparación no tiene un ID guardado.')
            return
        self._comparaciones_controller.obtener_detalle(id_comparacion, self._id_usuario())

    def _duplicate_comparison(self, index):
        self._preparar_repeticion(self.comparisons[index])

    def _categorias_comparaciones(self):
        return sorted({
            str(self._valor_comparacion(item, 'tipo_productos') or '')
            for item in self.comparisons
            if self._valor_comparacion(item, 'tipo_productos')
        })

    def _editar_comparacion(self, index):
        comparison = self.comparisons[index]
        id_comparacion = self._id_comparacion(comparison)
        if id_comparacion is None:
            self.historial_estado_texto.setText('Esta comparación no tiene un ID guardado.')
            return
        dialogo = ComparisonEditDialog(
            comparison,
            self._categorias_comparaciones(),
            parent=self.window() or self,
        )

        def guardar(datos):
            self._comparaciones_controller.editar(
                id_comparacion,
                self._id_usuario(),
                datos['nombre'],
                datos['tipo_productos'],
                datos['justificacion'],
            )

        dialogo.guardada.connect(guardar)
        dialogo.exec()

    def _borrar_comparacion(self, index):
        comparison = self.comparisons[index]
        id_comparacion = self._id_comparacion(comparison)
        if id_comparacion is None:
            self.historial_estado_texto.setText('Esta comparación no tiene un ID guardado.')
            return
        nombre = self._valor_comparacion(comparison, 'nombre', 'esta comparación')
        if confirmar_borrado(nombre, self.window() or self):
            self._comparaciones_controller.eliminar(id_comparacion, self._id_usuario())

    def _al_editar_comparacion(self, id_comparacion):
        if not id_comparacion:
            self.historial_estado_texto.setText('No se pudo editar la comparación.')
            return
        self.historial_estado_texto.setText(
            f'Comparación #{id_comparacion} actualizada.'
        )
        self._recargar_historial()

    def _al_eliminar_comparacion(self, id_comparacion):
        if not id_comparacion:
            self.historial_estado_texto.setText('No se pudo borrar la comparación.')
            return
        self.historial_estado_texto.setText(
            f'Comparación #{id_comparacion} y sus registros eliminados.'
        )
        self._recargar_historial()

    def _repetir_desde_detalle(self, id_comparacion):
        comparison = next(
            (
                item for item in self.comparisons
                if self._id_comparacion(item) == id_comparacion
            ),
            {'nombre': f'Comparación #{id_comparacion}', 'tipo_productos': ''},
        )
        self._preparar_repeticion(comparison)

    def _preparar_repeticion(self, comparison):
        self._reset_workspace()
        nombre = self._valor_comparacion(comparison, 'nombre', 'Comparación')
        self.name_edit.setText(f'{nombre} (repetida)')
        categoria = self._valor_comparacion(comparison, 'tipo_productos', '')
        indice = self.category_combo.findText(categoria)
        if indice >= 0:
            self.category_combo.setCurrentIndex(indice)
        elif categoria:
            self.category_combo.setCurrentText(categoria)
        self.historial_estado_texto.setText(
            'Carga las cotizaciones actualizadas; la comparación anterior se conserva.'
        )
        self._set_segment(0)
        self._go_step(1)


__all__ = [
    'SuppliersImportTab',
    'validar_seleccion_archivos',
    'texto_confirmacion_validacion',
    'mensaje_confirmacion',
    'confirmar_validacion',
    'mostrar_mensaje',
]
