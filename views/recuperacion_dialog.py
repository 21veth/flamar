from math import ceil
from time import monotonic

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QFrame, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from controllers.recuperacion_controller import RecuperacionController
from config.recuperacion import ESPERA_REENVIO_SEGUNDOS
from views.usuarios_theme import DIALOG_STYLE


def _label(text, name=None, wrap=False):
    label = QLabel(text)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(wrap)
    if name:
        label.setObjectName(name)
    return label


ESTADOS = {
    'codigo_enviado': 'Autorizada · Falta validar código', 'pendiente': 'En espera de autorización',
    'aprobada': 'Código validado', 'rechazada': 'Denegada', 'completada': 'Contraseña cambiada',
    'expirada': 'Caducada', 'bloqueada': 'Intentos agotados', 'envio_fallido': 'Autorizada · Correo pendiente',
    'cancelada': 'Cancelada', 'enviando': 'Autorizada · Enviando correo', 'no_disponible': 'No disponible',
}


def cabecera(layout, titulo, texto):
    panel = QFrame(objectName='dialogHeader')
    content = QVBoxLayout(panel)
    content.setContentsMargins(22, 18, 22, 18)
    content.addWidget(_label('ZEYVER  /  RECUPERACIÓN DE ACCESO', 'dialogKicker'))
    content.addWidget(_label(titulo, 'dialogTitle'))
    content.addWidget(_label(texto, 'dialogCopy', True))
    layout.addWidget(panel)


