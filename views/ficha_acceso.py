"""Carnet de acceso de dos caras, inspirado en assets/images/ficha_acceso.png."""

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame, QGraphicsEffect, QHBoxLayout, QLabel, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from views.avatar_usuario import AvatarUsuario


CARD_STYLE = '''
    QWidget#badgeSurface, QWidget#badgeFace, QStackedWidget#badgeFaces {
        background: transparent; border: none;
    }
    QWidget#badgeSurface QLabel {
        background: transparent; border: none; color: #202225;
        font-family: "Segoe UI"; font-size: 12px;
    }
    QWidget#badgeSurface QLabel#badgeAvatar {
        background: #ffecd9; color: #a43a08; border: 2px solid #ff9b18;
        border-radius: 28px; font-size: 48px; font-weight: 800;
    }
    QWidget#badgeSurface QLabel#badgeName { font-size: 28px; font-weight: 800; }
    QWidget#badgeSurface QLabel#badgeRole { color: #b8430c; font-size: 14px; font-weight: 650; }
    QWidget#badgeSurface QLabel#badgeStatus {
        background: #dff0df; color: #206c36; border-radius: 16px;
        padding: 6px 18px; font-size: 14px; font-weight: 650;
    }
    QWidget#badgeSurface QLabel#badgeStatus[active="false"] { background: #eceef0; color: #656b73; }
    QWidget#badgeSurface QLabel#badgeId {
        background: #ffead7; color: #a43a08; border-radius: 7px;
        padding: 5px 10px; font-size: 16px; font-weight: 750;
    }
    QWidget#badgeSurface QLabel#badgeCaption { color: #656970; font-size: 11px; }
    QWidget#badgeSurface QLabel#badgeValue { font-size: 12px; font-weight: 650; }
    QWidget#badgeSurface QFrame#badgeRule { background: #dcdedf; border: none; }
'''


def _text(text='', name='badgeValue', center=False):
    label = QLabel(text, objectName=name)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    if center:
        label.setAlignment(Qt.AlignCenter)
    return label


def _rule():
    line = QFrame(objectName='badgeRule')
    line.setFixedHeight(1)
    return line


