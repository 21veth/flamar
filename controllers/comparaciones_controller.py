from PySide6.QtCore import QObject, Signal

from services.comparacion_service import ComparacionService


class ComparacionesController(QObject):
    guardada = Signal(object)
    sincronizada = Signal(object)
    editada = Signal(object)
    eliminada = Signal(object)
    listado = Signal(object)
    detalle_consultado = Signal(object)
    fallo = Signal(str)

    def __init__(self, servicio=None, parent=None):
        super().__init__(parent)
        self._servicio = servicio if servicio is not None else ComparacionService()

    def guardar(
        self,
        nombre,
        tipo_productos,
        id_usuario,
        ids_importacion,
        decision,
        matrix_rows_data,
        razones,
    ):
        return self._ejecutar(
            self._servicio.guardar,
            (
                nombre,
                tipo_productos,
                id_usuario,
                ids_importacion,
                decision,
                matrix_rows_data,
                razones,
            ),
            self.guardada,
        )

    def sincronizar_historial(self, id_usuario):
        return self._ejecutar(
            self._servicio.sincronizar_desde_importaciones,
            (id_usuario,),
            self.sincronizada,
        )

    def editar(
        self, id_comparacion, id_usuario, nombre, tipo_productos, justificacion
    ):
        return self._ejecutar(
            self._servicio.editar,
            (id_comparacion, id_usuario, nombre, tipo_productos, justificacion),
            self.editada,
        )

    def eliminar(self, id_comparacion, id_usuario):
        return self._ejecutar(
            self._servicio.eliminar,
            (id_comparacion, id_usuario),
            self.eliminada,
        )

    def listar(self, id_usuario, busqueda='', categoria='', proveedor='', estado=''):
        return self._ejecutar(
            self._servicio.listar,
            (id_usuario, busqueda, categoria, proveedor, estado),
            self.listado,
        )

    def obtener_detalle(self, id_comparacion, id_usuario=None):
        return self._ejecutar(
            self._servicio.obtener_detalle,
            (id_comparacion, id_usuario),
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


__all__ = ['ComparacionesController']
