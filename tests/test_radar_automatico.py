"""Fixtures solo para probar contratos: no se muestran en el radar real."""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import psycopg

from services.radar_automatico import FuenteSerpApi, RadarAutomatico, clasificar_consulta
from services.tendencias_service import TendenciasService
from config.radar import conexion_comercial


class ConfiguracionTests(unittest.TestCase):
    def test_sin_autorizacion_explicita_una_clave_no_activa_consumo(self):
        with patch.dict('os.environ', {'SERPAPI_API_KEY': 'clave_solo_de_prueba', 'RADAR_SERPAPI_ENABLED': 'false'}):
            self.assertEqual(conexion_comercial(), '')

    def test_autorizacion_y_clave_requeridas(self):
        with patch.dict('os.environ', {'SERPAPI_API_KEY': '', 'RADAR_SERPAPI_ENABLED': 'true'}):
            self.assertEqual(conexion_comercial(), '')
        with patch.dict('os.environ', {'SERPAPI_API_KEY': 'clave_solo_de_prueba', 'RADAR_SERPAPI_ENABLED': 'true'}):
            self.assertEqual(conexion_comercial(), 'clave_solo_de_prueba')


class ClasificacionTests(unittest.TestCase):
    def test_categorias_a_partir_de_consultas_reales_recibidas(self):
        for consulta, categoria in (('tazas navideñas', 'navidad'), ('slime', 'juegos'),
                                    ('squishies', 'juegos'), ('aspiradora robot', 'limpieza'),
                                    ('organizador de cocina', 'hogar'), ('regalos para mama', 'regalos')):
            with self.subTest(consulta=consulta):
                self.assertEqual(clasificar_consulta(consulta)[0], categoria)

    def test_deportes_y_politica_no_son_productos(self):
        for consulta in ('stephen curry', 'presidente peru', 'partido peru vs chile'):
            self.assertEqual(clasificar_consulta(consulta), (None, None))

    def test_navidad_y_peliculas_no_implican_demanda_de_merchandising(self):
        self.assertEqual(clasificar_consulta('navidad'), ('navidad', 'tema'))
        self.assertEqual(clasificar_consulta('peliculas de estreno'), ('peliculas', 'tema'))


class ContratoProveedorTests(unittest.TestCase):
    def test_google_top_y_rising_separados_sin_ranking_global(self):
        datos = {'related_queries': {
            'rising': [{'query': 'tazas navideñas', 'value': '+250%', 'extracted_value': 250}],
            'top': [{'query': 'tazas navideñas', 'value': '100', 'extracted_value': 100},
                    {'query': 'luces navideñas', 'value': '72', 'extracted_value': 72}],
        }}
        filas = FuenteSerpApi.leer_google(datos, 'navidad')
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]['metrica'], 'crecimiento')
        self.assertEqual(filas[0]['valor'], 250)
        self.assertEqual(filas[1]['metrica'], 'interes_relativo')
        self.assertTrue(all(f['pais'] == 'PE' for f in filas))

    def test_google_sin_volumen_no_genera_ejemplos(self):
        self.assertEqual(FuenteSerpApi.leer_google({'related_queries': {}}, 'hogar'), [])

    def test_breakout_no_se_convierte_en_indice_100(self):
        filas = FuenteSerpApi.leer_google({'related_queries': {'rising': [
            {'query': 'squishy', 'value': 'Breakout'}]}}, 'juegos')
        self.assertIsNone(filas[0]['valor'])
        self.assertEqual(filas[0]['etiqueta_original'], 'Breakout')

    def test_indices_invalidos_no_se_muestran(self):
        for valor in (-1, 101, float('inf'), float('nan'), True):
            filas = FuenteSerpApi.leer_google({'related_queries': {'top': [
                {'query': 'squishy', 'extracted_value': valor}]}}, 'juegos')
            self.assertEqual(filas, [])

    def test_tiktok_reproducciones_no_son_busquedas_ni_son_peruanas(self):
        filas = FuenteSerpApi.leer_tiktok({'video_results': [
            {'description': 'Squishy de prueba', 'plays': 12400,
             'link': 'https://www.tiktok.com/@test/video/1'}]}, 'juegos')
        self.assertEqual(filas[0]['metrica'], 'reproducciones')
        self.assertEqual(filas[0]['tipo'], 'video')
        self.assertIsNone(filas[0]['pais'])

    def test_tiktok_ignora_links_inseguros_y_no_inventa_metricas(self):
        datos = {'video_results': [
            {'description': 'slime de prueba', 'link': 'https://evil.com/'},
            {'description': 'slime de prueba', 'link': 'https://www.tiktok.com/@test/video/1'},
        ]}
        filas = FuenteSerpApi.leer_tiktok(datos, 'juegos')
        self.assertEqual(len(filas), 1)
        self.assertIsNone(filas[0]['valor'])

    def test_error_proveedor_no_expone_clave(self):
        with patch('services.radar_automatico.urlopen') as red:
            red.return_value.__enter__.return_value.read.return_value = b'{"error":"token PRIVADO rechazado"}'
            with self.assertRaises(ValueError) as error:
                FuenteSerpApi('PRIVADO').consultar('google', 'hogar')
            self.assertNotIn('PRIVADO', str(error.exception))


