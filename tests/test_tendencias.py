"""Datos sintéticos exclusivamente de pruebas; no se distribuyen como tendencias."""

import hashlib
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock

import psycopg

from services.fuentes_tendencias import FuenteGoogleTrends, normalizar, url_segura
from services.tendencias_service import TendenciasService, analizar_serie, preparar_panel


def serie_prueba(valores, granularidad='dia', hasta=None):
    hasta = hasta or date.today()
    salto = 7 if granularidad == 'semana' else 1
    return {'id_tema': 1, 'pais': 'PE', 'granularidad': granularidad,
            'puntos': [{'fecha': (hasta - timedelta(days=(len(valores) - 1 - i) * salto)).isoformat(),
                        'valor': valor, 'parcial': False} for i, valor in enumerate(valores)]}


def datos_vacios():
    return dict(temas=[], series=[], evidencias=[], descubrimientos=[], categorias=[], productos=[])


class FuenteTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix='flamar_radar_')
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'multiTimeline.csv'

    def escribir(self, texto):
        self.ruta.write_text(texto, encoding='utf-8-sig')
        return self.ruta

    def csv(self, cabecera='Día,squishy: (Perú)', valores=('20', '30', '40')):
        inicio = date.today() - timedelta(days=len(valores))
        filas = '\n'.join(f'{inicio + timedelta(days=i)},{v}' for i, v in enumerate(valores))
        return self.escribir('Categoría: Todas las categorías\n\n' + cabecera + '\n' + filas)

    def test_csv_oficial_preambulo_bom_y_ultimo_parcial(self):
        serie = FuenteGoogleTrends.leer_csv(self.csv(), 'squishy', 'PE')
        self.assertEqual([p.valor for p in serie.puntos], [20, 30, 40])
        self.assertTrue(serie.puntos[-1].parcial)
        self.assertEqual(serie.huella, hashlib.sha256(self.ruta.read_bytes()).hexdigest())

    def test_censurado_no_inventa_valor(self):
        serie = FuenteGoogleTrends.leer_csv(self.csv(valores=('<1', '', '0')), 'squishy', 'PE', False)
        self.assertEqual([p.valor for p in serie.puntos], [None, None, 0])
        self.assertEqual(serie.puntos[0].original, '<1')

    def test_termino_o_pais_incorrecto(self):
        for termino, pais in (('otro', 'PE'), ('squishy', 'US')):
            with self.subTest(termino=termino, pais=pais), self.assertRaises(ValueError):
                FuenteGoogleTrends.leer_csv(self.csv(), termino, pais)

    def test_multiples_terminos_rechazados(self):
        with self.assertRaisesRegex(ValueError, 'un solo término'):
            FuenteGoogleTrends.leer_csv(self.csv('Día,squishy: (Perú),termo: (Perú)'), 'squishy', 'PE')

    def test_rechaza_valores_fuera_de_rango(self):
        for invalido in ('101', '-1', '1.5', 'nan', 'texto'):
            with self.subTest(valor=invalido), self.assertRaises(ValueError):
                FuenteGoogleTrends.leer_csv(self.csv(valores=('10', invalido)), 'squishy', 'PE')

    def test_rechaza_csv_de_tendencias_actuales(self):
        with self.assertRaisesRegex(ValueError, 'Interés a lo largo'):
            FuenteGoogleTrends.leer_csv(self.escribir('Tendencia,Volumen\nsquishy,1000+'), 'squishy', 'PE')

    def test_rechaza_intervalos_faltantes(self):
        with self.assertRaisesRegex(ValueError, 'intervalos faltantes'):
            FuenteGoogleTrends.leer_csv(self.escribir('Day,squishy: (Peru)\n2025-01-01,20\n2025-01-03,30'), 'squishy', 'PE')

    def test_rechaza_fechas_duplicadas_o_invertidas(self):
        for fecha in ('2025-01-01', '2024-12-31'):
            with self.subTest(fecha=fecha), self.assertRaises(ValueError):
                FuenteGoogleTrends.leer_csv(self.escribir('Day,squishy: (Peru)\n2025-01-01,20\n' + fecha + ',30'), 'squishy', 'PE')

    def test_rechaza_futuro(self):
        fecha = date.today() + timedelta(days=1)
        with self.assertRaises(ValueError):
            FuenteGoogleTrends.leer_csv(self.escribir(f'Day,squishy: (Peru)\n{date.today()},20\n{fecha},30'), 'squishy', 'PE')

    def test_admite_mensual_y_semanal(self):
        for cabecera, fechas, esperado in (('Month', ('2025-01', '2025-02'), 'mes'),
                                          ('Semana', ('2025-01-05', '2025-01-12'), 'semana')):
            with self.subTest(cabecera=cabecera):
                ruta = self.escribir(f'{cabecera},squishy: (Perú)\n{fechas[0]},10\n{fechas[1]},20')
                serie = FuenteGoogleTrends.leer_csv(ruta, 'squishy', 'PE', False)
                self.assertEqual(serie.granularidad, esperado)

    def test_rechaza_archivo_grande(self):
        with self.assertRaisesRegex(ValueError, '2 MB'):
            FuenteGoogleTrends.leer_csv(self.escribir('a' * 2_000_001), 'squishy', 'PE')

    def test_rss_con_trafico_y_noticia(self):
        xml = b'''<rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item>
        <title>producto de prueba &amp; accesorios</title><pubDate>Tue, 10 Nov 2026 12:00:00 GMT</pubDate>
        <ht:approx_traffic>1000+</ht:approx_traffic><ht:news_item>
        <ht:news_item_title>Nota de prueba</ht:news_item_title>
        <ht:news_item_url>https://example.com/noticia</ht:news_item_url></ht:news_item>
        </item></channel></rss>'''
        filas = FuenteGoogleTrends.leer_rss(xml, 'PE', 'https://trends.google.com/trending/rss?geo=PE')
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['trafico'], '1000+')
        self.assertEqual(filas[0]['termino'], 'producto de prueba & accesorios')
        self.assertEqual(len(filas[0]['noticias']), 1)
        self.assertIsNotNone(filas[0]['publicado'].tzinfo)

    def test_rss_vacio_es_valido_pero_html_y_xml_hostil_no(self):
        self.assertEqual(FuenteGoogleTrends.leer_rss(b'<rss><channel/></rss>', 'PE', ''), [])
        for contenido in (b'<html/>', b'<!DOCTYPE a><rss/>', b'<rss>', b'<!ENTITY a "a">'):
            with self.subTest(contenido=contenido), self.assertRaises(ValueError):
                FuenteGoogleTrends.leer_rss(contenido, 'PE', '')

    def test_enlaces_solo_https_y_dominio_real(self):
        for enlace in ('https://www.tiktok.com/@test/video/1', 'https://ads.tiktok.com/business/creativecenter/'):
            self.assertTrue(url_segura(enlace, 'tiktok.com'))
        for enlace in ('https://tiktok.com.evil.com/', 'https://eviltiktok.com/', 'file:///test',
                       'javascript:alert(1)', 'http://tiktok.com/', 'https://user:pw@tiktok.com/',
                       'https://tiktok.com:8080/', 'https://[malformado'):
            self.assertFalse(url_segura(enlace, 'tiktok.com'))

    def test_normalizar(self):
        self.assertEqual(normalizar('  PERÚ  Squishy '), 'peru squishy')


