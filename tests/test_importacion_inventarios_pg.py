from datetime import date
from decimal import Decimal

import pytest

from models.importacion_inventario import (
    ConfirmacionIngreso,
    FilaIngreso,
    ResumenIngreso,
    ResultadoGuardadoIngreso,
)
from services.importacion_inventarios_pg import (
    ContextoPostgresIngresos,
    PersistenciaPostgresIngresos,
)


HASH = 'hash-ingreso-unico'


class ConexionFake:
    def __init__(self):
        self.estado = 'abierta'
        self.confirmaciones = 0
        self.reversiones = 0
        self.estado_cursor = 'abierta'

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *argumentos):
        return False

    def commit(self):
        self.confirmaciones += 1
        self.estado = 'confirmada'

    def rollback(self):
        self.reversiones += 1
        self.estado = 'revertida'

    def close(self):
        self.estado = 'cerrada'


class ImportacionesFake:
    def __init__(self, hashes=(), estado='validado'):
        self.hashes = set(hashes)
        self.estado = estado
        self.bloqueos = []
        self.consultas_hash = 0
        self.estados = []
        self.errores = []

    def existe_hash(self, hash_archivo, cursor=None):
        self.consultas_hash += 1
        return hash_archivo in self.hashes

    def obtener_importacion(
        self, id_importacion=None, hash_archivo=None, cursor=None, bloquear=False
    ):
        self.bloqueos.append(bloquear)
        if id_importacion != 99 or hash_archivo != HASH:
            return None
        return {
            'id_importacion': 99,
            'estado': self.estado,
            'nombre_archivo': 'ingreso.xlsx',
            'hash_archivo': HASH,
        }

    def confirmar_importacion(
        self, id_importacion, validos, rechazados, cursor, estado='completada'
    ):
        self.estados.append((id_importacion, validos, rechazados, estado))

    def registrar_errores(self, id_importacion, errores, cursor):
        self.errores.append((id_importacion, list(errores)))


class CatalogoFake:
    def __init__(self, existentes=None, fallar_creacion=False):
        self.existentes = existentes or {}
        self.fallar_creacion = fallar_creacion
        self.categorias = []
        self.creados = []
        self.actualizados = []

    def buscar_producto(self, codigo, nombre, marca, presentacion, cursor=None):
        return self.existentes.get(codigo)

    def asegurar_categoria(self, nombre, cursor=None):
        self.categorias.append(nombre)
        return 1

    def crear_producto(
        self, codigo, nombre, id_categoria, marca, presentacion, cursor=None,
        unidad_medida=None, stock_minimo=0, precio_venta=None,
        fecha_precio=None, fecha_stock=None,
    ):
        if self.fallar_creacion:
            raise RuntimeError('fallo al crear producto')
        self.creados.append((
            codigo, nombre, id_categoria, unidad_medida, stock_minimo,
            precio_venta, fecha_precio, fecha_stock,
        ))
        return 30

    def actualizar_producto_ingreso(
        self, id_producto, unidad_medida, stock_minimo, precio_venta,
        fecha_ingreso, cursor=None,
    ):
        self.actualizados.append((
            id_producto, unidad_medida, stock_minimo, precio_venta, fecha_ingreso
        ))


class ProveedoresFake:
    def asegurar_proveedor(self, nombre, cursor=None):
        return 5


class IngresosFake:
    def __init__(self):
        self.cabecera = None
        self.detalles = None
        self.consultas = []

    def crear_ingreso(
        self, id_importacion, id_proveedor, fecha_ingreso, numero_productos,
        total_unidades, cursor, observacion=None,
    ):
        self.cabecera = (
            id_importacion, id_proveedor, fecha_ingreso, numero_productos,
            total_unidades, observacion,
        )
        return 100

    def guardar_detalle(self, id_ingreso, filas, cursor):
        self.detalles = [
            (id_ingreso, id_producto, fila.numero_fila) for fila, id_producto in filas
        ]

    def obtener_ingreso(self, id_ingreso, cursor=None):
        self.consultas.append(id_ingreso)
        return ('ingreso', id_ingreso)


def _fila(numero_fila, codigo, producto):
    return FilaIngreso(
        numero_fila=numero_fila,
        proveedor='LimpiaSur',
        codigo=codigo,
        producto=producto,
        categoria='Limpieza',
        marca='ZEYVER',
        presentacion='Botella 1 L',
        unidad_medida='botella',
        cantidad=numero_fila + 4,
        stock_minimo=5,
        precio_compra=Decimal('10.00'),
        precio_venta=Decimal('15.00'),
        fecha_ingreso=date(2026, 11, 15),
    )


