import unittest
from unittest.mock import MagicMock

import psycopg
from argon2 import PasswordHasher

from models.sesion_usuario import SesionUsuario
from repositories.usuario_repository import UsuarioRepository
from services.usuarios_service import UsuariosService


class UsuariosServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.repo.crear.return_value = 2
        self.hasher = MagicMock()
        self.hasher.hash.return_value = 'hash_seguro'
        self.sesion = SesionUsuario(1, 'admin', 'administrador')
        self.service = UsuariosService(self.sesion, self.repo, self.hasher)
        self.datos = dict(usuario='nuevo', rol='trabajador', activo=True, contrasena='ClaveSegura123')

    def test_no_administradores_no_pueden_hacer_ninguna_operacion(self):
        for rol in ('gerente', 'trabajador', '', None, 'Administrador'):
            servicio = UsuariosService(SesionUsuario(2, 'otro', rol), self.repo, self.hasher)
            for accion in ('listar', 'crear', 'modificar', 'eliminar'):
                with self.subTest(rol=rol, accion=accion), self.assertRaises(PermissionError):
                    servicio.ejecutar(accion, **self.datos)
        self.assertEqual(self.repo.mock_calls, [])

    def test_crea_con_hash_y_sin_devolver_credenciales(self):
        resultado = self.service.ejecutar('crear', **self.datos)
        self.hasher.hash.assert_called_once_with('ClaveSegura123')
        self.repo.crear.assert_called_once_with(1, 'nuevo', 'hash_seguro', 'trabajador', True)
        self.assertEqual(resultado, {'accion': 'crear', 'id_usuario': 2, 'reautenticar': False})

    def test_hash_real_compatible_con_login(self):
        hasher = PasswordHasher()
        service = UsuariosService(self.sesion, self.repo, hasher)
        service.ejecutar('crear', **self.datos)
        password_hash = self.repo.crear.call_args.args[2]
        self.assertTrue(password_hash.startswith('$argon2'))
        self.assertTrue(hasher.verify(password_hash, self.datos['contrasena']))

    def test_edita_sin_cambiar_password_si_esta_vacia(self):
        self.service.ejecutar('modificar', **dict(self.datos, id_usuario=2, contrasena=''))
        self.hasher.hash.assert_not_called()
        self.repo.modificar.assert_called_once_with(1, 2, 'nuevo', 'trabajador', True, None)

    def test_password_de_seis_caracteres_permitido_al_crear_y_editar(self):
        for contrasena in ('123456', 'abc123', '1234567'):
            with self.subTest(contrasena=contrasena):
                datos = dict(self.datos, contrasena=contrasena)
                self.service.ejecutar('crear', **datos)
                self.hasher.hash.assert_called_with(contrasena)
                self.service.ejecutar('modificar', id_usuario=2, **datos)
                self.hasher.hash.assert_called_with(contrasena)

    def test_password_de_menos_de_seis_caracteres_rechazado(self):
        for accion in ('crear', 'modificar'):
            for contrasena in ('12345', 'abcde', ' ' * 6):
                with self.subTest(accion=accion, contrasena=contrasena), self.assertRaisesRegex(ValueError, '6 y 128'):
                    self.service.ejecutar(accion, id_usuario=2, **dict(self.datos, contrasena=contrasena))
        self.hasher.hash.assert_not_called()
        self.assertEqual(self.repo.mock_calls, [])

    def test_edita_password_y_reautentica_solo_cuenta_propia(self):
        resultado = self.service.ejecutar('modificar', **dict(self.datos, id_usuario=1, rol='administrador'))
        self.assertTrue(resultado['reautenticar'])
        self.repo.modificar.assert_called_once_with(1, 1, 'nuevo', 'administrador', True, 'hash_seguro')

    def test_no_se_puede_borrar_desactivar_o_degradar_a_si_mismo(self):
        with self.assertRaises(ValueError):
            self.service.ejecutar('eliminar', id_usuario=1)
        for rol, activo in (('trabajador', True), ('gerente', True), ('administrador', False)):
            with self.assertRaises(ValueError):
                self.service.ejecutar('modificar', **dict(self.datos, id_usuario=1, rol=rol, activo=activo))
        self.assertEqual(self.repo.mock_calls, [])

    def test_validacion_de_formulario(self):
        invalidos = (
            dict(usuario=' '), dict(usuario='a' * 101), dict(usuario='abc\n'),
            dict(rol='invitado'), dict(activo=1), dict(contrasena=''),
            dict(contrasena='corta'), dict(contrasena=' ' * 10), dict(contrasena='x' * 129),
        )
        for invalido in invalidos:
            with self.subTest(invalido=invalido), self.assertRaises(ValueError):
                self.service.ejecutar('crear', **dict(self.datos, **invalido))
        self.assertEqual(self.repo.mock_calls, [])

    def test_ids_y_acciones_invalidos(self):
        for valor in (None, '1', True, 0, -1):
            with self.assertRaises(ValueError):
                self.service.ejecutar('eliminar', id_usuario=valor)
        with self.assertRaises(ValueError):
            self.service.ejecutar('__dict__')

    def test_normaliza_correo_y_telefono_al_crear(self):
        self.service.ejecutar('crear', **dict(self.datos, correo='  Persona+ventas@EXAMPLE.COM  ',
                                             telefono='+51 (987) 654-321'))
        self.repo.crear.assert_called_once_with(1, 'nuevo', 'hash_seguro', 'trabajador', True,
                                                correo='persona+ventas@example.com', telefono='+51987654321')

    def test_contactos_son_opcionales_y_se_pueden_borrar_explicitamente(self):
        self.service.ejecutar('modificar', id_usuario=2, **dict(self.datos, correo=' ', telefono=''))
        self.repo.modificar.assert_called_once_with(1, 2, 'nuevo', 'trabajador', True, 'hash_seguro',
                                                    correo=None, telefono=None)

    def test_contactos_invalidos_no_se_guardan_ni_generan_hash(self):
        invalidos = (
            dict(correo='no-es-correo'), dict(correo='a@b'), dict(correo='a b@example.com'),
            dict(correo='a\r\n@example.com'), dict(correo='a..b@example.com'),
            dict(correo='.abc@example.com'), dict(correo='abc@-example.com'),
            dict(correo='a' * 65 + '@example.com'), dict(correo='a@' + 'b' * 64 + '.com'),
            dict(correo=42), dict(telefono='987654321'), dict(telefono='+012345678'),
            dict(telefono='+51123'), dict(telefono='+1234567890123456'),
            dict(telefono='+51abc987654321'), dict(telefono='+51\n987654321'),
            dict(telefono='+٥١٩٨٧٦٥٤٣٢١'), dict(telefono=51987654321),
        )
        for datos in invalidos:
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                self.service.ejecutar('crear', **dict(self.datos, **datos))
        self.assertEqual(self.repo.mock_calls, [])
        self.hasher.hash.assert_not_called()

    def test_no_permite_marcar_contactos_verificados_desde_formulario(self):
        self.service.ejecutar('crear', **dict(self.datos, correo='nuevo@example.com', correo_verificado_en='hoy'))
        self.assertNotIn('correo_verificado_en', self.repo.crear.call_args.kwargs)

    def test_error_de_columnas_remite_al_esquema_general(self):
        self.repo.listar.side_effect = psycopg.errors.UndefinedColumn('detalle privado')
        with self.assertRaisesRegex(ValueError, 'database/flamar_postgres.sql') as resultado:
            self.service.ejecutar('listar')
        self.assertNotIn('detalle privado', str(resultado.exception))

    def test_listar_buscar_y_filtrar(self):
        self.repo.listar.return_value = [{'id_usuario': 2, 'usuario': 'nuevo'}]
        resultado = self.service.ejecutar('listar', buscar=' nue ', rol='trabajador', activo=False)
        self.repo.listar.assert_called_once_with(1, 'nue', 'trabajador', False)
        self.assertEqual(resultado['usuarios'], self.repo.listar.return_value)

    def test_errores_seguros_duplicados_registros_asociados_y_conexion(self):
        for error, mensaje in (
            (psycopg.errors.UniqueViolation('detalle privado'), 'ya existe'),
            (psycopg.errors.ForeignKeyViolation('detalle privado'), 'desactivar'),
            (psycopg.OperationalError('detalle privado'), 'conexión'),
        ):
            self.repo.eliminar.side_effect = error
            with self.assertRaisesRegex(ValueError, mensaje) as resultado:
                self.service.ejecutar('eliminar', id_usuario=2)
            self.assertNotIn('detalle privado', str(resultado.exception))


class UsuarioRepositoryTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        self.conexion = MagicMock()
        self.cursor = self.conexion.cursor.return_value.__enter__.return_value
        parche = patch('repositories.usuario_repository.obtener_conexion')
        conexion = parche.start()
        self.addCleanup(parche.stop)
        conexion.return_value.__enter__.return_value = self.conexion
        self.repo = UsuarioRepository()

    def test_revalida_permiso_vigente_para_todas_las_operaciones(self):
        for actor in (None, ('gerente', True), ('trabajador', True), ('administrador', False)):
            for operar in (
                lambda: self.repo.listar(1),
                lambda: self.repo.crear(1, 'nuevo', 'hash', 'trabajador', True),
                lambda: self.repo.modificar(1, 2, 'nuevo', 'trabajador', True),
                lambda: self.repo.eliminar(1, 2),
            ):
                self.cursor.reset_mock()
                self.cursor.fetchone.return_value = actor
                with self.assertRaises(PermissionError):
                    operar()
                consultas = [llamada.args[0] for llamada in self.cursor.execute.call_args_list]
                self.assertFalse(any(sql.startswith(('INSERT', 'UPDATE', 'DELETE')) for sql in consultas))

    def test_lista_sin_hash_y_busqueda_parametrizada(self):
        self.cursor.fetchone.return_value = ('administrador', True)
        self.cursor.fetchall.return_value = [(2, 'nuevo', 'trabajador', True, None, None)]
        resultado = self.repo.listar(1, "x' OR 1=1 --", 'trabajador', False)
        consulta, parametros = self.cursor.execute.call_args.args
        self.assertNotIn('password_hash', consulta)
        self.assertNotIn("x' OR", consulta)
        self.assertEqual(parametros[0], "x' OR 1=1 --")
        self.assertEqual(resultado[0]['usuario'], 'nuevo')

    def test_proteccion_de_cuenta_propia_tambien_en_repositorio(self):
        self.cursor.fetchone.return_value = ('administrador', True)
        with self.assertRaises(ValueError):
            self.repo.eliminar(1, 1)
        with self.assertRaises(ValueError):
            self.repo.modificar(1, 1, 'admin', 'trabajador', True)

    def test_escrituras_se_serializan_antes_de_comprobar_rol(self):
        self.cursor.fetchone.side_effect = [('administrador', True), (2,)]
        self.assertEqual(self.repo.eliminar(1, 2), 2)
        consultas = [c.args[0] for c in self.cursor.execute.call_args_list]
        bloqueo = next(i for i, sql in enumerate(consultas) if sql.startswith('LOCK TABLE'))
        permiso = next(i for i, sql in enumerate(consultas) if sql.startswith('SELECT rol'))
        self.assertLess(bloqueo, permiso)


if __name__ == '__main__':
    unittest.main()