class AnalisisTests(unittest.TestCase):
    def test_fases_explicables(self):
        for valores, esperado in (([10] * 4 + [30] * 4, 'Emergente'),
                                  ([30] * 4 + [60] * 4, 'En crecimiento'),
                                  ([60] * 8, 'Consolidada'),
                                  ([70] * 4 + [30] * 4, 'En descenso'),
                                  ([8] * 8, 'Sin señal clara')):
            with self.subTest(esperado=esperado):
                a = analizar_serie(serie_prueba(valores))
                self.assertEqual(a.estado, esperado)
                self.assertTrue(a.reciente)

    def test_base_cero_no_inventa_porcentaje(self):
        a = analizar_serie(serie_prueba([0] * 4 + [20] * 4))
        self.assertEqual(a.estado, 'Emergente')
        self.assertIsNone(a.crecimiento)

    def test_sin_serie_no_hay_datos(self):
        self.assertEqual(analizar_serie(None).estado, 'Sin datos')

    def test_censurados_y_pocos_puntos_no_clasifican(self):
        for valores in ([10] * 7, [10] * 7 + [None]):
            self.assertEqual(analizar_serie(serie_prueba(valores)).estado, 'Datos insuficientes')

    def test_parcial_excluido_del_analisis(self):
        serie = serie_prueba([10] * 4 + [20] * 4 + [100])
        serie['puntos'][-1]['parcial'] = True
        self.assertEqual(analizar_serie(serie).interes, 20)

    def test_serie_obsoleta_no_se_presenta_como_actual(self):
        a = analizar_serie(serie_prueba([20] * 4 + [80] * 4, hasta=date.today() - timedelta(days=60)))
        self.assertFalse(a.reciente)
        self.assertIn('desactualizado', a.motivo)

    def test_internacional_sin_peru_no_recomienda_compra(self):
        datos = datos_vacios()
        datos['temas'] = [{'id_tema': 1, 'termino': 'prueba'}]
        serie = serie_prueba([20] * 4 + [80] * 4)
        serie['pais'] = 'US'
        datos['series'] = [serie]
        fila = preparar_panel(datos)[0]
        self.assertEqual(fila['oportunidad'], 'Validar señal en Perú')

    def test_filtro_temporal_no_renormaliza(self):
        datos = datos_vacios()
        datos['temas'] = [{'id_tema': 1, 'termino': 'prueba'}]
        datos['series'] = [serie_prueba([20] * 4 + [80] * 4)]
        original = datos['series'][0]['puntos'][:]
        fila = preparar_panel(datos, dias=3)[0]
        self.assertEqual([p['valor'] for p in fila['series']['PE']['puntos']], [80] * 4)
        self.assertEqual(datos['series'][0]['puntos'], original)
        self.assertEqual(fila['analisis']['PE'].estado, 'Datos insuficientes')


