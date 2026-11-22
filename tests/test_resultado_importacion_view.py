from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from models.importacion_proveedor import (
    ErrorImportacion,
    ResumenProveedor,
    ResultadoImportacion,
)
from views.import_results_view import ImportResultPanel, SavedOffersDialog
from views.import_suppliers_view import SuppliersImportTab


@pytest.fixture(scope='module')
def aplicacion():
    return QApplication.instance() or QApplication([])


def _resultado(estado='completada', errores=None):
    return ResultadoImportacion(
        id_importacion=10,
        nombre_archivo='Proveedor_01_LimpiaSur_ZEYVER.xlsx',
        fecha_importacion=datetime(2026, 11, 21, 10, 30),
        registros_totales=30,
        registros_validos=30,
        registros_rechazados=0,
        estado=estado,
        id_cotizacion=20,
        proveedor='Distribuidora LimpiaSur',
        ofertas_guardadas=30,
        errores=list(errores or []),
    )


def _resumen():
    return [
        ResumenProveedor('LimpiaSur', 30, 'completada'),
        ResumenProveedor('HigieneTotal', 30, 'completada'),
        ResumenProveedor('CleanMax', 30, 'completada'),
    ]


def test_panel_muestra_conteos_proveedor_y_resumen_desde_dto(aplicacion):
    panel = ImportResultPanel()

    panel.mostrar_resultados([_resultado()], _resumen())

    assert panel.estado_chip.text() == 'Importación exitosa'
    assert panel.estado_chip.objectName() == 'resultSuccessChip'
    assert panel._valor_metrica(panel.metrica_procesados).text() == '30'
    assert 'font-size:24px' in panel._valor_metrica(panel.metrica_procesados).styleSheet()
    assert panel._valor_metrica(panel.metrica_guardadas).text() == '30'
    assert panel._valor_metrica(panel.metrica_rechazados).text() == '0'
    assert panel.detalles['proveedor'].text() == 'Distribuidora LimpiaSur'
    assert panel.detalles['fecha'].text() == '21/11/2026 10:30'
    assert panel.errores_badge.text() == 'Sin errores'
    assert panel.errores_boton.text() == '▸ Detalle de errores · 0'
    assert panel.tabla_errores.isHidden() is True
    assert panel.tabla_errores.rowCount() == 0
    assert panel.tabla_resumen.alternatingRowColors() is False
    assert 'Actualizar resumen' not in [
        boton.text() for boton in panel.findChildren(QPushButton)
    ]
    assert panel.tabla_resumen.rowCount() == 3
    assert panel.total_ofertas.text() == 'Total de ofertas importadas: 90'
    assert 'Los datos de Distribuidora LimpiaSur' in panel.mensaje.text()


def test_panel_fallido_muestra_errores_y_cero_ofertas(aplicacion):
    error = ErrorImportacion(1, 7, 'precio', '0', 'Precio inválido')
    panel = ImportResultPanel()

    panel.mostrar_resultados([_resultado('fallida', [error])], [])

    assert panel.estado_chip.text() == 'Importación fallida'
    assert panel.estado_chip.objectName() == 'resultErrorChip'
    assert panel._valor_metrica(panel.metrica_guardadas).text() == '30'
    assert panel.errores_badge.text() == '1 error(es)'
    assert panel.errores_badge.objectName() == 'resultErrorBadge'
    assert panel.errores_boton.text() == '▸ Detalle de errores · 1'
    assert panel.tabla_errores.isHidden() is True
    assert panel.tabla_errores.rowCount() == 1
    assert panel.tabla_errores.item(0, 3).text() == 'Precio inválido'
    assert 'No se guardaron cotizaciones' in panel.mensaje.text()

    panel.errores_boton.setChecked(True)

    assert panel.tabla_errores.isHidden() is False
    assert panel.errores_boton.text() == '▾ Detalle de errores · 1'


def test_panel_limpia_estado_aplicacion(aplicacion):
    panel = ImportResultPanel()
    panel.mostrar_resultados([_resultado()], _resumen())

    panel.limpiar()

    assert panel.estado_chip.text() == 'Sin resultados'
    assert panel.tabla_resumen.rowCount() == 0
    assert panel.total_ofertas.text() == 'Total de ofertas importadas: 0'


def test_dialogo_muestra_ofertas_guardadas(aplicacion, monkeypatch):
    from views import import_suppliers_view

    ofertas = []
    dialogos = []

    class DialogoFake:
        def __init__(self, resultado, filas, parent=None):
            dialogos.append((resultado, filas))

        def exec(self):
            return 1

    monkeypatch.setattr(import_suppliers_view, 'SavedOffersDialog', DialogoFake)
    tab = SuppliersImportTab()
    tab._resultados_actuales = [_resultado()]
    tab._ultimo_id_importacion = 10
    tab._detalle_resultado = tab._resultados_actuales[0]

    tab._al_consultar_detalle(ofertas)

    assert dialogos[0][0].id_importacion == 10
    assert dialogos[0][1] == ofertas


def test_vista_incluye_cuarto_paso_y_panel(aplicacion):
    tab = SuppliersImportTab()

    assert tab.stepper.titles == (
        'Seleccionar archivo',
        'Validar datos',
        'Vista previa y confirmar',
        'Resultado de importación',
    )
    assert tab.steps.count() == 4
    assert isinstance(tab.result_panel, ImportResultPanel)
    assert tab.result_panel.findChild(QLabel, 'resultMessage') is not None


def test_dialogo_tabla_acepta_ofertas_vacias(aplicacion):
    from views.import_results_view import SavedOffersDialog

    dialogo = SavedOffersDialog(_resultado(), [], None)

    assert dialogo.total.text() == '0 oferta(s) guardada(s)'
    assert dialogo.windowTitle() == 'Datos guardados · Distribuidora LimpiaSur'
    assert dialogo.objectName() == 'SavedOffersDialog'
    assert dialogo.width() >= 1100
    assert dialogo.height() >= 650
    assert dialogo.minimumWidth() >= 950
    assert dialogo.minimumHeight() >= 540
    assert dialogo.tabla.objectName() == 'savedOffersTable'
    assert dialogo.tabla.alternatingRowColors() is False
    assert 'QDialog#SavedOffersDialog' in dialogo.styleSheet()
    assert 'QTableWidget#savedOffersTable' in dialogo.styleSheet()
