"""Adaptadores PostgreSQL para la validacion de ingresos de inventario."""

from config.database import obtener_conexion
from models.importacion_inventario import AvisoIngreso, ResultadoGuardadoIngreso
from repositories.catalogo_repository import CatalogoRepository
from repositories.importacion_repository import ImportacionRepository
from repositories.ingreso_inventario_repository import IngresoInventarioRepository
from repositories.proveedor_repository import ProveedorRepository
from services.importacion_inventarios_service import (
    ContextoValidacionIngreso,
    PersistenciaValidacionIngreso,
)


class ContextoPostgresIngresos(ContextoValidacionIngreso):
    def __init__(
        self,
        importaciones=None,
        catalogo=None,
        proveedores=None,
        conexion_factory=None,
    ):
        self._importaciones = importaciones or ImportacionRepository()
        self._catalogo = catalogo or CatalogoRepository()
        self._proveedores = proveedores or ProveedorRepository()
        self._conexion_factory = conexion_factory or obtener_conexion
        self._conexion = None
        self._cursor = None
        self._hashes = {}
        self._hashes_actuales = {}
        self._productos = {}
        self._categorias = {}
        self._proveedores_cache = {}

    def __enter__(self):
        self.cerrar()
        self.invalidar_cache()
        return self

    def invalidar_cache(self):
        self._hashes = {}
        self._hashes_actuales = {}
        self._productos = {}
        self._categorias = {}
        self._proveedores_cache = {}

    def __exit__(self, *argumentos):
        self.cerrar()
        return False

    def cerrar(self):
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None
        if self._conexion is not None:
            self._conexion.close()
            self._conexion = None

    def _obtener_cursor(self):
        if self._cursor is None:
            self._conexion = self._conexion_factory()
            self._cursor = self._conexion.cursor()
        return self._cursor

    def existe_hash(self, hash_archivo):
        clave = str(hash_archivo or '')
        if clave not in self._hashes:
            self._hashes[clave] = self._importaciones.existe_hash(
                hash_archivo, self._obtener_cursor()
            )
        return self._hashes[clave]

    def obtener_importacion(self, id_importacion=None, hash_archivo=None):
        return self._importaciones.obtener_importacion(
            id_importacion=id_importacion,
            hash_archivo=hash_archivo,
            cursor=self._obtener_cursor(),
        )

    def existe_hash_actual(self, hash_archivo):
        clave = str(hash_archivo or '')
        if clave not in self._hashes_actuales:
            self._hashes_actuales[clave] = self._importaciones.existe_hash(
                hash_archivo, self._obtener_cursor()
            )
        return self._hashes_actuales[clave]

    def proveedor_existe(self, nombre):
        clave = str(nombre or '').strip()
        if clave not in self._proveedores_cache:
            self._proveedores_cache[clave] = self._proveedores.proveedor_existe(
                nombre, self._obtener_cursor()
            )
        return self._proveedores_cache[clave]

    def categoria_existe(self, nombre):
        clave = str(nombre or '').strip()
        if clave not in self._categorias:
            self._categorias[clave] = self._catalogo.categoria_existe(
                nombre, self._obtener_cursor()
            )
        return self._categorias[clave]

    def buscar_producto(self, codigo, nombre, marca, presentacion):
        clave = (
            str(codigo or ''),
            str(nombre or ''),
            str(marca or ''),
            str(presentacion or ''),
        )
        if clave not in self._productos:
            self._productos[clave] = self._catalogo.buscar_producto(
                codigo, nombre, marca, presentacion, self._obtener_cursor()
            )
        return self._productos[clave]