class ServicioTests(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.repo.cargar.return_value = datos_vacios()
        self.fuente = Mock()
        self.servicio = TendenciasService(self.repo, self.fuente)

    def test_carga_sin_consultar_red(self):
        self.assertEqual(self.servicio.ejecutar('cargar')['datos'], datos_vacios())
        self.fuente.obtener_descubrimientos.assert_not_called()

    def test_sincronizacion_parcial_conserva_pais_exitoso(self):
        self.fuente.obtener_descubrimientos.side_effect = [[], ValueError('sin cobertura')]
        resultado = self.servicio.ejecutar('sincronizar', pais='US')
        self.assertIn('sin cobertura', resultado['mensaje'])
        self.repo.guardar_descubrimientos.assert_called_once_with([])

    def test_sincronizacion_fallida_no_inventa_resultados(self):
        self.fuente.obtener_descubrimientos.side_effect = ValueError('sin red')
        with self.assertRaisesRegex(ValueError, 'sin red'):
            self.servicio.ejecutar('sincronizar', pais='US')
        self.repo.guardar_descubrimientos.assert_not_called()

    def test_sincronizar_peru_no_duplica_peticion(self):
        self.fuente.obtener_descubrimientos.return_value = []
        self.servicio.ejecutar('sincronizar', pais='PE')
        self.fuente.obtener_descubrimientos.assert_called_once_with('PE')

    def test_terminos_vacios_no_se_guardan(self):
        with self.assertRaises(ValueError):
            self.servicio.ejecutar('crear', termino='  ', id_usuario=1)
        self.repo.guardar_tema.assert_not_called()

    def test_duplicado_no_sobrescribe(self):
        self.repo.guardar_tema.return_value = False
        resultado = self.servicio.ejecutar('crear', termino='Prueba', id_usuario=1)
        self.assertIn('no se modificó', resultado['mensaje'])

    def test_tablas_ausentes_ofrecen_migracion(self):
        self.repo.cargar.side_effect = psycopg.errors.UndefinedTable()
        with self.assertRaisesRegex(ValueError, 'radar_tendencias.sql'):
            self.servicio.ejecutar('cargar')

    def test_error_db_no_filtra_credenciales(self):
        self.repo.cargar.side_effect = psycopg.OperationalError('password=secreto')
        with self.assertRaises(ValueError) as error:
            self.servicio.ejecutar('cargar')
        self.assertNotIn('secreto', str(error.exception))

    def test_evidencia_sin_tema_es_rechazada(self):
        with self.assertRaisesRegex(ValueError, 'producto en seguimiento'):
            self.servicio.ejecutar('evidencia', id_tema=1)

    def test_evidencia_manual_se_guarda_sin_consultar_tiktok(self):
        self.repo.cargar.return_value['temas'] = [{'id_tema': 1, 'termino': 'prueba'}]
        resultado = self.servicio.ejecutar('evidencia', id_tema=1, pais='PE',
            url='https://www.tiktok.com/@test/video/1', observado_el=date.today(), nota='Observación de prueba', id_usuario=1)
        self.assertIn('no ha sido verificada', resultado['mensaje'])
        self.repo.guardar_evidencia.assert_called_once()


if __name__ == '__main__':
    unittest.main()
