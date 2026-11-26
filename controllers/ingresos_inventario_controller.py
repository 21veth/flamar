from PySide6.QtCore import QObject, Signal

from services.importacion_inventarios_service import ImportacionIngresosService


class IngresosInventarioController(QObject):
    listado = Signal(object)
    detalle_consultado = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio=None, parent=None):
        super().__init__(parent)
        self._servicio = servicio if servicio is not None else ImportacionIngresosService()

    def listar(self, busqueda='', proveedor='', estado='', fecha=''):
        return self._ejecutar(
            self._servicio.listar_ingresos,
            (busqueda, proveedor, estado, fecha),
            self.listado,
        )

    def obtener_detalle(self, id_ingreso):
        return self._ejecutar(
            self._servicio.obtener_ingreso,
            (id_ingreso,),
            self.detalle_consultado,
        )

    def _ejecutar(self, operacion, argumentos, señal):
        try:
            resultado = operacion(*argumentos)
        except Exception as error:
            self.fallo.emit(str(error) or error.__class__.__name__)
            return False
        señal.emit(resultado)
        return True


__all__ = ['IngresosInventarioController']
