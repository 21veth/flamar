"""Archivos del usuario: validación completa antes de cualquier escritura."""

import csv
import hashlib
import io
import json
import math
import re
from datetime import date
from pathlib import Path

from config.radar import CATEGORIAS_RADAR
from services.clasificacion_tendencias import clasificar_consulta
from services.fuentes_tendencias import FuenteGoogleTrends, LIMITE_BYTES, PAISES, normalizar, url_google, url_segura


METRICAS = {
    'reproducciones': 'Reproducciones', 'publicaciones': 'Publicaciones',
    'popularidad': 'Popularidad (escala de la fuente)', 'posicion': 'Posición (menor es mejor)',
    'crecimiento': 'Crecimiento reportado (%)', 'presencia': 'Presencia sin cifra',
    'interes_relativo': 'Interés relativo (0–100)', 'trafico_rss': 'Tráfico aproximado (texto)',
}
TIKTOK_COLUMNAS = ('termino', 'tipo', 'categoria', 'pais', 'fecha', 'metrica', 'valor',
                   'valor_original', 'periodo', 'contexto', 'url')


def huella_json(datos):
    return hashlib.sha256(json.dumps(datos, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def clave_serie(item):
    # Nunca mezclar fuentes, países, métricas, tipos ni escalas/ventanas distintas.
    return huella_json({k: item.get(k) for k in
                       ('termino_clave', 'fuente', 'origen', 'pais', 'metrica', 'contexto', 'tipo')})


def preparar_items(items):
    vistos = set()
    for item in items:
        item['termino_clave'] = normalizar(item['termino'])
        item['clave_serie'] = clave_serie(item)
        identidad = (item['clave_serie'], item['observado_en'])
        if identidad in vistos:
            raise ValueError('Hay observaciones duplicadas para la misma serie y fecha. Revisa el archivo/fuente.')
        vistos.add(identidad)
    return items


def fecha_valida(texto):
    try:
        fecha = date.fromisoformat(texto)
    except (ValueError, TypeError):
        raise ValueError('Usa fechas ISO AAAA-MM-DD.') from None
    if fecha > date.today():
        raise ValueError('No se permiten fechas futuras.')
    return fecha.isoformat()


def leer_importacion(ruta, formato, pais='PE', periodo='', referencia='', fecha=None, ultimo_parcial=True):
    ruta = Path(ruta)
    if ruta.stat().st_size > LIMITE_BYTES:
        raise ValueError('El CSV no puede superar 2 MB.')
    contenido = ruta.read_bytes()
    try:
        texto = contenido.decode('utf-8-sig')
        filas = list(csv.reader(io.StringIO(texto), strict=True))
    except (UnicodeDecodeError, csv.Error):
        raise ValueError('El archivo debe ser un CSV válido UTF-8, separado por comas.') from None
    if pais not in PAISES:
        raise ValueError('País no disponible.')
    sha = hashlib.sha256(contenido).hexdigest()
    if formato == 'google_timeline':
        cabecera = next((f for f in filas if f and normalizar(f[0]) in
                         ('dia', 'day', 'semana', 'week', 'mes', 'month')), [])
        if len(cabecera) != 2:
            raise ValueError('Exporta Interés a lo largo del tiempo de un solo término y país.')
        coincidencia = re.fullmatch(r'(.+):\s*\((.+)\)', cabecera[1])
        if not coincidencia:
            raise ValueError('No se reconoce el término y país del encabezado de Google.')
        termino = coincidencia[1].strip()
        if not 1 <= len(termino) <= 200:
            raise ValueError('El término debe tener entre 1 y 200 caracteres.')
        serie = FuenteGoogleTrends.leer_csv(ruta, termino, pais, ultimo_parcial)
        if serie.huella != sha:
            raise ValueError('El archivo cambió durante la lectura. Repite la importación.')
        categoria, tipo = clasificar_consulta(termino)
        items = [dict(termino=termino, categoria=categoria or 'otros', tipo=tipo or 'consulta',
                      fuente='google', pais=pais, url=serie.url, indicador='Histórico importado de Google Trends',
                      valor=p.valor, etiqueta_original=p.original, metrica='interes_relativo',
                      referencia=termino, periodo=f'{serie.puntos[0].fecha} / {serie.puntos[-1].fecha}',
                      contexto='exportacion/' + sha, observado_en=p.fecha.isoformat() + 'T00:00:00+00:00',
                      parcial=p.parcial, proveedor='Google Trends CSV', origen='google_timeline') for p in serie.puntos]
    elif formato == 'google_now':
        fecha = fecha_valida(fecha)
        if not filas or len(filas[0]) < 2 or normalizar(filas[0][0]) not in ('trends', 'tendencias', 'tendencia') or normalizar(filas[0][1]) not in ('search volume', 'volumen de busqueda', 'volumen de busquedas'):
            raise ValueError('No se reconoce el CSV nativo de Tendencias actuales (Trends,Search volume,…).')
        items, vistos = [], set()
        for fila in filas[1:]:
            if not fila or not any(c.strip() for c in fila):
                continue
            if len(fila) != len(filas[0]) or not 1 <= len(fila[0].strip()) <= 200:
                raise ValueError('Tendencias actuales: fila incompleta o término demasiado largo.')
            termino = fila[0].strip()
            if normalizar(termino) in vistos:
                raise ValueError('Hay consultas duplicadas en el CSV de Tendencias actuales.')
            vistos.add(normalizar(termino))
            categoria, tipo = clasificar_consulta(termino)
            items.append(dict(termino=termino, categoria=categoria or 'otros', tipo=tipo or 'consulta',
                fuente='google', pais=pais, url=url_google(termino, pais),
                indicador='Tendencias actuales · país declarado por el usuario', valor=None,
                etiqueta_original=fila[1].strip()[:100], metrica='trafico_rss', referencia='Tendencias actuales CSV',
                periodo='Exportación de Tendencias actuales', contexto='google_now/' + pais,
                observado_en=fecha + 'T00:00:00+00:00', proveedor='Google Trends CSV', origen='google_now'))
    elif formato == 'google_related':
        if not referencia.strip() or not periodo.strip() or max(len(referencia), len(periodo)) > 300:
            raise ValueError('Indica la consulta de origen y el periodo exactos del CSV relacionado.')
        fecha = fecha_valida(fecha)
        items, grupo = [], None
        for fila in filas:
            if not fila or not any(c.strip() for c in fila):
                continue
            titulo = normalizar(fila[0])
            if titulo in ('top', 'principales', 'mas buscadas', 'rising', 'en aumento') and len(fila) == 1:
                grupo = 'top' if titulo in ('top', 'principales', 'mas buscadas') else 'rising'
                continue
            if grupo is None:
                continue  # Google incluye preámbulos; el contexto es declarado en la importación.
            if len(fila) != 2 or not fila[0].strip():
                raise ValueError('Consultas relacionadas: se esperaban filas término,valor después de TOP/RISING.')
            termino, original = fila[0].strip(), fila[1].strip()
            if len(termino) > 200:
                raise ValueError('Una consulta supera los 200 caracteres.')
            valor = None
            if grupo == 'top' and re.fullmatch(r'\d{1,3}', original) and int(original) <= 100:
                valor = int(original)
            elif grupo == 'rising':
                if normalizar(original) not in ('breakout', 'aumento puntual', 'aumento extraordinario'):
                    numero = original.rstrip('%').replace(',', '').replace(' ', '').lstrip('+')
                    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', numero):
                        numero = numero.replace('.', '')
                    if not re.fullmatch(r'\d{1,12}', numero):
                        raise ValueError('Crecimiento relacionado no reconocido; no se estimará un valor.')
                    valor = int(numero)
            else:
                raise ValueError('Índice TOP no válido: debe estar entre 0 y 100.')
            categoria, tipo = clasificar_consulta(termino)
            items.append(dict(termino=termino, categoria=categoria or 'otros', tipo=tipo or 'consulta',
                fuente='google', pais=pais, url=url_google(referencia, pais),
                indicador='Consulta relacionada · contexto declarado por el usuario', valor=valor,
                etiqueta_original=original, metrica='interes_relativo' if grupo == 'top' else 'crecimiento',
                referencia=referencia, periodo=periodo, contexto=f'exportacion/{sha}/{grupo}',
                observado_en=fecha + 'T00:00:00+00:00', proveedor='Google Trends CSV', origen='google_related'))
    elif formato == 'tiktok_manual':
        if not filas or tuple(filas[0]) != TIKTOK_COLUMNAS:
            raise ValueError('Usa la plantilla TikTok del radar; no se afirma compatibilidad con un exportador nativo universal.')
        items, vistos = [], set()
        for numero, fila in enumerate(filas[1:], 2):
            if not fila or not any(c.strip() for c in fila):
                continue
            if len(fila) != len(TIKTOK_COLUMNAS):
                raise ValueError(f'Fila {numero}: número de columnas incorrecto.')
            r = dict(zip(TIKTOK_COLUMNAS, (c.strip() for c in fila)))
            if not 1 <= len(r['termino']) <= 200 or r['tipo'] not in ('producto', 'hashtag', 'consulta', 'tema', 'video'):
                raise ValueError(f'Fila {numero}: término o tipo inválido.')
            if r['categoria'] not in CATEGORIAS_RADAR or r['pais'] not in (*PAISES, 'ND'):
                raise ValueError(f'Fila {numero}: categoría o país inválido; usa ND si no está confirmado.')
            if (r['metrica'] not in METRICAS or r['metrica'] in ('trafico_rss', 'interes_relativo')
                    or not url_segura(r['url'], 'tiktok.com') or len(r['url']) > 2000):
                raise ValueError(f'Fila {numero}: métrica o enlace HTTPS de TikTok inválido.')
            if not r['periodo'] or not r['contexto'] or max(len(r['periodo']), len(r['contexto'])) > 300:
                raise ValueError(f'Fila {numero}: indica periodo y contexto comparables (máximo 300 caracteres).')
            fecha_r = fecha_valida(r['fecha'])
            valor = None
            if r['valor']:
                try:
                    valor = float(r['valor'])
                except ValueError:
                    raise ValueError(f'Fila {numero}: valor numérico inválido; usa punto decimal y sin separadores.') from None
                if not math.isfinite(valor) or abs(valor) > 1e15 or (valor < 0 and r['metrica'] != 'crecimiento'):
                    raise ValueError(f'Fila {numero}: valor fuera de rango.')
                if r['metrica'] in ('posicion', 'publicaciones', 'reproducciones') and (not valor.is_integer() or (r['metrica'] == 'posicion' and valor < 1)):
                    raise ValueError(f'Fila {numero}: se esperaba un recuento entero o posición positiva.')
            if r['metrica'] == 'presencia' and valor is not None:
                raise ValueError(f'Fila {numero}: presencia no tiene cifra.')
            if len(r['valor_original']) > 100:
                raise ValueError(f'Fila {numero}: valor original demasiado largo.')
            # 1.2M, <1 y ausentes se conservan como texto; nunca se inventan cifras exactas.
            item = dict(termino=r['termino'], categoria=r['categoria'], tipo=r['tipo'],
                fuente='tiktok', pais=None if r['pais'] == 'ND' else r['pais'], url=r['url'],
                indicador='Observación manual · no verificada automáticamente', valor=valor,
                etiqueta_original=r['valor_original'] or r['valor'], metrica=r['metrica'], referencia=r['contexto'],
                periodo=r['periodo'], contexto=r['contexto'] + '/' + r['periodo'],
                observado_en=fecha_r + 'T00:00:00+00:00', proveedor='TikTok · registro del usuario', origen='tiktok_manual')
            identidad = (normalizar(r['termino']), r['pais'], r['metrica'], item['contexto'], r['tipo'], fecha_r)
            if identidad in vistos:
                raise ValueError(f'Fila {numero}: observación duplicada dentro del archivo.')
            vistos.add(identidad)
            items.append(item)
    else:
        raise ValueError('Formato de importación no disponible.')
    if not items or len(items) > 2000:
        raise ValueError('El archivo debe contener entre 1 y 2000 observaciones reconocibles.')
    for item in items:
        item['archivo'] = ruta.name
        item['sha256'] = sha
    preparar_items(items)
    identidad = [{k: v for k, v in item.items() if k != 'archivo'} for item in items]
    return dict(items=items, archivo=ruta.name, formato=formato,
                huella=huella_json({'sha256': sha, 'items': identidad}), sha256=sha)
