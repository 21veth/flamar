from PySide6.QtCore import Qt, QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from controllers.recuperacion_controller import RecuperacionController
from views.tabla_paginada import TablaPaginada
from views.confirmacion_dialog import ConfirmacionDialog
from views.recuperacion_dialog import ESTADOS, _label
from views.usuarios_theme import USERS_STYLE


class SolicitudesRecuperacionView(QFrame):
    """Historial completo, sin filtrar solicitudes por estado."""

    actualizado = Signal()

    def __init__(self, sesion, controller=None, parent=None):
        if not sesion.es_administrador:
            raise PermissionError('Solo un administrador puede revisar solicitudes.')
        super().__init__(parent)
        self.sesion, self._ocupado, self._recargar = sesion, False, False
        self._confirmacion = None
        self.setObjectName('directory')
        self.setStyleSheet(USERS_STYLE)
        self.controller = controller if controller is not None else RecuperacionController(sesion, parent=self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(_label('Historial de solicitudes de contraseña', 'sectionTitle'))
        layout.addWidget(_label('Aquí se conservan todas las solicitudes: pendientes, autorizadas, denegadas, '
                                 'completadas, caducadas y demás estados. Nunca se muestran códigos ni contraseñas.', 'muted', True))
        layout.addWidget(_label('Primero autoriza la solicitud: solo entonces se enviará el código al usuario. '
                                   'Tu propia recuperación debe revisarla otro administrador.', 'note', True))
        self.resumen = _label('Sin consultar todavía.', 'muted', True)
        layout.addWidget(self.resumen)
        acciones = QHBoxLayout()
        self.aprobar = QPushButton('Autorizar y enviar código', objectName='primary')
        self.rechazar = QPushButton('Denegar solicitud', objectName='danger')
        self.refrescar = QPushButton('Actualizar', objectName='secondary')
        self.aprobar.clicked.connect(lambda: self._resolver(True))
        self.rechazar.clicked.connect(lambda: self._resolver(False))
        self.refrescar.clicked.connect(self.cargar)
        for boton in (self.aprobar, self.rechazar, self.refrescar):
            acciones.addWidget(boton)
        acciones.addStretch()
        layout.addLayout(acciones)
        self.seleccion_label = _label('Selecciona una solicitud para autorizarla o denegarla.', 'note', True)
        layout.addWidget(self.seleccion_label)
        self.tabla = TablaPaginada(0, 9)
        self.tabla.setObjectName('usersTable')
        self.tabla.setHorizontalHeaderLabels(('Usuario', 'Canal', 'Contacto protegido', 'Estado', 'Correo',
                                             'Fecha de solicitud', 'Referencia', 'Revisó', 'Fecha de decisión'))
        self.tabla.setColumnHidden(6, True)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setShowGrid(False)
        self.tabla.setMinimumHeight(300)
        self.tabla.verticalHeader().show()
        self.tabla.verticalHeader().setDefaultSectionSize(48)
        self.tabla.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.tabla.setColumnWidth(0, 160)
        self.tabla.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabla.itemSelectionChanged.connect(self._acciones)
        layout.addWidget(self.tabla, 1)
        self.mensaje = _label('Selecciona Actualizar para consultar las solicitudes.', 'muted', True)
        layout.addWidget(self.mensaje)
        self.controller.actualizado.connect(self._recibir)
        self.controller.fallo.connect(self.mensaje.setText)
        self.controller.ocupado.connect(self._establecer_ocupado)
        self._acciones()

    def cargar(self):
        if self._ocupado or self._confirmacion is not None:
            self._recargar = True
        else:
            self.controller.ejecutar('listar')

    def _seleccion(self):
        item = self.tabla.item(self.tabla.currentRow(), 0)
        return item.data(Qt.UserRole) if item else None

    def _acciones(self):
        item = self._seleccion()
        ajena = bool(item and item['id_usuario'] != self.sesion.id_usuario)
        self.aprobar.setEnabled(not self._ocupado and ajena and item['estado'] in ('pendiente', 'envio_fallido', 'enviando')
                               and item.get('envio_intentos', 0) < 3 and not item.get('correo_pendiente', False))
        self.aprobar.setText('Reintentar envío' if item and item['estado'] in ('envio_fallido', 'enviando') else 'Autorizar y enviar código')
        self.rechazar.setEnabled(not self._ocupado and ajena and item['estado'] in ('codigo_enviado', 'pendiente', 'envio_fallido', 'enviando', 'aprobada'))
        if not item:
            texto = 'Selecciona una solicitud para autorizarla o denegarla.'
        else:
            texto = f'Seleccionada: {item["usuario"]} · Ref. {str(item["id_solicitud"])[:8]} · '
            if self._ocupado:
                texto += 'Procesando; espera a que termine la operación.'
            elif not ajena:
                texto += 'Otro administrador debe revisar la recuperación de tu cuenta.'
            elif item['estado'] == 'pendiente':
                texto += ('Falta registrar su correo: ve a Usuarios → Editar acceso y después actualiza esta lista. '
                          'También puedes denegar la solicitud.' if item.get('correo_pendiente', False) else
                          'Puedes autorizar el envío del código o denegar esta solicitud.')
            elif item['estado'] in ('envio_fallido', 'enviando'):
                texto += ('Se agotaron los 3 intentos de envío. Puedes denegar esta solicitud.'
                          if item.get('envio_intentos', 0) >= 3 else
                          'Autorizada. Puedes reintentar el correo tras 2 minutos desde el último intento. ')
                texto += item.get('detalle_envio', '')
            elif item['estado'] in ('codigo_enviado', 'aprobada'):
                texto += 'Ya autorizada; no necesita otro permiso. Puedes denegarla mientras siga vigente.'
            else:
                texto += ESTADOS.get(item['estado'], item['estado']) + '. No admite nuevas decisiones.'
        self.seleccion_label.setText(texto)

    def _resolver(self, aprobar):
        item = self._seleccion()
        if self._ocupado or not item or item['id_usuario'] == self.sesion.id_usuario:
            return
        if self._confirmacion is not None:
            self._confirmacion.raise_()
            return
        identificador = item['id_solicitud']
        dialogo = ConfirmacionDialog('Confirmar decisión',
                                    f'¿{"Autorizar y enviar el código para" if aprobar else "Denegar"} '
                                    f'la solicitud de «{item["usuario"]}»?\nRef. {identificador}',
                                    'Autorizar y enviar código' if aprobar else 'Denegar solicitud',
                                    parent=self, peligro=not aprobar)
        self._confirmacion = dialogo
        dialogo.accepted.connect(lambda: self.controller.ejecutar('aprobar' if aprobar else 'rechazar',
                                                                 id_solicitud=identificador))
        dialogo.finished.connect(self._cerrar_confirmacion)
        dialogo.open()

    def _cerrar_confirmacion(self, _resultado):
        dialogo, self._confirmacion = self._confirmacion, None
        if dialogo is not None:
            dialogo.deleteLater()
        if self._recargar and not self._ocupado:
            self._recargar = False
            self.cargar()

    def _recibir(self, resultado):
        if resultado['accion'] == 'listar':
            seleccion = self._seleccion()
            selected_id = seleccion['id_solicitud'] if seleccion else None
            bloqueo = QSignalBlocker(self.tabla)
            self.tabla.setRowCount(0)
            for fila, item in enumerate(resultado['solicitudes']):
                self.tabla.insertRow(fila)
                fecha = item['solicitado_en'].astimezone().strftime('%d/%m/%Y %H:%M')
                valores = (item['usuario'], 'Correo' if item['canal'] == 'correo' else 'Canal anterior',
                           item['destino'], ESTADOS.get(item['estado'], item['estado']),
                           ('Falta registrar correo' if item.get('correo_pendiente', False) else
                            {'pendiente': 'Aún no autorizado', 'enviando': 'Enviando…', 'codigo_enviado': 'Enviado',
                             'aprobada': 'Enviado / Validado', 'envio_fallido': 'No enviado',
                             'completada': 'Enviado / Usado'}.get(item['estado'], '—')), fecha,
                           str(item['id_solicitud'])[:8], item.get('administrador') or 'Sin decisión',
                           item['resuelto_en'].astimezone().strftime('%d/%m/%Y %H:%M') if item.get('resuelto_en') else '—')
                for columna, valor in enumerate(valores):
                    celda = QTableWidgetItem(valor)
                    if columna == 0:
                        celda.setData(Qt.UserRole, item)
                    self.tabla.setItem(fila, columna, celda)
                    if columna == 4:
                        celda.setToolTip(item.get('detalle_envio', ''))
                    elif columna in (0, 5, 6):
                        celda.setToolTip(f'Ref. {item["id_solicitud"]}\nSolicitada: {fecha}')
            solicitudes = resultado['solicitudes']
            if solicitudes:
                fila = next((i for i, item in enumerate(solicitudes) if item['id_solicitud'] == selected_id), None)
                if fila is None:
                    fila = next((i for i, item in enumerate(solicitudes)
                                 if item['id_usuario'] != self.sesion.id_usuario and item['estado'] == 'pendiente'), 0)
                self.tabla.selectRow(fila)
            bloqueo.unblock()
            pendientes = sum(item['estado'] in ('pendiente', 'envio_fallido') for item in solicitudes)
            self.resumen.setText(f'Historial completo: {len(solicitudes)} solicitud(es) en total · {pendientes} por revisar. '
                                 'El contador de avisos solo cuenta las que están por revisar, no el total del historial.')
            fallidos = sum(item['estado'] == 'envio_fallido' for item in resultado['solicitudes'])
            if fallidos:
                self.mensaje.setText(f'{fallidos} solicitud(es) autorizadas con correo pendiente: la autorización '
                                     'está guardada. Revisa el motivo del envío y reintenta después de 2 minutos.')
            else:
                self.mensaje.setText('El historial incluye todos los estados, en páginas de 7 filas. Cada fila es una solicitud; '
                                     'autorizarla o denegarla no la elimina del historial. Las pendientes aparecen primero.'
                                     if resultado['solicitudes'] else 'No hay solicitudes de contraseña registradas.')
        else:
            self.mensaje.setText(resultado.get('mensaje', 'Decisión guardada. El usuario verá el estado actualizado en el login.'))
            self._recargar = True
            self.actualizado.emit()
        self._acciones()

    def _establecer_ocupado(self, ocupado):
        self._ocupado = ocupado
        self.refrescar.setEnabled(not ocupado)
        self._acciones()
        if not ocupado and self._recargar:
            self._recargar = False
            self.cargar()
