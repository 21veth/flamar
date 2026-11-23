"""Visual language for Zeyver's team and access workspace."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from views.app_theme import APP_PALETTE as DASHBOARD_PALETTE


COLORS = {
    **DASHBOARD_PALETTE,
    'yellow': DASHBOARD_PALETTE['nav_gradient'][-1][1],
    'dark': '#202225',
    'warm': '#fff0e5',
}


def initials(name):
    return ''.join(part[:1] for part in name.split()[:2]).upper() or '?'


class UserDelegate(QStyledItemDelegate):
    """Avatar identities and role/status pills, with accessible item text intact."""

    def paint(self, painter, option, index):
        painter.save()
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        background = '#fff0e5' if selected else '#f7f8f9' if hover else '#ffffff'
        painter.fillRect(option.rect, QColor(background))
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect)
        painter.setPen(QColor('#edf0f2'))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        text = index.data(Qt.DisplayRole) or ''
        font = QFont(option.font)
        font.setPixelSize(12)
        painter.setFont(font)
        if index.column() == 1:
            record = index.siblingAtColumn(0).data(Qt.UserRole) or {}
            avatar = QRectF(rect.left() + 12, rect.center().y() - 20, 40, 40)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#ffdbc2' if selected else '#f0f1f3'))
            painter.drawRoundedRect(avatar, 13, 13)
            painter.setPen(QColor('#9d390c' if selected else COLORS['graphite']))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(avatar, Qt.AlignCenter, initials(text))
            copy = rect.adjusted(64, 13, -10, -30)
            painter.setPen(QColor(COLORS['ink']))
            painter.drawText(copy, Qt.AlignVCenter, painter.fontMetrics().elidedText(text, Qt.ElideRight, int(copy.width())))
            font.setBold(False)
            font.setPixelSize(10)
            painter.setFont(font)
            painter.setPen(QColor(COLORS['muted']))
            secondary = record.get('correo') or f'Cuenta #{record.get("id_usuario", "")}'
            secondary_rect = rect.adjusted(64, 35, -10, -10)
            painter.drawText(secondary_rect, Qt.AlignVCenter,
                             painter.fontMetrics().elidedText(secondary, Qt.ElideRight, int(secondary_rect.width())))
        elif index.column() in (2, 3):
            is_role = index.column() == 2
            warm = text == 'Administrador' if is_role else text == 'Activo'
            foreground, fill = ('#a33b0c', '#fff0e5') if warm else ('#62676e', '#eef0f2')
            width = min(rect.width() - 12, painter.fontMetrics().horizontalAdvance(text) + (26 if is_role else 35))
            pill = QRectF(rect.left() + 6, rect.center().y() - 13, width, 26)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(fill))
            painter.drawRoundedRect(pill, 13, 13)
            painter.setPen(QColor(foreground))
            if not is_role:
                painter.setBrush(QColor(COLORS['accent'] if warm else '#969ca4'))
                painter.drawEllipse(QPointF(pill.left() + 12, pill.center().y()), 3, 3)
                pill.adjust(10, 0, 0, 0)
            painter.drawText(pill, Qt.AlignCenter, text)
        else:
            painter.setPen(QColor(COLORS['muted']))
            painter.drawText(rect.adjusted(10, 0, -6, 0), Qt.AlignVCenter, text)
        painter.restore()


USERS_STYLE = f'''
    QWidget#usersPage, QWidget#usersCanvas, QScrollArea#usersScroll {{
        background: {COLORS['background']}; color: {COLORS['ink']};
        font-family: "Segoe UI Variable", "Segoe UI";
    }}
    QScrollArea#usersScroll {{ border: none; }}
    QTabWidget#usersTabs::pane {{ border: none; background: {COLORS['background']}; }}
    QTabWidget#usersTabs QTabBar::tab {{ color: {COLORS['muted']}; background: transparent;
        border: none; border-bottom: 2px solid transparent; padding: 12px 18px;
        font-size: 12px; font-weight: 650; }}
    QTabWidget#usersTabs QTabBar::tab:selected {{ color: #94350b; background: #fff0e5;
        border-bottom: 2px solid {COLORS['accent']}; }}
    QTabWidget#usersTabs QTabBar::tab:hover {{ color: #94350b; }}
    QLabel {{ background: transparent; color: {COLORS['ink']}; font-family: "Segoe UI Variable", "Segoe UI"; }}
    QLabel#eyebrow {{ color: #8c360f; font-size: 10px; font-weight: 800; letter-spacing: 2px; }}
    QLabel#pageTitle {{ font-size: 29px; font-weight: 800; letter-spacing: -1px; }}
    QLabel#muted, QLabel#accountRole {{ color: {COLORS['muted']}; font-size: 11px; }}
    QLabel#accountName {{ font-size: 12px; font-weight: 750; }}
    QLabel#accountAvatar {{ background: #ffdbc2; color: #94350b; border-radius: 14px; font-weight: 800; font-size: 14px; }}
    QFrame#metric, QFrame#directory, QFrame#inspector {{ background: white; border: 1px solid {COLORS['border']}; border-radius: 16px; }}
    QFrame#inspector {{ background: transparent; border: none; }}
    QFrame#metric[featured="true"] {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ff4f12,stop:0.75 #ff8a24,stop:1 #ffd43b); border: none; }}
    QLabel#metricValue {{ font-size: 30px; font-weight: 800; letter-spacing: -1px; }}
    QLabel#metricCaption {{ font-size: 11px; font-weight: 650; }}
    QLabel#metricHint {{ color: {COLORS['muted']}; font-size: 10px; }}
    QFrame#metric[featured="true"] QLabel#metricHint {{ color: #65260c; }}
    QLabel#metricSymbol {{ color: #ae420f; background: #fff0e5; border-radius: 12px; font-size: 18px; font-weight: 750; }}
    QFrame#metric[featured="true"] QLabel#metricSymbol {{ color: #24272b; background: rgba(255,255,255,90); }}
    QLabel#sectionTitle {{ font-size: 17px; font-weight: 750; }}
    QLabel#countBadge {{ color: #a33b0c; background: #fff0e5; border-radius: 10px; padding: 4px 9px; font-size: 10px; font-weight: 750; }}
    QLabel#profileAvatar {{ color: #9d390c; background: #fff0e5; border: 1px solid #ffd7ba; border-radius: 23px; font-size: 25px; font-weight: 800; }}
    QLabel#profileName {{ font-size: 19px; font-weight: 800; }}
    QLabel#profileRole {{ color: #9d390c; font-size: 11px; font-weight: 650; }}
    QLabel#fieldCaption {{ color: #7a7f85; font-size: 10px; font-weight: 650; }}
    QLabel#fieldValue {{ font-size: 12px; font-weight: 650; }}
    QLabel#permission {{ color: #555b63; font-size: 11px; }}
    QLabel#note {{ color: #7b461e; background: #fff7ed; border-radius: 10px; padding: 12px; font-size: 10px; }}
    QFrame#rule {{ background: #eceef0; border: none; max-height: 1px; }}
    QLineEdit, QComboBox {{ background: #f7f8f9; color: {COLORS['ink']}; border: 1px solid #e1e3e6; border-radius: 9px; padding: 9px 10px; min-height: 18px; font-size: 11px; }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid {COLORS['accent_light']}; background: white; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{ background: white; color: #24272b; selection-background-color: #fff0e5; selection-color: #94350b; }}
    QPushButton {{ font-family: "Segoe UI Variable", "Segoe UI"; font-size: 11px; font-weight: 650; padding: 10px 14px; border-radius: 9px; }}
    QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ff4f12,stop:0.8 #ff8a24,stop:1 #ffd43b); color: #24272b; border: 1px solid #ff8a24; }}
    QPushButton#primary:hover {{ background: #ff8a24; }}
    QPushButton#secondary {{ background: white; color: #34383d; border: 1px solid #d7dade; }}
    QPushButton#secondary:hover {{ background: #fff0e5; border-color: #ffae66; }}
    QPushButton#danger {{ color: #ac3037; background: white; border: 1px solid #efd5d7; }}
    QPushButton#danger:hover {{ background: #fff0f0; }}
    QPushButton:disabled, QPushButton#primary:disabled, QPushButton#secondary:disabled, QPushButton#danger:disabled {{ color: #989da4; background: #f2f3f5; border: 1px solid #e5e7eb; }}
    QPushButton:focus {{ border: 2px solid #a64716; }}
    QTableWidget#usersTable {{ background: white; color: {COLORS['ink']}; border: none; outline: none; font-size: 12px;
        selection-background-color: #fff0e5; selection-color: #94350b; }}
    QTableWidget#usersTable::item {{ background: white; color: {COLORS['ink']}; }}
    QTableWidget#usersTable::item:selected {{ background: #fff0e5; color: #94350b; }}
    QTableWidget#usersTable QHeaderView {{ background: #f7f8f9; color: #7a7f85; }}
    QTableWidget#usersTable QHeaderView::section {{ background: #f7f8f9; color: #7a7f85; border: none; padding: 11px 10px; font-size: 10px; font-weight: 650; text-align: left; }}
    QTableWidget#usersTable QTableCornerButton::section {{ background: #f7f8f9; border: none; }}
    QScrollBar:vertical {{ background: #eceef0; width: 6px; border: none; }}
    QScrollBar:horizontal {{ background: #eceef0; height: 6px; border: none; }}
    QScrollBar::handle {{ background: #a9aeb5; border-radius: 3px; min-height: 25px; min-width: 25px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QLabel#feedback {{ color: #9d390c; background: #fff0e5; padding: 10px 14px; border-radius: 9px; font-size: 11px; }}
    QLabel#feedback[error="true"], QLabel#error {{ color: #ac3037; background: #fff0f0; }}
'''


DIALOG_STYLE = USERS_STYLE + '''
    QDialog { background: #f1f2f4; font-family: "Segoe UI Variable", "Segoe UI"; }
    QFrame#dialogHeader { background: #202225; border-radius: 14px; }
    QFrame#dialogHeader QLabel#dialogTitle { color: white; font-size: 23px; font-weight: 750; }
    QFrame#dialogHeader QLabel#dialogKicker { color: #ffd43b; font-size: 10px; letter-spacing: 2px; font-weight: 750; }
    QFrame#dialogHeader QLabel#dialogCopy { color: #c2c4c8; font-size: 11px; }
    QLabel#formSection { color: #9d390c; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
    QLabel#error { border-radius: 8px; padding: 8px; font-size: 11px; }
    QCheckBox { color: #34383d; font-size: 12px; spacing: 9px; }
    QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #c1c5cb; border-radius: 5px; background: white; }
    QCheckBox::indicator:checked { background: #ff8a24; border: 4px solid #ff4f12; }
    QCheckBox:disabled { color: #8a9097; }
'''
