from datetime import date, timedelta
from pathlib import Path
from statistics import mean

import psycopg

from models.tendencia import AnalisisTendencia
from repositories.tendencias_repository import TendenciasRepository
from services.fuentes_tendencias import FuenteGoogleTrends, PAISES, normalizar, url_segura
from services.radar_automatico import RadarAutomatico


def analizar_serie(serie, hoy=None):
    """Heurística explicable, no pronóstico de ventas ni porcentaje de mercado."""
    if not serie:
        return AnalisisTendencia('Sin datos', None, None, 'Importa un histórico de Google Trends para este país.')
    hoy = hoy or date.today()
    puntos = [p for p in serie['puntos'] if not p.get('parcial')]
    intervalo = {'dia': 1, 'semana': 7, 'mes': 31}[serie['granularidad']]
    reciente = bool(puntos and (hoy - date.fromisoformat(puntos[-1]['fecha'])).days <= intervalo * 2 + 2)
    if len(puntos) < 8 or any(p['valor'] is None for p in puntos[-8:]):
        return AnalisisTendencia('Datos insuficientes', None, None,
                                 'Se necesitan 8 observaciones completas consecutivas; <1 y ausentes no se estiman.', reciente)
    base = mean(p['valor'] for p in puntos[-8:-4])
    actual = mean(p['valor'] for p in puntos[-4:])
    crecimiento = ((actual - base) / base * 100) if base else None
    if base == 0 and actual >= 10:
        estado = 'Emergente'
    elif crecimiento is not None and crecimiento <= -20:
        estado = 'En descenso'
    elif crecimiento is not None and crecimiento >= 25 and actual >= 10:
        estado = 'Emergente' if base < 20 else 'En crecimiento'
    elif actual >= 40:
        estado = 'Consolidada'
    else:
        estado = 'Sin señal clara'
    motivo = (f'Media anterior: {base:.1f}; media reciente: {actual:.1f}. '
              'Se comparan los últimos 4 puntos completos con los 4 anteriores. '
              + ('Base cero: crecimiento porcentual no calculable. ' if base == 0 else '')
              + ('Histórico desactualizado: no representa una señal actual.' if not reciente else ''))
    return AnalisisTendencia(estado, actual, crecimiento, motivo, reciente)


def preparar_panel(datos, dias=None, hoy=None):
    hoy = hoy or date.today()
    series = {}
    for original in datos['series']:
        serie = dict(original)
        if dias:
            limite = (hoy - timedelta(days=dias)).isoformat()
            serie['puntos'] = [p for p in serie['puntos'] if p['fecha'] >= limite]
        series[(serie['id_tema'], serie['pais'])] = serie
    filas = []
    for tema in datos['temas']:
        fila = dict(tema)
        fila['series'] = {pais: series.get((tema['id_tema'], pais)) for pais in PAISES}
        fila['analisis'] = {pais: analizar_serie(fila['series'][pais], hoy) for pais in PAISES}
        fila['evidencias'] = [e for e in datos['evidencias'] if e['id_tema'] == tema['id_tema']]
        pe = fila['analisis']['PE']
        if not pe.reciente or pe.interes is None:
            oportunidad = 'Validar señal en Perú'
        elif pe.estado in ('Emergente', 'En crecimiento'):
            oportunidad = 'Evaluar prueba comercial'
        elif pe.estado == 'En descenso':
            oportunidad = 'Revisar riesgo antes de comprar'
        elif pe.estado == 'Consolidada':
            oportunidad = 'Evaluar continuidad'
        else:
            oportunidad = 'Seguir observando'
        fila['oportunidad'] = oportunidad
        filas.append(fila)
    prioridad = {'Evaluar prueba comercial': 0, 'Evaluar continuidad': 1,
                 'Validar señal en Perú': 2, 'Seguir observando': 3,
                 'Revisar riesgo antes de comprar': 4}
    return sorted(filas, key=lambda f: (prioridad[f['oportunidad']], normalizar(f['termino'])))


