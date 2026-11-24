from decimal import Decimal

import pytest

from models.importacion_proveedor import (
    ArchivoFuente,
    CotizacionPreparada,
    FilaCotizacion,
    ReporteValidacion,
    ResultadoGuardado,
)
from repositories.catalogo_repository import CatalogoRepository
from repositories.importacion_repository import ImportacionRepository
from services.importacion_proveedores_pg import ContextoPostgres, PersistenciaPostgres


class ConexionFake:
    def __init__(self):
        self.estado = 'abierta'
        self.confirmaciones = 0
        self.reversiones = 0

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


class CursorFake:
    def __init__(self, fila=None):
        self.fila = fila
        self.parametros = None

    def execute(self, consulta, parametros):
        self.parametros = parametros

    def fetchone(self):
        return self.fila


class ImportacionesFake:
    def __init__(self, hashes=(), fallar=False):
        self.hashes = set(hashes)
        self.fallar = fallar
        self.consultas_hash = 0
        self.intentos = []
        self.errores = []
        self.cotizaciones = []
        self.detalles = []
        self.estados = []

    def existe_hash(self, hash_archivo, cursor=None):
        self.consultas_hash += 1
        return hash_archivo in self.hashes

    def crear_importacion(self, id_usuario, nombre, hash_archivo, totales, cursor):
        if self.fallar:
            raise RuntimeError('fallo al crear importacion')
        self.intentos.append((id_usuario, nombre, hash_archivo, totales))
        return 10

    def registrar_errores(self, id_importacion, errores, cursor):
        self.errores.append((id_importacion, list(errores)))

    def crear_cotizacion(self, id_proveedor, id_importacion, cursor):
        self.cotizaciones.append((id_proveedor, id_importacion))
        return 20

    def guardar_detalle(self, id_cotizacion, id_producto, fila, cursor):
        self.detalles.append((id_cotizacion, id_producto, fila.numero_fila))

    def confirmar_importacion(self, id_importacion, validos, rechazados, cursor):
        self.estados.append((id_importacion, validos, rechazados, 'completada'))


class CatalogoFake:
    def __init__(self, existentes=None):
        self.existentes = existentes or {}
        self.consultas_producto = 0
        self.consultas_categoria = 0
        self.categorias = []
        self.creados = []

    def buscar_producto(self, codigo, nombre, marca, presentacion, cursor=None):
        self.consultas_producto += 1
        return self.existentes.get(codigo)

    def categoria_existe(self, nombre, cursor=None):
        self.consultas_categoria += 1
        return True

    def asegurar_categoria(self, nombre, cursor=None):
        self.categorias.append(nombre)
        return 1

    def crear_producto(self, codigo, nombre, id_categoria, marca, presentacion, cursor=None):
        self.creados.append((codigo, nombre, id_categoria))
        return 30


class ProveedoresFake:
    def __init__(self):
        self.consultas = 0

    def proveedor_existe(self, nombre, cursor=None):
        self.consultas += 1
        return True

    def asegurar_proveedor(self, nombre, cursor=None):
        return 5


def _fila(numero_fila, codigo):
    return FilaCotizacion(
        numero_fila=numero_fila,
        producto='Lejía',
        categoria='Limpieza',
        precio_unitario=Decimal('5.20'),
        compra_minima=1,
        stock_disponible=10,
        descuento_desde=0,
        descuento_porcentaje=Decimal('0.10'),
        entrega_dias=2,
        codigo=codigo,
        marca='Blanco',
        presentacion='1 L',
    )


def _preparada():
    return CotizacionPreparada(
        archivo=ArchivoFuente(
            nombre='limpiasur.xlsx',
            hash_archivo='hash-unico',
            tamano_bytes=100,
        ),
        proveedor='LimpiaSur',
        columnas=[],
        indices={},
        filas=[_fila(2, 'P001'), _fila(3, 'P002'), _fila(4, 'P003')],
        reporte=ReporteValidacion(total_filas=3, correctas=3),
    )


def _persistencia(importaciones, catalogo=None, conexion=None):
    conexion = conexion or ConexionFake()
    persistencia = PersistenciaPostgres(
        importaciones=importaciones,
        catalogo=catalogo or CatalogoFake(),
        proveedores=ProveedoresFake(),
        conexion_factory=lambda: conexion,
    )
    return persistencia, conexion


