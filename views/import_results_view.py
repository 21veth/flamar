"""Panel de resultados de la Etapa 5 y consulta de datos guardados."""

from decimal import Decimal

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from views.import_shared import BLUE, IMPORT_STYLES, ORANGE


RESULT_STYLES = '''
QDialog#SavedOffersDialog { background:#ffffff; color:#09142f; font-family:"Segoe UI Variable","Segoe UI"; }
QLabel#resultSuccessChip { background:#e8f8f1; color:#087a51; border-radius:6px; padding:5px 9px; font-size:10px; font-weight:800; }
QLabel#resultErrorChip { background:#fdecea; color:#b42318; border-radius:6px; padding:5px 9px; font-size:10px; font-weight:800; }
QLabel#resultNeutralChip { background:#eef2f8; color:#4c5b76; border-radius:6px; padding:5px 9px; font-size:10px; font-weight:800; }
QLabel#resultOkBadge { background:#e8f8f1; color:#087a51; border-radius:6px; padding:4px 8px; font-size:10px; font-weight:800; }
QLabel#resultErrorBadge { background:#fdecea; color:#b42318; border-radius:6px; padding:4px 8px; font-size:10px; font-weight:800; }
QLabel#resultMessage { color:#09142f; font-size:12px; font-weight:700; }
QLabel#resultHint { color:#60708f; font-size:10px; }
QLabel#resultDetailLabel { color:#60708f; font-size:10px; font-weight:700; }
QLabel#resultDetailValue { color:#09142f; font-size:11px; font-weight:700; }
QLabel#resultTotal { color:#5133f5; font-size:11px; font-weight:800; }
QFrame#resultMetric { background:#ffffff; border:1px solid #dfe5ee; border-radius:9px; }
QLabel#resultMetricValue { font-size:24px; font-weight:800; }
QLabel#resultMetricLabel { color:#60708f; font-size:10px; font-weight:700; }
QLabel#resultMetricIcon { border-radius:21px; }
QPushButton#resultDisclosure { background:#f7f9fc; color:#273754; border:1px solid #dfe5ee; border-radius:7px; padding:8px 11px; font-size:11px; font-weight:800; text-align:left; }
QPushButton#resultDisclosure:checked { background:#ede9fe; color:#5133f5; border-color:#c9bcff; }
QTableWidget#resultTable { background:#ffffff; color:#273754; border:none; font-size:10px; alternate-background-color:#f8fafc; selection-background-color:#ede9fe; selection-color:#5133f5; }
QTableWidget#resultTable::item { border-bottom:1px solid #e5eaf1; padding:4px; }
QTableWidget#resultTable QHeaderView::section { background:#f7f9fc; color:#12203a; border:none; border-bottom:1px solid #dfe5ee; padding:6px 5px; font-size:10px; font-weight:700; }
QTableWidget#savedOffersTable { background:#ffffff; color:#273754; border:1px solid #dfe5ee; border-radius:8px; font-size:11px; selection-background-color:#ede9fe; selection-color:#5133f5; }
QTableWidget#savedOffersTable::item { border-bottom:1px solid #e5eaf1; padding:6px 5px; }
QTableWidget#savedOffersTable QHeaderView::section { background:#f7f9fc; color:#12203a; border:none; border-bottom:1px solid #dfe5ee; padding:8px 6px; font-size:10px; font-weight:800; }
QPushButton#resultPrimary { background:#5133f5; color:#ffffff; border:none; border-radius:7px; padding:9px 18px; font-size:11px; font-weight:800; min-width:96px; }
QPushButton#resultPrimary:hover { background:#4025c9; }
'''


