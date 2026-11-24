"""Acceso a las tablas public.categorias y public.productos."""

from config.database import obtener_conexion


class CatalogoRepository:
    """Resuelve y registra las categorias y productos de una cotizacion."""

    def __init__(self, conexion=None):
        self._conexion_externa = conexion is not None
        self._conexion = conexion

    def _cursor(self):
        if self._conexion_externa:
            return self._conexion, self._conexion.cursor()
        conexion = obtener_conexion()
        return conexion, conexion.cursor()

    def asegurar_categoria(self, nombre, cursor=None):
        consulta = (
            'INSERT INTO public.categorias (nombre) VALUES (%s) '
            'ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre '
            'RETURNING id_categoria'
        )
        propio = cursor is None
        if propio:
            conexion, cursor = self._cursor()
        try:
            cursor.execute(consulta, ((nombre or 'General').strip(),))
            id_categoria = cursor.fetchone()[0]
            if propio:
                conexion.commit()
            return id_categoria
        finally:
            if propio:
                cursor.close()
                conexion.close()

    def categoria_existe(self, nombre, cursor=None):
        propio = cursor is None
        if propio:
            conexion, cursor = self._cursor()
        try:
            cursor.execute(
                'SELECT 1 FROM public.categorias WHERE nombre = %s LIMIT 1',
                ((nombre or 'General').strip(),),
            )
            return cursor.fetchone() is not None
        finally:
            if propio:
                cursor.close()
                conexion.close()

    def buscar_producto(self, codigo, nombre, marca, presentacion, cursor=None):
        propio = cursor is None
        if propio:
            conexion, cursor = self._cursor()
        try:
            columnas = 'id_producto, nombre, marca, presentacion'
            if codigo:
                cursor.execute(
                    f'SELECT {columnas} FROM public.productos WHERE codigo = %s LIMIT 1',
                    (codigo,),
                )
            else:
                cursor.execute(
                    f'SELECT {columnas} FROM public.productos '
                    'WHERE lower(btrim(nombre)) = lower(btrim(%s)) '
                    'AND marca IS NOT DISTINCT FROM %s '
                    'AND presentacion IS NOT DISTINCT FROM %s LIMIT 1',
                    (nombre, marca, presentacion),
                )
            fila = cursor.fetchone()
            if fila is None:
                return None
            return {
                'id_producto': fila[0],
                'nombre': fila[1],
                'marca': fila[2],
                'presentacion': fila[3],
            }
        finally:
            if propio:
                cursor.close()
                conexion.close()

    def crear_producto(
        self, codigo, nombre, id_categoria, marca, presentacion, cursor=None,
        unidad_medida=None, stock_minimo=0, precio_venta=None,
        fecha_precio=None, fecha_stock=None,
    ):
        consulta = (
            'INSERT INTO public.productos '
            '(codigo, nombre, id_categoria, activo, marca, presentacion, '
            ' unidad_medida, stock_minimo, precio_venta_actual, '
            ' fecha_ultimo_precio_venta, fecha_ultimo_stock_minimo) '
            'VALUES (%s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s) '
            'RETURNING id_producto'
        )
        propio = cursor is None
        if propio:
            conexion, cursor = self._cursor()
        try:
            cursor.execute(consulta, (
                codigo, nombre, id_categoria, marca, presentacion,
                unidad_medida, stock_minimo or 0, precio_venta or 0,
                fecha_precio, fecha_stock,
            ))
            id_producto = cursor.fetchone()[0]
            if propio:
                conexion.commit()
            return id_producto
        finally:
            if propio:
                cursor.close()
                conexion.close()

    def actualizar_producto_ingreso(
        self, id_producto, unidad_medida, stock_minimo, precio_venta,
        fecha_ingreso, cursor=None,
    ):
        consulta = (
            'UPDATE public.productos SET unidad_medida = %s, stock_minimo = %s, '
            'precio_venta_actual = %s, fecha_ultimo_precio_venta = %s, '
            'fecha_ultimo_stock_minimo = %s WHERE id_producto = %s'
        )
        parametros = (
            unidad_medida, stock_minimo or 0, precio_venta or 0,
            fecha_ingreso, fecha_ingreso, id_producto,
        )
        propio = cursor is None
        if propio:
            conexion, cursor = self._cursor()
        try:
            cursor.execute(consulta, parametros)
            if propio:
                conexion.commit()
        finally:
            if propio:
                cursor.close()
                conexion.close()
