"""Validacion de archivos de ingreso de inventario."""

import hashlib
from decimal import Decimal
from pathlib import Path

from models.importacion_inventario import (
    ArchivoIngreso,
    AvisoIngreso,
    ConfirmacionIngreso,
    FilaIngreso,
    FilaVistaPreviaIngreso,
    IngresoGuardado,
    ProductoVistaPreviaIngreso,
    ReporteValidacionIngreso,
    ResumenIngreso,
    ResultadoGuardadoIngreso,
)
from views.import_shared import (
    ImportFileError,
    cell_to_text,
    header_indexes,
    normalize_header,
    parse_date,
    parse_number,
    read_table_file,
)

COLUMNS = (
    'Proveedor',
    'Código producto',
    'Producto',
    'Categoría',
    'Marca',
    'Presentación',
    'Unidad medida',
    'Cantidad ingresada',
    'Stock mínimo',
    'Precio compra (S/)',
    'Precio venta (S/)',
    'Fecha ingreso',
)
REQUIRED = COLUMNS
ALIASES = {
    'Proveedor': ('Distribuidora',),
    'Código producto': ('Codigo producto', 'Código', 'Codigo', 'SKU'),
    'Categoría': ('Categoria',),
    'Presentación': ('Presentacion',),
    'Unidad medida': ('Unidad', 'Unidad de medida'),
    'Cantidad ingresada': ('Cantidad', 'Cantidad ingreso'),
    'Stock mínimo': ('Stock minimo', 'Stock mínimo producto'),
    'Precio compra (S/)': ('Precio compra', 'Costo', 'Precio de compra'),
    'Precio venta (S/)': ('Precio venta', 'Precio de venta'),
    'Fecha ingreso': ('Fecha', 'Fecha de ingreso'),
}

_UNIDADES = (
    ('botella', ('botellas',)),
    ('unidad', ('unidades',)),
    ('bolsa', ('bolsas',)),
    ('paquete', ('paquetes',)),
    ('caja', ('cajas',)),
    ('lata', ('latas',)),
    ('sobre', ('sobres',)),
    ('galón', ('galon', 'galones')),
    ('otro', ('otros', 'otra', 'otras')),
)
UNIDADES_MEDIDA = {}
for _canonical, _variants in _UNIDADES:
    for _value in (_canonical,) + _variants:
        UNIDADES_MEDIDA[normalize_header(_value)] = _canonical


class ContextoValidacionIngreso:
    def __init__(
        self,
        existe_hash=None,
        proveedor_existe=None,
        categoria_existe=None,
        buscar_producto=None,
        obtener_importacion=None,
        existe_hash_actual=None,
    ):
        self.existe_hash = existe_hash or (lambda _hash: False)
        self.existe_hash_actual = existe_hash_actual or self.existe_hash
        self.proveedor_existe = proveedor_existe or (lambda _nombre: True)
        self.categoria_existe = categoria_existe or (lambda _nombre: True)
        self.buscar_producto = buscar_producto or (
            lambda _codigo, _nombre, _marca, _presentacion: None
        )
        self.obtener_importacion = obtener_importacion or (
            lambda **_filtros: None
        )


class PersistenciaValidacionIngreso:
    def crear_intento(self, reporte, estado, id_usuario=None):
        return None

    def registrar_errores(self, id_intento, errores):
        return None

    def guardar(self, confirmacion, id_usuario=None):
        return None

    def registrar_fallo(self, confirmacion, motivo, id_usuario=None):
        return None

    def obtener_ingreso(self, id_ingreso):
        return None

    def listar_ingresos(self, busqueda='', proveedor='', estado='', fecha=''):
        return ()


