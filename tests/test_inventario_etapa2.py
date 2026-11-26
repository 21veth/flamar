import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from models.importacion_inventario import (
    ArchivoIngreso,
    ConfirmacionIngreso,
    FilaIngreso,
    FilaVistaPreviaIngreso,
    ReporteValidacionIngreso,
    ResultadoGuardadoIngreso,
)
from services.importacion_inventarios_service import (
    COLUMNS,
    ImportacionIngresosService,
)
from views.import_inventory_view import InventoryImportTab
from views.import_shared import TableData


class ContextoFalso:
    def __init__(
        self,
        hash_duplicado=False,
        proveedores=('LimpiaSur',),
        categorias=('Limpieza',),
        productos=None,
    ):
        self.hash_duplicado = hash_duplicado
        self.proveedores = proveedores
        self.categorias = categorias
        self.productos = productos or {}

    def existe_hash(self, _hash):
        return self.hash_duplicado

    def proveedor_existe(self, nombre):
        return nombre in self.proveedores

    def categoria_existe(self, nombre):
        return nombre in self.categorias

    def buscar_producto(self, codigo, nombre, marca, presentacion):
        return self.productos.get(codigo)


class PersistenciaFalsa:
    def __init__(self):
        self.intentos = []
        self.errores = []

    def crear_intento(self, reporte, estado, id_usuario=None):
        self.intentos.append((
            reporte.archivo.nombre,
            estado,
            reporte.total_filas,
            reporte.correctas,
            reporte.total_errores,
            id_usuario,
        ))
        return 99

    def registrar_errores(self, id_intento, errores):
        self.errores.extend(errores)


class ServicioFalso:
    def __init__(self, reporte):
        self.reporte = reporte

    def validar(self, _ruta, _id_usuario=None):
        return self.reporte

    def construir_resumen(self, reporte):
        return ImportacionIngresosService.construir_resumen(reporte)

    def construir_productos_vista_previa(self, reporte):
        return ImportacionIngresosService.construir_productos_vista_previa(reporte)

    def confirmar(self, reporte, id_usuario=None):
        resumen = self.construir_resumen(reporte)
        return ConfirmacionIngreso(
            id_importacion=reporte.id_importacion or 99,
            hash_archivo=reporte.archivo.hash_archivo,
            proveedor=reporte.proveedor,
            archivo=reporte.archivo.nombre,
            resumen=resumen,
            filas=tuple(reporte.filas_validas),
            id_usuario=id_usuario,
        )

    def confirmar_y_guardar(self, reporte, id_usuario=None):
        confirmacion = self.confirmar(reporte, id_usuario)
        return ResultadoGuardadoIngreso(
            id_ingreso=123,
            id_importacion=confirmacion.id_importacion,
            proveedor=confirmacion.proveedor,
            archivo=confirmacion.archivo,
            fecha_ingreso=confirmacion.resumen.fecha_min or date(2026, 11, 15),
            productos=confirmacion.resumen.productos,
            unidades=confirmacion.resumen.total_unidades,
            incidencias=0,
        )

    def obtener_ingreso(self, id_ingreso):
        return None


def _fila(
    codigo='ZEY-L001',
    proveedor='LimpiaSur',
    categoria='Limpieza',
    marca='ZEYVER',
    unidad='Botella',
    cantidad='37',
    stock='5',
    compra='10.00',
    venta='15.00',
    fecha='15/11/2026',
):
    return (
        proveedor,
        codigo,
        'Lejía tradicional 1 L',
        categoria,
        marca,
        'Botella 1 L',
        unidad,
        cantidad,
        stock,
        compra,
        venta,
        fecha,
    )


def _datos(filas, headers=None):
    return TableData(
        path=None,
        name='ingreso.xlsx',
        extension='.xlsx',
        size_bytes=128,
        modified=None,
        headers=list(headers or COLUMNS),
        rows=filas,
        total=len(filas),
    )


