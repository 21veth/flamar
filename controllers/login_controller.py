from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from services.auth_service import (
    AuthService,
    CredencialesInvalidasError,
    ErrorDeConexionError,
    CambioPasswordPendiente,
)


class _AuthWorker(QThread):
    exito = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio, accion, datos):
        super().__init__(QCoreApplication.instance())
        self._servicio = servicio
        self._accion = accion
        self._datos = datos
        QCoreApplication.instance().aboutToQuit.connect(self._esperar_cierre)

    @Slot()
    def _esperar_cierre(self):
        self.wait()

    def run(self):
        try:
            sesion = getattr(self._servicio, self._accion)(*self._datos)
        except CredencialesInvalidasError as error:
            self.fallo.emit(str(error))
        except ErrorDeConexionError as error:
            self.fallo.emit(str(error))
        except ValueError as error:
            self.fallo.emit(str(error))
        except Exception:
            self.fallo.emit('No se pudo iniciar sesión. Inténtalo de nuevo.')
        else:
            self.exito.emit(sesion)
        finally:
            self._datos = None


class LoginController(QObject):
    """Coordina el inicio de sesión y la vida del worker de autenticación."""

    autenticado = Signal(object)
    cambio_requerido = Signal(object)
    fallo = Signal(str)
    finalizado = Signal()

    def __init__(self, auth_service=None, parent=None):
        super().__init__(parent)
        self._auth_service = auth_service if auth_service is not None else AuthService()
        self._worker = None

    def en_progreso(self):
        return self._worker is not None

    def autenticar(self, usuario, contrasena):
        return self._iniciar('autenticar', (usuario, contrasena))

    def cambiar_password(self, token, nueva, confirmacion):
        return self._iniciar('cambiar_password_inicial', (token, nueva, confirmacion))

    def cancelar_cambio(self, token):
        self._auth_service.cancelar_cambio(token)

    def _iniciar(self, accion, datos):
        if self._worker is not None:
            return False
        self._worker = _AuthWorker(self._auth_service, accion, datos)
        self._worker.exito.connect(self._resultado)
        self._worker.fallo.connect(self.fallo)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        return True

    def _resultado(self, resultado):
        if isinstance(resultado, CambioPasswordPendiente):
            self.cambio_requerido.emit(resultado)
        else:
            self.autenticado.emit(resultado)

    def _on_worker_finished(self):
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.finalizado.emit()
