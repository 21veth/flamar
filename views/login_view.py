from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
QLineEdit, QPushButton, QMessageBox)
from PySide6.QtCore import Qt

class LoginView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flamar Analytics - Login')
        self.setMinimumSize(600, 500)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        
        # Título
        title = QLabel('🔐 Flamar Analytics')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        layout.addWidget(title)
        
        # Campo usuario
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText('Usuario')
        layout.addWidget(self.user_input)
        
        # Campo contraseña
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Contraseña')
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Botón login
        login_btn = QPushButton('Iniciar Sesión')
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)
        
        self.setLayout(layout)
    
    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Completa todos los campos')
            return
        
        QMessageBox.information(self, 'Éxito', f'Bienvenido {username}!')