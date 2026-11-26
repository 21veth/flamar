import os
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTableWidget

from controllers.ingresos_inventario_controller import IngresosInventarioController
from models.importacion_inventario import (
    IngresoDetalleGuardado,
    IngresoGuardado,
    IngresoHistorial,
)
from models.sesion_usuario import SesionUsuario
from views import historial_ingresos_view as modulo_historial
from views.historial_ingresos_view import (
    DETALLE_COLUMNS,
    HISTORIAL_COLUMNS,
    HistorialIngresosView,
    IngresoHistorialDialog,
)
from views.core_inventory_views import ImportDataView
from views.inventario_section_view import InventarioSectionView


_APP = None


@pytest.fixture(scope='session')
def aplicacion():
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


class ServicioHistorialFake:
    def __init__(self, ingresos=(), detalle=None):
        self.ingresos = list(ingresos)
        self.detalle = detalle
        self.filtros = []
        self.detalle_id = None

    def listar_ingresos(self, busqueda='', proveedor='', estado='', fecha=''):
        self.filtros.append({
            'busqueda': busqueda,
            'proveedor': proveedor,
            'estado': estado,
            'fecha': fecha,
        })
        return self.ingresos

    def obtener_ingreso(self, id_ingreso):
        self.detalle_id = id_ingreso
        return self.detalle


class DialogoFake:
    def __init__(self, ingreso, parent=None):
        self.ingreso = ingreso
        self.ejecutado = False

    def exec(self):
        self.ejecutado = True
        return 0


def _ingreso(identificador, proveedor, archivo, costo):
    return IngresoHistorial(
        id_ingreso=identificador,
        creado_en=datetime(2026, 11, 22, 10, 30),
        proveedor=proveedor,
        archivo=archivo,
        productos=2,
        unidades=62,
        costo_total=Decimal(costo),
        estado='completada',
        responsable='admin',
    )


def _detalle():
    filas = (
        IngresoDetalleGuardado(
            numero_fila=2,
            codigo='ZEY-L001',
            producto='Lejía tradicional 1 L',
            categoria='Limpieza',
            cantidad=37,
            stock_minimo=5,
            precio_compra=Decimal('5.20'),
            precio_venta=Decimal('8.00'),
            unidad_medida='botella',
            fecha_ingreso=date(2026, 11, 15),
            marca='ZEYVER',
            presentacion='Botella 1 L',
        ),
        IngresoDetalleGuardado(
            numero_fila=3,
            codigo='ZEY-D001',
            producto='Detergente en polvo 1 kg',
            categoria='Limpieza',
            cantidad=25,
            stock_minimo=4,
            precio_compra=Decimal('12.50'),
            precio_venta=Decimal('18.00'),
            unidad_medida='bolsa',
            fecha_ingreso=date(2026, 11, 15),
            marca='ZEYVER',
            presentacion='Bolsa 1 kg',
        ),
    )
    return IngresoGuardado(
        id_ingreso=1,
        id_importacion=99,
        proveedor='LimpiaSur',
        archivo='limpieza.xlsx',
        fecha_ingreso=date(2026, 11, 15),
        numero_productos=2,
        total_unidades=62,
        creado_en=datetime(2026, 11, 22, 10, 30),
        filas=filas,
        estado='completada',
        responsable='admin',
        costo_total=Decimal('504.90'),
    )


def _encabezados(tabla):
    return tuple(
        tabla.horizontalHeaderItem(indice).text()
        for indice in range(tabla.columnCount())
    )


def test_historial_muestra_columnas_y_datos_desde_postgres(aplicacion):
    servicio = ServicioHistorialFake(ingresos=[
        _ingreso(2, 'DulceSur', 'dulces.xlsx', '312.50'),
        _ingreso(1, 'LimpiaSur', 'limpieza.xlsx', '512.40'),
    ])
    vista = HistorialIngresosView(IngresosInventarioController(servicio))

    vista.recargar()

    assert _encabezados(vista.tabla) == HISTORIAL_COLUMNS
    assert vista.tabla.rowCount() == 2
    assert vista.tabla.item(0, 0).text() == '#2'
    assert vista.tabla.item(0, 2).text() == 'DulceSur'
    assert vista.tabla.item(0, 6).text() == 'S/ 312.50'
    assert vista.tabla.item(0, 7).text() == 'Completado'
    assert servicio.filtros[-1] == {
        'busqueda': '',
        'proveedor': '',
        'estado': 'completada',
        'fecha': '',
    }


