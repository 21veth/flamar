"""Lectura, validacion y persistencia diferida de cotizaciones de proveedores."""

import hashlib
from decimal import Decimal
from pathlib import Path

from models.importacion_proveedor import (
    ArchivoFuente,
    AvisoImportacion,
    ConfirmacionImportacion,
    CotizacionPreparada,
    FilaCotizacion,
    IntentoFallido,
    FilaVistaPrevia,
    ReporteValidacion,
    ResumenVistaPrevia,
    VistaPreviaImportacion,
)
from views.import_shared import (
    ImportFileError,
    header_indexes,
    normalize_header,
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
    'Precio unitario (S/)',
    'Stock disponible',
    'Compra mínima',
    'Descuento desde (unid.)',
    'Descuento (%)',
    'Entrega (días)',
)

COLUMNS_REQUERIDAS = COLUMNS

ALIASES = {
    'Código producto': ('Código', 'Codigo producto', 'Cod producto'),
    'Precio unitario (S/)': ('Precio unitario', 'Precio', 'Precio oferta'),
    'Stock disponible': ('Stock', 'Existencias'),
    'Compra mínima': ('Cantidad mínima', 'Cantidad minima', 'Minimo'),
    'Descuento desde (unid.)': ('Descuento desde', 'Descuento desde cantidad'),
    'Descuento (%)': ('Descuento porcentaje', 'Descuento %', 'Descuento'),
    'Entrega (días)': ('Días de entrega', 'Dias de entrega', 'Entrega dias'),
}


class ArchivoDuplicadoError(Exception):
    """El hash del archivo ya fue validado anteriormente."""


def combinar_reportes(preparadas):
    """Une los reportes de todos los Excel en un unico resumen."""
    return ReporteValidacion(
        total_filas=sum(item.reporte.total_filas for item in preparadas),
        correctas=sum(item.reporte.correctas for item in preparadas),
        errores=[
            aviso for item in preparadas for aviso in item.reporte.errores
        ],
        advertencias=[
            aviso for item in preparadas for aviso in item.reporte.advertencias
        ],
    )


def construir_vista_previa(preparadas, excluidas=None):
    """Proyecta las filas validadas para revision; no consulta PostgreSQL."""
    excluidas = excluidas or {}
    filas = []
    proveedores = []
    for preparada in preparadas:
        nombre = preparada.archivo.nombre
        if preparada.proveedor not in proveedores:
            proveedores.append(preparada.proveedor)
        saltos = set(excluidas.get(nombre, ()))
        for fila in preparada.filas:
            filas.append(FilaVistaPrevia(
                archivo=nombre,
                proveedor=preparada.proveedor,
                numero_fila=fila.numero_fila,
                codigo=fila.codigo or '-',
                producto=fila.producto,
                categoria=fila.categoria,
                marca=fila.marca or '-',
                presentacion=fila.presentacion or '-',
                precio=fila.precio_unitario,
                stock=fila.stock_disponible,
                compra_minima=fila.compra_minima,
                descuento_desde=fila.descuento_desde,
                descuento_porcentaje=fila.descuento_porcentaje,
                entrega_dias=fila.entrega_dias,
                excluida=fila.numero_fila in saltos,
            ))
    reporte = combinar_reportes(preparadas)
    resumen = ResumenVistaPrevia(
        productos=sum(1 for fila in filas if not fila.excluida),
        sin_stock=sum(
            1 for fila in filas if not fila.excluida and fila.stock == 0
        ),
        errores=reporte.total_errores,
        advertencias=reporte.total_advertencias,
        excluidos=sum(1 for fila in filas if fila.excluida),
        proveedores=len(proveedores),
        archivos=len(preparadas),
    )
    return VistaPreviaImportacion(filas=filas, resumen=resumen, reporte=reporte)


