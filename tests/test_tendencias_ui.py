import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from controllers.tendencias_controller import TendenciasController
from models.sesion_usuario import SesionUsuario
from views.tendencias_view import TrendsView
from views.radar_historia_dialog import HistoriaRadarDialog, resumen_crecimiento
from views.radar_importacion_dialog import ImportacionRadarDialog


class ControllerPrueba(QObject):
    actualizado = Signal(object)
    fallo = Signal(str)
    ocupado = Signal(bool)

    def __init__(self):
        super().__init__()
        self.llamadas = []

    def ejecutar(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))


class RadarUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.vista = TrendsView(SesionUsuario(1, 'prueba', 'administrador'), controller=ControllerPrueba())
        self.vista.resize(1280, 945)
        self.addCleanup(self.vista.deleteLater)

    def test_vacio_sin_datos_simulados(self):
        self.vista._recibir({'radar': None, 'conexion_comercial': False, 'historial': False})
        self.assertEqual(self.vista._visibles, [])
        self.assertTrue(self.vista.buscar_tendencias.isEnabled())
        self.assertFalse(hasattr(self.vista, 'importar'))

    def test_un_boton_dispara_busqueda_sin_registros(self):
        self.vista.buscar_tendencias.click()
        self.assertEqual(self.vista.controller.llamadas, [(('buscar_radar',), {'id_usuario': 1})])

    def test_carga_tarjetas_y_filtros_sin_consultar_otra_vez(self):
        item = dict(termino='Squishy de prueba', categoria='juegos', tipo='producto', fuente='google',
                    metrica='crecimiento', valor=250, indicador='En aumento', referencia='juguetes',
                    url='https://trends.google.com/', periodo='Último mes')
        resultado = dict(items=[item], modo='comercial', consultado_en=datetime.now(timezone.utc).isoformat(), advertencias=[])
        self.vista._recibir({'radar': resultado, 'conexion_comercial': True, 'historial': True})
        self.assertEqual(len(self.vista._visibles), 1)
        self.assertEqual(self.vista.tarjetas.count(), 1)
        llamadas = len(self.vista.controller.llamadas)
        self.vista.botones_categoria['limpieza'].click()
        self.assertEqual(self.vista._visibles, [])
        self.vista.botones_categoria[None].click()
        self.assertEqual(len(self.vista._visibles), 1)
        self.vista.fuente.setCurrentIndex(self.vista.fuente.findData('tiktok'))
        self.assertEqual(self.vista._visibles, [])
        self.assertEqual(len(self.vista.controller.llamadas), llamadas)
        self.vista.show()
        self.app.processEvents()
        self.assertFalse(self.vista.grab().isNull())
        self.vista.close()

    def test_al_abrir_solo_carga_historial(self):
        self.vista.show()
        self.app.processEvents()
        self.assertEqual(self.vista.controller.llamadas[0][0], ('cargar_radar',))
        self.vista.close()

    def test_ayuda_fuera_de_la_pantalla_principal(self):
        def cancelar():
            dialogo = self.app.activeModalWidget()
            if isinstance(dialogo, QDialog):
                dialogo.reject()
        QTimer.singleShot(0, cancelar)
        self.vista._ayuda()

    def test_tiktok_no_se_presenta_como_conectado_sin_proveedor(self):
        resultado = dict(items=[], modo='gratuito', consultado_en=datetime.now(timezone.utc).isoformat())
        self.vista._recibir({'radar': resultado, 'conexion_comercial': False})
        self.vista.fuente.setCurrentIndex(self.vista.fuente.findData('tiktok'))
        self.assertIn('conexión de datos', self.vista.vacio_texto.text())

    def test_importacion_real_disponible(self):
        botones = [b.text() for b in self.vista.findChildren(QPushButton)]
        self.assertIn('Importar CSV real', botones)
        dialogo = ImportacionRadarDialog(self.vista)
        self.assertEqual(dialogo.opciones()['formato'], 'tiktok_manual')
        self.assertEqual(dialogo.opciones()['pais'], 'PE')
        dialogo.deleteLater()

    def test_grafico_solo_puntos_reales_y_huecos(self):
        base = dict(termino='prueba', fuente='google', pais='PE', proveedor='Google Trends CSV',
                    origen='google_timeline', metrica='interes_relativo', periodo='archivo', contexto='escala',
                    url='https://trends.google.com/')
        puntos = [dict(base, observado_en=f'2025-01-0{i}T00:00:00+00:00', valor=v)
                  for i, v in enumerate((10, 20, None, 40), 1)]
        dialogo = HistoriaRadarDialog(puntos, self.vista)
        dialogo.show()
        self.app.processEvents()
        self.assertFalse(dialogo.grab().isNull())
        self.assertIn('no calculable', resumen_crecimiento(puntos))
        dialogo.close()
        dialogo.deleteLater()

    def test_base_cero_y_posicion_no_generan_porcentaje_falso(self):
        puntos = [dict(observado_en=f'2025-01-0{i}T00:00:00+00:00', valor=v, metrica='reproducciones')
                  for i, v in enumerate((0, 20), 1)]
        self.assertIn('base cero', resumen_crecimiento(puntos))
        for punto in puntos:
            punto['metrica'] = 'posicion'
        self.assertIn('cambio de posición', resumen_crecimiento(puntos))

    def test_peru_prioritario_sin_atribuirle_senales_internacionales(self):
        base = dict(termino='prueba', categoria='otros', fuente='tiktok', tipo='hashtag',
                    indicador='Señal de prueba', metrica='presencia', valor=None,
                    referencia='test', url='https://www.tiktok.com/')
        resultado = dict(items=[dict(base, pais=None), dict(base, pais='PE'), dict(base, pais='MX')],
                         modo='gratuito', consultado_en=datetime.now(timezone.utc).isoformat())
        self.vista._recibir({'radar': resultado})
        self.assertEqual(self.vista._visibles[0]['pais'], 'PE')
        self.vista.mercado.setCurrentIndex(self.vista.mercado.findData('PE'))
        self.assertEqual(len(self.vista._visibles), 1)
        self.assertEqual(self.vista._visibles[0]['pais'], 'PE')

    def test_controller_trabaja_en_segundo_plano(self):
        class ServicioPrueba:
            def ejecutar(self, accion, **opciones):
                return {'accion': accion}
        controller = TendenciasController(ServicioPrueba())
        resultados = []
        from PySide6.QtCore import QEventLoop
        espera = QEventLoop()
        controller.actualizado.connect(resultados.append)
        controller.ocupado.connect(lambda ocupado: None if ocupado else espera.quit())
        self.assertTrue(controller.ejecutar('cargar'))
        self.assertFalse(controller.ejecutar('cargar'))
        QTimer.singleShot(5000, espera.quit)
        espera.exec()
        self.assertEqual(resultados, [{'accion': 'cargar'}])
        self.assertIsNone(controller._worker)


if __name__ == '__main__':
    unittest.main()
