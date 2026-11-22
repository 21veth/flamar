from decimal import Decimal

from config.database import obtener_conexion
from models.comparacion import (
    ComparacionGuardada,
    DetalleComparacion,
    DetalleComparacionGuardado,
)


def _decimal(valor):
    if valor is None:
        return Decimal('0')
    return Decimal(str(valor))


class ComparacionRepository:
    def _consultar(self, consulta, parametros=()):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, parametros)
                return cursor.fetchall()
        finally:
            conexion.close()

    def obtener_id_proveedor(self, nombre):
        filas = self._consultar(
            'SELECT id_proveedor FROM public.proveedores WHERE nombre = %s LIMIT 1',
            (nombre,),
        )
        return filas[0][0] if filas else None

    def obtener_ofertas_guardadas(self, ids_importacion):
        if not ids_importacion:
            return []
        filas = self._consultar(
            '''
            SELECT dc.id_detalle_cotizacion, p.nombre, pr.codigo, pr.nombre,
                   COALESCE(cat.nombre, ''), dc.precio_unitario,
                   dc.compra_minima, dc.stock_disponible,
                   dc.descuento_desde, dc.descuento_porcentaje, dc.entrega_dias
            FROM public.detalle_cotizacion dc
            JOIN public.cotizaciones c ON c.id_cotizacion = dc.id_cotizacion
            JOIN public.importaciones i ON i.id_importacion = c.id_importacion
            JOIN public.proveedores p ON p.id_proveedor = c.id_proveedor
            JOIN public.productos pr ON pr.id_producto = dc.id_producto
            LEFT JOIN public.categorias cat ON cat.id_categoria = pr.id_categoria
            WHERE i.id_importacion = ANY(%s)
            ORDER BY pr.codigo NULLS LAST, pr.nombre, p.nombre
            ''',
            (list(ids_importacion),),
        )
        return [
            {
                'id_detalle_cotizacion': fila[0],
                'proveedor': fila[1],
                'codigo': fila[2] or '',
                'producto': fila[3],
                'categoria': fila[4] or '',
                'precio_unitario': _decimal(fila[5]),
                'compra_minima': fila[6],
                'stock_disponible': fila[7],
                'descuento_desde': fila[8],
                'descuento_porcentaje': _decimal(fila[9]),
                'entrega_dias': fila[10],
            }
            for fila in filas
        ]

    def obtener_importaciones_sin_comparacion(self, id_usuario):
        if id_usuario is None:
            return []
        filas = self._consultar(
            '''
            SELECT i.id_importacion
            FROM public.importaciones i
            WHERE i.estado = 'completada'
              AND i.id_usuario = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM public.cotizaciones co
                  JOIN public.detalle_cotizacion dco
                    ON dco.id_cotizacion = co.id_cotizacion
                  JOIN public.detalle_comparacion dc
                    ON dc.id_detalle_cotizacion = dco.id_detalle_cotizacion
                  JOIN public.comparaciones c
                    ON c.id_comparacion = dc.id_comparacion
                  WHERE co.id_importacion = i.id_importacion
                    AND c.id_usuario = i.id_usuario
              )
            ORDER BY i.id_importacion
            ''',
            (id_usuario,),
        )
        return [fila[0] for fila in filas]

    def guardar(self, comparacion):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO public.comparaciones (
                        nombre, tipo_productos, id_usuario, estado,
                        id_proveedor_recomendado, proveedor_recomendado_nombre,
                        costo_proveedor_recomendado, costo_compra_combinada,
                        costo_referencia, ahorro_estimado, justificacion
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id_comparacion
                    ''',
                    (
                        comparacion.nombre,
                        comparacion.tipo_productos or None,
                        comparacion.id_usuario,
                        comparacion.estado,
                        comparacion.id_proveedor_recomendado,
                        comparacion.proveedor_recomendado_nombre or None,
                        comparacion.costo_proveedor_recomendado,
                        comparacion.costo_compra_combinada,
                        comparacion.costo_referencia,
                        comparacion.ahorro_estimado,
                        comparacion.justificacion or None,
                    ),
                )
                id_comparacion = cursor.fetchone()[0]
                for detalle in comparacion.detalles:
                    cursor.execute(
                        '''
                        INSERT INTO public.detalle_comparacion (
                            id_comparacion, id_detalle_cotizacion,
                            cantidad_requerida, precio_evaluado,
                            costo_total_linea, oferta_valida,
                            seleccionado_combinada, observacion,
                            proveedor_nombre, producto_codigo,
                            producto_nombre, categoria_nombre
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''',
                        (
                            id_comparacion,
                            detalle.id_detalle_cotizacion,
                            max(1, int(detalle.cantidad_requerida or 1)),
                            detalle.precio_evaluado,
                            detalle.costo_total_linea,
                            detalle.oferta_valida,
                            detalle.seleccionado_combinada,
                            detalle.observacion or None,
                            detalle.proveedor or None,
                            detalle.codigo or None,
                            detalle.producto or None,
                            detalle.categoria or None,
                        ),
                    )
            conexion.commit()
            return id_comparacion
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def listar(self, id_usuario, busqueda='', categoria='', proveedor='', estado=''):
        patron = f'%{busqueda.strip()}%'
        filas = self._consultar(
            '''
            SELECT c.id_comparacion, c.nombre, c.fecha_creacion, c.estado,
                   COALESCE(c.tipo_productos, ''),
                   COALESCE(c.proveedor_recomendado_nombre, pr.nombre, ''),
                   c.costo_proveedor_recomendado, c.costo_compra_combinada,
                   c.costo_referencia, c.ahorro_estimado,
                   COALESCE(c.justificacion, ''),
                   COALESCE(string_agg(DISTINCT COALESCE(dc.proveedor_nombre, p.nombre), ' · '), ''),
                   COUNT(DISTINCT COALESCE(dc.producto_codigo, prd.codigo, dc.producto_nombre, prd.nombre))
            FROM public.comparaciones c
            LEFT JOIN public.proveedores pr
                ON pr.id_proveedor = c.id_proveedor_recomendado
            LEFT JOIN public.detalle_comparacion dc
                ON dc.id_comparacion = c.id_comparacion
            LEFT JOIN public.detalle_cotizacion dco
                ON dco.id_detalle_cotizacion = dc.id_detalle_cotizacion
            LEFT JOIN public.cotizaciones co
                ON co.id_cotizacion = dco.id_cotizacion
            LEFT JOIN public.proveedores p
                ON p.id_proveedor = co.id_proveedor
            LEFT JOIN public.productos prd
                ON prd.id_producto = dco.id_producto
            WHERE c.id_usuario = %s
              AND (c.nombre ILIKE %s
                   OR COALESCE(c.tipo_productos, '') ILIKE %s
                   OR to_char(c.fecha_creacion, 'DD/MM/YYYY') ILIKE %s
                   OR COALESCE(c.proveedor_recomendado_nombre, pr.nombre, '') ILIKE %s)
              AND (%s = '' OR COALESCE(c.tipo_productos, '') = %s)
              AND (%s = '' OR COALESCE(c.proveedor_recomendado_nombre, pr.nombre, '') = %s)
              AND (%s = '' OR c.estado = %s)
            GROUP BY c.id_comparacion, pr.nombre
            ORDER BY c.fecha_creacion DESC, c.id_comparacion DESC
            ''',
            (
                id_usuario,
                patron,
                patron,
                patron,
                patron,
                categoria or '',
                categoria or '',
                proveedor or '',
                proveedor or '',
                estado or '',
                estado or '',
            ),
        )
        return [
            ComparacionGuardada(
                id_comparacion=fila[0],
                nombre=fila[1],
                fecha_creacion=fila[2],
                estado=fila[3],
                tipo_productos=fila[4],
                proveedor_recomendado=fila[5],
                costo_proveedor_recomendado=_decimal(fila[6]),
                costo_compra_combinada=_decimal(fila[7]),
                costo_referencia=_decimal(fila[8]),
                ahorro_estimado=_decimal(fila[9]),
                justificacion=fila[10],
                proveedores=fila[11],
                productos=fila[12],
            )
            for fila in filas
        ]

    def obtener_detalle(self, id_comparacion, id_usuario=None):
        filas = self._consultar(
            '''
            SELECT c.id_comparacion, c.nombre, c.fecha_creacion, c.estado,
                   COALESCE(c.tipo_productos, ''),
                   COALESCE(c.proveedor_recomendado_nombre, pr.nombre, ''),
                   c.costo_proveedor_recomendado, c.costo_compra_combinada,
                   c.costo_referencia, c.ahorro_estimado,
                   COALESCE(c.justificacion, '')
            FROM public.comparaciones c
            LEFT JOIN public.proveedores pr
                ON pr.id_proveedor = c.id_proveedor_recomendado
            WHERE c.id_comparacion = %s
              AND (%s = 0 OR c.id_usuario = %s)
            LIMIT 1
            ''',
            (id_comparacion, id_usuario or 0, id_usuario or 0),
        )
        if not filas:
            return None
        fila = filas[0]
        comparacion = ComparacionGuardada(
            id_comparacion=fila[0],
            nombre=fila[1],
            fecha_creacion=fila[2],
            estado=fila[3],
            tipo_productos=fila[4],
            proveedor_recomendado=fila[5],
            costo_proveedor_recomendado=_decimal(fila[6]),
            costo_compra_combinada=_decimal(fila[7]),
            costo_referencia=_decimal(fila[8]),
            ahorro_estimado=_decimal(fila[9]),
            justificacion=fila[10],
        )
        detalles = self._consultar(
            '''
            SELECT dc.id_detalle_comparacion,
                   COALESCE(dc.proveedor_nombre, p.nombre, ''),
                   COALESCE(dc.producto_nombre, prod.nombre, ''),
                   COALESCE(dc.producto_codigo, prod.codigo, ''),
                   COALESCE(dc.categoria_nombre, cat.nombre, ''),
                   dc.precio_evaluado, dc.cantidad_requerida,
                   dc.costo_total_linea, dc.oferta_valida,
                   dc.seleccionado_combinada, COALESCE(dc.observacion, '')
            FROM public.detalle_comparacion dc
            JOIN public.detalle_cotizacion dco
                ON dco.id_detalle_cotizacion = dc.id_detalle_cotizacion
            JOIN public.cotizaciones co
                ON co.id_cotizacion = dco.id_cotizacion
            LEFT JOIN public.proveedores p
                ON p.id_proveedor = co.id_proveedor
            LEFT JOIN public.productos prod
                ON prod.id_producto = dco.id_producto
            LEFT JOIN public.categorias cat
                ON cat.id_categoria = prod.id_categoria
            WHERE dc.id_comparacion = %s
            ORDER BY 4, 3, 2
            ''',
            (id_comparacion,),
        )
        filas_detalle = [
            DetalleComparacionGuardado(
                id_detalle_comparacion=detalle[0],
                proveedor=detalle[1],
                producto=detalle[2],
                codigo=detalle[3],
                categoria=detalle[4],
                precio_evaluado=_decimal(detalle[5]),
                cantidad_requerida=detalle[6],
                costo_total_linea=_decimal(detalle[7]),
                oferta_valida=bool(detalle[8]),
                seleccionado_combinada=bool(detalle[9]),
                observacion=detalle[10],
            )
            for detalle in detalles
        ]
        return DetalleComparacion(comparacion=comparacion, filas=filas_detalle)

    def actualizar(self, id_comparacion, id_usuario, nombre, tipo_productos, justificacion):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    '''
                    UPDATE public.comparaciones
                    SET nombre = %s, tipo_productos = %s, justificacion = %s
                    WHERE id_comparacion = %s AND id_usuario = %s
                    ''',
                    (
                        nombre,
                        tipo_productos or None,
                        justificacion or None,
                        id_comparacion,
                        id_usuario,
                    ),
                )
                actualizadas = cursor.rowcount
            conexion.commit()
            return actualizadas
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def eliminar(self, id_comparacion, id_usuario):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    '''
                    SELECT DISTINCT imp.id_importacion
                    FROM public.comparaciones comp
                    JOIN public.detalle_comparacion dcomp
                        ON dcomp.id_comparacion = comp.id_comparacion
                    JOIN public.detalle_cotizacion dcot
                        ON dcot.id_detalle_cotizacion = dcomp.id_detalle_cotizacion
                    JOIN public.cotizaciones cot
                        ON cot.id_cotizacion = dcot.id_cotizacion
                    JOIN public.importaciones imp
                        ON imp.id_importacion = cot.id_importacion
                    WHERE comp.id_comparacion = %s
                      AND comp.id_usuario = %s
                      AND imp.id_usuario = %s
                    ''',
                    (id_comparacion, id_usuario, id_usuario),
                )
                ids_importacion = [fila[0] for fila in cursor.fetchall()]

                if not ids_importacion:
                    cursor.execute(
                        '''
                        DELETE FROM public.detalle_comparacion
                        WHERE id_comparacion IN (
                            SELECT id_comparacion FROM public.comparaciones
                            WHERE id_comparacion = %s AND id_usuario = %s
                        )
                        ''',
                        (id_comparacion, id_usuario),
                    )
                    cursor.execute(
                        '''
                        DELETE FROM public.comparaciones
                        WHERE id_comparacion = %s AND id_usuario = %s
                        ''',
                        (id_comparacion, id_usuario),
                    )
                    eliminadas = cursor.rowcount
                else:
                    cursor.execute(
                        '''
                        SELECT DISTINCT dcomp.id_comparacion
                        FROM public.detalle_comparacion dcomp
                        JOIN public.detalle_cotizacion dcot
                            ON dcot.id_detalle_cotizacion = dcomp.id_detalle_cotizacion
                        JOIN public.cotizaciones cot
                            ON cot.id_cotizacion = dcot.id_cotizacion
                        WHERE cot.id_importacion = ANY(%s)
                        ''',
                        (ids_importacion,),
                    )
                    ids_comparacion = [fila[0] for fila in cursor.fetchall()]

                    cursor.execute(
                        '''
                        SELECT DISTINCT cot.id_proveedor
                        FROM public.cotizaciones cot
                        WHERE cot.id_importacion = ANY(%s)
                        ''',
                        (ids_importacion,),
                    )
                    ids_proveedor = [fila[0] for fila in cursor.fetchall()]

                    cursor.execute(
                        '''
                        DELETE FROM public.detalle_comparacion
                        WHERE id_comparacion = ANY(%s)
                        ''',
                        (ids_comparacion,),
                    )
                    cursor.execute(
                        '''
                        DELETE FROM public.comparaciones
                        WHERE id_comparacion = ANY(%s)
                        ''',
                        (ids_comparacion,),
                    )
                    eliminadas = cursor.rowcount
                    cursor.execute(
                        '''
                        DELETE FROM public.errores_importacion
                        WHERE id_importacion = ANY(%s)
                        ''',
                        (ids_importacion,),
                    )
                    cursor.execute(
                        '''
                        DELETE FROM public.detalle_cotizacion
                        WHERE id_cotizacion IN (
                            SELECT id_cotizacion FROM public.cotizaciones
                            WHERE id_importacion = ANY(%s)
                        )
                        ''',
                        (ids_importacion,),
                    )
                    cursor.execute(
                        '''
                        DELETE FROM public.cotizaciones
                        WHERE id_importacion = ANY(%s)
                        ''',
                        (ids_importacion,),
                    )
                    cursor.execute(
                        '''
                        DELETE FROM public.importaciones
                        WHERE id_importacion = ANY(%s)
                          AND id_usuario = %s
                        ''',
                        (ids_importacion, id_usuario),
                    )
                    cursor.execute(
                        '''
                        DELETE FROM public.proveedores pro
                        WHERE pro.id_proveedor = ANY(%s)
                          AND NOT EXISTS (
                              SELECT 1 FROM public.cotizaciones cot
                              WHERE cot.id_proveedor = pro.id_proveedor
                          )
                          AND NOT EXISTS (
                              SELECT 1 FROM public.comparaciones comp
                              WHERE comp.id_proveedor_recomendado = pro.id_proveedor
                          )
                        ''',
                        (ids_proveedor,),
                    )
            conexion.commit()
            return eliminadas
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()


__all__ = ['ComparacionRepository']
