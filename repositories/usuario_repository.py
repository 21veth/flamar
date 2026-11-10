import psycopg

from config.database import obtener_conexion


class UsuarioRepository:
    """Acceso a la tabla public.usuarios."""

    def obtener_por_usuario(self, usuario):
        """Devuelve el registro del usuario o None si no existe."""
        consulta = (
            'SELECT id_usuario, usuario, password_hash, rol, activo '
            'FROM public.usuarios '
            'WHERE usuario = %s'
        )
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, (usuario,))
                fila = cursor.fetchone()
        if fila is None:
            return None
        return {
            'id_usuario': fila[0],
            'usuario': fila[1],
            'password_hash': fila[2],
            'rol': fila[3],
            'activo': fila[4],
        }

    def actualizar_ultimo_acceso(self, id_usuario):
        """Registra el acceso de un usuario ya autenticado."""
        consulta = (
            'UPDATE public.usuarios '
            'SET ultimo_acceso = CURRENT_TIMESTAMP '
            'WHERE id_usuario = %s'
        )
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, (id_usuario,))
