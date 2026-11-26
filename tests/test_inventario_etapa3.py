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
    AvisoIngreso,
    FilaIngreso,
    FilaVistaPreviaIngreso,
    IngresoDetalleGuardado,
    IngresoGuardado,
    ReporteValidacionIngreso,
    ResultadoGuardadoIngreso,
)
from services.importacion_inventarios_service import COLUMNS, ImportacionIngresosService
from views.import_inventory_view import InventoryImportTab
from views.import_shared import TableData


HASH = 'hash-etapa3'


class ContextoEtapa3:
    def __init__(
        self,
        estado='validado',
        hash_duplicado=False,
        hash_duplicado_actual=None,
        productos=None,
        categorias=('Limpieza', 'Papelería'),
    ):
        self.estado = estado
        self.hash_duplicado = hash_duplicado
        self.hash_duplicado_actual = hash_duplicado_actual
        self.productos = productos or {}
        self.categorias = categorias
        self.importacion = {
            'id_importacion': 99,
            'estado': estado,
            'nombre_archivo': 'ingreso.xlsx',
            'hash_archivo': HASH,
        }

    def existe_hash(self, _hash):
        return self.hash_duplicado

    def existe_hash_actual(self, _hash):
        if self.hash_duplicado_actual is None:
            return self.hash_duplicado
        return self.hash_duplicado_actual

    def proveedor_existe(self, _nombre):
        return True

    def categoria_existe(self, nombre):
        return nombre in self.categorias

    def buscar_producto(self, codigo, _nombre, _marca, _presentacion):
        return self.productos.get(codigo)

    def obtener_importacion(self, **_filtros):
        return self.importacion


class PersistenciaEtapa3:
    def __init__(self, resultado=None, error=None):
        self.llamadas = []
        self.resultado = resultado
        self.error = error

    def crear_intento(self, reporte, estado, id_usuario=None):
        self.llamadas.append(('crear_intento', estado, id_usuario))
        return 99

    def registrar_errores(self, id_intento, errores):
        self.llamadas.append(('registrar_errores', id_intento, len(errores)))

    def guardar(self, confirmacion, id_usuario=None):
        self.llamadas.append(('guardar', id_usuario))
        if self.error:
            raise ValueError(self.error)
        if self.resultado is not None:
            return self.resultado
        return ResultadoGuardadoIngreso(
            id_ingreso=123,
            id_importacion=confirmacion.id_importacion,
            proveedor=confirmacion.proveedor,
            archivo=confirmacion.archivo,
            fecha_ingreso=confirmacion.resumen.fecha_min or date(2026, 11, 15),
            productos=len(confirmacion.filas),
            unidades=sum(fila.cantidad for fila in confirmacion.filas),
            incidencias=confirmacion.registros_rechazados,
        )

    def registrar_fallo(self, confirmacion, motivo, id_usuario=None):
        self.llamadas.append(('registrar_fallo', motivo))

    def obtener_ingreso(self, id_ingreso):
        return IngresoGuardado(
            id_ingreso=id_ingreso,
            id_importacion=99,
            proveedor='LimpiaSur',
            archivo='ingreso.xlsx',
            fecha_ingreso=date(2026, 11, 15),
            numero_productos=1,
            total_unidades=10,
            creado_en=None,
            filas=(IngresoDetalleGuardado(
                numero_fila=2,
                codigo='ZEY-L001',
                producto='Lejía tradicional 1 L',
                categoria='Limpieza',
                cantidad=10,
                stock_minimo=5,
                precio_compra=Decimal('10.00'),
                precio_venta=Decimal('15.00'),
                unidad_medida='botella',
                fecha_ingreso=date(2026, 11, 15),
            ),),
        )


class ServicioFalso:
    def __init__(self, reporte, error_confirmar=None):
        self.reporte = reporte
        self.error_confirmar = error_confirmar
        self.contexto = ContextoEtapa3()
        self.persistencia = PersistenciaEtapa3()

    def validar(self, _ruta, _id_usuario=None):
        return self.reporte

    def construir_resumen(self, reporte):
        return ImportacionIngresosService.construir_resumen(reporte)

    def construir_productos_vista_previa(self, reporte):
        return ImportacionIngresosService.construir_productos_vista_previa(reporte)

    def confirmar(self, reporte, id_usuario=None):
        if self.error_confirmar is not None:
            raise ValueError(self.error_confirmar)
        return ImportacionIngresosService(contexto=self.contexto).confirmar(
            reporte, id_usuario
        )

    def confirmar_y_guardar(self, reporte, id_usuario=None):
        confirmacion = self.confirmar(reporte, id_usuario)
        return self.persistencia.guardar(confirmacion, id_usuario)

    def obtener_ingreso(self, id_ingreso):
        return self.persistencia.obtener_ingreso(id_ingreso)


