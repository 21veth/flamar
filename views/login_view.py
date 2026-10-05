from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from views.home_view import HomeView
from views.ui_components import BrandWidget


class LoginView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics - Inicio de sesión')
        self.setMinimumSize(980, 620)
        self.resize(1360, 760)
        self.home_view = None
        self.setStyleSheet(self._styles())

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)

    def _build_sidebar(self):
        sidebar = QFrame(objectName='sidebar')
        sidebar.setFixedWidth(240)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(8)
        layout.addWidget(BrandWidget())
        layout.addSpacing(28)
        for icon, text, active in (
            ('⌂', 'Inicio de sesión', True), ('▦', 'Panel principal', False),
            ('▥', 'Reportes', False), ('♙', 'Consumidores', False),
            ('◉', 'Segmentaciones', False), ('↗', 'Comportamientos', False),
            ('✦', 'Predicciones', False), ('☆', 'Recomendaciones', False),
            ('⚙', 'Configuración', False), ('?', 'Ayuda', False),
        ):
            item = QLabel(f'{icon}    {text}', objectName='side_active' if active else 'side_item')
            item.setFixedHeight(42)
            item.setAlignment(Qt.AlignVCenter)
            layout.addWidget(item)
        layout.addStretch()
        line = QFrame(objectName='line')
        line.setFixedHeight(1)
        layout.addWidget(line)
        account = QHBoxLayout()
        avatar = QLabel('AA', objectName='avatar')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(38, 38)
        account.addWidget(avatar)
        detail = QVBoxLayout()
        detail.setSpacing(0)
        detail.addWidget(QLabel('Administrador', objectName='account_name'))
        detail.addWidget(QLabel('admin@flamar.com', objectName='account_email'))
        account.addLayout(detail)
        layout.addLayout(account)
        return sidebar

    def _build_content(self):
        content = QFrame(objectName='content')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 24, 40, 28)
        layout.addStretch()

        brand = QLabel('▥  FLAMAR', objectName='main_brand')
        brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand)
        caption = QLabel('A N A L Y T I C S', objectName='main_caption')
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(caption)
        layout.addSpacing(28)

        card = QFrame(objectName='login_card')
        card.setFixedWidth(470)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 30, 34, 28)
        card_layout.setSpacing(10)
        title = QLabel('Iniciar sesión', objectName='login_title')
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)
        subtitle = QLabel('Accede a tu cuenta para analizar el comportamiento\nde los consumidores.', objectName='login_subtitle')
        subtitle.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(14)
        card_layout.addWidget(QLabel('Usuario', objectName='field_label'))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText('  Ingresa tu usuario')
        self.user_input.setClearButtonEnabled(True)
        card_layout.addWidget(self.user_input)
        card_layout.addSpacing(6)
        card_layout.addWidget(QLabel('Contraseña', objectName='field_label'))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('  Ingresa tu contraseña')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.password_input)

        options = QHBoxLayout()
        remember = QCheckBox('Recordar sesión')
        remember.setChecked(True)
        options.addWidget(remember)
        options.addStretch()
        forgot = QPushButton('¿Olvidaste tu contraseña?', objectName='link_button')
        forgot.setCursor(Qt.PointingHandCursor)
        options.addWidget(forgot)
        card_layout.addLayout(options)
        card_layout.addSpacing(6)
        login_button = QPushButton('Iniciar sesión', objectName='login_button')
        login_button.setCursor(Qt.PointingHandCursor)
        login_button.clicked.connect(self.handle_login)
        card_layout.addWidget(login_button)
        card_layout.addSpacing(10)
        footer = QLabel('▣  © 2026 Flamar Analytics  ·  Todos los derechos reservados', objectName='footer')
        footer.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(footer)
        layout.addWidget(card, alignment=Qt.AlignHCenter)
        layout.addStretch()
        return content

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

    @staticmethod
    def _styles():
        return '''
            QWidget { color: #0b1739; font-family: "Segoe UI Variable", "Segoe UI"; }
            QFrame#sidebar { background: #071b37; }
            QLabel#side_item, QLabel#side_active { color: #e1e8f3; font-size: 12px; padding: 0 12px; border-radius: 8px; }
            QLabel#side_active { color: white; background: #553cff; font-weight: 700; }
            QFrame#line { background: #203752; border: none; }
            QLabel#avatar { color: white; background: #553cff; border-radius: 19px; font-size: 11px; font-weight: 700; }
            QLabel#account_name { color: white; font-size: 11px; font-weight: 700; }
            QLabel#account_email { color: #91a3ba; font-size: 9px; }
            QFrame#content { background: #f7f9ff; }
            QLabel#main_brand { color: #4932ee; font-size: 30px; font-weight: 850; letter-spacing: 1px; }
            QLabel#main_caption { color: #6151ed; font-size: 12px; font-weight: 800; letter-spacing: 4px; }
            QFrame#login_card { background: white; border: 1px solid #dce2eb; border-radius: 16px; }
            QLabel#login_title { color: #080d1c; font-size: 24px; font-weight: 800; }
            QLabel#login_subtitle { color: #687891; font-size: 12px; }
            QLabel#field_label { color: #111827; font-size: 11px; font-weight: 700; }
            QLineEdit { background: white; color: #111827; border: 1px solid #ccd5e2; border-radius: 7px; padding: 11px; font-size: 12px; }
            QLineEdit:focus { border: 2px solid #5a43f5; }
            QCheckBox { color: #253047; font-size: 11px; spacing: 7px; }
            QCheckBox::indicator { width: 15px; height: 15px; }
            QCheckBox::indicator:checked { background: #553cff; border: 1px solid #553cff; border-radius: 3px; }
            QPushButton#link_button { color: #4d35f3; background: transparent; border: none; font-size: 11px; }
            QPushButton#login_button { color: white; background: #553cff; border: none; border-radius: 7px; padding: 12px; font-size: 13px; font-weight: 700; }
            QPushButton#login_button:hover { background: #442be8; }
            QPushButton#login_button:pressed { background: #3922ce; }
            QLabel#footer { color: #8793a8; font-size: 9px; }
        '''