class InventarioEtapa2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ruta = Path(self.temp.name) / 'ingreso.xlsx'
        self.ruta.write_bytes(b'contenido')

    def _servicio(self, datos, contexto, persistencia):
        return ImportacionIngresosService(
            lector=lambda _ruta: datos,
            contexto=contexto,
            persistencia=persistencia,
        )

    def test_valida_36_productos_y_persiste_intento(self):
        filas = [
            _fila(codigo=f'ZEY-L{numero:03d}') for numero in range(2, 38)
        ]
        contexto = ContextoFalso()
        persistencia = PersistenciaFalsa()
        servicio = self._servicio(_datos(filas), contexto, persistencia)

        reporte = servicio.validar(self.ruta, 7)

        self.assertEqual(reporte.total_filas, 36)
        self.assertEqual(reporte.correctas, 36)
        self.assertEqual(reporte.proveedor, 'LimpiaSur')
        self.assertTrue(reporte.es_valido)
        self.assertEqual(reporte.id_importacion, 99)
        self.assertEqual(
            persistencia.intentos[0],
            ('ingreso.xlsx', 'validado', 36, 36, 0, 7),
        )
        self.assertEqual(persistencia.errores, [])

    def test_reporte_incluye_todas_las_filas_con_estado(self):
        producto = {
            'nombre': 'Lejía tradicional 1 L',
            'marca': 'ZEYVER',
            'presentacion': 'Botella 1 L',
        }
        filas = [
            _fila(codigo='ZEY-L001'),
            _fila(codigo='ZEY-L002', cantidad='-5'),
            _fila(codigo='ZEY-N001'),
        ]
        contexto = ContextoFalso(productos={'ZEY-L001': producto})
        servicio = self._servicio(
            _datos(filas), contexto, PersistenciaFalsa()
        )

        reporte = servicio.validar(self.ruta)

        self.assertEqual(len(reporte.filas_preview), 3)
        self.assertEqual(
            [fila.estado for fila in reporte.filas_preview],
            ['Válido', 'Error', 'Advertencia'],
        )
        self.assertEqual(reporte.filas_preview[1].codigo, 'ZEY-L002')
        self.assertEqual(reporte.filas_preview[2].codigo, 'ZEY-N001')

    def test_estructura_incompleta_bloquea_y_guarda_error(self):
        headers = [columna for columna in COLUMNS if columna != 'Unidad medida']
        contexto = ContextoFalso()
        persistencia = PersistenciaFalsa()
        servicio = self._servicio(_datos([_fila()], headers), contexto, persistencia)

        reporte = servicio.validar(self.ruta)

        self.assertFalse(reporte.es_valido)
        self.assertEqual(reporte.total_filas, 1)
        self.assertEqual(reporte.correctas, 0)
        self.assertIn('Unidad medida', [aviso.campo for aviso in reporte.errores])
        self.assertEqual(persistencia.intentos[0][1], 'con_errores')
        self.assertEqual(len(persistencia.errores), len(reporte.errores))

    def test_hash_duplicado_no_lee_archivo(self):
        llamadas = []

        def lector(_ruta):
            llamadas.append(True)
            return _datos([_fila()])

        persistencia = PersistenciaFalsa()
        servicio = ImportacionIngresosService(
            lector=lector,
            contexto=ContextoFalso(hash_duplicado=True),
            persistencia=persistencia,
        )

        reporte = servicio.validar(self.ruta)

        self.assertEqual(llamadas, [])
        self.assertEqual(reporte.errores[0].campo, 'Archivo')
        self.assertEqual(persistencia.intentos[0][1], 'con_errores')

    def test_detecta_errores_de_filas_y_advertencia_de_precio(self):
        filas = [
            _fila(codigo='ZEY-001', cantidad='-5'),
            _fila(codigo='ZEY-002', compra=''),
            _fila(codigo='ZEY-003', fecha='no es fecha'),
            _fila(codigo='ZEY-004', unidad='Desconocida'),
            _fila(codigo='ZEY-005', compra='10.00', venta='8.00'),
        ]
        producto = {
            'nombre': 'Lejía tradicional 1 L',
            'marca': 'ZEYVER',
            'presentacion': 'Botella 1 L',
        }
        contexto = ContextoFalso(productos={
            f'ZEY-{numero:03d}': producto for numero in range(1, 6)
        })
        persistencia = PersistenciaFalsa()
        servicio = self._servicio(_datos(filas), contexto, persistencia)

        reporte = servicio.validar(self.ruta)

        campos = {aviso.campo for aviso in reporte.errores}
        self.assertIn('Cantidad ingresada', campos)
        self.assertIn('Precio compra (S/)', campos)
        self.assertIn('Fecha ingreso', campos)
        self.assertIn('Unidad medida', campos)
        self.assertEqual(reporte.correctas, 1)
        self.assertFalse(reporte.es_valido)
        self.assertTrue(any(
            'menor que el precio de compra' in aviso.problema
            for aviso in reporte.advertencias
        ))

    def test_conflicto_de_identidad_por_codigo(self):
        producto = {
            'nombre': 'Lejía tradicional 1 L',
            'marca': 'ZEYVER',
            'presentacion': 'Botella 1 L',
        }
        contexto = ContextoFalso(productos={'ZEY-L001': producto})
        persistencia = PersistenciaFalsa()
        filas = [
            _fila(codigo='ZEY-L001'),
            _fila(codigo='ZEY-L001', marca='Otra marca'),
        ]
        servicio = self._servicio(_datos(filas), contexto, persistencia)

        reporte = servicio.validar(self.ruta)

        conflictos = [
            aviso for aviso in reporte.errores
            if aviso.campo == 'Código producto'
        ]
        self.assertEqual(len(conflictos), 1)
        self.assertEqual(conflictos[0].numero_fila, 3)
        self.assertEqual(reporte.correctas, 1)

    def test_producto_y_categoria_nuevos_son_advertencias(self):
        contexto = ContextoFalso(categorias=(), productos={})
        persistencia = PersistenciaFalsa()
        servicio = self._servicio(_datos([_fila()]), contexto, persistencia)

        reporte = servicio.validar(self.ruta)

        self.assertTrue(reporte.es_valido)
        self.assertEqual(reporte.correctas, 1)
        self.assertGreaterEqual(reporte.total_advertencias, 2)
        self.assertEqual(persistencia.errores, [])
        self.assertEqual(persistencia.intentos[0][1], 'validado')


