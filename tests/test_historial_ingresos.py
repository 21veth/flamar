from datetime import date, datetime
from decimal import Decimal

import pytest

from controllers.ingresos_inventario_controller import IngresosInventarioController
from models.importacion_inventario import IngresoHistorial
from repositories.ingreso_inventario_repository import IngresoInventarioRepository
from services.importacion_inventarios_service import ImportacionIngresosService


class CursorFake:
    def __init__(self, filas=(), cabecera=None, detalles=()):
        self.filas = list(filas)
        self.cabecera = cabecera
        self.detalles = list(detalles)
        self.consultas = []
        self.parametros = []
        self.resultado = []
        self.cerrado = False

    def execute(self, consulta, parametros=()):
        self.consultas.append(consulta)
        self.parametros.append(tuple(parametros))
        if 'COUNT(DISTINCT' in consulta:
            self.resultado = self.filas
        elif 'FROM public.ingresos_inventario' in consulta:
            self.resultado = [self.cabecera] if self.cabecera else []
        else:
            self.resultado = self.detalles

    def fetchall(self):
        return list(self.resultado)

    def fetchone(self):
        return self.resultado[0] if self.resultado else None

    def close(self):
        self.cerrado = True


class ConexionFake:
    def __init__(self, cursor):
        self.cursor_fake = cursor
        self.cerrada = False

    def cursor(self):
        return self.cursor_fake

    def close(self):
        self.cerrada = True


class PersistenciaHistorialFake:
    def __init__(self, ingresos=(), detalle=None):
        self.ingresos = list(ingresos)
        self.detalle = detalle
        self.filtros = None

    def listar_ingresos(self, busqueda='', proveedor='', estado='', fecha=''):
        self.filtros = {
            'busqueda': busqueda,
            'proveedor': proveedor,
            'estado': estado,
            'fecha': fecha,
        }
        return self.ingresos

    def obtener_ingreso(self, id_ingreso):
        self.filtros = {'id_ingreso': id_ingreso}
        return self.detalle


class ServicioHistorialFake:
    def __init__(self, ingresos=(), detalle=None):
        self.ingresos = list(ingresos)
        self.detalle = detalle
        self.llamadas = []

    def listar_ingresos(self, busqueda='', proveedor='', estado='', fecha=''):
        self.llamadas.append(('listar', {
            'busqueda': busqueda,
            'proveedor': proveedor,
            'estado': estado,
            'fecha': fecha,
        }))
        return self.ingresos

    def obtener_ingreso(self, id_ingreso):
        self.llamadas.append(('detalle', id_ingreso))
        return self.detalle


def test_repositorio_listar_es_solo_lectura_y_aplica_filtros(monkeypatch):
    fila = (
        7,
        datetime(2026, 11, 22, 10, 30),
        'LimpiaSur',
        'limpieza.xlsx',
        3,
        80,
        Decimal('812.00'),
        'completada',
        'admin',
    )
    cursor = CursorFake(filas=[fila])
    conexion = ConexionFake(cursor)
    monkeypatch.setattr(
        'repositories.ingreso_inventario_repository.obtener_conexion',
        lambda: conexion,
    )
    repositorio = IngresoInventarioRepository()

    resultado = repositorio.listar(
        busqueda='limpieza',
        proveedor='LimpiaSur',
        estado='completada',
        fecha='2026-11-22',
    )

    consulta = cursor.consultas[0]
    assert consulta.lstrip().upper().startswith('SELECT')
    assert 'INSERT' not in consulta.upper()
    assert 'UPDATE' not in consulta.upper()
    assert 'DELETE' not in consulta.upper()
    assert cursor.parametros[0] == (
        'limpieza', '%limpieza%', '%limpieza%',
        'LimpiaSur', 'LimpiaSur',
        'completada', 'completada',
        '2026-11-22', '2026-11-22',
    )
    assert resultado == [IngresoHistorial(
        id_ingreso=7,
        creado_en=fila[1],
        proveedor='LimpiaSur',
        archivo='limpieza.xlsx',
        productos=3,
        unidades=80,
        costo_total=Decimal('812.00'),
        estado='completada',
        responsable='admin',
    )]
    assert cursor.cerrado
    assert conexion.cerrada


def test_repositorio_obtener_detalle_incluye_marca_presentacion_y_costo(monkeypatch):
    cabecera = (
        7, 99, 'LimpiaSur', 'limpieza.xlsx',
        date(2026, 11, 15), 2, 80,
        datetime(2026, 11, 22, 10, 30), 'completada', 'admin',
    )
    detalles = [
        (
            2, 'ZEY-L001', 'Lejía tradicional 1 L', 'Limpieza',
            37, 5, Decimal('5.20'), Decimal('8.00'), 'botella',
            date(2026, 11, 15), 'ZEYVER', 'Botella 1 L',
        ),
        (
            3, 'ZEY-D001', 'Detergente en polvo 1 kg', 'Limpieza',
            25, 4, Decimal('12.50'), Decimal('18.00'), 'bolsa',
            date(2026, 11, 15), 'ZEYVER', 'Bolsa 1 kg',
        ),
    ]
    cursor = CursorFake(cabecera=cabecera, detalles=detalles)
    conexion = ConexionFake(cursor)
    monkeypatch.setattr(
        'repositories.ingreso_inventario_repository.obtener_conexion',
        lambda: conexion,
    )
    repositorio = IngresoInventarioRepository()

    ingreso = repositorio.obtener_ingreso(7)

    assert all(
        consulta.lstrip().upper().startswith('SELECT')
        for consulta in cursor.consultas
    )
    assert ingreso.estado == 'completada'
    assert ingreso.responsable == 'admin'
    assert ingreso.costo_total == Decimal('504.90')
    assert ingreso.filas[0].marca == 'ZEYVER'
    assert ingreso.filas[0].presentacion == 'Botella 1 L'
    assert ingreso.filas[0].subtotal == Decimal('192.40')
    assert ingreso.filas[1].subtotal == Decimal('312.50')
    assert cursor.consultas[1].strip().endswith('WHERE d.id_ingreso = %s ORDER BY d.numero_fila_excel')


def test_servicio_delega_listado_al_persistencia():
    persistencia = PersistenciaHistorialFake(ingresos=[object()])
    servicio = ImportacionIngresosService(persistencia=persistencia)

    resultado = servicio.listar_ingresos(
        busqueda='dulce', proveedor='DulceSur', estado='completada', fecha='2026-11-22'
    )

    assert resultado == persistencia.ingresos
    assert persistencia.filtros == {
        'busqueda': 'dulce',
        'proveedor': 'DulceSur',
        'estado': 'completada',
        'fecha': '2026-11-22',
    }


def test_controller_emite_listado_y_detalle():
    servicio = ServicioHistorialFake(ingresos=[object()], detalle='detalle')
    controller = IngresosInventarioController(servicio=servicio)
    listado = []
    detalles = []
    fallos = []
    controller.listado.connect(listado.append)
    controller.detalle_consultado.connect(detalles.append)
    controller.fallo.connect(fallos.append)

    assert controller.listar(busqueda='', proveedor='DulceSur', estado='completada', fecha='')
    assert controller.obtener_detalle(7)
    assert not fallos
    assert len(listado) == 1
    assert detalles == ['detalle']
    assert servicio.llamadas == [
        ('listar', {
            'busqueda': '', 'proveedor': 'DulceSur',
            'estado': 'completada', 'fecha': '',
        }),
        ('detalle', 7),
    ]
