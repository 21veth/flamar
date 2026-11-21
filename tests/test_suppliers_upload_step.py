from pathlib import Path

import pytest

import views.import_suppliers_view as vista
from views.import_shared import ImportFileError
from views.import_suppliers_view import (
    mensaje_confirmacion,
    texto_confirmacion_validacion,
    validar_seleccion_archivos,
)


def test_acepta_un_archivo_xlsx():
    rutas = validar_seleccion_archivos(['Proveedor_01_LimpiaSur_ZEYVER.xlsx'])
    assert isinstance(rutas, list)
    assert len(rutas) == 1
    assert isinstance(rutas[0], Path)
    assert rutas[0].name == 'Proveedor_01_LimpiaSur_ZEYVER.xlsx'


def test_acepta_extension_en_mayusculas():
    rutas = validar_seleccion_archivos(['LIMPIASUR.XLSX'])
    assert rutas[0].suffix == '.XLSX'


@pytest.mark.parametrize(
    'nombre', ['LimpiaSur.xls', 'LimpiaSur.csv', 'LimpiaSur.txt', 'LimpiaSur']
)
def test_rechaza_otras_extensiones(nombre):
    with pytest.raises(ImportFileError, match='xlsx'):
        validar_seleccion_archivos([nombre])


def test_acepta_varios_archivos():
    rutas = validar_seleccion_archivos(['a.xlsx', 'b.xlsx', 'c.xlsx'])
    assert [ruta.name for ruta in rutas] == ['a.xlsx', 'b.xlsx', 'c.xlsx']


def test_rechaza_mas_de_diez_archivos():
    rutas = [f'proveedor_{numero}.xlsx' for numero in range(11)]
    with pytest.raises(ImportFileError, match='máximo 10'):
        validar_seleccion_archivos(rutas)


def test_ignora_rutas_repetidas():
    rutas = validar_seleccion_archivos(['a.xlsx', 'a.xlsx', 'b.xlsx'])
    assert len(rutas) == 2


def test_rechaza_seleccion_vacia():
    with pytest.raises(ImportFileError, match='al menos un archivo'):
        validar_seleccion_archivos([])


def test_confirmacion_muestra_pregunta_y_nombre():
    titulo, pregunta, nombre = texto_confirmacion_validacion(
        'Proveedor_01_LimpiaSur_ZEYVER.xlsx'
    )
    assert titulo == 'Validar archivo'
    assert pregunta == '¿Estás seguro de validar este archivo?'
    assert nombre == 'Proveedor_01_LimpiaSur_ZEYVER.xlsx'


def test_mensaje_tras_confirmar_incluye_nombre():
    mensaje = mensaje_confirmacion('Proveedor_01_LimpiaSur_ZEYVER.xlsx')
    assert 'confirmado' in mensaje
    assert 'Proveedor_01_LimpiaSur_ZEYVER.xlsx' in mensaje


def test_texto_confirmacion_varios_archivos():
    titulo, pregunta, nombres = texto_confirmacion_validacion(
        ['a.xlsx', 'b.xlsx']
    )
    assert titulo == 'Validar archivos'
    assert '2 archivos' in pregunta
    assert nombres == 'a.xlsx\nb.xlsx'


def test_mensaje_tras_confirmar_varios_incluye_todos():
    mensaje = mensaje_confirmacion(['a.xlsx', 'b.xlsx'])
    assert '2 archivos' in mensaje
    assert 'a.xlsx' in mensaje and 'b.xlsx' in mensaje


def test_grupos_demo_usa_el_catalogo_y_el_proveedor():
    tab = vista.SuppliersImportTab.__new__(vista.SuppliersImportTab)
    tab.demo_catalog = vista._demo_catalog()
    grupos = tab._grupos_demo()
    assert grupos[0]['proveedor'] == 'LimpiaSur'
    assert grupos[0]['archivo'] == 'LimpiaSur.xlsx'
    assert len(grupos[0]['productos']) == len(tab.demo_catalog)
