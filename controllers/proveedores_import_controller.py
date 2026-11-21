"""Controller de la importacion de cotizaciones de proveedores."""

from PySide6.QtCore import QObject, Signal

from services.importacion_proveedores_service import ImportacionProveedoresService


class ProveedoresImportController(QObject):
    """Puerta de entrada de la vista al servicio de cotizaciones."""

    preparada = Signal(object)
    validada = Signal(object)
    guardada = Signal(object)
    descartada = Signal(object)
    fallo = Signal(str)
    fallo_detallado = Signal(object)
    resultado_consultado = Signal(object)
    detalle_consultado = Signal(object)
    resumen_consultado = Signal(object)
    fallo_registrado = Signal(object)

    def __init__(self, servicio=None, parent=None):
        super().__init__(parent)
        self._servicio = servicio if servicio is not None else ImportacionProveedoresService()

    def preparar(self, rutas, id_usuario=None):
        return self._ejecutar(
            self._servicio.preparar, (rutas, id_usuario), self.preparada
        )

    def preparar_demo(self, grupos):
        return self._ejecutar(self._servicio.preparar_demo, (grupos,), self.preparada)

    def validar(self, preparadas, id_usuario):
        return self._ejecutar(
            self._servicio.registrar_validacion, (preparadas, id_usuario), self.validada
        )

    def guardar(self, preparadas, excluidas=None, id_usuario=None):
        try:
            resultado = self._servicio.confirmar(
                preparadas, excluidas, id_usuario
            )
        except Exception as error:
            self.fallo.emit(str(error) or error.__class__.__name__)
            self.fallo_detallado.emit(
                getattr(self._servicio, 'ultimo_fallo', None)
            )
            return False
        self.guardada.emit(resultado)
        return True

    def consultar_resultado(self, ids_importacion):
        return self._ejecutar(
            self._servicio.consultar_resultado,
            (ids_importacion,),
            self.resultado_consultado,
        )

    def consultar_detalle(self, id_importacion):
        return self._ejecutar(
            self._servicio.consultar_ofertas,
            (id_importacion,),
            self.detalle_consultado,
        )

    def consultar_resumen(self):
        return self._ejecutar(
            self._servicio.consultar_resumen, (), self.resumen_consultado
        )

    def registrar_fallo(self, preparadas, motivo, id_usuario=None):
        return self._ejecutar(
            self._servicio.registrar_fallo,
            (preparadas, motivo, id_usuario),
            self.fallo_registrado,
        )

    def descartar(self, id_importacion):
        if id_importacion is None:
            return False
        return self._ejecutar(self._servicio.descartar, (id_importacion,), self.descartada)

    def _ejecutar(self, operacion, argumentos, señal):
        try:
            resultado = operacion(*argumentos)
        except Exception as error:
            self.fallo.emit(str(error) or error.__class__.__name__)
            return False
        señal.emit(resultado)
        return True


__all__ = ['ProveedoresImportController']
