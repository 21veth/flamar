from datetime import datetime
from decimal import Decimal

import pytest

from controllers.proveedores_import_controller import ProveedoresImportController
from models.importacion_proveedor import (
    ArchivoFuente,
    CotizacionPreparada,
    ErrorImportacion,
    IntentoFallido,
    OfertaGuardada,
    ReporteValidacion,
    ResumenProveedor,
    ResultadoImportacion,
)
from repositories.importacion_repository import ImportacionRepository
from repositories.resultado_importacion_repository import (
    ResultadoImportacionRepository,
)
from services.importacion_proveedores_pg import PersistenciaPostgres
from services.importacion_proveedores_service import ImportacionProveedoresService


class CursorFake:
    def __init__(self, filas=(), fila=None):
        self.filas = list(filas)
        self.fila = fila
        self.consultas = []
        self.parametros = []

    def execute(self, consulta, parametros=()):
        self.consultas.append(consulta)
        self.parametros.append(parametros)

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.fila


class ConexionFake:
    def __init__(self, cursor):
        self._cursor = cursor
        self.confirmaciones = 0
        self.reversiones = 0
        self.cerrada = False

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *argumentos):
        return False

    def execute(self, consulta, parametros=()):
        self._cursor.execute(consulta, parametros)

    def fetchone(self):
        return self._cursor.fetchone()

    def commit(self):
        self.confirmaciones += 1

    def rollback(self):
        self.reversiones += 1

    def close(self):
        self.cerrada = True


class ImportacionesFake:
    def __init__(self):
        self.intentos = []
        self.errores = []

    def crear_importacion(
        self, id_usuario, nombre, hash_archivo, totales, cursor,
        estado='pendiente',
    ):
        self.intentos.append((id_usuario, nombre, totales, estado))
        return 99

    def registrar_errores(self, id_importacion, avisos, cursor):
        self.errores.append((id_importacion, list(avisos)))


class ResultadosFake:
    def __init__(self):
        self.errores = [ErrorImportacion(1, 5, 'precio', '0', 'Precio inválido')]
        self.ofertas = [OfertaGuardada(
            'P001', 'Lejía', 'Limpieza', Decimal('5.20'), 10, 1,
            None, Decimal('0.10'), 2,
        )]
        self.resumen = [
            ResumenProveedor('LimpiaSur', 30, 'completada'),
            ResumenProveedor('HigieneTotal', 30, 'completada'),
            ResumenProveedor('CleanMax', 30, 'completada'),
        ]

    def obtener_resultado(self, id_importacion):
        return ResultadoImportacion(
            id_importacion=id_importacion,
            nombre_archivo='Proveedor_01_LimpiaSur_ZEYVER.xlsx',
            fecha_importacion=datetime(2026, 11, 21, 10, 30),
            registros_totales=30,
            registros_validos=30,
            registros_rechazados=0,
            estado='completada',
            id_cotizacion=20,
            proveedor='LimpiaSur',
            ofertas_guardadas=30,
        )

    def obtener_errores(self, id_importacion):
        return self.errores

    def obtener_ofertas(self, id_importacion):
        return self.ofertas

    def obtener_resumen_proveedores(self):
        return self.resumen


class PersistenciaFalla:
    def guardar(self, preparadas, excluidas=None, id_usuario=None):
        raise ValueError('fallo al guardar')

    def registrar_fallo(self, preparadas, motivo, id_usuario=None):
        return [IntentoFallido(99, 'limpiasur.xlsx', 'LimpiaSur', motivo, 30)]


class ServicioParcial:
    ultimo_fallo = [IntentoFallido(99, 'a.xlsx', 'LimpiaSur', 'boom', 30)]

    def confirmar(self, preparadas, excluidas=None, id_usuario=None):
        raise ValueError('boom')

    def consultar_resultado(self, ids):
        return ['resultado']

    def consultar_ofertas(self, id_importacion):
        return ['oferta']

    def consultar_resumen(self):
        return ['resumen']

    def registrar_fallo(self, preparadas, motivo, id_usuario=None):
        return ['fallo']


@pytest.fixture(scope='module')
def aplicacion():
    from PySide6.QtCore import QCoreApplication

    return QCoreApplication.instance() or QCoreApplication([])