def filtrar_filas_vista_previa(
    filas, texto='', categoria='Todas las categorías', disponibilidad='Todas'
):
    """Aplica busqueda por nombre/codigo y filtros de categoria o stock."""
    needle = str(texto or '').strip().casefold()
    resultado = []
    for fila in filas:
        if needle and needle not in f'{fila.codigo} {fila.producto}'.casefold():
            continue
        if (
            categoria not in ('Todas', 'Todas las categorías')
            and fila.categoria != categoria
        ):
            continue
        if disponibilidad == 'Con stock' and fila.stock <= 0:
            continue
        if disponibilidad == 'Sin stock' and fila.stock > 0:
            continue
        resultado.append(fila)
    return resultado


def preparar_confirmacion(vista, excluidas=None):
    """Congela en memoria la autorizacion; Etapa 4 hara el guardado real."""
    return ConfirmacionImportacion(
        filas=[fila for fila in vista.filas if not fila.excluida],
        excluidas=dict(excluidas or {}),
        resumen=vista.resumen,
    )


class ContextoValidacion:
    """Consultas opcionales de solo lectura; sin conexion por defecto."""

    def __enter__(self):
        return self

    def __exit__(self, *argumentos):
        return False

    def existe_hash(self, hash_archivo):
        return False

    def buscar_producto(self, codigo):
        return None

    def categoria_existe(self, nombre):
        return True

    def proveedor_existe(self, nombre):
        return True


class PersistenciaValidacion:
    """Escritura diferida del intento; sin conexion por defecto."""

    def crear_intento(self, preparada, id_usuario, estado):
        return None

    def registrar_errores(self, id_intento, errores):
        return None

    def actualizar_estado(self, id_intento, estado):
        return None

    def guardar(self, preparadas, excluidas=None, id_usuario=None):
        return []

    def registrar_fallo(self, preparadas, motivo, id_usuario=None):
        return []

    def descartar(self, id_intento):
        return False