class _DetailIcon(QWidget):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.setFixedSize(34, 34)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#fff0e1'))
        p.drawRoundedRect(self.rect(), 10, 10)
        p.setPen(QPen(QColor('#f1760c'), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        if self.kind == 'clock':
            p.drawEllipse(QRectF(8, 8, 18, 18))
            p.drawPolyline([QPointF(17, 11), QPointF(17, 17), QPointF(22, 20)])
        elif self.kind == 'calendar':
            p.drawRoundedRect(QRectF(9, 10, 17, 17), 2, 2)
            p.drawLine(9, 15, 26, 15)
            p.drawLine(13, 7, 13, 12)
            p.drawLine(22, 7, 22, 12)
        elif self.kind == 'mail':
            p.drawRoundedRect(QRectF(7, 10, 21, 15), 2, 2)
            p.drawPolyline([QPointF(8, 11), QPointF(17.5, 19), QPointF(27, 11)])
        elif self.kind == 'phone':
            path = QPainterPath(QPointF(10, 8))
            path.cubicTo(4, 12, 16, 30, 24, 26)
            path.lineTo(27, 22)
            path.lineTo(21, 19)
            path.lineTo(18, 22)
            path.quadTo(13, 19, 12, 15)
            path.lineTo(15, 13)
            path.lineTo(12, 8)
            path.closeSubpath()
            p.drawPath(path)
        else:
            p.drawEllipse(QRectF(12, 7, 9, 9))
            p.drawArc(QRectF(7, 20, 20, 17), 0, 180 * 16)
            p.drawArc(QRectF(21, 8, 7, 8), -90 * 16, 180 * 16)
            p.drawArc(QRectF(23, 20, 8, 13), 0, 90 * 16)


class _FlipEffect(QGraphicsEffect):
    def __init__(self, parent):
        super().__init__(parent)
        self.scale = 1.0

    def draw(self, painter):
        center = self.sourceBoundingRect().center()
        painter.save()
        painter.translate(center)
        painter.scale(self.scale, 1)
        painter.translate(-center)
        self.drawSource(painter)
        painter.restore()


class _BadgeSurface(QWidget):
    def __init__(self, parent):
        super().__init__(parent, objectName='badgeSurface')
        self.back = False
        self.identifier = ''
        self.setStyleSheet(CARD_STYLE)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        body = QRectF(7, 76, w - 14, h - 88)
        outline = QPainterPath()
        outline.addRoundedRect(body, 27, 27)
        # A soft, drawn shadow keeps the flip effect independent of platform effects.
        painter.setPen(Qt.NoPen)
        for offset in range(8, 0, -1):
            painter.setBrush(QColor(25, 27, 29, 3))
            painter.drawRoundedRect(body.adjusted(-offset / 2, 1, offset / 2, offset), 29, 29)
        paper = QLinearGradient(0, 180, w, h)
        paper.setColorAt(0, QColor('#ffffff'))
        paper.setColorAt(1, QColor('#f1f2f1'))
        painter.fillPath(outline, paper)
        painter.save()
        painter.setClipPath(outline)
        dark = QLinearGradient(0, 76, w, 230)
        dark.setColorAt(0, QColor('#292b2a'))
        dark.setColorAt(1, QColor('#121413'))
        header = QPainterPath()
        header.moveTo(0, 76)
        header.lineTo(w, 76)
        header.lineTo(w, 171)
        header.cubicTo(w - 48, 214, w - 62, 203, 58, 204)
        header.quadTo(19, 204, 0, 232)
        header.closeSubpath()
        painter.fillPath(header, QColor('#ff800b'))
        painter.translate(0, -5)
        painter.fillPath(header, dark)
        painter.translate(0, 5)
        orange = QLinearGradient(w / 3, h, w, h - 65)
        orange.setColorAt(0, QColor('#fff0e3'))
        orange.setColorAt(1, QColor('#ff7400'))
        swoosh = QPainterPath()
        swoosh.moveTo(35, h)
        swoosh.cubicTo(w - 90, h - 28, w - 43, h + 5, w, h - 82)
        swoosh.lineTo(w, h)
        swoosh.closeSubpath()
        if self.back:
            painter.fillRect(QRectF(0, h - 72, w, 75), dark)
        painter.fillPath(swoosh, orange)
        painter.restore()
        painter.setPen(QPen(QColor('#d3d5d3'), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(outline)
        # Lanyard, ring, and metal clip, rather than a static image with sample data.
        center = w / 2
        painter.setPen(QPen(QColor('#868985'), 3))
        painter.drawRoundedRect(QRectF(center - 24, 37, 48, 33), 10, 10)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor('#1b1d1b'))
        painter.drawRoundedRect(QRectF(center - 23, -10, 46, 64), 5, 5)
        metal = QLinearGradient(center - 13, 0, center + 13, 0)
        metal.setColorAt(0, QColor('#858984'))
        metal.setColorAt(.5, QColor('#e0e2df'))
        metal.setColorAt(1, QColor('#777b77'))
        painter.setPen(QPen(QColor('#bcbfba'), 1))
        painter.setBrush(QColor('#d2d4d0'))
        painter.drawRoundedRect(QRectF(center - 31, 91, 62, 12), 6, 6)
        painter.setBrush(metal)
        painter.drawRoundedRect(QRectF(center - 14, 51, 28, 46), 3, 3)
        # Brand lockup, shared by both sides.
        font = QFont('Segoe UI')
        font.setPixelSize(30)
        font.setBold(True)
        painter.setFont(font)
        x, y = 31, 126
        for part, color in (('zey', '#ffffff'), ('v', '#ff7400'), ('er', '#ffffff')):
            painter.setPen(QColor(color))
            width = painter.fontMetrics().horizontalAdvance(part)
            painter.drawText(QRectF(x, y, width + 2, 45), Qt.AlignVCenter, part)
            x += width
        divider = max(x + 13, w * .57)
        painter.setPen(QPen(QColor('#c9ccc8'), 1))
        painter.drawLine(int(divider), 133, int(divider), 166)
        font.setPixelSize(10)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(QRectF(divider + 15, 128, w - divider - 23, 45),
                         Qt.AlignVCenter, 'DETALLES\nDEL ACCESO' if self.back else 'FICHA DE\nACCESO')
        if self.back:
            painter.setPen(QPen(QColor('#f17816'), 1.7))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(33, h - 50, 14, 12), 2, 2)
            painter.drawArc(QRectF(36, h - 58, 8, 13), 0, 180 * 16)
            painter.setPen(QPen(QColor('#b9bcb9'), 1))
            painter.drawLine(62, h - 57, 62, h - 34)
            painter.setPen(QColor('#ffffff'))
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(QRectF(77, h - 66, w - 105, 42), Qt.AlignVCenter, 'USO INTERNO')
        else:
            # Decorative identifier bars; not an authentication credential.
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#202225'))
            x = 34
            seed = self.identifier or 'ZEYVER'
            for index in range(66):
                width = 1 + (ord(seed[index % len(seed)]) + index) % 3
                if x + width > w - 74:
                    break
                painter.drawRect(QRectF(x, h - 78, width, 35))
                x += width + 2
            painter.setPen(QColor('#f17816'))
            font.setPixelSize(27)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 0)
            painter.setFont(font)
            painter.setPen(QPen(QColor('#f17816'), 2, Qt.SolidLine, Qt.RoundCap))
            for radius in (6, 11, 16):
                painter.drawArc(QRectF(w - 62 - radius, h - 60 - radius, radius * 2, radius * 2),
                                -60 * 16, 120 * 16)


class FichaAcceso(QWidget):
    """Hover previews the back; a click pins it. Click again to return to front."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('accessBadge')
        self.setMinimumWidth(300)
        self.setMaximumWidth(360)
        self.setFixedHeight(620)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName('Carnet de acceso')
        self.setToolTip('Pasa el mouse para ver el reverso. Haz clic para fijarlo o volver.\nTambién puedes usar Enter o Espacio.')
        self._identity = None
        self._pinned = False
        self._progress = 0.0
        self.surface = _BadgeSurface(self)
        self.surface.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.faces = QStackedWidget(self.surface, objectName='badgeFaces')
        self.effect = _FlipEffect(self.surface)
        self.surface.setGraphicsEffect(self.effect)
        self._front()
        self._back()
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(420)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.valueChanged.connect(self._animate)
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(280)
        self.hover_timer.timeout.connect(lambda: self.show_back(True))

    @property
    def back_visible(self):
        return self.faces.currentIndex() == 1

    def sizeHint(self):
        return QSize(360, 620)

    def _front(self):
        face = QWidget(objectName='badgeFace')
        layout = QVBoxLayout(face)
        layout.setContentsMargins(30, 224, 30, 99)
        layout.setSpacing(9)
        self.avatar = AvatarUsuario('◎', 'badgeAvatar')
        self.avatar.setFixedSize(116, 116)
        layout.addWidget(self.avatar, 0, Qt.AlignHCenter)
        self.nombre = _text('Cada persona,\nsu lugar.', 'badgeName', True)
        self.nombre.setMaximumHeight(72)
        layout.addWidget(self.nombre)
        self.rol = _text('Selecciona una cuenta del directorio', 'badgeRole', True)
        self.rol.setMaximumHeight(40)
        layout.addWidget(self.rol)
        self.estado = _text('—', 'badgeStatus', True)
        self.estado.setFixedHeight(34)
        layout.addWidget(self.estado, 0, Qt.AlignHCenter)
        layout.addStretch(1)
        layout.addWidget(_rule())
        row = QHBoxLayout()
        row.addWidget(_text('ID DE ACCESO', 'badgeCaption'), 1)
        self.codigo = _text('ACC-—', 'badgeId', True)
        row.addWidget(self.codigo)
        layout.addLayout(row)
        layout.addWidget(_rule())
        self.faces.addWidget(face)

    def _back(self):
        face = QWidget(objectName='badgeFace')
        layout = QVBoxLayout(face)
        layout.setContentsMargins(29, 218, 29, 86)
        layout.setSpacing(7)
        self.acceso = _text('—')
        self.creacion = _text('—')
        self.correo = _text('—')
        self.telefono = _text('—')
        self.permisos = _text('Selecciona una cuenta para consultar su rol.')
        for index, (kind, caption, value) in enumerate((
            ('clock', 'Último acceso', self.acceso),
            ('calendar', 'Creación', self.creacion),
            ('mail', 'Correo', self.correo),
            ('phone', 'Teléfono', self.telefono),
            ('users', 'Alcance del rol', self.permisos),
        )):
            if index:
                layout.addWidget(_rule())
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(_DetailIcon(kind))
            copy = QVBoxLayout()
            copy.setSpacing(1)
            copy.addWidget(_text(caption, 'badgeCaption'))
            value.setMaximumHeight(45)
            copy.addWidget(value)
            row.addLayout(copy, 1)
            layout.addLayout(row, 1)
        self.faces.addWidget(face)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.surface.setGeometry(self.rect())
        self.faces.setGeometry(self.surface.rect())

    def _animate(self, value):
        self._progress = float(value)
        self.faces.setCurrentIndex(int(self._progress >= .5))
        self.surface.back = self.back_visible
        self.surface.update()
        self.effect.scale = max(.015, abs(math.cos(math.pi * self._progress)))
        self.effect.update()

    def show_back(self, back):
        self.animation.stop()
        self.animation.setStartValue(self._progress)
        self.animation.setEndValue(1.0 if back else 0.0)
        self.animation.start()

    def reset_for(self, identity):
        if identity == self._identity:
            return
        self._identity = identity
        self.hover_timer.stop()
        self.animation.stop()
        self._pinned = False
        self._animate(0.0)

    def set_status(self, active):
        self.estado.setProperty('active', bool(active))
        self.estado.style().unpolish(self.estado)
        self.estado.style().polish(self.estado)

    def set_code(self, identity):
        code = f'ACC-{identity:03d}' if identity is not None else 'ACC-—'
        self.codigo.setText(code)
        self.surface.identifier = code
        self.surface.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self._pinned:
            self.hover_timer.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hover_timer.stop()
        if not self._pinned:
            self.show_back(False)

    def _toggle(self):
        self.hover_timer.stop()
        self._pinned = not self._pinned
        self.show_back(self._pinned)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self._toggle()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if not event.isAutoRepeat():
                self._toggle()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.hasFocus():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor('#d96a13'), 1, Qt.DashLine))
            painter.drawRoundedRect(self.rect().adjusted(1, 73, -1, -2), 29, 29)
