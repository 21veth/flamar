"""Tema único de la aplicación: paleta Zeyver y adaptación de estilos heredados."""

import colorsys
import re
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget


LOGO_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'images' / 'logo.png'

APP_PALETTE = {
    'background': '#f1f2f4',
    'surface': '#ffffff',
    'border': '#d7dade',
    'ink': '#24272b',
    'muted': '#62676e',
    'grid': '#e5e7eb',
    'graphite': '#60656b',
    'accent': '#ff4f12',
    'accent_light': '#ff8a24',
    'accent_dark': '#d13a00',
    'yellow': '#ffd43b',
    'nav_gradient': ((0.0, '#ff4b0b'), (0.65, '#ff6212'), (0.88, '#ff8a1c'), (1.0, '#ffd43b')),
    'chart_start': '#ff8a24',
    'chart_end': '#ff4f12',
    'bar_low': '#fdc39c',
    'bar_high': '#ff4f12',
    'line': '#60656b',
    'categories': ('#ff4f12', '#60656b', '#ffae66', '#969ca4', '#c1c5cb', '#454b53'),
    'sidebar': '#080808',
    'sidebar_hover': '#30353b',
    'sidebar_submenu': '#262a30',
    'sidebar_line': '#3c4148',
    'warm': '#fff0e5',
    'dark': '#202225',
    'success': '#176d47',
    'success_bg': '#e5f4eb',
    'danger': '#b63738',
    'danger_bg': '#fff0f0',
    'warning': '#a85a12',
    'warning_bg': '#fff2e4',
}

FONT_FAMILY = '"Segoe UI Variable", "Segoe UI"'

APP_STYLESHEET = '''
QWidget { font-family: "Segoe UI Variable", "Segoe UI"; }
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
QFrame#card, QFrame#panel, QFrame#metricCard, QFrame#metric {
    background: #ffffff; border: 1px solid #d7dade; border-radius: 9px;
}
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
QPushButton#primary, QPushButton#primaryButton {
    background: #ff4f12; color: #ffffff; border: none; border-radius: 7px;
    padding: 10px 18px; font-weight: 700;
}
QPushButton#primary:hover, QPushButton#primaryButton:hover { background: #d13a00; }
QFrame#miniRow { background: #f7f8f9; border: 1px solid #e1e4e8; border-radius: 8px; }
QLabel#thumb { background: #e7e9ed; border-radius: 8px; font-size: 20px; padding: 7px; }
QTableWidget { background: #ffffff; alternate-background-color: #f3f4f6; color: #454b53; border: 1px solid #d7dade; }
QTableWidget#coreTable { background: #ffffff; alternate-background-color: #f3f4f6; color: #454b53; border: 1px solid #d7dade; border-radius: 7px; font-size: 10px; selection-background-color: #fff0e5; }
QTableWidget#coreTable::item { border-bottom: 1px solid #e5e7eb; padding: 3px; }
QTableWidget#coreTable QHeaderView::section { background: #60656b; color: #ffffff; border: none; border-bottom: 1px solid #454b53; padding: 6px 3px; font-size: 10px; font-weight: 700; }
QTableWidget#coreTable QTableCornerButton::section { background: #60656b; border: none; }
QHeaderView::section { background: #60656b; color: #ffffff; border: none; padding: 6px 3px; font-weight: 700; }
'''

APP_PAGE_STYLESHEET = APP_STYLESHEET

APP_SHELL_STYLESHEET = '''
QFrame#sidebar { background: #080808; border: none; border-right: 1px solid #454b53; }
QScrollArea#navScroll, QWidget#navContent { background: transparent; border: none; }
QScrollArea#navScroll QScrollBar:vertical { background: transparent; width: 5px; }
QScrollArea#navScroll QScrollBar::handle:vertical { background: #60656b; border-radius: 2px; min-height: 28px; }
QScrollArea#navScroll QScrollBar::add-line:vertical,
QScrollArea#navScroll QScrollBar::sub-line:vertical { height: 0; }
QWidget#intelligenceMenu { background: #262a30; border-radius: 8px; }
QFrame#sidebarLine { background: #3c4148; border: none; }
QFrame#navSectionDivider { background: #3c4148; border: none; margin-left: 12px; margin-right: 12px; }
QPushButton#sidebarToggle { color: #e4e7eb; background: #30353b; border: 1px solid #60656b; border-radius: 7px; font-size: 17px; font-weight: 700; }
QPushButton#sidebarToggle:hover { color: #ffffff; background: #454b53; border-color: #969ca4; }
'''

