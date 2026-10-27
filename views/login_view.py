from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from views.home_view import HomeView
from views.ui_components import BrandWidget, LogoMark


class HeroPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, objectName='hero')
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 38, 48, 42)
        layout.addWidget(BrandWidget())
        layout.addStretch(2)

        eyebrow = QLabel('INTELIGENCIA COMERCIAL', objectName='heroEyebrow')
        layout.addWidget(eyebrow)
        title = QLabel('Inventario bajo control.\nDecisiones con visión.', objectName='heroTitle')
        title.setWordWrap(True)
        layout.addWidget(title)
        subtitle = QLabel(
            'Convierte tus ventas, temporadas y señales del mercado en decisiones claras para comprar mejor y vender más.',
            objectName='heroSubtitle',
        )
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(570)
        layout.addWidget(subtitle)
        layout.addSpacing(26)

        features = QHBoxLayout()
        features.setSpacing(10)
        for icon, value, label in (
            ('↗', 'Demanda', 'Pronósticos precisos'),
            ('◇', 'Inventario', 'Alertas oportunas'),
            ('◎', 'Tendencias', 'Señales del mercado'),
        ):
            card = QFrame(objectName='featureCard')
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(2)
            card_layout.addWidget(QLabel(icon, objectName='featureIcon'))
            card_layout.addWidget(QLabel(value, objectName='featureValue'))
            card_layout.addWidget(QLabel(label, objectName='featureLabel'))
            features.addWidget(card)
        layout.addLayout(features)
        layout.addStretch()
        layout.addWidget(QLabel('FLAMAR ANALYTICS  ·  2026', objectName='heroFooter'))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor('#061a36'))
        gradient.setColorAt(.58, QColor('#10245a'))
        gradient.setColorAt(1, QColor('#3f24bc'))
        painter.fillRect(self.rect(), gradient)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(119, 91, 255, 35))
        painter.drawEllipse(QPointF(self.width() * .90, self.height() * .12), 210, 210)
        painter.setBrush(QColor(30, 174, 238, 22))
        painter.drawEllipse(QPointF(self.width() * .10, self.height() * .85), 175, 175)
        super().paintEvent(event)