def _icono_pixmap(tipo, color, size=27):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    escala = size / 38.0
    tono = QColor(color)
    painter.setPen(QPen(tono, 2.1 * escala))
    painter.setBrush(Qt.NoBrush)

    if tipo == 'procesados':
        bandeja = QPainterPath()
        bandeja.addRoundedRect(
            QRectF(7 * escala, 23 * escala, 24 * escala, 9 * escala),
            2.5 * escala, 2.5 * escala,
        )
        painter.drawPath(bandeja)
        painter.drawLine(
            QRectF(19 * escala, 7 * escala, 0, 0).topLeft(),
            QRectF(19 * escala, 21 * escala, 0, 0).topLeft(),
        )
        flecha = QPainterPath()
        flecha.moveTo(13 * escala, 15 * escala)
        flecha.lineTo(19 * escala, 21 * escala)
        flecha.lineTo(25 * escala, 15 * escala)
        painter.drawPath(flecha)
    elif tipo == 'guardadas':
        escudo = QPainterPath()
        escudo.moveTo(19 * escala, 5 * escala)
        escudo.lineTo(30 * escala, 9 * escala)
        escudo.lineTo(29 * escala, 20 * escala)
        escudo.lineTo(19 * escala, 32 * escala)
        escudo.lineTo(9 * escala, 20 * escala)
        escudo.lineTo(8 * escala, 9 * escala)
        escudo.closeSubpath()
        painter.drawPath(escudo)
        painter.setPen(QPen(tono, 2.6 * escala))
        painter.drawLine(
            QRectF(13 * escala, 19 * escala, 0, 0).topLeft(),
            QRectF(17 * escala, 23 * escala, 0, 0).topLeft(),
        )
        painter.drawLine(
            QRectF(17 * escala, 23 * escala, 0, 0).topLeft(),
            QRectF(26 * escala, 13 * escala, 0, 0).topLeft(),
        )
    else:
        painter.drawEllipse(QRectF(7 * escala, 7 * escala, 24 * escala, 24 * escala))
        painter.setPen(QPen(tono, 2.5 * escala))
        painter.drawLine(
            QRectF(14 * escala, 14 * escala, 0, 0).topLeft(),
            QRectF(24 * escala, 24 * escala, 0, 0).topLeft(),
        )
        painter.drawLine(
            QRectF(24 * escala, 14 * escala, 0, 0).topLeft(),
            QRectF(14 * escala, 24 * escala, 0, 0).topLeft(),
        )
    painter.end()
    return pixmap


def _texto(valor):
    if valor is None or str(valor).strip() == '':
        return '-'
    return str(valor)


def _fecha(valor):
    if valor is None:
        return '-'
    try:
        return valor.strftime('%d/%m/%Y %H:%M')
    except (AttributeError, ValueError):
        return str(valor)


def _dinero(valor):
    if valor is None:
        return '-'
    return f'S/ {float(valor):,.2f}'


def _porcentaje(valor):
    if valor is None:
        return '-'
    return f'{float(Decimal(str(valor))) * 100:.2f}%'


def _item(valor, alineacion=Qt.AlignLeft):
    celda = QTableWidgetItem(_texto(valor))
    celda.setTextAlignment(alineacion | Qt.AlignVCenter)
    return celda


def _tabla(encabezados, altura=130, object_name='resultTable'):
    tabla = QTableWidget(0, len(encabezados), objectName=object_name)
    tabla.setHorizontalHeaderLabels(encabezados)
    tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
    tabla.setAlternatingRowColors(False)
    tabla.verticalHeader().setVisible(False)
    tabla.horizontalHeader().setStretchLastSection(True)
    tabla.setMinimumHeight(altura)
    return tabla


def _llenar_tabla(tabla, filas):
    filas = list(filas)
    tabla.setRowCount(len(filas))
    for fila, valores in enumerate(filas):
        for columna, valor in enumerate(valores):
            tabla.setItem(fila, columna, _item(valor))
    tabla.resizeRowsToContents()


