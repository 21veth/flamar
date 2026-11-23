from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton

from controllers.comparaciones_controller import ComparacionesController
from models.comparacion import (
    ComparacionGuardada,
    DetalleComparacion,
    DetalleComparacionGuardado,
)
from repositories.comparacion_repository import ComparacionRepository
from services.comparacion_service import ComparacionService
from views.comparison_history_view import ComparisonDetailDialog
from views.import_suppliers_view import SuppliersImportTab, confirmar_borrado


@pytest.fixture(scope='module')
def aplicacion():
    return QApplication([])


class RepositorioFake:
    def __init__(self):
        self.guardada = None
        self.actualizada = None
        self.eliminada = None
        self.ofertas = [
            self._oferta(1, 'Proveedor A', 'LIM-01', 'Jabón', Decimal('10')),
            self._oferta(2, 'Proveedor B', 'LIM-01', 'Jabón', Decimal('12')),
            self._oferta(3, 'Proveedor A', 'LIM-02', 'Detergente', Decimal('10')),
            self._oferta(4, 'Proveedor B', 'LIM-02', 'Detergente', Decimal('11')),
        ]

    def _oferta(self, identificador, proveedor, codigo, producto, precio):
        return {
            'id_detalle_cotizacion': identificador,
            'proveedor': proveedor,
            'codigo': codigo,
            'producto': producto,
            'categoria': 'Limpieza',
            'precio_unitario': precio,
            'compra_minima': 2,
            'stock_disponible': 50,
            'descuento_desde': None,
            'descuento_porcentaje': Decimal('0.1'),
            'entrega_dias': 2,
        }

    def obtener_ofertas_guardadas(self, ids_importacion):
        return self.ofertas

    def obtener_importaciones_sin_comparacion(self, id_usuario):
        return []

    def obtener_id_proveedor(self, nombre):
        return 5 if nombre == 'Proveedor A' else None

    def guardar(self, comparacion):
        self.guardada = comparacion
        return 88

    def actualizar(self, id_comparacion, id_usuario, nombre, tipo_productos, justificacion):
        self.actualizada = (id_comparacion, id_usuario, nombre, tipo_productos, justificacion)
        return 1

    def eliminar(self, id_comparacion, id_usuario):
        self.eliminada = (id_comparacion, id_usuario)
        return 1

    def listar(self, id_usuario, **filtros):
        return []

    def obtener_detalle(self, id_comparacion, id_usuario=None):
        return None


def _matriz():
    return [
        {
            'product': 'Jabón',
            'category': 'Limpieza',
            'offers': {
                'Proveedor A': {'code': 'LIM-01', 'product': 'Jabón', 'price': Decimal('10')},
                'Proveedor B': {'code': 'LIM-01', 'product': 'Jabón', 'price': Decimal('12')},
            },
            'best_price': Decimal('10'),
            'best_provider': 'Proveedor A',
        },
        {
            'product': 'Detergente',
            'category': 'Limpieza',
            'offers': {
                'Proveedor A': {'code': 'LIM-02', 'product': 'Detergente', 'price': Decimal('10')},
                'Proveedor B': {'code': 'LIM-02', 'product': 'Detergente', 'price': Decimal('11')},
            },
            'best_price': Decimal('10'),
            'best_provider': 'Proveedor A',
        },
    ]


def test_servicio_guarda_snapshot_histórico(aplicacion):
    repositorio = RepositorioFake()
    servicio = ComparacionService(repositorio)

    resultado = servicio.guardar(
        'Productos de limpieza',
        'Limpieza',
        1,
        [10, 11],
        {'recommended': 'Proveedor A', 'advantage': Decimal('3')},
        _matriz(),
        ['Tuvo el mejor precio', 'Cumplió el stock'],
    )

    assert resultado == 88
    guardada = repositorio.guardada
    assert guardada.nombre == 'Productos de limpieza'
    assert guardada.id_proveedor_recomendado == 5
    assert guardada.proveedor_recomendado_nombre == 'Proveedor A'
    assert guardada.costo_proveedor_recomendado == Decimal('20')
    assert guardada.costo_compra_combinada == Decimal('20')
    assert guardada.ahorro_estimado == Decimal('3')
    assert guardada.costo_referencia == Decimal('23')
    assert guardada.justificacion == 'Tuvo el mejor precio\nCumplió el stock'
    assert len(guardada.detalles) == 4
    assert all(detalle.precio_evaluado for detalle in guardada.detalles)
    assert all(detalle.costo_total_linea for detalle in guardada.detalles)
    assert all(detalle.proveedor for detalle in guardada.detalles)
    assert all(detalle.producto for detalle in guardada.detalles)


