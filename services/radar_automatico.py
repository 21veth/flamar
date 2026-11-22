"""Consulta gratuita real: RSS de Perú y Discovery solo con autorización explícita."""

from datetime import datetime, timedelta, timezone

from services.clasificacion_tendencias import clasificar_consulta
from services.fuentes_tendencias import FuenteGoogleTrends
from services.tiktok_discovery import FuenteTikTokDiscovery


class RadarAutomatico:
    def __init__(self, fuente_gratuita=None, tiktok=None):
        self._rss = fuente_gratuita if fuente_gratuita is not None else FuenteGoogleTrends()
        self._tiktok = tiktok if tiktok is not None else FuenteTikTokDiscovery()
        self._cache = None

    def estado_conexion(self):
        return self._tiktok.configurada()

    def buscar(self):
        ahora = datetime.now(timezone.utc)
        if self._cache and ahora - datetime.fromisoformat(self._cache['consultado_en']) < timedelta(minutes=15):
            return dict(self._cache, cache=True)
        resultado = dict(items=[], advertencias=[], consultado_en=ahora.isoformat(), cache=False,
                         modo='gratuito', correctas=0, recibidas_rss=0)
        items, avisos, correctas = self._tiktok.obtener()
        resultado['items'].extend(items)
        resultado['advertencias'].extend(avisos)
        resultado['correctas'] += correctas
        try:
            registros = self._rss.obtener_descubrimientos('PE')
        except ValueError as error:
            resultado['advertencias'].append(str(error))
        else:
            resultado['correctas'] += 1
            resultado['recibidas_rss'] = len(registros)
            for r in registros:
                categoria, tipo = clasificar_consulta(r['termino'])
                if categoria:
                    resultado['items'].append(dict(
                        termino=r['termino'], categoria=categoria, tipo=tipo,
                        fuente='google', pais='PE', url=r['url'], indicador='Consulta en tendencia',
                        valor=None, metrica='trafico_rss', etiqueta_original=r['trafico'],
                        referencia='RSS Perú', periodo='Feed actual', contexto='RSS/PE',
                        publicado=r['publicado'].isoformat(), observado_en=ahora.isoformat(),
                        proveedor='Google Trends RSS', origen='google_rss'))
        if not resultado['correctas']:
            raise ValueError('No respondió ninguna fuente. ' + ' · '.join(resultado['advertencias']))
        self._cache = resultado
        return dict(resultado)