class ImportResultPanel(QFrame):
    """Muestra el resultado leido de PostgreSQL al terminar la importacion."""

    importar_otro = Signal()
    ver_datos = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, objectName='supplierCard')
        self.resultados = []
        self.resumen = []
        self._cantidad_errores = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(9)

        cabecera = QHBoxLayout()
        cabecera.addWidget(QLabel('Resultado de importación', objectName='cardTitle'))
        self.estado_chip = QLabel('Sin resultados', objectName='resultNeutralChip')
        cabecera.addWidget(self.estado_chip)
        cabecera.addStretch()
        layout.addLayout(cabecera)

        self.mensaje = QLabel(
            'Confirma una importación para ver el resultado guardado en PostgreSQL.',
            objectName='resultMessage',
        )
        self.mensaje.setWordWrap(True)
        layout.addWidget(self.mensaje)

        metricas = QHBoxLayout()
        metricas.setSpacing(10)
        self.metrica_procesados = self._metrica(
            'procesados', '0', 'Procesados', BLUE, '#eaf3ff'
        )
        self.metrica_guardadas = self._metrica(
            'guardadas', '0', 'Ofertas guardadas', '#087a51', '#e8f8f1'
        )
        self.metrica_rechazados = self._metrica(
            'rechazados', '0', 'Rechazados', ORANGE, '#fff5e5'
        )
        for metrica in (
            self.metrica_procesados,
            self.metrica_guardadas,
            self.metrica_rechazados,
        ):
            metricas.addWidget(metrica, 1)
        layout.addLayout(metricas)

        datos = QFrame(objectName='resultMetric')
        datos_layout = QVBoxLayout(datos)
        datos_layout.setContentsMargins(12, 9, 12, 9)
        datos_layout.setSpacing(5)
        datos_layout.addWidget(QLabel('Información de la importación', objectName='cardTitle'))
        self.detalles = {}
        campos = (
            ('Proveedor', 'proveedor'),
            ('Archivo', 'archivo'),
            ('Estado', 'estado'),
            ('Fecha de importación', 'fecha'),
            ('Cotización', 'cotizacion'),
        )
        renglon = QHBoxLayout()
        renglon.setSpacing(10)
        for indice, (etiqueta, clave) in enumerate(campos):
            celda = QWidget()
            celda_layout = QVBoxLayout(celda)
            celda_layout.setContentsMargins(0, 0, 0, 0)
            celda_layout.setSpacing(0)
            celda_layout.addWidget(QLabel(etiqueta, objectName='resultDetailLabel'))
            valor = QLabel('-', objectName='resultDetailValue')
            valor.setWordWrap(True)
            celda_layout.addWidget(valor)
            self.detalles[clave] = valor
            renglon.addWidget(celda, 1)
            if indice % 2 == 1:
                datos_layout.addLayout(renglon)
                renglon = QHBoxLayout()
                renglon.setSpacing(10)
        if renglon.count() > 0:
            datos_layout.addLayout(renglon)
        layout.addWidget(datos)

        errores_titulo = QHBoxLayout()
        self.errores_boton = QPushButton(
            '▸ Detalle de errores · 0', objectName='resultDisclosure'
        )
        self.errores_boton.setCheckable(True)
        self.errores_boton.setChecked(False)
        self.errores_badge = QLabel('Sin errores', objectName='resultOkBadge')
        errores_titulo.addWidget(self.errores_boton, 1)
        errores_titulo.addWidget(self.errores_badge)
        layout.addLayout(errores_titulo)
        self.tabla_errores = _tabla(('Fila', 'Campo', 'Valor original', 'Problema'), 105)
        self.tabla_errores.setVisible(False)
        self.errores_boton.toggled.connect(self.tabla_errores.setVisible)
        self.errores_boton.toggled.connect(self._refrescar_boton_errores)
        layout.addWidget(self.tabla_errores)

        resumen_titulo = QHBoxLayout()
        resumen_titulo.addWidget(QLabel('Proveedores importados', objectName='cardTitle'))
        resumen_titulo.addStretch()
        self.total_ofertas = QLabel('Total de ofertas importadas: 0', objectName='resultTotal')
        resumen_titulo.addWidget(self.total_ofertas)
        layout.addLayout(resumen_titulo)
        self.tabla_resumen = _tabla(('Proveedor', 'Ofertas', 'Estado'), 105)
        layout.addWidget(self.tabla_resumen)

        acciones = QHBoxLayout()
        acciones.addStretch()
        otro = QPushButton('Importar otro Excel', objectName='supplierSecondary')
        otro.clicked.connect(self.importar_otro.emit)
        ver = QPushButton('Ver datos guardados', objectName='supplierPrimary')
        ver.clicked.connect(self.ver_datos.emit)
        acciones.addWidget(otro)
        acciones.addWidget(ver)
        layout.addLayout(acciones)

        self.limpiar()

    def _metrica(self, tipo, valor, etiqueta, color, fondo):
        tarjeta = QFrame(objectName='resultMetric')
        tarjeta.setFixedHeight(88)
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(12, 10, 12, 10)
        fila.setSpacing(12)

        icono = QLabel(objectName='resultMetricIcon')
        icono.setFixedSize(42, 42)
        icono.setAlignment(Qt.AlignCenter)
        icono.setPixmap(_icono_pixmap(tipo, color))
        icono.setStyleSheet(f'background:{fondo};border-radius:21px;')

        texto = QVBoxLayout()
        texto.setSpacing(0)
        numero = QLabel(valor, objectName='resultMetricValue')
        numero.setMinimumWidth(54)
        numero.setStyleSheet(
            f'color:{color};font-size:24px;font-weight:800;'
            'background:transparent;border:0;'
        )
        texto.addWidget(numero)
        texto.addWidget(QLabel(etiqueta, objectName='resultMetricLabel'))

        fila.addWidget(icono)
        fila.addLayout(texto, 1)
        return tarjeta

    @staticmethod
    def _valor_metrica(tarjeta):
        return tarjeta.findChild(QLabel, 'resultMetricValue')

    def limpiar(self):
        self.resultados = []
        self.resumen = []
        self.estado_chip.setText('Sin resultados')
        self.estado_chip.setObjectName('resultNeutralChip')
        self.mensaje.setText(
            'Confirma una importación para ver el resultado guardado en PostgreSQL.'
        )
        for tarjeta in (
            self.metrica_procesados,
            self.metrica_guardadas,
            self.metrica_rechazados,
        ):
            self._valor_metrica(tarjeta).setText('0')
        for valor in self.detalles.values():
            valor.setText('-')
        self._actualizar_errores([])
        _llenar_tabla(self.tabla_resumen, [])
        self.total_ofertas.setText('Total de ofertas importadas: 0')
        self._pulir_chip()

    def _pulir_chip(self):
        self.estado_chip.style().unpolish(self.estado_chip)
        self.estado_chip.style().polish(self.estado_chip)

    def _refrescar_boton_errores(self):
        flecha = '▾' if self.errores_boton.isChecked() else '▸'
        self.errores_boton.setText(
            f'{flecha} Detalle de errores · {self._cantidad_errores}'
        )

    def _actualizar_errores(self, filas):
        filas = list(filas or [])
        self._cantidad_errores = len(filas)
        self.errores_badge.setText(
            'Sin errores' if not filas else f'{self._cantidad_errores} error(es)'
        )
        self.errores_badge.setObjectName(
            'resultOkBadge' if not filas else 'resultErrorBadge'
        )
        self.errores_badge.style().unpolish(self.errores_badge)
        self.errores_badge.style().polish(self.errores_badge)
        _llenar_tabla(self.tabla_errores, filas)
        if not filas:
            self.errores_boton.setChecked(False)
        self._refrescar_boton_errores()

    def mostrar_resultados(self, resultados, resumen=None):
        self.resultados = list(resultados or [])
        self.resumen = list(resumen or [])
        if not self.resultados:
            self.limpiar()
            return
        exitoso = all(resultado.exitoso for resultado in self.resultados)
        self.estado_chip.setText(
            'Importación exitosa' if exitoso else 'Importación fallida'
        )
        self.estado_chip.setObjectName(
            'resultSuccessChip' if exitoso else 'resultErrorChip'
        )
        self._pulir_chip()
        proveedores = ', '.join(
            resultado.proveedor or '-' for resultado in self.resultados
        )
        if exitoso:
            self.mensaje.setText(
                '¡Importación completada correctamente!\n'
                f'Los datos de {proveedores} se guardaron en PostgreSQL.'
            )
        else:
            self.mensaje.setText(
                'La importación no se completó.\n'
                'No se guardaron cotizaciones ni ofertas; revisa el detalle de errores.'
            )
        self._valor_metrica(self.metrica_procesados).setText(
            str(sum(resultado.registros_totales for resultado in self.resultados))
        )
        self._valor_metrica(self.metrica_guardadas).setText(
            str(sum(resultado.ofertas_guardadas for resultado in self.resultados))
        )
        self._valor_metrica(self.metrica_rechazados).setText(
            str(sum(resultado.registros_rechazados for resultado in self.resultados))
        )
        self.detalles['proveedor'].setText(proveedores)
        self.detalles['archivo'].setText(
            ', '.join(resultado.nombre_archivo for resultado in self.resultados)
        )
        self.detalles['estado'].setText(
            ', '.join(resultado.estado for resultado in self.resultados)
        )
        self.detalles['fecha'].setText(
            _fecha(self.resultados[0].fecha_importacion)
        )
        self.detalles['cotizacion'].setText(
            ', '.join(
                str(resultado.id_cotizacion or '-')
                for resultado in self.resultados
            )
        )
        errores = [
            error
            for resultado in self.resultados
            for error in resultado.errores
        ]
        self._actualizar_errores(
            (
                (error.numero_fila, error.campo, error.valor_original, error.problema)
                for error in errores
            )
        )
        self.actualizar_resumen(self.resumen)

    def mostrar_error_local(self, motivo):
        self.resultados = []
        self.estado_chip.setText('Importación fallida')
        self.estado_chip.setObjectName('resultErrorChip')
        self._pulir_chip()
        self.mensaje.setText(
            'La importación no se completó.\n'
            f'{motivo}\n'
            'No se guardaron cotizaciones ni ofertas.'
        )
        for tarjeta in (
            self.metrica_procesados,
            self.metrica_guardadas,
            self.metrica_rechazados,
        ):
            self._valor_metrica(tarjeta).setText('0')
        self.detalles['proveedor'].setText('-')
        self.detalles['archivo'].setText('-')
        self.detalles['estado'].setText('fallida')
        self.detalles['fecha'].setText('-')
        self.detalles['cotizacion'].setText('-')
        self._actualizar_errores(((1, 'importacion', '-', motivo),))

    def actualizar_resumen(self, resumen):
        self.resumen = list(resumen or [])
        _llenar_tabla(
            self.tabla_resumen,
            (
                (fila.proveedor, fila.ofertas, fila.estado)
                for fila in self.resumen
            ),
        )
        self.total_ofertas.setText(
            f'Total de ofertas importadas: '
            f'{sum(fila.ofertas for fila in self.resumen)}'
        )