def test_servicio_sincroniza_importaciones_previas(aplicacion):
    repositorio = RepositorioFake()
    repositorio.obtener_importaciones_sin_comparacion = lambda id_usuario: [7, 8]
    servicio = ComparacionService(repositorio)

    resultado = servicio.sincronizar_desde_importaciones(1)

    assert resultado == 88
    assert repositorio.guardada.nombre == 'Comparación de 2 proveedores'
    assert repositorio.guardada.proveedor_recomendado_nombre == 'Proveedor A'
    assert 'importaciones confirmadas previamente' in repositorio.guardada.justificacion
    assert len(repositorio.guardada.detalles) == 4


def test_servicio_editary_borrar_comparacion(aplicacion):
    repositorio = RepositorioFake()
    servicio = ComparacionService(repositorio)

    assert servicio.editar(12, 1, 'Nuevo nombre', 'Limpieza', 'Razón editada') == 12
    assert repositorio.actualizada == (
        12, 1, 'Nuevo nombre', 'Limpieza', 'Razón editada'
    )
    assert servicio.eliminar(12, 1) == 12
    assert repositorio.eliminada == (12, 1)


def test_controlador_emite_senales_del_historial(aplicacion):
    servicio = SimpleNamespace(
        guardar=lambda *argumentos: 91,
        sincronizar_desde_importaciones=lambda *argumentos: 92,
        editar=lambda *argumentos: 12,
        eliminar=lambda *argumentos: 12,
        listar=lambda *argumentos, **kwargs: ['a'],
        obtener_detalle=lambda *argumentos: 'detalle',
    )
    controlador = ComparacionesController(servicio=servicio)
    guardadas = []
    sincronizadas = []
    editadas = []
    eliminadas = []
    listados = []
    detalles = []
    controlador.guardada.connect(guardadas.append)
    controlador.sincronizada.connect(sincronizadas.append)
    controlador.editada.connect(editadas.append)
    controlador.eliminada.connect(eliminadas.append)
    controlador.listado.connect(listados.append)
    controlador.detalle_consultado.connect(detalles.append)

    controlador.guardar('Nombre', 'Limpieza', 1, [1], {}, [], [])
    controlador.sincronizar_historial(1)
    controlador.editar(12, 1, 'Nombre', 'Limpieza', 'Razón')
    controlador.eliminar(12, 1)
    controlador.listar(1)
    controlador.obtener_detalle(91, 1)

    assert guardadas == [91]
    assert sincronizadas == [92]
    assert editadas == [12]
    assert eliminadas == [12]
    assert listados == [['a']]
    assert detalles == ['detalle']


def test_historial_esta_al_lado_de_nueva_comparacion(aplicacion):
    tab = SuppliersImportTab()

    assert tab.new_button.parent() is tab.history_button.parent()
    assert tab.history_button.text().startswith('Historial')
    assert tab.historial_busqueda is not None
    assert tab.historial_categoria is not None
    assert tab.historial_proveedor is not None
    assert tab.historial_fecha.specialValueText() == 'Todas las fechas'
    assert tab.historial_fecha.date() == tab.historial_fecha.minimumDate()
    assert not hasattr(tab, 'historial_estado')
    assert tab.historial_estado_texto.parent() is None

    opciones = [tab.category_combo.itemText(i) for i in range(tab.category_combo.count())]
    assert tab.category_combo.isEditable()
    assert {'Limpieza', 'Dulces', 'Bebidas', 'Snacks', 'Ropa', 'Juguetes'} <= set(opciones)
    tab.category_combo.setCurrentText('Artesanías')
    assert tab.category_combo.currentText() == 'Artesanías'


