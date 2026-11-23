"""Entrega única de credenciales y cambio obligatorio antes de abrir el sistema."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from views.usuarios_theme import DIALOG_STYLE


def _copy(text, name='muted'):
    label = QLabel(text, objectName=name)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    return label


class CredencialesDialog(QDialog):
    def __init__(self, usuario, clave, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Usuario creado · Credenciales temporales')
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(_copy('Entrega estas credenciales al usuario', 'sectionTitle'))
        layout.addWidget(_copy('La clave se muestra solo esta vez. No podrás consultarla después.'))
        form = QFormLayout()
        self.usuario = _copy(usuario, 'fieldValue')
        self.usuario.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.clave = QLineEdit(clave, objectName='temporaryPassword')
        self.clave.setReadOnly(True)
        self.clave.setAccessibleName('Contraseña temporal de 8 dígitos')
        form.addRow('Usuario', self.usuario)
        form.addRow('Clave temporal', self.clave)
        layout.addLayout(form)
        layout.addWidget(_copy('Al iniciar sesión deberá elegir una contraseña nueva antes de acceder al sistema.', 'note'))
        self.cerrar = QPushButton('Ya guardé las credenciales', objectName='primary')
        self.cerrar.clicked.connect(self.accept)
        layout.addWidget(self.cerrar)
        self.finished.connect(lambda _: self.clave.setText(''))


class CambioPasswordDialog(QDialog):
    guardar = Signal(str, str)

    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self._ocupado = False
        self.setWindowTitle('Primer acceso · Cambia tu contraseña')
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(_copy('Tu contraseña, solo tuya', 'sectionTitle'))
        layout.addWidget(_copy(f'{usuario}, debes reemplazar la clave temporal antes de entrar.'))
        form = QFormLayout()
        self.nueva = QLineEdit()
        self.confirmacion = QLineEdit()
        for field in (self.nueva, self.confirmacion):
            field.setEchoMode(QLineEdit.Password)
            field.setMaxLength(128)
        self.nueva.setPlaceholderText('8 a 128 caracteres, distinta de la temporal')
        form.addRow('Nueva contraseña', self.nueva)
        form.addRow('Confirmar contraseña', self.confirmacion)
        layout.addLayout(form)
        self.error = _copy('', 'error')
        self.error.hide()
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        self.cancelar = QPushButton('Volver al login', objectName='secondary')
        self.cancelar.setAutoDefault(False)
        self.cancelar.clicked.connect(self.reject)
        self.guardar_button = QPushButton('Guardar y entrar', objectName='primary')
        self.guardar_button.setDefault(True)
        self.guardar_button.clicked.connect(self._enviar)
        buttons.addWidget(self.cancelar)
        buttons.addWidget(self.guardar_button)
        layout.addLayout(buttons)
        self.finished.connect(self._limpiar)

    def _enviar(self):
        if self._ocupado:
            return
        if self.nueva.text() != self.confirmacion.text():
            self.mostrar_error('Las contraseñas no coinciden.')
            return
        if not 8 <= len(self.nueva.text()) <= 128 or not self.nueva.text().strip():
            self.mostrar_error('La nueva contraseña debe tener entre 8 y 128 caracteres y no contener solo espacios.')
            return
        self.error.hide()
        self.guardar.emit(self.nueva.text(), self.confirmacion.text())

    def mostrar_error(self, mensaje):
        self.error.setText(mensaje)
        self.error.show()

    def establecer_ocupado(self, ocupado):
        self._ocupado = ocupado
        for widget in (self.nueva, self.confirmacion, self.guardar_button, self.cancelar):
            widget.setEnabled(not ocupado)

    def _limpiar(self, _resultado):
        self.nueva.setText('')
        self.confirmacion.setText('')

    def reject(self):
        if not self._ocupado:
            super().reject()

    def closeEvent(self, event):
        if self._ocupado:
            event.ignore()
        else:
            super().closeEvent(event)
