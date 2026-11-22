"""Acceso a importaciones, errores, cotizaciones y detalle de cotizacion."""

from config.database import obtener_conexion


class ImportacionRepository:
    """Persiste el ciclo completo de una cotizacion importada."""

    def existe_hash(self, hash_archivo, cursor=None):
        consulta = (
            'SELECT 1 FROM public.importaciones '
            "WHERE hash_archivo = %s AND estado = 'completada' LIMIT 1"
        )
        parametros = (hash_archivo,)
        if cursor is not None:
            cursor.execute(consulta, parametros)
            return cursor.fetchone() is not None

        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor_local:
                cursor_local.execute(consulta, parametros)
                return cursor_local.fetchone() is not None

    def crear_importacion(
        self, id_usuario, nombre_archivo, hash_archivo, total_filas, cursor,
        estado='pendiente',
    ):
        consulta = (
            'INSERT INTO public.importaciones '
            '(id_usuario, nombre_archivo, hash_archivo, registros_totales, '
            ' registros_validos, registros_rechazados, estado) '
            'VALUES (%s, %s, %s, %s, 0, 0, %s) RETURNING id_importacion'
        )
        cursor.execute(consulta, (
            id_usuario, nombre_archivo, hash_archivo, total_filas, estado,
        ))
        return cursor.fetchone()[0]

    def registrar_errores(self, id_importacion, avisos, cursor):
        if not avisos:
            return
        consulta = (
            'INSERT INTO public.errores_importacion '
            '(id_importacion, numero_fila, campo, valor_original, problema) '
            'VALUES (%s, %s, %s, %s, %s)'
        )
        datos = [
            (id_importacion, max(1, aviso.numero_fila), aviso.campo[:100],
             str(aviso.valor_original)[:500], aviso.problema)
            for aviso in avisos if aviso.grave
        ]
        if datos:
            cursor.executemany(consulta, datos)

    def crear_cotizacion(self, id_proveedor, id_importacion, cursor):
        consulta = (
            'INSERT INTO public.cotizaciones '
            '(id_proveedor, id_importacion, estado) VALUES (%s, %s, %s) '
            'ON CONFLICT (id_importacion) DO UPDATE '
            'SET id_proveedor = EXCLUDED.id_proveedor, estado = EXCLUDED.estado '
            'RETURNING id_cotizacion'
        )
        cursor.execute(consulta, (id_proveedor, id_importacion, 'vigente'))
        return cursor.fetchone()[0]

    def guardar_detalle(self, id_cotizacion, id_producto, fila, cursor):
        consulta = (
            'INSERT INTO public.detalle_cotizacion '
            '(id_cotizacion, id_producto, precio_unitario, stock_disponible, '
            ' compra_minima, descuento_desde, descuento_porcentaje, entrega_dias) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s) '
            'ON CONFLICT (id_cotizacion, id_producto) DO UPDATE SET '
            'precio_unitario = EXCLUDED.precio_unitario, '
            'stock_disponible = EXCLUDED.stock_disponible, '
            'compra_minima = EXCLUDED.compra_minima, '
            'descuento_desde = EXCLUDED.descuento_desde, '
            'descuento_porcentaje = EXCLUDED.descuento_porcentaje, '
            'entrega_dias = EXCLUDED.entrega_dias'
        )
        desde = fila.descuento_desde
        if desde is not None and desde <= 0:
            desde = None
        cursor.execute(consulta, (
            id_cotizacion,
            id_producto,
            fila.precio_unitario,
            fila.stock_disponible,
            fila.compra_minima,
            desde,
            fila.descuento_porcentaje,
            fila.entrega_dias,
        ))

    def confirmar_importacion(self, id_importacion, validos, rechazados, cursor, estado='completada'):
        consulta = (
            'UPDATE public.importaciones '
            'SET estado = %s, registros_validos = %s, registros_rechazados = %s '
            'WHERE id_importacion = %s'
        )
        cursor.execute(consulta, (estado, validos, rechazados, id_importacion))

    def obtener_estado(self, id_importacion):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    'SELECT estado FROM public.importaciones WHERE id_importacion = %s',
                    (id_importacion,),
                )
                fila = cursor.fetchone()
                return fila[0] if fila else None

    def descartar_importacion(self, id_importacion):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    'SELECT estado FROM public.importaciones WHERE id_importacion = %s',
                    (id_importacion,),
                )
                fila = cursor.fetchone()
                if fila is None or fila[0] != 'pendiente':
                    return False
                cursor.execute(
                    'DELETE FROM public.detalle_cotizacion WHERE id_cotizacion IN '
                    '(SELECT id_cotizacion FROM public.cotizaciones WHERE id_importacion = %s)',
                    (id_importacion,),
                )
                cursor.execute(
                    'DELETE FROM public.cotizaciones WHERE id_importacion = %s',
                    (id_importacion,),
                )
                cursor.execute(
                    'DELETE FROM public.errores_importacion WHERE id_importacion = %s',
                    (id_importacion,),
                )
                cursor.execute(
                    'DELETE FROM public.importaciones WHERE id_importacion = %s',
                    (id_importacion,),
                )
            return True