def test_tabla_historial_muestra_dto(aplicacion):
    tab = SuppliersImportTab()
    tab.comparisons = [
        ComparacionGuardada(
            id_comparacion=12,
            nombre='Productos de limpieza',
            fecha_creacion=datetime(2026, 11, 19, 10, 30),
            estado='completada',
            tipo_productos='Limpieza',
            proveedor_recomendado='HigieneTotal',
            proveedores='HigieneTotal · CleanMax',
            productos=30,
            ahorro_estimado=Decimal('180'),
        )
    ]

    tab._refresh_history()

    assert tab.history_table.rowCount() == 1
    assert tab.history_table.columnCount() == 8
    encabezados = [
        tab.history_table.horizontalHeaderItem(column).text()
        for column in range(tab.history_table.columnCount())
    ]
    assert encabezados == [
        'Comparación',
        'Categoría principal',
        'Proveedor con mejor precio',
        'Fecha',
        'Hora',
        'Productos',
        'Ahorro',
        'Acciones',
    ]
    assert tab.history_table.item(0, 0).text() == 'Productos de limpieza'
    assert tab.history_table.item(0, 1).text() == 'Limpieza'
    assert tab.history_table.item(0, 2).text() == 'HigieneTotal'
    assert tab.history_table.item(0, 3).text() == '19/11/2026'
    assert tab.history_table.item(0, 4).text() == '10:30'
    assert tab.history_table.item(0, 5).text() == '30'
    assert '180' in tab.history_table.item(0, 6).text()
    assert tab.history_button.text() == 'Historial · 1'


def test_acciones_historial_son_iconos(aplicacion, monkeypatch):
    tab = SuppliersImportTab()
    tab.comparisons = [
        ComparacionGuardada(
            id_comparacion=12,
            nombre='Productos de limpieza',
            fecha_creacion=datetime(2026, 11, 19, 10, 30),
        )
    ]
    llamadas = []
    monkeypatch.setattr(
        tab, '_open_comparison', lambda index: llamadas.append(('mostrar', index))
    )
    monkeypatch.setattr(
        tab, '_editar_comparacion', lambda index: llamadas.append(('editar', index))
    )
    monkeypatch.setattr(
        tab, '_borrar_comparacion', lambda index: llamadas.append(('borrar', index))
    )

    tab._refresh_history()

    nombres = ('historyMostrarButton', 'historyEditarButton', 'historyBorrarButton')
    botones = {
        boton.objectName(): boton
        for boton in tab.history_table.cellWidget(0, 7).findChildren(QPushButton)
    }
    assert set(botones) == set(nombres)
    assert [botones[nombre].toolTip() for nombre in nombres] == [
        'Mostrar', 'Editar', 'Borrar'
    ]
    assert all(boton.text() == '' for boton in botones.values())
    assert all(not boton.icon().isNull() for boton in botones.values())

    for nombre in nombres:
        botones[nombre].click()

    assert llamadas == [
        ('mostrar', 0),
        ('editar', 0),
        ('borrar', 0),
    ]


def test_detalle_muestra_recomendacion_y_tabla_guardada(aplicacion):
    comparacion = ComparacionGuardada(
        id_comparacion=12,
        nombre='Productos de limpieza',
        fecha_creacion=datetime(2026, 11, 19, 10, 30),
        estado='completada',
        tipo_productos='Limpieza',
        proveedor_recomendado='HigieneTotal',
        costo_proveedor_recomendado=Decimal('1250'),
        costo_compra_combinada=Decimal('1190'),
        ahorro_estimado=Decimal('180'),
        justificacion='Menor costo total entre los proveedores individuales.',
    )
    detalle = DetalleComparacion(
        comparacion=comparacion,
        filas=[
            DetalleComparacionGuardado(
                id_detalle_comparacion=1,
                proveedor='HigieneTotal',
                producto='Jabón',
                categoria='Limpieza',
                precio_evaluado=Decimal('10'),
                cantidad_requerida=2,
                costo_total_linea=Decimal('20'),
                seleccionado_combinada=True,
            )
        ],
    )
    dialogo = ComparisonDetailDialog(detalle)

    etiquetas = [
        etiqueta.text() for etiqueta in dialogo.findChildren(QLabel)
    ]
    assert dialogo.windowTitle().startswith('Detalle de comparación')
    assert dialogo.tabla.rowCount() == 1
    assert 'HigieneTotal' in etiquetas
    assert 'Menor costo total entre los proveedores individuales.' in etiquetas
    assert not any(
        boton.objectName() == 'comparisonPrimary'
        for boton in dialogo.findChildren(QPushButton)
    )


def test_preparar_repeticion_conserva_nombre_y_categoria(aplicacion):
    tab = SuppliersImportTab()

    tab._preparar_repeticion({
        'nombre': 'Productos de limpieza',
        'tipo_productos': 'Limpieza',
    })

    assert tab.name_edit.text() == 'Productos de limpieza (repetida)'
    assert tab.category_combo.currentText() == 'Limpieza'


