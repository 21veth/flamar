from PySide6.QtCore import QObject, QThread, Signal

from services.auth_service import (
    AuthService,
    CredencialesInvalidasError,
    ErrorDeConexionError,
)


class _AuthWorker(QThread):
    exito = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio, usuario, contrasena, parent=None):
        super().__init__(parent)
        self._servicio = servicio
        self._usuario = usuario
        self._contrasena = contrasena

    def run(self):
        try:
            sesion = self._servicio.autenticar(self._usuario, self._contrasena)
        except CredencialesInvalidasError as error:
            self.fallo.emit(str(error))
        except ErrorDeConexionError as error:
            self.fallo.emit(str(error))
        except Exception:
            self.fallo.emit('No se pudo iniciar sesión. Inténtalo de nuevo.')
        else:
            self.exito.emit(sesion)
        finally:
            self._contrasena = None


class LoginController(QObject):
    """Coordina el inicio de sesión y la vida del worker de autenticación."""

    autenticado = Signal(object)
    fallo = Signal(str)
    finalizado = Signal()

    def __init__(self, auth_service=None, parent=None):
        super().__init__(parent)
        self._auth_service = auth_service if auth_service is not None else AuthService()
        self._worker = None

    def en_progreso(self):
        return self._worker is not None and self._worker.isRunning()

    def autenticar(self, usuario, contrasena):
        if self._worker is not None:
            return False
        self._worker = _AuthWorker(self._auth_service, usuario, contrasena)
        self._worker.exito.connect(self.autenticado)
        self._worker.fallo.connect(self.fallo)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        return True

    def _on_worker_finished(self):
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self.finalizado.emit()
