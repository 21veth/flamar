from contextlib import contextmanager

from config.database import obtener_conexion


SIN_CAMBIOS = object()


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

    @contextmanager
    def _cursor_administrador(self, id_administrador, escritura=False):
        """Revalida el rol vigente en la misma transacción que la operación."""
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '15s'")
                if escritura:
                    # Serializa cambios de permisos y evita carreras entre administradores.
                    cursor.execute('LOCK TABLE public.usuarios IN SHARE ROW EXCLUSIVE MODE')
                cursor.execute(
                    'SELECT rol, activo FROM public.usuarios WHERE id_usuario = %s FOR SHARE',
                    (id_administrador,),
                )
                actor = cursor.fetchone()
                if actor is None or actor[0] != 'administrador' or not actor[1]:
                    raise PermissionError('Solo un administrador activo puede gestionar usuarios.')
                yield cursor

    def listar(self, id_administrador, buscar='', rol=None, activo=None):
        # Nunca devolver hashes de contraseñas a la interfaz.
        buscar_telefono = buscar.translate(str.maketrans('', '', ' ()-'))
        with self._cursor_administrador(id_administrador) as cursor:
            cursor.execute(
                'SELECT id_usuario, usuario, rol, activo, ultimo_acceso, fecha_creacion, '
                'correo, telefono, correo_verificado_en, telefono_verificado_en '
                'FROM public.usuarios '
                'WHERE (strpos(lower(usuario), lower(%s)) > 0 '
                'OR strpos(lower(COALESCE(correo, \'\')), lower(%s)) > 0 '
                'OR (%s <> \'\' AND strpos(COALESCE(telefono, \'\'), %s) > 0)) '
                'AND (%s::text IS NULL OR rol = %s) '
                'AND (%s::boolean IS NULL OR activo = %s) '
                'ORDER BY lower(usuario), id_usuario',
                (buscar, buscar, buscar_telefono, buscar_telefono, rol, rol, activo, activo),
            )
            campos = ('id_usuario', 'usuario', 'rol', 'activo', 'ultimo_acceso', 'fecha_creacion',
                      'correo', 'telefono', 'correo_verificado_en', 'telefono_verificado_en')
            return [dict(zip(campos, fila)) for fila in cursor.fetchall()]

    def crear(self, id_administrador, usuario, password_hash, rol, activo, *, correo=None, telefono=None):
        with self._cursor_administrador(id_administrador, escritura=True) as cursor:
            cursor.execute(
                'INSERT INTO public.usuarios (usuario, password_hash, rol, activo, correo, telefono) '
                'VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_usuario',
                (usuario, password_hash, rol, activo, correo, telefono),
            )
            return cursor.fetchone()[0]

    def modificar(self, id_administrador, id_usuario, usuario, rol, activo, password_hash=None,
                  *, correo=SIN_CAMBIOS, telefono=SIN_CAMBIOS):
        with self._cursor_administrador(id_administrador, escritura=True) as cursor:
            if id_usuario == id_administrador and (rol != 'administrador' or not activo):
                raise ValueError('No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.')
            cambiar_correo, cambiar_telefono = correo is not SIN_CAMBIOS, telefono is not SIN_CAMBIOS
            correo = correo if cambiar_correo else None
            telefono = telefono if cambiar_telefono else None
            cursor.execute(
                'UPDATE public.usuarios SET usuario = %s, rol = %s, activo = %s, '
                'password_hash = COALESCE(%s, password_hash), '
                'correo = CASE WHEN %s THEN %s ELSE correo END, '
                'telefono = CASE WHEN %s THEN %s ELSE telefono END, '
                'correo_verificado_en = CASE WHEN %s AND correo IS DISTINCT FROM %s '
                'THEN NULL ELSE correo_verificado_en END, '
                'telefono_verificado_en = CASE WHEN %s AND telefono IS DISTINCT FROM %s '
                'THEN NULL ELSE telefono_verificado_en END '
                'WHERE id_usuario = %s RETURNING id_usuario',
                (usuario, rol, activo, password_hash, cambiar_correo, correo, cambiar_telefono, telefono,
                 cambiar_correo, correo, cambiar_telefono, telefono, id_usuario),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise ValueError('El usuario ya no existe. Actualiza la lista.')
            return fila[0]

    def eliminar(self, id_administrador, id_usuario):
        with self._cursor_administrador(id_administrador, escritura=True) as cursor:
            if id_usuario == id_administrador:
                raise ValueError('No puedes eliminar tu propia cuenta.')
            cursor.execute('DELETE FROM public.usuarios WHERE id_usuario = %s RETURNING id_usuario', (id_usuario,))
            fila = cursor.fetchone()
            if fila is None:
                raise ValueError('El usuario ya no existe. Actualiza la lista.')
            return fila[0]
