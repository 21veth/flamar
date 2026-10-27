from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from views.analytics_redesign_views import DemandView, PurchasePatternsView, SegmentationView
from views.core_inventory_views import DashboardView, ImportDataView, ProductsView, SalesView
from views.decision_redesign_views import RecommendationsView, ReportsView, SupplyView
from views.intelligence_redesign_views import CalendarView, SmartRecommendationsView, TrendsView
from views.ui_components import BrandWidget, LogoMark


class NavButton(QPushButton):
    def __init__(self, text, kind, child=False, expandable=False, parent=None):
        super().__init__(parent)
        self.label = text
        self.kind = kind
        self.child = child
        self.expandable = expandable
        self.expanded = False
        self.compact = False
        self.setCheckable(not expandable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)

    def set_expanded(self, expanded):
        self.expanded = expanded
        self.update()

    def set_compact(self, compact):
        self.compact = compact
        self.setToolTip(self.label if compact else '')
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        active = self.isChecked()
        if active:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#5527f5'))
            painter.drawRoundedRect(self.rect().adjusted(0, 1, 0, -1), 8, 8)
        elif self.underMouse():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#122d51'))
            painter.drawRoundedRect(self.rect().adjusted(0, 1, 0, -1), 8, 8)

        color = QColor('#ffffff' if active else '#dbe5f3')
        icon_x = (self.width() - 20) / 2 if self.compact else 14 + (16 if self.child else 0)
        icon_rect = QRectF(icon_x, 9, 20, 20)
        self._draw_icon(painter, icon_rect, color)
        if not self.compact:
            painter.setPen(color)
            painter.setFont(QFont('Segoe UI', 8 if self.child else 9, QFont.DemiBold if active else QFont.Normal))
            painter.drawText(QRectF(47 + (16 if self.child else 0), 0, self.width() - 65, self.height()), Qt.AlignVCenter, self.label)
        if self.expandable and not self.compact:
            painter.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            x, y = self.width() - 17, self.height() / 2
            if self.expanded:
                painter.drawLine(QPointF(x - 4, y - 2), QPointF(x, y + 2))
                painter.drawLine(QPointF(x, y + 2), QPointF(x + 4, y - 2))
            else:
                painter.drawLine(QPointF(x - 2, y - 4), QPointF(x + 2, y))
                painter.drawLine(QPointF(x + 2, y), QPointF(x - 2, y + 4))

    def _draw_icon(self, painter, rect, color):
        painter.setPen(QPen(color, 1.55, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        if self.kind == 'home':
            painter.drawPolyline([QPointF(x+2,y+9), QPointF(x+10,y+2), QPointF(x+18,y+9)])
            painter.drawRoundedRect(QRectF(x+4,y+8,w-8,h-7), 2, 2)
        elif self.kind == 'import':
            painter.drawRoundedRect(QRectF(x+3,y+5,w-6,h-5), 3, 3)
            painter.drawLine(QPointF(x+10,y+1),QPointF(x+10,y+12)); painter.drawLine(QPointF(x+6,y+8),QPointF(x+10,y+12)); painter.drawLine(QPointF(x+14,y+8),QPointF(x+10,y+12))
        elif self.kind == 'cube':
            painter.drawPolygon([QPointF(x+10,y+1),QPointF(x+18,y+5),QPointF(x+18,y+14),QPointF(x+10,y+19),QPointF(x+2,y+14),QPointF(x+2,y+5)])
            painter.drawLine(QPointF(x+2,y+5),QPointF(x+10,y+10)); painter.drawLine(QPointF(x+18,y+5),QPointF(x+10,y+10)); painter.drawLine(QPointF(x+10,y+10),QPointF(x+10,y+19))
        elif self.kind == 'bars':
            for index, height in enumerate((7, 13, 18, 11)):
                painter.drawLine(QPointF(x+2+index*5,y+19),QPointF(x+2+index*5,y+19-height))
        elif self.kind == 'people':
            painter.drawEllipse(QRectF(x+3,y+2,6,6)); painter.drawEllipse(QRectF(x+12,y+4,5,5)); painter.drawArc(QRectF(x,y+9,12,10),0,180*16); painter.drawArc(QRectF(x+9,y+10,10,8),0,180*16)
        elif self.kind == 'pattern':
            painter.drawRoundedRect(QRectF(x+2,y+2,8,8),1,1); painter.drawRoundedRect(QRectF(x+10,y+10,8,8),1,1); painter.drawLine(QPointF(x+8,y+9),QPointF(x+12,y+12))
        elif self.kind == 'forecast':
            painter.drawRoundedRect(QRectF(x+2,y+3,w-4,h-4),2,2); painter.drawPolyline([QPointF(x+5,y+15),QPointF(x+8,y+11),QPointF(x+11,y+13),QPointF(x+15,y+7)])
        elif self.kind == 'intel':
            painter.drawEllipse(QRectF(x+5,y+2,10,13)); painter.drawLine(QPointF(x+7,y+16),QPointF(x+13,y+16)); painter.drawLine(QPointF(x+8,y+19),QPointF(x+12,y+19)); painter.drawLine(QPointF(x+1,y+7),QPointF(x+3,y+8)); painter.drawLine(QPointF(x+17,y+8),QPointF(x+19,y+7))
        elif self.kind == 'calendar':
            painter.drawRoundedRect(QRectF(x+2,y+4,w-4,h-5),2,2); painter.drawLine(QPointF(x+2,y+9),QPointF(x+18,y+9)); painter.drawLine(QPointF(x+6,y+1),QPointF(x+6,y+6)); painter.drawLine(QPointF(x+14,y+1),QPointF(x+14,y+6))
        elif self.kind == 'radar':
            painter.drawEllipse(QRectF(x+2,y+2,16,16)); painter.drawEllipse(QRectF(x+6,y+6,8,8)); painter.drawLine(QPointF(x+10,y+10),QPointF(x+18,y+2))
        elif self.kind == 'spark':
            painter.drawLine(QPointF(x+10,y+1),QPointF(x+10,y+19)); painter.drawLine(QPointF(x+1,y+10),QPointF(x+19,y+10)); painter.drawLine(QPointF(x+4,y+4),QPointF(x+16,y+16)); painter.drawLine(QPointF(x+16,y+4),QPointF(x+4,y+16))
        elif self.kind == 'recommend':
            painter.drawEllipse(QRectF(x+4,y+4,12,12)); painter.drawLine(QPointF(x+10,y),QPointF(x+10,y+3)); painter.drawLine(QPointF(x+10,y+17),QPointF(x+10,y+20)); painter.drawLine(QPointF(x,y+10),QPointF(x+3,y+10)); painter.drawLine(QPointF(x+17,y+10),QPointF(x+20,y+10))
        elif self.kind == 'supply':
            painter.drawRoundedRect(QRectF(x+3,y+7,w-6,h-8),3,3); painter.drawArc(QRectF(x+6,y+1,8,10),0,180*16)
        elif self.kind == 'logout':
            painter.drawRoundedRect(QRectF(x+7,y+2,10,16),2,2)
            painter.drawLine(QPointF(x+2,y+10),QPointF(x+12,y+10))
            painter.drawLine(QPointF(x+2,y+10),QPointF(x+6,y+6))
            painter.drawLine(QPointF(x+2,y+10),QPointF(x+6,y+14))
        else:
            painter.drawRoundedRect(QRectF(x+3,y+1,w-6,h-2),2,2); painter.drawLine(QPointF(x+6,y+6),QPointF(x+14,y+6)); painter.drawLine(QPointF(x+6,y+10),QPointF(x+14,y+10)); painter.drawLine(QPointF(x+6,y+14),QPointF(x+12,y+14))


class ResponsivePageView(QGraphicsView):
    DESIGN_WIDTH = 1280
    DESIGN_HEIGHT = 945

    def __init__(self, page, parent=None):
        super().__init__(parent)
        self.page = page
        self.page.setFixedSize(self.DESIGN_WIDTH, self.DESIGN_HEIGHT)
        self.scene = QGraphicsScene(self)
        self.proxy = self.scene.addWidget(self.page)
        self.setScene(self.scene)
        self.setSceneRect(0, 0, self.DESIGN_WIDTH, self.DESIGN_HEIGHT)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.setBackgroundBrush(QColor('#f6f9fe'))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.viewport().width() <= 0 or self.viewport().height() <= 0:
            return
        factor = min(self.viewport().width() / self.DESIGN_WIDTH, 1.0)
        self.resetTransform()
        self.scale(factor, factor)
        self.verticalScrollBar().setValue(0)


class HomeView(QWidget):
    logout_requested = Signal()

    PAGE_ITEMS = (
        ('Dashboard', 'dashboard', 'home', DashboardView),
        ('Importar datos', 'importar', 'import', ImportDataView),
        ('Productos e inventario', 'productos', 'cube', ProductsView),
        ('Análisis de ventas', 'ventas', 'bars', SalesView),
        ('Segmentación', 'segmentacion', 'people', SegmentationView),
        ('Patrones de compra', 'patrones', 'pattern', PurchasePatternsView),
        ('Estimación de demanda', 'demanda', 'forecast', DemandView),
    )
    INTELLIGENCE_ITEMS = (
        ('Calendario comercial', 'calendario', 'calendar', CalendarView),
        ('Radar de tendencias', 'tendencias', 'radar', TrendsView),
        ('Recomendaciones inteligentes', 'recomendaciones_ia', 'spark', SmartRecommendationsView),
    )
    DECISION_ITEMS = (
        ('Recomendaciones', 'recomendaciones', 'recommend', RecommendationsView),
        ('Abastecimiento', 'abastecimiento', 'supply', SupplyView),
        ('Reportes', 'reportes', 'report', ReportsView),
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics')
        self.setMinimumSize(1120, 700)
        self.resize(1680, 945)
        self.sidebar_collapsed = False
        self._initial_sidebar_state_set = False
        self.setStyleSheet(self._styles())
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        self.pages = QStackedWidget()
        self.page_views = {}
        for _, key, _, view_class in self.PAGE_ITEMS + self.INTELLIGENCE_ITEMS + self.DECISION_ITEMS:
            page = view_class()
            responsive_page = ResponsivePageView(page)
            self.page_views[key] = responsive_page
            self.pages.addWidget(responsive_page)
            self.page_indexes[key] = self.pages.count() - 1
        root.addWidget(self.pages, 1)

    def _build_sidebar(self):
        sidebar = QFrame(objectName='sidebar')
        sidebar.setFixedWidth(242)
        self.sidebar = sidebar
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(2)
        sidebar_header = QWidget(objectName='sidebarHeader')
        sidebar_header.setFixedHeight(68)
        header_layout = QHBoxLayout(sidebar_header)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(2)
        self.brand = BrandWidget()
        self.brand.setMaximumWidth(180)
        self.brand.setContentsMargins(8, 0, 0, 0)
        header_layout.addWidget(self.brand, 1)
        self.compact_logo = LogoMark()
        self.compact_logo.setFixedSize(28, 42)
        self.compact_logo.hide()
        header_layout.addWidget(self.compact_logo)
        self.sidebar_toggle = QPushButton('‹', objectName='sidebarToggle')
        self.sidebar_toggle.setToolTip('Contraer navegación')
        self.sidebar_toggle.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle.setFixedSize(24, 30)
        self.sidebar_toggle.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.sidebar_toggle)
        layout.addWidget(sidebar_header)
        layout.addSpacing(6)

        nav_scroll = QScrollArea(objectName='navScroll')
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_content = QWidget(objectName='navContent')
        nav_layout = QVBoxLayout(nav_content)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)
        nav_scroll.setWidget(nav_content)
        layout.addWidget(nav_scroll, 1)

        self.page_indexes = {}
        self.nav_buttons = {}
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for item in self.PAGE_ITEMS:
            nav_layout.addWidget(self._nav_button(item))

        self.intelligence_button = NavButton('Inteligencia comercial', 'intel', expandable=True)
        self.intelligence_button.clicked.connect(self._toggle_intelligence)
        nav_layout.addWidget(self.intelligence_button)
        self.intelligence_menu = QWidget(objectName='intelligenceMenu')
        submenu = QVBoxLayout(self.intelligence_menu)
        submenu.setContentsMargins(0, 7, 0, 7)
        submenu.setSpacing(5)
        for item in self.INTELLIGENCE_ITEMS:
            submenu.addWidget(self._nav_button(item, child=True))
        self.intelligence_menu.hide()
        self.intelligence_menu.setMinimumHeight(143)
        nav_layout.addWidget(self.intelligence_menu)
        nav_layout.addSpacing(16)
        decision_separator = QFrame(objectName='navSectionDivider')
        decision_separator.setFixedHeight(1)
        nav_layout.addWidget(decision_separator)
        nav_layout.addSpacing(16)

        for item in self.DECISION_ITEMS:
            nav_layout.addWidget(self._nav_button(item))
        self.nav_buttons['dashboard'].setChecked(True)
        nav_layout.addStretch()

        separator = QFrame(objectName='sidebarLine')
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        logout = NavButton('Cerrar sesión', 'logout')
        logout.setCheckable(False)
        logout.clicked.connect(self.logout_requested.emit)
        self.logout_button = logout
        layout.addWidget(logout)
        return sidebar

    def _nav_button(self, item, child=False):
        text, key, kind, _ = item
        button = NavButton(text, kind, child=child)
        self.nav_group.addButton(button)
        self.nav_buttons[key] = button
        button.clicked.connect(lambda checked=False, route=key: self._show_page(route))
        return button

    def _show_page(self, key):
        self.pages.setCurrentIndex(self.page_indexes[key])

    def _toggle_intelligence(self):
        expanded = not self.intelligence_menu.isVisible()
        self.intelligence_menu.setVisible(expanded)
        self.intelligence_button.set_expanded(expanded)

    def _toggle_sidebar(self):
        self._set_sidebar_collapsed(not self.sidebar_collapsed)

    def _set_sidebar_collapsed(self, collapsed):
        self.sidebar_collapsed = collapsed
        self.sidebar.setFixedWidth(84 if collapsed else 242)
        self.brand.setVisible(not collapsed)
        self.compact_logo.setVisible(collapsed)
        self.sidebar_toggle.setText('›' if collapsed else '‹')
        self.sidebar_toggle.setToolTip('Expandir navegación' if collapsed else 'Contraer navegación')
        self.logout_button.set_compact(collapsed)
        for button in self.nav_buttons.values():
            button.set_compact(collapsed)
        self.intelligence_button.set_compact(collapsed)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_sidebar_state_set:
            self._initial_sidebar_state_set = True
            self._set_sidebar_collapsed(self.width() < 1500)

    @staticmethod
    def _styles():
        return '''
            QWidget { font-family: "Segoe UI Variable", "Segoe UI"; }
            QFrame#sidebar { background: #071c38; border: none; }
            QScrollArea#navScroll, QWidget#navContent { background: transparent; border: none; }
            QScrollArea#navScroll QScrollBar:vertical { background: transparent; width: 5px; }
            QScrollArea#navScroll QScrollBar::handle:vertical { background: #35506f; border-radius: 2px; min-height: 28px; }
            QScrollArea#navScroll QScrollBar::add-line:vertical, QScrollArea#navScroll QScrollBar::sub-line:vertical { height: 0; }
            QWidget#intelligenceMenu { background: #19245a; border-radius: 8px; }
            QFrame#sidebarLine { background: #263d59; border: none; }
            QFrame#navSectionDivider { background: #34506f; border: none; margin-left: 12px; margin-right: 12px; }
            QPushButton#sidebarToggle { color: #aebdd2; background: #102b4d; border: 1px solid #294664; border-radius: 7px; font-size: 17px; font-weight: 700; }
            QPushButton#sidebarToggle:hover { color: white; background: #1b3a60; border-color: #526d90; }
            QLabel#sidebarAvatar { color: white; background: #5532f5; border-radius: 23px; font-size: 13px; font-weight: 700; }
            QLabel#accountName { color: white; font-size: 11px; font-weight: 700; }
            QLabel#accountRole { color: #a5b2c7; font-size: 9px; }
        '''


__all__ = ['HomeView']
