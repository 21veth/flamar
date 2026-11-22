"""Adaptadores PostgreSQL para el registro de cotizaciones importadas."""

from config.database import obtener_conexion
from models.importacion_proveedor import (
    AvisoImportacion,
    IntentoFallido,
    ResultadoGuardado,
)
from repositories.catalogo_repository import CatalogoRepository
from repositories.importacion_repository import ImportacionRepository
from repositories.proveedor_repository import ProveedorRepository
from services.importacion_proveedores_service import ContextoValidacion, PersistenciaValidacion


class ContextoPostgres(ContextoValidacion):
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
        self._productos = {}
        self._categorias = {}
        self._proveedores_cache = {}

    def __enter__(self):
        self.cerrar()
        self._hashes = {}
        self._productos = {}
        self._categorias = {}
        self._proveedores_cache = {}
        return self

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

    def buscar_producto(self, codigo):
        clave = str(codigo or '')
        if clave not in self._productos:
            self._productos[clave] = self._catalogo.buscar_producto(
                codigo, None, None, None, self._obtener_cursor()
            )
        return self._productos[clave]

    def categoria_existe(self, nombre):
        clave = str(nombre or '').strip()
        if clave not in self._categorias:
            self._categorias[clave] = self._catalogo.categoria_existe(
                nombre, self._obtener_cursor()
            )
        return self._categorias[clave]

    def proveedor_existe(self, nombre):
        clave = str(nombre or '').strip()
        if clave not in self._proveedores_cache:
            self._proveedores_cache[clave] = self._proveedores.proveedor_existe(
                nombre, self._obtener_cursor()
            )
        return self._proveedores_cache[clave]


class PersistenciaPostgres(PersistenciaValidacion):
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

    def crear_intento(self, preparada, id_usuario, estado):
        return None

    def registrar_errores(self, id_intento, errores):
        return None

    def actualizar_estado(self, id_intento, estado):
        return None

    def registrar_fallo(self, preparadas, motivo, id_usuario=None):
        if id_usuario is None or not preparadas:
            return None
        intentos = []
        conexion = self._conexion_factory()
        try:
            with conexion.cursor() as cursor:
                for preparada in preparadas:
                    nombre_archivo = preparada.archivo.nombre
                    totales = preparada.total_filas
                    id_importacion = self._importaciones.crear_importacion(
                        id_usuario,
                        nombre_archivo,
                        preparada.archivo.hash_archivo,
                        totales,
                        cursor,
                        estado='fallida',
                    )
                    avisos = list(preparada.reporte.errores)
                    avisos.append(AvisoImportacion(
                        numero_fila=1,
                        campo='importacion',
                        valor_original=nombre_archivo,
                        problema=motivo,
                        grave=True,
                    ))
                    self._importaciones.registrar_errores(
                        id_importacion, avisos, cursor
                    )
                    intentos.append(IntentoFallido(
                        id_importacion=id_importacion,
                        nombre_archivo=nombre_archivo,
                        proveedor=preparada.proveedor,
                        motivo=motivo,
                        registros_totales=totales,
                    ))
            conexion.commit()
        except Exception:
            conexion.rollback()
            return None
        finally:
            conexion.close()
        return intentos

    def descartar(self, id_intento):
        if id_intento is None:
            return False
        return self._importaciones.descartar_importacion(id_intento)

    def guardar(self, preparadas, excluidas=None, id_usuario=None):
        if id_usuario is None:
            raise ValueError('Se requiere un usuario para guardar la importación.')
        filas_excluidas = self._normalizar_excluidas(excluidas)
        resultados = []
        conexion = self._conexion_factory()
        try:
            with conexion.cursor() as cursor:
                cache_productos = {}
                for preparada in preparadas:
                    resultados.append(
                        self._guardar_uno(
                            preparada,
                            filas_excluidas,
                            id_usuario,
                            cursor,
                            cache_productos,
                        )
                    )
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()
        return resultados

    @staticmethod
    def _normalizar_excluidas(excluidas):
        normalizadas = {}
        for clave, filas in (excluidas or {}).items():
            if isinstance(filas, (int, str)):
                filas = [filas]
            numeros = set()
            for fila in (filas or []):
                try:
                    numeros.add(int(fila))
                except (TypeError, ValueError):
                    continue
            normalizadas[str(clave)] = numeros
        return normalizadas

    def _guardar_uno(
        self, preparada, excluidas, id_usuario, cursor, cache_productos
    ):
        nombre_archivo = preparada.archivo.nombre
        claves = {nombre_archivo}
        if preparada.id_importacion is not None:
            claves.add(str(preparada.id_importacion))
        numeros_excluidos = set()
        for clave in claves:
            numeros_excluidos.update(excluidas.get(clave, set()))

        if self._importaciones.existe_hash(preparada.archivo.hash_archivo, cursor):
            raise ValueError(f'El archivo {nombre_archivo} ya fue importado.')

        rechazos = {
            aviso.numero_fila for aviso in preparada.reporte.errores
        } | numeros_excluidos
        validas = [
            fila for fila in preparada.filas if fila.numero_fila not in rechazos
        ]
        totales = max(preparada.total_filas, len(validas) + len(rechazos))
        rechazadas = totales - len(validas)

        id_importacion = self._importaciones.crear_importacion(
            id_usuario,
            nombre_archivo,
            preparada.archivo.hash_archivo,
            totales,
            cursor,
        )
        preparada.id_importacion = id_importacion
        self._importaciones.registrar_errores(
            id_importacion, preparada.reporte.errores, cursor
        )

        id_proveedor = self._proveedores.asegurar_proveedor(
            preparada.proveedor, cursor
        )
        id_cotizacion = self._importaciones.crear_cotizacion(
            id_proveedor, id_importacion, cursor
        )
        preparada.id_cotizacion = id_cotizacion

        ofertas = 0
        for fila in validas:
            id_producto = self._id_producto(fila, cache_productos, cursor)
            self._importaciones.guardar_detalle(
                id_cotizacion, id_producto, fila, cursor
            )
            ofertas += 1

        self._importaciones.confirmar_importacion(
            id_importacion, len(validas), rechazadas, cursor
        )
        return ResultadoGuardado(
            id_importacion=id_importacion,
            id_cotizacion=id_cotizacion,
            proveedor=preparada.proveedor,
            registros_validos=len(validas),
            registros_rechazados=rechazadas,
            ofertas_registradas=ofertas,
        )

    def _id_producto(self, fila, cache, cursor):
        codigo = str(fila.codigo or '').strip()
        if codigo and codigo in cache:
            return cache[codigo]
        encontrado = self._catalogo.buscar_producto(
            fila.codigo, fila.producto, fila.marca, fila.presentacion, cursor
        )
        if encontrado is not None:
            id_producto = encontrado['id_producto']
        else:
            id_categoria = self._catalogo.asegurar_categoria(fila.categoria, cursor)
            id_producto = self._catalogo.crear_producto(
                fila.codigo,
                fila.producto,
                id_categoria,
                fila.marca,
                fila.presentacion,
                cursor,
            )
        if codigo:
            cache[codigo] = id_producto
        return id_producto


__all__ = ['ContextoPostgres', 'PersistenciaPostgres']
