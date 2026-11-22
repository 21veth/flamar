from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from services.usuarios_service import UsuariosService


class _UsuariosWorker(QThread):
    exito = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio, accion, datos):
        super().__init__(QCoreApplication.instance())
        self._servicio, self._accion, self._datos = servicio, accion, datos
        QCoreApplication.instance().aboutToQuit.connect(self._esperar_cierre)
        self.finished.connect(self.deleteLater)

    @Slot()
    def _esperar_cierre(self):
        self.wait()

    def run(self):
        try:
            resultado = self._servicio.ejecutar(self._accion, **self._datos)
        except (ValueError, PermissionError) as error:
            self.fallo.emit(str(error))
        except Exception:
            # No registrar datos de formularios ni excepciones con credenciales.
            self.fallo.emit('No se pudo completar la operación de usuarios.')
        else:
            self.exito.emit(resultado)
        finally:
            self._datos.clear()


class UsuariosController(QObject):
    actualizado = Signal(object)
    fallo = Signal(str)
    ocupado = Signal(bool)

    def __init__(self, sesion, servicio=None, parent=None):
        super().__init__(parent)
        self._servicio = servicio if servicio is not None else UsuariosService(sesion)
        self._worker = None

    def ejecutar(self, accion, **datos):
        if self._worker is not None:
            return False
        self._worker = _UsuariosWorker(self._servicio, accion, datos)
        self._worker.exito.connect(self.actualizado)
        self._worker.fallo.connect(self.fallo)
        self._worker.finished.connect(self._finalizar)
        self.ocupado.emit(True)
        self._worker.start()
        return True

    def _finalizar(self):
        self._worker = None
        self.ocupado.emit(False)
