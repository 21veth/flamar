from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QBoxLayout, QCheckBox, QComboBox, QDialog, QFormLayout,
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from controllers.usuarios_controller import UsuariosController
from views.tabla_paginada import TablaPaginada
from views.confirmacion_dialog import ConfirmacionDialog
from services.usuarios_service import ROLES, UsuariosService
from utils.fotos_perfil import leer_foto
from views.avatar_usuario import AvatarUsuario
from views.usuarios_theme import COLORS, DIALOG_STYLE, USERS_STYLE, UserDelegate, initials
from views.solicitudes_recuperacion_view import SolicitudesRecuperacionView
from views.ficha_acceso import FichaAcceso
from views.password_dialogs import CredencialesDialog


def _label(text, name=None, wrap=False):
    label = QLabel(text)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(wrap)
    if name:
        label.setObjectName(name)
    return label


def _rule():
    rule = QFrame(objectName='rule')
    rule.setFixedHeight(1)
    return rule


class UsuarioDialog(QDialog):
    guardar = Signal(dict)

    def __init__(self, sesion, registro=None, parent=None):
        super().__init__(parent)
        self.registro = registro
        self._foto_cambiada = False
        self._foto_seleccionada = registro.get('foto_perfil') if registro else None
        self._propio = registro is not None and registro['id_usuario'] == sesion.id_usuario
        self.setWindowTitle('Editar usuario' if registro else 'Nuevo usuario')
        self.setMinimumWidth(540)
        self.resize(580, 640)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        header = QFrame(objectName='dialogHeader')
        heading = QVBoxLayout(header)
        heading.setContentsMargins(22, 19, 22, 19)
        heading.addWidget(_label('ZEYVER  /  CONTROL DE ACCESO', 'dialogKicker'))
        heading.addWidget(_label(self.windowTitle(), 'dialogTitle'))
        heading.addWidget(_label('Un lugar en el equipo. Los permisos adecuados.', 'dialogCopy'))
        layout.addWidget(header)
        self.form_scroll = QScrollArea(objectName='usersScroll')
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        form_content = QWidget(objectName='usersCanvas')
        fields = QVBoxLayout(form_content)
        fields.setContentsMargins(0, 0, 10, 0)
        fields.setSpacing(14)
        self.form_scroll.setWidget(form_content)
        layout.addWidget(self.form_scroll, 1)
        fields.addWidget(_label('01  /  IDENTIDAD Y PERMISOS', 'formSection'))
        form = QFormLayout()
        form.setSpacing(12)
        self.usuario = QLineEdit()
        self.usuario.setMaxLength(100)
        photo_row = QHBoxLayout()
        photo_row.setSpacing(16)
        self.foto = AvatarUsuario(initials(registro['usuario']) if registro else '?')
        self.foto.setFixedSize(84, 84)
        self.foto.set_foto(self._foto_seleccionada)
        photo_row.addWidget(self.foto)
        photo_copy = QVBoxLayout()
        photo_copy.addWidget(_label('Foto de perfil · Opcional', 'fieldCaption'))
        photo_buttons = QHBoxLayout()
        self.elegir_foto = QPushButton('Elegir foto', objectName='secondary')
        self.elegir_foto.setAutoDefault(False)
        self.elegir_foto.clicked.connect(self._seleccionar_foto)
        self.quitar_foto = QPushButton('Quitar foto', objectName='secondary')
        self.quitar_foto.setAutoDefault(False)
        self.quitar_foto.setEnabled(bool(self._foto_seleccionada))
        self.quitar_foto.clicked.connect(self._quitar_foto)
        photo_buttons.addWidget(self.elegir_foto)
        photo_buttons.addWidget(self.quitar_foto)
        photo_buttons.addStretch()
        photo_copy.addLayout(photo_buttons)
        photo_copy.addWidget(_label('JPG, PNG o WebP · Máximo 10 MB. Se recorta al centro para el carnet.', 'muted', True))
        photo_row.addLayout(photo_copy, 1)
        fields.addLayout(photo_row)
        self.usuario.textChanged.connect(lambda text: self.foto.setText(initials(text)))
        self.rol = QComboBox()
        for rol in ROLES:
            self.rol.addItem(rol.capitalize(), rol)
        self.activo = QCheckBox('Cuenta activa')
        self.activo.setChecked(True)
        form.addRow('Usuario', self.usuario)
        form.addRow('Rol', self.rol)
        form.addRow('Estado', self.activo)
        fields.addLayout(form)
        fields.addWidget(_rule())
        fields.addWidget(_label('02  /  DATOS DE CONTACTO', 'formSection'))
        contacto = QFormLayout()
        contacto.setSpacing(12)
        self.correo = QLineEdit(placeholderText='nombre@dominio.com')
        self.correo.setMaxLength(254)
        self.telefono = QLineEdit(placeholderText='+51 987 654 321')
        self.telefono.setMaxLength(40)
        self.telefono.setToolTip('Número internacional con + y código de país, de 8 a 15 dígitos.')
        contacto.addRow('Correo electrónico *', self.correo)
        contacto.addRow('Teléfono *', self.telefono)
        fields.addLayout(contacto)
        fields.addWidget(_label('* Campos obligatorios. El correo se usa para recuperar la contraseña y el teléfono para contacto.', 'muted', True))
        fields.addWidget(_rule())
        fields.addWidget(_label('03  /  SEGURIDAD DE LA CUENTA', 'formSection'))
        fields.addWidget(_label(
            'Las contraseñas no se pueden consultar ni modificar desde este formulario.' if registro else
            'Al crear la cuenta se generará una clave temporal aleatoria de 8 dígitos. Se mostrará una sola vez y el usuario deberá cambiarla al iniciar sesión.',
            'note', True))
        if registro:
            self.usuario.setText(registro['usuario'])
            self.rol.setCurrentIndex(self.rol.findData(registro['rol']))
            self.activo.setChecked(registro['activo'])
            self.correo.setText(registro.get('correo') or '')
            self.telefono.setText(registro.get('telefono') or '')
            if self._propio:
                self.rol.setEnabled(False)
                self.activo.setEnabled(False)
                fields.addWidget(_label('Tu acceso está protegido. Al guardar tu cuenta deberás volver a iniciar sesión.', 'note', True))
        else:
            self.rol.setCurrentIndex(self.rol.findData('trabajador'))
        fields.addStretch()
        self.error = _label('', 'error', wrap=True)
        self.error.hide()
        layout.addWidget(self.error)
        botones = QHBoxLayout()
        botones.addStretch()
        self.cancelar = QPushButton('Cancelar', objectName='secondary')
        self.cancelar.setAutoDefault(False)
        self.cancelar.clicked.connect(self.reject)
        self.guardar_button = QPushButton('Guardar usuario  →', objectName='primary')
        self.guardar_button.setDefault(True)
        self.guardar_button.clicked.connect(self._enviar)
        botones.addWidget(self.cancelar)
        botones.addWidget(self.guardar_button)
        layout.addLayout(botones)

    def _seleccionar_foto(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Elegir foto de perfil', '',
                                             'Imágenes (*.jpg *.jpeg *.png *.webp)')
        if not path:
            return
        try:
            image = leer_foto(path)
        except ValueError as error:
            self.error.setText(str(error))
            self.error.show()
            return
        self._foto_seleccionada = path
        self._foto_cambiada = True
        self.foto.set_foto(path, image)
        self.quitar_foto.setEnabled(True)
        self.error.clear()
        self.error.hide()

    def _quitar_foto(self):
        self._foto_seleccionada = None
        self._foto_cambiada = True
        self.foto.set_foto(None)
        self.quitar_foto.setEnabled(False)

    def _enviar(self):
        for campo, validar in ((self.correo, UsuariosService._correo),
                               (self.telefono, UsuariosService._telefono)):
            try:
                validar(campo.text())
            except ValueError as error:
                self.error.setText(str(error))
                self.error.show()
                campo.setFocus()
                return
        datos = dict(usuario=self.usuario.text(), rol=self.rol.currentData(),
                     activo=self.activo.isChecked(),
                     correo=self.correo.text(), telefono=self.telefono.text())
        if self.registro:
            datos['id_usuario'] = self.registro['id_usuario']
        if self._foto_cambiada:
            datos['foto_perfil'] = self._foto_seleccionada
        self.error.clear()
        self.error.hide()
        self.guardar.emit(datos)

    def establecer_ocupado(self, ocupado):
        self.guardar_button.setEnabled(not ocupado)
        self.cancelar.setEnabled(not ocupado)
        self.elegir_foto.setEnabled(not ocupado)
        self.quitar_foto.setEnabled(not ocupado and bool(self._foto_seleccionada))
        for campo in (self.usuario, self.correo, self.telefono):
            campo.setEnabled(not ocupado)
        if not self._propio:
            self.rol.setEnabled(not ocupado)
            self.activo.setEnabled(not ocupado)


