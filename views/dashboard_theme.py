"""Compatibilidad: el tema Zeyver vive ahora en ``views.app_theme``."""

from views.app_theme import (
    APP_PALETTE as DASHBOARD_PALETTE,
    APP_PAGE_STYLESHEET as DASHBOARD_STYLES,
    APP_SHELL_STYLESHEET as DASHBOARD_SHELL_STYLES,
    APP_STYLESHEET,
    LOGO_PATH,
    ZeyverLogo,
    zeyver_color,
    zeyver_stylesheet,
)

__all__ = [
    'DASHBOARD_PALETTE', 'DASHBOARD_STYLES', 'DASHBOARD_SHELL_STYLES',
    'APP_STYLESHEET', 'LOGO_PATH', 'ZeyverLogo', 'zeyver_color', 'zeyver_stylesheet',
]
