from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

class LoginView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics - Login')
        self.setMinimumSize(760, 540)
        self.setStyleSheet('''
            QWidget {
                color: #18324b;
                font-family: "Segoe UI";
            }
            QFrame#page {
                background: #f4f8fc;
            }
            QFrame#brand_panel {
                background: #1261a0;
                border-radius: 22px;
            }
            QFrame#login_card {
                background: #ffffff;
                border: 1px solid #dce8f3;
                border-radius: 22px;
            }
            QLabel#brand_mark {
                color: #1261a0;
                background: #ffffff;
                border-radius: 28px;
                font-size: 26px;
                font-weight: bold;
            }
            QLabel#brand_title {
                color: #ffffff;
                font-size: 25px;
                font-weight: 700;
            }
            QLabel#brand_copy {
                color: #d9ecff;
                font-size: 14px;
                line-height: 1.4;
            }
            QLabel#eyebrow {
                color: #4d83b0;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#login_title {
                color: #173b5c;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#login_subtitle {
                color: #7190aa;
                font-size: 13px;
            }
            QLineEdit {
                background: #f7fbff;
                border: 1px solid #d2e1ee;
                border-radius: 10px;
                padding: 12px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2c8bd1;
                background: #ffffff;
            }
            QToolButton {
                border: none;
                color: #6e8da8;
                padding: 5px;
            }
            QPushButton#login_button {
                background: #1261a0;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 13px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton#login_button:hover {
                background: #0d4e83;
            }
            QLabel#footer {
                color: #8ba1b5;
                font-size: 11px;
            }
        ''')

        page = QFrame(objectName='page')
        layout = QHBoxLayout(page)
        layout.setContentsMargins(34, 34, 34, 34)
        layout.setSpacing(24)

        brand_panel = QFrame(objectName='brand_panel')
        brand_panel.setMinimumWidth(270)
        brand_layout = QVBoxLayout(brand_panel)
        brand_layout.setContentsMargins(30, 34, 30, 30)
        brand_layout.setSpacing(16)

        brand_mark = QLabel('F', objectName='brand_mark')
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_mark.setFixedSize(56, 56)
        brand_layout.addWidget(brand_mark, alignment=Qt.AlignLeft)

        brand_title = QLabel('Flamar\nAnalytics', objectName='brand_title')
        brand_layout.addWidget(brand_title)

        brand_copy = QLabel(
            'Convierte tus datos en decisiones claras y descubre nuevas oportunidades.',
            objectName='brand_copy',
        )
        brand_copy.setWordWrap(True)
        brand_layout.addWidget(brand_copy)
        brand_layout.addStretch()
        brand_layout.addWidget(QLabel('◈  Insights que impulsan tu negocio', objectName='brand_copy'))
        brand_layout.addWidget(QLabel('◈  Una vista simple de todo', objectName='brand_copy'))

        login_card = QFrame(objectName='login_card')
        login_layout = QVBoxLayout(login_card)
        login_layout.setContentsMargins(42, 38, 42, 34)
        login_layout.setSpacing(13)

        login_layout.addWidget(QLabel('ACCESO A LA PLATAFORMA', objectName='eyebrow'))
        login_title = QLabel('¡Hola de nuevo!', objectName='login_title')
        login_layout.addWidget(login_title)
        login_layout.addWidget(QLabel('Ingresa tus datos para continuar.', objectName='login_subtitle'))
        login_layout.addSpacing(12)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText('  Usuario')
        self.user_input.addAction(QApplication.style().standardIcon(QStyle.SP_DirHomeIcon), QLineEdit.LeadingPosition)
        login_layout.addWidget(self.user_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('  Contraseña')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.addAction(QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView), QLineEdit.LeadingPosition)
        self.password_input.addAction('◉', self.toggle_password_visibility)
        login_layout.addWidget(self.password_input)

        login_btn = QPushButton('  Iniciar sesión  ', objectName='login_button')
        login_btn.clicked.connect(self.handle_login)
        login_layout.addWidget(login_btn)
        login_layout.addSpacing(12)
        login_layout.addWidget(QLabel('Tus datos están protegidos', objectName='footer'), alignment=Qt.AlignCenter)

        layout.addWidget(brand_panel, 2)
        layout.addWidget(login_card, 3)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(page)

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Completa todos los campos')
            return
        
        QMessageBox.information(self, 'Éxito', f'Bienvenido {username}!')