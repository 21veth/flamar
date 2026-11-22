import pytest
from PySide6.QtWidgets import QApplication

from controllers.proveedores_import_controller import ProveedoresImportController


@pytest.fixture(scope='module')
def aplicacion():
    return QApplication.instance() or QApplication([])


class FakeServicio:
    def __init__(self, resultado=None, error=None):
        self.resultado = ['OK'] if resultado is None else resultado
        self.error = error
        self.llamadas = []

    def preparar(self, rutas, id_usuario=None):
        self.llamadas.append(('preparar', rutas, id_usuario))
        if self.error is not None:
            raise self.error
        return self.resultado

    def preparar_demo(self, grupos):
        self.llamadas.append(('preparar_demo', grupos))
        return self.resultado

    def descartar(self, id_importacion):
        self.llamadas.append(('descartar', id_importacion))
        return True


def test_preparar_emite_resultado(aplicacion):
    servicio = FakeServicio(resultado=['listo'])
    controller = ProveedoresImportController(servicio=servicio)
    recibidos = []
    controller.preparada.connect(recibidos.append)

    assert controller.preparar(['a.xlsx']) is True
    assert recibidos == [['listo']]
    assert servicio.llamadas == [('preparar', ['a.xlsx'], None)]


def test_preparar_propaga_id_usuario(aplicacion):
    servicio = FakeServicio(resultado=['listo'])
    controller = ProveedoresImportController(servicio=servicio)
    recibidos = []
    controller.preparada.connect(recibidos.append)

    assert controller.preparar(['a.xlsx'], id_usuario=7) is True
    assert recibidos == [['listo']]
    assert servicio.llamadas == [('preparar', ['a.xlsx'], 7)]


def test_preparar_demo_emite_resultado(aplicacion):
    servicio = FakeServicio(resultado=['demo'])
    controller = ProveedoresImportController(servicio=servicio)
    recibidos = []
    controller.preparada.connect(recibidos.append)

    assert controller.preparar_demo([{'proveedor': 'LimpiaSur'}]) is True
    assert recibidos == [['demo']]
    assert servicio.llamadas == [('preparar_demo', [{'proveedor': 'LimpiaSur'}])]


def test_fallo_emite_mensaje_real(aplicacion):
    servicio = FakeServicio(error=ValueError('Falta DB_PASSWORD en config/.env.'))
    controller = ProveedoresImportController(servicio=servicio)
    mensajes = []
    controller.fallo.connect(mensajes.append)

    assert controller.preparar(['a.xlsx']) is False
    assert mensajes == ['Falta DB_PASSWORD en config/.env.']


def test_descartar_sin_id_no_llama_al_servicio(aplicacion):
    servicio = FakeServicio()
    controller = ProveedoresImportController(servicio=servicio)
    descartados = []
    controller.descartada.connect(descartados.append)

    assert controller.descartar(None) is False
    assert servicio.llamadas == []
    assert descartados == []
