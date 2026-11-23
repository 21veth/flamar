import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from views.import_inventory_view import (
    MAX_FILE_BYTES,
    IngresoDropZone,
    InventoryImportTab,
)


class FakeMimeData:
    def __init__(self, path):
        self._url = QUrl.fromLocalFile(str(path))

    def urls(self):
        return [self._url]


class FakeDragEvent:
    def __init__(self, path):
        self._mime = FakeMimeData(path)
        self.accepted = False

    def mimeData(self):
        return self._mime

    def acceptProposedAction(self):
        self.accepted = True


class InventarioEtapa1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tab = InventoryImportTab()
        self.addCleanup(self.tab.deleteLater)
        self.addCleanup(self.tab.close)

    def _file(self, name, size=128):
        path = self.root / name
        with path.open('wb') as handle:
            handle.truncate(size)
        return path

    def test_estado_inicial_sin_archivo(self):
        self.assertIsNone(self.tab.archivo)
        self.assertEqual(
            self.tab.stepper.titles,
            ('Seleccionar archivo', 'Validar datos', 'Guardar'),
        )
        self.assertEqual(self.tab.stepper.numbers[0].objectName(), 'stepActive')
        self.assertEqual(self.tab.validate_button.text(), 'Validar archivo')
        self.assertFalse(self.tab.validate_button.isEnabled())
        self.assertTrue(self.tab.process_button.isHidden())
        self.assertTrue(self.tab.preview.isHidden())
        self.assertEqual(self.tab.details.record_count.text(), '-')

    def test_acepta_xlsx_y_no_lee_filas(self):
        path = self._file('ZEYVER_Ingreso_Limpieza.xlsx', 2048)
        with patch(
            'views.import_inventory_view.QFileDialog.getOpenFileName',
            return_value=(str(path), ''),
        ), patch(
            'views.import_shared.read_table_file',
            side_effect=AssertionError('no debe leerse'),
        ) as leer:
            self.tab.choose_file()

        self.assertIsNotNone(self.tab.archivo)
        self.assertEqual(self.tab.archivo.name, path.name)
        self.assertEqual(self.tab.archivo.extension, '.xlsx')
        self.assertEqual(self.tab.archivo.size_bytes, 2048)
        self.assertTrue(self.tab.validate_button.isEnabled())
        self.assertEqual(self.tab.details.file_name.text(), path.name)
        self.assertEqual(self.tab.details.file_type.text(), 'XLSX')
        self.assertEqual(self.tab.details.record_count.text(), 'Pendiente de validación')
        self.assertIn('Validar archivo', self.tab.footer_message.text())
        leer.assert_not_called()

    def test_rechaza_formatos_distintos_de_xlsx(self):
        for name in ('ventas.csv', 'antiguo.xls', 'foto.pdf', 'foto.png'):
            path = self._file(name)
            with self.subTest(name=name), patch(
                'views.import_inventory_view.QMessageBox.warning'
            ) as aviso:
                self.tab.load_file(path)
            aviso.assert_called_once()
            self.assertIsNone(self.tab.archivo)
            self.assertFalse(self.tab.validate_button.isEnabled())

    def test_rechaza_archivo_mayor_a_diez_mb(self):
        path = self._file('grande.xlsx', MAX_FILE_BYTES + 1)
        with patch('views.import_inventory_view.QMessageBox.warning') as aviso:
            self.tab.load_file(path)
        aviso.assert_called_once()
        self.assertIsNone(self.tab.archivo)
        self.assertFalse(self.tab.validate_button.isEnabled())

    def test_quitar_y_reemplazar_archivo(self):
        primero = self._file('uno.xlsx')
        segundo = self._file('dos.xlsx', 64)
        self.tab.load_file(primero)
        self.assertEqual(self.tab.archivo.name, 'uno.xlsx')

        self.tab.clear_file()
        self.assertIsNone(self.tab.archivo)
        self.assertFalse(self.tab.validate_button.isEnabled())

        self.tab.load_file(segundo)
        self.assertEqual(self.tab.archivo.name, 'dos.xlsx')
        self.assertEqual(self.tab.details.file_name.text(), 'dos.xlsx')
        self.assertTrue(self.tab.validate_button.isEnabled())

    def test_validar_solo_avisa_etapa_pendiente(self):
        self.tab.load_file(self._file('dulces.xlsx'))
        with patch('views.import_inventory_view.QMessageBox.information') as info, patch(
            'views.import_shared.read_table_file',
            side_effect=AssertionError('no debe leerse'),
        ) as leer:
            self.tab.validate_button.click()

        info.assert_called_once()
        self.assertIn('Etapa 2', info.call_args.args[2])
        leer.assert_not_called()
        self.assertIsNotNone(self.tab.archivo)

    def test_zona_solo_acepta_xlsx_por_arrastre(self):
        zone = IngresoDropZone()
        self.addCleanup(zone.deleteLater)
        self.addCleanup(zone.close)
        accepted = FakeDragEvent(self._file('aceptado.xlsx'))
        rejected = FakeDragEvent(self._file('rechazado.csv'))

        zone.dragEnterEvent(accepted)
        zone.dragEnterEvent(rejected)

        self.assertTrue(accepted.accepted)
        self.assertFalse(rejected.accepted)
