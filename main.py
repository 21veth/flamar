import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from PySide6.QtWidgets import QApplication
from views.login_view import LoginView

def main():
    app = QApplication(sys.argv)
    
    login_window = LoginView()
    login_window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()