class RecuperacionDialog(QDialog):
    def __init__(self, usuario='', controller=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Recuperar contraseña · Zeyver')
        self.setStyleSheet(DIALOG_STYLE)
        self.resize(560, 640)
        self.setMinimumWidth(500)
        self.controller = controller if controller is not None else RecuperacionController(parent=self)
        self.token = None
        self._ocupado = False
        self._canales = {}
        self._reenvio_hasta = 0
        self._retomando = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        cabecera(layout, 'Recupera tu acceso', 'Primero autorización del administrador; después tu código por correo.')
        self.pasos = QStackedWidget()
        layout.addWidget(self.pasos, 1)

        pagina, content = self._pagina('01  /  SOLICITA AUTORIZACIÓN')
        self.usuario = QLineEdit(usuario, placeholderText='Tu nombre de usuario')
        self.usuario.setMaxLength(100)
        content.addWidget(_label('Usuario', 'fieldCaption'))
        content.addWidget(self.usuario)
        self.configuracion = _label('Comprobando la configuración del correo…', 'note', True)
        content.addWidget(self.configuracion)
        self.solicitar = QPushButton('Solicitar recuperación  →', objectName='primary')
        self.solicitar.clicked.connect(self._solicitar)
        self.solicitar.setEnabled(False)
        content.addWidget(self.solicitar)
        self.retomar = QPushButton('Retomar con mi código', objectName='secondary')
        self.retomar.clicked.connect(self._mostrar_retomar)
        content.addWidget(self.retomar)
        content.addWidget(_label('Solo se usa el correo registrado por el administrador. '
                                 'La solicitud dura 3 horas y se guarda aunque cierres el sistema. '
                                 'Recibirás el código únicamente después de que la autoricen.', 'muted', True))
        content.addStretch()

        pagina, content = self._pagina('03  /  VALIDA TU CÓDIGO AUTORIZADO')
        self.aviso_envio = _label('', 'note', True)
        content.addWidget(self.aviso_envio)
        self.codigo = QLineEdit(placeholderText='8 letras y números')
        self.codigo.setMaxLength(8)
        self.codigo.setEchoMode(QLineEdit.Password)
        content.addWidget(self.codigo)
        self.validar = QPushButton('Validar código', objectName='primary')
        self.validar.clicked.connect(self._validar_codigo)
        content.addWidget(self.validar)
        self.reintentar = QPushButton('Solicitar otro código', objectName='secondary')
        self.reintentar.clicked.connect(self._reiniciar)
        content.addWidget(self.reintentar)
        content.addStretch()

        pagina, content = self._pagina('02  /  ESPERA LA AUTORIZACIÓN')
        self.estado_label = _label('Tu solicitud queda en espera del administrador. '
                                   'Todavía no se ha enviado ningún código.', 'note', True)
        content.addWidget(self.estado_label)
        content.addWidget(_label('La solicitud caduca a las 3 horas desde que la pediste. '
                                 'Puedes cerrar la ventana y entrar como administrador. '
                                 'Cuando la autoricen recibirás un código por correo; vuelve al login '
                                 'y elige «Retomar con mi código» para continuar.', 'muted', True))
        self.consultar = QPushButton('Consultar estado', objectName='secondary')
        self.consultar.clicked.connect(self._consultar)
        content.addWidget(self.consultar)
        self.reiniciar = QPushButton('Iniciar otra solicitud', objectName='secondary')
        self.reiniciar.clicked.connect(self._reiniciar)
        content.addWidget(self.reiniciar)
        content.addStretch()

        pagina, content = self._pagina('04  /  ESTABLECE TU NUEVA CONTRASEÑA')
        content.addWidget(_label('Solicitud aprobada. Elige una contraseña de 6 a 128 caracteres.', 'note', True))
        self.password = QLineEdit(placeholderText='Nueva contraseña')
        self.confirmacion = QLineEdit(placeholderText='Confirmar contraseña')
        for campo in (self.password, self.confirmacion):
            campo.setEchoMode(QLineEdit.Password)
            campo.setMaxLength(128)
            content.addWidget(campo)
        self.guardar = QPushButton('Cambiar contraseña', objectName='primary')
        self.guardar.clicked.connect(self._guardar)
        content.addWidget(self.guardar)
        content.addStretch()

        pagina, content = self._pagina('ACCESO RECUPERADO')
        content.addWidget(_label('Tu contraseña se cambió correctamente. '
                                 'Ya puedes iniciar sesión con la nueva contraseña.', 'note', True))
        content.addStretch()
        terminar = QPushButton('Volver al login', objectName='primary')
        terminar.clicked.connect(self.accept)
        content.addWidget(terminar)

        self.error = _label('', 'error', True)
        self.error.hide()
        layout.addWidget(self.error)
        cerrar = QPushButton('Cerrar', objectName='secondary')
        cerrar.clicked.connect(self.reject)
        layout.addWidget(cerrar)
        self.timer = QTimer(self)
        self.timer.setInterval(10000)
        self.timer.timeout.connect(self._consultar)
        self._reenvio_timer = QTimer(self)
        self._reenvio_timer.setInterval(250)
        self._reenvio_timer.timeout.connect(self._actualizar_reenvio)
        self.controller.actualizado.connect(self._recibir)
        self.controller.fallo.connect(self._fallo)
        self.controller.ocupado.connect(self._establecer_ocupado)
        self.finished.connect(self._limpiar)
        self._init_timer = QTimer(self)
        self._init_timer.setSingleShot(True)
        self._init_timer.timeout.connect(lambda: self._ejecutar('configuracion'))
        self._init_timer.start(0)

    def _pagina(self, titulo):
        pagina = QWidget()
        content = QVBoxLayout(pagina)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(12)
        content.addWidget(_label(titulo, 'formSection', True))
        self.pasos.addWidget(pagina)
        return pagina, content

    def _ejecutar(self, accion, **datos):
        if not self._ocupado:
            self.error.hide()
            return self.controller.ejecutar(accion, **datos)
        return False

    def _actualizar_correo(self):
        disponible = self._canales.get('correo', False)
        self.configuracion.setText('La solicitud se guardará para el administrador. No se enviará ningún correo '
                                  'hasta que la autorice.' if disponible else 'Puedes registrar la solicitud. '
                                  'El administrador deberá configurar el correo antes de autorizar el envío del código.')
        self._actualizar_reenvio()

    def _segundos_reenvio(self):
        return max(0, ceil(self._reenvio_hasta - monotonic()))

    def _actualizar_reenvio(self):
        segundos = self._segundos_reenvio()
        espera = f' ({segundos // 60:02d}:{segundos % 60:02d})' if segundos else ''
        habilitado = not self._ocupado and not segundos
        self.reintentar.setText('Solicitar otro código' + espera)
        self.reintentar.setEnabled(habilitado)
        self.reiniciar.setText('Iniciar otra solicitud' + espera)
        self.reiniciar.setEnabled(habilitado)
        self.solicitar.setText('Solicitar recuperación' + espera if segundos else 'Solicitar recuperación  →')
        self.solicitar.setEnabled(habilitado)
        if not segundos:
            self._reenvio_timer.stop()

    def _solicitar(self):
        if self._segundos_reenvio():
            return
        self._ejecutar('solicitar', usuario=self.usuario.text(), canal='correo')

    def _consultar(self):
        if self.token:
            self._ejecutar('estado', token=self.token)

    def _mostrar_retomar(self):
        if self._ocupado:
            return
        if not self.usuario.text().strip():
            self._fallo('Introduce tu nombre de usuario para retomar la solicitud.')
            return
        self.error.hide()
        self.timer.stop()
        self._retomando = True
        self.token = None
        self.codigo.clear()
        self.aviso_envio.setText('Introduce el código que recibiste por correo. Podrás continuar la misma '
                                 'solicitud aunque hayas cerrado la ventana o iniciado sesión como administrador. '
                                 'Usa el código del correo más reciente. El plazo de 3 horas no se reinicia.')
        self.validar.setText('Retomar solicitud')
        self.pasos.setCurrentIndex(1)
        self.codigo.setFocus()

    def _validar_codigo(self):
        if self._retomando:
            self._ejecutar('retomar', usuario=self.usuario.text(), codigo=self.codigo.text())
        else:
            self._ejecutar('verificar', token=self.token, codigo=self.codigo.text())

    def _guardar(self):
        if self.password.text() != self.confirmacion.text():
            self._fallo('Las contraseñas no coinciden.')
            return
        self._ejecutar('restablecer', token=self.token, contrasena=self.password.text())

    def _reiniciar(self):
        if self._ocupado or self._segundos_reenvio():
            return
        self.timer.stop()
        self.token = None
        self.codigo.clear()
        self.password.clear()
        self.confirmacion.clear()
        self.error.hide()
        self._retomando = False
        self.validar.setText('Validar código')
        self.pasos.setCurrentIndex(0)

    def _recibir(self, resultado):
        accion = resultado['accion']
        if accion == 'configuracion':
            self._canales = resultado['canales']
            self._actualizar_correo()
        elif accion == 'solicitar':
            self.token = resultado['token']
            self._retomando = False
            self.validar.setText('Validar código')
            self._reenvio_hasta = monotonic() + ESPERA_REENVIO_SEGUNDOS
            self._reenvio_timer.start()
            self._actualizar_reenvio()
            self.estado_label.setText(resultado['mensaje'])
            self.pasos.setCurrentIndex(2)
            self.timer.start()
        elif accion in ('verificar', 'estado', 'retomar'):
            if accion == 'retomar':
                self.token = resultado['token']
                self._retomando = False
            estado = resultado['estado']
            if estado == 'completada':
                self._limpiar()
                self.pasos.setCurrentIndex(4)
            elif estado == 'aprobada':
                self.timer.stop()
                self.codigo.clear()
                self.pasos.setCurrentIndex(3)
            elif estado == 'pendiente':
                self.estado_label.setText('Solicitud en espera de autorización. Puedes cerrar el sistema; '
                                          'el administrador la recibirá aunque no estés conectado. Aún no se ha enviado el código.')
                self.pasos.setCurrentIndex(2)
                self.timer.start()
            elif estado == 'codigo_enviado':
                self.timer.stop()
                self.aviso_envio.setText('El administrador autorizó tu solicitud y el servidor aceptó el correo. '
                                         'Revisa tu bandeja y el correo no deseado e introduce el código. '
                                         'La solicitud mantiene su vigencia original de 3 horas.')
                self.pasos.setCurrentIndex(1)
                self.codigo.setFocus()
            elif estado in ('enviando', 'envio_fallido'):
                self.estado_label.setText('La solicitud está autorizada. Se está enviando el código por correo.'
                                          if estado == 'enviando' else 'La solicitud está autorizada y guardada, '
                                          'pero el correo no pudo enviarse. El administrador puede reintentar el envío. '
                                          'No necesitas mantener abierto el sistema.')
                self.pasos.setCurrentIndex(2)
                self.timer.start()
            else:
                self.timer.stop()
                self.pasos.setCurrentIndex(2)
                self.estado_label.setText('Estado: ' + ESTADOS.get(estado, 'No disponible') + '. Puedes iniciar otra solicitud si lo necesitas.')
        elif accion == 'restablecer':
            self._limpiar()
            self.pasos.setCurrentIndex(4)

    def _fallo(self, mensaje):
        self.error.setText(mensaje)
        self.error.show()

    def _establecer_ocupado(self, ocupado):
        self._ocupado = ocupado
        self.pasos.setEnabled(not ocupado)
        self._actualizar_correo()

    def _limpiar(self, *_):
        self._init_timer.stop()
        self.timer.stop()
        self._reenvio_timer.stop()
        self._reenvio_hasta = 0
        self._retomando = False
        self.token = None
        self.codigo.clear()
        self.password.clear()
        self.confirmacion.clear()
