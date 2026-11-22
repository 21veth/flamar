"""Fuentes públicas: RSS oficial y CSV exportado por el usuario, sin scraping."""

import csv
import hashlib
import io
import re
import unicodedata
from datetime import date, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from models.tendencia import PuntoInteres, SerieInteres


PAISES = {'PE': 'Perú', 'US': 'Estados Unidos', 'MX': 'México',
          'CL': 'Chile', 'CO': 'Colombia', 'BR': 'Brasil'}
ALIAS_PAISES = {
    'PE': ('peru',), 'US': ('estados unidos', 'united states'),
    'MX': ('mexico',), 'CL': ('chile',), 'CO': ('colombia',),
    'BR': ('brasil', 'brazil'),
}
NS = {'ht': 'https://trends.google.com/trending/rss'}
LIMITE_BYTES = 2_000_000


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', texto)
                           if not unicodedata.combining(c)).casefold().split())


def url_google(termino, pais, periodo='today 3-m'):
    return 'https://trends.google.com/trends/explore?' + urlencode(
        {'geo': pais, 'q': termino, 'date': periodo, 'hl': 'es'})


def url_segura(url, dominio=None):
    try:
        partes = urlparse(url)
        host = (partes.hostname or '').lower()
        return (partes.scheme == 'https' and bool(host) and not partes.username
                and not partes.password and partes.port in (None, 443)
                and (dominio is None or host == dominio or host.endswith('.' + dominio)))
    except ValueError:
        return False


