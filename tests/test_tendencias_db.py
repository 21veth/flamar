"""Integración optativa: esquema aislado en una transacción que siempre se revierte."""

import os
import re
import unittest
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg

from config.database import obtener_conexion
from models.tendencia import PuntoInteres, SerieInteres
from repositories.tendencias_repository import TendenciasRepository
from services.importacion_tendencias import huella_json, preparar_items


@unittest.skipUnless(os.getenv('FLAMAR_TEST_DB') == '1', 'Requiere FLAMAR_TEST_DB=1 y PostgreSQL configurado')
class RepositorioPostgresTests(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion()
        self.addCleanup(self.conexion.close)
        self.addCleanup(self.conexion.rollback)
        esquema = 'radar_test_' + uuid.uuid4().hex

        class CursorAislado(psycopg.Cursor):
            def execute(self, query, params=None, **kwargs):
                if isinstance(query, str):
                    query = query.replace('public.', esquema + '.')
                return super().execute(query, params, **kwargs)

        self.conexion.cursor_factory = CursorAislado
        raiz = Path(__file__).resolve().parents[1]
        with self.conexion.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA {esquema}')
            cursor.execute(f'SET LOCAL search_path TO {esquema}')
            cursor.execute("SET LOCAL statement_timeout TO '10s'")
            for nombre in ('flamar_postgres.sql', 'radar_tendencias.sql', 'radar_busqueda_automatica.sql', 'radar_datos_reales.sql'):
                sql = (raiz / 'database' / nombre).read_text(encoding='utf-8')
                sql = re.sub(r'^\s*(?:BEGIN|COMMIT);\s*$', '', sql, flags=re.MULTILINE)
                cursor.execute(sql)
            cursor.execute("INSERT INTO usuarios(usuario, password_hash, rol) VALUES ('test_radar', 'no_login', 'administrador') RETURNING id_usuario")
            self.usuario = cursor.fetchone()[0]
            cursor.execute("INSERT INTO categorias(nombre) VALUES ('Categoría de prueba') RETURNING id_categoria")
            self.categoria = cursor.fetchone()[0]
            cursor.execute("INSERT INTO productos(codigo, nombre, id_categoria) VALUES ('TEST-RADAR', 'Producto de prueba', %s) RETURNING id_producto", (self.categoria,))
            self.producto = cursor.fetchone()[0]

        @contextmanager
        def conexion_aislada():
            yield self.conexion

        parche = patch('repositories.tendencias_repository.obtener_conexion', conexion_aislada)
        parche.start()
        self.addCleanup(parche.stop)
        self.repo = TendenciasRepository()

    def crear_tema(self):
        self.repo.guardar_tema('squishy', 'squishy', self.categoria, self.producto, None, self.usuario)
        return self.repo.cargar()['temas'][0]['id_tema']

    def test_migracion_y_catalogo_real(self):
        datos = self.repo.cargar()
        self.assertEqual(datos['temas'], [])
        self.assertEqual(datos['productos'][0]['unidades_30d'], 0)
        self.assertTrue(self.repo.guardar_tema('squishy', 'squishy', None, self.producto, None, self.usuario))
        self.assertFalse(self.repo.guardar_tema('squishy', 'squishy', None, None, None, self.usuario))
        tema = self.repo.cargar()['temas'][0]
        self.assertEqual(tema['id_categoria'], self.categoria)
        self.assertEqual(tema['codigo_producto'], 'TEST-RADAR')

    def test_series_deduplicadas_y_mas_reciente_por_pais(self):
        id_tema = self.crear_tema()
        def serie(dias, pais='PE', parcial=False):
            puntos = tuple(PuntoInteres(date.today() - timedelta(days=dias + 8 - i), i * 10, str(i * 10), parcial and i == 7) for i in range(8))
            return SerieInteres('squishy', pais, 'dia', puntos, 'prueba.csv', str(dias).zfill(64), 'https://trends.google.com/trends/explore')
        self.assertTrue(self.repo.guardar_serie(id_tema, serie(0), self.usuario))
        self.assertFalse(self.repo.guardar_serie(id_tema, serie(0), self.usuario))
        self.repo.guardar_serie(id_tema, serie(90), self.usuario)  # Importar algo antiguo no reemplaza lo actual.
        self.repo.guardar_serie(id_tema, serie(0, 'US'), self.usuario)
        self.assertTrue(self.repo.guardar_serie(id_tema, serie(0, parcial=True), self.usuario))
        series = self.repo.cargar()['series']
        self.assertEqual(len(series), 2)
        pe = next(s for s in series if s['pais'] == 'PE')
        self.assertEqual(pe['hasta'], date.today() - timedelta(days=1))
        self.assertIsInstance(pe['puntos'], list)
        self.assertTrue(pe['puntos'][-1]['parcial'])

    def test_feed_upsert_y_evidencia_deduplicada(self):
        id_tema = self.crear_tema()
        r = dict(termino='consulta de prueba', pais='PE', publicado=datetime.now(timezone.utc),
                 trafico='100+', url='https://trends.google.com/', feed_url='https://trends.google.com/trending/rss?geo=PE', noticias=[])
        self.repo.guardar_descubrimientos([r])
        r['trafico'] = '200+'
        self.repo.guardar_descubrimientos([r])
        self.assertTrue(self.repo.guardar_evidencia(id_tema, 'PE', 'https://www.tiktok.com/@test/video/1', date.today(), 'Prueba', self.usuario))
        self.assertFalse(self.repo.guardar_evidencia(id_tema, 'PE', 'https://www.tiktok.com/@test/video/1', date.today(), 'No sobrescribir', self.usuario))
        datos = self.repo.cargar()
        self.assertEqual(len(datos['descubrimientos']), 1)
        self.assertEqual(datos['descubrimientos'][0]['trafico'], '200+')
        self.assertEqual(datos['evidencias'][0]['nota'], 'Prueba')

    def test_categoria_incompatible_rechazada(self):
        with self.assertRaisesRegex(ValueError, 'categoría no coincide'):
            self.repo.guardar_tema('prueba', 'prueba', self.categoria + 1, self.producto, None, self.usuario)

    def test_historial_simple_guarda_y_recupera_snapshot_sin_crear_productos(self):
        self.assertIsNone(self.repo.cargar_busqueda())
        resultado = {'items': [], 'modo': 'gratuito', 'consultado_en': datetime.now(timezone.utc).isoformat()}
        self.repo.guardar_busqueda(resultado, self.usuario)
        self.assertEqual(self.repo.cargar_busqueda(), resultado)
        self.assertEqual(self.repo.cargar()['temas'], [])

    def senal(self, fecha='2025-01-01', valor=20, pais='PE'):
        return preparar_items([dict(termino='Prueba de integración', fuente='tiktok', origen='tiktok_manual',
            pais=pais, metrica='reproducciones', contexto='mismos filtros/7DAY', tipo='producto',
            observado_en=fecha + 'T00:00:00+00:00', valor=valor, url='https://ads.tiktok.com/',
            categoria='otros', periodo='7DAY', proveedor='Prueba aislada')])[0]

    def lote(self, items):
        return dict(items=items, formato='tiktok_manual', huella=huella_json(items), archivo='prueba.csv')

    def test_nuevo_historial_deduplica_ordena_y_no_mezcla_paises(self):
        a, b, c = self.senal(), self.senal('2025-01-02', 40), self.senal(pais='MX')
        self.assertTrue(self.repo.guardar_lote(self.lote([a, b, c]), self.usuario))
        self.assertFalse(self.repo.guardar_lote(self.lote([a, b, c]), self.usuario))
        ultimas = self.repo.cargar_senales()
        self.assertEqual(len(ultimas), 2)
        pe = next(i for i in ultimas if i['pais'] == 'PE')
        self.assertEqual(pe['valor'], 40)
        historia = self.repo.cargar_historia(a['clave_serie'])
        self.assertEqual([p['valor'] for p in historia], [20, 40])
        self.assertEqual(self.repo.cargar()['temas'], [])

    def test_correccion_preserva_auditoria_y_elige_ultima_revision(self):
        a = self.senal()
        self.repo.guardar_lote(self.lote([a]), self.usuario)
        corregida = self.senal(valor=25)
        self.repo.guardar_lote(self.lote([corregida]), self.usuario)
        self.assertEqual(self.repo.cargar_historia(a['clave_serie'])[0]['valor'], 25)
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM public.radar_senales')
            self.assertEqual(cursor.fetchone()[0], 2)

    def test_migracion_nueva_idempotente(self):
        sql = (Path(__file__).resolve().parents[1] / 'database/radar_datos_reales.sql').read_text(encoding='utf-8')
        sql = re.sub(r'^\s*(?:BEGIN|COMMIT);\s*$', '', sql, flags=re.MULTILINE)
        with self.conexion.cursor() as cursor:
            cursor.execute(sql)
        self.assertEqual(self.repo.cargar_senales(), [])

    def test_error_en_punto_no_deja_lote_parcial(self):
        import copy
        a = self.senal()
        invalida = copy.deepcopy(self.senal('2025-01-02'))
        invalida['observado_en'] = 'no-es-fecha'
        # Savepoint de prueba: producción usa el contexto transaccional de conexión.
        with self.assertRaises(psycopg.Error):
            with self.conexion.transaction():
                self.repo.guardar_lote(self.lote([a, invalida]), self.usuario)
        with self.conexion.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM public.radar_lotes')
            self.assertEqual(cursor.fetchone()[0], 0)
        self.assertEqual(self.repo.cargar_senales(), [])


if __name__ == '__main__':
    unittest.main()
