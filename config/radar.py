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
    'otros': {'nombre': 'Por clasificar', 'icono': '?'},
}
def conexion_comercial():
    # Tener una clave no basta: el administrador debe habilitar el consumo.
    habilitado = os.getenv('RADAR_SERPAPI_ENABLED', '').lower() in ('1', 'true', 'yes')
    return os.getenv('SERPAPI_API_KEY', '').strip() if habilitado else ''


def conexion_tiktok():
    """Configurar no equivale a estar autorizado: el servidor valida cada petición."""
    habilitado = os.getenv('RADAR_TIKTOK_ENABLED', '').lower() in ('1', 'true', 'yes')
    return {
        'habilitado': habilitado,
        'advertiser_token': os.getenv('TIKTOK_ADVERTISER_ACCESS_TOKEN', '').strip() if habilitado else '',
        'advertiser_id': os.getenv('TIKTOK_ADVERTISER_ID', '').strip() if habilitado else '',
        'business_token': os.getenv('TIKTOK_BUSINESS_ACCESS_TOKEN', '').strip() if habilitado else '',
        'business_id': os.getenv('TIKTOK_BUSINESS_ID', '').strip() if habilitado else '',
    }
