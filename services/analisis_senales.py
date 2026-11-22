"""Cambios descriptivos sobre una única serie comparable; no pronósticos."""


def resumen_crecimiento(items):
    if not items:
        return 'Sin observaciones guardadas.'
    puntos = [p for p in items if not p.get('parcial')]
    if len(puntos) < 2 or any(p.get('valor') is None for p in puntos[-2:]):
        return 'Crecimiento no calculable: se necesitan dos puntos completos con cifras comparables.'
    previo, ultimo = puntos[-2:]
    if ultimo['metrica'] in ('crecimiento', 'presencia', 'trafico_rss'):
        return 'Se muestran valores originales; no se calcula un crecimiento adicional sobre esta métrica.'
    a, b = previo['valor'], ultimo['valor']
    fechas = f'{previo["observado_en"][:10]} → {ultimo["observado_en"][:10]}'
    if ultimo['metrica'] == 'posicion':
        return f'{fechas}: cambio de posición {b - a:+g}; menor posición es mejor.'
    if not a:
        return f'{fechas}: base cero, porcentaje no calculable. Cambio absoluto: {b - a:+g}.'
    return f'{fechas}: cambio respecto al punto anterior {(b - a) / a * 100:+.1f}% ({a:g} → {b:g}). No es crecimiento de ventas.'
