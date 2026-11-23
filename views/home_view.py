"""Punto de compatibilidad del shell único de la aplicación."""

from controllers.recuperacion_controller import RecuperacionController
from views.app_shell import (
    ADMIN_ITEMS, DECISION_ITEMS, INTELLIGENCE_ITEMS, PAGE_ITEMS,
    AppShell, NavButton, NativePageView, ResponsivePageView,
)


HomeView = AppShell

__all__ = [
    'HomeView', 'AppShell', 'NavButton', 'NativePageView', 'ResponsivePageView',
    'PAGE_ITEMS', 'INTELLIGENCE_ITEMS', 'DECISION_ITEMS', 'ADMIN_ITEMS',
    'RecuperacionController',
]
