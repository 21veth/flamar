from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.ingresos_inventario_controller import IngresosInventarioController
from services.importacion_inventarios_pg import (
    ContextoPostgresIngresos,
    PersistenciaPostgresIngresos,
)
from services.importacion_inventarios_service import ImportacionIngresosService
from views.app_theme import zeyver_stylesheet
from views.historial_ingresos_view import HistorialIngresosView
from views.import_inventory_view import InventoryImportTab


SECTION_STYLES = zeyver_stylesheet('''
QPushButton#segment { background: #eef2f8; color: #4c5b76; border: 0; border-radius: 7px; padding: 9px 16px; font-size: 11px; font-weight: 700; }
QPushButton#segmentActive { background: #5133f5; color: white; border: 0; border-radius: 7px; padding: 9px 16px; font-size: 11px; font-weight: 700; }
''')


class InventarioSectionView(QWidget):
    ingreso_guardado = Signal(object)

    def __init__(self, parent=None, sesion=None, servicio=None, controlador=None):
        super().__init__(parent, objectName='inventarioSection')
        self.sesion = sesion
        if servicio is None:
            contexto = ContextoPostgresIngresos()
            servicio = ImportacionIngresosService(
                contexto=contexto,
                persistencia=PersistenciaPostgresIngresos(contexto=contexto),
            )
        self.servicio = servicio
        if controlador is None:
            controlador = IngresosInventarioController(servicio)
        self.controlador = controlador
        self.setStyleSheet(SECTION_STYLES)
        self._construir()

    def _construir(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 8, 0, 0)
        raiz.setSpacing(10)

        segmentos = QFrame()
        disposicion = QHBoxLayout(segmentos)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.setSpacing(7)
        self.grupo_segmentos = QButtonGroup(self)
        self.grupo_segmentos.setExclusive(True)
        self.registro_button = QPushButton('Registrar ingreso', objectName='segment')
        self.registro_button.setCheckable(True)
        self.historial_button = QPushButton('Historial', objectName='segment')
        self.historial_button.setCheckable(True)
        self.grupo_segmentos.addButton(self.registro_button)
        self.grupo_segmentos.addButton(self.historial_button)
        self.registro_button.clicked.connect(lambda: self._set_segmento(0))
        self.historial_button.clicked.connect(self._ir_historial)
        disposicion.addWidget(self.registro_button)
        disposicion.addWidget(self.historial_button)
        disposicion.addStretch()
        raiz.addWidget(segmentos)

        self.registro = InventoryImportTab(self, self.sesion, self.servicio)
        self.historial = HistorialIngresosView(self.controlador, self)
        self.registro.ingreso_guardado.connect(self._al_ingreso_guardado)

        self.paginas = QStackedWidget()
        self.paginas.addWidget(self.registro)
        self.paginas.addWidget(self.historial)
        raiz.addWidget(self.paginas, 1)
        self._set_segmento(0)

    def _set_segmento(self, indice):
        boton = self.registro_button if indice == 0 else self.historial_button
        boton.setChecked(True)
        self._pulir_segmentos()
        self.paginas.setCurrentIndex(indice)

    def _pulir_segmentos(self):
        for boton in (self.registro_button, self.historial_button):
            boton.setObjectName('segmentActive' if boton.isChecked() else 'segment')
            boton.style().unpolish(boton)
            boton.style().polish(boton)

    def _ir_historial(self):
        self._set_segmento(1)
        self.historial.recargar()

    def _al_ingreso_guardado(self, id_ingreso):
        self.ingreso_guardado.emit(id_ingreso)
        self.historial.recargar()


__all__ = ['InventarioSectionView']