def _fila(
    codigo='ZEY-L001',
    producto='Lejía tradicional 1 L',
    categoria='Limpieza',
    cantidad=10,
    fecha=date(2026, 11, 15),
    estado='Nuevo',
    id_producto=None,
):
    return FilaIngreso(
        numero_fila=2,
        proveedor='LimpiaSur',
        codigo=codigo,
        producto=producto,
        categoria=categoria,
        marca='ZEYVER',
        presentacion='Botella 1 L',
        unidad_medida='botella',
        cantidad=cantidad,
        stock_minimo=5,
        precio_compra=Decimal('10.00'),
        precio_venta=Decimal('15.00'),
        fecha_ingreso=fecha,
        id_producto=id_producto,
        estado_producto=estado,
    )


def _reporte(filas, errores=(), validas=None):
    if validas is None:
        validas = [] if errores else list(filas)
    return ReporteValidacionIngreso(
        archivo=ArchivoIngreso('ingreso.xlsx', 128, HASH),
        proveedor='LimpiaSur',
        total_filas=len(filas),
        filas_validas=list(validas),
        filas_preview=[],
        errores=list(errores),
        advertencias=[],
        id_importacion=99,
    )


def _fila_excel(codigo='ZEY-L001', categoria='Limpieza'):
    return (
        'LimpiaSur', codigo, 'Lejía tradicional 1 L', categoria, 'ZEYVER',
        'Botella 1 L', 'Botella', '10', '5', '10.00', '15.00', '15/11/2026',
    )


def _datos(filas):
    return TableData(
        path=None,
        name='ingreso.xlsx',
        extension='.xlsx',
        size_bytes=128,
        modified=None,
        headers=list(COLUMNS),
        rows=filas,
        total=len(filas),
    )