def test_filtros_de_historial_actualizan_la_consulta(aplicacion):
    servicio = ServicioHistorialFake(ingresos=[
        _ingreso(1, 'LimpiaSur', 'limpieza.xlsx', '512.40'),
        _ingreso(2, 'DulceSur', 'dulces.xlsx', '312.50'),
    ])
    vista = HistorialIngresosView(IngresosInventarioController(servicio))
    vista.recargar()

    vista.proveedor.setCurrentText('DulceSur')
    vista.busqueda.setText('dulces')
    vista.fecha.setDate(QDate(2026, 11, 22))
    vista.estado.setCurrentText('Todos los estados')

    assert servicio.filtros[-1] == {
        'busqueda': 'dulces',
        'proveedor': 'DulceSur',
        'estado': '',
        'fecha': '2026-11-22',
    }


def test_ver_detalle_consulta_solo_el_ingreso_elegido(aplicacion, monkeypatch):
    servicio = ServicioHistorialFake(
        ingresos=[
            _ingreso(1, 'LimpiaSur', 'limpieza.xlsx', '512.40'),
            _ingreso(2, 'DulceSur', 'dulces.xlsx', '312.50'),
        ],
        detalle=_detalle(),
    )
    dialogos = []

    def fabricar_dialogo(ingreso, parent=None):
        dialogo = DialogoFake(ingreso, parent)
        dialogos.append(dialogo)
        return dialogo

    monkeypatch.setattr(modulo_historial, 'IngresoHistorialDialog', fabricar_dialogo)
    vista = HistorialIngresosView(IngresosInventarioController(servicio))
    vista.recargar()

    boton = vista.tabla.cellWidget(1, 8).findChild(QPushButton)
    boton.click()

    assert servicio.detalle_id == 2
    assert len(dialogos) == 1
    assert dialogos[0].ingreso.id_ingreso == 1
    assert dialogos[0].ejecutado


def test_dialogo_de_detalle_muestra_productos_precios_y_subtotales(aplicacion):
    dialogo = IngresoHistorialDialog(_detalle())
    tablas = dialogo.findChildren(QTableWidget)

    assert len(tablas) == 1
    assert _encabezados(tablas[0]) == DETALLE_COLUMNS
    assert tablas[0].rowCount() == 2
    assert tablas[0].item(0, 2).text() == 'Lejía tradicional 1 L'
    assert tablas[0].item(0, 3).text() == 'ZEYVER'
    assert tablas[0].item(0, 5).text() == 'Botella 1 L'
    assert tablas[0].item(0, 9).text() == 'S/ 192.40'
    assert tablas[0].item(1, 9).text() == 'S/ 312.50'
    titulos = [
        etiqueta.text() for etiqueta in dialogo.findChildren(QLabel)
        if etiqueta.objectName() == 'detalleTitulo'
    ]
    assert titulos == ['Ingreso N.º 001 — LimpiaSur']


def test_inventario_tiene_dos_segmentos_y_recarga_tras_guardar(aplicacion):
    servicio = ServicioHistorialFake(ingresos=[
        _ingreso(1, 'LimpiaSur', 'limpieza.xlsx', '512.40'),
    ])
    seccion = InventarioSectionView(None, servicio=servicio)

    assert seccion.registro_button.text() == 'Registrar ingreso'
    assert seccion.historial_button.text() == 'Historial'
    assert seccion.paginas.currentIndex() == 0
    assert not servicio.filtros

    seccion.historial_button.click()

    assert seccion.paginas.currentIndex() == 1
    assert len(servicio.filtros) == 1

    seccion.registro.ingreso_guardado.emit(123)

    assert len(servicio.filtros) == 2


def test_importar_datos_permite_scroll_vertical(aplicacion):
    vista = ImportDataView(SesionUsuario(1, 'Usuario Prueba', 'administrador'))

    assert vista.scroll.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
