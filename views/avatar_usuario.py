"""Avatar con foto recortada y las iniciales como alternativa."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QLabel

from utils.fotos_perfil import leer_foto


class AvatarUsuario(QLabel):
    def __init__(self, text='', name='profileAvatar', parent=None):
        super().__init__(text, parent, objectName=name)
        self.setTextFormat(Qt.PlainText)
        self.setAlignment(Qt.AlignCenter)
        self.imagen = QImage()
        self._referencia = None

    def set_foto(self, referencia, imagen=None):
        if referencia == self._referencia and imagen is None:
            return
        self._referencia = referencia
        self.imagen = QImage()
        if referencia:
            try:
                self.imagen = imagen if imagen is not None else leer_foto(referencia)
            except ValueError:
                # Una foto perdida o dañada nunca debe impedir gestionar la cuenta.
                pass
        self.update()

    def paintEvent(self, event):
        if self.imagen.isNull():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        target = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        clip = QPainterPath()
        radius = min(28, target.width() * .24)
        clip.addRoundedRect(target, radius, radius)
        painter.setClipPath(clip)
        side = min(self.imagen.width(), self.imagen.height())
        source = QRectF((self.imagen.width() - side) / 2, (self.imagen.height() - side) / 2, side, side)
        painter.drawImage(target, self.imagen, source)
