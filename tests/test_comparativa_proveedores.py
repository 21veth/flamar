from decimal import Decimal

from models.importacion_proveedor import (
    ArchivoFuente,
    CotizacionPreparada,
    FilaCotizacion,
    ReporteValidacion,
)
from services.importacion_proveedores_service import COLUMNS
from views.import_suppliers_view import SuppliersImportTab


def _preparada():
    fila = FilaCotizacion(
        numero_fila=2,
        producto='Lejía tradicional 1 L',
        categoria='Limpieza',
        precio_unitario=Decimal('5.20'),
        compra_minima=2,
        stock_disponible=25,
        descuento_desde=5,
        descuento_porcentaje=Decimal('0.10'),
        entrega_dias=3,
        codigo='LIM-001',
        marca='Blanco',
        presentacion='1 L',
    )
    return CotizacionPreparada(
        archivo=ArchivoFuente(
            nombre='LimpiaSur.xlsx',
            hash_archivo='abc',
            tamano_bytes=100,
        ),
        proveedor='LimpiaSur',
        columnas=list(COLUMNS),
        indices={columna: indice for indice, columna in enumerate(COLUMNS)},
        filas=[fila],
        reporte=ReporteValidacion(total_filas=1, correctas=1),
    )


def test_ofertas_exponen_condiciones_reales():
    oferta = _preparada().ofertas[0]

    assert oferta['descuento_desde'] == 5
    assert oferta['descuento_porcentaje'] == Decimal('0.10')
    assert oferta['entrega_dias'] == 3
    assert 'bonus' not in oferta
    assert 'validity' not in oferta


def test_clave_producto_prefiere_codigo_y_hace_fallback_por_nombre():
    clave = SuppliersImportTab._clave_producto

    primera = clave({'code': 'LIM-001', 'product': 'Lejía tradicional 1 L'})
    segunda = clave({'code': 'lim 001', 'product': 'Lejía clásica'})
    sin_codigo = clave({'code': '-', 'product': 'Lejía tradicional 1 L'})
    sin_codigo_acento = clave({'code': '', 'product': 'LEJIA TRADICIONAL 1 L'})

    assert primera == segunda
    assert sin_codigo == sin_codigo_acento
    assert primera != sin_codigo
