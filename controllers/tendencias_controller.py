import logging

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from services.tendencias_service import TendenciasService


class _TendenciasWorker(QThread):
    exito = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio, accion, opciones):
        # La aplicación conserva el worker si se cambia de vista o se cierra sesión.
        super().__init__(QCoreApplication.instance())
        self._servicio, self._accion, self._opciones = servicio, accion, opciones
        QCoreApplication.instance().aboutToQuit.connect(self._esperar_cierre)
        self.finished.connect(self.deleteLater)

    @Slot()
    def _esperar_cierre(self):
        self.wait()

    def run(self):
        try:
            resultado = self._servicio.ejecutar(self._accion, **self._opciones)
        except ValueError as error:
            self.fallo.emit(str(error))
        except Exception:
            logging.getLogger(__name__).exception('Error inesperado en el radar')
            self.fallo.emit('No se pudo completar la operación del radar. Consulta el registro técnico.')
        else:
            self.exito.emit(resultado)


class TendenciasController(QObject):
    actualizado = Signal(object)
    fallo = Signal(str)
    ocupado = Signal(bool)

    def __init__(self, servicio=None, parent=None):
        super().__init__(parent)
        self._servicio = servicio if servicio is not None else TendenciasService()
        self._worker = None

    def ejecutar(self, accion, **opciones):
        if self._worker is not None:
            return False
        self._worker = _TendenciasWorker(self._servicio, accion, opciones)
        self._worker.exito.connect(self.actualizado)
        self._worker.fallo.connect(self.fallo)
        self._worker.finished.connect(self._finalizar)
        self.ocupado.emit(True)
        self._worker.start()
        return True

    def _finalizar(self):
        self._worker = None
        self.ocupado.emit(False)