class ImportacionIngresosService:
    def __init__(self, lector=None, contexto=None, persistencia=None):
        self._lector = lector or read_table_file
        self._contexto = contexto or ContextoValidacionIngreso()
        self._persistencia = persistencia or PersistenciaValidacionIngreso()

    def validar(self, ruta, id_usuario=None):
        ruta = Path(ruta)
        archivo = ArchivoIngreso(
            nombre=ruta.name,
            tamano_bytes=ruta.stat().st_size,
            hash_archivo=self._hash_archivo(ruta),
            ruta=ruta,
        )
        reporte = ReporteValidacionIngreso(archivo=archivo)

        if self._contexto.existe_hash(archivo.hash_archivo):
            reporte.errores.append(self._aviso(
                0,
                'Archivo',
                archivo.nombre,
                'Este archivo ya fue importado anteriormente.',
            ))
            self._persistir(reporte, id_usuario)
            return reporte

        try:
            datos = self._lector(ruta)
        except ImportFileError as exc:
            reporte.errores.append(self._aviso(0, 'Archivo', archivo.nombre, str(exc)))
            self._persistir(reporte, id_usuario)
            return reporte

        archivo.hoja = datos.sheet
        reporte.total_filas = datos.total
        indices = header_indexes(datos.headers, COLUMNS, ALIASES)
        faltantes = [columna for columna, indice in indices.items() if indice is None]
        if faltantes:
            for columna in faltantes:
                reporte.errores.append(self._aviso(
                    0, columna, '', 'Columna requerida no encontrada'
                ))
            self._persistir(reporte, id_usuario)
            return reporte

        self._validar_filas(datos, indices, reporte)
        self._persistir(reporte, id_usuario)
        return reporte

    @staticmethod
    def _hash_archivo(ruta):
        digest = hashlib.sha256()
        with Path(ruta).open('rb') as handle:
            for bloque in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(bloque)
        return digest.hexdigest()

    @staticmethod
    def _aviso(numero_fila, campo, valor, problema, grave=True):
        texto = '' if valor is None else str(valor)
        return AvisoIngreso(numero_fila, campo, texto, problema, grave)

    def _validar_filas(self, datos, indices, reporte):
        proveedor = ''
        proveedor_normalizado = ''

        for numero_fila, fila in enumerate(datos.rows, start=2):
            avisos = []
            valores = {
                columna: self._texto(datos.value(fila, indices[columna]))
                for columna in COLUMNS
            }

            proveedor_fila = valores['Proveedor']
            if not proveedor_fila:
                avisos.append(self._aviso(
                    numero_fila, 'Proveedor', '', 'Valor obligatorio'
                ))
            elif not proveedor_normalizado:
                proveedor = proveedor_fila
                proveedor_normalizado = proveedor_fila.casefold()
                if not self._contexto.proveedor_existe(proveedor):
                    avisos.append(self._aviso(
                        numero_fila,
                        'Proveedor',
                        proveedor,
                        'Proveedor no registrado; se creará al guardar.',
                        False,
                    ))
            elif proveedor_fila.casefold() != proveedor_normalizado:
                avisos.append(self._aviso(
                    numero_fila,
                    'Proveedor',
                    proveedor_fila,
                    f'Proveedor distinto al del archivo: {proveedor}',
                ))

            for columna in (
                'Código producto',
                'Producto',
                'Categoría',
                'Marca',
                'Presentación',
            ):
                if not valores[columna]:
                    avisos.append(self._aviso(
                        numero_fila, columna, '', 'Valor obligatorio'
                    ))

            unidad = self._unidad(valores['Unidad medida'])
            if unidad is None:
                avisos.append(self._aviso(
                    numero_fila,
                    'Unidad medida',
                    valores['Unidad medida'],
                    'Unidad no permitida.',
                ))

            if valores['Categoría'] and not self._contexto.categoria_existe(
                valores['Categoría']
            ):
                avisos.append(self._aviso(
                    numero_fila,
                    'Categoría',
                    valores['Categoría'],
                    'Categoría nueva; se creará al guardar.',
                    False,
                ))

            codigo = valores['Código producto']
            id_producto = None
            estado_producto = 'Nuevo'
            if codigo:
                existente = self._contexto.buscar_producto(
                    codigo,
                    valores['Producto'],
                    valores['Marca'],
                    valores['Presentación'],
                )
                if existente and self._identidad_distinta(existente, valores):
                    detalle = ' · '.join(
                        str(existente.get(campo) or '-')
                        for campo in ('nombre', 'marca', 'presentacion')
                    )
                    avisos.append(self._aviso(
                        numero_fila,
                        'Código producto',
                        codigo,
                        f'El código existe para otro producto: {detalle}',
                    ))
                    id_producto = existente.get('id_producto')
                    estado_producto = 'Existente'
                elif existente is None:
                    avisos.append(self._aviso(
                        numero_fila,
                        'Código producto',
                        codigo,
                        'Producto nuevo; se creará al guardar.',
                        False,
                    ))
                else:
                    id_producto = existente.get('id_producto')
                    estado_producto = 'Existente'

            cantidad = self._entero(valores['Cantidad ingresada'])
            if cantidad is None or cantidad <= 0:
                avisos.append(self._aviso(
                    numero_fila,
                    'Cantidad ingresada',
                    valores['Cantidad ingresada'],
                    'Debe ser un entero mayor que cero.',
                ))

            stock_minimo = self._entero(valores['Stock mínimo'])
            if stock_minimo is None or stock_minimo < 0:
                avisos.append(self._aviso(
                    numero_fila,
                    'Stock mínimo',
                    valores['Stock mínimo'],
                    'Debe ser un entero mayor o igual que cero.',
                ))

            precio_compra = self._decimal(valores['Precio compra (S/)'])
            if precio_compra is None or precio_compra <= 0:
                avisos.append(self._aviso(
                    numero_fila,
                    'Precio compra (S/)',
                    valores['Precio compra (S/)'],
                    'Debe ser un número mayor que cero.',
                ))

            precio_venta = self._decimal(valores['Precio venta (S/)'])
            if precio_venta is None or precio_venta <= 0:
                avisos.append(self._aviso(
                    numero_fila,
                    'Precio venta (S/)',
                    valores['Precio venta (S/)'],
                    'Debe ser un número mayor que cero.',
                ))
            elif precio_compra is not None and precio_venta < precio_compra:
                avisos.append(self._aviso(
                    numero_fila,
                    'Precio venta (S/)',
                    valores['Precio venta (S/)'],
                    'El precio de venta es menor que el precio de compra.',
                    False,
                ))

            fecha = parse_date(valores['Fecha ingreso'])
            if fecha is None:
                avisos.append(self._aviso(
                    numero_fila,
                    'Fecha ingreso',
                    valores['Fecha ingreso'],
                    'Fecha inválida o vacía.',
                ))

            for aviso in avisos:
                if aviso.grave:
                    reporte.errores.append(aviso)
                else:
                    reporte.advertencias.append(aviso)

            if any(aviso.grave for aviso in avisos):
                estado = 'Error'
            elif avisos:
                estado = 'Advertencia'
            else:
                estado = 'Válido'
            reporte.filas_preview.append(FilaVistaPreviaIngreso(
                numero_fila=numero_fila,
                proveedor=valores['Proveedor'],
                codigo=valores['Código producto'],
                producto=valores['Producto'],
                categoria=valores['Categoría'],
                cantidad=valores['Cantidad ingresada'],
                precio_compra=valores['Precio compra (S/)'],
                precio_venta=valores['Precio venta (S/)'],
                fecha_ingreso=valores['Fecha ingreso'],
                estado=estado,
                marca=valores['Marca'],
                presentacion=valores['Presentación'],
                unidad_medida=valores['Unidad medida'],
                stock_minimo=valores['Stock mínimo'],
                estado_producto=estado_producto,
            ))

            if (
                not any(aviso.grave for aviso in avisos)
                and cantidad is not None
                and stock_minimo is not None
                and precio_compra is not None
                and precio_venta is not None
                and fecha is not None
                and unidad is not None
            ):
                reporte.filas_validas.append(FilaIngreso(
                    numero_fila=numero_fila,
                    proveedor=proveedor,
                    codigo=codigo,
                    producto=valores['Producto'],
                    categoria=valores['Categoría'],
                    marca=valores['Marca'],
                    presentacion=valores['Presentación'],
                    unidad_medida=unidad,
                    cantidad=cantidad,
                    stock_minimo=stock_minimo,
                    precio_compra=precio_compra,
                    precio_venta=precio_venta,
                    fecha_ingreso=fecha,
                    id_producto=id_producto,
                    estado_producto=estado_producto,
                ))

        reporte.proveedor = proveedor

    @staticmethod
    def _texto(valor):
        return cell_to_text(valor).strip()

    @staticmethod
    def _entero(valor):
        numero = parse_number(valor)
        if numero is None or float(numero) != int(numero):
            return None
        return int(numero)

    @staticmethod
    def _decimal(valor):
        numero = parse_number(valor)
        if numero is None:
            return None
        return Decimal(str(numero))

    @staticmethod
    def _unidad(valor):
        return UNIDADES_MEDIDA.get(normalize_header(valor))

    @staticmethod
    def _identidad_distinta(existente, valores):
        def normal(valor):
            return normalize_header(str(valor or ''))

        return (
            normal(existente.get('nombre')) != normal(valores['Producto'])
            or normal(existente.get('marca')) != normal(valores['Marca'])
            or normal(existente.get('presentacion')) != normal(valores['Presentación'])
        )

    def _persistir(self, reporte, id_usuario):
        estado = 'con_errores' if reporte.errores else 'validado'
        id_intento = self._persistencia.crear_intento(reporte, estado, id_usuario)
        if id_intento is not None:
            reporte.id_importacion = id_intento
            self._persistencia.registrar_errores(id_intento, reporte.errores)

    @staticmethod
    def construir_resumen(reporte):
        filas = list(getattr(reporte, 'filas_validas', ()))
        fechas = [fila.fecha_ingreso for fila in filas if fila.fecha_ingreso is not None]
        categorias = tuple(sorted({
            fila.categoria for fila in filas if fila.categoria
        }))
        return ResumenIngreso(
            proveedor=getattr(reporte, 'proveedor', '') or '',
            archivo=reporte.archivo.nombre if reporte is not None else '',
            productos=len(filas),
            total_unidades=sum(fila.cantidad for fila in filas),
            fecha_min=min(fechas) if fechas else None,
            fecha_max=max(fechas) if fechas else None,
            categorias=categorias,
        )

    @staticmethod
    def _precio_texto(valor):
        numero = parse_number(valor)
        if numero is None:
            return str(valor or '')
        return f'S/ {numero:.2f}'

    @staticmethod
    def construir_productos_vista_previa(reporte):
        filas = list(getattr(reporte, 'filas_preview', ()))
        if filas:
            productos = []
            for fila in filas:
                productos.append(ProductoVistaPreviaIngreso(
                    numero_fila=fila.numero_fila,
                    codigo=fila.codigo,
                    producto=fila.producto,
                    categoria=fila.categoria,
                    marca=fila.marca,
                    presentacion=fila.presentacion,
                    cantidad=fila.cantidad,
                    precio_compra=ImportacionIngresosService._precio_texto(
                        fila.precio_compra
                    ),
                    precio_venta=ImportacionIngresosService._precio_texto(
                        fila.precio_venta
                    ),
                    fecha_ingreso=fila.fecha_ingreso,
                    unidad_medida=fila.unidad_medida,
                    stock_minimo=fila.stock_minimo,
                    estado_producto=fila.estado_producto,
                    estado=fila.estado,
                ))
            return tuple(productos)

        estados = {}
        for aviso in list(getattr(reporte, 'errores', ())) + list(
            getattr(reporte, 'advertencias', ())
        ):
            if not aviso.numero_fila:
                continue
            texto = 'Error' if aviso.grave else 'Advertencia'
            if aviso.numero_fila not in estados or texto == 'Error':
                estados[aviso.numero_fila] = texto

        productos = []
        for fila in getattr(reporte, 'filas_validas', ()):
            fecha = (
                fila.fecha_ingreso.strftime('%d/%m/%Y')
                if fila.fecha_ingreso is not None else ''
            )
            productos.append(ProductoVistaPreviaIngreso(
                numero_fila=fila.numero_fila,
                codigo=fila.codigo,
                producto=fila.producto,
                categoria=fila.categoria,
                marca=fila.marca,
                presentacion=fila.presentacion,
                cantidad=str(fila.cantidad),
                precio_compra=f'S/ {fila.precio_compra:.2f}',
                precio_venta=f'S/ {fila.precio_venta:.2f}',
                fecha_ingreso=fecha,
                unidad_medida=fila.unidad_medida,
                stock_minimo=str(fila.stock_minimo),
                estado_producto=fila.estado_producto,
                estado=estados.get(fila.numero_fila, 'Válido'),
            ))
        return tuple(productos)

    def _revalidar(self, reporte, id_usuario=None):
        if reporte is None:
            raise ValueError('No hay una validación disponible para confirmar.')
        if not reporte.es_valido:
            raise ValueError('La validación contiene errores bloqueantes.')
        if not reporte.filas_validas:
            raise ValueError('No hay productos válidos para confirmar.')
        if reporte.id_importacion is None:
            raise ValueError('El archivo no tiene un intento de validación registrado.')

        importacion = self._contexto.obtener_importacion(
            id_importacion=reporte.id_importacion,
            hash_archivo=reporte.archivo.hash_archivo,
        )
        if importacion is None:
            raise ValueError('No se encontró la importación validada.')
        if importacion.get('estado') != 'validado':
            raise ValueError('La importación ya no está vigente. Vuelve a validar el archivo.')
        if importacion.get('hash_archivo') != reporte.archivo.hash_archivo:
            raise ValueError('El archivo validado no coincide con el registro actual.')
        if reporte.archivo.ruta is not None and reporte.archivo.ruta.exists():
            hash_actual = self._hash_archivo(reporte.archivo.ruta)
            if hash_actual != reporte.archivo.hash_archivo:
                raise ValueError('El archivo cambió después de la validación. Vuelve a validarlo.')
        if self._contexto.existe_hash_actual(reporte.archivo.hash_archivo):
            raise ValueError('Este archivo ya fue importado anteriormente.')

        return ConfirmacionIngreso(
            id_importacion=reporte.id_importacion,
            hash_archivo=reporte.archivo.hash_archivo,
            proveedor=reporte.proveedor,
            archivo=reporte.archivo.nombre,
            resumen=self.construir_resumen(reporte),
            filas=tuple(reporte.filas_validas),
            id_usuario=id_usuario,
            total_filas=reporte.total_filas,
            registros_rechazados=len(reporte.filas_errores),
        )

    def confirmar(self, reporte, id_usuario=None):
        return self._revalidar(reporte, id_usuario)

    def confirmar_y_guardar(self, reporte, id_usuario=None) -> ResultadoGuardadoIngreso:
        confirmacion = self._revalidar(reporte, id_usuario)
        try:
            resultado = self._persistencia.guardar(confirmacion, id_usuario)
        except Exception as error:
            try:
                self._persistencia.registrar_fallo(confirmacion, str(error), id_usuario)
            except Exception:
                pass
            raise
        if resultado is None:
            raise ValueError('No se pudo registrar el ingreso.')
        return resultado

    def obtener_ingreso(self, id_ingreso) -> IngresoGuardado | None:
        return self._persistencia.obtener_ingreso(id_ingreso)

    def listar_ingresos(self, busqueda='', proveedor='', estado='', fecha=''):
        return self._persistencia.listar_ingresos(
            busqueda=busqueda,
            proveedor=proveedor,
            estado=estado,
            fecha=fecha,
        )