def _preparada():
    return CotizacionPreparada(
        archivo=ArchivoFuente(
            nombre='limpiasur.xlsx', hash_archivo='hash-unico', tamano_bytes=100,
        ),
        proveedor='LimpiaSur',
        columnas=[],
        indices={},
        reporte=ReporteValidacion(total_filas=30, correctas=30),
    )


def test_repositorio_devuelve_resultado_leido_de_postgres():
    cursor = CursorFake(filas=[(
        10, 'LimpiaSur.xlsx', datetime(2026, 11, 21), 30, 29, 1,
        'completada', 20, 'LimpiaSur', 29, 1,
    )])
    repositorio = ResultadoImportacionRepository()

    resultado = repositorio.obtener_resultado(10, cursor)

    assert resultado.ofertas_guardadas == 29
    assert resultado.proveedor == 'LimpiaSur'
    assert resultado.estado == 'completada'
    assert 'COUNT(DISTINCT d.id_detalle_cotizacion)' in cursor.consultas[0]
    assert cursor.parametros[0] == (10,)


def test_repositorio_devuelve_errores_ofertas_y_resumen():
    errores = [(1, 5, 'precio', '0', 'Precio inválido')]
    ofertas = [(
        'P001', 'Lejía', 'Limpieza', Decimal('5.20'), 10, 1, None,
        Decimal('0.10'), 2,
    )]
    resumen = [('LimpiaSur', 'completada', 30, datetime(2026, 11, 21), 10)]
    repositorio = ResultadoImportacionRepository()

    assert repositorio.obtener_errores(10, CursorFake(errores))[0].numero_fila == 5
    oferta = repositorio.obtener_ofertas(10, CursorFake(ofertas))[0]
    assert oferta.precio_unitario == Decimal('5.20')
    fila = repositorio.obtener_resumen_proveedores(CursorFake(resumen))[0]
    assert (fila.proveedor, fila.ofertas, fila.estado) == (
        'LimpiaSur', 30, 'completada'
    )


def test_existe_hash_ignora_intentos_fallidos():
    cursor = CursorFake(filas=[])

    assert ImportacionRepository().existe_hash('hash-fallido', cursor) is False
    assert "estado = 'completada'" in cursor.consultas[0]


def test_servicio_compone_resultado_con_errores():
    servicio = ImportacionProveedoresService(resultados=ResultadosFake())

    resultado = servicio.consultar_resultado([10])[0]
    ofertas = servicio.consultar_ofertas(10)
    resumen = servicio.consultar_resumen()

    assert resultado.errores[0].problema == 'Precio inválido'
    assert ofertas[0].codigo == 'P001'
    assert sum(fila.ofertas for fila in resumen) == 90


def test_fallo_de_guardado_queda_registrado_y_se_propaga():
    servicio = ImportacionProveedoresService(persistencia=PersistenciaFalla())

    with pytest.raises(ValueError, match='fallo al guardar'):
        servicio.confirmar([_preparada()], {}, 7)

    assert servicio.ultimo_fallo[0].id_importacion == 99
    assert servicio.ultimo_fallo[0].motivo == 'fallo al guardar'


def test_registrar_fallo_guarda_solo_intento_y_error():
    importaciones = ImportacionesFake()
    cursor = CursorFake(fila=99)
    conexion = ConexionFake(cursor)
    persistencia = PersistenciaPostgres(
        importaciones=importaciones,
        conexion_factory=lambda: conexion,
    )

    intentos = persistencia.registrar_fallo(
        [_preparada()], 'fallo de prueba', 7
    )

    assert intentos[0].id_importacion == 99
    assert importaciones.intentos == [(7, 'limpiasur.xlsx', 30, 'fallida')]
    assert importaciones.errores[0][1][-1].campo == 'importacion'
    assert importaciones.errores[0][1][-1].problema == 'fallo de prueba'
    assert conexion.confirmaciones == 1
    assert conexion.reversiones == 0
    assert conexion.cerrada is True


def test_controlador_emite_fallo_detallado_y_nuevas_consultas(aplicacion):
    controlador = ProveedoresImportController(servicio=ServicioParcial())
    fallos = []
    detallados = []
    consultados = []
    controlador.fallo.connect(fallos.append)
    controlador.fallo_detallado.connect(detallados.append)
    controlador.resultado_consultado.connect(consultados.append)

    assert controlador.guardar([_preparada()], {}, 7) is False
    assert controlador.consultar_resultado([10]) is True

    assert fallos == ['boom']
    assert detallados[0][0].id_importacion == 99
    assert consultados == [['resultado']]
