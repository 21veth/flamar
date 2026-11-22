"""Integración optativa: solo un esquema aislado, siempre revertido."""

import os
import re
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import psycopg
from argon2 import PasswordHasher

from config.database import obtener_conexion
from models.sesion_usuario import SesionUsuario
from repositories.usuario_repository import UsuarioRepository
from services.auth_service import AuthService, CredencialesInvalidasError
from services.usuarios_service import UsuariosService


@unittest.skipUnless(os.getenv('FLAMAR_TEST_DB') == '1', 'Requiere FLAMAR_TEST_DB=1 y PostgreSQL configurado')
class UsuariosPostgresTests(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion()
        self.addCleanup(self.conexion.close)
        self.addCleanup(self.conexion.rollback)
        esquema = 'usuarios_test_' + uuid.uuid4().hex

        class CursorAislado(psycopg.Cursor):
            def execute(self, query, params=None, **kwargs):
                return super().execute(query.replace('public.', esquema + '.') if isinstance(query, str) else query,
                                       params, **kwargs)

        self.conexion.cursor_factory = CursorAislado
        archivo = Path(__file__).resolve().parents[1] / 'database' / 'flamar_postgres.sql'
        sql = re.sub(r'^\s*(?:BEGIN|COMMIT);\s*$', '', archivo.read_text(encoding='utf-8'), flags=re.MULTILINE)
        with self.conexion.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA {esquema}')
            cursor.execute(f'SET LOCAL search_path TO {esquema}')
            cursor.execute(sql)
            cursor.execute("INSERT INTO usuarios(usuario,password_hash,rol) VALUES ('admin','no_login','administrador') RETURNING id_usuario")
            self.id_admin = cursor.fetchone()[0]

        @contextmanager
        def conexion_aislada():
            # Cada operación tiene su savepoint, también si viola una restricción.
            with self.conexion.transaction():
                yield self.conexion

        parche = patch('repositories.usuario_repository.obtener_conexion', conexion_aislada)
        parche.start()
        self.addCleanup(parche.stop)
        self.repo = UsuarioRepository()
        self.service = UsuariosService(SesionUsuario(self.id_admin, 'admin', 'administrador'), self.repo)

    def crear(self, usuario='nuevo', **datos):
        return self.service.ejecutar('crear', **dict(dict(
            usuario=usuario, rol='trabajador', activo=True, contrasena='ClaveDePrueba123'), **datos))['id_usuario']

    def test_crud_y_compatibilidad_con_inicio_de_sesion(self):
        nuevo = self.crear()
        auth = AuthService(self.repo)
        self.assertEqual(auth.autenticar('nuevo', 'ClaveDePrueba123').id_usuario, nuevo)
        self.service.ejecutar('modificar', id_usuario=nuevo, usuario='renombrado', rol='gerente', activo=True, contrasena='OtraClave123')
        self.assertEqual(auth.autenticar('renombrado', 'OtraClave123').rol, 'gerente')
        listado = self.service.ejecutar('listar', buscar='NOMB', rol='gerente', activo=True)['usuarios']
        self.assertEqual([u['id_usuario'] for u in listado], [nuevo])
        self.assertNotIn('password_hash', listado[0])
        self.service.ejecutar('eliminar', id_usuario=nuevo)
        self.assertEqual(self.service.ejecutar('listar', buscar='renombrado')['usuarios'], [])

    def test_desactivar_impide_login_y_password_vacio_conserva_hash(self):
        nuevo = self.crear()
        self.service.ejecutar('modificar', id_usuario=nuevo, usuario='nuevo', rol='trabajador', activo=False, contrasena='')
        with self.assertRaises(CredencialesInvalidasError):
            AuthService(self.repo).autenticar('nuevo', 'ClaveDePrueba123')
        registro = self.repo.obtener_por_usuario('nuevo')
        self.assertTrue(PasswordHasher().verify(registro['password_hash'], 'ClaveDePrueba123'))

    def test_duplicado_no_deja_cambios_parciales(self):
        self.crear()
        with self.assertRaisesRegex(ValueError, 'ya existe'):
            self.crear()
        self.assertEqual(len(self.service.ejecutar('listar')['usuarios']), 2)

    def test_revocacion_de_rol_en_bd_invalida_sesion_antigua(self):
        with self.conexion.cursor() as cursor:
            cursor.execute("UPDATE public.usuarios SET rol='trabajador' WHERE id_usuario=%s", (self.id_admin,))
        with self.assertRaises(PermissionError):
            self.service.ejecutar('listar')
        with self.assertRaises(PermissionError):
            self.crear()

    def test_historial_asociado_impide_borrado_sin_perder_datos(self):
        nuevo = self.crear()
        with self.conexion.cursor() as cursor:
            cursor.execute('CREATE TABLE historial (id_usuario BIGINT REFERENCES usuarios(id_usuario))')
            cursor.execute('INSERT INTO historial VALUES (%s)', (nuevo,))
        with self.assertRaisesRegex(ValueError, 'desactivar'):
            self.service.ejecutar('eliminar', id_usuario=nuevo)
        self.assertIsNotNone(self.repo.obtener_por_usuario('nuevo'))

    def test_usuario_sin_contactos_conserva_credenciales_y_campos_opcionales(self):
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT usuario, password_hash, correo, telefono FROM public.usuarios')
            self.assertEqual(cursor.fetchall(), [('admin', 'no_login', None, None)])

    def test_esquema_general_incluye_contactos_e_indices_unicos(self):
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT correo, telefono, correo_verificado_en, telefono_verificado_en FROM usuarios')
            self.assertEqual([col.name for col in cursor.description],
                             ['correo', 'telefono', 'correo_verificado_en', 'telefono_verificado_en'])
            cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename='usuarios'")
            indices = {fila[0] for fila in cursor.fetchall()}
            self.assertTrue({'uq_usuarios_correo', 'uq_usuarios_telefono'} <= indices)

    def test_contactos_normalizados_persisten_y_se_pueden_buscar(self):
        nuevo = self.crear(correo='  NUEVO@Example.com ', telefono='+51 (987) 654-321')
        for buscar in ('NUEVO@EXAMPLE.COM', '+51987654321', '+51 (987) 654-321', '987654'):
            with self.subTest(buscar=buscar):
                filas = self.service.ejecutar('listar', buscar=buscar)['usuarios']
                self.assertEqual([u['id_usuario'] for u in filas], [nuevo])
                self.assertEqual(filas[0]['correo'], 'nuevo@example.com')
                self.assertEqual(filas[0]['telefono'], '+51987654321')
                self.assertIsNone(filas[0]['correo_verificado_en'])
                self.assertIsNone(filas[0]['telefono_verificado_en'])

    def test_no_permite_correo_o_telefono_duplicado(self):
        self.crear(correo='nuevo@example.com', telefono='+51987654321')
        for datos, mensaje in ((dict(correo='NUEVO@EXAMPLE.COM'), 'correo'),
                               (dict(telefono='+51 987 654 321'), 'teléfono')):
            with self.subTest(datos=datos), self.assertRaisesRegex(ValueError, mensaje):
                self.crear(usuario='otro', **datos)
        self.assertEqual(len(self.service.ejecutar('listar')['usuarios']), 2)

    def test_duplicado_al_editar_revierte_todos_los_campos(self):
        self.crear(correo='nuevo@example.com')
        otro = self.crear(usuario='otro', correo='otro@example.com')
        with self.assertRaisesRegex(ValueError, 'correo'):
            self.service.ejecutar('modificar', id_usuario=otro, usuario='renombrado', rol='gerente',
                                 activo=False, correo='nuevo@example.com')
        registro = self.service.ejecutar('listar', buscar='otro')['usuarios'][0]
        self.assertEqual(registro['usuario'], 'otro')
        self.assertEqual(registro['rol'], 'trabajador')
        self.assertTrue(registro['activo'])
        self.assertEqual(registro['correo'], 'otro@example.com')

    def test_cambio_de_contacto_invalida_solo_su_verificacion(self):
        nuevo = self.crear(correo='nuevo@example.com', telefono='+51987654321')
        with self.conexion.cursor() as cursor:
            cursor.execute('UPDATE public.usuarios SET correo_verificado_en=CURRENT_TIMESTAMP, '
                           'telefono_verificado_en=CURRENT_TIMESTAMP WHERE id_usuario=%s', (nuevo,))
        self.service.ejecutar('modificar', id_usuario=nuevo, usuario='nuevo', rol='gerente', activo=True,
                             correo='nuevo@example.com', telefono='+51987654321')
        registro = self.service.ejecutar('listar', buscar='nuevo')['usuarios'][0]
        self.assertIsNotNone(registro['correo_verificado_en'])
        self.service.ejecutar('modificar', id_usuario=nuevo, usuario='nuevo', rol='gerente', activo=True,
                             correo='otro@example.com')
        registro = self.service.ejecutar('listar', buscar='nuevo')['usuarios'][0]
        self.assertIsNone(registro['correo_verificado_en'])
        self.assertEqual(registro['telefono'], '+51987654321')
        self.assertIsNotNone(registro['telefono_verificado_en'])
        self.service.ejecutar('modificar', id_usuario=nuevo, usuario='nuevo', rol='gerente', activo=True,
                             telefono='')
        registro = self.service.ejecutar('listar', buscar='nuevo')['usuarios'][0]
        self.assertIsNone(registro['telefono'])
        self.assertIsNone(registro['telefono_verificado_en'])

    def test_edicion_sin_contactos_los_conserva_y_vacios_los_quitan(self):
        nuevo = self.crear(correo='nuevo@example.com', telefono='+51987654321')
        datos = dict(id_usuario=nuevo, usuario='nuevo', rol='trabajador', activo=True)
        self.service.ejecutar('modificar', **datos)
        registro = self.service.ejecutar('listar', buscar='nuevo')['usuarios'][0]
        self.assertEqual(registro['correo'], 'nuevo@example.com')
        self.assertEqual(registro['telefono'], '+51987654321')
        self.service.ejecutar('modificar', **datos, correo='', telefono='')
        registro = self.service.ejecutar('listar', buscar='nuevo')['usuarios'][0]
        self.assertIsNone(registro['correo'])
        self.assertIsNone(registro['telefono'])


if __name__ == '__main__':
    unittest.main()