def _confirmacion():
    filas = (
        _fila(2, 'ZEY-L001', 'Lejía tradicional 1 L'),
        _fila(3, 'ZEY-L002', 'Detergente 1 L'),
    )
    return ConfirmacionIngreso(
        id_importacion=99,
        hash_archivo=HASH,
        proveedor='LimpiaSur',
        archivo='ingreso.xlsx',
        resumen=ResumenIngreso(
            proveedor='LimpiaSur',
            archivo='ingreso.xlsx',
            productos=2,
            total_unidades=13,
            fecha_min=date(2026, 11, 15),
            fecha_max=date(2026, 11, 15),
            categorias=('Limpieza',),
        ),
        filas=filas,
        id_usuario=7,
        total_filas=3,
        registros_rechazados=1,
    )


def _persistencia(
    importaciones=None, catalogo=None, conexion=None, contexto=None, ingresos=None
):
    conexion = conexion or ConexionFake()
    persistencia = PersistenciaPostgresIngresos(
        importaciones=importaciones or ImportacionesFake(),
        catalogo=catalogo or CatalogoFake(),
        proveedores=ProveedoresFake(),
        ingresos=ingresos or IngresosFake(),
        conexion_factory=lambda: conexion,
        contexto=contexto,
    )
    return persistencia, conexion


def test_guardar_registra_ingreso_y_actualiza_catalogo_en_una_transaccion():
    catalogo = CatalogoFake({
        'ZEY-L001': {
            'id_producto': 77,
            'nombre': 'Lejía tradicional 1 L',
            'marca': 'ZEYVER',
            'presentacion': 'Botella 1 L',
        }
    })
    importaciones = ImportacionesFake()
    ingresos = IngresosFake()
    persistencia, conexion = _persistencia(
        importaciones, catalogo, ingresos=ingresos
    )

    resultado = persistencia.guardar(_confirmacion())

    assert resultado == ResultadoGuardadoIngreso(
        id_ingreso=100,
        id_importacion=99,
        proveedor='LimpiaSur',
        archivo='ingreso.xlsx',
        fecha_ingreso=date(2026, 11, 15),
        productos=2,
        unidades=13,
        incidencias=1,
    )
    assert importaciones.bloqueos == [True]
    assert importaciones.estados == [(99, 2, 1, 'completada')]
    assert catalogo.actualizados == [(
        77, 'botella', 5, Decimal('15.00'), date(2026, 11, 15)
    )]
    assert catalogo.creados == [(
        'ZEY-L002', 'Detergente 1 L', 1, 'botella', 5,
        Decimal('15.00'), date(2026, 11, 15), date(2026, 11, 15),
    )]
    assert ingresos.cabecera == (
        99, 5, date(2026, 11, 15), 2, 13, 'Ingreso desde ingreso.xlsx'
    )
    assert ingresos.detalles == [(100, 77, 2), (100, 30, 3)]
    assert conexion.confirmaciones == 1
    assert conexion.reversiones == 0
    assert conexion.estado == 'cerrada'


def test_guardar_rechaza_hash_duplicado_y_revierte():
    importaciones = ImportacionesFake(hashes={HASH})
    persistencia, conexion = _persistencia(importaciones)

    with pytest.raises(ValueError, match='ya fue importado'):
        persistencia.guardar(_confirmacion())

    assert conexion.confirmaciones == 0
    assert conexion.reversiones == 1
    assert conexion.estado == 'cerrada'


def test_guardar_rechaza_producto_incoherente_y_revierte():
    catalogo = CatalogoFake({
        'ZEY-L001': {
            'id_producto': 77,
            'nombre': 'Producto distinto',
            'marca': 'ZEYVER',
            'presentacion': 'Botella 1 L',
        }
    })
    persistencia, conexion = _persistencia(catalogo=catalogo)

    with pytest.raises(ValueError, match='pertenece a otro producto'):
        persistencia.guardar(_confirmacion())

    assert catalogo.actualizados == []
    assert conexion.confirmaciones == 0
    assert conexion.reversiones == 1


def test_registrar_fallo_marca_importacion_como_fallida():
    importaciones = ImportacionesFake()
    persistencia, conexion = _persistencia(importaciones)

    persistencia.registrar_fallo(_confirmacion(), 'Fallo de base de datos')

    assert importaciones.estados == [(99, 0, 0, 'fallida')]
    assert len(importaciones.errores[0][1]) == 1
    assert conexion.confirmaciones == 1
    assert conexion.reversiones == 0


def test_contexto_postgres_reutiliza_cursor_y_cache():
    importaciones = ImportacionesFake()
    contexto = ContextoPostgresIngresos(
        importaciones=importaciones,
        conexion_factory=ConexionFake,
    )

    with contexto:
        assert contexto.existe_hash_actual(HASH) is False
        assert contexto.existe_hash_actual(HASH) is False
        importacion = contexto.obtener_importacion(
            id_importacion=99, hash_archivo=HASH
        )

    assert importaciones.consultas_hash == 1
    assert importacion['estado'] == 'validado'
    assert importaciones.bloqueos == [False]
