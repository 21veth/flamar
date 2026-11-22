from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from config.database import obtener_conexion


class TendenciasRepository:
    """SQL del radar; conexiones y transacciones como UsuarioRepository."""

    def guardar_lote(self, lote, id_usuario):
        """Lote y puntos en una transacción; un error no deja importaciones parciales."""
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '10s'")
                cursor.execute('''INSERT INTO public.radar_lotes
                    (huella, origen, archivo, sha256, metadata, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (huella) DO NOTHING RETURNING id_lote''',
                    (lote['huella'], lote['formato'], lote.get('archivo'), lote.get('sha256'),
                     Jsonb(lote.get('metadata', {})), id_usuario))
                fila = cursor.fetchone()
                if fila is None:
                    return False
                for item in lote['items']:
                    cursor.execute('''INSERT INTO public.radar_senales
                        (id_lote, clave_serie, termino, pais, observado_en, valor, datos)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                        (fila[0], item['clave_serie'], item['termino'], item.get('pais'),
                         item['observado_en'], item.get('valor'), Jsonb(item)))
                return True

    def cargar_senales(self):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute('''SELECT datos FROM (
                    SELECT DISTINCT ON (clave_serie) datos, observado_en, id_senal
                    FROM public.radar_senales
                    ORDER BY clave_serie, observado_en DESC, id_senal DESC
                    ) ultimas ORDER BY observado_en DESC, id_senal DESC''')
                return [fila[0] for fila in cursor.fetchall()]

    def cargar_historia(self, clave_serie):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute('''SELECT datos FROM (
                    SELECT DISTINCT ON (s.observado_en) s.datos, s.observado_en, s.id_senal
                    FROM public.radar_senales s WHERE s.clave_serie = %s
                    ORDER BY s.observado_en, s.id_senal DESC
                    ) puntos ORDER BY observado_en''', (clave_serie,))
                return [fila[0] for fila in cursor.fetchall()]

    def cargar_busqueda(self):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute('''SELECT resultado FROM public.radar_busquedas
                                  ORDER BY id_busqueda DESC LIMIT 1''')
                fila = cursor.fetchone()
        return fila[0] if fila else None

    def guardar_busqueda(self, resultado, id_usuario):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute('''INSERT INTO public.radar_busquedas (resultado, creado_por)
                                  VALUES (%s, %s)''', (Jsonb(resultado), id_usuario))

    def cargar(self):
        with obtener_conexion() as conexion:
            with conexion.cursor(row_factory=dict_row) as cursor:
                cursor.execute('''
                    SELECT t.*, c.nombre AS categoria, p.nombre AS producto,
                           p.codigo AS codigo_producto
                    FROM public.radar_temas t
                    LEFT JOIN public.categorias c USING (id_categoria)
                    LEFT JOIN public.productos p USING (id_producto)
                    ORDER BY t.creado_en DESC, t.id_tema DESC
                ''')
                temas = cursor.fetchall()
                cursor.execute('''
                    SELECT DISTINCT ON (id_tema, pais) * FROM public.radar_series
                    ORDER BY id_tema, pais, hasta DESC, importado_en DESC, id_serie DESC
                ''')
                series = cursor.fetchall()
                cursor.execute('''
                    SELECT * FROM public.radar_descubrimientos
                    WHERE consultado_en >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                    ORDER BY consultado_en DESC, publicado DESC LIMIT 300
                ''')
                descubrimientos = cursor.fetchall()
                cursor.execute('''SELECT * FROM public.radar_evidencias
                                  ORDER BY observado_el DESC, id_evidencia DESC''')
                evidencias = cursor.fetchall()
                cursor.execute('SELECT id_categoria, nombre FROM public.categorias ORDER BY nombre')
                categorias = cursor.fetchall()
                cursor.execute('''
                    SELECT p.id_producto, p.codigo, p.nombre, p.id_categoria,
                        COALESCE(r.unidades_30d, 0) AS unidades_30d
                    FROM public.productos p
                    LEFT JOIN (
                        SELECT d.id_producto, SUM(d.cantidad) AS unidades_30d
                        FROM public.ventas v
                        JOIN public.detalle_venta d USING (id_venta)
                        WHERE v.fecha >= CURRENT_DATE - 29 AND v.fecha <= CURRENT_DATE
                        GROUP BY d.id_producto
                    ) r USING (id_producto)
                    WHERE p.activo
                    ORDER BY p.nombre
                ''')
                productos = cursor.fetchall()
        return dict(temas=temas, series=series, descubrimientos=descubrimientos,
                    evidencias=evidencias, categorias=categorias, productos=productos)

    def guardar_tema(self, termino, clave, id_categoria, id_producto, imagen, id_usuario):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                if id_producto is not None:
                    cursor.execute('SELECT id_categoria FROM public.productos WHERE id_producto = %s AND activo', (id_producto,))
                    producto = cursor.fetchone()
                    if producto is None:
                        raise ValueError('El producto seleccionado ya no está activo.')
                    if id_categoria is not None and id_categoria != producto[0]:
                        raise ValueError('La categoría no coincide con el producto vinculado.')
                    id_categoria = producto[0]
                cursor.execute('''
                    INSERT INTO public.radar_temas
                        (termino, clave, id_categoria, id_producto, imagen_path, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (clave) DO NOTHING RETURNING id_tema
                ''', (termino, clave, id_categoria, id_producto, imagen, id_usuario))
                return cursor.fetchone() is not None

    def guardar_descubrimientos(self, registros):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                for r in registros:
                    cursor.execute('''
                        INSERT INTO public.radar_descubrimientos
                            (termino, pais, publicado, trafico, url, feed_url, noticias)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (pais, termino, publicado) DO UPDATE SET
                            trafico = EXCLUDED.trafico, noticias = EXCLUDED.noticias,
                            consultado_en = CURRENT_TIMESTAMP
                    ''', (r['termino'], r['pais'], r['publicado'], r['trafico'],
                          r['url'], r['feed_url'], Jsonb(r['noticias'])))

    def guardar_serie(self, id_tema, serie, id_usuario):
        puntos = [{'fecha': p.fecha.isoformat(), 'valor': p.valor,
                   'original': p.original, 'parcial': p.parcial} for p in serie.puntos]
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO public.radar_series
                        (id_tema, pais, granularidad, puntos, desde, hasta,
                         archivo, huella, ultimo_parcial, url, importado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id_tema, pais, huella, ultimo_parcial) DO NOTHING RETURNING id_serie
                ''', (id_tema, serie.pais, serie.granularidad, Jsonb(puntos),
                      serie.puntos[0].fecha, serie.puntos[-1].fecha, serie.archivo,
                      serie.huella, serie.puntos[-1].parcial, serie.url, id_usuario))
                return cursor.fetchone() is not None

    def guardar_evidencia(self, id_tema, pais, url, observado_el, nota, id_usuario):
        with obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO public.radar_evidencias
                        (id_tema, pais, url, observado_el, nota, registrado_por)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id_tema, pais, url, observado_el) DO NOTHING
                    RETURNING id_evidencia
                ''', (id_tema, pais, url, observado_el, nota, id_usuario))
                return cursor.fetchone() is not None
