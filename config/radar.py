"""Ámbitos de exploración, NO una lista de productos detectados."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / '.env')

CATEGORIAS_RADAR = {
    'hogar': {'nombre': 'Hogar', 'google': 'hogar', 'tiktok': 'productos para el hogar', 'icono': '⌂'},
    'limpieza': {'nombre': 'Limpieza', 'google': 'limpieza', 'tiktok': 'productos de limpieza', 'icono': '✧'},
    'juegos': {'nombre': 'Juegos y juguetes', 'google': 'juguetes', 'tiktok': 'juguetes virales', 'icono': '▦'},
    'peliculas': {'nombre': 'Películas', 'google': 'películas', 'tiktok': 'merchandising peliculas', 'icono': '▷'},
    'navidad': {'nombre': 'Navidad', 'google': 'navidad', 'tiktok': 'decoracion de navidad', 'icono': '☆'},
    'regalos': {'nombre': 'Regalos', 'google': 'regalos', 'tiktok': 'regalos originales', 'icono': '◇'},
}


def conexion_comercial():
    # Tener una clave no basta: el administrador debe habilitar el consumo.
    habilitado = os.getenv('RADAR_SERPAPI_ENABLED', '').lower() in ('1', 'true', 'yes')
    return os.getenv('SERPAPI_API_KEY', '').strip() if habilitado else ''