class FuenteGoogleTrends:
    def obtener_descubrimientos(self, pais):
        if pais not in PAISES:
            raise ValueError('País no disponible.')
        url = 'https://trends.google.com/trending/rss?' + urlencode({'geo': pais})
        peticion = Request(url, headers={'User-Agent': 'FlamarRadar/1.0',
                                        'Accept': 'application/rss+xml, application/xml'})
        try:
            with urlopen(peticion, timeout=15) as respuesta:
                contenido = respuesta.read(LIMITE_BYTES + 1)
        except HTTPError as error:
            if error.code == 429:
                raise ValueError('Google limitó las solicitudes. Espera unos minutos; no se reintentará automáticamente.') from None
            raise ValueError(f'Google Trends no respondió correctamente (HTTP {error.code}).') from None
        except (URLError, TimeoutError, OSError):
            raise ValueError('No se pudo consultar Google Trends. Revisa Internet e inténtalo más tarde.') from None
        return self.leer_rss(contenido, pais, url)

    @staticmethod
    def leer_rss(contenido, pais, url):
        if (len(contenido) > LIMITE_BYTES or b'<!DOCTYPE' in contenido.upper()
                or b'<!ENTITY' in contenido.upper()):
            raise ValueError('El feed excede el tamaño permitido o contiene XML no admitido.')
        try:
            raiz = ElementTree.fromstring(contenido)
        except ElementTree.ParseError:
            raise ValueError('Google devolvió un feed no válido.') from None
        if raiz.tag != 'rss' or raiz.find('channel') is None:
            raise ValueError('La respuesta no es un feed RSS de Google Trends.')
        resultados = []
        for item in raiz.findall('./channel/item')[:100]:
            titulo = (item.findtext('title') or '').strip()[:200]
            try:
                publicado = parsedate_to_datetime(item.findtext('pubDate') or '')
                publicado = publicado.replace(tzinfo=publicado.tzinfo or timezone.utc)
            except (ValueError, TypeError, IndexError):
                continue
            if not titulo:
                continue
            noticias = []
            for noticia in item.findall('ht:news_item', NS)[:3]:
                enlace = noticia.findtext('ht:news_item_url', '', NS)
                if url_segura(enlace):
                    noticias.append({'titulo': noticia.findtext('ht:news_item_title', '', NS)[:300],
                                     'url': enlace})
            resultados.append({
                'termino': titulo, 'pais': pais, 'publicado': publicado,
                'trafico': item.findtext('ht:approx_traffic', '', NS)[:50],
                'url': url_google(titulo, pais), 'feed_url': url, 'noticias': noticias,
            })
        return resultados

    @staticmethod
    def leer_csv(ruta, termino, pais, ultimo_parcial=True):
        """Un único término y país por exportación; nunca mezcla escalas de archivos."""
        if pais not in PAISES:
            raise ValueError('Selecciona un país disponible.')
        ruta = Path(ruta)
        if ruta.stat().st_size > LIMITE_BYTES:
            raise ValueError('El CSV no puede superar 2 MB.')
        contenido = ruta.read_bytes()
        try:
            texto = contenido.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError('Exporta el CSV de Google Trends en UTF-8.') from None
        filas = list(csv.reader(io.StringIO(texto)))
        cabeceras = {'dia': 'dia', 'day': 'dia', 'semana': 'semana',
                     'week': 'semana', 'mes': 'mes', 'month': 'mes'}
        indice = next((i for i, fila in enumerate(filas) if fila and
                       normalizar(fila[0]) in cabeceras), None)
        if indice is None:
            raise ValueError('No se encontró «Interés a lo largo del tiempo». Usa el CSV de Explorar, no el de Tendencias actuales.')
        cabecera = filas[indice]
        if len(cabecera) != 2:
            raise ValueError('Exporta un solo término y un solo país por CSV, sin comparaciones.')
        etiqueta = normalizar(cabecera[1])
        esperado = normalizar(termino)
        coincidencia = re.fullmatch(r'(.+):\s*\((.+)\)', etiqueta)
        if (not coincidencia or coincidencia[1].strip() != esperado
                or coincidencia[2].strip() not in ALIAS_PAISES[pais]):
            raise ValueError('El término o país del CSV no coincide con la selección. Usa el término exacto del encabezado de Google.')
        granularidad = cabeceras[normalizar(cabecera[0])]
        puntos = []
        for fila in filas[indice + 1:]:
            if not fila or not any(c.strip() for c in fila):
                continue
            if len(fila) != 2:
                raise ValueError('El CSV contiene una fila con columnas inesperadas.')
            try:
                fecha = date.fromisoformat(fila[0].strip() + ('-01' if granularidad == 'mes' else ''))
            except ValueError:
                raise ValueError('Fechas no admitidas: usa datos diarios, semanales o mensuales en formato ISO.') from None
            original = fila[1].strip()
            if original in ('', '<1', '< 1'):
                valor = None  # censurado o ausente: no se inventa 0 ni 0.5
            elif re.fullmatch(r'\d{1,3}', original) and int(original) <= 100:
                valor = int(original)
            else:
                raise ValueError('El CSV debe contener índices de Google entre 0 y 100, o <1.')
            if fecha > date.today() or (puntos and fecha <= puntos[-1].fecha):
                raise ValueError('Las fechas deben estar ordenadas, sin duplicados ni fechas futuras.')
            if puntos:
                anterior = puntos[-1].fecha
                salto = (fecha - anterior).days
                mensual = (fecha.year * 12 + fecha.month) - (anterior.year * 12 + anterior.month)
                if ((granularidad == 'dia' and salto != 1)
                        or (granularidad == 'semana' and salto != 7)
                        or (granularidad == 'mes' and (mensual != 1 or fecha.day != 1))):
                    raise ValueError('La serie tiene intervalos faltantes o incompatibles con su encabezado.')
            puntos.append(PuntoInteres(fecha, valor, original))
        if len(puntos) < 2 or len(puntos) > 2000:
            raise ValueError('El CSV debe tener entre 2 y 2000 observaciones.')
        if ultimo_parcial:
            ultimo = puntos[-1]
            puntos[-1] = PuntoInteres(ultimo.fecha, ultimo.valor, ultimo.original, True)
        huella = hashlib.sha256(contenido).hexdigest()
        return SerieInteres(termino, pais, granularidad, tuple(puntos), ruta.name,
                            huella, url_google(termino, pais))
