"""Zeyver branding scoped to the dashboard, without changing other pages."""

from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget


LOGO_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'images' / 'logo.png'

DASHBOARD_PALETTE = {
    'background': '#f1f2f4',
    'surface': '#ffffff',
    'border': '#d7dade',
    'ink': '#24272b',
    'muted': '#62676e',
    'grid': '#e5e7eb',
    'graphite': '#60656b',
    'accent': '#ff4f12',
    'accent_light': '#ff8a24',
    'nav_gradient': ((0.0, '#ff4b0b'), (0.65, '#ff6212'), (0.88, '#ff8a1c'), (1.0, '#ffd43b')),
    'chart_start': '#ff8a24',
    'chart_end': '#ff4f12',
    'bar_low': '#fdc39c',
    'bar_high': '#ff4f12',
    'line': '#60656b',
    'categories': ('#ff4f12', '#60656b', '#ffae66', '#969ca4', '#c1c5cb', '#454b53'),
}


class ZeyverLogo(QWidget):
    """Render the original logo without its large outer square margins."""

    def __init__(self, compact=False, parent=None):
        super().__init__(parent)
        self.compact = compact
        self.pixmap = QPixmap(str(LOGO_PATH))
        self.setAccessibleName('Zeyver · sale porque sale')
        self.setToolTip('Zeyver · sale porque sale')
        self.setMinimumSize(24, 32)

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # Source coordinates are relative to the original 1080 × 1080 artwork.
        crop = (555, 395, 140, 150) if self.compact else (180, 380, 720, 290)
        x, y, width, height = crop
        source = QRectF(x / 1080 * self.pixmap.width(), y / 1080 * self.pixmap.height(),
                        width / 1080 * self.pixmap.width(), height / 1080 * self.pixmap.height())
        scale = min(self.width() / source.width(), self.height() / source.height())
        target = QRectF(0, 0, source.width() * scale, source.height() * scale)
        target.moveCenter(QRectF(self.rect()).center())
        painter.drawPixmap(target, self.pixmap, source)


DASHBOARD_STYLES = '''
QWidget#corePage, QWidget#coreContent, QScrollArea#coreScroll {
    background: #f1f2f4; color: #24272b;
    font-family: "Segoe UI Variable", "Segoe UI"; border: none;
}
QLabel { color: #24272b; background: transparent; }
QScrollBar:vertical { background: #e9ebee; width: 8px; }
QScrollBar::handle:vertical { background: #969ca4; border-radius: 4px; min-height: 40px; }
QScrollBar::handle:vertical:hover { background: #ff8a24; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QLabel#pageTitle { font-size: 30px; font-weight: 800; color: #24272b; }
QLabel#subtitle, QLabel#muted, QLabel#smallMuted { color: #62676e; font-size: 11px; }
QLabel#smallMuted { font-size: 9px; }
QWidget#shellHeader { background: transparent; }
QFrame#dateFrame { background: #ffffff; border: 1px solid #d7dade; border-radius: 8px; }
QLabel#dateText { color: #454b53; font-size: 11px; }
QLabel#topAvatar { background: #e3e6ea; color: #454b53; border-radius: 20px; font-weight: 800; }
QLabel#accountName { color: #24272b; font-size: 12px; font-weight: 750; }
QLabel#accountRole { color: #62676e; font-size: 10px; }
QFrame#card { background: #ffffff; border: 1px solid #d7dade; border-radius: 9px; }
QLabel#metricValue { font-size: 23px; font-weight: 800; color: #24272b; }
QLabel#metricLabel { font-size: 11px; color: #555b63; }
QLabel#sectionTitle { font-size: 15px; font-weight: 750; color: #30353b; }
QLabel#rowTitle { font-size: 11px; font-weight: 700; color: #30353b; }
QLabel#goodChip { background: #e5f4eb; color: #176d47; border-radius: 6px; padding: 4px 7px; font-size: 10px; font-weight: 700; }
QLabel#badChip { background: #fff0f0; color: #b63738; border-radius: 6px; padding: 4px 7px; font-size: 10px; font-weight: 700; }
QLabel#purpleChip { background: #fff0e5; color: #a64716; border-radius: 6px; padding: 4px 7px; font-size: 9px; font-weight: 650; }
QPushButton#linkButton { background: transparent; color: #b83e0b; border: none; font-size: 11px; font-weight: 650; padding: 4px; }
QPushButton#linkButton:hover { color: #8c2e08; background: #fff0e5; border-radius: 4px; }
QPushButton#linkButton:focus { border: 1px solid #ff8a24; border-radius: 4px; }
QFrame#miniRow { background: #f7f8f9; border: 1px solid #e1e4e8; border-radius: 8px; }
QLabel#thumb { background: #e7e9ed; border-radius: 8px; font-size: 20px; padding: 7px; }
QTableWidget#coreTable { background: #ffffff; alternate-background-color: #f3f4f6; color: #454b53; border: 1px solid #d7dade; border-radius: 7px; font-size: 10px; selection-background-color: #fff0e5; }
QTableWidget#coreTable::item { border-bottom: 1px solid #e5e7eb; padding: 3px; }
QTableWidget#coreTable QHeaderView::section { background: #60656b; color: #ffffff; border: none; border-bottom: 1px solid #454b53; padding: 6px 3px; font-size: 10px; font-weight: 700; }
QTableWidget#coreTable QTableCornerButton::section { background: #60656b; border: none; }
'''


DASHBOARD_SHELL_STYLES = '''
QFrame#sidebar { background: #080808; border: none; border-right: 1px solid #454b53; }
QScrollArea#navScroll QScrollBar::handle:vertical { background: #60656b; }
QWidget#intelligenceMenu { background: #262a30; }
QFrame#sidebarLine, QFrame#navSectionDivider { background: #3c4148; }
QPushButton#sidebarToggle { color: #e4e7eb; background: #30353b; border-color: #60656b; }
QPushButton#sidebarToggle:hover { color: #ffffff; background: #454b53; border-color: #969ca4; }
'''
