"""Fotos locales administradas: la BD guarda la ruta, nunca la imagen completa."""

from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QImageReader, QPainter


APP_ROOT = Path(__file__).resolve().parents[1]
PHOTO_DIRECTORY = Path('assets/perfiles')
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000


def ruta_foto(referencia, root=APP_ROOT):
    path = Path(referencia)
    return path if path.is_absolute() else Path(root) / path


def leer_foto(referencia, root=APP_ROOT):
    """Valida el contenido y limita la decodificación antes de crear la imagen."""
    if not isinstance(referencia, str) or not referencia.strip():
        raise ValueError('Selecciona una imagen JPG, PNG o WebP.')
    try:
        path = ruta_foto(referencia, root)
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('La foto debe ser un archivo de imagen de hasta 10 MB.')
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        if bytes(reader.format()).lower() not in (b'jpeg', b'png', b'webp'):
            raise ValueError('Selecciona una imagen JPG, PNG o WebP válida.')
        size = reader.size()
        if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > MAX_PIXELS:
            raise ValueError('La foto no puede superar los 25 megapíxeles.')
        if size.width() > 1024 or size.height() > 1024:
            reader.setScaledSize(size.scaled(QSize(1024, 1024), Qt.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            raise ValueError('No se pudo leer la imagen. Prueba con otra foto.')
        return image
    except (OSError, TypeError, RuntimeError) as error:
        raise ValueError('No se pudo abrir la foto. Comprueba que el archivo esté disponible.') from error


class FotosPerfil:
    def __init__(self, root=APP_ROOT):
        self.root = Path(root)

    @contextmanager
    def preparar(self, referencia):
        """Importa al guardar; descarta solo la copia nueva si falla la transacción."""
        if referencia is None or referencia == '':
            yield None
            return
        image = leer_foto(referencia, self.root)
        side = min(image.width(), image.height())
        image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
        image = image.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        output = QImage(image.size(), QImage.Format_RGB32)
        output.fill(Qt.white)
        painter = QPainter(output)
        painter.drawImage(0, 0, image)
        painter.end()
        reference = (PHOTO_DIRECTORY / (uuid4().hex + '.jpg')).as_posix()
        destination = self.root / reference
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not output.save(str(destination), 'JPG', 90):
                raise ValueError('No se pudo guardar la foto. Revisa los permisos de la carpeta de imágenes.')
        except (OSError, ValueError) as error:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
            raise ValueError('No se pudo guardar la foto. Revisa los permisos de la carpeta de imágenes.') from error
        try:
            yield reference
        except BaseException:
            # Nunca borrar originales ni fotos anteriores: pueden seguir en uso.
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
            raise