_ZEYVER_KEEP = {
    '#ffffff', '#f1f2f4', '#f7f8f9', '#f3f4f6', '#e9ebee', '#e5e7eb',
    '#e1e4e8', '#e3e6ea', '#e7e9ed',
    '#d7dade', '#c1c5cb', '#969ca4', '#60656b', '#62676e', '#555b63',
    '#454b53', '#30353b', '#24272b', '#202225', '#080808', '#262a30',
    '#3c4148', '#e4e7eb', '#ff4f12', '#ff8a24', '#ffd43b', '#ff4b0b',
    '#ff6212', '#ff8a1c', '#ffae66', '#fdc39c', '#fff0e5', '#fff2e4',
    '#fff0f0', '#ffe5ed', '#e5f4eb', '#176d47', '#b63738', '#a85a12',
    '#94350b', '#a64716', '#b83e0b', '#8c2e08', '#9d390c', '#ffdbc2',
    '#ffad70', '#d13a00', '#d4d7dc', '#dbe5f3',
}

_BORDERS = {
    '#dfe5ee', '#d5deea', '#dfe6f0', '#e5eaf1', '#dde5f1', '#dce4f0',
    '#e0e6ef', '#d7dfeb', '#e0e4ef', '#e2e6f0', '#dfe4f2', '#e0e7f0',
    '#e1e7f0', '#dce4ee', '#d6dfeb', '#d5dcef', '#d9dfed', '#d6dfec',
    '#d9e0ea', '#d8e0ea', '#d4deea', '#bdc8d8', '#cbd4e1', '#c8d1df',
    '#c6d1e2', '#cad3e0', '#cbd2e2', '#c7cfda', '#c4cddb', '#e3e8f0',
    '#e4e9f1', '#e6ebf2', '#e8ebf3', '#e3e9f1', '#e6eaf1', '#e7ecf4',
    '#e8edf5', '#e1e3e6', '#e1e6ef', '#e2e7ef', '#dde5ee', '#dfe4ee',
    '#bac5d5', '#e7eaf3', '#e8f2ff', '#dce3ed', '#e4eaf2', '#e6eaf1',
    '#d8e0ec', '#d6eee3',
}

_BACKGROUNDS = {
    '#f7f9fd', '#f6f9fe', '#f8faff', '#f9faff', '#fbfbff', '#fbfcff',
    '#f7f9fc', '#f8fafc', '#f1f4f9', '#f2f5fa', '#edf1f6', '#eef3fa',
    '#f1f3f9', '#eef2f7', '#f4f7fb', '#f6f8fc', '#f9fbfe', '#faf9ff',
    '#f3f6fa', '#fafbfe', '#fbfcfe', '#f8f7ff', '#f4f5f8', '#f3f2fa',
    '#f0f1f3', '#eceffa', '#eef2f8', '#fbfaff', '#fbfcfe', '#eaf3ff',
    '#e8f0ff', '#e7f1ff', '#edf5ff', '#f4f2ff',
}

_LAVENDER = {
    '#f0edff', '#eee9ff', '#f7f5ff', '#f4f1ff', '#f0eaff', '#ede9fe',
    '#f3f0ff', '#f2efff', '#ebe8ff', '#f6f3ff', '#f8f6ff', '#f4f2ff',
    '#e9e3ff', '#e5e0ff', '#e4ddff', '#dcd7f9', '#dcd6ff', '#ded7ff',
    '#f5f2ff', '#f3f5f8', '#f8f6ff', '#e6e0ff', '#eeefff', '#efeaff',
}

_SUCCESS = {'#08a66c', '#079557', '#09a868', '#0a9f67', '#22ad78', '#37c978', '#087a51', '#087b4b', '#079365'}
_SUCCESS_BG = {'#e9faf2', '#e4f8ee', '#e2e8f1', '#e1f8ed', '#e6f9f0', '#e8f8f1', '#e8f9f1', '#e7f9f1', '#eaf9f2', '#effaf5', '#d6eee3'}
_DANGER = {'#ef334e', '#ee3157', '#e62e45', '#f3484a', '#ea3f49', '#e9424b', '#e52643', '#e62e45', '#f12678', '#df2531'}
_DANGER_BG = {'#fff0f3', '#ffeaed', '#ffeaef', '#ffedf0', '#ffeaee', '#ffe9eb', '#ffe9ed', '#fdecea', '#fff1f3', '#f2b8c0'}
_WARM = {'#ff9815', '#f59e0b', '#ff8a16', '#f39a1e', '#ff960d', '#ffad18', '#ff9f16', '#f28b00', '#ed7a0a', '#ff7622', '#ff8b22'}
_PURPLE_DARK = {'#4215d8', '#4425dd', '#4518df', '#4125dd', '#4025c9', '#442be8', '#3519bd', '#3f24bc', '#3f35ed'}


