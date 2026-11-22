from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class OfertaComparacionNueva:
    id_detalle_cotizacion: int
    proveedor: str
    producto: str
    codigo: str = ''
    categoria: str = ''
    precio_evaluado: Decimal = Decimal('0')
    cantidad_requerida: int = 1
    costo_total_linea: Decimal = Decimal('0')
    oferta_valida: bool = True
    seleccionado_combinada: bool = False
    observacion: str = ''


@dataclass
class ComparacionNueva:
    nombre: str
    tipo_productos: str
    id_usuario: int
    id_proveedor_recomendado: int | None = None
    proveedor_recomendado_nombre: str = ''
    estado: str = 'completada'
    costo_proveedor_recomendado: Decimal = Decimal('0')
    costo_compra_combinada: Decimal = Decimal('0')
    costo_referencia: Decimal = Decimal('0')
    ahorro_estimado: Decimal = Decimal('0')
    justificacion: str = ''
    detalles: list[OfertaComparacionNueva] = field(default_factory=list)


@dataclass
class ComparacionGuardada:
    id_comparacion: int
    nombre: str
    fecha_creacion: datetime | None = None
    estado: str = ''
    tipo_productos: str = ''
    proveedor_recomendado: str = ''
    costo_proveedor_recomendado: Decimal = Decimal('0')
    costo_compra_combinada: Decimal = Decimal('0')
    costo_referencia: Decimal = Decimal('0')
    ahorro_estimado: Decimal = Decimal('0')
    justificacion: str = ''
    proveedores: str = ''
    productos: int = 0


@dataclass
class DetalleComparacionGuardado:
    id_detalle_comparacion: int
    proveedor: str
    producto: str
    codigo: str = ''
    categoria: str = ''
    precio_evaluado: Decimal = Decimal('0')
    cantidad_requerida: int = 1
    costo_total_linea: Decimal = Decimal('0')
    oferta_valida: bool = True
    seleccionado_combinada: bool = False
    observacion: str = ''


@dataclass
class DetalleComparacion:
    comparacion: ComparacionGuardada
    filas: list[DetalleComparacionGuardado] = field(default_factory=list)


__all__ = [
    'ComparacionGuardada',
    'ComparacionNueva',
    'DetalleComparacion',
    'DetalleComparacionGuardado',
    'OfertaComparacionNueva',
]
