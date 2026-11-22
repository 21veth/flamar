"""Contratos con fixtures solo de prueba, nunca resultados del radar real."""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from config.radar import conexion_tiktok
from services.radar_automatico import RadarAutomatico, clasificar_consulta
from services.tendencias_service import TendenciasService
from services.tiktok_discovery import FuenteTikTokDiscovery


def configuracion(**opciones):
    return dict(dict(habilitado=True, advertiser_token='', advertiser_id='', business_token='', business_id=''), **opciones)


class ClasificacionTests(unittest.TestCase):
    def test_categorias_de_consultas_recibidas(self):
        for consulta, categoria in (('tazas navideñas', 'navidad'), ('slime', 'juegos'),
                                   ('aspiradora robot', 'limpieza'), ('organizador de cocina', 'hogar')):
            self.assertEqual(clasificar_consulta(consulta)[0], categoria)

    def test_noticias_no_son_productos(self):
        for consulta in ('stephen curry', 'presidente peru', 'partido peru vs chile'):
            self.assertEqual(clasificar_consulta(consulta), (None, None))
        self.assertEqual(clasificar_consulta('navidad'), ('navidad', 'tema'))


class TikTokTests(unittest.TestCase):
    def test_sin_habilitacion_no_envia_tokens(self):
        with patch.dict('os.environ', {'RADAR_TIKTOK_ENABLED': 'false', 'TIKTOK_ADVERTISER_ACCESS_TOKEN': 'PRIVADO'}):
            self.assertEqual(conexion_tiktok()['advertiser_token'], '')

    def test_sin_cuenta_autorizada_no_consulta(self):
        fuente = FuenteTikTokDiscovery(configuracion())
        with patch.object(fuente, '_get') as red:
            items, avisos, correctas = fuente.obtener()
        red.assert_not_called()
        self.assertEqual(items, [])
        self.assertEqual(correctas, 0)
        self.assertTrue(avisos)

    def test_busquedas_no_inventan_pais_ni_volumen(self):
        fuente = FuenteTikTokDiscovery(configuracion(business_token='PRIVADO', business_id='test'))
        with patch.object(fuente, '_get', return_value={'search_keywords': ['slime', 'producto desconocido']}) as red:
            items, avisos, correctas = fuente.obtener()
        self.assertEqual(correctas, 1)
        self.assertFalse(avisos)
        self.assertTrue(all(i['pais'] is None and i['valor'] is None for i in items))
        self.assertEqual(items[1]['categoria'], 'otros')
        self.assertNotIn('country_code', red.call_args.args[2])

    def test_hashtags_solo_peru_confirmado_y_sin_fallback(self):
        fuente = FuenteTikTokDiscovery(configuracion(advertiser_token='PRIVADO', advertiser_id='test'))
        for filtros in ({}, {'country_code': 'US', 'date_range': '7DAY'}, {'country_code': 'PE', 'date_range': '30DAY'}):
            with patch.object(fuente, '_get', return_value={'filter_info': filtros, 'list': []}) as red:
                items, avisos, correctas = fuente.obtener()
            self.assertEqual(items, [])
            self.assertTrue(avisos)
            self.assertEqual(correctas, 0)
            red.assert_called_once()
            self.assertEqual(red.call_args.args[2]['country_code'], 'PE')

    def test_hashtags_no_son_productos_validados(self):
        fuente = FuenteTikTokDiscovery(configuracion(advertiser_token='PRIVADO', advertiser_id='test'))
        datos = {'filter_info': {'country_code': 'PE', 'date_range': '7DAY'},
                 'list': [{'hashtag_name': 'slime', 'views': 100}, {'hashtag_name': 'otro', 'views': True}]}
        with patch.object(fuente, '_get', return_value=datos):
            items, _, _ = fuente.obtener()
        self.assertEqual(items[0]['tipo'], 'hashtag')
        self.assertEqual(items[0]['valor'], 100)
        self.assertIsNone(items[1]['valor'])

    def test_error_api_no_filtra_secretos(self):
        with patch('services.tiktok_discovery.urlopen') as red:
            red.return_value.__enter__.return_value.read.return_value = b'{"code":401,"message":"PRIVADO"}'
            with self.assertRaises(ValueError) as error:
                FuenteTikTokDiscovery._get('discovery/trending_list', 'PRIVADO', {})
        self.assertNotIn('PRIVADO', str(error.exception))


class BusquedaTests(unittest.TestCase):
    def setUp(self):
        self.rss, self.tiktok = Mock(), Mock()
        self.tiktok.configurada.return_value = False
        self.tiktok.obtener.return_value = ([], ['TikTok sin autorización'], 0)
        self.rss.obtener_descubrimientos.return_value = []
        self.radar = RadarAutomatico(self.rss, self.tiktok)

    def test_vacio_no_se_rellena(self):
        self.assertEqual(self.radar.buscar()['items'], [])

    def test_solo_consultas_comerciales_del_rss(self):
        self.rss.obtener_descubrimientos.return_value = [
            dict(termino=t, trafico='200+', url='https://trends.google.com/', publicado=datetime.now(timezone.utc))
            for t in ('slime', 'stephen curry')]
        r = self.radar.buscar()
        self.assertEqual([i['termino'] for i in r['items']], ['slime'])
        self.assertEqual(r['recibidas_rss'], 2)
        self.assertIsNone(r['items'][0]['valor'])

    def test_cache_no_fabrica_observaciones(self):
        self.radar.buscar()
        self.assertTrue(self.radar.buscar()['cache'])
        self.rss.obtener_descubrimientos.assert_called_once_with('PE')

    def test_fallo_total_es_error(self):
        self.rss.obtener_descubrimientos.side_effect = ValueError('sin conexión')
        with self.assertRaisesRegex(ValueError, 'No respondió ninguna fuente'):
            self.radar.buscar()

    def test_respuesta_tiktok_vacia_es_exito_aunque_otro_endpoint_falle(self):
        self.rss.obtener_descubrimientos.side_effect = ValueError('sin conexión')
        self.tiktok.obtener.return_value = ([], ['permiso parcial'], 1)
        self.assertEqual(self.radar.buscar()['correctas'], 1)


class ServicioTests(unittest.TestCase):
    def test_carga_solo_postgres(self):
        repo, radar = Mock(), Mock()
        repo.cargar_senales.return_value = []
        resultado = TendenciasService(repo, radar=radar).ejecutar('cargar_radar')
        self.assertEqual(resultado['radar']['items'], [])
        radar.buscar.assert_not_called()

    def test_sin_bd_no_confirma_historial(self):
        repo, radar = Mock(), Mock()
        radar.buscar.return_value = {'items': [], 'consultado_en': datetime.now(timezone.utc).isoformat()}
        repo.guardar_lote.side_effect = ValueError('sin configuración')
        repo.cargar_senales.side_effect = ValueError('sin configuración')
        resultado = TendenciasService(repo, radar=radar).ejecutar('buscar_radar', id_usuario=1)
        self.assertFalse(resultado['historial'])
        self.assertIn('radar_datos_reales.sql', resultado['mensaje'])


if __name__ == '__main__':
    unittest.main()
