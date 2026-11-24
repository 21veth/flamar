import hashlib
from decimal import Decimal

import pytest

from services.importacion_proveedores_service import (
    COLUMNS,
    ContextoValidacion,
    ImportacionProveedoresService,
    combinar_reportes,
)
from views.import_shared import TableData


class FakeContexto:
    def __init__(self, hashes=(), productos=None, categorias=None, proveedores=None):
        self.hashes = set(hashes)
        self.productos = productos or {}
        self.categorias = set(categorias or ())
        self.proveedores = set(proveedores or ())

    def existe_hash(self, hash_archivo):
        return hash_archivo in self.hashes

    def buscar_producto(self, codigo):
        return self.productos.get(codigo)

    def categoria_existe(self, nombre):
        return not self.categorias or nombre in self.categorias

    def proveedor_existe(self, nombre):
        return not self.proveedores or nombre in self.proveedores


class ContextoConCiclo(ContextoValidacion):
    def __init__(self):
        self.entradas = 0
        self.salidas = 0

    def __enter__(self):
        self.entradas += 1
        return self

    def __exit__(self, *argumentos):
        self.salidas += 1
        return False


class FakePersistencia:
    def __init__(self):
        self.intentos = []
        self.errores = []
        self.estados = []

    def crear_intento(self, preparada, id_usuario, estado):
        self.intentos.append((preparada.proveedor, id_usuario, estado))
        return 99

    def registrar_errores(self, id_intento, errores):
        self.errores.append((id_intento, list(errores)))

    def actualizar_estado(self, id_intento, estado):
        self.estados.append((id_intento, estado))

    def guardar(self, preparadas, excluidas=None, id_usuario=None):
        return ['guardado']

    def descartar(self, id_intento):
        return True


def _archivo(tmp_path, contenido=b'contenido', nombre='cotizacion.xlsx'):
    ruta = tmp_path / nombre
    ruta.write_bytes(contenido)
    return ruta


def _tabla(headers, rows, sheet='Catalogo', name='cotizacion.xlsx'):
    return TableData(
        path=None,
        name=name,
        extension='.xlsx',
        size_bytes=100,
        modified=None,
        headers=headers,
        rows=rows,
        total=len(rows),
        sheet=sheet,
    )


def _servicio(contexto=None, persistencia=None, lector=None):
    return ImportacionProveedoresService(
        lector=lector or (lambda path: _tabla(list(COLUMNS), [])),
        contexto=contexto,
        persistencia=persistencia,
    )


def test_por_defecto_no_usa_base_de_datos(tmp_path):
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), [
        ['LimpiaSur', 'P001', 'Lejía 1 L', 'Limpieza', 'Blanco', '1 L',
         '5.20', '10', '1', '5', '0.10', '2'],
    ]))

    assert servicio._contexto is None
    assert servicio._persistencia is None

    preparadas = servicio.preparar([_archivo(tmp_path)])

    assert len(preparadas) == 1
    assert preparadas[0].reporte.es_valido is True


def test_preparar_normaliza_valores_y_reporta_errores(tmp_path):
    rows = [
        ['LimpiaSur', 'P001', 'Lejía 1 L', 'Limpieza', 'Blanco', '1 L',
         '5.20', '10', '1', '5', '0.10', '2'],
        ['LimpiaSur', 'P002', '', 'Limpieza', '', '', '3.00', '0', '1', '0', '0', '0'],
        ['LimpiaSur', 'P003', 'Desengrasante', 'Limpieza', '', '', '-2', '0', '1', '0', '0', '0'],
    ]
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.proveedor == 'LimpiaSur'
    assert len(preparada.filas) == 1
    assert preparada.reporte.correctas == 1
    assert preparada.reporte.total_errores == 2
    assert preparada.reporte.es_valido is False
    fila = preparada.filas[0]
    assert fila.precio_unitario == Decimal('5.2')
    assert fila.stock_disponible == 10
    assert fila.compra_minima == 1
    assert fila.descuento_desde == 5
    assert fila.descuento_porcentaje == Decimal('0.1')
    assert fila.entrega_dias == 2
    assert fila.codigo == 'P001'
    assert fila.marca == 'Blanco'
    assert fila.presentacion == '1 L'


