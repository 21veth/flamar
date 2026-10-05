from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


INK = '#0b1739'
MUTED = '#64748b'
PURPLE = '#553cff'
BLUE = '#1479ed'
GREEN = '#08a66c'
ORANGE = '#ff8a16'
RED = '#f3484a'


class BrandWidget(QWidget):
    def __init__(self, compact=False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54 if compact else 68)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(11)

        mark = LogoMark()
        mark.setFixedSize(48, 48)
        layout.addWidget(mark)

        text = QVBoxLayout()
        text.setContentsMargins(0, 3, 0, 3)
        text.setSpacing(0)
        title = QLabel('FLAMAR')
        title.setStyleSheet('color: white; font-size: 20px; font-weight: 800; letter-spacing: 1px;')
        caption = QLabel('A N A L Y T I C S')
        caption.setStyleSheet('color: #7c6cff; font-size: 9px; font-weight: 800;')
        text.addWidget(title)
        text.addWidget(caption)
        layout.addLayout(text)
        layout.addStretch()


class LogoMark(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        heights = (9, 18, 29, 40)
        colors = ('#21b7ee', '#338ff5', '#665cf7', '#7b4cff')
        baseline = self.height() - 7
        for index, (height, color) in enumerate(zip(heights, colors)):
            rect = QRectF(4 + index * 10, baseline - height, 6, height)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(rect, 3, 3)


class BarChart(QWidget):
    def __init__(self, values, labels, parent=None):
        super().__init__(parent)
        self.values = values
        self.labels = labels
        self.setMinimumHeight(150)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(44, 12, -10, -28)
        painter.setFont(QFont('Segoe UI', 8))
        painter.setPen(QColor('#94a3b8'))
        for index in range(4):
            y = area.bottom() - index * area.height() / 3
            painter.drawText(3, int(y + 3), f'{index * 10}K')
            painter.setPen(QPen(QColor('#e8edf5'), 1))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor('#94a3b8'))

        slot = area.width() / len(self.values)
        bar_width = min(22, slot * 0.44)
        maximum = max(self.values)
        gradient = QLinearGradient(0, area.top(), 0, area.bottom())
        gradient.setColorAt(0, QColor('#6d56ff'))
        gradient.setColorAt(1, QColor('#5140ed'))
        for index, value in enumerate(self.values):
            height = value / maximum * area.height() * .92
            x = area.left() + slot * index + (slot - bar_width) / 2
            rect = QRectF(x, area.bottom() - height, bar_width, height)
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor('#64748b'))
            painter.drawText(QRectF(area.left() + slot * index, area.bottom() + 7, slot, 18), Qt.AlignCenter, self.labels[index])


class DonutChart(QWidget):
    COLORS = (PURPLE, BLUE, '#1fb378', ORANGE, RED)

    def __init__(self, values, labels, parent=None):
        super().__init__(parent)
        self.values = values
        self.labels = labels
        self.setMinimumHeight(150)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = min(116, self.height() - 24)
        donut = QRectF(16, (self.height() - size) / 2, size, size)
        start = 90 * 16
        total = sum(self.values)
        pen = QPen()
        pen.setWidth(22)
        pen.setCapStyle(Qt.FlatCap)
        for value, color in zip(self.values, self.COLORS):
            span = -int(value / total * 360 * 16)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(donut.adjusted(11, 11, -11, -11), start, span)
            start += span

        legend_x = donut.right() + 32
        row_height = 23
        top = (self.height() - row_height * len(self.values)) / 2
        painter.setFont(QFont('Segoe UI', 9))
        for index, (value, label, color) in enumerate(zip(self.values, self.labels, self.COLORS)):
            y = top + index * row_height
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(legend_x, y + 7), 5, 5)
            painter.setPen(QColor(INK))
            painter.drawText(QRectF(legend_x + 14, y, max(80, self.width() - legend_x - 60), 16), Qt.AlignVCenter, label)
            painter.drawText(QRectF(self.width() - 45, y, 38, 16), Qt.AlignRight | Qt.AlignVCenter, f'{value}%')


class LineChart(QWidget):
    def __init__(self, values, labels, parent=None):
        super().__init__(parent)
        self.values = values
        self.labels = labels
        self.setMinimumHeight(150)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(40, 12, -12, -28)
        painter.setFont(QFont('Segoe UI', 8))
        for index in range(4):
            y = area.bottom() - index * area.height() / 3
            painter.setPen(QPen(QColor('#e8edf5'), 1))
            painter.drawLine(area.left(), int(y), area.right(), int(y))
            painter.setPen(QColor('#94a3b8'))
            painter.drawText(4, int(y + 3), str(index * 250))

        low, high = min(self.values) - 40, max(self.values) + 40
        step = area.width() / (len(self.values) - 1)
        points = []
        for index, value in enumerate(self.values):
            x = area.left() + index * step
            y = area.bottom() - (value - low) / (high - low) * area.height()
            points.append(QPointF(x, y))

        painter.setPen(QPen(QColor(PURPLE), 3))
        painter.drawPolyline(points)
        for point in points:
            painter.setPen(QPen(QColor(PURPLE), 2))
            painter.setBrush(QColor('white'))
            painter.drawEllipse(point, 3.5, 3.5)

        painter.setPen(QColor('#64748b'))
        for index, label in enumerate(self.labels):
            if index % 2 == 0:
                x = area.left() + index * step
                painter.drawText(QRectF(x - 20, area.bottom() + 7, 40, 16), Qt.AlignCenter, label)
