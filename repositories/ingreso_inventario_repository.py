"""Acceso a ingresos de inventario y su detalle."""

from decimal import Decimal

from config.database import obtener_conexion
from models.importacion_inventario import (
    IngresoDetalleGuardado,
    IngresoGuardado,
    IngresoHistorial,
)


def _decimal(valor):
    if valor is None:
        return Decimal('0.00')
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


class IngresoInventarioRepository:
    """Persiste la cabecera y las lineas de un ingreso de mercaderia."""

    def __init__(self, conexion=None):
        self._conexion_externa = conexion is not None
        self._conexion = conexion

    def _cursor(self):
        if self._conexion_externa:
            return self._conexion, self._conexion.cursor()
        conexion = obtener_conexion()
        return conexion, conexion.cursor()

    def crear_ingreso(
        self, id_importacion, id_proveedor, fecha_ingreso, numero_productos,
        total_unidades, cursor, observacion=None,
    ):
        consulta = (
            'INSERT INTO public.ingresos_inventario '
            '(id_importacion, id_proveedor, fecha_ingreso, numero_productos, '
            ' total_unidades, observacion) '
            'VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_ingreso'
        )
        cursor.execute(consulta, (
            id_importacion, id_proveedor, fecha_ingreso, numero_productos,
            total_unidades, observacion,
        ))
        return cursor.fetchone()[0]

    def guardar_detalle(self, id_ingreso, filas, cursor):
        if not filas:
            return
        consulta = (
            'INSERT INTO public.detalle_ingreso_inventario '
            '(id_ingreso, id_producto, numero_fila_excel, cantidad, stock_minimo, '
            ' precio_compra, precio_venta, unidad_medida, fecha_ingreso) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'
        )
        datos = [
            (
                id_ingreso,
                id_producto,
                fila.numero_fila,
                fila.cantidad,
                fila.stock_minimo,
                fila.precio_compra,
                fila.precio_venta,
                fila.unidad_medida,
                fila.fecha_ingreso,
            )
            for fila, id_producto in filas
        ]
        cursor.executemany(consulta, datos)

    def listar(self, busqueda='', proveedor='', estado='', fecha=''):
        consulta = (
            'SELECT i.id_ingreso, i.creado_en, p.nombre, imp.nombre_archivo, '
            'COUNT(DISTINCT d.id_producto), COALESCE(SUM(d.cantidad), 0), '
            'COALESCE(SUM(d.cantidad * d.precio_compra), 0), '
            'imp.estado, COALESCE(u.usuario, \'\') '
            'FROM public.ingresos_inventario i '
            'JOIN public.proveedores p ON p.id_proveedor = i.id_proveedor '
            'JOIN public.importaciones imp ON imp.id_importacion = i.id_importacion '
            'LEFT JOIN public.usuarios u ON u.id_usuario = imp.id_usuario '
            'LEFT JOIN public.detalle_ingreso_inventario d ON d.id_ingreso = i.id_ingreso '
            'WHERE (%s = \'\' OR p.nombre ILIKE %s OR imp.nombre_archivo ILIKE %s) '
            'AND (%s = \'\' OR p.nombre = %s) '
            'AND (%s = \'\' OR imp.estado = %s) '
            'AND (%s = \'\' OR i.creado_en::date = NULLIF(%s, \'\')::date) '
            'GROUP BY i.id_ingreso, i.creado_en, p.nombre, imp.nombre_archivo, '
            'imp.estado, u.usuario '
            'ORDER BY i.creado_en DESC, i.id_ingreso DESC'
        )
        termino = str(busqueda or '').strip()
        patron = f'%{termino}%'
        parametros = (
            termino, patron, patron,
            proveedor or '', proveedor or '',
            estado or '', estado or '',
            fecha or '', fecha or '',
        )
        propio = not self._conexion_externa
        conexion, cursor = self._cursor()
        try:
            cursor.execute(consulta, parametros)
            return [
                IngresoHistorial(
                    id_ingreso=fila[0],
                    creado_en=fila[1],
                    proveedor=fila[2],
                    archivo=fila[3],
                    productos=int(fila[4] or 0),
                    unidades=int(fila[5] or 0),
                    costo_total=_decimal(fila[6]),
                    estado=fila[7] or '',
                    responsable=fila[8] or '',
                )
                for fila in cursor.fetchall()
            ]
        finally:
            cursor.close()
            if propio:
                conexion.close()

    def obtener_ingreso(self, id_ingreso, cursor=None):
        consulta = (
            'SELECT i.id_ingreso, i.id_importacion, p.nombre, imp.nombre_archivo, '
            'i.fecha_ingreso, i.numero_productos, i.total_unidades, i.creado_en, '
            'imp.estado, COALESCE(u.usuario, \'\') '
            'FROM public.ingresos_inventario i '
            'JOIN public.proveedores p ON p.id_proveedor = i.id_proveedor '
            'JOIN public.importaciones imp ON imp.id_importacion = i.id_importacion '
            'LEFT JOIN public.usuarios u ON u.id_usuario = imp.id_usuario '
            'WHERE i.id_ingreso = %s'
        )
        propio = cursor is None
        if propio:
            conexion, cursor = self._cursor()
        try:
            cursor.execute(consulta, (id_ingreso,))
            cabecera = cursor.fetchone()
            if cabecera is None:
                return None
            cursor.execute(
                'SELECT d.numero_fila_excel, pr.codigo, pr.nombre, c.nombre, '
                'd.cantidad, d.stock_minimo, d.precio_compra, d.precio_venta, '
                'd.unidad_medida, d.fecha_ingreso, '
                'COALESCE(pr.marca, \'\'), COALESCE(pr.presentacion, \'\') '
                'FROM public.detalle_ingreso_inventario d '
                'JOIN public.productos pr ON pr.id_producto = d.id_producto '
                'JOIN public.categorias c ON c.id_categoria = pr.id_categoria '
                'WHERE d.id_ingreso = %s ORDER BY d.numero_fila_excel',
                (id_ingreso,),
            )
            filas = tuple(
                IngresoDetalleGuardado(
                    numero_fila=fila[0],
                    codigo=fila[1],
                    producto=fila[2],
                    categoria=fila[3],
                    cantidad=fila[4],
                    stock_minimo=fila[5],
                    precio_compra=fila[6],
                    precio_venta=fila[7],
                    unidad_medida=fila[8] or '',
                    fecha_ingreso=fila[9],
                    marca=fila[10] or '',
                    presentacion=fila[11] or '',
                )
                for fila in cursor.fetchall()
            )
            return IngresoGuardado(
                id_ingreso=cabecera[0],
                id_importacion=cabecera[1],
                proveedor=cabecera[2],
                archivo=cabecera[3],
                fecha_ingreso=cabecera[4],
                numero_productos=cabecera[5],
                total_unidades=cabecera[6],
                creado_en=cabecera[7],
                filas=filas,
                estado=cabecera[8] or '',
                responsable=cabecera[9] or '',
                costo_total=sum((fila.subtotal for fila in filas), Decimal('0.00')),
            )
        finally:
            if propio:
                cursor.close()
                conexion.close()