@patch('services.radar_automatico.conexion_comercial', return_value='')
class BusquedaTests(unittest.TestCase):
    def test_un_clic_consulta_fuente_sin_requerir_terminos(self, _config):
        rss = Mock()
        rss.obtener_descubrimientos.return_value = [
            dict(termino='slime', trafico='200+', url='https://trends.google.com/', publicado=datetime.now(timezone.utc)),
            dict(termino='politica', trafico='1000+', url='https://trends.google.com/', publicado=datetime.now(timezone.utc)),
        ]
        resultado = RadarAutomatico(rss).buscar()
        self.assertEqual([i['termino'] for i in resultado['items']], ['slime'])
        rss.obtener_descubrimientos.assert_called_once_with('PE')

    def test_lista_vacia_no_se_rellena_con_semillas(self, _config):
        rss = Mock()
        rss.obtener_descubrimientos.return_value = []
        self.assertEqual(RadarAutomatico(rss).buscar()['items'], [])

    def test_clave_sola_no_habilita_solicitudes_comerciales(self, _config):
        rss = Mock()
        rss.obtener_descubrimientos.return_value = []
        with patch('services.radar_automatico.FuenteSerpApi') as proveedor:
            RadarAutomatico(rss).buscar()
            proveedor.assert_not_called()

    def test_cache_evital_consumo_repetido(self, _config):
        rss = Mock()
        rss.obtener_descubrimientos.return_value = []
        radar = RadarAutomatico(rss)
        radar.buscar()
        self.assertTrue(radar.buscar()['cache'])
        rss.obtener_descubrimientos.assert_called_once()

    def test_proveedor_maximo_doce_solicitudes_y_sin_rss(self, _config):
        proveedor = Mock()
        proveedor.consultar.return_value = []
        rss = Mock()
        resultado = RadarAutomatico(rss, proveedor).buscar()
        self.assertEqual(proveedor.consultar.call_count, 12)
        self.assertEqual(resultado['correctas'], 12)
        rss.obtener_descubrimientos.assert_not_called()

    def test_fallo_total_no_presenta_actualizacion_exitosa(self, _config):
        proveedor = Mock()
        proveedor.consultar.side_effect = ValueError('sin cuota')
        with self.assertRaises(ValueError):
            RadarAutomatico(proveedor=proveedor).buscar()

    def test_fallo_parcial_es_visible(self, _config):
        proveedor = Mock()
        proveedor.consultar.side_effect = lambda fuente, categoria: [] if fuente == 'google' else (_ for _ in ()).throw(ValueError('sin cobertura'))
        resultado = RadarAutomatico(proveedor=proveedor).buscar()
        self.assertEqual(resultado['correctas'], 6)
        self.assertEqual(len(resultado['advertencias']), 6)


class ServicioSimpleTests(unittest.TestCase):
    def test_consulta_funciona_sin_migracion_del_historial(self):
        repo, radar = Mock(), Mock()
        radar.buscar.return_value = {'items': [], 'cache': False}
        radar.estado_conexion.return_value = False
        repo.guardar_busqueda.side_effect = psycopg.errors.UndefinedTable()
        resultado = TendenciasService(repositorio=repo, radar=radar).ejecutar('buscar_radar', id_usuario=1)
        self.assertFalse(resultado['historial'])
        self.assertEqual(resultado['radar']['items'], [])

    def test_cargar_historial_no_consulta_api(self):
        repo, radar = Mock(), Mock()
        repo.cargar_busqueda.return_value = None
        resultado = TendenciasService(repositorio=repo, radar=radar).ejecutar('cargar_radar')
        self.assertIsNone(resultado['radar'])
        radar.buscar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
