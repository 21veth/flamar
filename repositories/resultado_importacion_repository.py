"""Consultas de solo lectura para la Etapa 5 de importacion de proveedores."""

from config.database import obtener_conexion
from models.importacion_proveedor import (
    ErrorImportacion,
    OfertaGuardada,
    ResumenProveedor,
    ResultadoImportacion,
)


class ResultadoImportacionRepository:
    """Recupera el resultado confirmado desde PostgreSQL."""

    def _consultar(self, consulta, parametros=(), cursor=None):
        if cursor is not None:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as propio:
                propio.execute(consulta, parametros)
                return propio.fetchall()
        finally:
            conexion.close()

    def obtener_resultado(self, id_importacion, cursor=None):
        filas = self._consultar(
            '''
            SELECT i.id_importacion, i.nombre_archivo, i.fecha_importacion,
                   i.registros_totales, i.registros_validos, i.registros_rechazados,
                   i.estado, c.id_cotizacion, p.nombre,
                   COUNT(DISTINCT d.id_detalle_cotizacion),
                   COUNT(DISTINCT e.id_error)
            FROM public.importaciones i
            LEFT JOIN public.cotizaciones c ON c.id_importacion = i.id_importacion
            LEFT JOIN public.proveedores p ON p.id_proveedor = c.id_proveedor
            LEFT JOIN public.detalle_cotizacion d ON d.id_cotizacion = c.id_cotizacion
            LEFT JOIN public.errores_importacion e ON e.id_importacion = i.id_importacion
            WHERE i.id_importacion = %s
            GROUP BY i.id_importacion, c.id_cotizacion, p.nombre
            ''',
            (id_importacion,),
            cursor,
        )
        if not filas:
            return None
        fila = filas[0]
        return ResultadoImportacion(
            id_importacion=fila[0],
            nombre_archivo=fila[1],
            fecha_importacion=fila[2],
            registros_totales=fila[3],
            registros_validos=fila[4],
            registros_rechazados=fila[5],
            estado=fila[6],
            id_cotizacion=fila[7],
            proveedor=fila[8] or '',
            ofertas_guardadas=fila[9],
        )

    def obtener_errores(self, id_importacion, cursor=None):
        filas = self._consultar(
            '''
            SELECT id_error, numero_fila, campo, valor_original, problema
            FROM public.errores_importacion
            WHERE id_importacion = %s
            ORDER BY numero_fila, id_error
            ''',
            (id_importacion,),
            cursor,
        )
        return [
            ErrorImportacion(
                id_error=fila[0],
                numero_fila=fila[1],
                campo=fila[2],
                valor_original=fila[3],
                problema=fila[4],
            )
            for fila in filas
        ]

    def obtener_ofertas(self, id_importacion, cursor=None):
        filas = self._consultar(
            '''
            SELECT p.codigo, p.nombre, cat.nombre, d.precio_unitario,
                   d.stock_disponible, d.compra_minima, d.descuento_desde,
                   d.descuento_porcentaje, d.entrega_dias
            FROM public.detalle_cotizacion d
            JOIN public.cotizaciones c ON c.id_cotizacion = d.id_cotizacion
            JOIN public.productos p ON p.id_producto = d.id_producto
            LEFT JOIN public.categorias cat ON cat.id_categoria = p.id_categoria
            WHERE c.id_importacion = %s
            ORDER BY p.codigo NULLS LAST, p.nombre
            ''',
            (id_importacion,),
            cursor,
        )
        return [
            OfertaGuardada(
                codigo=fila[0],
                producto=fila[1],
                categoria=fila[2],
                precio_unitario=fila[3],
                stock_disponible=fila[4],
                compra_minima=fila[5],
                descuento_desde=fila[6],
                descuento_porcentaje=fila[7],
                entrega_dias=fila[8],
            )
            for fila in filas
        ]

    def obtener_resumen_proveedores(self, cursor=None):
        filas = self._consultar(
            '''
            SELECT p.nombre, i.estado, COUNT(d.id_detalle_cotizacion),
                   i.fecha_importacion, i.id_importacion
            FROM public.importaciones i
            JOIN public.cotizaciones c ON c.id_importacion = i.id_importacion
            JOIN public.proveedores p ON p.id_proveedor = c.id_proveedor
            LEFT JOIN public.detalle_cotizacion d ON d.id_cotizacion = c.id_cotizacion
            WHERE i.estado = %s
            GROUP BY i.id_importacion, p.nombre, i.estado, i.fecha_importacion
            ORDER BY i.fecha_importacion DESC, p.nombre
            ''',
            ('completada',),
            cursor,
        )
        return [
            ResumenProveedor(
                proveedor=fila[0],
                estado=fila[1],
                ofertas=fila[2],
                fecha_importacion=fila[3],
                id_importacion=fila[4],
            )
            for fila in filas
        ]


__all__ = ['ResultadoImportacionRepository']
