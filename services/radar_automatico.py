"""Búsqueda de un clic. Nunca transforma ejemplos o semillas en resultados."""

import json
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config.radar import CATEGORIAS_RADAR, conexion_comercial
from services.fuentes_tendencias import FuenteGoogleTrends, normalizar, url_google, url_segura


# Vocabulario para descartar deportes/política/noticias ajenas a la tienda.
# Se usa exclusivamente como filtro de datos recibidos, nunca como resultados.
VOCABULARIO = {
    'hogar': ('taza', 'vaso', 'termo', 'tomatodo', 'organizador', 'lampara', 'luces', 'cojin', 'sarten', 'licuadora', 'adorno', 'decoracion', 'mueble', 'espejo', 'alfombra'),
    'limpieza': ('detergente', 'limpiador', 'desinfectante', 'trapeador', 'mopa', 'aspiradora', 'esponja', 'escoba', 'lejia', 'jabon', 'cepillo', 'lavavajilla'),
    'juegos': ('squishy', 'squishies', 'slime', 'labubu', 'lego', 'juguete', 'peluche', 'muneca', 'figura', 'rompecabezas', 'juego de mesa', 'funko', 'pokemon'),
    'navidad': ('navidad', 'navideno', 'navidena', 'arbol de navidad', 'christmas', 'nacimiento', 'guirnalda', 'esfera navidena'),
    'regalos': ('regalo', 'gift', 'perfume', 'pulsera', 'collar', 'llavero', 'chocolate', 'set de maquillaje'),
}


def contiene(texto, palabra):
    return bool(re.search(r'(?<!\w)' + re.escape(palabra) + r'(?:s|es)?(?!\w)', texto))


def clasificar_consulta(texto, categoria_origen=None):
    texto = normalizar(texto).replace('#', ' ')
    if any(contiene(texto, p) for p in VOCABULARIO['navidad']):
        # Navidad genérica es temática, no prueba de un producto concreto.
        if any(contiene(texto, p) for c in ('hogar', 'juegos', 'regalos') for p in VOCABULARIO[c]):
            return 'navidad', 'producto'
        return 'navidad', 'tema'
    for categoria in ('limpieza', 'juegos', 'hogar', 'regalos'):
        if any(contiene(texto, p) for p in VOCABULARIO[categoria]):
            return categoria, 'producto'
    if categoria_origen == 'peliculas' or any(contiene(texto, p) for p in ('pelicula', 'cine', 'estreno')):
        return 'peliculas', 'tema'
    return None, None


class FuenteSerpApi:
    """Proveedor opcional documentado; no es una API oficial de Google/TikTok."""

    def __init__(self, clave):
        self._clave = clave

    def consultar(self, fuente, categoria):
        ambito = CATEGORIAS_RADAR[categoria]
        if fuente == 'google':
            parametros = dict(engine='google_trends', q=ambito['google'], geo='PE',
                              date='today 1-m', hl='es', data_type='RELATED_QUERIES')
        else:
            parametros = dict(engine='tiktok_discover', q=ambito['tiktok'])
        parametros['api_key'] = self._clave
        peticion = Request('https://serpapi.com/search.json?' + urlencode(parametros),
                           headers={'Accept': 'application/json', 'User-Agent': 'FlamarRadar/1.0'})
        try:
            with urlopen(peticion, timeout=15) as respuesta:
                contenido = respuesta.read(2_000_001)
            if len(contenido) > 2_000_000:
                raise ValueError('Respuesta del proveedor demasiado grande.')
            datos = json.loads(contenido)
        except HTTPError as error:
            raise ValueError(f'Proveedor no disponible (HTTP {error.code}); revisa clave, cuota o cobertura.') from None
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            # Nunca incluir URLs de petición ni mensajes del proveedor: pueden contener claves.
            raise ValueError('No se pudo consultar el proveedor de tendencias.') from None
        if not isinstance(datos, dict) or datos.get('error'):
            raise ValueError('El proveedor no entregó resultados válidos; revisa cuota y disponibilidad.')
        return self.leer_google(datos, categoria) if fuente == 'google' else self.leer_tiktok(datos, categoria)

    @staticmethod
    def leer_google(datos, categoria):
        consultas = datos.get('related_queries')
        if not isinstance(consultas, dict):
            # Google puede no tener suficiente volumen para una consulta/país.
            if consultas is None:
                return []
            raise ValueError('Formato de consultas de Google no reconocido.')
        resultado = {}
        for grupo in ('rising', 'top'):
            filas = consultas.get(grupo, [])
            if not isinstance(filas, list):
                raise ValueError('Formato de consultas de Google no reconocido.')
            for posicion, fila in enumerate(filas[:25], 1):
                if not isinstance(fila, dict) or not isinstance(fila.get('query'), str):
                    continue
                termino = fila['query'].strip()[:200]
                clasificacion, tipo = clasificar_consulta(termino, categoria)
                if not termino or not clasificacion:
                    continue
                clave = normalizar(termino)
                if clave in resultado:
                    continue  # El crecimiento y el índice top son métricas distintas.
                valor = fila.get('extracted_value')
                numerico = (isinstance(valor, (int, float)) and not isinstance(valor, bool)
                            and math.isfinite(valor))
                if grupo == 'top' and (not numerico or not 0 <= valor <= 100):
                    continue
                if grupo == 'rising' and (not numerico or valor < 0):
                    valor = None
                resultado[clave] = {
                    'termino': termino, 'categoria': clasificacion, 'tipo': tipo,
                    'fuente': 'google', 'pais': 'PE',
                    'url': url_google(CATEGORIAS_RADAR[categoria]['google'], 'PE', 'today 1-m'),
                    'indicador': ('En aumento' if grupo == 'rising' else 'Búsqueda destacada'),
                    'valor': valor, 'metrica': 'crecimiento' if grupo == 'rising' else 'interes_relativo',
                    'etiqueta_original': str(fila.get('value', ''))[:50],
                    'referencia': CATEGORIAS_RADAR[categoria]['google'], 'posicion': posicion,
                    'periodo': 'Último mes', 'proveedor': 'SerpApi',
                }
        return list(resultado.values())

    @staticmethod
    def leer_tiktok(datos, categoria):
        videos = datos.get('video_results', [])
        if not isinstance(videos, list):
            raise ValueError('Formato de videos de TikTok no reconocido.')
        resultado = []
        for video in videos[:25]:
            if not isinstance(video, dict) or not isinstance(video.get('description'), str):
                continue
            descripcion = video['description'].strip()
            clasificacion, _tipo = clasificar_consulta(descripcion)
            enlace = video.get('link', '')
            if not clasificacion or not isinstance(enlace, str) or not url_segura(enlace, 'tiktok.com'):
                continue
            reproducciones = video.get('plays')
            if not isinstance(reproducciones, int) or isinstance(reproducciones, bool) or reproducciones < 0:
                reproducciones = None
            resultado.append({
                'termino': descripcion[:160], 'categoria': clasificacion, 'tipo': 'video',
                'fuente': 'tiktok', 'pais': None, 'url': enlace,
                'indicador': 'Video encontrado', 'valor': reproducciones, 'metrica': 'reproducciones',
                'referencia': CATEGORIAS_RADAR[categoria]['tiktok'], 'periodo': 'Discover · sin filtro temporal',
                'publicado': str(video.get('published_date', ''))[:50], 'proveedor': 'SerpApi',
            })
            if len(resultado) == 6:
                break
        return resultado