def test_preparar_exige_hoja_catalogo_en_excel(tmp_path):
    ruta = _archivo(tmp_path)
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), [], sheet='Ventas'))

    preparada = servicio.preparar([ruta])[0]

    assert preparada.reporte.es_valido is False
    assert any(
        'Catalogo' in aviso.problema for aviso in preparada.reporte.errores
    )


def test_preparar_acepta_hash_repetido(tmp_path):
    contenido = b'Proveedor,Producto,LimpiaSur,Lejia\n'
    hash_conocido = hashlib.sha256(contenido).hexdigest()
    servicio = _servicio(
        contexto=FakeContexto(hashes=[hash_conocido]),
        lector=lambda path: _tabla(list(COLUMNS), []),
    )

    preparadas = servicio.preparar([_archivo(tmp_path, contenido)])

    assert len(preparadas) == 1
    assert preparadas[0].archivo.hash_archivo == hash_conocido


def test_preparar_usa_contexto_con_manejador(tmp_path):
    contexto = ContextoConCiclo()
    servicio = _servicio(
        contexto=contexto,
        lector=lambda path: _tabla(list(COLUMNS), []),
    )

    servicio.preparar([_archivo(tmp_path)])

    assert contexto.entradas == 1
    assert contexto.salidas == 1


def test_alias_de_encabezado_genera_advertencia_no_error(tmp_path):
    headers = [
        'Proveedor', 'Código producto', 'Producto', 'Categoría', 'Marca',
        'Presentación', 'Precio unitario', 'Stock', 'Cantidad mínima',
        'Descuento desde (unid.)', 'Descuento porcentaje', 'Entrega (días)',
    ]
    rows = [
        ['LimpiaSur', 'P001', 'Lejía 1 L', 'Limpieza', 'Blanco', '1 L',
         '5.20', '10', '1', '0', '0', '2'],
    ]
    servicio = _servicio(lector=lambda path: _tabla(headers, rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.reporte.total_errores == 0
    assert preparada.reporte.total_advertencias >= 1
    assert any(
        'alterno' in aviso.problema for aviso in preparada.reporte.advertencias
    )


def test_varios_proveedores_es_error_bloqueante(tmp_path):
    rows = [
        ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', '', '', '5.20', '10', '1', '0', '0', '2'],
        ['OtroProveedor', 'P002', 'Jabón', 'Limpieza', '', '', '3.00', '5', '1', '0', '0', '1'],
    ]
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.reporte.es_valido is False
    assert any('uno solo' in aviso.problema for aviso in preparada.reporte.errores)


def test_codigo_duplicado_es_error(tmp_path):
    rows = [
        ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', '', '', '5.20', '10', '1', '0', '0', '2'],
        ['LimpiaSur', 'P001', 'Jabón', 'Limpieza', '', '', '3.00', '5', '1', '0', '0', '1'],
    ]
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.reporte.es_valido is False
    assert any('duplicado' in aviso.problema for aviso in preparada.reporte.errores)


def test_descuento_fuera_de_rango_es_error(tmp_path):
    rows = [
        ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', '', '', '5.20', '10', '1', '0', '5', '2'],
    ]
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.reporte.es_valido is False
    assert any('entre 0 y 1' in aviso.problema for aviso in preparada.reporte.errores)


def test_codigo_existente_con_otra_identidad_es_error(tmp_path):
    contexto = FakeContexto(
        productos={'P001': {'nombre': 'Otro', 'marca': 'X', 'presentacion': 'Y'}}
    )
    rows = [
        ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', 'Blanco', '1 L',
         '5.20', '10', '1', '0', '0', '2'],
    ]
    servicio = _servicio(contexto=contexto, lector=lambda path: _tabla(list(COLUMNS), rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.reporte.es_valido is False
    assert any('otro producto' in aviso.problema for aviso in preparada.reporte.errores)


def test_categoria_y_proveedor_inexistentes_son_advertencias(tmp_path):
    contexto = FakeContexto(categorias={'Limpieza'}, proveedores={'Otro'})
    rows = [
        ['LimpiaSur', 'P001', 'Lejía', 'Detergentes', '', '', '5.20', '10', '1', '0', '0', '2'],
    ]
    servicio = _servicio(contexto=contexto, lector=lambda path: _tabla(list(COLUMNS), rows))

    preparada = servicio.preparar([_archivo(tmp_path)])[0]

    assert preparada.reporte.es_valido is True
    assert preparada.reporte.total_advertencias >= 2


def test_registrar_validacion_usa_persistencia_inyectada(tmp_path):
    persistencia = FakePersistencia()
    rows = [
        ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', '', '', '5.20', '10', '1', '0', '0', '2'],
    ]
    servicio = _servicio(persistencia=persistencia, lector=lambda path: _tabla(list(COLUMNS), rows))

    preparadas = servicio.preparar([_archivo(tmp_path)], id_usuario=7)

    assert preparadas[0].id_importacion == 99
    assert persistencia.intentos == [('LimpiaSur', 7, 'validado')]
    assert persistencia.errores == [(99, [])]


def test_registrar_validacion_marca_con_errores(tmp_path):
    persistencia = FakePersistencia()
    rows = [
        ['LimpiaSur', 'P001', '', 'Limpieza', '', '', '5.20', '10', '1', '0', '0', '2'],
    ]
    servicio = _servicio(persistencia=persistencia, lector=lambda path: _tabla(list(COLUMNS), rows))

    servicio.preparar([_archivo(tmp_path)], id_usuario=1)

    assert persistencia.intentos[0][2] == 'con_errores'


def test_confirmar_sin_persistencia_no_guarda(tmp_path):
    servicio = _servicio(lector=lambda path: _tabla(list(COLUMNS), []))

    assert servicio.confirmar([]) == []
    assert servicio.descartar(5) is False


def test_preparar_varios_archivos_devuelve_un_resultado_por_proveedor(tmp_path):
    def lector(path):
        proveedor = path.stem
        fila = [proveedor, 'P001', 'Lejía', 'Limpieza', '', '',
                '5.20', '10', '1', '0', '0', '2']
        return _tabla(list(COLUMNS), [fila], name=path.name)

    servicio = _servicio(lector=lector)

    resultados = servicio.preparar([
        _archivo(tmp_path, nombre='LimpiaSur.xlsx'),
        _archivo(tmp_path, nombre='OtroProveedor.xlsx'),
    ])

    assert len(resultados) == 2
    assert [item.proveedor for item in resultados] == ['LimpiaSur', 'OtroProveedor']
    assert all(item.reporte.es_valido for item in resultados)


def test_proveedor_repetido_entre_archivos_es_error(tmp_path):
    fila = ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', '', '',
            '5.20', '10', '1', '0', '0', '2']
    servicio = _servicio(
        lector=lambda path: _tabla(list(COLUMNS), [fila], name=path.name)
    )

    resultados = servicio.preparar([
        _archivo(tmp_path, nombre='a.xlsx'),
        _archivo(tmp_path, nombre='b.xlsx'),
    ])

    assert all(not item.reporte.es_valido for item in resultados)
    assert all(
        any('varios archivos' in aviso.problema for aviso in item.reporte.errores)
        for item in resultados
    )
    nombres = ', '.join(item.archivo.nombre for item in resultados)
    assert 'a.xlsx' in nombres and 'b.xlsx' in nombres


def test_combinar_reportes_suma_errores_y_filas(tmp_path):
    correcta = ['LimpiaSur', 'P001', 'Lejía', 'Limpieza', '', '',
                '5.20', '10', '1', '0', '0', '2']
    con_error = ['Otro', 'P002', '', 'Limpieza', '', '',
                 '5.20', '10', '1', '0', '0', '2']

    def lector(path):
        fila = correcta if path.name == 'bueno.xlsx' else con_error
        return _tabla(list(COLUMNS), [fila], name=path.name)

    servicio = _servicio(lector=lector)
    resultados = servicio.preparar([
        _archivo(tmp_path, nombre='bueno.xlsx'),
        _archivo(tmp_path, nombre='malo.xlsx'),
    ])

    resumen = combinar_reportes(resultados)

    assert resumen.total_filas == 2
    assert resumen.correctas == 1
    assert resumen.total_errores == 1
    assert resumen.es_valido is False
    assert resultados[1].archivo.nombre == 'malo.xlsx'
    assert resultados[1].reporte.total_errores == 1
