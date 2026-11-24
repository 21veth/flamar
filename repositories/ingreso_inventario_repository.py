"""Acceso a ingresos de inventario y su detalle."""

from config.database import obtener_conexion
from models.importacion_inventario import IngresoDetalleGuardado, IngresoGuardado


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

    def obtener_ingreso(self, id_ingreso, cursor=None):
        consulta = (
            'SELECT i.id_ingreso, i.id_importacion, p.nombre, imp.nombre_archivo, '
            'i.fecha_ingreso, i.numero_productos, i.total_unidades, i.creado_en '
            'FROM public.ingresos_inventario i '
            'JOIN public.proveedores p ON p.id_proveedor = i.id_proveedor '
            'JOIN public.importaciones imp ON imp.id_importacion = i.id_importacion '
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
                'd.unidad_medida, d.fecha_ingreso '
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
            )
        finally:
            if propio:
                cursor.close()
                conexion.close()