def zeyver_color(value):
    """Traduce un color legacy a la paleta Zeyver (idempotente)."""
    if not isinstance(value, str) or not value.startswith('#'):
        return value
    digits = value[1:]
    suffix = ''
    if len(digits) == 8:
        digits, suffix = digits[:6], value[7:]
    elif len(digits) == 3:
        digits = ''.join(char * 2 for char in digits)
    if len(digits) != 6 or not re.fullmatch(r'[0-9a-fA-F]{6}', digits):
        return value
    color = '#' + digits.lower()
    if color in _ZEYVER_KEEP:
        return color + suffix
    if color in _BORDERS:
        return '#d7dade' + suffix
    if color in _BACKGROUND_COLORS():
        return '#f1f2f4' + suffix
    if color in _LAVENDER:
        return '#fff0e5' + suffix
    if color in _SUCCESS:
        return '#176d47' + suffix
    if color in _SUCCESS_BG:
        return '#e5f4eb' + suffix
    if color in _DANGER:
        return '#b63738' + suffix
    if color in _DANGER_BG:
        return '#fff0f0' + suffix
    if color in _WARM:
        return '#ff8a24' + suffix
    if color in _PURPLE_DARK:
        return '#d13a00' + suffix

    red, green, blue = (int(digits[index:index + 2], 16) / 255 for index in (0, 2, 4))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    if saturation < 0.10:
        if lightness > 0.96:
            result = '#ffffff'
        elif lightness > 0.86:
            result = '#f7f8f9'
        elif lightness > 0.68:
            result = '#c1c5cb'
        elif lightness > 0.30:
            result = '#60656b'
        else:
            result = '#24272b'
    elif 0.24 <= hue <= 0.48:
        result = '#e5f4eb' if lightness > 0.86 else '#176d47'
    elif 0.48 < hue < 0.90:
        if lightness > 0.86:
            result = '#f7f8f9'
        elif lightness < 0.42:
            result = '#24272b'
        elif saturation > 0.55:
            result = '#ff4f12'
        else:
            result = '#60656b'
    elif hue > 0.90 or hue < 0.04:
        result = '#fff0f0' if lightness > 0.86 else '#b63738'
    elif 0.04 <= hue < 0.18:
        result = '#ffd43b' if lightness > 0.80 else '#ff8a24'
    elif lightness > 0.93:
        result = '#f7f8f9' if saturation < 0.15 else '#fff0e5'
    elif lightness > 0.84:
        result = '#fff0e5'
    elif lightness > 0.65:
        result = '#ffae66'
    elif lightness >= 0.42 and saturation > 0.55:
        result = '#ff4f12'
    elif lightness > 0.42:
        result = '#ff8a24'
    elif lightness < 0.22:
        result = '#24272b'
    else:
        result = '#ff4f12'
    return result + suffix


def _BACKGROUND_COLORS():
    return _BACKGROUNDS


_HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')


def zeyver_stylesheet(stylesheet):
    """Aplica la paleta Zeyver a una hoja de estilos existente."""
    if not stylesheet:
        return stylesheet
    themed = _HEX.sub(lambda match: zeyver_color(match.group(0)), stylesheet)
    return themed.replace('"Sans Serif"', FONT_FAMILY)


def apply_theme(widget):
    """Aplica el tema a un widget ya construido y a sus descendientes."""
    stylesheet = widget.styleSheet()
    if stylesheet:
        widget.setStyleSheet(zeyver_stylesheet(stylesheet))
    for child in widget.findChildren(QWidget):
        child_stylesheet = child.styleSheet()
        if child_stylesheet:
            child.setStyleSheet(zeyver_stylesheet(child_stylesheet))
    return widget


class ZeyverLogo(QWidget):
    """Logotipo recortado, sin el margen exterior del arte original."""

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
        crop = (555, 395, 140, 150) if self.compact else (180, 380, 720, 290)
        x, y, width, height = crop
        source = QRectF(x / 1080 * self.pixmap.width(), y / 1080 * self.pixmap.height(),
                        width / 1080 * self.pixmap.width(), height / 1080 * self.pixmap.height())
        scale = min(self.width() / source.width(), self.height() / source.height())
        target = QRectF(0, 0, source.width() * scale, source.height() * scale)
        target.moveCenter(QRectF(self.rect()).center())
        painter.drawPixmap(target, self.pixmap, source)


__all__ = [
    'APP_PALETTE', 'APP_STYLESHEET', 'APP_PAGE_STYLESHEET', 'APP_SHELL_STYLESHEET',
    'FONT_FAMILY', 'LOGO_PATH', 'ZeyverLogo', 'apply_theme', 'zeyver_color', 'zeyver_stylesheet',
]
