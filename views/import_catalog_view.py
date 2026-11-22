"""Pestana de catalogo estacional (pendiente de desarrollo)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from views.import_shared import IMPORT_STYLES


class CatalogImportTab(QWidget):
    TITLE = 'Catalogo estacional'

    def __init__(self, parent=None):
        super().__init__(parent, objectName='importTab')
        self.setStyleSheet(IMPORT_STYLES)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(QLabel(self.TITLE, objectName='importTabTitle'))
        header.addWidget(QLabel(
            'Carga campanas, temporadas y eventos para planificar tu inventario.',
            objectName='subtitle',
        ))
        layout.addLayout(header)

        card = QFrame(objectName='card')
        card.setMinimumHeight(300)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 26, 30, 26)
        card_layout.setSpacing(10)
        card_layout.addStretch()

        icon = QLabel('▣', objectName='importMetricIcon')
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(64, 64)
        icon.setStyleSheet('background: #f0edff; color: #5133f5; font-size: 26px;')
        card_layout.addWidget(icon, alignment=Qt.AlignCenter)

        title = QLabel('Catalogo estacional pendiente de desarrollo', objectName='sectionTitle')
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        copy = QLabel(
            'Esta seccion permitira importar campanas, temporadas y eventos '
            'para cruzar la demanda estacional con tu inventario. Por ahora '
            'solo esta disponible como vista informativa.',
            objectName='muted',
        )
        copy.setAlignment(Qt.AlignCenter)
        copy.setWordWrap(True)
        card_layout.addWidget(copy)
        card_layout.addStretch()

        badge_row = QHBoxLayout()
        badge_row.addStretch()
        badge = QLabel('Proximamente', objectName='purpleChip')
        badge.setAlignment(Qt.AlignCenter)
        badge_row.addWidget(badge)
        badge_row.addStretch()
        card_layout.addLayout(badge_row)

        layout.addWidget(card)
        layout.addStretch()