def test_confirmacion_guarda_comparacion_automaticamente(aplicacion, monkeypatch):
    tab = SuppliersImportTab()
    tab._sesion = SimpleNamespace(id_usuario=1)
    tab._guardado_demo = False
    tab.files = [{'preparada': object(), 'provider': 'Proveedor A'}]
    decision = {'recommended': 'Proveedor A', 'advantage': 3}
    guardados = []
    consultados = []
    resumen = []

    monkeypatch.setattr(
        tab, '_reconstruir_ofertas',
        lambda: setattr(tab, 'offers', [{'price': 10}]),
    )
    monkeypatch.setattr(
        tab, '_refresh_matrix',
        lambda: setattr(tab, 'matrix_rows_data', [{'product': 'Jabón'}]),
    )
    monkeypatch.setattr(tab, '_refresh_decision', lambda: decision)
    monkeypatch.setattr(tab, '_guardar_comparacion_actual', guardados.append)
    monkeypatch.setattr(
        tab._controller, 'consultar_resultado', lambda ids: consultados.append(ids)
    )
    monkeypatch.setattr(
        tab._controller, 'consultar_resumen', lambda: resumen.append(True)
    )

    resultados = [
        SimpleNamespace(id_importacion=7, proveedor='Proveedor A'),
        SimpleNamespace(id_importacion=8, proveedor='Proveedor B'),
    ]
    tab._al_guardar(resultados)

    assert tab._ids_importacion_actuales == [7, 8]
    assert consultados == [[7, 8]]
    assert guardados == [decision]
    assert resumen == [True]


def test_abrir_comparativa_no_sale_de_resultados(aplicacion, monkeypatch):
    tab = SuppliersImportTab()
    tab.files = [{'preparada': object(), 'provider': 'Proveedor A'}]
    decision = {'recommended': 'Proveedor A'}
    guardados = []
    pasos = []

    monkeypatch.setattr(
        tab, '_reconstruir_ofertas',
        lambda: setattr(tab, 'offers', [{'price': 10}]),
    )
    monkeypatch.setattr(
        tab, '_refresh_matrix',
        lambda: setattr(tab, 'matrix_rows_data', [{'product': 'Jabón'}]),
    )
    monkeypatch.setattr(tab, '_refresh_decision', lambda: decision)
    monkeypatch.setattr(tab, '_guardar_comparacion_actual', guardados.append)
    monkeypatch.setattr(tab, '_go_step', pasos.append)

    tab._al_cambiar_tab_resultado(1)

    assert guardados == [decision]
    assert pasos == []


def test_clic_historial_recarga_listado(aplicacion, monkeypatch):
    tab = SuppliersImportTab()
    recargas = []
    monkeypatch.setattr(tab, '_recargar_historial', lambda: recargas.append(True))

    tab.history_button.click()

    assert tab.pages.currentIndex() == 1
    assert recargas == [True]


def test_historial_se_sincroniza_al_abrir(aplicacion, monkeypatch):
    tab = SuppliersImportTab()
    sincronizaciones = []
    monkeypatch.setattr(tab, '_historial_sincronizado', False)
    monkeypatch.setattr(
        tab._comparaciones_controller,
        'sincronizar_historial',
        lambda id_usuario: sincronizaciones.append(id_usuario),
    )

    tab._ir_historial()

    assert sincronizaciones == [tab._id_usuario()]


def test_confirmacion_demo_no_guarda_comparacion(aplicacion, monkeypatch):
    tab = SuppliersImportTab()
    tab._sesion = SimpleNamespace(id_usuario=1)
    tab._guardado_demo = True
    tab.files = [{'preparada': object(), 'provider': 'Proveedor A'}]
    guardados = []

    monkeypatch.setattr(
        tab, '_reconstruir_ofertas',
        lambda: setattr(tab, 'offers', [{'price': 10}]),
    )
    monkeypatch.setattr(
        tab, '_refresh_matrix',
        lambda: setattr(tab, 'matrix_rows_data', [{'product': 'Jabón'}]),
    )
    monkeypatch.setattr(
        tab, '_refresh_decision',
        lambda: {'recommended': 'Proveedor A', 'advantage': 0},
    )
    monkeypatch.setattr(
        tab._comparaciones_controller, 'guardar', lambda *args: guardados.append(args)
    )
    monkeypatch.setattr(tab._controller, 'consultar_resultado', lambda ids: None)
    monkeypatch.setattr(tab._controller, 'consultar_resumen', lambda: None)

    tab._al_guardar([SimpleNamespace(id_importacion=7, proveedor='Proveedor A')])

    assert guardados == []


