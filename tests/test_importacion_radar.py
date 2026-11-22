"""Fixtures generados solo en temporales de prueba; sin datos de demostración en producción."""

import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock

from services.importacion_tendencias import TIKTOK_COLUMNAS, leer_importacion
from services.tendencias_service import TendenciasService


class ImportacionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='radar_test_')
        self.addCleanup(self.temp.cleanup)
        self.ruta = Path(self.temp.name) / 'prueba.csv'

    def tiktok(self, **cambios):
        fila = dict(termino='Producto de prueba', tipo='producto', categoria='otros', pais='PE',
                    fecha='2025-01-01', metrica='reproducciones', valor='100', valor_original='100',
                    periodo='7 días', contexto='misma categoría y filtros', url='https://ads.tiktok.com/business/creativecenter/')
        fila.update(cambios)
        with self.ruta.open('w', encoding='utf-8-sig', newline='') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=TIKTOK_COLUMNAS)
            writer.writeheader()
            writer.writerow(fila)
        return leer_importacion(self.ruta, 'tiktok_manual')

    def test_tiktok_real_con_procedencia_y_deduplicacion(self):
        lote = self.tiktok()
        item = lote['items'][0]
        self.assertEqual(item['pais'], 'PE')
        self.assertEqual(item['tipo'], 'producto')
        self.assertEqual(item['valor'], 100)
        self.assertEqual(item['origen'], 'tiktok_manual')
        self.assertEqual(lote['huella'], self.tiktok()['huella'])
        self.assertEqual(item['sha256'], lote['sha256'])

    def test_renombrar_archivo_no_duplica_datos(self):
        lote = self.tiktok()
        renombrado = self.ruta.with_name('renombrado.csv')
        renombrado.write_bytes(self.ruta.read_bytes())
        self.assertEqual(lote['huella'], leer_importacion(renombrado, 'tiktok_manual')['huella'])

    def test_duplicados_se_rechazan_antes_de_guardar(self):
        self.tiktok()
        with self.ruta.open(encoding='utf-8-sig') as archivo:
            filas = list(csv.reader(archivo))
        with self.ruta.open('w', encoding='utf-8-sig', newline='') as archivo:
            csv.writer(archivo).writerows([*filas, filas[1]])
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            leer_importacion(self.ruta, 'tiktok_manual')

    def test_cifras_abreviadas_se_conservan_sin_estimar(self):
        item = self.tiktok(valor='', valor_original='1.2M', pais='ND')['items'][0]
        self.assertIsNone(item['valor'])
        self.assertIsNone(item['pais'])
        self.assertEqual(item['etiqueta_original'], '1.2M')

    def test_no_acepta_fechas_futuras_numeros_falsos_o_url_ajena(self):
        for cambios in ({'fecha': (date.today() + timedelta(days=1)).isoformat()}, {'valor': 'nan'},
                        {'valor': 'inf'}, {'valor': '-1'}, {'valor': '1.2M'}, {'valor': '1.2'},
                        {'url': 'https://tiktok.com.evil.test/'}, {'metrica': 'ventas_inventadas'}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                self.tiktok(**cambios)

    def test_serie_no_mezcla_pais_metrica_ventana_tipo(self):
        original = self.tiktok()['items'][0]['clave_serie']
        for cambio in ({'pais': 'MX'}, {'metrica': 'publicaciones'}, {'periodo': '30 días'},
                       {'contexto': 'otra escala'}, {'tipo': 'hashtag'}):
            self.assertNotEqual(original, self.tiktok(**cambio)['items'][0]['clave_serie'])
        self.assertEqual(original, self.tiktok(fecha='2025-01-02')['items'][0]['clave_serie'])

    def test_google_timeline_infiere_termino_y_valida_pais(self):
        self.ruta.write_text('Day,prueba: (Peru)\n2025-01-01,20\n2025-01-02,<1\n2025-01-03,30', encoding='utf-8-sig')
        lote = leer_importacion(self.ruta, 'google_timeline')
        self.assertEqual(lote['items'][0]['termino'], 'prueba')
        self.assertIsNone(lote['items'][1]['valor'])
        self.assertTrue(lote['items'][-1]['parcial'])
        self.assertEqual(len({i['clave_serie'] for i in lote['items']}), 1)
        with self.assertRaises(ValueError):
            leer_importacion(self.ruta, 'google_timeline', pais='MX')

    def test_google_archivos_no_concatenan_escalas(self):
        self.ruta.write_text('Day,prueba: (Peru)\n2025-01-01,20\n2025-01-02,30', encoding='utf-8')
        a = leer_importacion(self.ruta, 'google_timeline')['items'][0]
        self.ruta.write_text('Day,prueba: (Peru)\n2025-01-01,40\n2025-01-02,60', encoding='utf-8')
        b = leer_importacion(self.ruta, 'google_timeline')['items'][0]
        self.assertNotEqual(a['clave_serie'], b['clave_serie'])

    def test_related_descubre_sin_semillas_y_breakout_no_es_100(self):
        self.ruta.write_text('Categoría: Todas\n\nTOP\nproducto desconocido,45\n\nRISING\nslime,Breakout\ntermo,+250%', encoding='utf-8-sig')
        lote = leer_importacion(self.ruta, 'google_related', referencia='juguetes', periodo='mes', fecha='2025-01-01')
        self.assertEqual(len(lote['items']), 3)
        self.assertEqual(lote['items'][0]['categoria'], 'otros')
        self.assertIsNone(lote['items'][1]['valor'])
        self.assertEqual(lote['items'][2]['valor'], 250)
        self.assertNotEqual(lote['items'][0]['clave_serie'], lote['items'][1]['clave_serie'])

    def test_google_now_preserva_cifras_aproximadas(self):
        self.ruta.write_text('Trends,Search volume,Started,Ended,Trend breakdown\nprueba,2000+,2025-01-01,,prueba', encoding='utf-8')
        item = leer_importacion(self.ruta, 'google_now', fecha='2025-01-01')['items'][0]
        self.assertIsNone(item['valor'])
        self.assertEqual(item['etiqueta_original'], '2000+')

    def test_preview_no_escritura_y_confirmacion_revalida_archivo(self):
        self.tiktok()
        repo = Mock()
        servicio = TendenciasService(repo)
        opciones = dict(ruta=str(self.ruta), formato='tiktok_manual')
        respuesta = servicio.ejecutar('previsualizar_radar', **opciones)
        repo.guardar_lote.assert_not_called()
        self.tiktok(valor='200')
        with self.assertRaisesRegex(ValueError, 'cambió'):
            servicio.ejecutar('importar_radar', **opciones, huella_confirmada=respuesta['preview']['huella'], id_usuario=1)
        repo.guardar_lote.assert_not_called()

    def test_confirmacion_guarda_y_recarga(self):
        self.tiktok()
        repo = Mock()
        repo.cargar_senales.return_value = []
        servicio = TendenciasService(repo)
        opciones = dict(ruta=str(self.ruta), formato='tiktok_manual')
        preview = servicio.ejecutar('previsualizar_radar', **opciones)['preview']
        r = servicio.ejecutar('importar_radar', **opciones, huella_confirmada=preview['huella'], id_usuario=1)
        self.assertIn('guardada', r['mensaje'])
        repo.guardar_lote.assert_called_once()


if __name__ == '__main__':
    unittest.main()