class UsuariosView(QWidget):
    reautenticar = Signal()
    solicitudes_actualizadas = Signal()

    def __init__(self, sesion, controller=None, parent=None, recovery_controller=None):
        if not sesion.es_administrador:
            raise PermissionError('Solo un administrador puede gestionar usuarios.')
        super().__init__(parent)
        self.sesion = sesion
        self.colors = COLORS
        self.setObjectName('usersPage')
        self.setStyleSheet(USERS_STYLE)
        self.controller = controller if controller is not None else UsuariosController(sesion, parent=self)
        self._dialogo = None
        self._credenciales = None
        self._confirmacion = None
        self._ocupado = False
        self._recarga_pendiente = False
        self._reautenticacion_pendiente = False
        self._filtros_consulta = None
        self._busqueda_timer = QTimer(self)
        self._busqueda_timer.setSingleShot(True)
        self._busqueda_timer.setInterval(250)
        self._busqueda_timer.timeout.connect(self.cargar)
        self._usuarios = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(objectName='usersScroll')
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.canvas = QWidget(objectName='usersCanvas')
        self.content = QVBoxLayout(self.canvas)
        self.content.setContentsMargins(28, 22, 28, 22)
        self.content.setSpacing(18)
        self.scroll.setWidget(self.canvas)
        outer.addWidget(self.scroll)
        self.content.addLayout(self._header())
        self.tabs = QTabWidget(objectName='usersTabs')
        self.cuentas = QWidget()
        accounts_layout = QVBoxLayout(self.cuentas)
        accounts_layout.setContentsMargins(0, 16, 0, 0)
        accounts_layout.setSpacing(18)
        accounts_layout.addLayout(self._metrics())
        self.body = QBoxLayout(QBoxLayout.LeftToRight)
        self.body.setSpacing(18)
        self.body.addWidget(self._directory(), 3)
        self.body.addWidget(self._inspector(), 1)
        accounts_layout.addLayout(self.body, 1)
        self.tabs.addTab(self.cuentas, 'Usuarios')
        self.solicitudes = SolicitudesRecuperacionView(sesion, controller=recovery_controller, parent=self)
        self.solicitudes.actualizado.connect(self.solicitudes_actualizadas.emit)
        self.tabs.addTab(self.solicitudes, 'Solicitudes de contraseña')
        self.tabs.currentChanged.connect(self._cambiar_pestana)
        self.content.addWidget(self.tabs, 1)
        self.mensaje = _label('', 'feedback', True)
        self.mensaje.hide()
        self.content.addWidget(self.mensaje)
        self.controller.actualizado.connect(self._recibir)
        self.controller.fallo.connect(self._fallo)
        self.controller.ocupado.connect(self._establecer_ocupado)
        self._acciones()

    def _cambiar_pestana(self, index):
        self.nuevo.setVisible(index == 0)
        self.mensaje.hide()
        self.scroll.verticalScrollBar().setValue(0)
        if index == 1:
            self._busqueda_timer.stop()
            self.solicitudes.cargar()
        else:
            self.cargar()

    def activar(self):
        if self.tabs.currentIndex() == 1:
            self.solicitudes.cargar()
        else:
            self.cargar()

    def actualizar_solicitudes_pendientes(self, cantidad):
        self.tabs.setTabText(1, f'Solicitudes de contraseña · {cantidad} por revisar')
        self.tabs.setTabToolTip(1, f'{cantidad} solicitudes por revisar. La tabla incluye el historial completo de todos los estados.')

    def _header(self):
        row = QHBoxLayout()
        copy = QVBoxLayout()
        copy.setSpacing(3)
        copy.addWidget(_label('ORGANIZACIÓN  /  PERSONAS Y ACCESOS', 'eyebrow'))
        copy.addWidget(_label('Gestión de usuarios', 'pageTitle'))
        row.addLayout(copy, 1)
        self.nuevo = QPushButton('+  Nuevo usuario', objectName='primary')
        self.nuevo.setCursor(Qt.PointingHandCursor)
        self.nuevo.clicked.connect(self._nuevo)
        row.addWidget(self.nuevo)
        row.addSpacing(16)
        avatar = _label(self.sesion.iniciales, 'accountAvatar')
        avatar.setFixedSize(42, 42)
        avatar.setAlignment(Qt.AlignCenter)
        row.addWidget(avatar)
        account = QVBoxLayout()
        account.setSpacing(2)
        account.addWidget(_label(self.sesion.usuario, 'accountName'))
        account.addWidget(_label(self.sesion.rol_mostrar, 'accountRole'))
        row.addLayout(account)
        return row

    def _metrics(self):
        self.metric_grid = QGridLayout()
        self.metric_grid.setSpacing(14)
        self.metric_cards, self.metric_values = [], {}
        for columna, (key, caption, hint, symbol) in enumerate((
            ('total', 'Cuentas en esta vista', 'Personas de tu organización', '◎'),
            ('activos', 'Accesos activos', 'Listos para trabajar', '↗'),
            ('admins', 'Administradores', 'Gestión y control de usuarios', '◇'),
            ('inactivos', 'Cuentas pausadas', 'Sin acceso al iniciar sesión', 'II'),
        )):
            card = QFrame(objectName='metric')
            card.setProperty('featured', columna == 0)
            layout = QHBoxLayout(card)
            layout.setContentsMargins(18, 14, 18, 14)
            text = QVBoxLayout()
            text.setSpacing(1)
            text.addWidget(_label(caption, 'metricCaption'))
            value = _label('—', 'metricValue')
            self.metric_values[key] = value
            text.addWidget(value)
            text.addWidget(_label(hint, 'metricHint'))
            layout.addLayout(text, 1)
            icon = _label(symbol, 'metricSymbol')
            icon.setFixedSize(38, 38)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)
            self.metric_cards.append(card)
            self.metric_grid.addWidget(card, 0, columna)
        return self.metric_grid

    def _directory(self):
        panel = QFrame(objectName='directory')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 12)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        heading.addWidget(_label('Directorio del equipo', 'sectionTitle'))
        self.contador = _label('—', 'countBadge')
        heading.addWidget(self.contador)
        heading.addStretch()
        heading.addWidget(_label('Selecciona una cuenta para gestionarla', 'muted'))
        layout.addLayout(heading)
        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.buscar = QLineEdit(placeholderText='Buscar por usuario, correo o teléfono…')
        self.buscar.setClearButtonEnabled(True)
        self.buscar.setMinimumWidth(120)
        self.buscar.setMaxLength(254)
        self.buscar.textChanged.connect(self._programar_busqueda)
        self.buscar.returnPressed.connect(self.cargar)
        self.rol = QComboBox()
        self.rol.addItem('Todos los roles', None)
        for rol in ROLES:
            self.rol.addItem(rol.capitalize(), rol)
        self.estado = QComboBox()
        for texto, valor in (('Todos los estados', None), ('Activos', True), ('Inactivos', False)):
            self.estado.addItem(texto, valor)
        self.actualizar = QPushButton('Buscar', objectName='secondary')
        self.actualizar.setToolTip('Buscar o actualizar el directorio')
        self.actualizar.clicked.connect(self.cargar)
        for widget in (self.buscar, self.rol, self.estado, self.actualizar):
            tools.addWidget(widget)
        tools.setStretch(0, 1)
        layout.addLayout(tools)
        self.rol.currentIndexChanged.connect(self.cargar)
        self.estado.currentIndexChanged.connect(self.cargar)
        self.tabla = TablaPaginada(0, 6)
        self.tabla.setObjectName('usersTable')
        self.tabla.setHorizontalHeaderLabels(('ID', 'Usuario', 'Rol', 'Estado', 'Último acceso', 'Creación'))
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setShowGrid(False)
        self.tabla.setMouseTracking(True)
        self.tabla.setItemDelegate(UserDelegate(self.tabla))
        self.tabla.verticalHeader().hide()
        self.tabla.verticalHeader().setDefaultSectionSize(70)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for column, width in ((2, 140), (3, 96), (4, 146)):
            self.tabla.horizontalHeader().setSectionResizeMode(column, QHeaderView.Fixed)
            self.tabla.setColumnWidth(column, width)
        self.tabla.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabla.setColumnHidden(0, True)
        self.tabla.setColumnHidden(5, True)
        self.tabla.setMinimumHeight(240)
        self.tabla.itemSelectionChanged.connect(self._acciones)
        self.tabla.cellDoubleClicked.connect(lambda *_: self._editar())
        layout.addWidget(self.tabla, 1)
        self.vacio = QFrame()
        empty = QVBoxLayout(self.vacio)
        empty.setContentsMargins(20, 36, 20, 36)
        empty.setSpacing(8)
        for texto, name in (('◎', 'metricValue'), ('Tu equipo empieza aquí', 'sectionTitle'),
                            ('Carga el directorio o crea una nueva cuenta.', 'muted')):
            label = _label(texto, name, True)
            label.setAlignment(Qt.AlignCenter)
            empty.addWidget(label)
        self.empty_title = empty.itemAt(1).widget()
        self.empty_copy = empty.itemAt(2).widget()
        layout.addWidget(self.vacio, 1)
        self.tabla.hide()
        layout.addWidget(_rule())
        self.resumen = _label('Datos reales de tu organización · Sin consultar todavía', 'muted', True)
        layout.addWidget(self.resumen)
        return panel

    def _inspector(self):
        self.inspector = QFrame(objectName='inspector')
        self.inspector.setMinimumWidth(310)
        self.inspector.setMaximumWidth(380)
        layout = QVBoxLayout(self.inspector)
        layout.setContentsMargins(5, 0, 5, 16)
        layout.setSpacing(9)
        self.carnet = FichaAcceso()
        layout.addWidget(self.carnet, 0, Qt.AlignHCenter)
        self.perfil_avatar = self.carnet.avatar
        self.perfil_nombre = self.carnet.nombre
        self.perfil_rol = self.carnet.rol
        self.perfil_estado = self.carnet.estado
        self.perfil_acceso = self.carnet.acceso
        self.perfil_creacion = self.carnet.creacion
        self.perfil_correo = self.carnet.correo
        self.perfil_telefono = self.carnet.telefono
        self.permisos = self.carnet.permisos
        hint = _label('↔  Pasa el mouse para girar · Clic para fijar', 'muted')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        actions = QVBoxLayout()
        actions.setContentsMargins(16, 0, 16, 0)
        actions.setSpacing(8)
        self.editar = QPushButton('Editar acceso  ↗', objectName='primary')
        self.editar.clicked.connect(self._editar)
        self.eliminar = QPushButton('Eliminar cuenta', objectName='danger')
        self.eliminar.clicked.connect(self._eliminar)
        actions.addWidget(self.editar)
        actions.addWidget(self.eliminar)
        self.perfil_nota = _label('¿Solo necesitas pausar el acceso? Desactiva la cuenta desde Editar para conservar su historial.', 'note', True)
        actions.addWidget(self.perfil_nota)
        layout.addLayout(actions)
        layout.addStretch()
        return self.inspector

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() < 1000
        self.body.setDirection(QBoxLayout.TopToBottom if compact else QBoxLayout.LeftToRight)
        self.body.setAlignment(self.inspector, Qt.AlignHCenter if compact else Qt.AlignTop)
        columns = 2 if compact else 4
        for index, card in enumerate(self.metric_cards):
            self.metric_grid.removeWidget(card)
            self.metric_grid.addWidget(card, index // columns, index % columns)

    def _programar_busqueda(self, _texto):
        self._busqueda_timer.start()

    def _filtros_actuales(self):
        return dict(buscar=self.buscar.text(), rol=self.rol.currentData(), activo=self.estado.currentData())

    def cargar(self, *_):
        self._busqueda_timer.stop()
        if self._ocupado or self._confirmacion is not None:
            self._recarga_pendiente = True
            return
        self._filtros_consulta = self._filtros_actuales()
        self.controller.ejecutar('listar', **self._filtros_consulta)

    def _seleccionado(self):
        fila = self.tabla.currentRow()
        item = self.tabla.item(fila, 0) if fila >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def _acciones(self):
        registro = self._seleccionado()
        self.carnet.reset_for(registro['id_usuario'] if registro else None)
        self.carnet.set_code(registro['id_usuario'] if registro else None)
        self.carnet.set_status(registro['activo'] if registro else False)
        self.perfil_avatar.set_foto(registro.get('foto_perfil') if registro else None)
        self.editar.setEnabled(not self._ocupado and registro is not None)
        self.eliminar.setEnabled(not self._ocupado and registro is not None
                                 and registro['id_usuario'] != self.sesion.id_usuario)
        if registro:
            self.perfil_avatar.setText(initials(registro['usuario']))
            self.perfil_nombre.setText(registro['usuario'])
            propio = registro['id_usuario'] == self.sesion.id_usuario
            self.perfil_rol.setText(f'{registro["rol"].capitalize()}  ·  {"Tu cuenta" if propio else "#" + str(registro["id_usuario"])}')
            self.perfil_estado.setText('●  Activo' if registro['activo'] else '○  Inactivo')
            self.perfil_acceso.setText(self._fecha(registro['ultimo_acceso']) if registro['ultimo_acceso'] else 'Sin accesos registrados')
            self.perfil_creacion.setText(self._fecha(registro['fecha_creacion']))
            self.perfil_correo.setText(registro.get('correo') or 'Sin registrar')
            self.perfil_telefono.setText(registro.get('telefono') or 'Sin registrar')
            self.permisos.setText('✓  Puede gestionar usuarios y sus roles.' if registro['rol'] == 'administrador'
                                 else '—  Sin permisos de gestión de usuarios.')
            self.perfil_nota.setText('Tu cuenta está protegida: no puedes eliminarla, desactivarla ni quitarte el rol de administrador.' if propio
                                    else 'Para conservar su historial, puedes desactivar la cuenta desde Editar.')
        else:
            self.perfil_avatar.setText('◎')
            self.perfil_nombre.setText('Cada persona,\nsu lugar.')
            self.perfil_rol.setText('Selecciona una cuenta del directorio')
            for campo in (self.perfil_estado, self.perfil_acceso, self.perfil_creacion,
                          self.perfil_correo, self.perfil_telefono):
                campo.setText('—')
            self.permisos.setText('Consulta su rol y administra sus credenciales desde un solo lugar.')
            self.perfil_nota.setText('¿Solo necesitas pausar el acceso? Desactiva la cuenta desde Editar para conservar su historial.')

    def _abrir_dialogo(self, registro=None):
        if self._ocupado:
            return
        if self._dialogo is not None:
            self._dialogo.raise_()
            return
        dialogo = UsuarioDialog(self.sesion, registro, self)
        self._dialogo = dialogo
        dialogo.guardar.connect(lambda datos: self.controller.ejecutar('modificar' if registro else 'crear', **datos))
        dialogo.finished.connect(self._cerrar_dialogo)
        dialogo.open()

    def _cerrar_dialogo(self, _resultado):
        dialogo, self._dialogo = self._dialogo, None
        if dialogo is not None:
            dialogo.deleteLater()

    def _nuevo(self):
        self._abrir_dialogo()

    def _editar(self):
        registro = self._seleccionado()
        if registro:
            self._abrir_dialogo(registro)

    def _eliminar(self):
        registro = self._seleccionado()
        if not registro or self._ocupado or registro['id_usuario'] == self.sesion.id_usuario:
            return
        if self._confirmacion is not None:
            self._confirmacion.raise_()
            return
        identificador = registro['id_usuario']
        dialogo = ConfirmacionDialog('Eliminar usuario',
                                    f'¿Eliminar permanentemente la cuenta «{registro["usuario"]}»?\n'
                                    'Esta acción no se puede deshacer. Si tiene historial asociado, '
                                    'deberás desactivarla en lugar de eliminarla.',
                                    'Eliminar usuario', parent=self, peligro=True)
        self._confirmacion = dialogo
        dialogo.accepted.connect(lambda: self.controller.ejecutar('eliminar', id_usuario=identificador))
        dialogo.finished.connect(self._cerrar_confirmacion)
        dialogo.open()

    def _cerrar_confirmacion(self, _resultado):
        dialogo, self._confirmacion = self._confirmacion, None
        if dialogo is not None:
            dialogo.deleteLater()
        if self._recarga_pendiente and not self._ocupado:
            self._recarga_pendiente = False
            self.cargar()

    @staticmethod
    def _fecha(valor):
        return valor.astimezone().strftime('%d/%m/%Y %H:%M') if valor else '—'

    def _recibir(self, resultado):
        if resultado['accion'] == 'listar':
            # No mostrar una respuesta antigua si se siguió escribiendo durante la consulta.
            if self._filtros_consulta is not None and self._filtros_consulta != self._filtros_actuales():
                self._recarga_pendiente = True
                return
            usuarios = resultado['usuarios']
            self._usuarios = usuarios
            seleccionado = self._seleccionado()
            selected_id = seleccionado['id_usuario'] if seleccionado else None
            self.tabla.setRowCount(0)
            for fila, usuario in enumerate(usuarios):
                self.tabla.insertRow(fila)
                valores = (usuario['id_usuario'], usuario['usuario'], usuario['rol'].capitalize(),
                           'Activo' if usuario['activo'] else 'Inactivo',
                           self._fecha(usuario['ultimo_acceso']), self._fecha(usuario['fecha_creacion']))
                for columna, valor in enumerate(valores):
                    item = QTableWidgetItem(str(valor))
                    if columna == 0:
                        item.setData(Qt.UserRole, usuario)
                    self.tabla.setItem(fila, columna, item)
            self.tabla.setVisible(bool(usuarios))
            self.vacio.setVisible(not usuarios)
            self.empty_title.setText('Sin coincidencias por ahora')
            self.empty_copy.setText('Prueba con otro nombre, rol o estado para encontrar a tu equipo.')
            self.resumen.setText(f'{len(usuarios)} usuario(s) encontrado(s).' if usuarios else 'No hay usuarios que coincidan con la búsqueda.')
            self.contador.setText(str(len(usuarios)))
            counts = dict(total=len(usuarios), activos=sum(u['activo'] for u in usuarios),
                          admins=sum(u['rol'] == 'administrador' for u in usuarios),
                          inactivos=sum(not u['activo'] for u in usuarios))
            for key, value in counts.items():
                self.metric_values[key].setText(str(value))
            if usuarios:
                row = next((i for i, u in enumerate(usuarios) if u['id_usuario'] == selected_id), 0)
                self.tabla.selectRow(row)
        else:
            if self._dialogo:
                self._dialogo.accept()
            if resultado['accion'] == 'crear':
                clave = resultado.pop('contrasena_temporal', None)
                if clave:
                    self._credenciales = CredencialesDialog(resultado.get('usuario', ''), clave, self)
                    self._credenciales.finished.connect(self._cerrar_credenciales)
                    self._credenciales.open()
            self._feedback({'crear': 'Usuario creado. Ya tiene un lugar en tu equipo.',
                            'modificar': 'Usuario actualizado. Sus cambios de acceso se guardaron.',
                            'eliminar': 'Usuario eliminado.'}[resultado['accion']])
            self._reautenticacion_pendiente = resultado.get('reautenticar', False)
            self._recarga_pendiente = not self._reautenticacion_pendiente
        self._acciones()

    def _cerrar_credenciales(self, _resultado):
        dialogo, self._credenciales = self._credenciales, None
        if dialogo:
            dialogo.deleteLater()

    def _fallo(self, mensaje):
        self._feedback(mensaje, error=True)
        if self._dialogo:
            self._dialogo.error.setText(mensaje)
            self._dialogo.error.show()

    def _feedback(self, mensaje, error=False):
        self.mensaje.setText(mensaje)
        self.mensaje.setProperty('error', error)
        self.mensaje.style().unpolish(self.mensaje)
        self.mensaje.style().polish(self.mensaje)
        self.mensaje.show()

    def _establecer_ocupado(self, ocupado):
        self._ocupado = ocupado
        for widget in (self.rol, self.estado, self.actualizar, self.nuevo):
            widget.setEnabled(not ocupado)
        self.actualizar.setText('Consultando…' if ocupado else 'Buscar')
        if self._dialogo:
            self._dialogo.establecer_ocupado(ocupado)
        self._acciones()
        if not ocupado and self._reautenticacion_pendiente:
            self._busqueda_timer.stop()
            self._reautenticacion_pendiente = False
            QMessageBox.information(self, 'Cuenta actualizada', 'Vuelve a iniciar sesión con tus credenciales actualizadas.')
            self.reautenticar.emit()
        elif not ocupado and self._recarga_pendiente:
            self._recarga_pendiente = False
            self.cargar()