class SavedOffersDialog(QDialog):
    """Muestra las ofertas realmente almacenadas para una importacion."""

    def __init__(self, resultado, ofertas, parent=None):
        super().__init__(parent)
        self.setObjectName('SavedOffersDialog')
        self.setWindowTitle(
            f'Datos guardados · {resultado.proveedor or resultado.nombre_archivo}'
        )
        self.setStyleSheet(IMPORT_STYLES + RESULT_STYLES)
        self.resize(1120, 660)
        self.setMinimumSize(960, 540)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)
        layout.addWidget(QLabel(
            f'Importación #{resultado.id_importacion} · '
            f'{resultado.nombre_archivo} · {_fecha(resultado.fecha_importacion)}',
            objectName='resultHint',
        ))
        self.tabla = _tabla(
            (
                'Código', 'Producto', 'Categoría', 'Precio', 'Stock', 'Mínimo',
                'Desc. desde', 'Desc. %', 'Entrega',
            ),
            420,
            'savedOffersTable',
        )
        _llenar_tabla(
            self.tabla,
            (
                (
                    oferta.codigo,
                    oferta.producto,
                    oferta.categoria,
                    _dinero(oferta.precio_unitario),
                    oferta.stock_disponible,
                    oferta.compra_minima,
                    oferta.descuento_desde,
                    _porcentaje(oferta.descuento_porcentaje),
                    oferta.entrega_dias,
                )
                for oferta in ofertas
            ),
        )
        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(1, QHeaderView.Stretch)
        cabecera.setMinimumSectionSize(78)
        layout.addWidget(self.tabla)
        self.total = QLabel(f'{len(ofertas)} oferta(s) guardada(s)', objectName='resultTotal')
        layout.addWidget(self.total)
        aceptar = QPushButton('Cerrar', objectName='resultPrimary')
        aceptar.clicked.connect(self.accept)
        layout.addWidget(aceptar, alignment=Qt.AlignRight)


__all__ = ['RESULT_STYLES', 'ImportResultPanel', 'SavedOffersDialog']
