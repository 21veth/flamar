"""Clasificación conservadora de señales recibidas, nunca semillas de resultados."""

import re

from services.fuentes_tendencias import normalizar


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
        if any(contiene(texto, p) for c in ('hogar', 'juegos', 'regalos') for p in VOCABULARIO[c]):
            return 'navidad', 'producto'
        return 'navidad', 'tema'
    for categoria in ('limpieza', 'juegos', 'hogar', 'regalos'):
        if any(contiene(texto, p) for p in VOCABULARIO[categoria]):
            return categoria, 'producto'
    if categoria_origen == 'peliculas' or any(contiene(texto, p) for p in ('pelicula', 'cine', 'estreno')):
        return 'peliculas', 'tema'
    return None, None