class LoginView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics - Iniciar sesión')
        self.setMinimumSize(720, 560)
        self.resize(1280, 760)
        self.home_view = None
        self.setStyleSheet(self._styles())

        self.root = QHBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.hero = HeroPanel()
        self.root.addWidget(self.hero, 6)
        self.root.addWidget(self._build_access_panel(), 5)

    def _build_access_panel(self):
        panel = QFrame(objectName='accessPanel')
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(52, 32, 52, 30)
        outer.addStretch()

        self.mobile_brand = QWidget(objectName='mobileBrand')
        brand_layout = QHBoxLayout(self.mobile_brand)
        brand_layout.setContentsMargins(0, 0, 0, 16)
        mark = LogoMark()
        mark.setFixedSize(42, 42)
        brand_layout.addWidget(mark)
        brand_layout.addWidget(QLabel('FLAMAR', objectName='mobileBrandName'))
        brand_layout.addStretch()
        self.mobile_brand.hide()
        outer.addWidget(self.mobile_brand)

        card = QFrame(objectName='loginCard')
        card.setMinimumWidth(430)
        card.setMaximumWidth(480)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(18, 35, 70, 32))
        card.setGraphicsEffect(shadow)
        form = QVBoxLayout(card)
        form.setContentsMargins(38, 36, 38, 34)
        form.setSpacing(9)

        form.addWidget(QLabel('Bienvenido de nuevo', objectName='loginTitle'))
        intro = QLabel('Ingresa tus credenciales para continuar a tu espacio de análisis.', objectName='loginSubtitle')
        intro.setWordWrap(True)
        form.addWidget(intro)
        form.addSpacing(18)

        form.addWidget(QLabel('Usuario', objectName='fieldLabel'))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText('Ingresa tu usuario')
        self.user_input.setClearButtonEnabled(True)
        form.addWidget(self.user_input)
        form.addSpacing(8)

        form.addWidget(QLabel('Contraseña', objectName='fieldLabel'))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Ingresa tu contraseña')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        form.addWidget(self.password_input)

        options = QHBoxLayout()
        remember = QCheckBox('Mantener sesión iniciada')
        remember.setChecked(True)
        options.addWidget(remember)
        options.addStretch()
        forgot = QPushButton('¿Olvidaste tu contraseña?', objectName='linkButton')
        forgot.setCursor(Qt.PointingHandCursor)
        forgot.clicked.connect(self._show_recovery)
        options.addWidget(forgot)
        form.addLayout(options)
        form.addSpacing(12)

        login = QPushButton('Entrar a Flamar  →', objectName='loginButton')
        login.setCursor(Qt.PointingHandCursor)
        login.clicked.connect(self.handle_login)
        form.addWidget(login)
        form.addSpacing(14)

        security = QLabel('◉  Acceso seguro y datos protegidos', objectName='security')
        security.setAlignment(Qt.AlignCenter)
        form.addWidget(security)
        outer.addWidget(card, alignment=Qt.AlignHCenter)
        outer.addStretch()
        outer.addWidget(QLabel('© 2026 Flamar Analytics', objectName='copyright'), alignment=Qt.AlignHCenter)
        return panel

    def resizeEvent(self, event):
        super().resizeEvent(event)
        narrow = self.width() < 980
        self.hero.setVisible(not narrow)
        self.mobile_brand.setVisible(narrow)

    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, 'Campos incompletos', 'Completa el usuario y la contraseña.')
            return
        if self.home_view is None:
            self.home_view = HomeView()
            self.home_view.logout_requested.connect(self.handle_logout)
        self.home_view.show()
        self.close()

    def handle_logout(self):
        self.home_view.hide()
        self.password_input.clear()
        self.show()
        self.activateWindow()

    def _show_recovery(self):
        QMessageBox.information(self, 'Recuperar acceso', 'Contacta al administrador de tu organización para restablecer tu contraseña.')

    @staticmethod
    def _styles():
        return '''
            QWidget { color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; }
            QFrame#hero { border: none; }
            QLabel#heroEyebrow { color: #8f80ff; font-size: 11px; font-weight: 800; letter-spacing: 2px; }
            QLabel#heroTitle { color: white; font-size: 36px; font-weight: 850; }
            QLabel#heroSubtitle { color: #bdcbe0; font-size: 14px; }
            QFrame#featureCard { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.13); border-radius: 12px; }
            QLabel#featureIcon { color: #8d7bff; font-size: 18px; font-weight: 800; }
            QLabel#featureValue { color: white; font-size: 12px; font-weight: 750; }
            QLabel#featureLabel { color: #aebed5; font-size: 9px; }
            QLabel#heroFooter { color: #879ab5; font-size: 9px; font-weight: 700; letter-spacing: 1px; }
            QFrame#accessPanel { background: #f6f8fc; border: none; }
            QFrame#loginCard { background: white; border: 1px solid #e1e6ef; border-radius: 18px; }
            QLabel#loginTitle { color: #07132f; font-size: 27px; font-weight: 850; }
            QLabel#loginSubtitle { color: #6c7990; font-size: 12px; }
            QLabel#fieldLabel { color: #17233b; font-size: 11px; font-weight: 700; }
            QLineEdit { color: #14213a; background: #fbfcfe; border: 1px solid #d8e0eb; border-radius: 9px; padding: 14px 14px; font-size: 12px; }
            QLineEdit:focus { background: white; border: 2px solid #5b3df5; }
            QCheckBox { color: #536178; font-size: 9px; spacing: 7px; }
            QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #bac5d5; border-radius: 4px; background: white; }
            QCheckBox::indicator:checked { background: #5838f3; border-color: #5838f3; }
            QPushButton#linkButton { color: #5235ec; background: transparent; border: none; font-size: 9px; font-weight: 650; }
            QPushButton#loginButton { color: white; background: #5534f3; border: none; border-radius: 9px; padding: 13px; font-size: 12px; font-weight: 750; }
            QPushButton#loginButton:hover { background: #4425dd; }
            QPushButton#loginButton:pressed { background: #3519bd; }
            QLabel#security, QLabel#copyright { color: #8a96a8; font-size: 9px; }
            QWidget#mobileBrand { background: transparent; }
            QLabel#mobileBrandName { color: #17234a; font-size: 20px; font-weight: 850; letter-spacing: 1px; }
        '''


__all__ = ['LoginView']