class ImportacionProveedoresService:
    """Lee y valida cotizaciones sin usar PostgreSQL hasta que se inyecte."""

    def __init__(
        self, lector=read_table_file, contexto=None, persistencia=None,
        resultados=None,
    ):
        self._lector = lector
        self._contexto = contexto
        self._persistencia = persistencia
        self._resultados = resultados
        self._ultimo_fallo = None

    @staticmethod
    def _hash_archivo(ruta):
        digest = hashlib.sha256()
        with Path(ruta).open('rb') as origen:
            for bloque in iter(lambda: origen.read(1024 * 1024), b''):
                digest.update(bloque)
        return digest.hexdigest()

    def preparar(self, rutas, id_usuario=None):
        contexto = self._contexto
        if contexto is None or not hasattr(contexto, '__enter__'):
            return self._preparar_archivos(rutas, id_usuario)
        with contexto:
            return self._preparar_archivos(rutas, id_usuario)

    def _preparar_archivos(self, rutas, id_usuario=None):
        resultados = []
        for ruta in rutas:
            ruta = Path(ruta)
            hash_archivo = self._hash_archivo(ruta)
            if self._contexto is not None and self._contexto.existe_hash(hash_archivo):
                raise ArchivoDuplicadoError(
                    f'El archivo {ruta.name} ya fue validado anteriormente.'
                )
            try:
                datos = self._lector(ruta)
            except ImportFileError:
                raise
            indices, avisos = self._validar_estructura(datos, ruta)
            filas = []
            proveedor = ruta.stem
            if not any(aviso.grave for aviso in avisos):
                filas, avisos_contenido, proveedor = self._validar_contenido(
                    datos, indices
                )
                avisos.extend(avisos_contenido)
            archivo = ArchivoFuente(
                nombre=datos.name,
                hash_archivo=hash_archivo,
                tamano_bytes=datos.size_bytes,
                ruta=ruta,
                hoja=datos.sheet,
            )
            resultados.append(CotizacionPreparada(
                archivo=archivo,
                proveedor=proveedor,
                columnas=datos.headers,
                indices=indices,
                filas=filas,
                avisos=avisos,
                reporte=self._reporte(datos, filas, avisos),
            ))
        self._validar_proveedores_unicos(resultados)
        if id_usuario is not None:
            self.registrar_validacion(resultados, id_usuario)
        return resultados

    def _validar_proveedores_unicos(self, resultados):
        """Un mismo proveedor no puede ocupar dos archivos de la comparacion."""
        if len(resultados) < 2:
            return
        agrupados = {}
        for resultado in resultados:
            nombre = str(resultado.proveedor).strip()
            if nombre:
                agrupados.setdefault(nombre, []).append(resultado)
        for nombre, grupo in agrupados.items():
            if len(grupo) < 2:
                continue
            archivos = ', '.join(item.archivo.nombre for item in grupo)
            for resultado in grupo:
                resultado.avisos.append(AvisoImportacion(
                    1, 'Proveedor', nombre,
                    f'El proveedor "{nombre}" aparece en varios archivos ({archivos}); '
                    'use un Excel por proveedor.',
                    True,
                ))
                resultado.reporte = self._construir_reporte(
                    resultado.reporte.total_filas, resultado.filas, resultado.avisos
                )

    def _validar_estructura(self, datos, ruta):
        avisos = []
        if (
            ruta.suffix.lower() in ('.xlsx', '.xls')
            and normalize_header(datos.sheet) != 'catalogo'
        ):
            avisos.append(AvisoImportacion(
                1, 'Hoja', str(datos.sheet), 'La hoja debe llamarse "Catalogo".', True
            ))
        if not datos.headers or not any(str(header).strip() for header in datos.headers):
            avisos.append(AvisoImportacion(
                1, 'Encabezados', '', 'El archivo no tiene encabezados.', True
            ))
            return {}, avisos
        indices = header_indexes(datos.headers, COLUMNS, ALIASES)
        for columna in COLUMNS:
            indice = indices.get(columna)
            if indice is None:
                avisos.append(AvisoImportacion(
                    1, columna, '', f'Falta el encabezado "{columna}".', True
                ))
                continue
            actual = str(datos.headers[indice]).strip()
            if normalize_header(actual) != normalize_header(columna):
                avisos.append(AvisoImportacion(
                    1,
                    columna,
                    actual,
                    f'Encabezado alterno interpretado como "{columna}".',
                    False,
                ))
        if not datos.rows:
            avisos.append(AvisoImportacion(
                1, 'Registros', '', 'El archivo no contiene productos.', True
            ))
        return indices, avisos

    def _validar_contenido(self, datos, indices):
        avisos = []
        filas = []
        proveedores = []
        filas_sin_proveedor = []
        for position, fila in enumerate(datos.rows):
            valor = str(datos.value(fila, indices['Proveedor'])).strip()
            if valor:
                if valor not in proveedores:
                    proveedores.append(valor)
            else:
                filas_sin_proveedor.append(position + 2)
        if filas_sin_proveedor:
            lista = ', '.join(str(numero) for numero in filas_sin_proveedor[:5])
            avisos.append(AvisoImportacion(
                filas_sin_proveedor[0], 'Proveedor', '',
                f'Falta proveedor en filas {lista}.', True,
            ))
        if not proveedores:
            avisos.append(AvisoImportacion(
                1, 'Proveedor', '', 'Debe indicar un proveedor.', True
            ))
        elif len(proveedores) > 1:
            avisos.append(AvisoImportacion(
                1, 'Proveedor', ', '.join(proveedores[:3]),
                'El archivo contiene varios proveedores; debe haber uno solo.', True,
            ))
        proveedor = proveedores[0] if proveedores else ''
        if (
            self._contexto is not None
            and proveedor
            and not self._contexto.proveedor_existe(proveedor)
        ):
            avisos.append(AvisoImportacion(
                1, 'Proveedor', proveedor,
                'El proveedor aun no esta registrado; se creara al confirmar.', False,
            ))

        vistos = set()
        for position, fila in enumerate(datos.rows):
            numero_fila = position + 2

            codigo = self._texto(
                datos, fila, indices, 'Código producto', numero_fila,
                avisos, obligatorio=True,
            )
            if codigo is None:
                continue
            if codigo in vistos:
                avisos.append(AvisoImportacion(
                    numero_fila, 'Código producto', codigo,
                    'Código duplicado dentro del mismo archivo.', True,
                ))
                continue
            vistos.add(codigo)

            producto = self._texto(
                datos, fila, indices, 'Producto', numero_fila,
                avisos, obligatorio=True,
            )
            if producto is None:
                continue
            categoria = self._texto(
                datos, fila, indices, 'Categoría', numero_fila,
                avisos, obligatorio=True,
            )
            if categoria is None:
                continue
            marca = self._texto(
                datos, fila, indices, 'Marca', numero_fila, avisos,
                obligatorio=False,
            )
            presentacion = self._texto(
                datos, fila, indices, 'Presentación', numero_fila, avisos,
                obligatorio=False,
            )

            precio_texto = str(datos.value(fila, indices['Precio unitario (S/)'])).strip()
            precio = parse_number(precio_texto)
            if precio is None or precio <= 0:
                avisos.append(AvisoImportacion(
                    numero_fila, 'Precio unitario (S/)', precio_texto,
                    'Debe ser un número mayor que 0.', True,
                ))
                continue

            stock = self._entero(
                datos, fila, indices, 'Stock disponible', numero_fila, avisos,
                minimo=0, defecto=None, obligatorio=True,
            )
            if stock is None:
                continue
            minima = self._entero(
                datos, fila, indices, 'Compra mínima', numero_fila, avisos,
                minimo=1, defecto=None, obligatorio=True,
            )
            if minima is None:
                continue
            desde = self._entero(
                datos, fila, indices, 'Descuento desde (unid.)', numero_fila, avisos,
                minimo=0, defecto=None, obligatorio=False, silencioso=True,
            )
            entrega = self._entero(
                datos, fila, indices, 'Entrega (días)', numero_fila, avisos,
                minimo=0, defecto=None, obligatorio=True,
            )
            descuento = self._porcentaje(
                datos.value(fila, indices['Descuento (%)']), numero_fila, avisos
            )
            if descuento is None:
                continue

            if desde is not None and desde > 0 and descuento == 0:
                avisos.append(AvisoImportacion(
                    numero_fila, 'Descuento desde (unid.)', str(desde),
                    'Hay cantidad para descuento pero el porcentaje es 0.', False,
                ))
            if descuento > 0 and desde is None:
                avisos.append(AvisoImportacion(
                    numero_fila, 'Descuento (%)', str(descuento),
                    'Hay descuento sin cantidad desde; se aplica desde la unidad 1.', False,
                ))
            if stock > 0 and minima > stock:
                avisos.append(AvisoImportacion(
                    numero_fila, 'Compra mínima', str(minima),
                    f'La compra mínima supera el stock disponible ({stock}).', False,
                ))

            if self._contexto is not None:
                encontrado = self._contexto.buscar_producto(codigo)
                if encontrado and self._identidad_distinta(
                    encontrado, producto, marca, presentacion
                ):
                    avisos.append(AvisoImportacion(
                        numero_fila, 'Código producto', codigo,
                        'El código existe en PostgreSQL con otro producto, marca o presentación.',
                        True,
                    ))
                    continue
                if not self._contexto.categoria_existe(categoria):
                    avisos.append(AvisoImportacion(
                        numero_fila, 'Categoría', categoria,
                        'La categoría aun no existe; se creara al confirmar.', False,
                    ))

            filas.append(FilaCotizacion(
                numero_fila=numero_fila,
                producto=producto,
                categoria=categoria,
                precio_unitario=Decimal(str(precio)),
                compra_minima=minima,
                stock_disponible=stock,
                descuento_desde=desde,
                descuento_porcentaje=descuento,
                entrega_dias=entrega,
                codigo=codigo,
                marca=marca,
                presentacion=presentacion,
            ))
        return filas, avisos, proveedor

    @staticmethod
    def _texto(datos, fila, indices, columna, numero_fila, avisos, obligatorio):
        valor = str(datos.value(fila, indices[columna])).strip()
        if valor:
            return valor
        avisos.append(AvisoImportacion(
            numero_fila, columna, '',
            f'Falta {columna.lower()}.' if obligatorio
            else 'Texto vacío; se deja sin valor.',
            obligatorio,
        ))
        return None

    @staticmethod
    def _entero(
        datos, fila, indices, columna, numero_fila, avisos,
        minimo, defecto, obligatorio, silencioso=False,
    ):
        valor = str(datos.value(fila, indices[columna])).strip()
        if not valor:
            if obligatorio:
                avisos.append(AvisoImportacion(
                    numero_fila, columna, '', f'Falta {columna.lower()}.', True
                ))
                return None
            if defecto is not None and not silencioso:
                avisos.append(AvisoImportacion(
                    numero_fila, columna, '', f'Valor vacío; se usa {defecto}.', False
                ))
            return defecto
        try:
            numero = int(round(float(valor)))
        except (TypeError, ValueError, OverflowError):
            avisos.append(AvisoImportacion(
                numero_fila, columna, valor, 'Debe ser un entero.', True
            ))
            return None
        if numero < minimo:
            avisos.append(AvisoImportacion(
                numero_fila, columna, valor, f'Debe ser mayor o igual a {minimo}.', True
            ))
            return None
        return numero

    @staticmethod
    def _porcentaje(valor, numero_fila, avisos):
        texto = str(valor).strip()
        if not texto:
            avisos.append(AvisoImportacion(
                numero_fila, 'Descuento (%)', '', 'Descuento vacío; se usa 0.', False
            ))
            return Decimal('0')
        numero = parse_number(texto)
        if numero is None:
            avisos.append(AvisoImportacion(
                numero_fila, 'Descuento (%)', texto, 'No es un número válido.', True
            ))
            return None
        descuento = Decimal(str(numero))
        if descuento < 0 or descuento > 1:
            detalle = (
                'Use 0.05 para 5%.' if descuento > 1
                else 'No puede ser negativo.'
            )
            avisos.append(AvisoImportacion(
                numero_fila, 'Descuento (%)', texto,
                f'Debe estar entre 0 y 1. {detalle}', True,
            ))
            return None
        return descuento

    @staticmethod
    def _identidad_distinta(encontrado, producto, marca, presentacion):
        def igual(a, b):
            return str(a or '').strip().casefold() == str(b or '').strip().casefold()

        return not (
            igual(encontrado.get('nombre'), producto)
            and igual(encontrado.get('marca'), marca)
            and igual(encontrado.get('presentacion'), presentacion)
        )

    @staticmethod
    def _reporte(datos, filas, avisos):
        return ImportacionProveedoresService._construir_reporte(
            len(datos.rows), filas, avisos
        )

    @staticmethod
    def _construir_reporte(total_filas, filas, avisos):
        return ReporteValidacion(
            total_filas=total_filas,
            correctas=len(filas),
            errores=[aviso for aviso in avisos if aviso.grave],
            advertencias=[aviso for aviso in avisos if not aviso.grave],
        )

    def preparar_demo(self, grupos):
        resultados = []
        for grupo in grupos:
            filas = []
            for numero, producto in enumerate(grupo['productos'], start=2):
                filas.append(FilaCotizacion(
                    numero_fila=numero,
                    producto=producto['name'],
                    categoria=producto.get('category') or 'General',
                    precio_unitario=Decimal(str(producto['price'])),
                    compra_minima=max(1, int(producto.get('minimum') or 1)),
                    stock_disponible=max(0, int(producto.get('stock') or 0)),
                    entrega_dias=0,
                    codigo=producto.get('code'),
                    observacion=(
                        f"Bonificación: {producto.get('bonus', 0)}; "
                        f"Vigencia: {producto.get('validity', '')}"
                    ),
                ))
            archivo = ArchivoFuente(
                nombre=grupo['archivo'],
                hash_archivo=hashlib.sha256(
                    f"{grupo['proveedor']}|{grupo['archivo']}|{len(filas)}".encode('utf-8')
                ).hexdigest(),
                tamano_bytes=0,
                hoja='Catalogo',
                es_demo=True,
            )
            resultados.append(CotizacionPreparada(
                archivo=archivo,
                proveedor=grupo['proveedor'],
                columnas=list(COLUMNS),
                indices={},
                filas=filas,
                reporte=ReporteValidacion(
                    total_filas=len(filas), correctas=len(filas)
                ),
            ))
        return resultados

    def registrar_validacion(self, preparadas, id_usuario=None):
        if self._persistencia is None:
            return preparadas
        for preparada in preparadas:
            if preparada.id_importacion is not None:
                continue
            estado = 'con_errores' if preparada.reporte.total_errores else 'validado'
            id_intento = self._persistencia.crear_intento(
                preparada, id_usuario, estado
            )
            preparada.id_importacion = id_intento
            self._persistencia.registrar_errores(
                id_intento, preparada.reporte.errores
            )
        return preparadas

    @property
    def ultimo_fallo(self):
        return self._ultimo_fallo

    def confirmar(self, preparadas, excluidas=None, id_usuario=None):
        self._ultimo_fallo = None
        if self._persistencia is None:
            return []
        try:
            return self._persistencia.guardar(preparadas, excluidas, id_usuario)
        except Exception as error:
            motivo = str(error) or error.__class__.__name__
            self._ultimo_fallo = self.registrar_fallo(
                preparadas, motivo, id_usuario
            )
            if self._ultimo_fallo is None:
                self._ultimo_fallo = [
                    IntentoFallido(
                        id_importacion=None,
                        nombre_archivo=preparada.archivo.nombre,
                        proveedor=preparada.proveedor,
                        motivo=motivo,
                        registros_totales=preparada.total_filas,
                    )
                    for preparada in preparadas
                ]
            raise

    def registrar_fallo(self, preparadas, motivo, id_usuario=None):
        if self._persistencia is None:
            return []
        return self._persistencia.registrar_fallo(
            preparadas, motivo, id_usuario
        )

    def consultar_resultado(self, ids_importacion):
        if self._resultados is None:
            return []
        resultados = []
        for id_importacion in ids_importacion or []:
            resultado = self._resultados.obtener_resultado(id_importacion)
            if resultado is None:
                continue
            resultado.errores = self._resultados.obtener_errores(id_importacion)
            resultados.append(resultado)
        return resultados

    def consultar_ofertas(self, id_importacion):
        if self._resultados is None or id_importacion is None:
            return []
        return self._resultados.obtener_ofertas(id_importacion)

    def consultar_resumen(self):
        if self._resultados is None:
            return []
        return self._resultados.obtener_resumen_proveedores()

    def descartar(self, id_importacion):
        if self._persistencia is None or id_importacion is None:
            return False
        return self._persistencia.descartar(id_importacion)


__all__ = [
    'ALIASES',
    'COLUMNS',
    'COLUMNS_REQUERIDAS',
    'ArchivoDuplicadoError',
    'ContextoValidacion',
    'ImportacionProveedoresService',
    'PersistenciaValidacion',
    'combinar_reportes',
    'construir_vista_previa',
    'filtrar_filas_vista_previa',
    'preparar_confirmacion',
]