class InventarioEtapa3ServicioTests(unittest.TestCase):
    def setUp(self):
        self.servicio = ImportacionIngresosService(contexto=ContextoEtapa3())

    def test_resumen_y_productos_de_vista_previa(self):
        filas = [
            _fila(codigo='ZEY-L001', cantidad=10, fecha=date(2026, 11, 15)),
            _fila(
                codigo='ZEY-P002', producto='Cuaderno A4', categoria='Papelería',
                cantidad=12, fecha=date(2026, 11, 20),
            ),
            _fila(
                codigo='ZEY-P003', producto='Lápiz HB', categoria='Papelería',
                cantidad=8, fecha=date(2026, 11, 18),
            ),
        ]
        reporte = _reporte(filas)

        resumen = self.servicio.construir_resumen(reporte)
        productos = self.servicio.construir_productos_vista_previa(reporte)

        self.assertEqual(resumen.proveedor, 'LimpiaSur')
        self.assertEqual(resumen.archivo, 'ingreso.xlsx')
        self.assertEqual(resumen.productos, 3)
        self.assertEqual(resumen.total_unidades, 30)
        self.assertEqual(resumen.fecha_rango, '15/11/2026 - 20/11/2026')
        self.assertEqual(resumen.categorias, ('Limpieza', 'Papelería'))
        self.assertEqual(len(productos), 3)
        self.assertEqual(productos[0].numero_fila, 2)
        self.assertEqual(productos[0].codigo, 'ZEY-L001')
        self.assertEqual(productos[0].precio_compra, 'S/ 10.00')
        self.assertEqual(productos[0].precio_venta, 'S/ 15.00')
        self.assertEqual(productos[0].fecha_ingreso, '15/11/2026')
        self.assertEqual(productos[0].estado_producto, 'Nuevo')
        self.assertEqual(productos[0].estado, 'Válido')

    def test_vista_previa_incluye_filas_con_error(self):
        reporte = _reporte(
            [_fila()],
            errores=[AvisoIngreso(3, 'Cantidad ingresada', '-5', 'Error grave')],
        )
        reporte.filas_preview = [
            FilaVistaPreviaIngreso(
                2, 'LimpiaSur', 'ZEY-L001', 'Lejía', 'Limpieza', '10',
                '10.00', '15.00', '15/11/2026', 'Válido', 'ZEYVER',
                'Botella 1 L', 'botella', '5', 'Nuevo',
            ),
            FilaVistaPreviaIngreso(
                3, 'LimpiaSur', 'ZEY-L002', 'Detergente', 'Limpieza', '-5',
                '8.00', '12.00', '15/11/2026', 'Error', 'ZEYVER',
                'Botella 1 L', 'botella', '5', 'Nuevo',
            ),
        ]

        productos = self.servicio.construir_productos_vista_previa(reporte)

        self.assertEqual(len(productos), 2)
        self.assertEqual([producto.estado for producto in productos], ['Válido', 'Error'])
        self.assertEqual(productos[1].numero_fila, 3)
        self.assertEqual(productos[1].marca, 'ZEYVER')
        self.assertEqual(productos[1].presentacion, 'Botella 1 L')
        self.assertEqual(productos[1].unidad_medida, 'botella')
        self.assertEqual(productos[1].stock_minimo, '5')

    def test_validacion_clasifica_producto_nuevo_y_existente(self):
        producto = {
            'id_producto': 17,
            'nombre': 'Lejía tradicional 1 L',
            'marca': 'ZEYVER',
            'presentacion': 'Botella 1 L',
        }
        contexto = ContextoEtapa3(productos={'ZEY-L001': producto})
        persistencia = PersistenciaEtapa3()
        servicio = ImportacionIngresosService(
            lector=lambda _ruta: _datos([
                _fila_excel('ZEY-L001'),
                _fila_excel('ZEY-N002'),
            ]),
            contexto=contexto,
            persistencia=persistencia,
        )
        ruta = Path(tempfile.gettempdir()) / 'ingreso-etapa3.xlsx'
        ruta.write_bytes(b'contenido')
        self.addCleanup(ruta.unlink, missing_ok=True)

        reporte = servicio.validar(ruta, 7)

        self.assertTrue(reporte.es_valido)
        self.assertEqual(
            [(fila.codigo, fila.estado_producto) for fila in reporte.filas_validas],
            [('ZEY-L001', 'Existente'), ('ZEY-N002', 'Nuevo')],
        )
        self.assertEqual(reporte.filas_validas[0].id_producto, 17)
        self.assertIsNone(reporte.filas_validas[1].id_producto)

    def test_confirmar_genera_payload_sin_escribir(self):
        persistencia = PersistenciaEtapa3()
        servicio = ImportacionIngresosService(
            contexto=ContextoEtapa3(), persistencia=persistencia
        )
        reporte = _reporte([_fila()])

        confirmacion = servicio.confirmar(reporte, 7)

        self.assertEqual(confirmacion.id_importacion, 99)
        self.assertEqual(confirmacion.hash_archivo, HASH)
        self.assertEqual(confirmacion.id_usuario, 7)
        self.assertEqual(confirmacion.resumen.productos, 1)
        self.assertEqual(len(confirmacion.filas), 1)
        self.assertEqual(persistencia.llamadas, [])

    def test_confirmar_y_guardar_registra_el_ingreso(self):
        persistencia = PersistenciaEtapa3()
        servicio = ImportacionIngresosService(
            contexto=ContextoEtapa3(), persistencia=persistencia
        )

        resultado = servicio.confirmar_y_guardar(_reporte([_fila()]), 7)

        self.assertEqual(resultado.id_ingreso, 123)
        self.assertEqual(resultado.productos, 1)
        self.assertEqual(resultado.unidades, 10)
        self.assertEqual(resultado.incidencias, 0)
        self.assertEqual(resultado.estado, 'Completado')
        self.assertEqual(persistencia.llamadas, [('guardar', 7)])

    def test_confirmar_y_guardar_registra_fallo_si_la_persistencia_falla(self):
        persistencia = PersistenciaEtapa3(error='Fallo de base de datos')
        servicio = ImportacionIngresosService(
            contexto=ContextoEtapa3(), persistencia=persistencia
        )

        with self.assertRaisesRegex(ValueError, 'Fallo de base de datos'):
            servicio.confirmar_y_guardar(_reporte([_fila()]), 7)

        self.assertEqual(
            persistencia.llamadas,
            [('guardar', 7), ('registrar_fallo', 'Fallo de base de datos')],
        )

    def test_confirmar_bloquea_si_la_importacion_no_esta_vigente(self):
        servicio = ImportacionIngresosService(
            contexto=ContextoEtapa3(estado='completada')
        )

        with self.assertRaisesRegex(ValueError, 'ya no está vigente'):
            servicio.confirmar(_reporte([_fila()]))

    def test_confirmar_bloquea_si_el_hash_ya_fue_importado(self):
        servicio = ImportacionIngresosService(
            contexto=ContextoEtapa3(hash_duplicado_actual=True)
        )

        with self.assertRaisesRegex(ValueError, 'ya fue importado'):
            servicio.confirmar(_reporte([_fila()]))

    def test_confirmar_bloquea_si_el_archivo_cambio_tras_validarse(self):
        ruta = Path(tempfile.gettempdir()) / 'ingreso-cambiado-etapa3.xlsx'
        ruta.write_bytes(b'contenido original')
        self.addCleanup(ruta.unlink, missing_ok=True)
        reporte = _reporte([_fila()])
        reporte.archivo.ruta = ruta
        ruta.write_bytes(b'contenido modificado')

        with self.assertRaisesRegex(ValueError, 'cambió después de la validación'):
            self.servicio.confirmar(reporte)

    def test_confirmar_bloquea_si_hay_errores_bloqueantes(self):
        reporte = _reporte(
            [_fila()],
            errores=[AvisoIngreso(3, 'Cantidad ingresada', '-5', 'Error grave')],
        )

        with self.assertRaisesRegex(ValueError, 'errores bloqueantes'):
            self.servicio.confirmar(reporte)


