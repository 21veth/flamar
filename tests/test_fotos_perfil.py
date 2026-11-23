import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import psycopg
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage

from models.sesion_usuario import SesionUsuario
from services.usuarios_service import UsuariosService
from utils.fotos_perfil import FotosPerfil, MAX_FILE_BYTES, PHOTO_DIRECTORY, leer_foto


class FotosPerfilTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix='zeyver-fotos-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.original = self.root / 'original.png'
        image = QImage(240, 320, QImage.Format_ARGB32)
        image.fill(QColor('#4386bc'))
        self.assertTrue(image.save(str(self.original)))
        self.fotos = FotosPerfil(self.root)

    def test_importa_copia_jpg_cuadrada_y_no_depende_del_original(self):
        self.assertEqual(PHOTO_DIRECTORY.as_posix(), 'assets/perfiles')
        with self.fotos.preparar(str(self.original)) as reference:
            self.assertLessEqual(len(reference), 500)
            self.assertTrue(reference.startswith(PHOTO_DIRECTORY.as_posix() + '/'))
        path = self.root / reference
        self.original.unlink()
        self.assertTrue(path.is_file())
        image = leer_foto(reference, self.root)
        self.assertFalse(image.isNull())
        self.assertEqual(image.width(), image.height())
        stored = QImage(str(path))
        self.assertEqual(stored.size(), QSize(512, 512))

    def test_error_de_guardado_revierte_solo_la_copia_nueva(self):
        with self.fotos.preparar(str(self.original)) as previous:
            pass
        with self.assertRaisesRegex(ValueError, 'fallo'):
            with self.fotos.preparar(str(self.original)) as new:
                self.assertTrue((self.root / new).exists())
                raise ValueError('fallo')
        self.assertFalse((self.root / new).exists())
        self.assertTrue((self.root / previous).exists())
        self.assertTrue(self.original.exists())

    def test_sin_foto_no_crea_archivos(self):
        for value in (None, ''):
            with self.fotos.preparar(value) as reference:
                self.assertIsNone(reference)
        self.assertFalse((self.root / PHOTO_DIRECTORY).exists())

    def test_rechaza_archivo_falso_inexistente_o_tipo_invalido(self):
        invalid = self.root / 'falsa.jpg'
        invalid.write_text('esto no es una imagen', encoding='utf-8')
        for reference in (str(invalid), str(self.root / 'no-existe.png'), 123, [], '\x00'):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                leer_foto(reference, self.root)

    def test_limita_peso_y_dimensiones_antes_de_decodificar(self):
        large = self.root / 'grande.png'
        with large.open('wb') as file:
            file.truncate(MAX_FILE_BYTES + 1)
        with self.assertRaisesRegex(ValueError, '10 MB'):
            leer_foto(str(large))
        with patch('utils.fotos_perfil.QImageReader') as reader_class:
            reader = reader_class.return_value
            reader.format.return_value = b'png'
            reader.size.return_value = QSize(6000, 6000)
            with self.assertRaisesRegex(ValueError, 'megapíxeles'):
                leer_foto(str(self.original))
            reader.read.assert_not_called()

    def test_service_persiste_ruta_y_limpia_foto_si_falla_bd(self):
        repo, hasher = MagicMock(), MagicMock()
        repo.crear.return_value = 2
        service = UsuariosService(SesionUsuario(1, 'admin', 'administrador'), repo, hasher, self.fotos)
        datos = dict(usuario='nuevo', rol='trabajador', activo=True,
                     correo='nuevo@example.com', telefono='+51987654321', foto_perfil=str(self.original))
        service.ejecutar('crear', **datos)
        reference = repo.crear.call_args.kwargs['foto_perfil']
        self.assertTrue((self.root / reference).exists())
        self.assertNotEqual(reference, str(self.original))
        repo.modificar.side_effect = psycopg.OperationalError('detalle privado')
        with self.assertRaisesRegex(ValueError, 'conexión'):
            service.ejecutar('modificar', id_usuario=2, **datos)
        failed = repo.modificar.call_args.kwargs['foto_perfil']
        self.assertFalse((self.root / failed).exists())
        self.assertTrue((self.root / reference).exists())

    def test_service_no_importa_foto_antes_de_validar_contactos(self):
        fotos = MagicMock()
        service = UsuariosService(SesionUsuario(1, 'admin', 'administrador'), MagicMock(), MagicMock(), fotos)
        with self.assertRaisesRegex(ValueError, 'obligatorio'):
            service.ejecutar('crear', usuario='nuevo', rol='trabajador', activo=True,
                             foto_perfil=str(self.original))
        fotos.preparar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