class InventarioEtapa2UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ruta = Path(self.temp.name) / 'ingreso.xlsx'
        self.ruta.write_bytes(b'contenido')

    def _reporte(self, errores=(), advertencias=(), filas_preview=None, validas=None):
        archivo = ArchivoIngreso('ingreso.xlsx', 128, 'hash')
        fila = FilaIngreso(
            numero_fila=2,
            proveedor='LimpiaSur',
            codigo='ZEY-L001',
            producto='Lejía tradicional 1 L',
            categoria='Limpieza',
            marca='ZEYVER',
            presentacion='Botella 1 L',
            unidad_medida='botella',
            cantidad=37,
            stock_minimo=5,
            precio_compra=Decimal('10.00'),
            precio_venta=Decimal('15.00'),
            fecha_ingreso=date(2026, 11, 15),
        )
        if filas_preview is None:
            filas_preview = [FilaVistaPreviaIngreso(
                numero_fila=2,
                proveedor='LimpiaSur',
                codigo='ZEY-L001',
                producto='Lejía tradicional 1 L',
                categoria='Limpieza',
                cantidad='37',
                precio_compra='10.00',
                precio_venta='15.00',
                fecha_ingreso='15/11/2026',
                estado='Válido',
            )]
        if validas is None:
            validas = [] if errores else [fila]
        return ReporteValidacionIngreso(
            archivo=archivo,
            proveedor='LimpiaSur',
            total_filas=len(filas_preview),
            filas_validas=list(validas),
            filas_preview=list(filas_preview),
            errores=list(errores),
            advertencias=list(advertencias),
        )

    def _tablero(self, reporte):
        tab = InventoryImportTab(servicio=ServicioFalso(reporte))
        self.addCleanup(tab.deleteLater)
        self.addCleanup(tab.close)
        tab.load_file(self.ruta)
        tab.validate_file()
        return tab

    def test_ui_muestra_errores_en_la_tabla_y_bloquea_confirmar(self):
        from models.importacion_inventario import AvisoIngreso

        reporte = self._reporte(
            errores=[AvisoIngreso(3, 'Cantidad ingresada', '-5', 'Error grave')],
            advertencias=[AvisoIngreso(4, 'Precio venta (S/)', '8', 'Aviso leve', False)],
            filas_preview=[
                FilaVistaPreviaIngreso(
                    2, 'LimpiaSur', 'ZEY-L001', 'Lejía', 'Limpieza',
                    '37', '10.00', '15.00', '15/11/2026', 'Válido',
                ),
                FilaVistaPreviaIngreso(
                    3, 'LimpiaSur', 'ZEY-L002', 'Detergente', 'Limpieza',
                    '-5', '8.00', '12.00', '15/11/2026', 'Error',
                ),
                FilaVistaPreviaIngreso(
                    4, 'LimpiaSur', 'ZEY-L003', 'Escobilla', 'Limpieza',
                    '6', '8.00', '8.00', '15/11/2026', 'Advertencia',
                ),
            ],
            validas=[FilaIngreso(
                numero_fila=2,
                proveedor='LimpiaSur',
                codigo='ZEY-L001',
                producto='Lejía',
                categoria='Limpieza',
                marca='ZEYVER',
                presentacion='Botella 1 L',
                unidad_medida='botella',
                cantidad=37,
                stock_minimo=5,
                precio_compra=Decimal('10.00'),
                precio_venta=Decimal('15.00'),
                fecha_ingreso=date(2026, 11, 15),
            )],
        )
        tab = self._tablero(reporte)

        self.assertEqual(tab.validation_status.text(), 'Pendiente')
        self.assertEqual(tab.validation_status.objectName(), 'warningChip')
        self.assertEqual(tab.preview_summary_values['registros'].text(), '3')
        self.assertEqual(tab.preview_summary_values['validos'].text(), '1')
        self.assertNotIn('errores', tab.preview_summary_values)
        self.assertEqual(tab.confirm_table.rowCount(), 3)
        self.assertEqual(
            [tab.confirm_table.item(index, 13).text() for index in range(3)],
            ['Listo', 'Revisar', 'Advertencia'],
        )
        self.assertFalse(tab.confirm_button.isEnabled())
        mensaje = tab.confirm_status.text()
        self.assertIn('Validación con 1 error(es) bloqueante(s)', mensaje)
        self.assertIn('Fila 3 · Cantidad ingresada: "-5" Error grave', mensaje)
        self.assertIn('Vuelve a cargar un Excel corregido', mensaje)
        self.assertIn('QPushButton#primaryButton:disabled', tab.styleSheet())
        tab._confirmar()
        self.assertEqual(tab.confirm_status.text(), mensaje)
        self.assertEqual(tab.stepper.numbers[1].objectName(), 'stepActive')

    def test_ui_sin_errores_habilita_confirmar_y_muestra_resumen(self):
        tab = self._tablero(self._reporte())

        self.assertEqual(tab.validation_status.text(), 'Listo')
        self.assertEqual(tab.validation_status.objectName(), 'goodChip')
        self.assertEqual(tab.preview_summary_values['proveedor'].text(), 'LimpiaSur')
        self.assertEqual(tab.preview_summary_values['archivo'].text(), 'ingreso.xlsx')
        self.assertEqual(tab.preview_summary_values['registros'].text(), '1')
        self.assertEqual(tab.preview_summary_values['validos'].text(), '1')
        self.assertNotIn('errores', tab.preview_summary_values)
        self.assertEqual(tab.confirm_table.rowCount(), 1)
        self.assertEqual(
            tab.confirm_table.horizontalHeaderItem(0).text(), 'Fila'
        )
        self.assertEqual(
            tab.confirm_table.horizontalHeaderItem(13).text(), 'Estado'
        )
        self.assertEqual(tab.confirm_table.item(0, 13).text(), 'Listo')
        self.assertEqual(tab.confirm_table.item(0, 7).text(), 'S/ 10.00')
        self.assertTrue(tab.confirm_button.isEnabled())
        self.assertTrue(tab.upload_page.isHidden())
        self.assertFalse(tab.preview_page.isHidden())

    def test_no_existe_pantalla_de_validacion_independiente(self):
        from PySide6.QtWidgets import QLabel

        tab = self._tablero(self._reporte())
        textos = [label.text() for label in tab.findChildren(QLabel)]

        self.assertFalse(hasattr(tab, 'validation_card'))
        self.assertFalse(hasattr(tab, 'continue_button'))
        self.assertFalse(hasattr(tab, 'ingreso_preview'))
        self.assertFalse(any('Validación exitosa' in texto for texto in textos))
        self.assertFalse(any('Reglas validadas' in texto for texto in textos))
        self.assertFalse(any('Resumen de validación' in texto for texto in textos))
        self.assertFalse(any('Columnas detectadas' in texto for texto in textos))
        self.assertFalse(any('Errores críticos' in texto for texto in textos))
        self.assertFalse(any('Advertencias detectadas' in texto for texto in textos))
        self.assertFalse(any('primeras 5 filas' in texto for texto in textos))
        self.assertFalse(any('error' in texto.casefold() for texto in textos))
        self.assertFalse(any('incorrecto' in texto.casefold() for texto in textos))

    def test_confirmar_muestra_resultado_guardado(self):
        tab = self._tablero(self._reporte())

        tab.confirm_button.click()

        self.assertEqual(tab.stepper.numbers[2].objectName(), 'stepActive')
        self.assertFalse(tab.result_page.isHidden())
        self.assertIn('LimpiaSur', tab.result_detail.text())
        self.assertIn('ingreso.xlsx', tab.result_detail.text())
        self.assertIn('N.º 123', tab.result_detail.text())
        self.assertIn('PostgreSQL', tab.result_status.text())
        self.assertEqual(tab.result_metric_values['incidencias'].text(), '0')
