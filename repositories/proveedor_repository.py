"""Acceso a la tabla public.proveedores."""

from config.database import obtener_conexion


class ProveedorRepository:
    """Registra proveedores evitando duplicados por nombre."""

    def proveedor_existe(self, nombre, cursor=None):
        consulta = 'SELECT 1 FROM public.proveedores WHERE nombre = %s LIMIT 1'
        if cursor is not None:
            cursor.execute(consulta, (nombre.strip(),))
            return cursor.fetchone() is not None

        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor_local:
                cursor_local.execute(consulta, (nombre.strip(),))
                return cursor_local.fetchone() is not None

    def asegurar_proveedor(self, nombre, cursor=None):
        consulta = (
            'INSERT INTO public.proveedores (nombre, activo) VALUES (%s, TRUE) '
            'ON CONFLICT (nombre) DO UPDATE SET activo = TRUE '
            'RETURNING id_proveedor'
        )
        if cursor is not None:
            cursor.execute(consulta, (nombre.strip(),))
            return cursor.fetchone()[0]

        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor_local:
                cursor_local.execute(consulta, (nombre.strip(),))
                return cursor_local.fetchone()[0]