def test_repositorio_listar_agrupa_por_comparacion(monkeypatch):
    repositorio = ComparacionRepository()
    consultas = []

    def consultar(sql, parametros):
        consultas.append(sql)
        return [(
            12,
            'Productos de limpieza',
            datetime(2026, 11, 19, 10, 30),
            'completada',
            'Limpieza',
            'HigieneTotal',
            Decimal('1250'),
            Decimal('1190'),
            Decimal('1430'),
            Decimal('180'),
            '',
            'HigieneTotal · CleanMax',
            30,
        )]

    monkeypatch.setattr(repositorio, '_consultar', consultar)

    comparaciones = repositorio.listar(1)

    assert len(comparaciones) == 1
    assert comparaciones[0].productos == 30
    grupo = consultas[0].split('GROUP BY', 1)[1]
    assert 'prd.codigo' not in grupo
    assert 'prd.nombre' not in grupo


def test_repositorio_listar_filtra_por_fecha(monkeypatch):
    repositorio = ComparacionRepository()
    consultas = []

    def consultar(sql, parametros):
        consultas.append((sql, parametros))
        return []

    monkeypatch.setattr(repositorio, '_consultar', consultar)

    repositorio.listar(1, fecha='2026-11-19')

    sql, parametros = consultas[0]
    assert 'c.fecha_creacion::date = NULLIF(%s, \'\')::date' in sql
    assert parametros[-2:] == ('2026-11-19', '2026-11-19')
    assert 'c.estado = %s' not in sql


def test_confirmar_borrado_usa_dialogo_blanco(aplicacion, monkeypatch):
    dialogos = []

    def ejecutar(dialogo):
        dialogos.append(dialogo)
        return QDialog.Accepted

    monkeypatch.setattr(QDialog, 'exec', ejecutar)

    assert confirmar_borrado('Productos de limpieza') is True
    assert dialogos[0].windowTitle() == 'Borrar comparación'
    assert 'background:#ffffff' in dialogos[0].styleSheet()
    assert 'Sí, borrar' in [
        boton.text() for boton in dialogos[0].findChildren(QPushButton)
    ]
    assert 'como si nunca se hubiera subido' in dialogos[0].findChild(QLabel).text()


def test_historial_no_tiene_boton_nueva_comparacion(aplicacion):
    tab = SuppliersImportTab()

    textos = [
        boton.text() for boton in tab.history_view.findChildren(QPushButton)
    ]

    assert not any('Nueva comparación' in texto for texto in textos)
    assert tab.new_button.text() == 'Nueva comparación'


class _CursorFake:
    def __init__(self):
        self.consultas = []
        self.parametros = []
        self.resultado = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        return False

    def execute(self, consulta, parametros=None):
        consulta_normalizada = ' '.join(consulta.split())
        self.consultas.append(consulta_normalizada)
        self.parametros.append(parametros)
        if 'SELECT DISTINCT imp.id_importacion' in consulta_normalizada:
            self.resultado = [(7,)]
        elif 'SELECT DISTINCT dcomp.id_comparacion' in consulta_normalizada:
            self.resultado = [(6,)]
        elif 'SELECT DISTINCT cot.id_proveedor' in consulta_normalizada:
            self.resultado = [(3,), (4,)]
        else:
            self.resultado = []

    def fetchall(self):
        return self.resultado


class _ConexionFake:
    def __init__(self, cursor):
        self.cursor_fake = cursor
        self.confirmada = False
        self.revertida = False
        self.cerrada = False

    def cursor(self):
        return self.cursor_fake

    def commit(self):
        self.confirmada = True

    def rollback(self):
        self.revertida = True

    def close(self):
        self.cerrada = True


def test_eliminar_borra_todos_los_datos_del_excel(monkeypatch):
    cursor = _CursorFake()
    conexion = _ConexionFake(cursor)
    monkeypatch.setattr(
        'repositories.comparacion_repository.obtener_conexion', lambda: conexion
    )

    assert ComparacionRepository().eliminar(6, 1) == 1

    consultas = ' '.join(cursor.consultas)
    for tabla in (
        'public.detalle_comparacion',
        'public.comparaciones',
        'public.errores_importacion',
        'public.detalle_cotizacion',
        'public.cotizaciones',
        'public.importaciones',
        'public.proveedores',
    ):
        assert f'DELETE FROM {tabla}' in consultas
    assert any(
        'DELETE FROM public.importaciones' in consulta for consulta in cursor.consultas
    )
    assert conexion.confirmada
    assert not conexion.revertida
    assert conexion.cerrada
