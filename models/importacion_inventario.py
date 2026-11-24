"""Estructuras de datos de la importacion de ingresos de inventario."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


@dataclass
class ArchivoIngreso:
    nombre: str
    tamano_bytes: int
    hash_archivo: str
    hoja: str | None = None
    ruta: Path | None = None


@dataclass(frozen=True)
class FilaIngreso:
    numero_fila: int
    proveedor: str
    codigo: str
    producto: str
    categoria: str
    marca: str
    presentacion: str
    unidad_medida: str
    cantidad: int
    stock_minimo: int
    precio_compra: Decimal
    precio_venta: Decimal
    fecha_ingreso: date
    id_producto: int | None = None
    estado_producto: str = 'Nuevo'


@dataclass(frozen=True)
class FilaVistaPreviaIngreso:
    numero_fila: int
    proveedor: str
    codigo: str
    producto: str
    categoria: str
    cantidad: str
    precio_compra: str
    precio_venta: str
    fecha_ingreso: str
    estado: str = 'Válido'
    marca: str = ''
    presentacion: str = ''
    unidad_medida: str = ''
    stock_minimo: str = ''
    estado_producto: str = 'Nuevo'


@dataclass(frozen=True)
class AvisoIngreso:
    numero_fila: int
    campo: str
    valor_original: str
    problema: str
    grave: bool = True


@dataclass
class ReporteValidacionIngreso:
    archivo: ArchivoIngreso
    proveedor: str = ''
    total_filas: int = 0
    filas_validas: list[FilaIngreso] = field(default_factory=list)
    filas_preview: list[FilaVistaPreviaIngreso] = field(default_factory=list)
    errores: list[AvisoIngreso] = field(default_factory=list)
    advertencias: list[AvisoIngreso] = field(default_factory=list)
    id_importacion: int | None = None

    @property
    def correctas(self):
        return len(self.filas_validas)

    @property
    def total_errores(self):
        return len(self.errores)

    @property
    def total_advertencias(self):
        return len(self.advertencias)

    @property
    def filas_errores(self):
        return sorted({aviso.numero_fila for aviso in self.errores})

    @property
    def es_valido(self):
        return not self.errores


@dataclass(frozen=True)
class ResumenIngreso:
    proveedor: str
    archivo: str
    productos: int
    total_unidades: int
    fecha_min: date | None
    fecha_max: date | None
    categorias: tuple[str, ...] = ()

    @property
    def fecha_rango(self):
        if self.fecha_min is None or self.fecha_max is None:
            return '-'
        if self.fecha_min == self.fecha_max:
            return self.fecha_min.strftime('%d/%m/%Y')
        inicio = self.fecha_min.strftime('%d/%m/%Y')
        fin = self.fecha_max.strftime('%d/%m/%Y')
        return f'{inicio} - {fin}'


@dataclass(frozen=True)
class ProductoVistaPreviaIngreso:
    codigo: str
    producto: str
    categoria: str
    marca: str
    presentacion: str
    cantidad: int
    precio_compra: str
    precio_venta: str
    fecha_ingreso: str
    unidad_medida: str
    stock_minimo: int | str
    estado_producto: str
    estado: str = 'Válido'
    numero_fila: int = 0


@dataclass(frozen=True)
class ConfirmacionIngreso:
    id_importacion: int
    hash_archivo: str
    proveedor: str
    archivo: str
    resumen: ResumenIngreso
    filas: tuple[FilaIngreso, ...]
    id_usuario: int | None = None
    total_filas: int = 0
    registros_rechazados: int = 0


@dataclass(frozen=True)
class IngresoDetalleGuardado:
    numero_fila: int
    codigo: str
    producto: str
    categoria: str
    cantidad: int
    stock_minimo: int
    precio_compra: Decimal
    precio_venta: Decimal
    unidad_medida: str
    fecha_ingreso: date


@dataclass(frozen=True)
class IngresoGuardado:
    id_ingreso: int
    id_importacion: int
    proveedor: str
    archivo: str
    fecha_ingreso: date
    numero_productos: int
    total_unidades: int
    creado_en: datetime | None
    filas: tuple[IngresoDetalleGuardado, ...] = ()


@dataclass(frozen=True)
class ResultadoGuardadoIngreso:
    id_ingreso: int
    id_importacion: int
    proveedor: str
    archivo: str
    fecha_ingreso: date
    productos: int
    unidades: int
    incidencias: int
    estado: str = 'Completado'