class TendenciasService:
    def __init__(self, repositorio=None, fuente=None, radar=None):
        self._repositorio = repositorio if repositorio is not None else TendenciasRepository()
        self._fuente = fuente if fuente is not None else FuenteGoogleTrends()
        self._radar = radar if radar is not None else RadarAutomatico(self._fuente)

    def ejecutar(self, accion, **opciones):
        if accion in ('cargar_radar', 'buscar_radar'):
            return self._ejecutar_radar(accion, opciones)
        try:
            mensaje = ''
            if accion == 'sincronizar':
                advertencias = []
                cantidades = []
                for pais in dict.fromkeys(('PE', opciones['pais'])):
                    try:
                        registros = self._fuente.obtener_descubrimientos(pais)
                    except ValueError as error:
                        advertencias.append(f'{PAISES[pais]}: {error}')
                        continue
                    self._repositorio.guardar_descubrimientos(registros)
                    cantidades.append(f'{PAISES[pais]}: {len(registros)} consultas')
                mensaje = ' · '.join(cantidades + advertencias)
                if not cantidades:
                    raise ValueError(mensaje or 'No se pudo consultar ninguna fuente.')
            elif accion == 'crear':
                termino = opciones['termino'].strip()
                if not termino or len(termino) > 200:
                    raise ValueError('Escribe un término de entre 1 y 200 caracteres.')
                imagen = opciones.get('imagen') or None
                if imagen and (not Path(imagen).is_file() or Path(imagen).suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp')):
                    raise ValueError('La imagen debe ser un archivo local PNG, JPG o WebP existente.')
                creado = self._repositorio.guardar_tema(
                    termino, normalizar(termino), opciones.get('id_categoria'),
                    opciones.get('id_producto'), imagen, opciones['id_usuario'])
                mensaje = 'Producto incorporado al seguimiento.' if creado else 'Ese término ya está en seguimiento; no se modificó.'
            elif accion == 'importar':
                tema = self._obtener_tema(opciones['id_tema'])
                serie = self._fuente.leer_csv(opciones['ruta'], tema['termino'],
                                             opciones['pais'], opciones['ultimo_parcial'])
                creado = self._repositorio.guardar_serie(tema['id_tema'], serie, opciones['id_usuario'])
                mensaje = 'Histórico importado. Se conservan la serie, el nombre de archivo y su huella SHA256.' if creado else 'Este histórico ya estaba importado; no se duplicó.'
            elif accion == 'evidencia':
                self._obtener_tema(opciones['id_tema'])
                url = opciones['url'].strip()
                nota = opciones['nota'].strip()
                if not url_segura(url, 'tiktok.com') or len(url) > 2000:
                    raise ValueError('Usa un enlace HTTPS de tiktok.com o ads.tiktok.com.')
                if opciones['pais'] not in PAISES:
                    raise ValueError('País no disponible.')
                if not nota or len(nota) > 2000:
                    raise ValueError('Describe lo observado (hasta 2000 caracteres), incluyendo periodo y contexto si están disponibles.')
                if opciones['observado_el'] > date.today():
                    raise ValueError('La fecha de observación no puede ser futura.')
                creado = self._repositorio.guardar_evidencia(
                    opciones['id_tema'], opciones['pais'], url, opciones['observado_el'], nota, opciones['id_usuario'])
                mensaje = ('Evidencia manual guardada; no ha sido verificada automáticamente.' if creado
                           else 'Ese enlace y fecha ya estaban registrados para este país.')
            elif accion != 'cargar':
                raise ValueError('Acción de radar no disponible.')
            return {'datos': self._repositorio.cargar(), 'mensaje': mensaje}
        except psycopg.errors.UndefinedTable:
            raise ValueError('Falta instalar el radar en PostgreSQL. Ejecuta database/radar_tendencias.sql sobre la base existente.') from None
        except psycopg.errors.IntegrityConstraintViolation:
            raise ValueError('No se pudo guardar: el usuario, producto o categoría ya no está disponible. Recarga el radar.') from None
        except psycopg.Error:
            raise ValueError('No se pudo acceder a PostgreSQL. Revisa la conexión y los permisos; no se mostrarán datos simulados.') from None
        except OSError:
            raise ValueError('No se pudo leer el archivo seleccionado. Revisa su ubicación y permisos.') from None

    def _obtener_tema(self, id_tema):
        datos = self._repositorio.cargar()
        tema = next((t for t in datos['temas'] if t['id_tema'] == id_tema), None)
        if tema is None:
            raise ValueError('Selecciona un producto en seguimiento válido.')
        return tema

    def _ejecutar_radar(self, accion, opciones):
        historial = True
        if accion == 'buscar_radar':
            resultado = self._radar.buscar()
            if not resultado.get('cache'):
                try:
                    self._repositorio.guardar_busqueda(resultado, opciones['id_usuario'])
                except (psycopg.Error, ValueError):
                    historial = False  # La falta de migración no impide consultar fuentes.
        else:
            try:
                resultado = self._repositorio.cargar_busqueda()
            except (psycopg.Error, ValueError):
                resultado, historial = None, False
        return {'radar': resultado, 'historial': historial,
                'conexion_comercial': self._radar.estado_conexion()}
