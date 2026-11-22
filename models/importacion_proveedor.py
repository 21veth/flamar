"""Estructuras de datos del modulo de importacion de cotizaciones."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path


@dataclass
class ArchivoFuente:
    """Archivo leido (o generado en modo demo) que origina una cotizacion."""

    nombre: str
    hash_archivo: str
    tamano_bytes: int
    ruta: Path | None = None
    hoja: str | None = None
    es_demo: bool = False


@dataclass
class FilaCotizacion:
    """Una oferta valida lista para guardarse en detalle_cotizacion."""

    numero_fila: int
    producto: str
    categoria: str
    precio_unitario: Decimal
    compra_minima: int = 1
    stock_disponible: int = 0
    descuento_desde: int | None = None
    descuento_porcentaje: Decimal = Decimal('0')
    entrega_dias: int = 0
    codigo: str | None = None
    marca: str | None = None
    presentacion: str | None = None
    observacion: str | None = None

    @property
    def clave_producto(self):
        return (self.codigo or '', self.producto, self.marca or '', self.presentacion or '')


@dataclass
class AvisoImportacion:
    """Problema detectado al validar una fila del Excel."""

    numero_fila: int
    campo: str
    valor_original: str
    problema: str
    grave: bool = True


@dataclass
class ReporteValidacion:
    """Conteos y filas detectadas durante la validacion de un archivo."""

    total_filas: int = 0
    correctas: int = 0
    errores: list[AvisoImportacion] = field(default_factory=list)
    advertencias: list[AvisoImportacion] = field(default_factory=list)

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


@dataclass
class CotizacionPreparada:
    """Resultado de leer y validar un archivo, antes de persistirlo."""

    archivo: ArchivoFuente
    proveedor: str
    columnas: list
    indices: dict
    filas: list[FilaCotizacion] = field(default_factory=list)
    avisos: list[AvisoImportacion] = field(default_factory=list)
    reporte: ReporteValidacion = field(default_factory=ReporteValidacion)
    id_importacion: int | None = None
    id_cotizacion: int | None = None

    @property
    def total_filas(self):
        return self.reporte.total_filas or (
            len(self.filas) + sum(1 for aviso in self.avisos if aviso.grave)
        )

    @property
    def total_rechazadas(self):
        return self.reporte.total_errores or sum(
            1 for aviso in self.avisos if aviso.grave
        )

    @property
    def ofertas(self):
        """Filas en el formato que consume la matriz comparativa de la vista."""
        resultado = []
        for fila in self.filas:
            resultado.append({
                'numero_fila': fila.numero_fila,
                'product': fila.producto,
                'category': fila.categoria,
                'code': fila.codigo or '-',
                'marca': fila.marca,
                'presentacion': fila.presentacion,
                'price': fila.precio_unitario,
                'minimum': fila.compra_minima,
                'stock': fila.stock_disponible,
                'descuento_desde': fila.descuento_desde,
                'descuento_porcentaje': fila.descuento_porcentaje,
                'entrega_dias': fila.entrega_dias,
                'observacion': fila.observacion or '',
            })
        return resultado


@dataclass
class ResultadoGuardado:
    id_importacion: int
    id_cotizacion: int
    proveedor: str
    registros_validos: int
    registros_rechazados: int
    ofertas_registradas: int = 0


@dataclass
class ErrorImportacion:
    """Problema leido de public.errores_importacion."""

    id_error: int
    numero_fila: int
    campo: str | None
    valor_original: str | None
    problema: str


@dataclass
class ResultadoImportacion:
    """Estado real de una importacion, leido desde PostgreSQL."""

    id_importacion: int
    nombre_archivo: str
    fecha_importacion: datetime | None
    registros_totales: int
    registros_validos: int
    registros_rechazados: int
    estado: str
    id_cotizacion: int | None = None
    proveedor: str = ''
    ofertas_guardadas: int = 0
    errores: list[ErrorImportacion] = field(default_factory=list)

    @property
    def exitoso(self):
        return self.estado == 'completada'


@dataclass
class OfertaGuardada:
    """Oferta efectivamente almacenada en public.detalle_cotizacion."""

    codigo: str | None
    producto: str
    categoria: str | None
    precio_unitario: Decimal
    stock_disponible: int
    compra_minima: int
    descuento_desde: int | None
    descuento_porcentaje: Decimal
    entrega_dias: int


@dataclass
class ResumenProveedor:
    """Fila del resumen de proveedores importados."""

    proveedor: str
    ofertas: int
    estado: str
    fecha_importacion: datetime | None = None
    id_importacion: int | None = None


@dataclass
class IntentoFallido:
    """Intento fallido registrado de forma independiente al rollback comercial."""

    id_importacion: int | None
    nombre_archivo: str
    proveedor: str
    motivo: str
    registros_totales: int = 0


@dataclass
class FilaVistaPrevia:
    """Fila lista para revisar en la Etapa 3, sin persistencia."""

    archivo: str
    proveedor: str
    numero_fila: int
    codigo: str
    producto: str
    categoria: str
    marca: str
    presentacion: str
    precio: Decimal
    stock: int
    compra_minima: int
    descuento_desde: int | None
    descuento_porcentaje: Decimal
    entrega_dias: int
    estado_producto: str = 'No verificado (BD desactivada)'
    excluida: bool = False


@dataclass
class ResumenVistaPrevia:
    """Totales mostrados en la cabecera de la vista previa."""

    productos: int = 0
    sin_stock: int = 0
    errores: int = 0
    advertencias: int = 0
    excluidos: int = 0
    proveedores: int = 0
    archivos: int = 0


@dataclass
class VistaPreviaImportacion:
    """Datos en memoria que el administrador revisa antes de confirmar."""

    filas: list[FilaVistaPrevia] = field(default_factory=list)
    resumen: ResumenVistaPrevia = field(default_factory=ResumenVistaPrevia)
    reporte: ReporteValidacion = field(default_factory=ReporteValidacion)

    @property
    def es_valido(self):
        return self.reporte.es_valido

    @property
    def es_confirmable(self):
        return self.es_valido and any(not fila.excluida for fila in self.filas)

    @property
    def categorias(self):
        return sorted({fila.categoria for fila in self.filas if fila.categoria})


@dataclass
class ConfirmacionImportacion:
    """Autorizacion local para la Etapa 4; no escribe en PostgreSQL."""

    filas: list[FilaVistaPrevia] = field(default_factory=list)
    excluidas: dict = field(default_factory=dict)
    resumen: ResumenVistaPrevia = field(default_factory=ResumenVistaPrevia)
