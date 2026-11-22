from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from services.recuperacion_service import RecuperacionService


class _RecuperacionWorker(QThread):
    exito = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio, accion, datos):
        super().__init__(QCoreApplication.instance())
        self.servicio, self.accion, self.datos = servicio, accion, datos
        QCoreApplication.instance().aboutToQuit.connect(self._esperar)
        self.finished.connect(self.deleteLater)

    @Slot()
    def _esperar(self):
        self.wait()

    def run(self):
        try:
            resultado = self.servicio.ejecutar(self.accion, **self.datos)
        except (ValueError, PermissionError) as error:
            self.fallo.emit(str(error))
        except Exception:
            self.fallo.emit('No se pudo completar la operación de recuperación.')
        else:
            self.exito.emit(resultado)
        finally:
            self.datos.clear()


class RecuperacionController(QObject):
    actualizado = Signal(object)
    fallo = Signal(str)
    ocupado = Signal(bool)

    def __init__(self, sesion=None, servicio=None, parent=None):
        super().__init__(parent)
        self.servicio = servicio if servicio is not None else RecuperacionService(sesion)
        self._worker = None

    def ejecutar(self, accion, **datos):
        if self._worker is not None:
            return False
        self._worker = _RecuperacionWorker(self.servicio, accion, datos)
        self._worker.exito.connect(self.actualizado)
        self._worker.fallo.connect(self.fallo)
        self._worker.finished.connect(self._finalizar)
        self.ocupado.emit(True)
        self._worker.start()
        return True

    def _finalizar(self):
        self._worker = None
        self.ocupado.emit(False)
