from decimal import Decimal

from models.importacion_proveedor import (
    ArchivoFuente,
    CotizacionPreparada,
    FilaCotizacion,
    AvisoImportacion,
    ReporteValidacion,
)
from services.importacion_proveedores_service import (
    COLUMNS,
    construir_vista_previa,
    filtrar_filas_vista_previa,
    preparar_confirmacion,
)


class PersistenciaEspia:
    def __init__(self):
        self.llamadas = 0

    def guardar(self, preparadas, excluidas=None, id_usuario=None):
        self.llamadas += 1
        return []


def _fila(numero, codigo, producto, categoria, stock, precio='5.00'):
    return FilaCotizacion(
        numero_fila=numero,
        producto=producto,
        categoria=categoria,
        precio_unitario=Decimal(precio),
        compra_minima=1,
        stock_disponible=stock,
        descuento_desde=5,
        descuento_porcentaje=Decimal('0.10'),
        entrega_dias=2,
        codigo=codigo,
        marca='Marca',
        presentacion='1 L',
    )


def _preparada(nombre='LimpiaSur.xlsx', proveedor='LimpiaSur', filas=None, errores=()):
    filas = filas if filas is not None else [
        _fila(2, 'LIM-001', 'Lejía tradicional 1 L', 'Limpieza', 120),
        _fila(3, 'LIM-002', 'Alcohol en gel 500 mL', 'Limpieza', 0, '12.50'),
    ]
    return CotizacionPreparada(
        archivo=ArchivoFuente(
            nombre=nombre, hash_archivo=nombre, tamano_bytes=100
        ),
        proveedor=proveedor,
        columnas=list(COLUMNS),
        indices={columna: indice for indice, columna in enumerate(COLUMNS)},
        filas=filas,
        reporte=ReporteValidacion(
            total_filas=len(filas),
            correctas=len(filas),
            errores=list(errores),
        ),
    )


def test_construir_vista_previa_resumen_y_filas():
    vista = construir_vista_previa([_preparada()])

    assert len(vista.filas) == 2
    assert vista.resumen.productos == 2
    assert vista.resumen.sin_stock == 1
    assert vista.resumen.errores == 0
    assert vista.resumen.advertencias == 0
    assert vista.resumen.proveedores == 1
    assert vista.resumen.archivos == 1
    assert vista.es_valido is True
    assert vista.es_confirmable is True
    assert vista.filas[0].estado_producto == 'No verificado (BD desactivada)'
    assert vista.filas[0].descuento_porcentaje == Decimal('0.10')


def test_exclusiones_se_aplican_por_archivo():
    primera = _preparada(nombre='A.xlsx', proveedor='Proveedor A')
    segunda = _preparada(nombre='B.xlsx', proveedor='Proveedor B')
    vista = construir_vista_previa(
        [primera, segunda], {'A.xlsx': {3}}
    )

    assert [fila.excluida for fila in vista.filas] == [False, True, False, False]
    assert vista.resumen.excluidos == 1
    assert vista.resumen.productos == 3


def test_busqueda_y_filtros_de_vista_previa():
    filas = [
        _fila(2, 'LIM-001', 'Lejía tradicional 1 L', 'Limpieza', 120),
        _fila(3, 'ALC-002', 'Alcohol en gel 500 mL', 'Higiene', 0, '12.50'),
        _fila(4, 'DET-003', 'Detergente líquido', 'Limpieza', 8, '11.50'),
    ]
    vista = construir_vista_previa([_preparada(filas=filas)])

    por_codigo = filtrar_filas_vista_previa(vista.filas, texto='alc-002')
    por_nombre = filtrar_filas_vista_previa(vista.filas, texto='detergente')
    por_categoria = filtrar_filas_vista_previa(
        vista.filas, categoria='Higiene'
    )
    con_stock = filtrar_filas_vista_previa(
        vista.filas, disponibilidad='Con stock'
    )
    sin_stock = filtrar_filas_vista_previa(
        vista.filas, disponibilidad='Sin stock'
    )

    assert [fila.codigo for fila in por_codigo] == ['ALC-002']
    assert [fila.codigo for fila in por_nombre] == ['DET-003']
    assert [fila.codigo for fila in por_categoria] == ['ALC-002']
    assert len(con_stock) == 2
    assert [fila.codigo for fila in sin_stock] == ['ALC-002']


def test_confirmacion_no_escribe_y_excluye_filas_marcadas():
    vista = construir_vista_previa(
        [_preparada()], {'LimpiaSur.xlsx': {3}}
    )
    persistencia = PersistenciaEspia()
    confirmacion = preparar_confirmacion(
        vista, {'LimpiaSur.xlsx': {3}}
    )

    assert persistencia.llamadas == 0
    assert confirmacion.resumen.productos == 1
    assert len(confirmacion.filas) == 1
    assert confirmacion.filas[0].codigo == 'LIM-001'
    assert confirmacion.excluidas == {'LimpiaSur.xlsx': {3}}


def test_no_confirmable_con_errores_o_sin_filas():
    error = AvisoImportacion(
        numero_fila=2, campo='Precio unitario', valor_original='0',
        problema='Debe ser mayor a cero'
    )
    con_error = construir_vista_previa([_preparada(errores=[error])])
    sin_filas = construir_vista_previa([_preparada(filas=[])])

    assert con_error.es_valido is False
    assert con_error.es_confirmable is False
    assert sin_filas.es_confirmable is False
