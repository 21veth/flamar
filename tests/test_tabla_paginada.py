import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractItemView, QTableWidgetItem

from views.tabla_paginada import TablaPaginada


class TablaPaginadaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tabla(self, cantidad, columnas=2):
        tabla = TablaPaginada(cantidad, columnas)
        tabla.setHorizontalHeaderLabels([f'Columna {i}' for i in range(columnas)])
        for fila in range(cantidad):
            tabla.setItem(fila, 0, QTableWidgetItem(f'Registro {fila + 1}'))
        tabla.resize(800, 600)
        tabla.show()
        self.addCleanup(tabla.deleteLater)
        self.addCleanup(tabla.close)
        self.app.processEvents()
        return tabla

    @staticmethod
    def visibles(tabla):
        return [fila for fila in range(tabla.rowCount()) if not tabla.isRowHidden(fila)]

    def test_pie_desde_siete_y_maximo_siete_filas_por_pagina(self):
        for cantidad in (0, 1, 6, 7, 8, 14, 15, 45):
            with self.subTest(cantidad=cantidad):
                tabla = self.tabla(cantidad)
                self.assertEqual(tabla.rowCount(), cantidad)
                self.assertEqual(self.visibles(tabla), list(range(min(cantidad, 7))))
                self.assertEqual(not tabla.pie_pagina.isHidden(), cantidad >= 7)
                self.assertEqual(tabla.total_paginas, max(1, (cantidad + 6) // 7))
                self.assertFalse(tabla.anterior.isEnabled())
                self.assertEqual(tabla.siguiente.isEnabled(), cantidad > 7)

    def test_avanzar_y_retroceder_no_pierde_ni_duplica_datos(self):
        tabla = self.tabla(15)
        altura = tabla.height()
        QTest.mouseClick(tabla.siguiente, Qt.LeftButton)
        self.assertEqual(self.visibles(tabla), list(range(7, 14)))
        self.assertEqual(tabla.rango_pagina.text(), '8–14 de 15')
        self.assertEqual(tabla.indicador_pagina.text(), 'Página 2 de 3')
        self.assertEqual(tabla.currentRow(), 7)
        QTest.mouseClick(tabla.siguiente, Qt.LeftButton)
        self.assertEqual(self.visibles(tabla), [14])
        self.assertFalse(tabla.siguiente.isEnabled())
        self.assertEqual(tabla.rango_pagina.text(), '15–15 de 15')
        self.assertEqual(tabla.height(), altura)
        QTest.mouseClick(tabla.anterior, Qt.LeftButton)
        self.assertEqual(self.visibles(tabla), list(range(7, 14)))
        self.assertEqual([tabla.item(fila, 0).text() for fila in range(15)],
                         [f'Registro {i + 1}' for i in range(15)])

    def test_filtros_externos_no_se_confunden_con_otra_pagina(self):
        tabla = self.tabla(20)
        tabla.setSelectionMode(QAbstractItemView.NoSelection)
        for fila in range(20):
            tabla.setRowHidden(fila, fila % 2 == 0)
        self.app.processEvents()
        self.assertEqual(self.visibles(tabla), [1, 3, 5, 7, 9, 11, 13])
        tabla.siguiente.click()
        self.assertEqual(self.visibles(tabla), [15, 17, 19])
        self.assertEqual(tabla.rango_pagina.text(), '8–10 de 10')
        for fila in range(20):
            tabla.setRowHidden(fila, False)
        self.app.processEvents()
        self.assertEqual(self.visibles(tabla), list(range(7)))
        self.assertEqual(tabla.rango_pagina.text(), '1–7 de 20')

    def test_refrescar_conserva_la_pagina_y_reducir_datos_ajusta_limites(self):
        tabla = self.tabla(15)
        tabla.siguiente.click()
        tabla.setItem(7, 0, QTableWidgetItem('Actualizado'))
        self.app.processEvents()
        self.assertEqual(tabla.pagina_actual, 1)
        tabla.setRowCount(3)
        self.app.processEvents()
        self.assertEqual(tabla.pagina_actual, 0)
        self.assertEqual(self.visibles(tabla), [0, 1, 2])
        self.assertTrue(tabla.pie_pagina.isHidden())
        tabla.setRowCount(0)
        self.app.processEvents()
        self.assertEqual(tabla.currentRow(), -1)
        self.assertEqual(tabla.rango_pagina.text(), '0–0 de 0')

    def test_pie_no_tapa_filas_ni_barra_horizontal(self):
        tabla = self.tabla(15, columnas=9)
        tabla.resize(550, tabla.height())
        self.app.processEvents()
        pie = tabla.pie_pagina.geometry()
        self.assertLess(tabla.viewport().geometry().bottom(), pie.top())
        if tabla.horizontalScrollBar().isVisible():
            posicion = tabla.horizontalScrollBar().mapTo(tabla, tabla.horizontalScrollBar().rect().topLeft())
            self.assertLess(pie.bottom(), posicion.y())
        ultima = tabla.visualItemRect(tabla.item(6, 0))
        self.assertTrue(tabla.viewport().rect().contains(ultima.center()))


if __name__ == '__main__':
    unittest.main()