class RadarAutomatico:
    def __init__(self, fuente_gratuita=None, proveedor=None):
        self._rss = fuente_gratuita if fuente_gratuita is not None else FuenteGoogleTrends()
        self._proveedor = proveedor
        self._cache = None

    def estado_conexion(self):
        return bool(self._proveedor is not None or conexion_comercial())

    def buscar(self):
        ahora = datetime.now(timezone.utc)
        if self._cache and ahora - datetime.fromisoformat(self._cache['consultado_en']) < timedelta(minutes=15):
            return dict(self._cache, cache=True)
        clave = conexion_comercial()
        proveedor = self._proveedor if self._proveedor is not None else (FuenteSerpApi(clave) if clave else None)
        resultado = dict(items=[], advertencias=[], consultado_en=ahora.isoformat(), cache=False,
                         modo='comercial' if proveedor else 'gratuito', correctas=0)
        if proveedor is None:
            registros = self._rss.obtener_descubrimientos('PE')
            resultado['correctas'] = 1
            for r in registros:
                categoria, tipo = clasificar_consulta(r['termino'])
                if categoria:
                    resultado['items'].append({
                        'termino': r['termino'], 'categoria': categoria, 'tipo': tipo,
                        'fuente': 'google', 'pais': 'PE', 'url': 'https://trends.google.com/trending?geo=PE',
                        'indicador': 'Consulta en tendencia', 'valor': None, 'metrica': 'trafico_rss',
                        'etiqueta_original': r['trafico'], 'referencia': 'Tendencias actuales de Perú',
                        'periodo': 'Feed actual', 'publicado': r['publicado'].isoformat(), 'proveedor': 'Google RSS',
                    })
        else:
            # Máximo 12 solicitudes por actualización, sin paginación ni reintentos.
            with ThreadPoolExecutor(max_workers=3) as ejecutor:
                trabajos = {ejecutor.submit(proveedor.consultar, fuente, categoria): (fuente, categoria)
                            for fuente in ('google', 'tiktok') for categoria in CATEGORIAS_RADAR}
                for trabajo in as_completed(trabajos):
                    fuente, categoria = trabajos[trabajo]
                    try:
                        items = trabajo.result()
                    except ValueError as error:
                        resultado['advertencias'].append(f'{fuente} / {CATEGORIAS_RADAR[categoria]["nombre"]}: {error}')
                    else:
                        resultado['correctas'] += 1
                        resultado['items'].extend(items)
            if resultado['correctas'] == 0:
                raise ValueError('Las fuentes no respondieron. Revisa la conexión, clave y cuota del proveedor. Se conservan los últimos resultados.')
        vistos = set()
        unicos = []
        orden_categorias = {c: i for i, c in enumerate(CATEGORIAS_RADAR)}
        for item in sorted(resultado['items'], key=lambda i: (
                orden_categorias[i['categoria']], i['fuente'],
                0 if i['metrica'] == 'crecimiento' else 1,
                i['referencia'], i.get('posicion', 0), normalizar(i['termino']))):
            identificador = (item['fuente'], item['url'] if item['fuente'] == 'tiktok' else normalizar(item['termino']))
            if identificador not in vistos:
                unicos.append(item)
                vistos.add(identificador)
        resultado['items'] = unicos
        self._cache = resultado
        return dict(resultado)