class InventarioEtapa3UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ruta = Path(self.temp.name) / 'ingreso.xlsx'
        self.ruta.write_bytes(b'contenido')

    def _tablero(self, filas, error_confirmar=None, errores=(), validas=None):
        reporte = _reporte(filas, errores=errores, validas=validas)
        servicio = ServicioFalso(reporte, error_confirmar=error_confirmar)
        tab = InventoryImportTab(servicio=servicio)
        self.addCleanup(tab.deleteLater)
        self.addCleanup(tab.close)
        tab.load_file(self.ruta)
        tab.validate_file()
        return tab, reporte

    def test_ui_muestra_resumen_tabla_y_paginacion(self):
        filas = [
            _fila(
                codigo=f'ZEY-L{numero:03d}',
                categoria='Limpieza' if numero % 2 else 'Papelería',
                cantidad=numero,
                estado='Existente' if numero == 1 else 'Nuevo',
                id_producto=17 if numero == 1 else None,
            )
            for numero in range(1, 10)
        ]
        tab, _ = self._tablero(filas)

        self.assertEqual(tab.stepper.numbers[1].objectName(), 'stepActive')
        self.assertEqual(
            tab.confirm_summary_values['proveedor'].text(), 'LimpiaSur'
        )
        self.assertEqual(
            tab.confirm_summary_values['archivo'].text(), 'ingreso.xlsx'
        )
        self.assertEqual(tab.confirm_summary_values['registros'].text(), '9')
        self.assertEqual(tab.confirm_summary_values['validos'].text(), '9')
        self.assertNotIn('errores', tab.confirm_summary_values)
        self.assertEqual(tab.confirm_summary_values['unidades'].text(), '45')
        self.assertEqual(
            tab.confirm_summary_values['fecha'].text(), '15/11/2026'
        )
        self.assertEqual(
            tab.confirm_table.horizontalHeaderItem(12).text(), 'Estado producto'
        )
        self.assertEqual(
            tab.confirm_table.horizontalHeaderItem(13).text(), 'Estado'
        )
        self.assertEqual(tab.confirm_table.rowCount(), 9)
        self.assertEqual(tab.confirm_table.rango_pagina.text(), '1–7 de 9')
        self.assertFalse(tab.confirm_table.pie_pagina.isHidden())
        self.assertEqual(
            tab.confirm_caption.text(),
            'Mostrando 9 de 9 productos · Solo lectura',
        )
        self.assertEqual(tab.confirm_filter.count(), 3)
        self.assertTrue(tab.confirm_button.isEnabled())

    def test_ui_busca_y_filtra_y_volver_conserva_reporte(self):
        filas = [
            _fila(codigo='ZEY-L001'),
            _fila(
                codigo='ZEY-P002', producto='Cuaderno A4',
                categoria='Papelería',
            ),
        ]
        tab, reporte = self._tablero(filas)

        tab.confirm_search.setText('cuaderno')
        self.assertEqual(tab.confirm_table.rowCount(), 1)
        self.assertEqual(tab.confirm_table.item(0, 1).text(), 'ZEY-P002')

        tab.confirm_search.clear()
        tab.confirm_filter.setCurrentText('Papelería')
        self.assertEqual(tab.confirm_table.rowCount(), 1)
        self.assertEqual(
            tab.confirm_caption.text(),
            'Mostrando 1 de 2 productos · Solo lectura',
        )

        tab.confirm_back.click()
        self.assertFalse(tab.upload_page.isHidden())
        self.assertTrue(tab.preview_page.isHidden())
        self.assertIs(tab.reporte, reporte)

    def test_ui_no_genera_payload_si_la_revalidacion_falla(self):
        tab, _ = self._tablero(
            [_fila()], error_confirmar='La importación ya no está vigente.'
        )

        with patch('views.import_inventory_view.QMessageBox.critical') as critico:
            tab.confirm_button.click()

        critico.assert_not_called()
        mensaje = tab.confirm_status.text()
        self.assertIn(
            'Guardado fallido: ValueError: La importación ya no está vigente.',
            mensaje,
        )
        self.assertIn('Vuelve a cargar el archivo para revalidar', mensaje)
        self.assertEqual(tab.confirm_status.objectName(), 'validationError')
        self.assertIsNone(tab.reporte)
        self.assertIsNone(tab.confirmacion)
        self.assertIsNone(tab.resultado_guardado)
        self.assertFalse(tab.confirm_button.isEnabled())

    def test_ui_muestra_detalle_cuando_excepcion_no_tiene_mensaje(self):
        tab, _ = self._tablero([_fila()], error_confirmar='')

        with patch('views.import_inventory_view.QMessageBox.critical') as critico:
            tab.confirm_button.click()

        critico.assert_not_called()
        mensaje = tab.confirm_status.text()
        self.assertIn(
            'Guardado fallido: ValueError: sin mensaje del servidor', mensaje
        )
        self.assertEqual(tab.confirm_status.objectName(), 'validationError')
        self.assertIsNone(tab.reporte)
        self.assertFalse(tab.confirm_button.isEnabled())

    def test_ui_guarda_y_muestra_resultado_real(self):
        tab, _ = self._tablero([_fila()])

        with patch('views.import_inventory_view.QMessageBox.critical') as critico:
            tab.confirm_button.click()

        critico.assert_not_called()
        self.assertEqual(tab.confirm_status.objectName(), 'validationLead')
        self.assertFalse(tab.result_page.isHidden())
        self.assertEqual(tab.stepper.numbers[2].objectName(), 'stepActive')
        self.assertIn('Ingreso registrado: N.º 123', tab.result_detail.text())
        self.assertIn('PostgreSQL', tab.result_status.text())
        self.assertEqual(tab.result_metric_values['productos'].text(), '1')
        self.assertEqual(tab.result_metric_values['lineas'].text(), '10')
        self.assertEqual(tab.result_metric_values['incidencias'].text(), '0')
        self.assertEqual(tab.result_metric_values['estado'].text(), 'Completado')
        self.assertEqual(tab.result_back.text(), 'Ver ingreso registrado')
        self.assertEqual(tab.result_finish.text(), 'Importar otro Excel')

    def test_ui_ver_ingreso_registrado_abre_detalle(self):
        tab, _ = self._tablero([_fila()])
        tab.confirm_button.click()

        with patch(
            'views.import_inventory_view.IngresoGuardadoDialog.exec'
        ) as ejecutar:
            tab.result_back.click()

        ejecutar.assert_called_once()

    def test_ui_importar_otro_excel_limpia_el_resultado(self):
        tab, _ = self._tablero([_fila()])
        tab.confirm_button.click()

        tab.result_finish.click()

        self.assertIsNone(tab.resultado_guardado)
        self.assertFalse(tab.result_back.isEnabled())
        self.assertEqual(tab.result_metric_values['productos'].text(), '-')
        self.assertEqual(tab.stepper.numbers[0].objectName(), 'stepActive')

    def test_ui_entra_a_etapa2_con_errores_y_bloquea_confirmacion(self):
        filas = [
            _fila(codigo='ZEY-L001'),
            _fila(codigo='ZEY-P002', categoria='Papelería'),
        ]
        tab, _ = self._tablero(
            filas,
            errores=[AvisoIngreso(3, 'Cantidad ingresada', '-5', 'Error grave')],
            validas=filas,
        )

        self.assertFalse(tab.preview_page.isHidden())
        self.assertEqual(tab.stepper.numbers[1].objectName(), 'stepActive')
        self.assertEqual(tab.confirm_table.rowCount(), 2)
        self.assertEqual(tab.preview_summary_values['registros'].text(), '2')
        self.assertEqual(tab.preview_summary_values['validos'].text(), '2')
        self.assertFalse(tab.confirm_button.isEnabled())
        mensaje = tab.confirm_status.text()
        self.assertIn('Validación con 1 error(es) bloqueante(s)', mensaje)
        self.assertIn('Fila 3 · Cantidad ingresada: "-5" Error grave', mensaje)
        self.assertIn('Vuelve a cargar un Excel corregido', mensaje)
