"""Solo endpoints oficiales autorizados; sin cookies, scraping ni OAuth embebido."""

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from config.radar import conexion_tiktok
from services.clasificacion_tendencias import clasificar_consulta
from services.fuentes_tendencias import LIMITE_BYTES


class FuenteTikTokDiscovery:
    def __init__(self, configuracion=None):
        self.config = configuracion if configuracion is not None else conexion_tiktok()

    def configurada(self):
        c = self.config
        return bool(c['habilitado'] and ((c['advertiser_token'] and c['advertiser_id'])
                                        or (c['business_token'] and c['business_id'])))

    @staticmethod
    def _get(endpoint, token, parametros):
        peticion = Request('https://business-api.tiktok.com/open_api/v1.3/' + endpoint + '/?' + urlencode(parametros),
                           headers={'Access-Token': token, 'Accept': 'application/json'})
        try:
            with urlopen(peticion, timeout=15) as respuesta:
                contenido = respuesta.read(LIMITE_BYTES + 1)
            if len(contenido) > LIMITE_BYTES:
                raise ValueError('Respuesta de TikTok demasiado grande.')
            datos = json.loads(contenido)
        except HTTPError as error:
            raise ValueError(f'TikTok respondió HTTP {error.code}. Revisa autorización, cuota y disponibilidad de Perú.') from None
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, ValueError):
            raise ValueError('No se pudo consultar TikTok Discovery.') from None
        if not isinstance(datos, dict) or datos.get('code') != 0 or not isinstance(datos.get('data'), dict):
            # Nunca registrar mensajes ni URLs del proveedor: pueden contener secretos.
            raise ValueError('TikTok rechazó la consulta. Verifica permisos, token, cuenta y cobertura; no se cambió de país.')
        return datos['data']

    def obtener(self):
        if not self.configurada():
            return [], ['TikTok automático no autorizado/configurado. Usa la importación gratuita de observaciones reales.'], 0
        c = self.config
        items, avisos, correctas = [], [], 0
        ahora = datetime.now(timezone.utc).isoformat()
        if c['advertiser_token'] and c['advertiser_id']:
            try:
                datos = self._get('discovery/trending_list', c['advertiser_token'], {
                    'advertiser_id': c['advertiser_id'], 'discovery_type': 'HASHTAG',
                    'country_code': 'PE', 'category_name': 'ALL', 'date_range': '7DAY'})
                # No atribuir el país solicitado sin confirmación del filtro devuelto.
                filtros = datos.get('filter_info')
                if not isinstance(filtros, dict) or filtros.get('country_code') != 'PE' or filtros.get('date_range') != '7DAY':
                    raise ValueError('TikTok no confirmó Perú y 7DAY; se rechazaron los resultados, sin fallback a EE. UU.')
                if not isinstance(datos.get('list'), list):
                    raise ValueError('Formato de hashtags de TikTok no reconocido.')
                correctas += 1
                for fila in datos['list'][:200]:
                    if not isinstance(fila, dict) or not isinstance(fila.get('hashtag_name'), str):
                        continue
                    nombre = fila['hashtag_name'].strip()[:200]
                    if not nombre:
                        continue
                    categoria, _ = clasificar_consulta(nombre)
                    valor = fila.get('views')
                    if not isinstance(valor, int) or isinstance(valor, bool) or valor < 0:
                        valor = None
                    items.append(dict(termino=nombre, categoria=categoria or 'otros', tipo='hashtag',
                        fuente='tiktok', pais='PE', url='https://www.tiktok.com/tag/' + quote(nombre.lstrip('#'), safe=''),
                        indicador='Hashtag · no producto validado', valor=valor, metrica='reproducciones',
                        etiqueta_original=str(valor) if valor is not None else '', referencia='HASHTAG/ALL',
                        periodo='7DAY', contexto='HASHTAG/ALL/7DAY', observado_en=ahora,
                        proveedor='TikTok Discovery API', origen='tiktok_api'))
            except ValueError as error:
                avisos.append(str(error))
        if c['business_token'] and c['business_id']:
            try:
                datos = self._get('discovery/trending/search', c['business_token'],
                                  {'business_id': c['business_id'], 'is_personalized': 'false'})
                if not isinstance(datos.get('search_keywords'), list):
                    raise ValueError('Formato de búsquedas de TikTok no reconocido.')
                correctas += 1
                for nombre in datos['search_keywords'][:20]:
                    if not isinstance(nombre, str) or not nombre.strip():
                        continue
                    nombre = nombre.strip()[:200]
                    categoria, _ = clasificar_consulta(nombre)
                    items.append(dict(termino=nombre, categoria=categoria or 'otros', tipo='consulta',
                        fuente='tiktok', pais=None, url='https://www.tiktok.com/search?' + urlencode({'q': nombre}),
                        indicador='Búsqueda en tendencia · país no informado', valor=None, metrica='presencia',
                        etiqueta_original='', referencia='Búsquedas no personalizadas', periodo='No informado por TikTok',
                        contexto='search/non_personalized', observado_en=ahora,
                        proveedor='TikTok Discovery API', origen='tiktok_api'))
            except ValueError as error:
                avisos.append(str(error))
        return items, avisos, correctas
