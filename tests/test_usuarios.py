import unittest
from unittest.mock import MagicMock, patch

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
        self.datos = dict(usuario='nuevo', rol='trabajador', activo=True,
                          correo='nuevo@example.com', telefono='+51987654321')

    def test_no_administradores_no_pueden_hacer_ninguna_operacion(self):
        for rol in ('gerente', 'trabajador', '', None, 'Administrador'):
            servicio = UsuariosService(SesionUsuario(2, 'otro', rol), self.repo, self.hasher)
            for accion in ('listar', 'crear', 'modificar', 'eliminar'):
                with self.subTest(rol=rol, accion=accion), self.assertRaises(PermissionError):
                    servicio.ejecutar(accion, **self.datos)
        self.assertEqual(self.repo.mock_calls, [])

    def test_crea_clave_temporal_de_ocho_digitos_y_entrega_solo_al_crear(self):
        with patch('services.usuarios_service.secrets.randbelow', return_value=1234567):
            resultado = self.service.ejecutar('crear', **self.datos)
        self.hasher.hash.assert_called_once_with('01234567')
        self.repo.crear.assert_called_once_with(1, 'nuevo', 'hash_seguro', 'trabajador', True,
                                                correo='nuevo@example.com', telefono='+51987654321')
        self.assertEqual(resultado, {'accion': 'crear', 'id_usuario': 2, 'reautenticar': False,
                                     'usuario': 'nuevo', 'contrasena_temporal': '01234567'})

    def test_hash_real_compatible_con_login(self):
        hasher = PasswordHasher()
        service = UsuariosService(self.sesion, self.repo, hasher)
        resultado = service.ejecutar('crear', **self.datos)
        password_hash = self.repo.crear.call_args.args[2]
        self.assertTrue(password_hash.startswith('$argon2'))
        self.assertTrue(hasher.verify(password_hash, resultado['contrasena_temporal']))
        self.assertRegex(resultado['contrasena_temporal'], r'^[0-9]{8}$')

    def test_edita_sin_cambiar_password_ni_devolver_claves(self):
        resultado = self.service.ejecutar('modificar', **dict(self.datos, id_usuario=2))
        self.hasher.hash.assert_not_called()
        self.assertNotIn('contrasena_temporal', resultado)
        self.repo.modificar.assert_called_once_with(1, 2, 'nuevo', 'trabajador', True,
                                                    correo='nuevo@example.com', telefono='+51987654321')

    def test_rechaza_contrasena_manual_incluso_por_llamada_directa(self):
        for accion in ('crear', 'modificar'):
            for campo in ('contrasena', 'password_hash'):
                for valor in ('', None, 'NuevaClave123'):
                    with self.subTest(accion=accion, campo=campo, valor=valor), self.assertRaisesRegex(ValueError, 'Gestión de usuarios'):
                        self.service.ejecutar(accion, id_usuario=2, **dict(self.datos, **{campo: valor}))
        self.hasher.hash.assert_not_called()
        self.assertEqual(self.repo.mock_calls, [])

    def test_edita_datos_y_reautentica_cuenta_propia(self):
        resultado = self.service.ejecutar('modificar', **dict(self.datos, id_usuario=1, rol='administrador'))
        self.assertTrue(resultado['reautenticar'])
        self.repo.modificar.assert_called_once_with(1, 1, 'nuevo', 'administrador', True,
                                                    correo='nuevo@example.com', telefono='+51987654321')

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
            dict(rol='invitado'), dict(activo=1),
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

    def test_contactos_obligatorios_al_crear_y_editar_incluso_si_se_omiten(self):
        for accion in ('crear', 'modificar'):
            for campo in ('correo', 'telefono'):
                for valor in (None, '', '   ', 'omitido'):
                    datos = dict(self.datos, id_usuario=2)
                    if valor == 'omitido':
                        datos.pop(campo)
                    else:
                        datos[campo] = valor
                    with self.subTest(accion=accion, campo=campo, valor=valor), self.assertRaisesRegex(ValueError, 'obligatorio'):
                        self.service.ejecutar(accion, **datos)
        self.assertEqual(self.repo.mock_calls, [])
        self.hasher.hash.assert_not_called()

    def test_foto_omitida_se_conserva_y_none_la_quita(self):
        self.service.ejecutar('modificar', id_usuario=2, **self.datos)
        self.assertNotIn('foto_perfil', self.repo.modificar.call_args.kwargs)
        self.service.ejecutar('modificar', id_usuario=2, **dict(self.datos, foto_perfil=None))
        self.assertIsNone(self.repo.modificar.call_args.kwargs['foto_perfil'])

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
        for actor in (None, ('gerente', True, False), ('trabajador', True, False),
                      ('administrador', False, False), ('administrador', True, True)):
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
        self.cursor.fetchone.return_value = ('administrador', True, False)
        self.cursor.fetchall.return_value = [(2, 'nuevo', 'trabajador', True, None, None,
                                             'nuevo@example.com', '+51987654321', None, None,
                                             'assets/perfiles/foto.jpg')]
        resultado = self.repo.listar(1, "x' OR 1=1 --", 'trabajador', False)
        consulta, parametros = self.cursor.execute.call_args.args
        self.assertNotIn('password_hash', consulta)
        self.assertNotIn("x' OR", consulta)
        self.assertEqual(parametros[0], "x' OR 1=1 --")
        self.assertEqual(resultado[0]['usuario'], 'nuevo')
        self.assertEqual(resultado[0]['foto_perfil'], 'assets/perfiles/foto.jpg')

    def test_crear_y_modificar_persisten_foto_con_parametros(self):
        foto = 'assets/perfiles/foto.jpg'
        self.cursor.fetchone.side_effect = [('administrador', True, False), (2,)]
        self.repo.crear(1, 'nuevo', 'hash', 'trabajador', True, foto_perfil=foto)
        consulta, parametros = self.cursor.execute.call_args.args
        self.assertIn('foto_perfil', consulta)
        self.assertIn('debe_cambiar_password', consulta)
        self.assertIn('TRUE)', consulta)
        self.assertEqual(parametros[-1], foto)
        for cambio, esperado in (({}, (False, None)), ({'foto_perfil': foto}, (True, foto)),
                                  ({'foto_perfil': None}, (True, None))):
            self.cursor.fetchone.side_effect = [('administrador', True, False), (2,)]
            self.repo.modificar(1, 2, 'nuevo', 'trabajador', True, **cambio)
            consulta, parametros = self.cursor.execute.call_args.args
            self.assertIn('foto_perfil = CASE WHEN %s THEN %s ELSE foto_perfil END', consulta)
            self.assertEqual(parametros[7:9], esperado)
            self.assertNotIn('password_hash', consulta)
            self.assertNotIn('debe_cambiar_password', consulta)

    def test_proteccion_de_cuenta_propia_tambien_en_repositorio(self):
        self.cursor.fetchone.return_value = ('administrador', True, False)
        with self.assertRaises(ValueError):
            self.repo.eliminar(1, 1)
        with self.assertRaises(ValueError):
            self.repo.modificar(1, 1, 'admin', 'trabajador', True)

    def test_escrituras_se_serializan_antes_de_comprobar_rol(self):
        self.cursor.fetchone.side_effect = [('administrador', True, False), (2,)]
        self.assertEqual(self.repo.eliminar(1, 2), 2)
        consultas = [c.args[0] for c in self.cursor.execute.call_args_list]
        bloqueo = next(i for i, sql in enumerate(consultas) if sql.startswith('LOCK TABLE'))
        permiso = next(i for i, sql in enumerate(consultas) if sql.startswith('SELECT rol'))
        self.assertLess(bloqueo, permiso)


if __name__ == '__main__':
    unittest.main()