class PersistenciaPostgresIngresos(PersistenciaValidacionIngreso):
    def __init__(
        self, importaciones=None, catalogo=None, proveedores=None, ingresos=None,
        conexion_factory=None, contexto=None,
    ):
        super().__init__()
        self._importaciones = importaciones or ImportacionRepository()
        self._catalogo = catalogo or CatalogoRepository()
        self._proveedores = proveedores or ProveedorRepository()
        self._ingresos = ingresos or IngresoInventarioRepository()
        self._conexion_factory = conexion_factory or obtener_conexion
        self._contexto = contexto

    def crear_intento(self, reporte, estado, id_usuario=None):
        if id_usuario is None:
            return None
        conexion = self._conexion_factory()
        try:
            with conexion.cursor() as cursor:
                id_intento = self._importaciones.crear_importacion(
                    id_usuario,
                    reporte.archivo.nombre,
                    reporte.archivo.hash_archivo,
                    reporte.total_filas,
                    cursor,
                    estado,
                )
                cursor.execute(
                    'UPDATE public.importaciones '
                    'SET registros_validos = %s, registros_rechazados = %s '
                    'WHERE id_importacion = %s',
                    (reporte.correctas, len(reporte.filas_errores), id_intento),
                )
            conexion.commit()
            return id_intento
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def registrar_errores(self, id_intento, errores):
        if id_intento is None or not errores:
            return
        conexion = self._conexion_factory()
        try:
            with conexion.cursor() as cursor:
                self._importaciones.registrar_errores(id_intento, errores, cursor)
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    @staticmethod
    def _mismo_producto(fila, existente):
        esperado = str(fila.producto or '').strip().casefold()
        encontrado = str(existente.get('nombre') or '').strip().casefold()
        if esperado and encontrado and esperado != encontrado:
            return False
        for campo in ('marca', 'presentacion'):
            valor_fila = str(getattr(fila, campo) or '').strip().casefold()
            valor_existente = str(existente.get(campo) or '').strip().casefold()
            if valor_fila and valor_existente and valor_fila != valor_existente:
                return False
        return True

    def guardar(self, confirmacion, id_usuario=None) -> ResultadoGuardadoIngreso:
        usuario = confirmacion.id_usuario if id_usuario is None else id_usuario
        if usuario is None:
            raise ValueError('Se requiere un usuario para registrar el ingreso.')
        conexion = self._conexion_factory()
        try:
            with conexion.cursor() as cursor:
                importacion = self._importaciones.obtener_importacion(
                    id_importacion=confirmacion.id_importacion,
                    hash_archivo=confirmacion.hash_archivo,
                    cursor=cursor,
                    bloquear=True,
                )
                if importacion is None:
                    raise ValueError('No se encontró la importación validada.')
                if importacion.get('estado') != 'validado':
                    raise ValueError('La importación ya no está vigente. Vuelve a validar el archivo.')
                if importacion.get('hash_archivo') != confirmacion.hash_archivo:
                    raise ValueError('El archivo validado no coincide con el registro actual.')
                if self._importaciones.existe_hash(confirmacion.hash_archivo, cursor):
                    raise ValueError('Este archivo ya fue importado anteriormente.')

                id_proveedor = self._proveedores.asegurar_proveedor(
                    confirmacion.proveedor, cursor
                )
                filas_resueltas = []
                cache = {}
                for fila in confirmacion.filas:
                    codigo = str(fila.codigo or '').strip()
                    id_producto = cache.get(codigo) if codigo else None
                    if id_producto is None:
                        existente = self._catalogo.buscar_producto(
                            fila.codigo, fila.producto, fila.marca, fila.presentacion, cursor
                        )
                        if existente is not None:
                            if not self._mismo_producto(fila, existente):
                                raise ValueError(
                                    f'El código {fila.codigo} pertenece a otro producto.'
                                )
                            id_producto = existente['id_producto']
                            self._catalogo.actualizar_producto_ingreso(
                                id_producto,
                                fila.unidad_medida,
                                fila.stock_minimo,
                                fila.precio_venta,
                                fila.fecha_ingreso,
                                cursor,
                            )
                        else:
                            id_categoria = self._catalogo.asegurar_categoria(
                                fila.categoria, cursor
                            )
                            id_producto = self._catalogo.crear_producto(
                                fila.codigo,
                                fila.producto,
                                id_categoria,
                                fila.marca,
                                fila.presentacion,
                                cursor,
                                unidad_medida=fila.unidad_medida,
                                stock_minimo=fila.stock_minimo,
                                precio_venta=fila.precio_venta,
                                fecha_precio=fila.fecha_ingreso,
                                fecha_stock=fila.fecha_ingreso,
                            )
                        if codigo:
                            cache[codigo] = id_producto
                    filas_resueltas.append((fila, id_producto))

                fecha_ingreso = confirmacion.resumen.fecha_min or min(
                    fila.fecha_ingreso for fila in confirmacion.filas
                )
                id_ingreso = self._ingresos.crear_ingreso(
                    confirmacion.id_importacion,
                    id_proveedor,
                    fecha_ingreso,
                    len(confirmacion.filas),
                    sum(fila.cantidad for fila in confirmacion.filas),
                    cursor,
                    observacion=f'Ingreso desde {confirmacion.archivo}',
                )
                self._ingresos.guardar_detalle(id_ingreso, filas_resueltas, cursor)
                self._importaciones.confirmar_importacion(
                    confirmacion.id_importacion,
                    len(confirmacion.filas),
                    confirmacion.registros_rechazados,
                    cursor,
                )
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()
        if self._contexto is not None and hasattr(self._contexto, 'invalidar_cache'):
            self._contexto.invalidar_cache()
        return ResultadoGuardadoIngreso(
            id_ingreso=id_ingreso,
            id_importacion=confirmacion.id_importacion,
            proveedor=confirmacion.proveedor,
            archivo=confirmacion.archivo,
            fecha_ingreso=fecha_ingreso,
            productos=len(confirmacion.filas),
            unidades=sum(fila.cantidad for fila in confirmacion.filas),
            incidencias=confirmacion.registros_rechazados,
        )

    def registrar_fallo(self, confirmacion, motivo, id_usuario=None):
        if confirmacion is None or confirmacion.id_importacion is None:
            return
        conexion = self._conexion_factory()
        try:
            with conexion.cursor() as cursor:
                self._importaciones.confirmar_importacion(
                    confirmacion.id_importacion, 0, 0, cursor, estado='fallida'
                )
                self._importaciones.registrar_errores(
                    confirmacion.id_importacion,
                    [AvisoIngreso(1, 'importacion', confirmacion.archivo, motivo)],
                    cursor,
                )
            conexion.commit()
        except Exception:
            conexion.rollback()
        finally:
            conexion.close()

    def obtener_ingreso(self, id_ingreso):
        if id_ingreso is None:
            return None
        return self._ingresos.obtener_ingreso(id_ingreso)