def test_guardar_respeta_exclusiones_y_reutiliza_producto():
    preparada = _preparada()
    catalogo = CatalogoFake({
        'P001': {
            'id_producto': 77,
            'nombre': 'Lejía',
            'marca': 'Blanco',
            'presentacion': '1 L',
        }
    })
    importaciones = ImportacionesFake()
    persistencia, conexion = _persistencia(importaciones, catalogo)

    resultados = persistencia.guardar([preparada], {'limpiasur.xlsx': {3}}, 7)

    assert resultados == [
        ResultadoGuardado(
            id_importacion=10,
            id_cotizacion=20,
            proveedor='LimpiaSur',
            registros_validos=2,
            registros_rechazados=1,
            ofertas_registradas=2,
        )
    ]
    assert importaciones.intentos == [(7, 'limpiasur.xlsx', 'hash-unico', 3)]
    assert importaciones.cotizaciones == [(5, 10)]
    assert importaciones.detalles == [(20, 77, 2), (20, 30, 4)]
    assert importaciones.estados == [(10, 2, 1, 'completada')]
    assert catalogo.creados == [('P003', 'Lejía', 1)]
    assert preparada.id_importacion == 10
    assert preparada.id_cotizacion == 20
    assert conexion.confirmaciones == 1
    assert conexion.reversiones == 0
    assert conexion.estado == 'cerrada'


def test_guardar_acepta_hash_repetido():
    importaciones = ImportacionesFake(hashes={'hash-unico'})
    persistencia, conexion = _persistencia(importaciones)

    resultados = persistencia.guardar([_preparada()], None, 7)

    assert len(resultados) == 1
    assert importaciones.intentos[0][2] == 'hash-unico'
    assert importaciones.consultas_hash == 0
    assert conexion.confirmaciones == 1
    assert conexion.reversiones == 0
    assert conexion.estado == 'cerrada'


def test_guardar_revierte_si_falla_la_escritura():
    importaciones = ImportacionesFake(fallar=True)
    persistencia, conexion = _persistencia(importaciones)

    with pytest.raises(RuntimeError, match='fallo al crear importacion'):
        persistencia.guardar([_preparada()], None, 7)

    assert conexion.confirmaciones == 0
    assert conexion.reversiones == 1


def test_guardar_requiere_usuario():
    persistencia, conexion = _persistencia(ImportacionesFake())

    with pytest.raises(ValueError, match='usuario'):
        persistencia.guardar([_preparada()])

    assert conexion.estado == 'abierta'


def test_guardar_detalle_normaliza_descuento_desde_cero():
    cursor = CursorFake()
    repo = ImportacionRepository()

    repo.guardar_detalle(1, 2, _fila(2, 'P001'), cursor)

    assert cursor.parametros[5] is None


def test_buscar_producto_devuelve_identidad():
    cursor = CursorFake((77, 'Lejía', 'Blanco', '1 L'))

    resultado = CatalogoRepository().buscar_producto('P001', None, None, None, cursor)

    assert resultado == {
        'id_producto': 77,
        'nombre': 'Lejía',
        'marca': 'Blanco',
        'presentacion': '1 L',
    }


def test_contexto_reutiliza_conexion_y_cachea_consultas():
    conexiones = []

    def fabrica():
        conexion = ConexionFake()
        conexiones.append(conexion)
        return conexion

    importaciones = ImportacionesFake()
    catalogo = CatalogoFake()
    proveedores = ProveedoresFake()
    contexto = ContextoPostgres(importaciones, catalogo, proveedores, fabrica)

    with contexto:
        assert contexto.existe_hash('hash') is False
        assert contexto.existe_hash('hash') is False
        assert contexto.buscar_producto('P001') is None
        assert contexto.buscar_producto('P001') is None
        assert contexto.categoria_existe('Limpieza') is True
        assert contexto.categoria_existe('Limpieza') is True
        assert contexto.proveedor_existe('LimpiaSur') is True
        assert contexto.proveedor_existe('LimpiaSur') is True

    assert len(conexiones) == 1
    assert importaciones.consultas_hash == 1
    assert catalogo.consultas_producto == 1
    assert catalogo.consultas_categoria == 1
    assert proveedores.consultas == 1
    assert conexiones[0].estado == 'cerrada'
    assert contexto._conexion is None
