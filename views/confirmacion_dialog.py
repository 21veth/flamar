from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from views.usuarios_theme import DIALOG_STYLE


class ConfirmacionDialog(QDialog):
    """Confirmación no bloqueante: cerrar, Escape y Cancelar no ejecutan acciones."""

    def __init__(self, titulo, texto, accion, parent=None, peligro=False):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setWindowModality(Qt.WindowModal)
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumWidth(420)
        self.resize(480, 220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        heading = QLabel(titulo, objectName='sectionTitle')
        heading.setTextFormat(Qt.PlainText)
        layout.addWidget(heading)
        mensaje = QLabel(texto)
        mensaje.setTextFormat(Qt.PlainText)
        mensaje.setWordWrap(True)
        layout.addWidget(mensaje, 1)
        botones = QHBoxLayout()
        botones.addStretch()
        self.cancelar = QPushButton('Cancelar', objectName='secondary')
        self.cancelar.setDefault(True)
        self.cancelar.clicked.connect(self.reject)
        self.confirmar = QPushButton(accion, objectName='danger' if peligro else 'primary')
        self.confirmar.setAutoDefault(False)
        self.confirmar.clicked.connect(self.accept)
        botones.addWidget(self.cancelar)
        botones.addWidget(self.confirmar)
        layout.addLayout(botones)
